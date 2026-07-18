# PrintFlow-3D 后续规划

## v1.11.0 — 仪表盘首页 + 数据查询优化

替代当前空白首页，一屏掌握经营全貌；同时优化销售统计页面的查询性能。

### 仪表盘首页

#### 核心卡片

| 卡片 | 数据来源 | 说明 |
|------|---------|------|
| 待发货 | orders (status=pending_ship) | 数量 + 点击跳转订单页 |
| 库存预警 | inventories (quantity < warning_threshold) | 数量 + 点击跳转库存页 |
| 本月利润 | orders (当月 completed) | 收入/成本/利润三行 |
| 打印中 | print_tasks (status=printing/pending) | 数量 + 点击跳转打印页 |

#### 布局

- 顶部：4 个统计卡片横排
- 中部：最近 5 笔订单快速列表
- 底部：打印任务状态统计（待打印/打印中/已完成）

#### 新增文件

| 文件 | 说明 |
|------|------|
| `frontend/src/views/Dashboard.vue` | 仪表盘页面 |
| `backend/routers/dashboard.py` | 聚合统计 API |

### 销售统计查询优化

当前问题：3 个端点各自全表扫描 + N+1 懒加载 order_items + Python 循环聚合，100 个订单产生 ~300 次 SQL。

#### 优化项

| 优先级 | 问题 | 方案 |
|--------|------|------|
| P0 | N+1 懒加载 order_items（3x） | 加 `selectinload(Order.items)` |
| P0 | 三次全表扫描同一数据 | 合并为单次查询，或提取共享数据层 |
| P1 | Python 循环聚合代替 SQL 聚合 | 改用 `func.sum()` / `func.count()` + `GROUP BY` |
| P2 | 切换排序重查全部 3 个端点 | 前端仅重查 by-product 端点 |
| P3 | 缺少复合索引 | 加 `(status, completed_time)` 复合索引 |

#### 改动文件

| 文件 | 说明 |
|------|------|
| `backend/routers/sales.py` | 重写为 SQL 聚合查询，消除 N+1 |
| `backend/models.py` | 加复合索引 |
| `frontend/src/views/Sales.vue` | 排序变更仅重查 by-product |

---

## v1.12.0 — 移动端适配

树莓派内网访问场景下，手机浏览器是常见入口。

### 适配要点

| 组件 | 桌面端 | 移动端 |
|------|--------|--------|
| 侧边栏 | 常驻左侧 | 汉堡菜单 + 抽屉式滑出 |
| 数据表格 | 横向滚动表格 | 卡片列表（每行一张卡片） |
| 表单弹窗 | 居中弹窗 max-w-xl | 全屏弹窗 |
| 操作按钮 | 横排文字按钮 | 图标按钮 / 竖排 |
| 分类筛选 | 横排 tab | 横向滚动 chip |

### 实现方式

- TailwindCSS 响应式断点（`md:` 前缀）
- Sidebar 组件增加 `collapsed` 状态 + 触摸遮罩
- DataTable 组件增加 `card-mode`（`<768px` 自动切换）
- FormModal 组件移动端全屏化

---

## v1.13.0 — 游戏大类 + 商品分类（双层配置）

引入游戏维度，支持商品属于多个桌游；同时将商品分类（counter/token/other/bundle）从硬编码枚举改为配置表，两层均支持页面增删改查。

### 数据模型

```
games              product_games          categories          products
──────             ────────────           ───────────         ────────
id                 game_id  ──────────→   id                  id
name               product_id ────────→   name                name
slug               ...                    slug                category_id ──→ categories.id
icon                                      game_id ──→ games.id  sort_order
sort_order                                sort_order          ...
...                                       ...
```

- `games` 表：id, name, slug, icon（可选）, sort_order, created_at
- `categories` 表：id, name, slug, game_id（外键→games）, sort_order, created_at
  - 每个游戏下有独立的分类列表（如诡镇奇谈→计数器/指示物/其他，DND→指示物/配件）
- `product_games` 关联表：game_id, product_id（联合主键）
- `products.category` 改为 `products.category_id`（外键→categories.id）

### 后端改动

