"""通用 CRUD 样板工具：get-or-404、PATCH 应用、唯一性校验。

收敛各 router 重复的 `query→first→404`、`model_dump→setattr 循环`、
`slug/name 查重` 三类样板。
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session


def get_or_404(db: Session, model, entity_id, message: str):
    """按主键取实体，不存在时抛 404。"""
    obj = db.query(model).filter(model.id == entity_id).first()
    if not obj:
        raise HTTPException(404, message)
    return obj


def apply_update(obj, update_data: dict):
    """把 model_dump(exclude_unset=True) 得到的字段字典逐个 setattr 到实体上。"""
    for key, value in update_data.items():
        setattr(obj, key, value)
    return obj


def ensure_unique(db: Session, model, filters: dict, label: str, exclude_id: int | None = None):
    """字段唯一性校验，任一冲突即 400。

    filters: {字段名: 值}，值为 None 时跳过；exclude_id 用于更新场景排除自身。
    错误文案与既有行为一致：slug 字段报 "游戏slug 'x' 已存在"，其余报 "游戏名 'x' 已存在"。
    """
    for field, value in filters.items():
        if value is None:
            continue
        q = db.query(model).filter(getattr(model, field) == value)
        if exclude_id is not None:
            q = q.filter(model.id != exclude_id)
        if q.first():
            field_label = "slug" if field == "slug" else "名"
            raise HTTPException(400, f"{label}{field_label} '{value}' 已存在")
