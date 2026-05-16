from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.database import get_db
from backend.models import Product, Filament, Order, PrintRecipe, OrderItem
from backend.services.logger_service import log_business

router = APIRouter(prefix="/admin", tags=["admin"])


class PermanentDeleteRequest(BaseModel):
    type: str  # products | filaments | orders
    ids: list[int]


@router.get("/archived")
def list_archived(db: Session = Depends(get_db)):
    """Return all archived data grouped by type."""
    products = (
        db.query(Product)
        .filter(Product.status == "archived")
        .order_by(Product.name)
        .all()
    )
    filaments = (
        db.query(Filament)
        .filter(Filament.status == "archived")
        .order_by(Filament.brand, Filament.material)
        .all()
    )
    orders = (
        db.query(Order)
        .filter(Order.status == "archived")
        .order_by(Order.created_at.desc())
        .all()
    )

    return {
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "price_single": str(p.price_single),
                "archived_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in products
        ],
        "filaments": [
            {
                "id": f.id,
                "display_name": f"{f.brand} {f.material}",
                "brand": f.brand,
                "material": f.material,
                "price_per_kg": str(f.price_per_kg),
                "archived_at": f.updated_at.isoformat() if f.updated_at else None,
            }
            for f in filaments
        ],
        "orders": [
            {
                "id": o.id,
                "order_no": o.order_no,
                "status": o.status,
                "actual_amount": str(o.actual_amount),
                "buyer_nickname": o.buyer.nickname if o.buyer else None,
                "order_time": o.order_time.isoformat() if o.order_time else None,
                "archived_at": o.updated_at.isoformat() if o.updated_at else None,
            }
            for o in orders
        ],
    }


@router.delete("/archived")
def permanent_delete(data: PermanentDeleteRequest, db: Session = Depends(get_db)):
    """Permanently delete archived records by type and ids."""
    if data.type not in ("products", "filaments", "orders"):
        raise HTTPException(400, "不支持的类型，可选: products, filaments, orders")

    deleted = 0
    if data.type == "products":
        products = db.query(Product).filter(
            Product.id.in_(data.ids),
            Product.status == "archived",
        ).all()
        for p in products:
            # Also delete associated recipes
            db.query(PrintRecipe).filter(PrintRecipe.product_id == p.id).delete()
            log_business("永久删除商品", p.name)
        deleted = len(products)
        for p in products:
            db.delete(p)

    elif data.type == "filaments":
        filaments = db.query(Filament).filter(
            Filament.id.in_(data.ids),
            Filament.status == "archived",
        ).all()
        for f in filaments:
            log_business("永久删除耗材", f"{f.brand} {f.material}")
        deleted = len(filaments)
        for f in filaments:
            db.delete(f)

    elif data.type == "orders":
        orders = db.query(Order).filter(
            Order.id.in_(data.ids),
            Order.status == "archived",
        ).all()
        for o in orders:
            # Delete associated order items first
            db.query(OrderItem).filter(OrderItem.order_id == o.id).delete()
            log_business("永久删除订单", o.order_no)
        deleted = len(orders)
        for o in orders:
            db.delete(o)

    db.commit()
    return {"deleted": deleted, "message": f"已永久删除 {deleted} 条{data.type}记录"}
