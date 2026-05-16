import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Color
from backend.schemas import ColorCreate, ColorUpdate, ColorResponse, MessageResponse

router = APIRouter(prefix="/colors", tags=["colors"])

# Chinese → English color name mapping
CN_MAP = {
    "黑色": "black", "白色": "white", "灰色": "gray", "银色": "silver",
    "金色": "gold", "红色": "red", "蓝色": "blue", "紫色": "purple",
    "黄色": "yellow", "青铜色": "bronze", "橙色": "orange",
    "亮金色": "brightgold", "深紫色": "deeppurple",
    "绿色": "green", "深绿色": "darkgreen",
    "黑金": "blackgold", "黑银": "blacksilver",
    "白红蓝": "whiteredblue", "白红": "whitered",
    "紫白": "purplewhite",
    "亮金-金-银": "brightgold-gold-silver",
    "金-银-青铜": "gold-silver-bronze",
}


def _translate_name(name: str) -> str:
    """Translate Chinese color name to English. Returns lowercase ASCII slug."""
    if name in CN_MAP:
        return CN_MAP[name]
    # Fallback: strip Chinese chars, keep ASCII letters/digits/hyphens
    slug = re.sub(r"[^\x00-\x7F]+", "", name).strip()
    slug = re.sub(r"[^a-zA-Z0-9\-_]", "", slug).lower()
    if slug:
        return slug
    # Last resort: use a hash-based id
    import hashlib
    h = hashlib.md5(name.encode()).hexdigest()[:8]
    return f"color-{h}"


def _generate_color_id(db: Session, name: str) -> str:
    """Generate unique color_id from Chinese name."""
    base = _translate_name(name)
    cand = base
    n = 2
    while db.query(Color).filter(Color.color_id == cand).first():
        cand = f"{base}{n}"
        n += 1
    return cand


@router.get("", response_model=list[ColorResponse])
def list_colors(db: Session = Depends(get_db)):
    return db.query(Color).order_by(Color.type, Color.name).all()


@router.post("", response_model=ColorResponse, status_code=201)
def create_color(data: ColorCreate, db: Session = Depends(get_db)):
    color_id = _generate_color_id(db, data.name)

    if data.type == "combo":
        if not data.combo_of:
            raise HTTPException(400, "组合色必须填写 combo_of")
        for cid in data.combo_of:
            ref = db.query(Color).filter(Color.color_id == cid, Color.type == "standard").first()
            if not ref:
                raise HTTPException(400, f"引用的标准色 '{cid}' 不存在")

    color = Color(color_id=color_id, **data.model_dump())
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
