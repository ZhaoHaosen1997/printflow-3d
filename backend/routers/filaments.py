from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Filament
from backend.schemas import FilamentCreate, FilamentUpdate, FilamentResponse, MessageResponse
from backend.services.product_service import update_filament_price
from backend.services.logger_service import log_business

router = APIRouter(prefix="/filaments", tags=["filaments"])


@router.get("", response_model=list[FilamentResponse])
def list_filaments(status: str = "active", db: Session = Depends(get_db)):
    q = db.query(Filament)
    if status != "all":
        q = q.filter(Filament.status == status)
    return q.order_by(Filament.brand, Filament.material).all()


@router.post("", response_model=FilamentResponse, status_code=201)
def create_filament(data: FilamentCreate, db: Session = Depends(get_db)):
    filament = Filament(**data.model_dump())
    db.add(filament)
    db.commit()
    db.refresh(filament)
    log_business("耗材创建", f"{filament.brand} {filament.material}",
                 price=str(filament.price_per_kg))
    return filament


@router.get("/{filament_id}", response_model=FilamentResponse)
def get_filament(filament_id: int, db: Session = Depends(get_db)):
    filament = db.query(Filament).filter(Filament.id == filament_id).first()
    if not filament:
        raise HTTPException(404, "耗材不存在")
    return filament


@router.put("/{filament_id}", response_model=FilamentResponse)
def update_filament(filament_id: int, data: FilamentUpdate, db: Session = Depends(get_db)):
    filament = db.query(Filament).filter(Filament.id == filament_id).first()
    if not filament:
        raise HTTPException(404, "耗材不存在")

    old_price = filament.price_per_kg
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(filament, key, value)

    db.commit()
    db.refresh(filament)

    if "price_per_kg" in update_data and update_data["price_per_kg"] != old_price:
        update_filament_price(db, filament_id, update_data["price_per_kg"])

    return filament


@router.delete("/{filament_id}", response_model=MessageResponse)
def delete_filament(filament_id: int, db: Session = Depends(get_db)):
    filament = db.query(Filament).filter(Filament.id == filament_id).first()
    if not filament:
        raise HTTPException(404, "耗材不存在")
    filament.status = "archived"
    db.commit()
    log_business("耗材归档", f"{filament.brand} {filament.material}")
    return MessageResponse(message=f"耗材 '{filament.brand} {filament.material}' 已归档")
