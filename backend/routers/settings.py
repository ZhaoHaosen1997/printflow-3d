from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Setting
from backend.schemas import SettingResponse, SettingUpdate
from backend.services.logger_service import log_business

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=list[SettingResponse])
def list_settings(db: Session = Depends(get_db)):
    return db.query(Setting).order_by(Setting.key).all()


@router.put("/{key}", response_model=SettingResponse)
def update_setting(key: str, data: SettingUpdate, db: Session = Depends(get_db)):
    setting = db.query(Setting).filter(Setting.key == key).first()
    if not setting:
        raise HTTPException(404, f"配置项 '{key}' 不存在")
    old_value = setting.value
    setting.value = data.value
    db.commit()
    db.refresh(setting)
    log_business("配置变更", key, detail=f"{old_value}→{setting.value}")
    return setting
