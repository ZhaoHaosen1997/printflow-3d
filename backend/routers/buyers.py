from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Buyer, Order
from backend.schemas import (
    BuyerUpdate, BuyerResponse, BuyerDetailResponse,
    BuyerOrderSummary, PaginatedBuyersResponse,
)
from backend.services.logger_service import log_business

router = APIRouter(prefix="/buyers", tags=["buyers"])


@router.get("", response_model=PaginatedBuyersResponse)
def list_buyers(
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Buyer)
    if search:
        q = q.filter(Buyer.nickname.ilike(f"%{search}%"))
    total = q.count()
    items = (
        q.order_by(Buyer.last_order_time.desc().nullslast(), Buyer.nickname)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": items, "total": total}


@router.get("/{buyer_id}", response_model=BuyerDetailResponse)
def get_buyer(buyer_id: int, db: Session = Depends(get_db)):
    buyer = db.query(Buyer).filter(Buyer.id == buyer_id).first()
    if not buyer:
        raise HTTPException(404, "买家不存在")

    orders = (
        db.query(Order)
        .filter(Order.buyer_id == buyer_id)
        .order_by(Order.created_at.desc())
        .limit(50)
        .all()
    )

    result = {
        "id": buyer.id,
        "nickname": buyer.nickname,
        "province": buyer.province,
        "first_order_time": buyer.first_order_time,
        "last_order_time": buyer.last_order_time,
        "total_orders": buyer.total_orders,
        "total_amount": buyer.total_amount,
        "tags": buyer.tags,
        "notes": buyer.notes,
        "created_at": buyer.created_at,
        "updated_at": buyer.updated_at,
        "recent_orders": [
            {
                "id": o.id,
                "order_no": o.order_no,
                "status": o.status,
                "order_time": o.order_time,
                "actual_amount": o.actual_amount,
            }
            for o in orders
        ],
    }
    return result


@router.put("/{buyer_id}", response_model=BuyerResponse)
def update_buyer(buyer_id: int, data: BuyerUpdate, db: Session = Depends(get_db)):
    buyer = db.query(Buyer).filter(Buyer.id == buyer_id).first()
    if not buyer:
        raise HTTPException(404, "买家不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(buyer, key, value)

    db.commit()
    db.refresh(buyer)
    log_business("买家信息更新", buyer.nickname, tags=str(buyer.tags))
    return buyer