| 改动 | 说明 |
|------|------|
| 新增 `Game` 模型 + `product_games` 关联表 | 多对多关系 |
| 新增 `Category` 模型 | 分类配置表，关联游戏 |
| `/api/games` CRUD | 游戏管理接口 |
| `/api/categories` CRUD + `?game_id=` 筛选 | 分类管理接口 |
| `products.category` → `products.category_id` | 字段迁移，外键关联 |
| 商品列表加 `?game_id=` / `?category_id=` 筛选 | 按游戏或分类过滤 |
| ProductResponse 加 `games` + `category` 字段 | 返回关联信息 |
| 商品创建/编辑支持 `game_ids` + `category_id` | 关联选择 |
| 长图生成按游戏+分类分组 | 每个游戏生成独立分类长图，标题带游戏名 |

### 前端改动

| 改动 | 说明 |
|------|------|
| 设置页新增游戏管理 | 游戏列表 + 增删改 |
| 设置页新增分类管理 | 按游戏分组展示分类列表 + 增删改 |
| 商品页加游戏筛选 | tab 或下拉，筛选某游戏下的商品 |
| 商品表单加游戏多选 + 分类单选 | 游戏多选（至少一个），分类根据所选游戏联动 |
| 长图页按游戏生成 | 选择游戏 → 生成该游戏的分类长图 |

### 数据迁移

- 自动创建默认游戏"诡镇奇谈"（slug: `arkham_horror`）
- 自动创建默认分类：计数器（counter）、指示物（token）、其他（other）、合集（bundle），关联到诡镇奇谈
- 现有商品的 `category` 字符串值迁移为 `category_id` 外键
- 现有全部 active 商品关联到诡镇奇谈游戏

### 语义示例

```
诡镇奇谈 → 计数器 → 两位数计数器
诡镇奇谈 → 指示物 → 知识token
DND      → 计数器 → 两位数计数器（同一个商品，关联两个游戏）
DND      → 指示物 → 灵感token
DND      → 配件   → 骰塔（DND 独有分类）
```

---

## v1.14.0 — MCP 录单工具层

构建 MCP Server 基础框架，聚焦录单闭环，同时服务于 Hermes（QQ 机器人）和 Web 页面。

### 架构

```
QQ图片 → Hermes + Vision ──┐
                            ├→ printflow MCP Server → PrintFlow API → DB
Web 页面（手动/粘贴导入） ──┘
```

### 新增文件

| 文件 | 说明 |
|------|------|
| `mcp/printflow_mcp.py` | stdio MCP Server，录单相关工具 |
| `mcp/requirements.txt` | MCP SDK 依赖（mcp>=1.0.0, httpx） |

### MCP 录单工具

| 工具 | 触发场景 | API |
|------|---------|-----|
| `search_products` | "有哪些xx商品" / 商品匹配 | GET /api/products?search= |
| `parse_order_text` | 粘贴文本解析 | POST /api/orders/parse |
| `create_order` | 确认入库 | POST /api/orders |
| `get_product_detail` | 查商品详情（成本、库存） | GET /api/products/{id} |

### 后端优化

| 改动 | 说明 |
|------|------|
| 新增 `POST /api/orders/parse-structured` | 接收 JSON 字段直接解析，跳过文本拼装环节，仍走商品匹配/合集展开逻辑 |
| order_items 创建时自动快照 material_cost | 从 products.material_cost 读取，无需前端传 0 |

### Hermes skill 调整

现有 order-entry skill 改为调用 MCP tools，而非直接调 HTTP API：
- Vision 识别 → 构造结构化数据 → `parse-structured` → 确认 → `create_order`
- 避免文本拼装环节的格式陷阱（前缀、省份误判等）

---

## v2.0.0 — MCP 分析工具 + AI 助手

在录单 MCP 基础上扩展分析能力和 Web AI 助手界面。

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

| 文件 | 说明 |
|------|------|
| `frontend/src/components/AiAssistant.vue` | 页面右下角 AI 对话悬浮窗 |

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

## 已发布

| 版本 | 内容 |
|------|------|
| v1.10.0 | 商品自定义排序（sort_order + 拖拽排序 + 长图排序联动） |
| v1.9.1 | 图片上传裁剪 + 弹窗拖拽修复 + 不单卖标识 + 配色预览分组 + 表单样式优化 |
| v1.9.0 | 商品长图生成（Jinja2 + Playwright 截图，羊皮纸/暗金双主题） |
| v1.8.1 | 合集价修复 + 订单表单增强（闲鱼号/自动费用/公益按需）+ 买家好评标签 + Pi 部署迁移 |
| v1.8.0 | Nginx + systemd 生产部署（WSL2）→ 后迁移至 Raspberry Pi |
