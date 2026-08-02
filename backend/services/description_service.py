from decimal import Decimal
from sqlalchemy.orm import Session

from backend.models import Product, Color, Category, product_games
from backend.services.logger_service import log_business

GAME_FALLBACK = "诡镇奇谈"

# 分类 slug -> 闲鱼商品图位置引用
CATEGORY_IMAGE_MAP = {
    "token": 7,
    "counter": 8,
    "other": 9,
}

# ===== 固定合集（Token合集包）静态文案 =====
FIXED_BUNDLE = {
    "title": "【{game} token合集】3D打印桌游 指示物 合集",
    "price_line": "价格：¥{price}（比单买合算，非偏远包邮）",
    "contents_header": " 包含内容：",
    "colors_header": " 配色说明：",
    "notices_header": " 购买须知：",
    "notices": [
        "1. 3D打印存在层纹等正常瑕疵，完美主义慎拍",
        "2. 下单前请私聊确认款式与配色，直接拍下按默认配色发货",
        "3. 2-5天发货，非偏远地区包邮",
        "4. 支持个性化调整：包内配件可根据需求增减，私聊沟通后改价下单",
    ],
    "tags": "#诡镇奇谈 #ArkhamHorror #桌游配件 #3D打印 #克苏鲁",
}

# ===== 自选合集静态文案 =====
CUSTOM_BUNDLE = {
    "title": "{game} 3D打印 Token 打包链接",
    "shipping_line": "本链接满 30元 非偏远地区包邮，拍下后现打现发。",
    "ship_header": " 发货说明",
    "ship_text": "下单后根据订单量预计 1~5天 发货。下单前请先私信确认和改价，感谢理解。",
    "print_header": " 关于3D打印",
    "print_text": "层纹和表面轻微不平整是工艺特质，无法完全避免，完美主义朋友请慎拍，介意慎拍。",
}


def _fmt_price(value) -> str:
    """39.0 -> '39'; 12.5 -> '12.5'"""
    if value is None:
        return "0"
    f = float(value)
    return str(int(f)) if f == int(f) else f"{f:g}"


def _game_name(product: Product) -> str:
    if product.games:
        return product.games[0].name
    return GAME_FALLBACK


def _short_name(name: str) -> str:
    for suffix in ("指示物",):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _sort_key(p: Product):
    return (p.sort_order if p.sort_order is not None else 0, p.id)


def _resolve_optional_colors(db: Session, color_entry: dict) -> dict:
    names = []
    for cid in color_entry.get("optionalColorSetIds", []):
        c = db.query(Color).filter(Color.color_id == cid).first()
        names.append(c.name if c else cid)
    default_cid = color_entry.get("defaultColorSetId", "")
    default_name = None
    if default_cid:
        c = db.query(Color).filter(Color.color_id == default_cid).first()
        default_name = c.name if c else default_cid
    return {"names": names, "default": default_name}


def _ordered_subs(db: Session, bundle: Product) -> list[Product]:
    sub_ids = bundle.bundle_items or []
    subs = {p.id: p for p in db.query(Product).filter(Product.id.in_(sub_ids)).all()}
    ordered = [subs[i] for i in sub_ids if i in subs]
    ordered.sort(key=_sort_key)
    return ordered


def generate_fixed_bundle_description(db: Session, bundle: Product) -> str:
    ordered = _ordered_subs(db, bundle)
    game = _game_name(bundle)

    lines = []
    lines.append(FIXED_BUNDLE["title"].format(game=game))
    lines.append(FIXED_BUNDLE["price_line"].format(price=_fmt_price(bundle.price_single)))
    lines.append("")
    lines.append(FIXED_BUNDLE["contents_header"])

    for sub in ordered:
        contents = sub.contents or []
        if len(contents) >= 2:
            lines.append("✦ {}（内容包含：{}）".format(sub.name, "、".join(contents)))
        elif len(contents) == 1:
            item = contents[0]
            if item.startswith(sub.name):
                item = item[len(sub.name):].strip()
            lines.append("✦ {}{}".format(sub.name, (" " + item) if item else ""))
        else:
            lines.append("✦ {}".format(sub.name))

    lines.append("")
    lines.append(FIXED_BUNDLE["colors_header"])
    fixed_names = []
    for sub in ordered:
        colors = sub.colors
        if not colors or not isinstance(colors, dict):
            continue
        if colors.get("type") == "可选":
            info = _resolve_optional_colors(db, colors)
            default_part = "（默认{}）".format(info["default"]) if info["default"] else ""
            lines.append("• {}：{}可选{}".format(sub.name, "/".join(info["names"]), default_part))
        else:
            fixed_names.append(sub.name)
    if fixed_names:
        lines.append("• {}：固定配色".format("/".join(fixed_names)))

    lines.append("")
    lines.append(FIXED_BUNDLE["notices_header"])
    lines.extend(FIXED_BUNDLE["notices"])

    lines.append("")
    lines.append("{}全套指示物一次搞定！{} 全包含".format(
        game,
        "、".join(_short_name(s.name) for s in ordered),
    ))
    lines.append("")
    lines.append(FIXED_BUNDLE["tags"])
    return "\n".join(lines)


def generate_custom_bundle_description(db: Session, bundle: Product) -> str:
    game_ids = [g.id for g in bundle.games]
    products = (
        db.query(Product)
        .join(product_games)
        .filter(
            product_games.c.game_id.in_(game_ids),
            Product.status == "active",
            Product.category != "bundle",
        )
        .all()
    )

    groups = {}
    for p in products:
        groups.setdefault(p.category, []).append(p)
    for lst in groups.values():
        lst.sort(key=_sort_key)

    cats = {c.slug: c for c in db.query(Category).all()}
    cat_order = sorted(
        cats.items(),
        key=lambda kv: (kv[1].sort_order if kv[1].sort_order is not None else 0, kv[1].id),
    )
    order = {slug: idx for idx, (slug, _) in enumerate(cat_order)}

    lines = []
    lines.append(CUSTOM_BUNDLE["title"].format(game=_game_name(bundle)))
    lines.append("")
    lines.append(CUSTOM_BUNDLE["shipping_line"])
    lines.append("")
    lines.append(CUSTOM_BUNDLE["ship_header"])
    lines.append(CUSTOM_BUNDLE["ship_text"])
    lines.append("")
    lines.append(CUSTOM_BUNDLE["print_header"])
    lines.append(CUSTOM_BUNDLE["print_text"])
    lines.append("")

    for slug in sorted(groups.keys(), key=lambda s: order.get(s, 999)):
        img = CATEGORY_IMAGE_MAP.get(slug, "")
        title = cats[slug].name if slug in cats else slug
        header = " {}类".format(title)
        if img:
            header += "（详细规格见商品图{}）".format(img)
        lines.append(header)
        for p in groups[slug]:
            price = p.price_bundle if p.price_bundle and p.price_bundle > 0 else p.price_single
            lines.append("- {}：{}元".format(p.name, _fmt_price(price)))
        lines.append("")

    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def generate_bundle_description(db: Session, product_id: int) -> str:
    bundle = db.query(Product).filter(Product.id == product_id).first()
    if not bundle or bundle.category != "bundle":
        raise ValueError("该商品不是合集，无法生成介绍")

    if bundle.bundle_items:
        text = generate_fixed_bundle_description(db, bundle)
        log_business("生成商品介绍", bundle.name, detail="固定合集", bundle_id=bundle.id)
    else:
        text = generate_custom_bundle_description(db, bundle)
        log_business("生成商品介绍", bundle.name, detail="自选合集", bundle_id=bundle.id)
    return text
