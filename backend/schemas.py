from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, computed_field


# ============ Colors ============

class ColorBase(BaseModel):
    color_id: str
    name: str
    type: str  # standard / combo
    swatches: List[str]
    combo_of: Optional[List[str]] = None


class ColorCreate(ColorBase):
    pass


class ColorUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    swatches: Optional[List[str]] = None
    combo_of: Optional[List[str]] = None


class ColorResponse(ColorBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ Filaments ============

class FilamentBase(BaseModel):
    brand: str
    material: str
    price_per_kg: Decimal


class FilamentCreate(FilamentBase):
    pass


class FilamentUpdate(BaseModel):
    brand: Optional[str] = None
    material: Optional[str] = None
    price_per_kg: Optional[Decimal] = None
    status: Optional[str] = None


class FilamentResponse(BaseModel):
    id: int
    brand: str
    material: str
    price_per_kg: Decimal
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def display_name(self) -> str:
        return f"{self.brand} {self.material}"


# ============ Print Recipe Filaments ============

class PrintRecipeFilamentBase(BaseModel):
    filament_id: int
    grams: Decimal


class PrintRecipeFilamentCreate(PrintRecipeFilamentBase):
    pass


class PrintRecipeFilamentUpdate(BaseModel):
    grams: Decimal


class FilamentInfo(BaseModel):
    id: int
    brand: str
    material: str
    price_per_kg: Decimal

    model_config = ConfigDict(from_attributes=True)


class PrintRecipeFilamentResponse(PrintRecipeFilamentBase):
    id: int
    filament: Optional[FilamentInfo] = None

    model_config = ConfigDict(from_attributes=True)


# ============ Print Recipes ============

class PrintRecipeBase(BaseModel):
    name: str
    output_qty: int = 1
    print_time_min: Optional[int] = None
    notes: Optional[str] = None
    is_default: bool = False


class PrintRecipeCreate(PrintRecipeBase):
    filaments: List[PrintRecipeFilamentCreate] = []


class PrintRecipeUpdate(BaseModel):
    name: Optional[str] = None
    output_qty: Optional[int] = None
    print_time_min: Optional[int] = None
    notes: Optional[str] = None
    is_default: Optional[bool] = None
    status: Optional[str] = None


class PrintRecipeResponse(PrintRecipeBase):
    id: int
    product_id: int
    print_count: int
    status: str
    total_cost: Decimal = Decimal("0")
    unit_cost: Decimal = Decimal("0")
    recipe_filaments: List[PrintRecipeFilamentResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ Products ============

class ProductBase(BaseModel):
    name: str
    category: str  # counter / token / other / bundle
    xianyu_item_id: Optional[str] = None
    price_single: Decimal = Decimal("0")
    price_bundle: Decimal = Decimal("0")
    image: Optional[str] = None
    bundle_items: Optional[List[int]] = None
    colors: Optional[dict] = None
    contents: Optional[List[str]] = None
    status: str = "active"


class ProductCreate(ProductBase):
    default_recipe: Optional[PrintRecipeCreate] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    xianyu_item_id: Optional[str] = None
    price_single: Optional[Decimal] = None
    price_bundle: Optional[Decimal] = None
    image: Optional[str] = None
    bundle_items: Optional[List[int]] = None
    colors: Optional[dict] = None
    contents: Optional[List[str]] = None
    status: Optional[str] = None


class ProductResponse(ProductBase):
    id: int
    material_cost: Decimal
    recipes: List[PrintRecipeResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    id: int
    name: str
    category: str
    price_single: Decimal
    price_bundle: Decimal
    material_cost: Decimal
    image: Optional[str] = None
    bundle_items: Optional[List[int]] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ Orders ============

class OrderItemBase(BaseModel):
    product_id: int
    product_name: Optional[str] = None
    quantity: int = 1
    unit_price: Decimal = Decimal("0")
    material_cost: Decimal = Decimal("0")


class OrderItemResponse(OrderItemBase):
    id: int
    order_id: int

    model_config = ConfigDict(from_attributes=True)


# ============ Inventories ============

class InventoryResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    warning_threshold: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ Settings ============

class SettingResponse(BaseModel):
    id: int
    key: str
    value: str
    value_type: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SettingUpdate(BaseModel):
    value: str


# ============ Common ============

class MessageResponse(BaseModel):
    message: str
    success: bool = True
