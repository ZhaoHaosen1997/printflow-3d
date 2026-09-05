"""全局共享常量：协议枚举的唯一来源（后端各层与 mcp/server.py 共用）。

新增订单状态时只改这里；中英文映射、迁移表、前端展示全部由本文件派生。
"""

# 订单状态：英文 key → 中文展示名
ORDER_STATUS = {
    "pending_ship": "待发货",
    "shipped": "已发货",
    "completed": "交易成功",
    "cancelled": "已取消",
    "returned": "退货",
    "archived": "已归档",
}

# 反向映射：中文展示名 → 英文 key（数据库迁移、解析器共用）
STATUS_LABEL_TO_KEY = {label: key for key, label in ORDER_STATUS.items()}

# 终态：进入这些状态后写入 completed_time
TERMINAL_STATUSES = {"completed", "cancelled", "returned", "archived"}
