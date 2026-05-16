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


class ColorCreate(BaseModel):
    name: str
    type: str  # standard / combo
    swatches: List[str]
    combo_of: Optional[List[str]] = None


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
    charity_rate: Optional[Decimal] = None
    search_keywords: Optional[List[str]] = None
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
    charity_rate: Optional[Decimal] = None
    search_keywords: Optional[List[str]] = None
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
    charity_rate: Optional[Decimal] = None
    search_keywords: Optional[List[str]] = None
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


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    id: int
    order_id: int

    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    xianyu_order_id: Optional[str] = None
    buyer_nickname: Optional[str] = None
    buyer_province: Optional[str] = None
    status: str = "pending_ship"
    order_time: Optional[datetime] = None
    total_amount: Decimal = Decimal("0")
    discount: Decimal = Decimal("0")
    actual_amount: Decimal = Decimal("0")
    shipping_fee: Optional[Decimal] = None
    packaging_fee: Optional[Decimal] = None
    service_fee: Optional[Decimal] = None
    service_fee_rate: Optional[Decimal] = None
    charity_fee: Optional[Decimal] = None
    charity_fee_rate: Optional[Decimal] = None
    province: Optional[str] = None
    notes: Optional[str] = None
    source: str = "manual"
    items: List[OrderItemCreate] = []


class OrderUpdate(BaseModel):
    buyer_id: Optional[int] = None
    buyer_nickname: Optional[str] = None
    status: Optional[str] = None
    total_amount: Optional[Decimal] = None
    discount: Optional[Decimal] = None
    actual_amount: Optional[Decimal] = None
    shipping_fee: Optional[Decimal] = None
    packaging_fee: Optional[Decimal] = None
    service_fee: Optional[Decimal] = None
    service_fee_rate: Optional[Decimal] = None
    charity_fee: Optional[Decimal] = None
    charity_fee_rate: Optional[Decimal] = None
    province: Optional[str] = None
    notes: Optional[str] = None
    items: Optional[List[OrderItemCreate]] = None


