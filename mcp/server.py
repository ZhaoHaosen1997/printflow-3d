import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("printflow")

API_BASE = "http://localhost:8848/api"
TIMEOUT = 30.0


def _get(path: str, params: dict = None) -> dict | list | str:
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.get(f"{API_BASE}{path}", params=params or {})
            r.raise_for_status()
            return r.json()
    except httpx.ConnectError:
        return f"Error: Cannot connect to PrintFlow API ({API_BASE})"
    except httpx.HTTPStatusError as e:
        return f"Error: API returned {e.response.status_code}"
    except Exception as e:
        return f"Error: {e}"


def _post(path: str, json: dict = None) -> dict | list | str:
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(f"{API_BASE}{path}", json=json or {})
            r.raise_for_status()
            return r.json()
    except httpx.ConnectError:
        return f"Error: Cannot connect to PrintFlow API ({API_BASE})"
    except httpx.HTTPStatusError as e:
        try:
            detail = e.response.json().get("detail", e.response.text)
        except Exception:
            detail = e.response.text
        return f"Error: {detail}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def search_products(search: str = "", game_id: int = None, category_id: int = None) -> list[dict]:
    """Search PrintFlow products by name or keyword.

    Returns a list of matching products with id, name, category, prices, and games.
    Use this to find product IDs before creating orders.

    Args:
        search: Search term to match against product names. Leave empty to list all.
        game_id: Optional game ID to filter by.
        category_id: Optional category ID to filter by.

    Returns:
        List of product objects with id, name, category, category_obj, games, price_single, price_bundle, material_cost, status.
    """
    params = {"status": "active"}
    if search:
        params["search"] = search
    if game_id:
        params["game_id"] = game_id
    if category_id:
        params["category_id"] = category_id
    result = _get("/products", params)
    if isinstance(result, str):
        return [{"error": result}]
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "category": p.get("category"),
            "category_name": p.get("category_obj", {}).get("name") if p.get("category_obj") else None,
            "games": [g["name"] for g in p.get("games", [])],
            "price_single": p.get("price_single"),
            "price_bundle": p.get("price_bundle"),
            "material_cost": p.get("material_cost"),
            "status": p.get("status"),
        }
        for p in result
    ]


@mcp.tool()
def get_product_detail(product_id: int) -> dict:
    """Get detailed information about a specific product.

    Returns full product data including recipes (with filament cost breakdown),
    inventory status, colors, and bundle items.

    Args:
        product_id: The product ID (required).

    Returns:
        Product detail object with all fields including recipes and inventory info.
    """
    result = _get(f"/products/{product_id}")
    if isinstance(result, str):
        return {"error": result}
    return {
        "id": result["id"],
        "name": result["name"],
        "category": result.get("category"),
        "category_name": result.get("category_obj", {}).get("name") if result.get("category_obj") else None,
        "games": result.get("games", []),
        "price_single": result.get("price_single"),
        "price_bundle": result.get("price_bundle"),
        "material_cost": result.get("material_cost"),
        "colors": result.get("colors"),
        "contents": result.get("contents"),
        "bundle_items": result.get("bundle_items"),
        "recipes": [
            {
                "id": r["id"],
                "name": r["name"],
                "output_qty": r["output_qty"],
                "is_default": r["is_default"],
                "total_cost": r.get("total_cost"),
                "unit_cost": r.get("unit_cost"),
                "filaments": [
                    {
                        "filament_id": rf["filament_id"],
                        "grams": rf["grams"],
                    }
                    for rf in r.get("recipe_filaments", [])
                ],
            }
            for r in result.get("recipes", [])
        ],
        "status": result.get("status"),
    }


