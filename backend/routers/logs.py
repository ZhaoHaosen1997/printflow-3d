"""日志查询 API。"""

import os
import re
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from backend.services.logger_service import LOG_DIR, LOG_FILE

router = APIRouter(prefix="/logs", tags=["logs"])

LOG_LINE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+"
    r"(\w+)\s+"
    r"(\w+)\s+"
    r"(.+)$"
)


class LogEntry(BaseModel):
    time: str
    level: str
    category: str
    message: str


class LogInfo(BaseModel):
    file_path: str
    size_bytes: int
    size_mb: float
    backup_count: int
    total_entries: int


def _read_all_log_files() -> list[str]:
    """Read app.log + app.log.N rotated files, return lines newest first."""
    files = [LOG_FILE]
    for i in range(1, 20):
        rf = f"{LOG_FILE}.{i}"
        if os.path.exists(rf):
            files.append(rf)
        else:
            break
    lines = []
    for fp in reversed(files):  # oldest rotated file first
        try:
            with open(fp, "r", encoding="utf-8") as f:
                lines.extend(f.readlines())
        except OSError:
            continue
    # Reverse so newest entries first
    lines.reverse()
    return lines


def _parse_line(line: str) -> LogEntry | None:
    m = LOG_LINE_RE.match(line.strip())
    if not m:
        return None
    return LogEntry(time=m.group(1), level=m.group(2), category=m.group(3), message=m.group(4))


@router.get("", response_model=list[LogEntry])
def list_logs(
    level: str | None = Query(None, description="逗号分隔级别，如 ERROR,WARNING"),
    category: str | None = Query(None, description="逗号分隔分类，如 API,BUSINESS"),
    keyword: str | None = Query(None, description="关键词搜索"),
    date: str | None = Query(None, description="日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=10, le=1000),
):
    """查询日志，支持筛选和分页。"""
    raw_lines = _read_all_log_files()

    level_set = set(level.upper().split(",")) if level else None
    cat_set = set(category.upper().split(",")) if category else None

    entries: list[LogEntry] = []
    for line in raw_lines:
        entry = _parse_line(line)
        if not entry:
            continue
        if level_set and entry.level not in level_set:
            continue
        if cat_set and entry.category not in cat_set:
            continue
        if keyword and keyword.lower() not in entry.message.lower():
            continue
        if date and not entry.time.startswith(date):
            continue
        entries.append(entry)

    start = (page - 1) * page_size
    return entries[start : start + page_size]


@router.get("/info", response_model=LogInfo)
def log_info():
    """日志文件信息。"""
    total = 0
    size = 0
    files = [LOG_FILE]
    for i in range(1, 20):
        rf = f"{LOG_FILE}.{i}"
        if os.path.exists(rf):
            files.append(rf)
        else:
            break
    backup = len(files) - 1
    for fp in files:
        try:
            size += os.path.getsize(fp)
            with open(fp, "r", encoding="utf-8") as f:
                total += sum(1 for _ in f)
        except OSError:
            continue
    return LogInfo(
        file_path=LOG_FILE,
        size_bytes=size,
        size_mb=round(size / (1024 * 1024), 2),
        backup_count=backup,
        total_entries=total,
    )
