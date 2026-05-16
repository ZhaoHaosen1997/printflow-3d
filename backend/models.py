from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, JSON, Text, DateTime,
    ForeignKey, Index, Numeric, text,
)
from sqlalchemy.orm import relationship
from backend.database import Base


class Color(Base):
    __tablename__ = "colors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    color_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    type = Column(String(20), nullable=False)
    swatches = Column(JSON, nullable=False)
    combo_of = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Filament(Base):
    __tablename__ = "filaments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    brand = Column(String(100), nullable=False)
    material = Column(String(50), nullable=False)
    price_per_kg = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    recipe_filaments = relationship("PrintRecipeFilament", back_populates="filament")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    xianyu_item_id = Column(String(100), unique=True, nullable=True)
    name = Column(String(200), nullable=False)
    category = Column(String(20), nullable=False)
    price_single = Column(Numeric(10, 2), default=0)
    price_bundle = Column(Numeric(10, 2), default=0)
    image = Column(Text, nullable=True)
    bundle_items = Column(JSON, nullable=True)
    colors = Column(JSON, nullable=True)
    contents = Column(JSON, nullable=True)
    material_cost = Column(Numeric(10, 2), default=0)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    recipes = relationship("PrintRecipe", back_populates="product", order_by="PrintRecipe.print_count.desc()")


class PrintRecipe(Base):
    __tablename__ = "print_recipes"
    __table_args__ = (
        Index(
            "idx_product_default_recipe", "product_id",
            unique=True,
            sqlite_where=text("is_default = 1"),
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    output_qty = Column(Integer, default=1)
    print_time_min = Column(Integer, nullable=True)
    print_count = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="recipes")
    recipe_filaments = relationship("PrintRecipeFilament", back_populates="recipe", cascade="all, delete-orphan")


class PrintRecipeFilament(Base):
    __tablename__ = "print_recipe_filaments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_id = Column(Integer, ForeignKey("print_recipes.id"), nullable=False)
    filament_id = Column(Integer, ForeignKey("filaments.id"), nullable=False)
    grams = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    recipe = relationship("PrintRecipe", back_populates="recipe_filaments")
    filament = relationship("Filament", back_populates="recipe_filaments")


class Buyer(Base):
    __tablename__ = "buyers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nickname = Column(String(100), nullable=False)
    province = Column(String(50), nullable=True)
    first_order_time = Column(DateTime, nullable=True)
    last_order_time = Column(DateTime, nullable=True)
    total_orders = Column(Integer, default=0)
    total_amount = Column(Numeric(10, 2), default=0)
    tags = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(50), unique=True, nullable=False)
    xianyu_order_id = Column(String(100), nullable=True)
    buyer_id = Column(Integer, ForeignKey("buyers.id"), nullable=True)
    status = Column(String(20), default="待发货")
    order_time = Column(DateTime, nullable=True)
    ship_time = Column(DateTime, nullable=True)
    completed_time = Column(DateTime, nullable=True)
    total_amount = Column(Numeric(10, 2), default=0)
    discount = Column(Numeric(10, 2), default=0)
    actual_amount = Column(Numeric(10, 2), default=0)
    shipping_fee = Column(Numeric(10, 2), default=0)
    packaging_fee = Column(Numeric(10, 2), default=0)
    service_fee = Column(Numeric(10, 2), default=0)
    service_fee_rate = Column(Numeric(5, 4), default=0)
    province = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    source = Column(String(20), default="manual")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    buyer = relationship("Buyer")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_name = Column(String(200), nullable=True)
    quantity = Column(Integer, default=1)
    unit_price = Column(Numeric(10, 2), default=0)
    material_cost = Column(Numeric(10, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")


class Inventory(Base):
    __tablename__ = "inventories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), unique=True, nullable=False)
    quantity = Column(Integer, default=0)
    warning_threshold = Column(Integer, default=5)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product")


class PrintTask(Base):
    __tablename__ = "print_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_no = Column(String(50), unique=True, nullable=False)
    recipe_id = Column(Integer, ForeignKey("print_recipes.id"), nullable=False)
    status = Column(String(20), default="pending")
    fail_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    recipe = relationship("PrintRecipe")


class Printer(Base):
    __tablename__ = "printers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    printer_no = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    status = Column(String(20), default="idle")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    value_type = Column(String(20), default="string")
    description = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
