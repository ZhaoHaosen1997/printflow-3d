import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Color
from backend.schemas import ColorCreate, ColorUpdate, ColorResponse, MessageResponse

router = APIRouter(prefix="/colors", tags=["colors"])

# Chinese → English color name mapping
CN_MAP = {
    "黑色": "black", "白色": "white", "灰色": "gray", "银色": "silver",
    "金色": "gold", "红色": "red", "蓝色": "blue", "紫色": "purple",
    "黄色": "yellow", "青铜色": "bronze", "橙色": "orange",
    "亮金色": "brightgold", "深紫色": "deeppurple",
    "绿色": "green", "深绿色": "darkgreen",
    "黑金": "blackgold", "黑银": "blacksilver",
    "白红蓝": "whiteredblue", "白红": "whitered",
    "紫白": "purplewhite",
    "亮金-金-银": "brightgold-gold-silver",
    "金-银-青铜": "gold-silver-bronze",
}

# Tokenized Chinese color-name components (longest match first)
_CN_COLOR_TOKENS = {
    # ===== 多字组合词 =====
    "婴儿蓝": "babyblue",
    "半透明": "translucent",
    "大理石": "marble",
    "樱花粉": "sakurapink",
    "樱花": "sakura",
    "荧光": "neon",
    "透明": "transparent",
    "金属": "metallic",
    "磨砂": "matte",
    "哑光": "matte",
    "珠光": "pearl",
    "丝绸": "silk",
    "渐变": "gradient",
    "混色": "mixed",
    "星空": "starry",
    "极光": "aurora",
    "炫彩": "iridescent",
    "幻彩": "iridescent",
    # ===== 常用双字颜色 =====
    "黑金": "blackgold",
    "黑银": "blacksilver",
    "青铜": "bronze",
    "古铜": "copper",
    "香槟": "champagne",
    "天蓝": "skyblue",
    "海蓝": "seablue",
    "湖蓝": "lakeblue",
    "冰蓝": "iceblue",
    "雾蓝": "mistblue",
    "藏青": "navy",
    "浅蓝": "lightblue",
    "深蓝": "darkblue",
    "薄荷": "mint",
    "翠绿": "emerald",
    "草绿": "grassgreen",
    "军绿": "militarygreen",
    "墨绿": "darkgreen",
    "浅绿": "lightgreen",
    "黄绿": "yellowgreen",
    "青绿": "teal",
    "蓝绿": "bluegreen",
    "深绿": "darkgreen",
    "酒红": "winered",
    "玫红": "rosered",
    "桃红": "peachpink",
    "粉红": "pink",
    "橙红": "orangered",
    "朱红": "vermillion",
    "暗红": "darkred",
    "砖红": "brickred",
    "棕红": "brownred",
    "品红": "magenta",
    "紫红": "purplered",
    "酱紫": "maroon",
    "浅紫": "lightpurple",
    "深紫": "deeppurple",
    "金黄": "golden",
    "亮金": "brightgold",
    "暗金": "darkgold",
    "亮银": "brightsilver",
    "银灰": "silvergray",
    "钛灰": "titaniumgray",
    "太空灰": "spacegray",
    "石墨": "graphite",
    "炭黑": "carbonblack",
    "纯黑": "pureblack",
    "纯白": "purewhite",
    "雪白": "snowwhite",
    "米白": "ivory",
    "奶白": "cream",
    "米色": "beige",
    "咖啡": "coffee",
    "卡其": "khaki",
    "驼色": "camel",
    "琥珀": "amber",
    "玫瑰": "rose",
    "珊瑚": "coral",
    "松石": "turquoise",
    "蜂蜜": "honey",
    "果冻": "jelly",
    "牛奶": "milky",
    "奶油": "cream",
    "木纹": "wood",
    # ===== 水果/景物前缀 =====
    "苹果": "apple",
    "柠檬": "lemon",
    "草莓": "strawberry",
    "葡萄": "grape",
    "巧克力": "chocolate",
    "天空": "sky",
    "海洋": "ocean",
    "森林": "forest",
    "沙漠": "desert",
    "大地": "earth",
    # ===== 单字 =====
    "黑": "black", "白": "white", "灰": "gray", "银": "silver",
    "金": "gold", "红": "red", "蓝": "blue", "紫": "purple",
    "黄": "yellow", "绿": "green", "橙": "orange", "棕": "brown",
    "青": "cyan", "粉": "pink", "铜": "bronze", "褐": "tan",
    "米": "beige", "玫": "rose", "墨": "ink",
    "深": "dark", "亮": "bright", "浅": "light",
}
_CN_TOKENS_SORTED = sorted(_CN_COLOR_TOKENS.items(), key=lambda kv: len(kv[0]), reverse=True)


