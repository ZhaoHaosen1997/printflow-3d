from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Game
from backend.schemas import GameCreate, GameUpdate, GameResponse, MessageResponse
from backend.services.logger_service import log_business

router = APIRouter(prefix="/games", tags=["games"])


@router.get("", response_model=list[GameResponse])
def list_games(db: Session = Depends(get_db)):
    return db.query(Game).order_by(Game.sort_order, Game.id).all()


@router.post("", response_model=GameResponse, status_code=201)
def create_game(data: GameCreate, db: Session = Depends(get_db)):
    if db.query(Game).filter(Game.slug == data.slug).first():
        raise HTTPException(400, f"游戏slug '{data.slug}' 已存在")
    if db.query(Game).filter(Game.name == data.name).first():
        raise HTTPException(400, f"游戏名 '{data.name}' 已存在")
    game = Game(**data.model_dump())
    db.add(game)
    db.commit()
    db.refresh(game)
    log_business("游戏创建", game.name)
    return game


@router.put("/{game_id}", response_model=GameResponse)
def update_game(game_id: int, data: GameUpdate, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(404, "游戏不存在")
    update_data = data.model_dump(exclude_unset=True)
    if "slug" in update_data and update_data["slug"] != game.slug:
        if db.query(Game).filter(Game.slug == update_data["slug"]).first():
            raise HTTPException(400, f"游戏slug '{update_data['slug']}' 已存在")
    if "name" in update_data and update_data["name"] != game.name:
        if db.query(Game).filter(Game.name == update_data["name"]).first():
            raise HTTPException(400, f"游戏名 '{update_data['name']}' 已存在")
    for key, value in update_data.items():
        setattr(game, key, value)
    db.commit()
    db.refresh(game)
    log_business("游戏更新", game.name)
    return game


@router.delete("/{game_id}", response_model=MessageResponse)
def delete_game(game_id: int, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(404, "游戏不存在")
    game.status = "archived"
    db.commit()
    log_business("游戏归档", game.name)
    return MessageResponse(message=f"游戏 '{game.name}' 已归档")
