import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("printflow")

API_BASE = "http://localhost:8848/api"
TIMEOUT = 30.0

# Order status keys → Chinese labels (kept in sync with backend.models.ORDER_STATUS)
ORDER_STATUS = {
    "pending_ship": "待发货",
    "shipped": "已发货",
    "completed": "交易成功",
    "cancelled": "已取消",
    "returned": "退货",
    "archived": "已归档",
}
# Reverse lookup: Chinese label / alias → canonical key
STATUS_ALIASES = {
    "待发货": "pending_ship",
    "已发货": "shipped",
    "交易成功": "completed",
    "已完成": "completed",
    "完成": "completed",
    "已取消": "cancelled",
    "取消": "cancelled",
    "退货": "returned",
    "已归档": "archived",
    "归档": "archived",
    "pending_ship": "pending_ship",
    "shipped": "shipped",
    "completed": "completed",
    "cancelled": "cancelled",
    "returned": "returned",
    "archived": "archived",
}
for k, label in ORDER_STATUS.items():
    STATUS_ALIASES[label] = k

# Statuses that are NOT finished/archived (awaiting action)
ACTIVE_STATUSES = {"pending_ship", "shipped"}


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


def _put(path: str, json: dict = None) -> dict | list | str:
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.put(f"{API_BASE}{path}", json=json or {})
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


def _normalize_status(status: str) -> str | None:
    """Normalize a user-supplied status (English key or Chinese label) to its key.

    Returns the canonical key, or None when the value is not recognized.
    """
    if not status:
        return None
    key = STATUS_ALIASES.get(str(status).strip())
    return key if key else None


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


@mcp.tool()
def list_unfinished_orders(status: str = None, limit: int = 50, offset: int = 0) -> dict:
    """List all unfinished (non-terminal) orders for status handling.

    "Unfinished" means orders still awaiting action — status in
    (pending_ship 待发货, shipped 已发货). Archived / completed / cancelled /
    returned orders are excluded. Returns a compact list ordered newest-first.

    Args:
        status: Optional filter. Accepts English key ("pending_ship",
            "shipped") or Chinese label ("待发货", "已发货"). If omitted,
            lists all unfinished orders.
        limit: Max number of orders to return. Default 50, max 200.
        offset: Pagination offset. Default 0.

    Returns:
        A dict with "items" (list of compact order objects) and "total".
        Each item has id, order_no, status, status_label, buyer_nickname,
        order_time, actual_amount, and item summary.
    """
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))

    status_key = _normalize_status(status) if status else None
    if status and not status_key:
        return {
            "error": f"未知状态: {status}。有效值: {', '.join(ORDER_STATUS)} 或中文(待发货/已发货/交易成功/已取消/退货/已归档)"
        }
    if status_key and status_key not in ACTIVE_STATUSES:
        return {
            "error": f"状态 '{status}' 不属于待处理(未完成)范围。未完成订单仅含: 待发货(pending_ship)、已发货(shipped)"
        }

    params = {"status": status_key} if status_key else {}
    params["limit"] = limit
    params["offset"] = offset
    result = _get("/orders", params)
    if isinstance(result, str):
        return {"error": result}

    items = []
    for o in result.get("items", []):
        o_status = o.get("status")
        # Belt-and-suspenders: skip anything that is actually terminal
        if o_status not in ACTIVE_STATUSES:
            continue
        items.append({
            "id": o["id"],
            "order_no": o["order_no"],
            "status": o_status,
            "status_label": ORDER_STATUS.get(o_status, o_status),
            "buyer_nickname": o.get("buyer_nickname"),
            "order_time": o.get("order_time"),
            "actual_amount": o.get("actual_amount"),
            "source": o.get("source"),
            "items": [
                {
                    "product_name": oi.get("product_name"),
                    "quantity": oi.get("quantity"),
                }
                for oi in o.get("items", [])
            ],
        })
    return {"items": items, "total": result.get("total")}


@mcp.tool()
def update_order_status(order_id: int, status: str, reason: str = None) -> dict:
    """Change the status of an existing order.

    Backend auto-handles side effects: setting completed_time when entering a
    terminal status, restoring inventory when cancelled/returned, re-deducting
    inventory when reactivating, and buyer stats sync. Archiving is not allowed.

    Args:
        order_id: The order ID (required).
        status: Target status. Accepts English key or Chinese label:
            pending_ship 待发货, shipped 已发货, completed 交易成功,
            cancelled 已取消, returned 退货. ("archived" 已归档 is NOT allowed.)
        reason: Optional note appended to the order's notes field.

    Returns:
        Updated order object with id, order_no, status, completed_time and
        other key fields. Returns an error dict on failure.
    """
    status_key = _normalize_status(status)
    if not status_key:
        return {
            "error": f"未知状态: {status}。有效值: {', '.join(k for k in ORDER_STATUS if k != 'archived')} 或中文(待发货/已发货/交易成功/已取消/退货)"
        }
    if status_key == "archived":
        return {"error": "不允许将订单归档，请选择其他状态。未完成订单可改为: 已发货(发货)、交易成功(完成)、已取消、退货。"}

    payload = {"status": status_key}
    result = _put(f"/orders/{int(order_id)}", payload)
    if isinstance(result, str):
        return {"error": result}

    if reason:
        old_notes = result.get("notes") or ""
        new_notes = f"{old_notes}\n[状态变更] {reason}".strip()
        updated = _put(f"/orders/{int(order_id)}", {"notes": new_notes})
        if not isinstance(updated, str):
            result = updated

    return {
        "id": result["id"],
        "order_no": result["order_no"],
        "status": result.get("status"),
        "status_label": ORDER_STATUS.get(result.get("status"), result.get("status")),
        "completed_time": result.get("completed_time"),
        "buyer_nickname": result.get("buyer_nickname"),
        "actual_amount": result.get("actual_amount"),
        "notes": result.get("notes"),
        "message": f"订单 {result.get('order_no')} 状态已更新为 {ORDER_STATUS.get(result.get('status'), result.get('status'))}",
    }


if __name__ == "__main__":
    mcp.run()
