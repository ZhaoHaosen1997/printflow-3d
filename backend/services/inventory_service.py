"""Shared inventory helper functions used across routers."""
from fastapi import HTTPException
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


def deduct_inventory(db: Session, product_id: int, qty: int) -> None:
    """原子扣减库存：单条 UPDATE 带余量条件，并发下不会丢失更新。

    库存不足时抛 400（由事务回滚保证不产生半扣减），不再静默截断为 0。
    """
    if qty <= 0:
        return
    updated = (
        db.query(Inventory)
        .filter(Inventory.product_id == product_id, Inventory.quantity >= qty)
        .update({Inventory.quantity: Inventory.quantity - qty}, synchronize_session=False)
    )
    if updated:
        return
    # 无库存记录视为 0：补建记录后走统一报错（失败路径才查询商品名，正常路径零开销）
    ensure_inventory(db, product_id)
    from backend.models import Product
    product = db.query(Product).filter(Product.id == product_id).first()
    name = product.name if product else f"商品#{product_id}"
    inv = db.query(Inventory).filter(Inventory.product_id == product_id).first()
    raise HTTPException(400, f"「{name}」库存不足（当前 {inv.quantity if inv else 0}，需 {qty}）")


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
