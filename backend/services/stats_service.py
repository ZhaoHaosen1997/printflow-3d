"""销售/统计共享聚合：dashboard 与 sales 共用的 SQL 聚合与利润公式。

利润公式历史上曾出现三处实现不一致的事故（code-review H3），
统一由 calc_profit 提供。
"""

from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models import Order, OrderItem


def completed_aggregate(db: Session, *filters):
    """完成态订单的头部聚合：单数/收入/四项费用/折扣（SQL 端 sum）。"""
    return db.query(
        func.count(Order.id).label("cnt"),
        func.coalesce(func.sum(Order.actual_amount), 0).label("revenue"),
        func.coalesce(func.sum(Order.shipping_fee), 0).label("shipping"),
        func.coalesce(func.sum(Order.packaging_fee), 0).label("packaging"),
        func.coalesce(func.sum(Order.service_fee), 0).label("service"),
        func.coalesce(func.sum(Order.charity_fee), 0).label("charity"),
        func.coalesce(func.sum(Order.discount), 0).label("discount"),
    ).filter(Order.status == "completed", *filters).one()


def completed_material_cost(db: Session, *filters) -> Decimal:
    """完成态订单的材料成本合计（明细成本 × 数量，SQL 端 sum）。"""
    return db.query(
        func.coalesce(func.sum(OrderItem.material_cost * OrderItem.quantity), 0)
    ).join(Order, OrderItem.order_id == Order.id).filter(
        Order.status == "completed", *filters
    ).scalar()


def fees_total(shipping, packaging, service, charity) -> Decimal:
    """四项费用合计：运费 + 包装费 + 服务费 + 公益支出。"""
    return (
        Decimal(str(shipping)) + Decimal(str(packaging))
        + Decimal(str(service)) + Decimal(str(charity))
    )


def calc_profit(revenue, material_cost, *fees) -> Decimal:
    """利润公式的唯一来源：收入 − 材料成本 − 各项费用。"""
    return Decimal(str(revenue)) - Decimal(str(material_cost)) - sum(
        Decimal(str(f)) for f in fees
    )
