# PrintFlow-3D — 项目上下文 & 开发约束

## 项目概述

- **项目名**：printflow-3d（3D打印商品管理工具 v2.0）
- **定位**：个人闲鱼3D打印副业管理系统，覆盖商品/耗材/订单/买家/库存/打印任务/销售统计全链路
- **运行环境**：WSL2 Debian（与云服务器环境一致）
- **访问方式**：Windows 浏览器 → `http://localhost:8848`

---

## 技术栈（禁止随意更换）

### 后端
- **FastAPI** (Python 3.11+)，SQLAlchemy ORM，Pydantic 校验
- **SQLite**（单用户，`data/app.db`），预留一键切换 PostgreSQL
- **Nginx**：`:18848` 反向代理至 `:8848`
- **systemd**：WSL2 开机自启，暂不引入 Redis

### 前端
- **Vue 3** (Composition API) + **Vite 6** + **TailwindCSS 3** + **Lucide Icons**
- 深色主题（深色背景 + 金色点缀），卡片式布局，响应式
- 公共组件：`Layout.vue`、`Sidebar.vue`、`DataTable.vue`、`FormModal.vue`、`StatusBadge.vue`

---

## 目录结构

```
printflow-3d/
├── backend/
│   ├── main.py / models.py / schemas.py / database.py
│   ├── routers/   # products, orders, inventories, buyers,
│   │              # print_tasks, filaments, settings, parser
│   └── services/  # parser_service.py, analytics.py
├── frontend/
│   └── src/
│       ├── views/      # Orders, Products, Filaments, Inventories,
│       │               # PrintTasks, Buyers, Sales, PasteImport, Settings
│       ├── components/ # 公共组件
│       └── composables/ # useApi, useOrders, useProducts
├── data/app.db
├── old_data/        # 旧版 JSON，永久保留，禁止删除
├── scripts/migrate.py / merge_xianyu.py
├── requirements.txt
└── nginx.conf
```

---

## 核心数据表

| 表名 | 说明 |
|------|------|
| `products` | 商品（合集用 `category='bundle'` 标识，`bundle_items` JSON 存子商品ID） |
| `print_recipes` | 打印配方（`product_id`、`output_qty`、成本**实时计算不存储**） |
| `print_recipe_filaments` | 配方-耗材关联（`grams` 克数） |
| `filaments` | 耗材（品牌/材料/价格，用于成本计算，不追踪库存，显示名=brand+material） |
| `orders` | 订单（`order_no: ORD-YYYYMMDD-001`） |
| `order_items` | 订单明细 |
| `buyers` | 买家（昵称去重，自动聚合） |
| `inventories` | 成品库存（每个商品一条记录） |
| `print_tasks` | 打印任务（`task_no: TASK-001`，关联配方） |
| `printers` | 打印机（预留多机扩展） |
| `colors` | 标准色表（**最先建**，是商品颜色选项的前置依赖） |
| `settings` | 全局配置（运费/服务费率/包装费） |

---

## 核心业务逻辑（不可篡改）

### 成本计算
```
配方总成本（实时）   = Σ(耗材克数 × filaments.price_per_kg / 1000)
配方单位成本（实时） = 配方总成本 / output_qty
products.material_cost = 默认配方单位成本快照（保存配方时 service 层手动写入）
利润 = actual_amount - order_items.material_cost - 包装费 - 运费 - 服务费
服务费 = actual_amount × service_fee_rate（默认 1.6%）
运费 = 全局配置（默认 0，包邮）
discount = total_amount - actual_amount（砍价金额，不计入成本，独立统计）

### 商品价格语义（重要，避免认知偏差）
- `price_single`：单独出售价格。普通商品=单品售价，bundle商品=合集售价（一口价），0=不单卖仅作子商品
- `price_bundle`：作为子商品被收入合集时的优惠单价，bundle商品该字段为0
- Token合集包：定价走 price_single（一口价38），成本遍历子商品 material_cost 求和
```
> 注意：`print_recipes` 表**不存** `calculated_material_cost` / `unit_material_cost` 字段，成本全部实时查询计算。

### 打印完成联动（原子操作）
1. `recipe.print_count += 1`
2. `inventories.quantity += output_qty`

### 打印配方的"数量"语义（重要，避免误解）
- **一个配方对应一次上机打印，`output_qty` 是该次打印的产出件数**
- 同一商品可以有多个配方（如"打1个"、"打2组"），按实际打印方式选用
- 打印任务直接关联配方，任务数量 = `output_qty`，**打印任务本身不再设数量字段**
- `material_cost` 在下单时从当前 `products.material_cost` 快照，历史订单不追溯

### 合集商品处理
- **Token合集包**：内容固定（如5个子商品），下单时自动展开为子商品明细写入 order_items
- **自选合集**：由买家与我协商决定，下单时手动选择包含的商品
- 子商品写入 order_items 时采用**快照模式**：存储当时的商品名称、单价、材料成本，后续修改不影响历史订单

