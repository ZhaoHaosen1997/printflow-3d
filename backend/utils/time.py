"""统一的业务时间基准。"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    TZ = ZoneInfo("Asia/Shanghai")
except ZoneInfoNotFoundError:
    # Windows 无系统 tzdata 时的回退；北京时间恒为 UTC+8，无夏令时，结果一致
    TZ = timezone(timedelta(hours=8))


def now_local() -> datetime:
    """当前业务时间：北京时间（naive datetime），全项目唯一时间入口。

    约定：所有新写入的业务时间（created_at/order_time/completed_time 等）
    一律使用北京时间。历史存量数据以 UTC 为主（早期 default=datetime.utcnow），
    仅在月度聚合边界上存在 8 小时差异，不做迁移。
    """
    return datetime.now(TZ).replace(tzinfo=None)
