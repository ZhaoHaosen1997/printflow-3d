"""Shared inventory helper functions used across routers."""
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
