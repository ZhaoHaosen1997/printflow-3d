from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Color
from backend.schemas import ColorCreate, ColorUpdate, ColorResponse, MessageResponse

router = APIRouter(prefix="/colors", tags=["colors"])


@router.get("", response_model=list[ColorResponse])
def list_colors(db: Session = Depends(get_db)):
    return db.query(Color).order_by(Color.type, Color.name).all()


@router.post("", response_model=ColorResponse, status_code=201)
def create_color(data: ColorCreate, db: Session = Depends(get_db)):
    existing = db.query(Color).filter(Color.color_id == data.color_id).first()
    if existing:
        raise HTTPException(400, f"颜色标识符 '{data.color_id}' 已存在")

    if data.type == "combo":
        if not data.combo_of:
            raise HTTPException(400, "组合色必须填写 combo_of")
        for cid in data.combo_of:
            ref = db.query(Color).filter(Color.color_id == cid, Color.type == "standard").first()
            if not ref:
                raise HTTPException(400, f"引用的标准色 '{cid}' 不存在")

    color = Color(**data.model_dump())
    db.add(color)
    db.commit()
    db.refresh(color)
    return color


@router.get("/{color_id}", response_model=ColorResponse)
def get_color(color_id: int, db: Session = Depends(get_db)):
    color = db.query(Color).filter(Color.id == color_id).first()
    if not color:
        raise HTTPException(404, "颜色不存在")
    return color


@router.put("/{color_id}", response_model=ColorResponse)
def update_color(color_id: int, data: ColorUpdate, db: Session = Depends(get_db)):
    color = db.query(Color).filter(Color.id == color_id).first()
    if not color:
        raise HTTPException(404, "颜色不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(color, key, value)

    db.commit()
    db.refresh(color)
    return color


@router.delete("/{color_id}", response_model=MessageResponse)
def delete_color(color_id: int, db: Session = Depends(get_db)):
    color = db.query(Color).filter(Color.id == color_id).first()
    if not color:
        raise HTTPException(404, "颜色不存在")
    db.delete(color)
    db.commit()
    return MessageResponse(message=f"颜色 '{color.name}' 已删除")
