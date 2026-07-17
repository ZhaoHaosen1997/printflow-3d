import re
import time
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from backend.models import Product
from backend.services.logger_service import log_parser, log_parser_warn


STATUS_MAP = {
    "待发货": "pending_ship",
    "已发货": "shipped",
    "交易成功": "completed",
}

# Pattern: status → 订单编号 → order number (whitespace-insensitive)
ORDER_HEADER_RE = re.compile(
    r"(待发货|已发货|交易成功)\s+订单编号\s+(\d{15,20})",
)


def parse_order_text(text: str) -> list[dict]:
    """Parse 闲鱼 order text into structured data using regex rules."""
    t0 = time.time()
    blocks = _split_blocks(text)
    results = []
    for block in blocks:
        order_data = _parse_single_block(block)
        if order_data and order_data.get("xianyu_order_id"):
            results.append(order_data)
    elapsed = (time.time() - t0) * 1000
    log_parser("解析完成", blocks=str(len(blocks)), results=str(len(results)),
               elapsed_ms=f"{elapsed:.0f}")
    return results


def _split_blocks(text: str) -> list[str]:
    """
    Split multi-order text into individual order blocks.
    Uses the order header pattern: status line → 订单编号 → order number.
    """
    text = text.strip()
    headers = list(ORDER_HEADER_RE.finditer(text))

    if len(headers) <= 1:
        return [text]

    blocks = []
    for i, h in enumerate(headers):
        start = h.start()
        if i + 1 < len(headers):
            end = headers[i + 1].start()
        else:
            end = len(text)
        blocks.append(text[start:end].strip())

    return blocks


def _parse_single_block(text: str) -> dict | None:
    """Parse a single order text block."""
    # Remove clutter
    clean = re.sub(r"点击复制|添加备注", "", text)

    # Status
    status = "pending_ship"
    for key, val in STATUS_MAP.items():
        if key in text:
            status = val
            break

    # Order number
    m = re.search(r"\b(\d{15,20})\b", clean)
    xianyu_order_id = m.group(1) if m else None

    # Order time: 下单时间 YYYY-MM-DD HH:MM:SS
    order_time = None
    m = re.search(r"下单时间\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", clean)
    if m:
        try:
            order_time = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

    # Product name inside 【...】
    product_name = None
    m = re.search(r"【(.+?)】", clean)
    if m:
        product_name = m.group(1).strip()

    # Fallback: product name without brackets (between 下单时间 and status/price)
    if not product_name:
        lines = clean.split("\n")
        capture = False
        for line in lines:
            s = line.strip()
            if not s:
                continue
            if "下单时间" in s:
                capture = True
                continue
            if capture:
                if re.match(r"^\d{15,20}$", s):
                    continue
                if s in ("待发货", "已发货", "交易成功") or s.startswith("¥") or s.startswith("×"):
                    break
                product_name = s
                break

    # Prices: collapse whitespace for reliable matching
    flat = re.sub(r"\s+", " ", clean)
    total_amount = Decimal("0")
    actual_amount = Decimal("0")
    quantity = 1

    m = re.search(r"¥\s*([\d.]+)\s*[xX×]\s*(\d+)\s*¥\s*([\d.]+)", flat)
    if m:
        total_amount = Decimal(m.group(1))
        quantity = int(m.group(2))
        actual_amount = Decimal(m.group(3))
    else:
        prices = re.findall(r"¥\s*([\d.]+)", flat)
        if len(prices) >= 2:
            total_amount = Decimal(prices[0])
            actual_amount = Decimal(prices[-1])
        elif len(prices) == 1:
            total_amount = Decimal(prices[0])
            actual_amount = Decimal(prices[0])

    shipping_free = "包邮" in text

    # Buyer info: extract from the portion of text AFTER price/shipping
    buyer_nickname = None
    buyer_name = None
    buyer_phone = None
    buyer_address = None
    buyer_province = None

    # Locate the "body end" — everything after the price+shipping line
    lines = text.split("\n")
    body_start = 0
    for i, line in enumerate(lines):
        s = line.strip()
        if re.search(r"包邮", s) or re.search(r"¥\s*[\d.]+\s*$", s):
            body_start = i + 1
            break

    # Also try parsing from flat text if line-based approach didn't find it
    if body_start == 0:
        m_body = re.search(r"包邮\s*\n+(.+)$", text, re.DOTALL)
        if m_body:
            body_text = m_body.group(1).strip()
        else:
            body_text = ""
    else:
        body_text = "\n".join(lines[body_start:]).strip()

    body_lines = [l.strip() for l in body_text.split("\n") if l.strip()]

    # Skip lines that are status, order labels, prices, etc.
    skip_re = re.compile(
        r"^(待发货|已发货|交易成功|订单编号|下单时间|点击复制|添加备注|"
        r"【|¥|包邮|\d{15,20})$"
    )
    buyer_lines = [l for l in body_lines if not skip_re.match(l)]

    if buyer_lines:
        # 1st meaningful line = buyer nickname (or nickname+name combined)
        buyer_nickname = buyer_lines[0]

        # Check remaining lines
        for line in buyer_lines[1:]:
            if _looks_like_address(line):
                buyer_address = line
                buyer_province = _extract_province(line)
            elif re.search(r"\d{11}", line):
                m_p = re.search(r"(\d{11})", line)
                if m_p:
                    buyer_phone = m_p.group(1)
                name_part = re.sub(r"\d{11}", "", line).strip()
                if _is_chinese_name(name_part):
                    buyer_name = name_part
            elif _is_chinese_name(line):
                buyer_name = line

        # Also check the nickname line for phone/name
        if not buyer_phone:
            m_p = re.search(r"(\d{11})", buyer_nickname)
            if m_p:
                buyer_phone = m_p.group(1)

    # Phone fallback: search entire text
    if not buyer_phone:
        m = re.search(r"(?<!\d)(1[3-9]\d{9})(?!\d)", text)
        if m:
            buyer_phone = m.group(1)

    return {
        "xianyu_order_id": xianyu_order_id,
        "status": status,
        "order_time": order_time,
        "product_name": product_name,
        "total_amount": total_amount,
        "actual_amount": actual_amount,
        "quantity": quantity,
        "buyer_nickname": buyer_nickname,
        "buyer_name": buyer_name,
        "buyer_phone": buyer_phone,
        "buyer_address": buyer_address,
        "buyer_province": buyer_province,
        "shipping_free": shipping_free,
    }


