# PrintFlow-3D 后续规划

## v1.9.0 — 商品长图生成

- Jinja2 模板 + Playwright 截图
- 自动生成闲鱼商品详情长图（商品名/价格/颜色选项/实物图）

---

## v2.0.0 — MCP Server + AI 助手

构建统一的 MCP 工具层，同时服务于 Hermes（QQ 机器人）和 Web 页面 AI 小助手。

### 架构

```
QQ消息 → Hermes Gateway ──┐
                          ├→ printflow MCP Server → PrintFlow API → DB
Web AI 助手（页面小窗） ──┘
```

### 新增文件

| 文件 | 说明 |
|------|------|
| `mcp/printflow_mcp.py` | stdio MCP Server，包装业务操作为 LLM 工具 |
| `mcp/requirements.txt` | MCP SDK 依赖（mcp>=1.0.0, httpx） |
| `frontend/src/components/AiAssistant.vue` | 页面右下角 AI 对话悬浮窗，调用 MCP 工具 |

### MCP 基础工具（CRUD）

| 工具 | 触发场景 | API |
|------|---------|-----|
| `search_products` | "有哪些xx商品" | GET /api/products?search= |
| `create_order` | "新增订单xx卖了38" | POST /api/orders |
| `update_order_status` | "xx订单已发货" | PUT /api/orders/{id}/status |
| `query_orders` | "今天卖了多少" | GET /api/orders |
| `query_inventory` | "库存还有多少" | GET /api/inventories |
| `complete_print_task` | "xx打印好了" | PUT /api/print_tasks/{id}/complete |

### MCP 分析工具（AI）

| 工具 | 触发场景 | 说明 |
|------|---------|------|
| `sales_report` | "这个月哪种商品最赚钱" | 按商品/时间段聚合销售、利润、排名 |
| `sales_trend` | "最近一周的销售趋势" | 日销售额汇总 |
| `buyer_profile` | "小明的购买习惯" | 购买频次、偏好商品、议价幅度 |
| `buyer_ranking` | "谁买得最多" | 按金额/次数买家排行 |
| `suggest_price` | "给龙猫定个价" | 成本+历史利润 → 建议售价区间 |
| `check_price` | "龙猫卖38合理吗" | 当前定价 vs 成本 vs 历史成交价 |
| `generate_description` | "帮龙猫写个闲鱼文案" | 根据商品信息生成标题+描述 |
| `paste_import_ai` | 粘贴文本正则解析失败 | LLM 兜底解析订单信息 |

### AI 助手（Web 页面）

- 右下角悬浮对话窗，类似客服小助手
- 直接输入自然语言："龙猫卖38合理吗"、"今天卖了多少钱"
- 后端 `mcp/` 目录起一个 HTTP MCP endpoint，前端通过 SSE 调用
- 对话历史本地存储，不跨会话

### 使用示例

```
Hermes（QQ 机器人）:
  "新增一个蓝色龙猫订单，38块钱，买家小明"
  → search_products → create_order
  → 回复："已创建订单 ORD-20260517-001"

Web AI 助手（页面内）:
  "龙猫卖38合理吗"
  → check_price → 成本12.5 + 包装1.5 + 服务费0.61 = 14.61
  → 利润23.39，利润率60%，历史均价35-42
  → 回复："定价38合理。利润23.4元（60%利润率），处于历史成交价区间内。"

  "帮我写个蓝色龙猫的闲鱼文案"
  → generate_description
  → 回复标题+描述文案
```

---

## v2.1.0 — PostgreSQL 迁移

- 一键迁移脚本
- SQLAlchemy 切换数据库连接
- 数据导入导出

---

## 已发布

| 版本 | 内容 |
|------|------|
| v1.8.1 | 合集价修复 + 订单表单增强（闲鱼号/自动费用/公益按需）+ 买家好评标签 + Pi 部署迁移 |
| v1.8.0 | Nginx + systemd 生产部署（WSL2）→ 后迁移至 Raspberry Pi |
