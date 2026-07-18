from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import get_db
from backend.models import Order, OrderItem, Inventory, Product, PrintTask, Buyer
from backend.schemas import DashboardSummary, RecentOrder, PrintTaskStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    pending_ship_count = db.query(func.count(Order.id)).filter(
        Order.status == "pending_ship"
    ).scalar() or 0

    low_stock_count = (
        db.query(func.count(Inventory.id))
        .join(Product, Inventory.product_id == Product.id)
        .filter(
            Inventory.quantity <= Inventory.warning_threshold,
            Product.category != "bundle",
            Product.status == "active",
        )
        .scalar()
    ) or 0

    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)

    order_agg = db.query(
        func.coalesce(func.sum(Order.actual_amount), 0).label("revenue"),
        func.coalesce(func.sum(Order.shipping_fee), 0).label("shipping"),
        func.coalesce(func.sum(Order.packaging_fee), 0).label("packaging"),
        func.coalesce(func.sum(Order.service_fee), 0).label("service"),
        func.coalesce(func.sum(Order.charity_fee), 0).label("charity"),
    ).filter(
        Order.status == "completed",
        Order.completed_time >= month_start,
    ).one()

    monthly_revenue = Decimal(str(order_agg.revenue))
    monthly_fees = (
        Decimal(str(order_agg.shipping))
        + Decimal(str(order_agg.packaging))
        + Decimal(str(order_agg.service))
        + Decimal(str(order_agg.charity))
    )

    material_cost_row = db.query(
        func.coalesce(func.sum(OrderItem.material_cost * OrderItem.quantity), 0)
    ).join(Order, OrderItem.order_id == Order.id).filter(
        Order.status == "completed",
        Order.completed_time >= month_start,
    ).scalar()
    monthly_cost = Decimal(str(material_cost_row)) + monthly_fees
    monthly_profit = monthly_revenue - monthly_cost

    task_stats_rows = db.query(
        PrintTask.status,
        func.count(PrintTask.id),
    ).group_by(PrintTask.status).all()

    task_stats = PrintTaskStats()
    printing_count = 0
    pending_print_count = 0
    for status, cnt in task_stats_rows:
        if status == "pending":
            task_stats.pending = cnt
            pending_print_count = cnt
        elif status == "printing":
            task_stats.printing = cnt
            printing_count = cnt
        elif status == "done":
            task_stats.done = cnt
        elif status == "failed":
            task_stats.failed = cnt

    recent_orders_q = (
        db.query(Order, Buyer.nickname.label("buyer_nickname"))
        .outerjoin(Buyer, Order.buyer_id == Buyer.id)
        .filter(Order.status != "archived")
        .order_by(Order.order_time.desc())
        .limit(5)
        .all()
    )

    recent_orders = []
    if recent_orders_q:
        order_ids = [o.id for o, _ in recent_orders_q]
        items_by_order: dict[int, list] = {}
        for item in db.query(OrderItem).filter(OrderItem.order_id.in_(order_ids)).all():
            items_by_order.setdefault(item.order_id, []).append(item)

        for o, bname in recent_orders_q:
            items = items_by_order.get(o.id, [])
            parts = []
            for it in items[:3]:
                name = it.product_name or f"商品#{it.product_id}"
                qty = it.quantity or 1
                parts.append(f"{name}x{qty}" if qty > 1 else name)
            summary = ", ".join(parts)
            if len(items) > 3:
                summary += f" 等{len(items)}件"

            recent_orders.append(RecentOrder(
                id=o.id,
                order_no=o.order_no,
                buyer_nickname=bname,
                status=o.status,
                actual_amount=o.actual_amount or Decimal("0"),
                order_time=o.order_time,
                item_summary=summary,
            ))

    return DashboardSummary(
        pending_ship_count=pending_ship_count,
        low_stock_count=low_stock_count,
        monthly_revenue=monthly_revenue,
        monthly_cost=monthly_cost,
        monthly_profit=monthly_profit,
        printing_count=printing_count,
        pending_print_count=pending_print_count,
        recent_orders=recent_orders,
        print_task_stats=task_stats,
    )
