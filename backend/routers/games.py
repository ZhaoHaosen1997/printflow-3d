from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.crud_utils import apply_update, ensure_unique, get_or_404
from backend.database import get_db
from backend.models import Game
from backend.schemas import GameCreate, GameUpdate, GameResponse, MessageResponse
from backend.services.logger_service import log_business

router = APIRouter(prefix="/games", tags=["games"])

LABEL = "游戏"


@router.get("", response_model=list[GameResponse])
def list_games(db: Session = Depends(get_db)):
    return db.query(Game).order_by(Game.sort_order, Game.id).all()


@router.post("", response_model=GameResponse, status_code=201)
def create_game(data: GameCreate, db: Session = Depends(get_db)):
    ensure_unique(db, Game, {"slug": data.slug, "name": data.name}, LABEL)
    game = Game(**data.model_dump())
    db.add(game)
    db.commit()
    db.refresh(game)
    log_business("游戏创建", game.name)
    return game


@router.put("/{game_id}", response_model=GameResponse)
def update_game(game_id: int, data: GameUpdate, db: Session = Depends(get_db)):
    game = get_or_404(db, Game, game_id, "游戏不存在")
    update_data = data.model_dump(exclude_unset=True)
    ensure_unique(
        db, Game,
        {"slug": update_data.get("slug"), "name": update_data.get("name")},
        LABEL, exclude_id=game.id,
    )
    apply_update(game, update_data)
    db.commit()
    db.refresh(game)
    log_business("游戏更新", game.name)
    return game


@router.delete("/{game_id}", response_model=MessageResponse)
def delete_game(game_id: int, db: Session = Depends(get_db)):
    game = get_or_404(db, Game, game_id, "游戏不存在")
    game.status = "archived"
    db.commit()
    log_business("游戏归档", game.name)
    return MessageResponse(message=f"游戏 '{game.name}' 已归档")
