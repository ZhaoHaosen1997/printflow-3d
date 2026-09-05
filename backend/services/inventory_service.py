"""Shared inventory helper functions used across routers."""
from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.models import Inventory


def ensure_inventory(db: Session, product_id: int) -> Inventory:
    """Get or create inventory record for a product."""
    inv = db.query(Inventory).filter(Inventory.product_id == product_id).first()
    if not inv:
        inv = Inventory(product_id=product_id, quantity=0, warning_threshold=5)
        db.add(inv)
        db.flush()
    return inv


def deduct_inventory(db: Session, product_id: int, qty: int) -> bool:
    """原子扣减库存：单条 UPDATE，并发下不会丢失更新。

    v1.21.1 语义：订单不因库存不足而拦截（买家已下单必须记录），
    库存不足时扣至 0 并返回 False 供调用方提示，充足时返回 True。
    """
    if qty <= 0:
        return True
    # 无记录视为 0：先补建再原子截断
    ensure_inventory(db, product_id)
    updated = (
        db.query(Inventory)
        .filter(Inventory.product_id == product_id)
        .update(
            {Inventory.quantity: func.max(0, Inventory.quantity - qty)},
            synchronize_session=False,
        )
    )
    return bool(updated)


def restore_inventory(db: Session, product_id: int, qty: int) -> None:
    """原子回补库存，记录不存在时先补建再加数。"""
    if qty <= 0:
        return
    updated = (
        db.query(Inventory)
        .filter(Inventory.product_id == product_id)
        .update({Inventory.quantity: Inventory.quantity + qty}, synchronize_session=False)
    )
    if not updated:
        ensure_inventory(db, product_id)
        db.query(Inventory).filter(Inventory.product_id == product_id).update(
            {Inventory.quantity: Inventory.quantity + qty}, synchronize_session=False
        )
