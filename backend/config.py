"""集中路径与环境配置。

只依赖标准库，可被 backend 任何模块安全导入（无循环依赖风险）。
路径统一在此推导，禁止在各模块重复 os.path.dirname 链。
"""

import os

# 仓库根目录（backend/config.py 的上两级）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "data")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend", "dist")

# CORS：默认覆盖本机开发与内网生产访问地址，可用环境变量覆盖
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:18848,http://192.168.10.20:8848",
).split(",")
