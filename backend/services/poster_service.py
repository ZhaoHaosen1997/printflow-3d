import os
import base64
import mimetypes
from pathlib import Path
from decimal import Decimal

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from sqlalchemy.orm import Session

from backend.models import Product, Color
from backend.services.logger_service import log_business, log_error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IMAGES_DIR = os.path.join(BASE_DIR, "data", "images")
TEMPLATES_DIR = os.path.join(BASE_DIR, "backend", "templates", "posters")

CATEGORY_TITLES = {
    "counter": "诡镇奇谈 3D打印 计数器 合集",
    "token": "诡镇奇谈 3D打印 指示物 token合集",
    "other": "诡镇奇谈 3D打印 其他配件 合集",
}

CATEGORY_NOTICES = [
    "✅ 非偏远满30元包邮 | 1-5天发货",
    "✅ 3D打印存在层纹等正常瑕疵，完美主义慎拍",
    "✅ 款式与数量私聊确认后，改价下单",
]

BUNDLE_NOTICES = [
    "✅ 全套指示物一次配齐",
    "✅ 3D打印存在层纹等正常瑕疵，完美主义慎拍",
]

FOOTER_LINES = [
    "本链接持续更新新品",
    "下单前可咨询款式与发货时间",
]

jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=True,
)


def _image_to_base64(filename: str) -> str | None:
    if not filename:
        return None
    filepath = os.path.join(IMAGES_DIR, filename)
    if not os.path.isfile(filepath):
        return None
    mime_type, _ = mimetypes.guess_type(filepath)
    if not mime_type:
        mime_type = "image/png"
    with open(filepath, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


def _resolve_colors(product: Product, db: Session) -> list[dict]:
    colors_data = product.colors
    if not colors_data:
        return []

    if isinstance(colors_data, dict):
        colors_data = [colors_data]

    result = []
    for color_entry in colors_data:
        color_type = color_entry.get("type", "")
        if color_type == "固定":
            color_set_id = color_entry.get("colorSetId", "")
            label = color_entry.get("label", "")
            swatches = color_entry.get("swatches", [])
            result.append({
                "type": "fixed",
                "label": f"固定配色：{label}" if label else "固定配色",
                "color_items": [{"name": label, "swatches": swatches}],
            })
        elif color_type == "可选":
            optional_ids = color_entry.get("optionalColorSetIds", [])
            default_id = color_entry.get("defaultColorSetId", "")
            label = color_entry.get("label", "")
            items = []
            for cid in optional_ids:
                color_obj = db.query(Color).filter(Color.color_id == cid).first()
                if color_obj:
                    is_default = cid == default_id
                    items.append({
                        "name": color_obj.name + ("（默认）" if is_default else ""),
                        "swatches": color_obj.swatches or [],
                        "is_default": is_default,
                    })
            if not items:
                swatches = color_entry.get("swatches", [])
                items.append({"name": label, "swatches": swatches, "is_default": False})
            result.append({
                "type": "optional",
                "label": label or "可选配色",
                "color_items": items,
            })

    return result


def _build_product_data(product: Product, db: Session, show_price: bool = True) -> dict:
    image_b64 = _image_to_base64(product.image) if product.image else None
    colors = _resolve_colors(product, db)
    contents = product.contents or []

    data = {
        "name": product.name,
        "image_b64": image_b64,
        "colors": colors,
        "contents": contents,
    }
    if show_price:
        price = product.price_bundle if product.price_bundle and product.price_bundle > 0 else product.price_single
        if isinstance(price, Decimal):
            price = float(price)
        data["price"] = price
    return data


def get_category_poster_data(db: Session, category: str) -> dict:
    if category not in CATEGORY_TITLES:
        raise ValueError(f"Invalid category: {category}")

    products = (
        db.query(Product)
        .filter(Product.category == category, Product.status == "active")
        .order_by(Product.sort_order, Product.id)
        .all()
    )

    product_list = [_build_product_data(p, db, show_price=True) for p in products]

    return {
        "title": CATEGORY_TITLES[category],
        "notices": CATEGORY_NOTICES,
        "products": product_list,
        "footer_lines": FOOTER_LINES,
        "is_bundle": False,
    }


def get_bundle_poster_data(db: Session, product_id: int) -> dict:
    bundle = db.query(Product).filter(Product.id == product_id).first()
    if not bundle or bundle.category != "bundle":
        raise ValueError(f"Product {product_id} is not a bundle")

    bundle_items_ids = bundle.bundle_items or []
    sub_products = []
    unit_total = Decimal("0")

    for item_id in bundle_items_ids:
        sub = db.query(Product).filter(Product.id == item_id, Product.status == "active").first()
        if sub:
            sub_products.append(_build_product_data(sub, db, show_price=False))
            price = sub.price_bundle if sub.price_bundle and sub.price_bundle > 0 else sub.price_single
            if price:
                unit_total += price

    bundle_price = bundle.price_single or Decimal("0")
    savings = unit_total - bundle_price

    return {
        "title": bundle.name,
        "bundle_price": float(bundle_price),
        "unit_total": float(unit_total),
        "savings": float(savings),
        "notices": BUNDLE_NOTICES,
        "products": sub_products,
        "footer_lines": FOOTER_LINES,
        "is_bundle": True,
    }


def render_poster_html(data: dict, template: str = "parchment", width: int = 750) -> str:
    if template == "dark-gold":
        tpl_name = "bundle-poster.html" if data.get("is_bundle") else "category-poster.html"
    else:
        tpl_name = "bundle-poster.html" if data.get("is_bundle") else "category-poster.html"

    tpl = jinja_env.get_template(tpl_name)
    return tpl.render(
        **data,
        theme=template,
        width=width,
    )


def html_to_png(html_content: str, width: int = 750) -> bytes:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 800})
        page.set_content(html_content, wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        body = page.query_selector("body")
        png_bytes = body.screenshot(type="png")
        browser.close()
    return png_bytes


def generate_category_poster(db: Session, category: str, template: str = "parchment", width: int = 750, preview: bool = False):
    data = get_category_poster_data(db, category)
    html_content = render_poster_html(data, template, width)
    log_business("生成分类长图", poster_category=category, template=template)

    if preview:
        return html_content

    return html_to_png(html_content, width)


def generate_bundle_poster(db: Session, product_id: int, template: str = "parchment", width: int = 750, preview: bool = False):
    data = get_bundle_poster_data(db, product_id)
    html_content = render_poster_html(data, template, width)
    log_business("生成合集长图", bundle_id=product_id, template=template)

    if preview:
        return html_content

    return html_to_png(html_content, width)
