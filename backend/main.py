import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.database import init_db
from backend.routers.colors import router as colors_router
from backend.routers.filaments import router as filaments_router
from backend.routers.products import router as products_router
from backend.routers.orders import router as orders_router
from backend.routers.inventories import router as inventories_router
from backend.routers.settings import router as settings_router
from backend.routers.logs import router as logs_router
from backend.routers.print_tasks import router as print_tasks_router
from backend.routers.buyers import router as buyers_router
from backend.routers.sales import router as sales_router
from backend.routers.admin import router as admin_router
from backend.middleware.logging_middleware import LoggingMiddleware
from backend.services.logger_service import log_business

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES_DIR = os.path.join(BASE_DIR, "data", "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

app = FastAPI(title="PrintFlow-3D", version="1.7.3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)

app.include_router(colors_router, prefix="/api")
app.include_router(filaments_router, prefix="/api")
app.include_router(products_router, prefix="/api")
app.include_router(orders_router, prefix="/api")
app.include_router(inventories_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(logs_router, prefix="/api")
app.include_router(print_tasks_router, prefix="/api")
app.include_router(buyers_router, prefix="/api")
app.include_router(sales_router, prefix="/api")
app.include_router(admin_router, prefix="/api")

app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")


@app.on_event("startup")
def on_startup():
    init_db()
    log_business("服务启动", "PrintFlow-3D", version="1.7.3")


@app.get("/api/health")
def health():
    return {"status": "ok"}
