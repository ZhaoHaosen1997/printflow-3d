from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Product, PrintRecipe, PrintRecipeFilament, Inventory
from backend.schemas import (
    ProductCreate, ProductUpdate, ProductResponse,
    PrintRecipeCreate, PrintRecipeUpdate, PrintRecipeResponse,
    PrintRecipeFilamentCreate, PrintRecipeFilamentResponse,
    MessageResponse,
)
from backend.services.product_service import (
    calculate_recipe_cost, create_recipe, update_recipe, delete_recipe,
    set_default_recipe, sync_product_material_cost,
)
from backend.services.logger_service import log_business

router = APIRouter(tags=["products"])


# ============ Product CRUD ============

@router.get("/products", response_model=list[ProductResponse])
def list_products(
    category: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Product)
    if category:
        q = q.filter(Product.category == category)
    if status:
        q = q.filter(Product.status == status)
    return q.order_by(Product.category, Product.name).all()


@router.post("/products", response_model=ProductResponse, status_code=201)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    if data.xianyu_item_id:
        existing = db.query(Product).filter(Product.xianyu_item_id == data.xianyu_item_id).first()
        if existing:
            raise HTTPException(400, f"闲鱼商品ID '{data.xianyu_item_id}' 已存在")

    product_data = data.model_dump(exclude={"default_recipe"})
    product = Product(**product_data)
    db.add(product)
    db.flush()

    # Auto-create inventory record
    db.add(Inventory(product_id=product.id, quantity=0, warning_threshold=5))

    if data.default_recipe:
        create_recipe(db, product.id, data.default_recipe)

    db.commit()
    db.refresh(product)
    log_business("商品创建", product.name, category=product.category)
    return product


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "商品不存在")

    for recipe in product.recipes:
        costs = calculate_recipe_cost(db, recipe.id)
        recipe.total_cost = costs["total_cost"]
        recipe.unit_cost = costs["unit_cost"]

    return product


@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, data: ProductUpdate, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "商品不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/products/{product_id}", response_model=MessageResponse)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "商品不存在")
    product.status = "archived"
    db.commit()
    log_business("商品归档", product.name)
    return MessageResponse(message=f"商品 '{product.name}' 已归档")


# ============ Recipe sub-resources ============

@router.get("/products/{product_id}/recipes", response_model=list[PrintRecipeResponse])
def list_recipes(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "商品不存在")

    recipes = (
        db.query(PrintRecipe)
        .filter(PrintRecipe.product_id == product_id)
        .order_by(PrintRecipe.print_count.desc())
        .all()
    )

    for recipe in recipes:
        costs = calculate_recipe_cost(db, recipe.id)
        recipe.total_cost = costs["total_cost"]
        recipe.unit_cost = costs["unit_cost"]

    return recipes


@router.post("/products/{product_id}/recipes", response_model=PrintRecipeResponse, status_code=201)
def add_recipe(product_id: int, data: PrintRecipeCreate, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "商品不存在")

    recipe = create_recipe(db, product_id, data)
    costs = calculate_recipe_cost(db, recipe.id)
    recipe.total_cost = costs["total_cost"]
    recipe.unit_cost = costs["unit_cost"]
    return recipe


@router.put("/recipes/{recipe_id}", response_model=PrintRecipeResponse)
def update_recipe_endpoint(recipe_id: int, data: PrintRecipeUpdate, db: Session = Depends(get_db)):
    recipe = update_recipe(db, recipe_id, data)
    if not recipe:
        raise HTTPException(404, "配方不存在")

    costs = calculate_recipe_cost(db, recipe_id)
    recipe.total_cost = costs["total_cost"]
    recipe.unit_cost = costs["unit_cost"]
    return recipe


@router.delete("/recipes/{recipe_id}", response_model=MessageResponse)
def delete_recipe_endpoint(recipe_id: int, db: Session = Depends(get_db)):
    result = delete_recipe(db, recipe_id)
    if not result:
        raise HTTPException(404, "配方不存在")
    return MessageResponse(message="配方已删除")


@router.put("/recipes/{recipe_id}/default", response_model=MessageResponse)
def set_default(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.query(PrintRecipe).filter(PrintRecipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(404, "配方不存在")
    set_default_recipe(db, recipe_id)
    return MessageResponse(message=f"已设为默认配方: {recipe.name}")


# ============ Recipe-Filament sub-resources ============

@router.post("/recipes/{recipe_id}/filaments", response_model=PrintRecipeFilamentResponse, status_code=201)
def add_recipe_filament(recipe_id: int, data: PrintRecipeFilamentCreate, db: Session = Depends(get_db)):
    recipe = db.query(PrintRecipe).filter(PrintRecipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(404, "配方不存在")

    rf = PrintRecipeFilament(recipe_id=recipe_id, filament_id=data.filament_id, grams=data.grams)
    db.add(rf)
    db.commit()
    db.refresh(rf)

    if recipe.is_default:
        sync_product_material_cost(db, recipe.product_id)

    return rf


@router.put("/recipe-filaments/{rf_id}", response_model=PrintRecipeFilamentResponse)
def update_recipe_filament(rf_id: int, data: PrintRecipeFilamentCreate, db: Session = Depends(get_db)):
    rf = db.query(PrintRecipeFilament).filter(PrintRecipeFilament.id == rf_id).first()
    if not rf:
        raise HTTPException(404, "配方耗材不存在")

    rf.filament_id = data.filament_id
    rf.grams = data.grams
    db.commit()
    db.refresh(rf)

    recipe = db.query(PrintRecipe).filter(PrintRecipe.id == rf.recipe_id).first()
    if recipe and recipe.is_default:
        sync_product_material_cost(db, recipe.product_id)

    return rf


@router.delete("/recipe-filaments/{rf_id}", response_model=MessageResponse)
def delete_recipe_filament(rf_id: int, db: Session = Depends(get_db)):
    rf = db.query(PrintRecipeFilament).filter(PrintRecipeFilament.id == rf_id).first()
    if not rf:
        raise HTTPException(404, "配方耗材不存在")

    recipe_id = rf.recipe_id
    recipe = db.query(PrintRecipe).filter(PrintRecipe.id == recipe_id).first()

    db.delete(rf)
    db.commit()

    if recipe and recipe.is_default:
        sync_product_material_cost(db, recipe.product_id)

    return MessageResponse(message="配方耗材已删除")
