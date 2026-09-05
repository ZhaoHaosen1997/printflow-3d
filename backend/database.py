import os

from backend.config import BASE_DIR, DATA_DIR
from backend.constants import STATUS_LABEL_TO_KEY
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# PRINTFLOW_DB_PATH 仅供测试脚本指向临时库，生产不设置
DB_PATH = os.getenv("PRINTFLOW_DB_PATH") or os.path.join(DATA_DIR, "app.db")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 15,  # busy_timeout：并发写时等待锁而不是立即抛 database is locked
    },
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """SQLite 默认不启用外键约束，需每个连接显式开启。"""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        # 显式回滚未提交事务（已 commit 或只读请求时为 no-op），不依赖 close 的隐式行为
        db.rollback()
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


STATUS_MIGRATION = STATUS_LABEL_TO_KEY  # 单一来源：backend/constants.py


def fix_order_statuses(db):
    """Migrate Chinese order status values to English."""
    from backend.models import Order
    updated = 0
    for chn, eng in STATUS_MIGRATION.items():
        rows = db.query(Order).filter(Order.status == chn).update(
            {Order.status: eng}, synchronize_session=False
        )
        updated += rows
    if updated:
        db.commit()
        print(f"Fixed {updated} order status(es)")


def seed_settings(db):
    from backend.models import Setting

    defaults = [
        ("shipping_fee", "0", "decimal", "卖家实际快递成本，利润计算时扣除"),
        ("service_fee_rate", "0.016", "decimal", "闲鱼服务费费率"),
        ("packaging_fee", "1.5", "decimal", "单品包装费"),
        ("packaging_fee_bundle", "2.0", "decimal", "合集包装费"),
    ]
    for key, value, value_type, desc in defaults:
        if not db.query(Setting).filter(Setting.key == key).first():
            db.add(Setting(key=key, value=value, value_type=value_type, description=desc))
    db.commit()


def _add_column_safe(table: str, column: str, col_def: str) -> bool:
    """Add a column if it doesn't already exist (SQLite). Returns True if added."""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(f"PRAGMA table_info({table})")
        cols = {row[1] for row in cur.fetchall()}
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
            conn.commit()
            print(f"Added column {table}.{column}")
            return True
        return False
    finally:
        conn.close()


def seed_games(db):
    from backend.models import Game

    if db.query(Game).count() > 0:
        return

    default_games = [
        Game(name="诡镇奇谈", slug="arkham_horror", sort_order=0),
    ]
    for game in default_games:
        db.add(game)
    db.commit()
    print("Seeded default games")


def seed_categories(db):
    from backend.models import Category

    if db.query(Category).count() > 0:
        return

    default_categories = [
        Category(name="计数器", slug="counter", sort_order=0),
        Category(name="指示物", slug="token", sort_order=1),
        Category(name="其他", slug="other", sort_order=2),
        Category(name="合集", slug="bundle", sort_order=3),
    ]
    for cat in default_categories:
        db.add(cat)
    db.commit()
    print("Seeded default categories")


CATEGORY_SLUG_MAP = {
    "counter": "counter",
    "token": "token",
    "other": "other",
    "bundle": "bundle",
}


def migrate_category_to_id(db):
    from backend.models import Product, Category, Game, product_games

    if db.query(Product).filter(Product.category_id.is_(None), Product.category.isnot(None)).count() == 0:
        return

    slug_to_id = {c.slug: c.id for c in db.query(Category).all()}
    updated = 0
    for product in db.query(Product).filter(Product.category_id.is_(None), Product.category.isnot(None)).all():
        cat_slug = CATEGORY_SLUG_MAP.get(product.category)
        if cat_slug and cat_slug in slug_to_id:
            product.category_id = slug_to_id[cat_slug]
            updated += 1
    if updated:
        db.commit()
        print(f"Migrated {updated} products.category → category_id")


def migrate_product_games(db):
    from backend.models import Product, Game, product_games
    from sqlalchemy import text

    game = db.query(Game).filter(Game.slug == "arkham_horror").first()
    if not game:
        return

    result = db.execute(text("SELECT COUNT(*) FROM product_games")).scalar()
    if result > 0:
        return

    products = db.query(Product).filter(Product.status == "active").all()
    for product in products:
        db.execute(
            product_games.insert().values(product_id=product.id, game_id=game.id)
        )
    db.commit()
    print(f"Associated {len(products)} products with default game")


def cleanup_orphan_rows(db):
    """清理 FK 未启用时期 bulk delete 遗留的孤儿行（存量数据一次性修复）。"""
    from backend.models import PrintRecipe, PrintRecipeFilament, PrintTask, Inventory, Product

    orphan_rf = (
        db.query(PrintRecipeFilament)
        .filter(~PrintRecipeFilament.recipe_id.in_(db.query(PrintRecipe.id)))
        .delete(synchronize_session=False)
    )
    orphan_task = (
        db.query(PrintTask)
        .filter(~PrintTask.recipe_id.in_(db.query(PrintRecipe.id)))
        .delete(synchronize_session=False)
    )
    orphan_inv = (
        db.query(Inventory)
        .filter(~Inventory.product_id.in_(db.query(Product.id)))
        .delete(synchronize_session=False)
    )
    if orphan_rf or orphan_task or orphan_inv:
        db.commit()
        log_db("迁移", f"清理孤儿行: 配方耗材={orphan_rf}, 打印任务={orphan_task}, 库存={orphan_inv}")


def init_db():
    from backend import models  # noqa: ensure all models loaded
    from backend.services.logger_service import log_db
    log_db("初始化", "创建/更新数据表结构")
    Base.metadata.create_all(bind=engine)
    added = _add_column_safe("products", "search_keywords", "JSON")
    if added:
        log_db("迁移", "products.search_keywords 列已添加")
    added = _add_column_safe("products", "sort_order", "INTEGER DEFAULT 0")
    if added:
        log_db("迁移", "products.sort_order 列已添加")
    added = _add_column_safe("products", "category_id", "INTEGER REFERENCES categories(id)")
    if added:
        log_db("迁移", "products.category_id 列已添加")
    db = SessionLocal()
    try:
        seed_colors(db)
        seed_settings(db)
        fix_color_ids(db)
        fix_order_statuses(db)
        seed_games(db)
        seed_categories(db)
        migrate_category_to_id(db)
        migrate_product_games(db)
        cleanup_orphan_rows(db)
    finally:
        db.close()
