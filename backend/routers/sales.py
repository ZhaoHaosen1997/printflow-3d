from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from backend.database import get_db
from backend.models import Order, OrderItem, Product
from backend.services.stats_service import calc_profit, completed_aggregate, completed_material_cost
from backend.schemas import SalesOverviewResponse, MonthlySalesItem, ProductSalesItem

router = APIRouter(prefix="/sales", tags=["sales"])


def _completed_filter(query, date_from: str | None = None, date_to: str | None = None):
    q = query.filter(Order.status == "completed")
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
    filters = []
    if date_from:
        filters.append(Order.completed_time >= date_from)
    if date_to:
        filters.append(Order.completed_time <= date_to + " 23:59:59")

    order_agg = completed_aggregate(db, *filters)

    total_orders = order_agg.cnt
    total_revenue = Decimal(str(order_agg.revenue))
    total_shipping_fee = Decimal(str(order_agg.shipping))
    total_packaging_fee = Decimal(str(order_agg.packaging))
    total_service_fee = Decimal(str(order_agg.service))
    total_charity_fee = Decimal(str(order_agg.charity))
    total_discount = Decimal(str(order_agg.discount))

    total_material_cost = Decimal(str(completed_material_cost(db, *filters)))

    total_profit = calc_profit(
        total_revenue, total_material_cost,
        total_shipping_fee, total_packaging_fee, total_service_fee, total_charity_fee,
    )

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
    monthly_orders = (
        db.query(
            extract("month", Order.completed_time).label("month"),
            func.count(Order.id).label("orders"),
            func.coalesce(func.sum(Order.actual_amount), 0).label("revenue"),
            func.coalesce(func.sum(Order.shipping_fee), 0).label("shipping"),
            func.coalesce(func.sum(Order.packaging_fee), 0).label("packaging"),
            func.coalesce(func.sum(Order.service_fee), 0).label("service"),
            func.coalesce(func.sum(Order.charity_fee), 0).label("charity"),
        )
        .filter(Order.status == "completed", extract("year", Order.completed_time) == year)
        .group_by(extract("month", Order.completed_time))
        .all()
    )
    order_map = {int(row.month): row for row in monthly_orders}

    monthly_cost = (
        db.query(
            extract("month", Order.completed_time).label("month"),
            func.coalesce(func.sum(OrderItem.material_cost * OrderItem.quantity), 0).label("material_cost"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .filter(Order.status == "completed", extract("year", Order.completed_time) == year)
        .group_by(extract("month", Order.completed_time))
        .all()
    )
    cost_map = {int(row.month): Decimal(str(row.material_cost)) for row in monthly_cost}

    result = []
    for m in range(1, 13):
        row = order_map.get(m)
        if row:
            revenue = Decimal(str(row.revenue))
            material_cost = cost_map.get(m, Decimal("0"))
            profit = calc_profit(
                revenue, material_cost,
                row.shipping, row.packaging, row.service, row.charity,
            )
            result.append(MonthlySalesItem(
                month=m,
                orders=row.orders,
                revenue=revenue,
                profit=profit,
            ))
        else:
            result.append(MonthlySalesItem(month=m))
    return result


@router.get("/by-product", response_model=list[ProductSalesItem])
def sales_by_product(
    date_from: str | None = None,
    date_to: str | None = None,
    sort_by: str = "profit",
    db: Session = Depends(get_db),
):
    rows = _completed_filter(
        db.query(
            OrderItem.product_id,
            OrderItem.product_name,
            OrderItem.quantity,
            OrderItem.unit_price,
            OrderItem.material_cost,
            Order.id.label("order_id"),
            Order.shipping_fee,
            Order.packaging_fee,
            Order.service_fee,
            Order.charity_fee,
        ).join(Order, OrderItem.order_id == Order.id),
        date_from, date_to,
    ).all()

    all_pids = {r.product_id for r in rows}
    product_map = {
        p.id: p
        for p in db.query(Product).filter(Product.id.in_(all_pids)).all()
    } if all_pids else {}

    order_fees: dict[int, dict] = {}
    for r in rows:
        oid = r.order_id
        if oid not in order_fees:
            order_fees[oid] = {
                "fees": (r.shipping_fee or Decimal("0")) + (r.packaging_fee or Decimal("0"))
                        + (r.service_fee or Decimal("0")) + (r.charity_fee or Decimal("0")),
                "items": [],
            }
        item_revenue = (r.unit_price or Decimal("0")) * (r.quantity or 1)
        order_fees[oid]["items"].append({
            "product_id": r.product_id,
            "item_revenue": item_revenue,
        })

    for oid, of in order_fees.items():
        total_item_revenue = sum(it["item_revenue"] for it in of["items"]) or Decimal("1")
        for it in of["items"]:
            it["fee_share"] = (of["fees"] * it["item_revenue"] / total_item_revenue).quantize(Decimal("0.01"))

    product_stats: dict[int, dict] = {}
    for r in rows:
        pid = r.product_id
        item_revenue = (r.unit_price or Decimal("0")) * (r.quantity or 1)
        item_material_cost = (r.material_cost or Decimal("0")) * (r.quantity or 1)

        fee_share = Decimal("0")
        for it in order_fees.get(r.order_id, {}).get("items", []):
            if it["product_id"] == pid:
                fee_share = it.get("fee_share", Decimal("0"))
                break

        if pid not in product_stats:
            product = product_map.get(pid)
            product_stats[pid] = {
                "product_id": pid,
                "product_name": product.name if product else (r.product_name or f"商品#{pid}"),
                "category": (product.category if product else None) or "other",
                "quantity": 0,
                "revenue": Decimal("0"),
                "material_cost": Decimal("0"),
                "fees": Decimal("0"),
            }
        product_stats[pid]["quantity"] += r.quantity or 1
        product_stats[pid]["revenue"] += item_revenue
        product_stats[pid]["material_cost"] += item_material_cost
        product_stats[pid]["fees"] += fee_share

    result = []
    for ps in product_stats.values():
        ps["profit"] = calc_profit(ps["revenue"], ps["material_cost"], ps.pop("fees"))
        result.append(ProductSalesItem(**ps))

    reverse = sort_by not in ("profit", "quantity", "revenue")
    result.sort(key=lambda x: getattr(x, sort_by, x.profit), reverse=True)
    return result