def _looks_like_address(text: str) -> bool:
    indicators = ["省", "市", "区", "县", "镇", "街道", "路", "号", "弄", "园", "期", "栋", "单元", "室"]
    return any(ind in text for ind in indicators) and len(text) > 8


def _is_chinese_name(text: str) -> bool:
    return bool(re.match(r"^[一-鿿]{2,4}$", text.strip()))


def _extract_province(text: str) -> str | None:
    m = re.match(r"([一-鿿]{2,3})(?:省|市)", text)
    if m:
        return m.group(1)
    for city in ["北京", "上海", "天津", "重庆"]:
        if city in text[:6]:
            return city
    return None


def match_products(db: Session, orders: list[dict]) -> list[dict]:
    """Fuzzy match product names and resolve bundle items."""
    products = db.query(Product).filter(
        Product.status == "active",
        Product.price_single > 0,
    ).all()
    results = []

    for order in orders:
        matched_product = None
        if order.get("product_name"):
            matched_product = _fuzzy_match(order["product_name"], products)

        result = {
            **order,
            "matched_product_id": matched_product.id if matched_product else None,
            "matched": matched_product is not None,
            "is_bundle": matched_product.category == "bundle" if matched_product else False,
            "bundle_items": None,
        }

        if matched_product and matched_product.category == "bundle" and matched_product.bundle_items:
            children_ids = matched_product.bundle_items
            children_products = {
                p.id: p for p in db.query(Product)
                .filter(Product.id.in_(children_ids))
                .all()
            }
            bundle_items = []
            for cid in children_ids:
                cp = children_products.get(cid)
                if cp:
                    bundle_items.append({
                        "product_id": cp.id,
                        "product_name": cp.name,
                        "quantity": 1,
                        "unit_price": float(cp.price_bundle),
                        "material_cost": float(cp.material_cost),
                        "matched": True,
                        "is_bundle": False,
                        "bundle_children": None,
                    })
            result["bundle_items"] = bundle_items

            if bundle_items:
                total_bundle_price = float(matched_product.price_single)
                result["total_amount"] = total_bundle_price
                actual = float(order["actual_amount"])
                result["discount"] = max(total_bundle_price - actual, 0)

        if result["matched"]:
            log_parser("商品匹配", xianyu_name=order.get("product_name", ""),
                       system_name=matched_product.name,
                       product_id=str(result["matched_product_id"]),
                       is_bundle=str(result["is_bundle"]))
        elif order.get("product_name"):
            log_parser_warn("未匹配商品", xianyu_name=order["product_name"])

        results.append(result)

    return results


def _fuzzy_match(name: str, products: list[Product]) -> Product | None:
    if not name:
        return None

    name_lower = name.lower()

    # ---- Phase 1: keyword scoring ----
    best_kw_product = None
    best_kw_score = 0
    for p in products:
        if not p.search_keywords:
            continue
        score = sum(1 for kw in p.search_keywords if kw.lower() in name_lower)
        if score > best_kw_score:
            best_kw_score = score
            best_kw_product = p
    if best_kw_score >= 1:
        log_parser("关键词命中", xianyu_name=name,
                   product_name=best_kw_product.name,
                   score=f"{best_kw_score}/{len(best_kw_product.search_keywords)}")
        return best_kw_product

    # ---- Phase 2: legacy fuzzy match ----
    valid = [p for p in products if p.name and p.name.strip()]

    for p in valid:
        if p.name == name:
            return p

    name_norm = re.sub(r"\s+", "", name).lower()
    for p in valid:
        if re.sub(r"\s+", "", p.name).lower() == name_norm:
            return p

    for p in valid:
        if len(p.name) >= 2 and (p.name in name or name in p.name):
            return p

    for p in valid:
        tokens = re.findall(r"[一-鿿\w]+", p.name)
        if len(tokens) >= 2:
            match_count = sum(1 for t in tokens if t.lower() in name.lower())
            if match_count >= len(tokens) * 0.6:
                return p

    return None
