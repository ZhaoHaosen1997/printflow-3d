from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Category
from backend.schemas import CategoryCreate, CategoryUpdate, CategoryResponse, MessageResponse
from backend.services.logger_service import log_business

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.sort_order, Category.id).all()


@router.post("", response_model=CategoryResponse, status_code=201)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    if db.query(Category).filter(Category.slug == data.slug).first():
        raise HTTPException(400, f"分类slug '{data.slug}' 已存在")
    if db.query(Category).filter(Category.name == data.name).first():
        raise HTTPException(400, f"分类名 '{data.name}' 已存在")
    category = Category(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    log_business("分类创建", category.name)
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, data: CategoryUpdate, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(404, "分类不存在")
    update_data = data.model_dump(exclude_unset=True)
    if "slug" in update_data and update_data["slug"] != category.slug:
        if db.query(Category).filter(Category.slug == update_data["slug"]).first():
            raise HTTPException(400, f"分类slug '{update_data['slug']}' 已存在")
    if "name" in update_data and update_data["name"] != category.name:
        if db.query(Category).filter(Category.name == update_data["name"]).first():
            raise HTTPException(400, f"分类名 '{update_data['name']}' 已存在")
    for key, value in update_data.items():
        setattr(category, key, value)
    db.commit()
    db.refresh(category)
    log_business("分类更新", category.name)
    return category


@router.delete("/{category_id}", response_model=MessageResponse)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(404, "分类不存在")
    category.status = "archived"
    db.commit()
    log_business("分类归档", category.name)
    return MessageResponse(message=f"分类 '{category.name}' 已归档")