### 合集售出联动
- 自动扣减所有子商品成品库存

### 粘贴导入（核心功能）
- 优先**正则规则引擎**解析，兼容「待发货 / 已发货 / 交易成功」三种文本格式
- 商品名模糊匹配 `products` 表，固定合集自动展开子商品，自选合集标记「待确认」
- 支持一次粘贴多个订单（空行分隔），买家信息自动创建/更新

---

## 全局配置预设

| key | 默认值 | 说明 |
|-----|--------|------|
| `shipping_fee` | 0 | 默认运费（包邮） |
| `service_fee_rate` | 0.016 | 闲鱼服务费率 |
| `packaging_fee` | 1.5 | 单品包装费 |
| `packaging_fee_bundle` | 2.0 | 合集包装费 |

---

## 版本迭代路线

| 版本 | 重点 | 状态 |
|------|------|------|
| v1.0.0 | 后端骨架 + DB初始化 + **配色CRUD（最先）** + 耗材CRUD + 商品/配方CRUD + Vue前端框架 | ✅ |
| v1.1.0 | 订单管理 + 粘贴导入 + 商品匹配/合集展开 | ✅ |
| v1.2.0 | 旧数据迁移脚本（JSON → SQLite） | ✅ |
| v1.3.0 | 成品库存联动 + 预警 + 全局设置 | ✅ |
| v1.3.1 | 粘贴导入优化：关键词匹配 + 合集格式修正 + 省份入库 + 无括号解析 | ✅ |
| v1.4.0 | 日志系统：文件滚动日志 + API中间件 + 前端日志查看页 + 全业务埋点 | ✅ |
| v1.5.0 | 打印任务管理 | ✅ |
| v1.6.0 | 买家管理 + 标签 + 统计 | ✅ |
| v1.7.0 | 销售统计 + 利润报表（从orders实时聚合，无独立sales表）+ 数据导出 | 🔲 |
| v1.8.0 | Nginx + systemd 生产部署 | 🔲 |
| v1.9.0 | 商品长图生成（Jinja2 + Playwright 截图） | 🔲 |

---

## 开发铁律

1. **每次只做一个版本**，完成并测试通过后再推进下一版本
2. 先在 Windows 环境测试，再部署 WSL
3. 测试通过后 git commit，版本号按实际修改内容自动生成
4. 优先开发核心差异化功能：粘贴导入订单
5. `old_data/` 目录只读，禁止删除或修改
6. 后端：路由层只做分发，业务逻辑全放 services 层
7. 禁止手动填写材料费，全部自动计算
8. 禁止在 `print_recipes` 表中持久化 `calculated_material_cost` / `unit_material_cost`，必须实时计算
9. `products.xianyu_item_id` 允许为空（未上架闲鱼的商品也能录入），但不能重复
10. 商品是否合集统一用 `category == 'bundle'` 判断，不使用 `is_bundle` 字段
11. **日志埋点**：新增业务操作必须接入日志。路由层用 `log_business()`，解析层用 `log_parser()`/`log_parser_warn()`，异常用 `log_error()`。API 层由中间件自动记录，无需手动埋点。
12. **提交时更新版本号**：每次 git commit 并推送前，须同步更新两处版本展示：
    - `frontend/src/components/Sidebar.vue` 中版本号显示文本
    - `backend/main.py` 中 `FastAPI(title="PrintFlow-3D", version="...")`

---

## 开发规范

### BAT 脚本
- 必须纯 ASCII，不含中文，不加 `chcp 65001`（多数终端反而乱码）

### 侧边栏
- 只放一级功能，子功能（如粘贴导入）通过页面内按钮跳转，不在侧边栏展示

### 表单精简原则
- **我不会改的字段不展示**（如来源、状态），直接用默认值
- **我很少改的字段**给输入框 + 默认值
- **自动计算的值**只读展示（如单价、材料成本、原价总额、砍价金额）
- 目标：尽可能少填表单就能完成操作

### DataTable 操作列
- 不加固定宽度，`whitespace-nowrap` 让按钮横向排列

### 推送 GitHub
- 远程仓库：https://github.com/ZhaoHaosen1997/printflow-3d
当用户说"帮我推送远程仓库 / 推送 github"时：
1. `git add` 所有变更文件（不含 .env、node_modules、__pycache__、.venv）
2. `git commit`，提交信息概括本轮改动要点（中文，一行）
3. `git push origin master`

### 操作按钮五种风格（按语义选用）
| 风格 | class | 适用场景 |
|------|-------|----------|
| 轮廓线 | `btn-outline` | 常规操作（编辑/查看） |
| 柔和 | `btn-soft` | 强调/推进流程（发货/配方） |
| 实心 | `btn-filled` | 主操作/确认（完成/保存） |
| 危险轮廓 | `btn-danger-outline` | 危险操作（取消/归档/删除） |
| 幽灵 | `btn-ghost` | 低调操作 |
