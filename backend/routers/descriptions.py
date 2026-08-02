from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services import description_service

router = APIRouter(prefix="/descriptions", tags=["descriptions"])


@router.get("/bundle/{product_id}")
def generate_bundle_description(product_id: int, db: Session = Depends(get_db)):
    try:
        text = description_service.generate_bundle_description(db, product_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"text": text}
