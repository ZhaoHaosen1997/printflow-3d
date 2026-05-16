from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Order, OrderItem, Buyer, Product
from backend.schemas import (
    OrderCreate, OrderUpdate, OrderResponse, OrderListResponse,
    OrderItemCreate, OrderItemResponse,
    ParseRequest, ParseResponse, ParsedOrder, ParsedOrderItem,
    MessageResponse,
)
from backend.services.parser_service import parse_order_text, match_products

router = APIRouter(prefix="/orders", tags=["orders"])

TERMINAL_STATUSES = {"交易成功", "已取消", "退货"}


def _generate_order_no(db: Session) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"ORD-{today}-"
    last = (
        db.query(Order)
        .filter(Order.order_no.like(f"{prefix}%"))
        .order_by(Order.order_no.desc())
        .first()
    )
    if last:
        seq = int(last.order_no.split("-")[-1]) + 1
    else:
        seq = 1
    return f"{prefix}{seq:03d}"


def _upsert_buyer(db: Session, nickname: str | None, province: str | None = None) -> int | None:
    if not nickname:
        return None
    buyer = db.query(Buyer).filter(Buyer.nickname == nickname).first()
    if buyer:
        return buyer.id
    buyer = Buyer(nickname=nickname, province=province)
    db.add(buyer)
    db.flush()
    return buyer.id


def _sync_buyer_stats(db: Session, buyer_id: int):
    buyer = db.query(Buyer).filter(Buyer.id == buyer_id).first()
    if not buyer:
        return
    orders = db.query(Order).filter(Order.buyer_id == buyer_id).all()
    buyer.total_orders = len(orders)
    buyer.total_amount = sum(
        (o.actual_amount for o in orders if o.status != "已取消"),
        Decimal("0"),
    )
    if orders:
        times = [o.order_time for o in orders if o.order_time]
        if times:
            buyer.first_order_time = min(times)
            buyer.last_order_time = max(times)
    db.commit()


def _get_settings(db: Session) -> dict:
    from backend.models import Setting
    settings = {s.key: s.value for s in db.query(Setting).all()}
    return {
        "shipping_fee": Decimal(settings.get("shipping_fee", "0")),
        "service_fee_rate": Decimal(settings.get("service_fee_rate", "0.016")),
        "packaging_fee": Decimal(settings.get("packaging_fee", "1.5")),
        "packaging_fee_bundle": Decimal(settings.get("packaging_fee_bundle", "2.0")),
    }


def _fill_order_defaults(data: OrderCreate, db: Session):
    """Auto-fill shipping, service fee, packaging fee from global settings."""
    s = _get_settings(db)

    if data.shipping_fee is None:
        data.shipping_fee = s["shipping_fee"]

    if data.service_fee_rate is None:
        data.service_fee_rate = s["service_fee_rate"]

    if data.service_fee is None:
        data.service_fee = (data.actual_amount * data.service_fee_rate).quantize(Decimal("0.01"))

    if data.packaging_fee is None:
        # Check if any item is a bundle to decide packaging fee
        is_bundle = False
        for item in data.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product and product.category == "bundle":
                is_bundle = True
                break
        data.packaging_fee = s["packaging_fee_bundle"] if is_bundle else s["packaging_fee"]


# ============ Order CRUD ============


