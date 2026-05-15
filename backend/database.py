import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "app.db")

os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_colors(db):
    from backend.models import Color

    if db.query(Color).count() > 0:
        return

    standard_colors = [
        ("black", "黑色", ["#000000"]),
        ("white", "白色", ["#ffffff"]),
        ("gray", "灰色", ["#8e8e8e"]),
        ("silver", "银色", ["#c0c0c0"]),
        ("gold", "金色", ["#d4af37"]),
        ("red", "红色", ["#ff0000"]),
        ("blue", "蓝色", ["#1a90ff"]),
        ("purple", "紫色", ["#B25FEC"]),
        ("yellow", "黄色", ["#dad236"]),
        ("bronze", "青铜色", ["#74632e"]),
        ("orange", "橙色", ["#FFA500"]),
        ("亮gold", "亮金色", ["#FFDE66"]),
        ("深purple", "深紫色", ["#44004D"]),
        ("green", "绿色", ["#00FF00"]),
        ("深green", "深绿色", ["#054D00"]),
    ]

    combo_colors = [
        ("blackgold", "黑金", ["#000000", "#d4af37"], ["black", "gold"]),
        ("blacksilver", "黑银", ["#000000", "#c0c0c0"], ["black", "silver"]),
        ("whiteredblue", "白红蓝", ["#ffffff", "#ff0000", "#1a90ff"], ["white", "red", "blue"]),
        ("亮gold-gold-silver", "亮金-金-银", ["#FFDE66", "#d4af37", "#c0c0c0"], ["亮gold", "gold", "silver"]),
        ("purplewhite", "紫白", ["#B25FEC", "#ffffff"], ["purple", "white"]),
        ("whitered", "白红", ["#ffffff", "#ff0000"], ["white", "red"]),
        ("gold-silver-cyancopper", "金-银-青铜", ["#d4af37", "#c0c0c0", "#74632e"], ["gold", "silver", "bronze"]),
    ]

    for color_id, name, swatches in standard_colors:
        db.add(Color(color_id=color_id, name=name, type="standard", swatches=swatches))

    for color_id, name, swatches, combo_of in combo_colors:
        db.add(Color(color_id=color_id, name=name, type="combo", swatches=swatches, combo_of=combo_of))

    db.commit()


def init_db():
    from backend import models  # noqa: ensure all models loaded
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_colors(db)
    finally:
        db.close()
