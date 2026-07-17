from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response, HTMLResponse
from sqlalchemy.orm import Session
from urllib.parse import quote

from backend.database import get_db
from backend.services import poster_service

router = APIRouter(prefix="/posters", tags=["posters"])


@router.get("/category")
def generate_category_poster(
    category: str = Query(..., description="分类: counter | token | other"),
    template: str = Query("parchment", description="模板: parchment | dark-gold"),
    width: int = Query(750, description="图片宽度"),
    preview: bool = Query(False, description="预览模式，返回HTML"),
    db: Session = Depends(get_db),
):
    if category not in poster_service.CATEGORY_TITLES:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}. Must be one of: counter, token, other")
    if template not in ("parchment", "dark-gold"):
        raise HTTPException(status_code=400, detail=f"Invalid template: {template}. Must be parchment or dark-gold")

    try:
        result = poster_service.generate_category_poster(db, category, template, width, preview)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if preview:
        return HTMLResponse(content=result)

    title = poster_service.CATEGORY_TITLES[category]
    filename = f"{title}-poster.png"
    encoded_filename = quote(filename)
    return Response(
        content=result,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )


@router.get("/bundle/{product_id}")
def generate_bundle_poster(
    product_id: int,
    template: str = Query("parchment", description="模板: parchment | dark-gold"),
    width: int = Query(750, description="图片宽度"),
    preview: bool = Query(False, description="预览模式，返回HTML"),
    db: Session = Depends(get_db),
):
    if template not in ("parchment", "dark-gold"):
        raise HTTPException(status_code=400, detail=f"Invalid template: {template}. Must be parchment or dark-gold")

    try:
        result = poster_service.generate_bundle_poster(db, product_id, template, width, preview)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if preview:
        return HTMLResponse(content=result)

    from backend.models import Product
    bundle = db.query(Product).filter(Product.id == product_id).first()
    filename = f"{bundle.name}-poster.png" if bundle else "bundle-poster.png"
    encoded_filename = quote(filename)
    return Response(
        content=result,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )


@router.get("/bundles")
def list_bundles(db: Session = Depends(get_db)):
    from backend.models import Product
    bundles = (
        db.query(Product)
        .filter(Product.category == "bundle", Product.status == "active")
        .all()
    )
    return [
        {"id": b.id, "name": b.name, "price": float(b.price_single) if b.price_single else 0}
        for b in bundles
    ]
