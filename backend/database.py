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
        ("gold-silver-bronze", "金-银-青铜", ["#d4af37", "#c0c0c0", "#74632e"], ["gold", "silver", "bronze"]),
    ]

    for color_id, name, swatches in standard_colors:
        db.add(Color(color_id=color_id, name=name, type="standard", swatches=swatches))

    for color_id, name, swatches, combo_of in combo_colors:
        db.add(Color(color_id=color_id, name=name, type="combo", swatches=swatches, combo_of=combo_of))

    db.commit()


def fix_color_ids(db):
    """Migrate Chinese or malformed color_ids to clean English slugs."""
    from backend.models import Color
    from backend.routers.colors import _translate_name

    colors = db.query(Color).all()
    updated = 0
    for c in colors:
        expected = _translate_name(c.name)
        if c.color_id != expected:
            # Check if expected id already taken by another record
            existing = db.query(Color).filter(
                Color.color_id == expected,
                Color.id != c.id,
            ).first()
            if existing:
                n = 2
                while db.query(Color).filter(Color.color_id == f"{expected}{n}").first():
                    n += 1
                expected = f"{expected}{n}"
            c.color_id = expected
            updated += 1
    if updated:
        db.commit()
        print(f"Fixed {updated} color_id(s)")


STATUS_MIGRATION = {
    "pending": "待发货",
    "shipped": "已发货",
    "completed": "交易成功",
    "cancelled": "已取消",
}


def fix_order_statuses(db):
    """Migrate English order status values to Chinese."""
    from backend.models import Order
    updated = 0
    for eng, chn in STATUS_MIGRATION.items():
        rows = db.query(Order).filter(Order.status == eng).update(
            {Order.status: chn}, synchronize_session=False
        )
        updated += rows
    if updated:
        db.commit()
        print(f"Fixed {updated} order status(es)")


def seed_settings(db):
    from backend.models import Setting

    defaults = [
        ("shipping_fee", "0", "decimal", "默认运费（包邮为0）"),
        ("service_fee_rate", "0.016", "decimal", "闲鱼服务费费率"),
        ("packaging_fee", "1.5", "decimal", "单品包装费"),
        ("packaging_fee_bundle", "2.0", "decimal", "合集包装费"),
    ]
    for key, value, value_type, desc in defaults:
        if not db.query(Setting).filter(Setting.key == key).first():
            db.add(Setting(key=key, value=value, value_type=value_type, description=desc))
    db.commit()


def init_db():
    from backend import models  # noqa: ensure all models loaded
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_colors(db)
        seed_settings(db)
        fix_color_ids(db)
        fix_order_statuses(db)
    finally:
        db.close()