def _translate_name(name: str) -> str:
    """Translate Chinese color name to English. Returns lowercase ASCII slug."""
    if name in CN_MAP:
        return CN_MAP[name]

    parts = []
    i = 0
    while i < len(name):
        matched = False
        for tok, en in _CN_TOKENS_SORTED:
            if name.startswith(tok, i):
                parts.append(en)
                i += len(tok)
                matched = True
                break
        if not matched:
            ch = name[i]
            if ch in "-_ ":
                parts.append(ch)
            i += 1

    slug = "".join(parts)
    slug = re.sub(r"[^a-zA-Z0-9\-_]", "", slug).strip("-_").lower()
    if slug:
        return slug
    # Last resort: use a hash-based id
    import hashlib
    h = hashlib.md5(name.encode()).hexdigest()[:8]
    return f"color-{h}"


def _generate_color_id(db: Session, name: str) -> str:
    """Generate unique color_id from Chinese name."""
    base = _translate_name(name)
    cand = base
    n = 2
    while db.query(Color).filter(Color.color_id == cand).first():
        cand = f"{base}{n}"
        n += 1
    return cand


def _resolve_combo_swatches(db: Session, combo_of: list[str]) -> list[str]:
    """Compute swatches for a combo color from its referenced standard colors."""
    swatches = []
    for cid in combo_of:
        ref = db.query(Color).filter(Color.color_id == cid, Color.type == "standard").first()
        if not ref:
            raise HTTPException(400, f"引用的标准色 '{cid}' 不存在")
        swatches.extend(ref.swatches)
    return swatches


@router.get("", response_model=list[ColorResponse])
def list_colors(db: Session = Depends(get_db)):
    return db.query(Color).order_by(Color.type, Color.name).all()


@router.post("", response_model=ColorResponse, status_code=201)
def create_color(data: ColorCreate, db: Session = Depends(get_db)):
    color_id = _generate_color_id(db, data.name)

    if data.type == "combo":
        if not data.combo_of:
            raise HTTPException(400, "组合色必须填写 combo_of")
        payload = data.model_dump()
        payload["combo_of"] = list(data.combo_of)
        payload["swatches"] = _resolve_combo_swatches(db, payload["combo_of"])
    else:
        payload = data.model_dump()

    color = Color(color_id=color_id, **payload)
    db.add(color)
    db.commit()
    db.refresh(color)
    return color


@router.get("/{color_id}", response_model=ColorResponse)
def get_color(color_id: int, db: Session = Depends(get_db)):
    color = db.query(Color).filter(Color.id == color_id).first()
    if not color:
        raise HTTPException(404, "颜色不存在")
    return color


@router.put("/{color_id}", response_model=ColorResponse)
def update_color(color_id: int, data: ColorUpdate, db: Session = Depends(get_db)):
    color = db.query(Color).filter(Color.id == color_id).first()
    if not color:
        raise HTTPException(404, "颜色不存在")

    update_data = data.model_dump(exclude_unset=True)

    new_type = update_data.get("type", color.type)
    if new_type == "combo":
        combo_of = list(update_data.get("combo_of", color.combo_of or []))
        if not combo_of:
            raise HTTPException(400, "组合色必须填写 combo_of")
        update_data["combo_of"] = combo_of
        update_data["swatches"] = _resolve_combo_swatches(db, combo_of)

    for key, value in update_data.items():
        setattr(color, key, value)

    db.commit()
    db.refresh(color)
    return color


@router.delete("/{color_id}", response_model=MessageResponse)
def delete_color(color_id: int, db: Session = Depends(get_db)):
    color = db.query(Color).filter(Color.id == color_id).first()
    if not color:
        raise HTTPException(404, "颜色不存在")
    db.delete(color)
    db.commit()
    return MessageResponse(message=f"颜色 '{color.name}' 已删除")
