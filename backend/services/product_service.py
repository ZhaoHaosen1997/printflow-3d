from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from backend.models import PrintRecipe, PrintRecipeFilament, Product, Filament


def calculate_recipe_cost(db: Session, recipe_id: int) -> dict:
    recipe = (
        db.query(PrintRecipe)
        .options(joinedload(PrintRecipe.recipe_filaments).joinedload(PrintRecipeFilament.filament))
        .filter(PrintRecipe.id == recipe_id)
        .first()
    )
    if not recipe or not recipe.recipe_filaments:
        return {"total_cost": Decimal("0"), "unit_cost": Decimal("0")}

    total = Decimal("0")
    for rf in recipe.recipe_filaments:
        if rf.filament and rf.filament.price_per_kg:
            total += rf.grams * rf.filament.price_per_kg / Decimal("1000")

    total = total.quantize(Decimal("0.01"))
    unit_cost = (total / recipe.output_qty).quantize(Decimal("0.01")) if recipe.output_qty else Decimal("0")
    return {"total_cost": total, "unit_cost": unit_cost}


# 事务约定：service 层只 flush 不 commit，事务由调用方（路由层）统一提交/回滚


def sync_product_material_cost(db: Session, product_id: int):
    """用默认配方的实时单位成本刷新商品成本快照。"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return

    default_recipe = (
        db.query(PrintRecipe)
        .filter(PrintRecipe.product_id == product_id, PrintRecipe.is_default == True)  # noqa: E712
        .first()
    )

    if default_recipe:
        costs = calculate_recipe_cost(db, default_recipe.id)
        product.material_cost = costs["unit_cost"]
    else:
        product.material_cost = Decimal("0")

    db.flush()


def set_default_recipe(db: Session, recipe_id: int):
    recipe = db.query(PrintRecipe).filter(PrintRecipe.id == recipe_id).first()
    if not recipe:
        return

    db.query(PrintRecipe).filter(
        PrintRecipe.product_id == recipe.product_id,
        PrintRecipe.is_default == True,  # noqa: E712
    ).update({PrintRecipe.is_default: False}, synchronize_session=False)

    recipe.is_default = True
    db.flush()
    sync_product_material_cost(db, recipe.product_id)


def create_recipe(db: Session, product_id: int, data) -> PrintRecipe:
    recipe = PrintRecipe(
        product_id=product_id,
        name=data.name,
        output_qty=data.output_qty,
        print_time_min=data.print_time_min,
        notes=data.notes,
        is_default=data.is_default,
    )

    if data.is_default:
        db.query(PrintRecipe).filter(
            PrintRecipe.product_id == product_id,
            PrintRecipe.is_default == True,  # noqa: E712
        ).update({PrintRecipe.is_default: False}, synchronize_session=False)

    db.add(recipe)
    db.flush()

    for f_data in data.filaments:
        rf = PrintRecipeFilament(
            recipe_id=recipe.id,
            filament_id=f_data.filament_id,
            grams=f_data.grams,
        )
        db.add(rf)

    db.refresh(recipe)

    if recipe.is_default:
        sync_product_material_cost(db, product_id)

    return recipe


def update_recipe(db: Session, recipe_id: int, data) -> PrintRecipe:
    recipe = db.query(PrintRecipe).filter(PrintRecipe.id == recipe_id).first()
    if not recipe:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(recipe, key, value)

    if data.is_default:
        db.query(PrintRecipe).filter(
            PrintRecipe.product_id == recipe.product_id,
            PrintRecipe.id != recipe_id,
            PrintRecipe.is_default == True,  # noqa: E712
        ).update({PrintRecipe.is_default: False}, synchronize_session=False)

    db.flush()

    if recipe.is_default:
        sync_product_material_cost(db, recipe.product_id)

    return recipe


def replace_recipe_filaments(db: Session, recipe_id: int, items) -> list[PrintRecipeFilament] | None:
    """整单替换配方耗材：先清空再写入，单事务原子生效。

    替代前端"逐条删 + 逐条建"的 2N 次请求模式，且中途失败不再静默丢数据。
    """
    recipe = db.query(PrintRecipe).filter(PrintRecipe.id == recipe_id).first()
    if not recipe:
        return None

    fids = {i.filament_id for i in items}
    if fids:
        valid_count = db.query(Filament.id).filter(Filament.id.in_(fids)).count()
        if valid_count != len(fids):
            raise HTTPException(400, "存在无效的耗材引用，请刷新耗材列表后重试")

    db.query(PrintRecipeFilament).filter(
        PrintRecipeFilament.recipe_id == recipe_id
    ).delete(synchronize_session=False)

    rfs = [
        PrintRecipeFilament(recipe_id=recipe_id, filament_id=i.filament_id, grams=i.grams)
        for i in items
    ]
    db.add_all(rfs)
    db.flush()

    if recipe.is_default:
        sync_product_material_cost(db, recipe.product_id)

    return rfs


def delete_recipe(db: Session, recipe_id: int):
    recipe = db.query(PrintRecipe).filter(PrintRecipe.id == recipe_id).first()
    if not recipe:
        return None

    product_id = recipe.product_id
    was_default = recipe.is_default

    db.delete(recipe)
    db.flush()

    if was_default:
        next_recipe = (
            db.query(PrintRecipe)
            .filter(PrintRecipe.product_id == product_id)
            .first()
        )
        if next_recipe:
            next_recipe.is_default = True
        sync_product_material_cost(db, product_id)

    return True


def sync_product_costs_for_filament(db: Session, filament_id: int):
    """耗材价格变更后，级联刷新所有引用该耗材的默认配方所属商品的成本快照。

    新价格须由调用方先写入 filament.price_per_kg（依赖 autoflush 使其对本函数可见）。
    """
    default_recipes = (
        db.query(PrintRecipe)
        .join(PrintRecipeFilament)
        .filter(
            PrintRecipeFilament.filament_id == filament_id,
            PrintRecipe.is_default == True,  # noqa: E712
        )
        .all()
    )

    updated_products = set()
    for recipe in default_recipes:
        if recipe.product_id not in updated_products:
            sync_product_material_cost(db, recipe.product_id)
            updated_products.add(recipe.product_id)
