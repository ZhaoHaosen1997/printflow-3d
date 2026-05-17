from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from backend.database import get_db
from backend.models import Order, OrderItem, Product
from backend.schemas import SalesOverviewResponse, MonthlySalesItem, ProductSalesItem

router = APIRouter(prefix="/sales", tags=["sales"])


def _completed_orders(db: Session, date_from: str | None = None, date_to: str | None = None):
    q = db.query(Order).filter(Order.status == "completed")
    if date_from:
        q = q.filter(Order.completed_time >= date_from)
    if date_to:
        q = q.filter(Order.completed_time <= date_to + " 23:59:59")
    return q


@router.get("/overview", response_model=SalesOverviewResponse)
def sales_overview(
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_db),
):
    orders = _completed_orders(db, date_from, date_to).all()

    total_orders = len(orders)
    total_revenue = Decimal("0")
    total_material_cost = Decimal("0")
    total_shipping_fee = Decimal("0")
    total_packaging_fee = Decimal("0")
    total_service_fee = Decimal("0")
    total_charity_fee = Decimal("0")
    total_discount = Decimal("0")

    for o in orders:
        total_revenue += o.actual_amount or Decimal("0")
        total_shipping_fee += o.shipping_fee or Decimal("0")
        total_packaging_fee += o.packaging_fee or Decimal("0")
        total_service_fee += o.service_fee or Decimal("0")
        total_charity_fee += o.charity_fee or Decimal("0")
        total_discount += o.discount or Decimal("0")
        for item in o.items:
            total_material_cost += (item.material_cost or Decimal("0")) * (item.quantity or 1)

    total_profit = total_revenue - total_material_cost - total_shipping_fee - total_packaging_fee - total_service_fee - total_charity_fee

    return SalesOverviewResponse(
        total_orders=total_orders,
        total_revenue=total_revenue,
        total_profit=total_profit,
        total_material_cost=total_material_cost,
        total_shipping_fee=total_shipping_fee,
        total_packaging_fee=total_packaging_fee,
        total_service_fee=total_service_fee,
        total_charity_fee=total_charity_fee,
        total_discount=total_discount,
        avg_order_value=(total_revenue / total_orders).quantize(Decimal("0.01")) if total_orders else Decimal("0"),
        avg_profit_per_order=(total_profit / total_orders).quantize(Decimal("0.01")) if total_orders else Decimal("0"),
    )


@router.get("/monthly", response_model=list[MonthlySalesItem])
def sales_monthly(
    year: int = Query(ge=2020, le=2100),
    db: Session = Depends(get_db),
):
    orders = (
        db.query(Order)
        .filter(
            Order.status == "completed",
            extract("year", Order.completed_time) == year,
        )
        .all()
    )

    monthly = {m: {"orders": 0, "revenue": Decimal("0"), "material_cost": Decimal("0"),
                   "shipping_fee": Decimal("0"), "packaging_fee": Decimal("0"),
                   "service_fee": Decimal("0"), "charity_fee": Decimal("0")} for m in range(1, 13)}

    for o in orders:
        m = o.completed_time.month
        monthly[m]["orders"] += 1
        monthly[m]["revenue"] += o.actual_amount or Decimal("0")
        monthly[m]["shipping_fee"] += o.shipping_fee or Decimal("0")
        monthly[m]["packaging_fee"] += o.packaging_fee or Decimal("0")
        monthly[m]["service_fee"] += o.service_fee or Decimal("0")
        monthly[m]["charity_fee"] += o.charity_fee or Decimal("0")
        for item in o.items:
            monthly[m]["material_cost"] += (item.material_cost or Decimal("0")) * (item.quantity or 1)

    result = []
    for m in range(1, 13):
        d = monthly[m]
        profit = (d["revenue"] - d["material_cost"] - d["shipping_fee"]
                  - d["packaging_fee"] - d["service_fee"] - d["charity_fee"])
        result.append(MonthlySalesItem(
            month=m,
            orders=d["orders"],
            revenue=d["revenue"],
            profit=profit,
        ))
    return result


@router.get("/by-product", response_model=list[ProductSalesItem])
def sales_by_product(
    date_from: str | None = None,
    date_to: str | None = None,
    sort_by: str = "profit",
    db: Session = Depends(get_db),
):
    orders = _completed_orders(db, date_from, date_to).all()

    # Batch-load all referenced products
    all_pids = {item.product_id for o in orders for item in o.items}
    product_map = {
        p.id: p
        for p in db.query(Product).filter(Product.id.in_(all_pids)).all()
    } if all_pids else {}

    product_stats: dict[int, dict] = {}

    for o in orders:
        # Per-order fees
        o_shipping = o.shipping_fee or Decimal("0")
        o_packaging = o.packaging_fee or Decimal("0")
        o_service = o.service_fee or Decimal("0")
        o_charity = o.charity_fee or Decimal("0")
        o_fees = o_shipping + o_packaging + o_service + o_charity
        # Total item revenue for this order (for fee allocation)
        o_item_revenue = sum(
            (item.unit_price or Decimal("0")) * (item.quantity or 1)
            for item in o.items
        ) or Decimal("1")

        for item in o.items:
            pid = item.product_id
            item_revenue = (item.unit_price or Decimal("0")) * (item.quantity or 1)
            if pid not in product_stats:
                product = product_map.get(pid)
                product_stats[pid] = {
                    "product_id": pid,
                    "product_name": product.name if product else (item.product_name or f"商品#{pid}"),
                    "category": product.category if product else "other",
                    "quantity": 0,
                    "revenue": Decimal("0"),
                    "material_cost": Decimal("0"),
                    "fees": Decimal("0"),
                }
            product_stats[pid]["quantity"] += item.quantity or 1
            product_stats[pid]["revenue"] += item_revenue
            product_stats[pid]["material_cost"] += (item.material_cost or Decimal("0")) * (item.quantity or 1)
            # Allocate order fees proportionally by item revenue share
            product_stats[pid]["fees"] += (o_fees * item_revenue / o_item_revenue).quantize(Decimal("0.01"))

    result = []
    for ps in product_stats.values():
        ps["profit"] = ps["revenue"] - ps["material_cost"] - ps.pop("fees")
        result.append(ProductSalesItem(**ps))

    reverse = sort_by not in ("profit", "quantity", "revenue")
    result.sort(key=lambda x: getattr(x, sort_by, x.profit), reverse=True)
    return result


