from decimal import Decimal
from sqlalchemy.orm import Session
from backend.models import PrintRecipe, PrintRecipeFilament, Product, Filament


def calculate_recipe_cost(db: Session, recipe_id: int) -> dict:
    recipe = db.query(PrintRecipe).filter(PrintRecipe.id == recipe_id).first()
    if not recipe or not recipe.recipe_filaments:
        return {"total_cost": Decimal("0"), "unit_cost": Decimal("0")}

    total = Decimal("0")
    for rf in recipe.recipe_filaments:
        filament = db.query(Filament).filter(Filament.id == rf.filament_id).first()
        if filament and filament.price_per_kg:
            total += rf.grams * filament.price_per_kg / Decimal("1000")

    total = total.quantize(Decimal("0.01"))
    unit_cost = (total / recipe.output_qty).quantize(Decimal("0.01")) if recipe.output_qty else Decimal("0")
    return {"total_cost": total, "unit_cost": unit_cost}


def sync_product_material_cost(db: Session, product_id: int):
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

    db.commit()


def set_default_recipe(db: Session, recipe_id: int):
    recipe = db.query(PrintRecipe).filter(PrintRecipe.id == recipe_id).first()
    if not recipe:
        return

    db.query(PrintRecipe).filter(
        PrintRecipe.product_id == recipe.product_id,
        PrintRecipe.is_default == True,  # noqa: E712
    ).update({PrintRecipe.is_default: False})

    recipe.is_default = True
    db.commit()
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
        ).update({PrintRecipe.is_default: False})

    db.add(recipe)
    db.flush()

    for f_data in data.filaments:
        rf = PrintRecipeFilament(
            recipe_id=recipe.id,
            filament_id=f_data.filament_id,
            grams=f_data.grams,
        )
        db.add(rf)

    db.commit()
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
        ).update({PrintRecipe.is_default: False})

    db.commit()
    db.refresh(recipe)

    if recipe.is_default:
        sync_product_material_cost(db, recipe.product_id)

    return recipe


def delete_recipe(db: Session, recipe_id: int):
    recipe = db.query(PrintRecipe).filter(PrintRecipe.id == recipe_id).first()
    if not recipe:
        return None

    product_id = recipe.product_id
    was_default = recipe.is_default

    db.delete(recipe)
    db.commit()

    if was_default:
        next_recipe = (
            db.query(PrintRecipe)
            .filter(PrintRecipe.product_id == product_id)
            .first()
        )
        if next_recipe:
            next_recipe.is_default = True
            db.commit()
        sync_product_material_cost(db, product_id)

    return True


def update_filament_price(db: Session, filament_id: int, new_price: Decimal):
    filament = db.query(Filament).filter(Filament.id == filament_id).first()
    if not filament:
        return

    filament.price_per_kg = new_price
    db.commit()

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
