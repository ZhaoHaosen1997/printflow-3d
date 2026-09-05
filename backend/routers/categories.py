from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.crud_utils import apply_update, ensure_unique, get_or_404
from backend.database import get_db
from backend.models import Category
from backend.schemas import CategoryCreate, CategoryUpdate, CategoryResponse, MessageResponse
from backend.services.logger_service import log_business

router = APIRouter(prefix="/categories", tags=["categories"])

LABEL = "分类"


@router.get("", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.sort_order, Category.id).all()


@router.post("", response_model=CategoryResponse, status_code=201)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    ensure_unique(db, Category, {"slug": data.slug, "name": data.name}, LABEL)
    category = Category(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    log_business("分类创建", category.name)
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, data: CategoryUpdate, db: Session = Depends(get_db)):
    category = get_or_404(db, Category, category_id, "分类不存在")
    update_data = data.model_dump(exclude_unset=True)
    ensure_unique(
        db, Category,
        {"slug": update_data.get("slug"), "name": update_data.get("name")},
        LABEL, exclude_id=category.id,
    )
    apply_update(category, update_data)
    db.commit()
    db.refresh(category)
    log_business("分类更新", category.name)
    return category


@router.delete("/{category_id}", response_model=MessageResponse)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = get_or_404(db, Category, category_id, "分类不存在")
    category.status = "archived"
    db.commit()
    log_business("分类归档", category.name)
    return MessageResponse(message=f"分类 '{category.name}' 已归档")