@router.get("", response_model=list[OrderListResponse])
def list_orders(
    status: str | None = None,
    source: str | None = None,
    buyer_id: int | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(Order)
    if status:
        q = q.filter(Order.status == status)
    if source:
        q = q.filter(Order.source == source)
    if buyer_id:
        q = q.filter(Order.buyer_id == buyer_id)
    orders = q.order_by(Order.order_time.desc(), Order.id.desc()).offset(offset).limit(limit).all()
    for o in orders:
        o.buyer_nickname = o.buyer.nickname if o.buyer else None
    return orders


@router.post("", response_model=OrderResponse, status_code=201)
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    # Auto-fill from settings
    _fill_order_defaults(data, db)

    # Upsert buyer
    buyer_id = _upsert_buyer(db, data.buyer_nickname, data.buyer_province)

    order_no = _generate_order_no(db)
    order = Order(
        order_no=order_no,
        xianyu_order_id=data.xianyu_order_id,
        buyer_id=buyer_id,
        status=data.status,
        order_time=data.order_time or datetime.utcnow(),
        total_amount=data.total_amount,
        discount=data.discount,
        actual_amount=data.actual_amount,
        shipping_fee=data.shipping_fee,
        packaging_fee=data.packaging_fee,
        service_fee=data.service_fee,
        service_fee_rate=data.service_fee_rate,
        province=data.province,
        notes=data.notes,
        source=data.source,
    )
    db.add(order)
    db.flush()

    # Create order items with material cost snapshot
    for item_data in data.items:
        product = db.query(Product).filter(Product.id == item_data.product_id).first()
        oi = OrderItem(
            order_id=order.id,
            product_id=item_data.product_id,
            product_name=item_data.product_name or (product.name if product else None),
            quantity=item_data.quantity,
            unit_price=item_data.unit_price if item_data.unit_price > 0 else (product.price_single if product else Decimal("0")),
            material_cost=item_data.material_cost if item_data.material_cost > 0 else (product.material_cost if product else Decimal("0")),
        )
        db.add(oi)

    db.commit()
    db.refresh(order)

    if buyer_id:
        _sync_buyer_stats(db, buyer_id)

    return order


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "订单不存在")
    return order


@router.put("/{order_id}", response_model=OrderResponse)
def update_order(order_id: int, data: OrderUpdate, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "订单不存在")

    update_data = data.model_dump(exclude_unset=True)
    items_data = update_data.pop("items", None)

    for key, value in update_data.items():
        setattr(order, key, value)

    # Set completed_time when entering a terminal status
    if order.status in TERMINAL_STATUSES and not order.completed_time:
        order.completed_time = datetime.now(timezone.utc).replace(tzinfo=None)
    elif order.status not in TERMINAL_STATUSES:
        order.completed_time = None

    if items_data is not None:
        # Replace all order items
        db.query(OrderItem).filter(OrderItem.order_id == order.id).delete()
        for item_data in items_data:
            product = db.query(Product).filter(Product.id == item_data["product_id"]).first()
            oi = OrderItem(
                order_id=order.id,
                product_id=item_data["product_id"],
                product_name=item_data.get("product_name") or (product.name if product else None),
                quantity=item_data.get("quantity", 1),
                unit_price=item_data.get("unit_price", Decimal("0")),
                material_cost=item_data.get("material_cost", Decimal("0")),
            )
            db.add(oi)

    db.commit()
    db.refresh(order)

    if order.buyer_id:
        _sync_buyer_stats(db, order.buyer_id)

    return order


@router.delete("/{order_id}", response_model=MessageResponse)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "订单不存在")
    order.status = "已取消"
    order.completed_time = datetime.now(timezone.utc).replace(tzinfo=None)
    buyer_id = order.buyer_id
    db.commit()

    if buyer_id:
        _sync_buyer_stats(db, buyer_id)

    return MessageResponse(message=f"订单 '{order.order_no}' 已取消")


# ============ Parse Endpoint ============


@router.post("/parse", response_model=ParseResponse)
def parse_order(data: ParseRequest, db: Session = Depends(get_db)):
    """Parse pasted 闲鱼 order text and match products."""
    raw_orders = parse_order_text(data.text)
    matched = match_products(db, raw_orders)

    results = []
    errors = []
    for mo in matched:
        try:
            po = ParsedOrder(**mo)
            results.append(po)
        except Exception as e:
            errors.append(f"解析失败: {e}")

    return ParseResponse(orders=results, errors=errors)
