from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import init_db
from backend.routers.colors import router as colors_router
from backend.routers.filaments import router as filaments_router
from backend.routers.products import router as products_router

app = FastAPI(title="PrintFlow-3D", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(colors_router, prefix="/api")
app.include_router(filaments_router, prefix="/api")
app.include_router(products_router, prefix="/api")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}
