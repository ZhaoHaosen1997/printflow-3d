import os
import secrets
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.database import get_db
from backend.models import (
    Product, Filament, Order, PrintRecipe, PrintRecipeFilament,
    PrintTask, OrderItem, Inventory, product_games,
)
from backend.services.logger_service import log_business

# 共享密钥防护：设置 ADMIN_TOKEN 环境变量后，/api/admin/* 要求请求头 X-Admin-Token
# 未设置时不启用（本地开发模式）。密钥用常数时间比较，防时序侧信道。
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")


def _verify_admin_token(x_admin_token: str | None = Header(default=None)):
    if not ADMIN_TOKEN:
        return
    if not x_admin_token or not secrets.compare_digest(x_admin_token, ADMIN_TOKEN):
        raise HTTPException(403, "管理操作需要有效的 X-Admin-Token 请求头")


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(_verify_admin_token)])


class PermanentDeleteRequest(BaseModel):
    type: str  # products | filaments | orders
    ids: list[int]
    confirm: str | None = None  # 必须显式传 "DELETE"，二次确认防误触


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
    if data.confirm != "DELETE":
        raise HTTPException(400, '缺少删除确认：请求体需包含 confirm="DELETE"')

    deleted = 0
    if data.type == "products":
        products = db.query(Product).filter(
            Product.id.in_(data.ids),
            Product.status == "archived",
        ).all()
        pids = [p.id for p in products]

        # 仍被订单明细引用的商品不允许物理删除（外键约束 + 避免破坏历史订单）
        if pids and db.query(OrderItem).filter(OrderItem.product_id.in_(pids)).first():
            raise HTTPException(400, "所选商品仍被订单明细引用，请先永久删除相关订单（先删订单，再删商品）")

        for p in products:
            recipe_ids = [r.id for r in db.query(PrintRecipe).filter(PrintRecipe.product_id == p.id).all()]
            if recipe_ids:
                # bulk delete 不触发 ORM 级联，子表必须显式先删，避免孤儿行
                db.query(PrintRecipeFilament).filter(PrintRecipeFilament.recipe_id.in_(recipe_ids)).delete(synchronize_session=False)
                db.query(PrintTask).filter(PrintTask.recipe_id.in_(recipe_ids)).delete(synchronize_session=False)
            db.query(PrintRecipe).filter(PrintRecipe.product_id == p.id).delete(synchronize_session=False)
            db.query(Inventory).filter(Inventory.product_id == p.id).delete(synchronize_session=False)
            db.execute(
                product_games.delete().where(product_games.c.product_id == p.id)
            )
            log_business("永久删除商品", p.name)
        deleted = len(products)
        for p in products:
            db.delete(p)

    elif data.type == "filaments":
        filaments = db.query(Filament).filter(
            Filament.id.in_(data.ids),
            Filament.status == "archived",
        ).all()
        fids = [f.id for f in filaments]
        # 仍被配方引用的耗材不允许物理删除，否则配方成本计算失真
        if fids and db.query(PrintRecipeFilament).filter(PrintRecipeFilament.filament_id.in_(fids)).first():
            raise HTTPException(400, "所选耗材仍被打印配方引用，请先删除相关配方或恢复耗材")
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
            db.query(OrderItem).filter(OrderItem.order_id == o.id).delete(synchronize_session=False)
            log_business("永久删除订单", o.order_no)
        deleted = len(orders)
        for o in orders:
            db.delete(o)

    db.commit()
    return {"deleted": deleted, "message": f"已永久删除 {deleted} 条{data.type}记录"}
