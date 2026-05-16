"""PrintFlow-3D 日志服务

日志写入 data/logs/app.log，按 5MB 滚动，保留 10 个历史文件。
同时输出到控制台（stdout），方便 uvicorn 日志聚合。

用法:
    from backend.services.logger_service import log_business, log_parser, log_db, log_error, logger
    log_business("订单状态变更", f"待发货→已发货", order_no="ORD-20260516-001")
"""

import logging
import os
from logging.handlers import RotatingFileHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(BASE_DIR, "data", "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")

os.makedirs(LOG_DIR, exist_ok=True)

# ---- Formatter ----
# 2026-05-16 15:30:00  INFO     API      GET /api/orders 200 12ms
LOG_FORMAT = "%(asctime)s  %(levelname)-8s  %(category)-8s  %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class _CategoryFilter(logging.Filter):
    """Inject a default category if not set on the record."""
    def filter(self, record):
        if not hasattr(record, "category"):
            record.category = "SYSTEM"
        return True


class _PlainFormatter(logging.Formatter):
    """Standard formatter with category support."""
    def format(self, record):
        if not hasattr(record, "category"):
            record.category = "SYSTEM"
        return super().format(record)


# ---- Logger Setup ----
logger = logging.getLogger("printflow")
logger.setLevel(logging.DEBUG)

# File handler (Rotating: 5 MB × 10 files)
fh = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=10, encoding="utf-8")
fh.setLevel(logging.DEBUG)
fh.setFormatter(_PlainFormatter(LOG_FORMAT, DATE_FORMAT))
fh.addFilter(_CategoryFilter())
logger.addHandler(fh)

# Console handler
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(_PlainFormatter(LOG_FORMAT, DATE_FORMAT))
ch.addFilter(_CategoryFilter())
logger.addHandler(ch)

# Prevent propagation to root logger
logger.propagate = False

# ---- Convenience Functions ----


def _log(level: int, category: str, msg: str, **kwargs):
    """Internal: emit a log record with structured k=v extras."""
    extra = {"category": category}
    parts = [msg]
    for k, v in kwargs.items():
        parts.append(f"{k}={v}")
    logger.log(level, "  ".join(parts), extra=extra)


def log_api(method: str, path: str, status: int, duration_ms: float, **kwargs):
    """API 请求/响应日志。"""
    cat = "API"
    if status >= 500:
        level = logging.ERROR
    elif status >= 400:
        level = logging.WARNING
    else:
        level = logging.INFO
    _log(level, cat, f"{method} {path} {status} {duration_ms:.0f}ms", **kwargs)


def log_business(action: str, target: str = "", detail: str = "", **kwargs):
    """核心业务操作日志。"""
    msg = action
    if target:
        msg += f"  {target}"
    if detail:
        msg += f"  {detail}"
    _log(logging.INFO, "BUSINESS", msg, **kwargs)


def log_parser(action: str, **kwargs):
    """粘贴导入解析日志。"""
    _log(logging.INFO, "PARSER", action, **kwargs)


def log_parser_warn(action: str, **kwargs):
    """解析警告（如未匹配商品）。"""
    _log(logging.WARNING, "PARSER", action, **kwargs)


def log_db(action: str, detail: str = "", **kwargs):
    """数据库操作日志。"""
    msg = action
    if detail:
        msg += f"  {detail}"
    _log(logging.INFO, "DB", msg, **kwargs)


def log_error(source: str, error_msg: str, **kwargs):
    """系统错误日志。"""
    _log(logging.ERROR, "ERROR", f"{source}  {error_msg}", **kwargs)