class OrderResponse(BaseModel):
    id: int
    order_no: str
    xianyu_order_id: Optional[str] = None
    buyer_id: Optional[int] = None
    buyer_nickname: Optional[str] = None
    status: str
    order_time: Optional[datetime] = None
    ship_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None
    total_amount: Decimal
    discount: Decimal
    actual_amount: Decimal
    shipping_fee: Decimal
    packaging_fee: Decimal
    service_fee: Decimal
    service_fee_rate: Decimal
    charity_fee: Decimal
    charity_fee_rate: Optional[Decimal] = None
    province: Optional[str] = None
    notes: Optional[str] = None
    source: str
    items: List[OrderItemResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderListResponse(BaseModel):
    id: int
    order_no: str
    xianyu_order_id: Optional[str] = None
    buyer_id: Optional[int] = None
    buyer_nickname: Optional[str] = None
    status: str
    order_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None
    total_amount: Decimal
    discount: Decimal
    actual_amount: Decimal
    source: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedOrdersResponse(BaseModel):
    items: List[OrderListResponse]
    total: int


# ============ Parser ============

class ParsedOrderItem(BaseModel):
    product_id: Optional[int] = None
    product_name: str
    quantity: int = 1
    unit_price: Decimal = Decimal("0")
    material_cost: Decimal = Decimal("0")
    matched: bool = False
    is_bundle: bool = False
    bundle_children: Optional[List[dict]] = None


class ParsedOrder(BaseModel):
    xianyu_order_id: Optional[str] = None
    status: str = "pending_ship"
    order_time: Optional[datetime] = None
    product_name: Optional[str] = None
    total_amount: Decimal = Decimal("0")
    actual_amount: Decimal = Decimal("0")
    quantity: int = 1
    buyer_nickname: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_phone: Optional[str] = None
    buyer_address: Optional[str] = None
    buyer_province: Optional[str] = None
    matched_product_id: Optional[int] = None
    matched: bool = False
    is_bundle: bool = False
    bundle_items: Optional[List[ParsedOrderItem]] = None
    discount: Decimal = Decimal("0")
    shipping_free: bool = True


class ParseRequest(BaseModel):
    text: str


class ParseResponse(BaseModel):
    orders: List[ParsedOrder] = []
    errors: List[str] = []


# ============ Inventories ============

class InventoryCreate(BaseModel):
    product_id: int
    quantity: int = 0
    warning_threshold: int = 5


class InventoryUpdate(BaseModel):
    quantity: Optional[int] = None
    warning_threshold: Optional[int] = None


class InventoryResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    warning_threshold: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryListResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_category: str
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


# ============ Print Tasks ============

class PrintTaskCreate(BaseModel):
    recipe_id: int
    notes: Optional[str] = None


class PrintTaskUpdate(BaseModel):
    notes: Optional[str] = None
    status: Optional[str] = None


class PrintTaskFailRequest(BaseModel):
    fail_reason: Optional[str] = None


class RecipeInfo(BaseModel):
    id: int
    name: str
    product_id: int
    output_qty: int
    print_time_min: Optional[int] = None
    product_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PrintTaskResponse(BaseModel):
    id: int
    task_no: str
    recipe_id: int
    status: str
    fail_reason: Optional[str] = None
    retry_count: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    recipe: Optional[RecipeInfo] = None

    model_config = ConfigDict(from_attributes=True)


class PrintTaskListResponse(BaseModel):
    id: int
    task_no: str
    recipe_id: int
    status: str
    fail_reason: Optional[str] = None
    retry_count: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    recipe_name: Optional[str] = None
    product_name: Optional[str] = None
    product_id: Optional[int] = None
    output_qty: Optional[int] = None
    print_time_min: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedPrintTasksResponse(BaseModel):
    items: List[PrintTaskListResponse]
    total: int


# ============ Buyers ============

class BuyerUpdate(BaseModel):
    nickname: Optional[str] = None
    province: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


class BuyerResponse(BaseModel):
    id: int
    nickname: str
    province: Optional[str] = None
    first_order_time: Optional[datetime] = None
    last_order_time: Optional[datetime] = None
    total_orders: int
    total_amount: Decimal
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BuyerOrderSummary(BaseModel):
    id: int
    order_no: str
    status: str
    order_time: Optional[datetime] = None
    actual_amount: Decimal

    model_config = ConfigDict(from_attributes=True)


class BuyerDetailResponse(BuyerResponse):
    recent_orders: List[BuyerOrderSummary] = []


class PaginatedBuyersResponse(BaseModel):
    items: List[BuyerResponse]
    total: int


# ============ Sales ============

class SalesOverviewResponse(BaseModel):
    total_orders: int = 0
    total_revenue: Decimal = Decimal("0")
    total_profit: Decimal = Decimal("0")
    total_material_cost: Decimal = Decimal("0")
    total_shipping_fee: Decimal = Decimal("0")
    total_packaging_fee: Decimal = Decimal("0")
    total_service_fee: Decimal = Decimal("0")
    total_charity_fee: Decimal = Decimal("0")
    total_discount: Decimal = Decimal("0")
    avg_order_value: Decimal = Decimal("0")
    avg_profit_per_order: Decimal = Decimal("0")


class MonthlySalesItem(BaseModel):
    month: int
    orders: int = 0
    revenue: Decimal = Decimal("0")
    profit: Decimal = Decimal("0")


class ProductSalesItem(BaseModel):
    product_id: int
    product_name: str
    category: str
    quantity: int = 0
    revenue: Decimal = Decimal("0")
    material_cost: Decimal = Decimal("0")
    profit: Decimal = Decimal("0")


# ============ Common ============

class MessageResponse(BaseModel):
    message: str
    success: bool = True