@mcp.tool()
def parse_order_text(text: str) -> dict:
    """Parse pasted Xianyu order text into structured order data.

    Use this when you have raw order text (from copy-paste).
    For structured data from Vision/AI, use parse_structured_order instead.

    Args:
        text: The raw order text pasted from Xianyu app.

    Returns:
        Parse result with orders list and errors list.
        Each order contains matched product info, buyer info, and pricing.
    """
    result = _post("/orders/parse", {"text": text})
    if isinstance(result, str):
        return {"error": result}
    return result


@mcp.tool()
def parse_structured_order(
    xianyu_order_id: str = None,
    status: str = "pending_ship",
    order_time: str = None,
    product_name: str = None,
    total_amount: float = 0,
    actual_amount: float = 0,
    quantity: int = 1,
    buyer_nickname: str = None,
    buyer_province: str = None,
) -> dict:
    """Parse structured order data from Vision/AI recognition.

    Use this instead of parse_order_text when you already have structured fields
    (e.g., from image recognition). Skips the text assembly step and goes directly
    to product matching and bundle expansion.

    Args:
        xianyu_order_id: Xianyu order ID (15-20 digit number).
        status: Order status, one of: pending_ship, shipped, completed. Default: pending_ship.
        order_time: Order time in ISO format (e.g., "2026-06-12T12:45:56").
        product_name: Product name as shown on Xianyu (for fuzzy matching).
        total_amount: Original total amount (before discount).
        actual_amount: Actual amount paid by buyer.
        quantity: Number of items. Default: 1.
        buyer_nickname: Buyer's nickname on Xianyu.
        buyer_province: Buyer's province (extracted from address).

    Returns:
        Parse result with orders list (containing matched product info) and errors list.
    """
    items = [{
        "product_name": product_name or "",
        "total_amount": total_amount,
        "actual_amount": actual_amount,
        "quantity": quantity,
    }]
    payload = {
        "xianyu_order_id": xianyu_order_id,
        "status": status,
        "buyer_nickname": buyer_nickname,
        "buyer_province": buyer_province,
        "items": items,
    }
    if order_time:
        payload["order_time"] = order_time
    result = _post("/orders/parse-structured", payload)
    if isinstance(result, str):
        return {"error": result}
    return result


@mcp.tool()
def create_order(
    xianyu_order_id: str = None,
    buyer_nickname: str = None,
    buyer_province: str = None,
    status: str = "pending_ship",
    order_time: str = None,
    total_amount: float = 0,
    discount: float = 0,
    actual_amount: float = 0,
    source: str = "image_import",
    notes: str = None,
    items: list[dict] = None,
) -> dict:
    """Create a new order in PrintFlow.

    Call this after confirming parsed order data with the user.
    Items should include product_id, product_name, quantity, unit_price from the parse result.

    Important:
    - Do NOT set shipping_fee, packaging_fee, service_fee — backend auto-calculates from settings.
    - material_cost: pass 0, backend snapshots from product automatically.
    - discount: total_amount - actual_amount (bargain amount).

    Args:
        xianyu_order_id: Xianyu order ID.
        buyer_nickname: Buyer nickname.
        buyer_province: Buyer province.
        status: Order status. Default: pending_ship.
        order_time: Order time in ISO format.
        total_amount: Original total amount.
        discount: Bargain/discount amount. Default: 0.
        actual_amount: Actual amount paid.
        source: Order source. Default: "image_import".
        notes: Optional notes.
        items: List of order items, each with product_id, product_name, quantity, unit_price, material_cost.

    Returns:
        Created order object with order_no, id, and all details.
    """
    payload = {
        "xianyu_order_id": xianyu_order_id,
        "buyer_nickname": buyer_nickname,
        "buyer_province": buyer_province,
        "status": status,
        "total_amount": total_amount,
        "discount": discount,
        "actual_amount": actual_amount,
        "source": source,
        "items": items or [],
    }
    if order_time:
        payload["order_time"] = order_time
    if notes:
        payload["notes"] = notes
    result = _post("/orders", payload)
    if isinstance(result, str):
        return {"error": result}
    return result


if __name__ == "__main__":
    mcp.run()
