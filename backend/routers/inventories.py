from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Inventory, Product
from backend.schemas import (
    InventoryCreate, InventoryUpdate, InventoryListResponse, InventoryResponse,
    MessageResponse,
)
from backend.services.logger_service import log_business
from backend.services.inventory_service import ensure_inventory

router = APIRouter(prefix="/inventories", tags=["inventories"])


@router.get("", response_model=list[InventoryListResponse])
def list_inventories(db: Session = Depends(get_db)):
    """List all active products with their inventory status."""
    products = (
        db.query(Product)
        .filter(Product.status == "active", Product.category != "bundle")
        .order_by(Product.category, Product.name)
        .all()
    )

    result = []
    for p in products:
        inv = ensure_inventory(db, p.id)
        result.append({
            "id": inv.id,
            "product_id": p.id,
            "product_name": p.name,
            "product_category": p.category,
            "quantity": inv.quantity,
            "warning_threshold": inv.warning_threshold,
            "created_at": inv.created_at,
            "updated_at": inv.updated_at,
        })

    db.commit()
    return result


@router.get("/{inventory_id}", response_model=InventoryResponse)
def get_inventory(inventory_id: int, db: Session = Depends(get_db)):
    inv = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if not inv:
        raise HTTPException(404, "库存记录不存在")
    return inv


@router.put("/{inventory_id}", response_model=InventoryResponse)
def update_inventory(inventory_id: int, data: InventoryUpdate, db: Session = Depends(get_db)):
    inv = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if not inv:
        raise HTTPException(404, "库存记录不存在")

    old_qty = inv.quantity
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(inv, key, value)

    db.commit()
    db.refresh(inv)
    if "quantity" in update_data:
        p = db.query(Product).filter(Product.id == inv.product_id).first()
        log_business("库存调整", p.name if p else str(inv.product_id),
                     detail=f"{old_qty}→{inv.quantity}")
    return inv


@router.post("/ensure-all", response_model=MessageResponse)
def ensure_all_inventories(db: Session = Depends(get_db)):
    """Ensure every active product has an inventory record."""
    products = db.query(Product).filter(Product.status == "active", Product.category != "bundle").all()
    created = 0
    for p in products:
        inv = db.query(Inventory).filter(Inventory.product_id == p.id).first()
        if not inv:
            db.add(Inventory(product_id=p.id, quantity=0, warning_threshold=5))
            created += 1
    db.commit()
    return MessageResponse(message=f"已为 {created} 个商品创建库存记录")
