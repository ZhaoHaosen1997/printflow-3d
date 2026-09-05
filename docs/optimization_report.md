# PrintFlow-3D 全量代码优化分析报告

> **审查日期**：2026-09-05（基于 master @ `7cc6548`，v1.17.0）
> **审查范围**：backend/（4,887 行）+ frontend/src/（约 6,400 行）+ mcp/server.py（547 行），合计约 11,900 行源码；共 70 个 API 路由、60 个 Pydantic 模型、14 个前端页面
> **审查方法**：全量人工精读核心模块（main/database/models/orders/products/parser/product_service/useApi）+ 并行代理扫描外围模块，所有发现均附带文件路径与行号，关键结论已交叉验证
> **背景约定**：本系统为内网单用户个人工具（`192.168.10.20:8848`），无用户认证体系属已知设计取舍，安全类问题在此背景下定级
> **关联文档**：`docs/code-review.md`（2026-05-16 首审，2026-08-01 复查），本报告附录 A 对照了其余留项

---

## 目录

- [一、总览与整体评价](#一总览与整体评价)
- [二、安全漏洞](#二安全漏洞)
- [三、性能瓶颈](#三性能瓶颈)
- [四、错误处理健壮性](#四错误处理健壮性)
- [五、数据一致性与事务设计](#五数据一致性与事务设计)
- [六、重复代码与设计模式](#六重复代码与设计模式)
- [七、代码可读性与可维护性](#七代码可读性与可维护性)
- [八、测试覆盖](#八测试覆盖)
- [九、文档完善度](#九文档完善度)
- [十、优先级汇总与实施路线图](#十优先级汇总与实施路线图)
- [附录 A：历史 code-review.md 遗留问题对照](#附录-a历史code-reviewmd-遗留问题对照)

---

## 一、总览与整体评价

### 1.1 代码规模

| 模块 | 行数 | 最大文件 |
|------|------|----------|
| backend/（Python） | 4,887 | `schemas.py` 708 行、`routers/orders.py` 613 行 |
| frontend/src/（Vue/JS） | ≈6,400 | `views/Products.vue` **1,245 行**、`views/Orders.vue` 622 行 |
| mcp/server.py | 547 | — |
| 自动化测试 | **0** | 无任何 pytest / vitest 用例 |

### 1.2 整体评价

**优势**（值得保持的部分）：

- 数据建模规范：金额全 `Numeric(10,2)` + `Decimal`、关键列有索引、部分复合索引（`idx_order_status_completed`）；成本实时计算不持久化的设计贯彻到位。
- 分层意识清晰：路由层薄、业务在 services 层、`main.py` 只做装配；sales/dashboard 聚合用 SQL 端 `sum/group by` 而非 Python 循环。
- MCP 工具层 docstring 质量高、有超时、limit clamp、状态白名单校验。
- 前端 CSS 变量多主题方案、`useApi` 并发计数、`DataTable` 的 columns/slots 抽象、无 `v-html`、定时器/监听器清理基本到位。

**四大短板**：

1. **横切关注点未收敛**——状态映射 5 处、Modal 外壳 8 处、库存加减 3 套、格式化函数 4 份手工复制，已出现死代码与行为漂移（详见第六章）。
2. **写路径健壮性欠账**——库存读-改-写非原子、service 层多重 commit 无回滚、admin 批量删除留孤儿行（详见第五章）。
3. **前端错误处理链断裂**——`useApi` 维护的 `error` 无任何 UI 消费，大量裸 `await` 与空 `catch`，接口失败时用户基本无感知（详见第四章）。
4. **零测试保护**——价格语义、库存联动这两块最核心、历史上已出过两次线上 bug（v1.8.1 合集价归零、v1.17.0 订单价格修正）的业务逻辑没有任何回归测试（详见第八章）。

### 1.3 问题统计

| 优先级 | 数量 | 代表问题 |
|--------|------|----------|
| 高 | 5 | SPA 路径遍历、库存非原子扣减、前端错误链断裂、配方编辑静默丢数据、零测试 |
| 中 | 22 | N+1 查询集群、事务边界混乱、双 badge 体系、README 过时等 |
| 低 | 18 | 死代码清单、魔法数字、弃用 API 等 |

---

## 二、安全漏洞

> 定级基准：内网单用户环境。若未来暴露公网（README 中有云服务器部署方案），本章所有"低"项需全部升级。

### 2.1 【高】SPA catch-all 路由存在路径遍历，可读取数据库与任意文件

**位置**：`backend/main.py:80-85`

```python
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    file_path = os.path.join(FRONTEND_DIR, full_path)   # ← 未做规范化校验
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
```

`full_path` 来自 URL 路径参数，Starlette 会解码 `%2e%2e%2f` 为 `../`。构造 `GET /..%2fdata%2fapp.db`，`os.path.join` 拼出 `frontend/dist/../data/app.db`，`isfile` 判真后直接以 `FileResponse` 返回——**数据库、日志、乃至服务器上 FastAPI 进程可读的任意文件均可被下载**。MCP 与内网任意设备均可触发。该路由在生产（dist 已构建）常驻生效。

**优化建议**：改用 `StaticFiles(html=True)` 挂载，其内部自带路径逃逸防护；或手工规范化校验。

**实施步骤**：
1. 删除 `serve_frontend`，改为：

```python
# 生产模式：StaticFiles 自带 SPA fallback 与路径逃逸防护
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend", "dist")
if os.path.exists(FRONTEND_DIR) and os.listdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="spa")
```

   注意 mount 要放在所有 `include_router` 之后（现有代码顺序已满足）。
2. 若坚持手写路由，则校验解析后的真实路径：

```python
real = os.path.realpath(os.path.join(FRONTEND_DIR, full_path))
if real.startswith(os.path.realpath(FRONTEND_DIR) + os.sep) and os.path.isfile(real):
    return FileResponse(real)
```

3. 验证：`curl --path-as-is "http://localhost:8848/..%2fdata%2fapp.db"` 应返回 index.html 而非数据库。

**预期收益**：消除项目内唯一的"任意文件读取"级漏洞，修复成本约 5 行代码，为未来上云扫清障碍。

### 2.2 【中】admin 硬删除 / 费率配置 / 全量日志接口无任何防护

**位置**：`backend/routers/admin.py:75-120`（永久批量删除）、`settings.py:16-26`、`logs.py:34-93`

内网无认证是既定取舍，但 `/api/admin/*` 的**不可恢复批量删除**连一个确认令牌都没有，而 MCP 工具层接通后，AI 误调用即可触发。建议最低限度加一道共享密钥头校验（`X-Admin-Token`，值放 `.env`），前端 ArchivedData 页与 MCP 侧各自带上；删除类接口再要求请求体携带确认串（如 `confirm: "DELETE"`）。

**预期收益**：把"误触即永久丢数据"的爆炸半径降为零；实施约半天。

### 2.3 【中低】PosterGenerator 用 iframe srcdoc 预览后端 HTML，缺少 sandbox

**位置**：`frontend/src/views/PosterGenerator.vue:270-291`

```html
<iframe :srcdoc="previewHtml" ... />
```

srcdoc iframe 与父页面**同源**。商品名/关键词若含恶意标签且后端 Jinja2 模板存在转义疏漏，脚本将以应用全权限执行（可调 `/api/admin` 删除数据）。当前 Jinja2 自动转义大概率挡住了直接注入，但这是双重依赖。修复：`<iframe sandbox ...>` 一行属性即可（预览不需要脚本执行时甚至可 `sandbox=""`）。

### 2.4 【低】安全杂项清单

| # | 位置 | 问题 | 修复 |
|---|------|------|------|
| a | `main.py:30-42` | CORS 默认 origins 与实际部署地址（192.168.10.20:8848）不匹配；methods/headers 全 `*` | 默认值加入内网地址；methods 收敛为实际动词 |
| b | `services/logger_service.py:67-73`、`middleware/logging_middleware.py:14-20` | 日志注入：买家昵称/备注含换行可伪造日志行；query string 全量入日志 | 写入前 `replace("\n", "\\n")`；query 超 200 字符截断 |
| c | `routers/buyers.py:23` | `ilike(f"%{search}%")` 未转义 `%`/`_`，可扩大匹配 | `search.replace("%", r"\%").replace("_", r"\_")` + `escape=True` |
| d | `routers/logs.py:116-117` | `/logs/info` 返回服务器绝对路径 | 只返回文件名 |
| e | `routers/orders.py:309-437` | CSV 导出未加 BOM，Excel 打开中文乱码；备注/商品名以 `=`/`+`/`@` 开头存在公式注入 | 首行前写 `\ufeff`；敏感前缀单元格加 `'` 前缀 |
| f | `routers/products.py:166-190` | 图片上传仅信任客户端 `content_type`，未校验文件魔数；且 `await file.read()` 先全量读入再判 10MB | 用 `file.read(10*1024*1024+1)` 限量读取；可用 `filetype` 库校验魔数 |
| g | `services/poster_service.py:46-57` | `os.path.join(IMAGES_DIR, filename)` 未 `basename()` 归一，DB 被污染即成路径遍历 | `os.path.basename(filename)` 一行 |

---

## 三、性能瓶颈

> 当前数据量（个人副业，数百订单）下多数项尚无体感，但 N+1 类问题随数据线性恶化，且修复成本低，建议按清单批量处理。

### 3.1 【中】后端 N+1 查询集群

| # | 位置 | 模式 | 修复 |
|---|------|------|------|
| 1 | `routers/inventories.py:37-51, 86-93` | 列表页对每个商品逐条 `ensure_inventory`（N 次查询）；且 GET 接口带 `db.commit()` 写副作用 | 一次 `IN` 批量取全部 Inventory 建 dict 映射；补建逻辑挪到商品创建时（`products.py:93-95` 已有） |
| 2 | `routers/print_tasks.py:22-41, 55-60` | 每行任务 lazy-load `task.recipe` → `recipe.product` 链（2N 次查询） | `.options(selectinload(PrintTask.recipe).selectinload(PrintRecipe.product))` |
| 3 | `routers/admin.py:66` | 归档订单列表逐单 lazy-load `o.buyer` | `options(joinedload(Order.buyer))` |
| 4 | `routers/orders.py:354-360`（export） | **导出全量订单**逐单 lazy-load `o.buyer` + `o.items`（2N+1 次），是列表页的放大版 | 同列表页加 `selectinload` |
| 5 | `routers/products.py:106-126, 195-213` | `get_product`/`list_recipes` 对每个配方单独调 `calculate_recipe_cost`（每次重查 recipe + filaments，与已 selectinload 的数据重复） | `calculate_recipe_cost` 增加"接受已加载 recipe 对象"的入口，复用 ORM 身份映射 |
| 6 | `services/poster_service.py:60-103` | 海报数据构建：每商品每可选色单独查 Color + 每商品一次图片文件读 | 预载全部 Color 建 `{color_id: obj}` 字典；图片读入可用 `lru_cache` |
| 7 | `services/description_service.py:68-78` | 同上，介绍生成时逐色查询 | 同上 |
| 8 | `mcp/server.py:203-209` | HTTP 层 N+1：bundle 详情对每个子商品发一次请求 | 后端加批量接口或复用 list 数据 |

**实施步骤**：均为局部改动、互不依赖，可按"一次 commit 清 2-3 项"推进；每项改完用 `sqlite3` 开 `PRAGMA profiling` 或简单计时对比查询次数。

**预期收益**：列表/导出/海报接口查询次数从 O(N) 降到 O(1)~O(3)；导出千单时从约 2000 次查询降到 3 次。

### 3.2 【中】日志接口全量读文件（最多 55MB）再内存分页

**位置**：`backend/routers/logs.py:34-52, 62-93`

`_read_all_log_files` 每次请求把最多 11 个 5MB 滚动文件 `readlines()` 全量载入并逐行正则解析，分页只是最后切片；`/logs/info` 又独立重读全部文件数行数。

**优化建议**：倒序逐文件流式读取，凑满 `offset+page_size` 行即早停；info 的文件大小/行数改用 `os.path.getsize` 估算 + 短 TTL 缓存。前端 `LogViewer.vue` 的无限累加数组（每次 `[...old, ...new]` 全量拷贝）同步改为分页替换。

**预期收益**：日志页打开从"读 55MB"降到"读 2 个文件尾部"，内存占用与首屏延迟数量级下降。

### 3.3 【中】海报生成：数据双重计算 + 每请求冷启动 Chromium + 参数无上限

**位置**：`routers/posters.py:27-34`、`services/poster_service.py:202-211`

1. 分类海报数据被算两次：`generate_category_poster` 内部已调 `get_category_poster_data`，路由又调一次仅为取 title 做文件名——商品查询、颜色解析、图片 base64 全部重算。
2. 每次请求 `sync_playwright() + chromium.launch()`，单请求秒级耗时。
3. `width: int = Query(750, ...)` 无 `le` 上限，可传 100000 撑爆内存。

**优化建议**：`generate` 返回 `(png_bytes, title)` 元组；Playwright 改为模块级单例 browser（启动时创建、请求复用 context）；`Query(750, ge=200, le=2000)`；可选按 `(category, game_id, template, width)` 做文件级结果缓存。

**预期收益**：海报接口耗时从 ~3-5s 降至 <1s（数据重算消除 + 浏览器复用），并封死资源滥用参数。

### 3.4 【高·兼数据丢失】配方编辑 = 串行逐条删除 + 逐条新建 HTTP 请求，且失败静默吞

**位置**：`frontend/src/views/Products.vue:505-510`

```js
for (const rf of (editingRecipe.value.recipe_filaments || [])) {
  try { await del(`/api/recipe-filaments/${rf.id}`) } catch { /* best-effort */ }
}
for (const f of filaments) {
  try { await post(`/api/recipes/${editingRecipe.value.id}/filaments`, f) } catch { /* best-effort */ }
}
```

一个含 5 种耗材的配方保存 = 10 次串行请求；中途任何一条失败被 `catch` 吞掉，**配方耗材静默丢失**，且后端每次操作都触发 `sync_product_material_cost` 重算——同一保存动作多次级联。这是性能与正确性的双重问题。

**优化建议**：后端新增批量替换接口 `PUT /api/recipes/{id}/filaments`（事务内 delete-all + bulk insert + 一次 sync），前端一次调用完成。

```python
@router.put("/recipes/{recipe_id}/filaments", response_model=list[PrintRecipeFilamentResponse])
def replace_recipe_filaments(recipe_id: int, data: RecipeFilamentsBulkUpdate, db: Session = Depends(get_db)):
    recipe = db.query(PrintRecipe).filter(PrintRecipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(404, "配方不存在")
    db.query(PrintRecipeFilament).filter(PrintRecipeFilament.recipe_id == recipe_id).delete()
    rfs = [PrintRecipeFilament(recipe_id=recipe_id, filament_id=d.filament_id, grams=d.grams)
           for d in data.items]
    db.add_all(rfs)
    db.commit()                      # 单事务：要么全成要么全不动
    if recipe.is_default:
        sync_product_material_cost(db, recipe.product_id)
    return rfs
```

**预期收益**：保存配方从 2N 次请求降为 1 次；消除静默丢数据路径；成本快照只重算一次。

### 3.5 【中】useApi 无请求取消，翻页/筛选存在响应竞态

**位置**：`frontend/src/composables/useApi.js:8-31`、`views/Orders.vue:76-96`

快速翻页时旧请求不取消，慢响应后到会整体覆盖 `orders.value`，展示与页码错位。

**优化建议**：`request` 接收 `AbortSignal`，或在页面级维护"最新请求序号"丢弃过期响应：

```js
let fetchSeq = 0
async function fetchAll() {
  const seq = ++fetchSeq
  const data = await get(url)
  if (seq !== fetchSeq) return        // 过期响应直接丢弃
  orders.value = data.items
}
```

**预期收益**：约 10 行改动消除整类竞态，无需引入新依赖。

### 3.6 【低】性能杂项

| # | 位置 | 问题 | 修复 |
|---|------|------|------|
| a | `views/Orders.vue:85-89` | 每次翻页重复拉取不变的 `/api/products`、`/api/settings` | 拉一次缓存到组件；配合 6.5 的轻量 store 更优 |
| b | `views/Products.vue:808,823,1067`、`Orders.vue:531` | 可增删的动态行 `v-for :key="idx"`，删除中间行导致输入状态错位（正确性兼性能） | 行对象生成时加临时 `uid` 字段作 key |
| c | `views/LogViewer.vue:72` | 无限累加全量渲染，千条日志 v-for 无虚拟滚动 | 分页替换或引入虚拟列表 |
| d | `views/Products.vue:225-237` | 拖拽排序保存后全量重拉 5 个接口 | 只重拉 products 或本地更新 sort_order |
| e | `components/DataTable.vue:82` | 骨架屏宽度绑定 `Math.random()`，每次重渲染抖动 | 改为按列 index 的确定性伪随机 |
| f | `routers/products.py:60-68` | 排序保存对每项单独 `query().first()` | `bulk_update_mappings` 或一条 `CASE WHEN` |

---

## 四、错误处理健壮性

### 4.1 【高】前端错误链整体断裂：error 无消费者 + 裸 await + 空 catch

这是前端最系统性的问题，三个层面同时失效：

**(1) useApi 维护的 `error` 从未被任何 UI 消费**（`useApi.js:5,20,25` 定义，全部 14 个 view 解构时都不取它）——错误处理形同虚设。

**(2) 大量裸 `await` 无 catch**：

- `views/Orders.vue:167-189` 编辑订单 `get().then()` 无 catch，失败则弹窗永不打开、无提示；
- `Orders.vue:194,200,206,212` 发货/完成/取消/归档四个操作全部裸奔；
- `Products.vue:291,431,479,484`（归档/配方列表/删配方/设默认）同样；
- 全部 13 处 `onMounted(fetchXxx)` 无错误分支，接口挂掉页面永久停在骨架屏。

**(3) 提交函数 try/finally 缺 catch**：`Orders.vue:294-331`、`Colors.vue:101-125`、`Filaments.vue:90-106`、`Inventories.vue:63-78`、`Buyers.vue:89-103`、`PrintTasks.vue:92-105`、`Settings.vue:37-54` 等 8+ 处，保存失败时用户看不到任何反馈（仅 Products 主表单有 alert）。另有 `PosterGenerator.vue:69-71,128` 完全空 catch。

**优化建议**（三步走，一次迭代可完成）：

1. **建全局 toast**：新增 `useToast.js`（模块级单例，与 `useTheme.js` 同模式）+ `ToastContainer.vue` 挂在 `App.vue`，提供 `success/error` 两级。
2. **useApi 收敛错误出口**：

```js
// composables/useApi.js 内，在 catch 中统一弹错（页面可传 silent: true 关闭）
import { toast } from '@/composables/useToast'
async function request(endpoint, options = {}) {
  // ...
  catch (e) {
    if (!options.silent) toast.error(e.message || '请求失败，请稍后重试')
    throw e
  }
}
```

   一次改动让全站所有 API 失败都有可见反馈，各 view 的裸 await 由此兜底。
3. **清理空 catch**：`PosterGenerator.vue:128`、`Products.vue:506,509` 等 4 处空 catch 逐个补日志或提示（3.4 的批量接口落地后 Products.vue 那两处自然消失）。

**预期收益**：接口故障从"无感知/白屏卡死"变为"明确报错 + 可重试"；同时替代现有 18 处 `alert()` / 10 处 `confirm()` 的原始反馈（confirm 可后续换为确认弹窗组件，非必须）。

### 4.2 【中】后端：commit 无回滚、异常信息直接外泄

- **`get_db` 只 close 不 rollback**（`database.py:21-26`）：commit 前抛异常依赖 close 隐式回滚，SQLite 下通常可行但脆弱。修复：

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()   # 无未决事务时是 no-op
        db.close()
```

- **posters 路由裸 500**（`posters.py:28-29, 60-61`）：`except Exception as e: raise HTTPException(500, str(e))`——内部异常文本（可能含路径）直接给客户端，且未 `log_error`。改为分类型捕获 + 通用文案 + 服务层记日志。
- **mcp/server.py 三处 `return f"Error: {e}"`**（44-55, 58-73, 76-91）：无日志无堆栈，排查全靠猜。补 `logging.exception` 后再返回结构化 `{"error": ...}`（文件内已有部分工具用 dict 风格，两种并存，见 6.1-f）。

### 4.3 【中】MCP `update_order_status`：状态与备注两次 PUT 非原子

**位置**：`mcp/server.py:521-531`

改状态成功后追加 reason 备注是第二次 PUT，失败分支静默——状态已变但备注丢失，AI 侧无从得知。修复：后端 `PUT /orders/{id}` 本就支持 notes 字段，MCP 侧改为**单次 PUT 同时提交 status + notes**（拼接原备注），消除中间态。

### 4.4 【低】校验类杂项

| # | 位置 | 问题 | 修复 |
|---|------|------|------|
| a | `routers/sales.py:14-17` | `date_from/date_to` 裸字符串直接比较 DateTime 列，非法格式静默产出错误聚合（orders.py:203 已用 `fromisoformat`，两处不一致） | 统一解析 + 422 |
| b | `routers/sales.py:210-211` | `sort_by` 任意字符串，非法值静默回退为 profit **升序**（语义反转） | 白名单校验 |
| c | `useApi.js:23` | `res.json()` 无保护，502 返回 HTML 时报 "Unexpected token" | `.catch(() => null)` 兜底 |
| d | `routers/print_tasks.py:160` | `data: PrintTaskFailRequest = None` 绕过 FastAPI 校验惯例 | `Optional[...] | None = None` |

---

## 五、数据一致性与事务设计

### 5.1 【高】库存扣减/回补为读-改-写，非原子且超卖静默截断

**位置**：`routers/orders.py:142,149`、`routers/print_tasks.py:143`

```python
inv = db.query(Inventory).filter(Inventory.product_id == pid).first()
inv.quantity = max(0, inv.quantity - qty)   # ← 读-改-写 + 超卖静默归零
```

三个叠加风险：
1. **丢失更新**：`check_same_thread=False`（`database.py:13`）下 FastAPI 线程池并发请求 + MCP 自动化调用并存，两个"读→算→写"交错时后写覆盖先写。订单完成回补（orders.py:161-168）与打印任务完成加库存（print_tasks.py:139-149）并发时互相覆盖。
2. **超卖静默**：`max(0, ...)` 把库存不足截断为 0 而非报错，订单照常创建，账实从此背离且无告警。
3. **engine 未配 busy_timeout**（`database.py:13`）：并发写直接抛 `database is locked` 变 500。

**优化建议**：

```python
# database.py —— 连接层加固
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 15},  # busy_timeout
)

from sqlalchemy import event
@event.listens_for(engine, "connect")
def _fk_pragma(dbapi_conn, _):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")   # 顺带解决 5.2 的外键不生效
    cur.close()
```

```python
# 库存操作改原子 UPDATE，检查影响行数；负库存时回滚并报业务错
def _atomic_deduct(db: Session, product_id: int, qty: int):
    updated = (
        db.query(Inventory)
        .filter(Inventory.product_id == product_id, Inventory.quantity >= qty)
        .update({Inventory.quantity: Inventory.quantity - qty},
                synchronize_session=False)
    )
    if updated == 0:
        inv = db.query(Inventory).filter(Inventory.product_id == product_id).first()
        if inv is None:
            ensure_inventory(db, product_id)
            db.flush()
            return _atomic_deduct(db, product_id, qty)
        raise HTTPException(400, f"商品库存不足（当前 {inv.quantity}，需 {qty}）")
```

**实施步骤**：
1. `inventory_service.py` 收敛为唯一的 `deduct / restore`（原子版），`orders.py` 的 `_deduct_order_inventory/_restore_order_inventory` 与 `print_tasks.py` 内联逻辑全部改调它（顺带完成 6.1-e 的三套合一）；
2. engine 加 busy_timeout + FK pragma；
3. 补"库存不足创建订单应 400"的测试（第八章）。

**预期收益**：并发下库存不再丢更新；超卖从静默截断变为显式报错，账实一致性可依赖。改动集中在 2 个文件。

### 5.2 【中】admin 批量删除绕过 ORM 级联，产生孤儿 recipe_filaments 行

**位置**：`routers/admin.py:89`

`db.query(PrintRecipe).filter(...).delete()`（bulk delete）不触发 `cascade="all, delete-orphan"`（models.py:122 的 cascade 仅对 `session.delete` 生效），而 `print_recipe_filaments.recipe_id` FK 无 `ondelete`（models.py:129）且 SQLite 默认不开外键——**删除配方后其耗材关联行残留**。对比同函数 113 行 orders 分支显式删了 OrderItem，products 分支漏删子表。

**修复**（配合 5.1 的 `PRAGMA foreign_keys=ON`）：给 FK 加 `ondelete="CASCADE"`（新库生效；存量库用 `_add_column_safe` 同款方式跑一次性清理脚本删除孤儿行），admin 删除改为显式逐级 `db.delete` 或 bulk delete 前先删子表。

### 5.3 【中】service 层事务边界混乱：一个用例多次 commit，中途失败留中间态

**位置**：`services/product_service.py:43, 57-58, 88-92, 113-117, 131-142, 153-168`

典型链路：`set_default_recipe` 先 commit"切换默认"，再调 `sync_product_material_cost` 又 commit——第二步失败则"默认配方已换但成本快照还是旧配方"。`update_filament_price` 更是在循环里对每个产品逐个 sync+commit。此外 `filaments.py:47-54` 路由已 setattr+commit 新价格，再调 `update_filament_price` 重复 set 同一字段并二次 commit。

**优化建议**：确立约定——**service 函数只 flush 不 commit，事务由路由层（或 `get_db` 的 finally）统一提交**。按 `sync_product_material_cost`、`set_default_recipe`、`create_recipe`、`update_filament_price` 四个函数逐个改造，路由层补 `db.commit()`。这是纯结构调整无行为变化，适合一次独立 commit 完成。

### 5.4 【低】单号生成竞态

`orders.py:27-40`（`max+1` 式扫 `order_no` 前缀）与 `print_tasks.py:17-19`（`max(id)+1`）在并发创建时会撞 unique 约束直接 500。单用户场景概率低，低成本方案：捕获 `IntegrityError` 重试一次即可，不必引入序列表。

### 5.5 【中】时间基准三套混用，月度统计边界偏移 8 小时

**位置**：`models.py` 全部 `default=datetime.utcnow`、`orders.py:253` 用 `utcnow()` vs `orders.py:486,538` 用 `now(timezone.utc).replace(tzinfo=None)`、`routers/dashboard.py:30-31` 用 UTC 算月初。

后果：dashboard/sales 的"本月"按 UTC 月界切分，**每月 1 日北京时间 0-8 点完成的订单被计入上月**——对一个月度利润报表系统是实际可见的统计偏差。另 `datetime.utcnow()` 在 Python 3.12 起已弃用。

**优化建议**：项目新建 `utils/time.py`：

```python
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")

def now_local() -> datetime:
    """统一的业务时间基准：本地(北京)时间的 naive datetime，全项目唯一入口。"""
    return datetime.now(TZ).replace(tzinfo=None)
```

models 的 `default=`、路由里的时间赋值、dashboard/sales 的月初计算统一改调它；dashboard 月界用 `now_local().replace(day=1, hour=0, minute=0, second=0, microsecond=0)`。存量 UTC 数据无需迁移（只影响聚合边界，不改变存储值），在函数 docstring 里注明该前提。

---

## 六、重复代码与设计模式

### 6.1 【中】后端重复模式

| # | 位置 | 问题 | 建议 |
|---|------|------|------|
| a | `models.py:155`（ORDER_STATUS）、`database.py:99`（STATUS_MIGRATION）、`orders.py:346`（STATUS_LABEL）、`parser_service.py:10`（STATUS_MAP）、`mcp/server.py:10`（ORDER_STATUS，注释自认"kept in sync"） | **订单状态映射 5 处独立维护**，历史遗留 H7 至今未修 | 收敛为 `backend/constants.py` 单一定义（含 label 英中双向映射），其余全部 import；前端经 `/api/meta` 下发或构建时生成 |
| b | `routers/games.py:16-58` vs `categories.py:16-58` | 两个文件逐行同构（create 查重/update/delete 归档） | 抽 `crud_factory(Model, schemas)` 或至少共享校验函数 |
| c | colors/filaments/buyers/print_tasks/inventories/settings 等 10+ 处 | `query→first→404` 与 `model_dump(exclude_unset)→setattr 循环` 样板 | `backend/crud_utils.py` 提供 `get_or_404(db, Model, id, msg)` 与 `apply_update(obj, schema)` |
| d | `dashboard.py:33-58` vs `sales.py:27-56` | 月度五费聚合两处独立实现同一 SQL 逻辑 | 抽 `services/stats_service.py` 供两者调用 |
| e | `orders.py:128-168`、`print_tasks.py:139-149`、`inventories.py:15-24` | **库存加减三套实现**，且 inventories 那套（`_deduct_inventory/_add_inventory`）**全项目零引用（死代码）** | 5.1 改造时统一收敛到 `inventory_service`，删除死代码 |
| f | `mcp/server.py:44-91` | `_get/_post/_put` 三份 HTTP 包装 90% 相同，且 `_get` 不解析 detail（与其他两个不一致）；错误返回 `"Error: ..."` 字符串与 dict 两种风格并存 | 合并为 `_request(method, ...)` 单函数；错误统一 dict 结构 |
| g | `main.py:26-28`、`poster_service.py:14-16`、`database.py:5-7` | `BASE_DIR/IMAGES_DIR` 三处独立推导 | 统一 `backend/config.py`（顺带收 CORS origins、日志级别等 env） |
| h | `orders.py:354-430` | CSV 导出三个分支（无明细/单明细/多明细）重复 16 列 f-string 三遍 | 提取 `_csv_row(order, item_or_none)` 函数，列定义为一等公民 |

### 6.2 【中】前端重复模式

| # | 位置 | 问题 | 建议 |
|---|------|------|------|
| a | `components/FormModal.vue`（176 行）**零引用**；Products(×5)/Orders/Colors/Filaments/Inventories/PrintTasks/Buyers/ArchivedData 共 **8 页 12 处**手写相同的 `Teleport + backdrop + 头部X + 底部按钮` 外壳 | Modal 外壳是全站最大的重复源；FormModal 的"配置驱动全量表单"抽象被实践证伪（复杂表单满足不了，于是所有页面退回手写），整文件沦为死代码 | 删除 FormModal；新建轻量 `ModalShell.vue`（只管外壳：标题/宽度/loading/关闭），各表单页只填内容插槽。见 6.3 拆分方案 |
| b | `Dashboard.vue:27-30`、`Sales.vue:180-183`、`Buyers.vue:120-123`、`ArchivedData.vue:90-93` | 金额格式化 4 份相同实现且行为不一致（空值一处返回 `¥0.00`、其余返回 `-`） | 新建 `utils/format.js`：`formatMoney/formatDateTime/formatCategory` 一处定义 |
| c | `StatusBadge.vue:13-18`、`Buyers.vue:46-52`、`PrintTasks.vue:22-28`、`PasteImport.vue:113-117`、`Orders.vue:18-25` | 状态→中文映射 5 处（与后端 6.1-a 同根） | 并入 6.1-a 的常量下发方案 |
| d | `Orders.vue:35,109-113,465-484`、`PrintTasks.vue:237-259`、`Buyers.vue:199-217` | 分页逻辑三份逐字重复 | `usePagination(fetchFn)` composable + `PaginationBar.vue` |
| e | `Settings.vue:56-108 vs 110-162`、模板 `:237-294 vs :302-358` | Games 与 Categories 两段函数级复制粘贴 | 抽 `useSimpleCrud(resourceName)` 复用（该页 6 个提交函数全部是同一骨架） |
| f | `Products.vue:149-156,167-174`、`Colors.vue:79-87`、`Buyers.vue:105-112`、`LogViewer.vue:41-45` | toggle 数组成员同构函数 5 处 | `utils/array.js` 的 `toggleItem(arr, v)` |

### 6.3 【中】Products.vue 1,245 行：五个模态内联，应拆分

结构现状：商品表单（701-904）、配方列表（907-981）、配方表单（984-1121）、介绍生成（1124-1175）、图片裁剪（1178-1211）全部内联，script 管理 5 组模态状态（74-106 行 20+ 个 ref）。配方管理与商品主列表是完全独立的业务子域，是最该先拆的。

**拆分方案**（配合 ModalShell）：

```
views/Products.vue            (~300行) 列表/筛选/拖拽排序
components/products/ProductFormModal.vue
components/products/RecipeManagerModal.vue   (内含配方表单)
components/products/DescriptionModal.vue
components/products/ImageCropModal.vue
```

**实施步骤**：先拆耦合最低的 ImageCropModal 与 DescriptionModal（纯展示+回调），再拆 RecipeManager（顺带落地 3.4 批量接口），最后 ProductForm。每拆一个本地跑通商品页全流程再继续，符合增量验证约定。

**预期收益**：单文件从 1,245 行降至 ~300 行；配方/裁剪逻辑可独立修改；状态 ref 数量减半，新增功能不再加剧主文件膨胀。

### 6.4 【低】组件设计杂项

| # | 位置 | 问题 | 建议 |
|---|------|------|------|
| a | `StatusBadge.vue` vs `SemanticBadge.vue` | 双 badge 体系并存（Orders 用前者、PrintTasks/Buyers 用后者），且 StatusBadge 同时承载订单状态/实体状态/商品分类三种语义——商品分类列用"状态徽章"渲染语义错位（`Products.vue:647`） | 统一到 SemanticBadge（tone/label 分离的设计更好），各域维护自己的 label map |
| b | `DataTable.vue:13` | `defineEmits(['sort'])` 死 emit，排序实际是组件内部状态 | 删除；分页/空态建议纳入 DataTable（配合 6.2-d） |
| c | `useApi.js` `del()` | DELETE 语义承载"取消订单/归档"等业务动作，REST 语义扭曲（历史遗留 H1 的一部分） | 中期可加 `POST /orders/{id}/cancel` 语义化端点，前端 del 保留给真删除 |
| d | `Sidebar.vue:36` | `/logs` 是内部路由却被标 `external: true`（target=_blank 打开自己） | 去掉 external 标记 |

### 6.5 【低】无全局数据层，基础数据跨页重复拉取

无 pinia；`/api/products` 被 Products/Orders/PrintTasks 三页各自拉取，`/api/settings`、`/api/games`、`/api/categories` 同样；无 keep-alive，切页即重拉。个人工具规模下主要是请求浪费与**跨页数据不同步**（Settings 改运费后 Orders 页不知道）。

**建议**：不必引入 pinia，沿用项目已有的"模块级单例 ref"模式（useTheme/useBreakpoint 先例）建 `composables/useReferenceData.js`，带 5 分钟 TTL 缓存与手动失效；仅收 products/settings/games/categories/colors 五类基础数据，订单等业务数据仍页面自管。

---

## 七、代码可读性与可维护性

### 7.1 【中】中文魔法字符串作为前后端协议值

**位置**：`views/Products.vue:187,198,273-277`

```js
type: '固定'          // 介绍模板类型
type: '可选'
// ...另一处
if (c.type === '固定') { ... }
```

中文文案被用作协议枚举，一旦调整 UI 文案（"固定"→"固定合集"）即静默破坏逻辑。同类：合集类型 `'固定'/'可选'`、订单来源映射（`Orders.vue:453`）。建议协议层改英文枚举（`fixed/optional`），中文只留在展示层映射——与 6.1-a 的常量收敛同批处理。

### 7.2 【中】功能 bug：Dashboard 快捷跳转的筛选参数被 Orders 页忽略

**位置**：`views/Dashboard.vue:61,105,145` 跳转 `/orders?status=pending_ship` 等，但 `Orders.vue` 未读 `route.query`（filters 初始为空，27-33 行）——点"待发货"卡片看到的是全部订单，筛选意图丢失。

**修复**：Orders `onMounted` 里 `Object.assign(filters, route.query)`（约 5 行），收益直观。

### 7.3 【低】硬编码与死代码清单

| 类别 | 位置 | 内容 |
|------|------|------|
| 死代码（整文件） | `components/FormModal.vue` | 零引用，176 行 |
| 死代码（函数） | `routers/inventories.py:15-24` | `_deduct_inventory/_add_inventory` 零引用 |
| 死代码（分支） | `services/poster_service.py:188-192` | if/else 两分支代码完全相同 |
| 死状态 | `views/Colors.vue:21,30,53` | `comboPickerOpen` 设置但模板未用 |
| 死变量 | `views/Products.vue:16-17` | `standardColors/comboColors` 赋值后未用 |
| 未使用导入 | `models.py:2`(Float)、`print_tasks.py:9,12`、`buyers.py:7`、`inventories.py:6`、`poster_service.py:4,12`、`description_service.py:1`、`useBreakpoint.js:1` | 一次 `ruff check --fix` + 手工确认可清完 |
| 死 emit | `DataTable.vue:13` | 见 6.4-b |
| 词库重复 | `routers/colors.py:11-22` vs `25-128` | CN_MAP 与 token 表中"黑金/青铜"等词条两处定义，易漂移 |
| 年份硬编码 | `views/Sales.vue:210` | `[2024..2028]`，2029 年需改代码；改 `new Date().getFullYear()` 推导区间 |
| 版本号双写 | `main.py:35` + `Sidebar.vue:79` | AGENTS.md 已约定手动同步；可用构建时注入（`__version__.py` 单一来源）改善 |
| pageSize 不一致 | Orders=30 / PrintTasks,Buyers=20 / LogViewer=100 | 无统一常量，非 bug 但增加认知负担 |
| 弃用 API | `main.py:66` `@app.on_event`；`datetime.utcnow`（3.12 弃用） | 迁移 lifespan context manager；见 5.5 |
| 依赖双份 | 根 `requirements.txt` 混入 mcp 依赖（`mcp[cli]`、`httpx`）与 `mcp/requirements.txt` 重复 | 分开或注释说明部署角色 |
| 外网依赖 | `templates/posters/base.html:8` Google Fonts | 内网部署字体回退致海报样式漂移；字体文件本地化到 static |
| 导入位置 | `PosterGenerator.vue:138` | script 中部 `import { onBeforeUnmount }`，应置顶 |

### 7.4 【低】可读性正面记录

整体命名一致（英文标识符 + 中文文案）、`Orders.vue:239-248` 关于 bundle 计价规则的业务注释是全项目最佳实践、`parser_service.py` 注释密度合理。**建议**：把 Orders.vue 这类"关键业务规则注释"推广到 `recalcItemPrices`、`_fill_order_defaults`、`sync_product_material_cost` 三处价格/成本核心逻辑——这三处正是历史上两次价格 bug 的案发地，注释即防回归的第一道防线。

---

## 八、测试覆盖

### 8.1 【高】全项目零测试，核心业务裸奔

**现状**：整个仓库无任何 pytest/vitest 用例（已全量扫描确认）。而本项目最核心的三块逻辑恰是**纯函数性强、易测试、历史上出过真实 bug** 的：

| 优先覆盖目标 | 理由 | 已知事故 |
|--------------|------|----------|
| 价格语义（bundle 恒用 price_single；普通子商品合集场景用 price_bundle、0 值回退） | 前端 `recalcItemPrices` + 后端 `_fill_order_defaults` 双实现 | v1.8.1 Token合集包混单归零；v1.17.0 订单价格修正 |
| 库存联动（下单扣、取消回补、bundle 展开、打印完成加） | 分支最多的写路径 | — |
| 粘贴解析器 `parse_order_text` / `_fuzzy_match` | 核心差异化功能，纯函数最易测 | — |

**优化建议**：不必追求覆盖率数字，按"每次修 bug 先补一个复现用例"的节奏建立最小安全网：

**实施步骤**：
1. `backend/tests/test_parser.py`：纯函数用例——三种状态文本、多单分隔、无括号商品名、价格 ×N 格式、买家信息提取、模糊匹配优先级。零 mock，半天可写 15-20 例。
2. `backend/tests/test_orders_flow.py`：`TestClient` + 临时 SQLite（`sqlite:///file:testdb?mode=memory&uri=true`）——创建订单扣库存、取消回补、bundle 展开扣子商品、xianyu_order_id 幂等拦截、5.1 的库存不足 400。
3. `package.json` 加 vitest（可选，优先级低）：`formatMoney` 等纯函数与 Orders 计价逻辑抽出的计算函数。
4. `AGENTS.md` 开发铁律追加一条：修 bug 必先补复现用例。

**预期收益**：价格与库存两块核心从此有回归保护；以本项目两次价格事故计，一套 30-40 例的最小测试集的期望收益远超其半天到一天的建设成本。

---

## 九、文档完善度

### 9.1 【中】README 部署章节与现状脱节

`README.md` 的部署叙事仍是 **Nginx + 18848 + deploy.sh/git pull**（65-124 行），而实际生产已切换为 **rsync 直同步 + FastAPI 直挂 + 8848**（AGENTS.md 与 commit `7cc6548`）。云服务器章节（126-163 行）引用的部署路径也已退役。版本历史止于 v1.15.2（当前 v1.17.0，缺 v1.16/v1.17 两条）。

**修复**：以 AGENTS.md 的"WSL 部署（rsync 同步模式）"章节为准重写 README 部署与架构部分（保留快速开始），版本历史补全两行；"部署细节见 AGENTS.md"的指向保留。约半小时。

### 9.2 【低】其他

- `docs/` 下 4 份文档（ROADMAP / code-review / ui-review / v1.9.0-poster-design）无索引；建议 README 或 ROADMAP 末尾加 3 行文档导航。
- `docs/code-review.md` 的复查结论（23 项仍存在）与本报告附录 A 对照后，可在其头部加一行"已由 optimization_report.md (2026-09-05) 接替维护"避免双头维护。
- 正面：`AGENTS.md` 是同类个人项目中少见的优质工程文档（部署流程、业务铁律、价格语义、MCP 重载均有记录），本次审查大量依赖它完成背景对齐。

---

## 十、优先级汇总与实施路线图

### 10.1 汇总表

| 优先级 | 编号 | 问题 | 章节 | 预估工作量 |
|--------|------|------|------|-----------|
| **高** | P0-1 | SPA catch-all 路径遍历 | §2.1 | 0.5h |
| **高** | P0-2 | 库存非原子扣减 + 超卖静默 + busy_timeout/FK 缺失 | §5.1 | 0.5-1d |
| **高** | P0-3 | 前端错误链断裂（toast + useApi 出口 + 空 catch） | §4.1 | 0.5-1d |
| **高** | P0-4 | 配方编辑串行 N+1 且静默丢数据（批量接口） | §3.4 | 0.5d |
| **高** | P0-5 | 零测试 → 最小回归安全网 | §8.1 | 0.5-1d |
| 中 | P1-1 | 后端 N+1 集群（8 项清单） | §3.1 | 1d |
| 中 | P1-2 | service 事务边界收敛 + get_db rollback | §5.3/§4.2 | 0.5d |
| 中 | P1-3 | admin 孤儿行 + 防护令牌 | §5.2/§2.2 | 0.5d |
| 中 | P1-4 | 时间基准统一（月度统计偏移修复） | §5.5 | 0.5d |
| 中 | P1-5 | 日志接口流式化 + 海报 Chromium 复用 | §3.2/§3.3 | 1d |
| 中 | P1-6 | 状态映射/CRUD 样板/库存三套收敛（后端重复） | §6.1 | 1d |
| 中 | P1-7 | ModalShell + 格式化/分页/状态映射收敛（前端重复） | §6.2 | 1d |
| 中 | P1-8 | Products.vue 拆分 | §6.3 | 1d |
| 中 | P1-9 | useApi 竞态防护 + Dashboard 跳转修复 | §3.5/§7.2 | 0.5d |
| 中 | P1-10 | MCP：单次 PUT 原子改状态+备注、_request 合并、API_BASE 进 env | §4.3/§6.1-f | 0.5d |
| 中 | P1-11 | README 部署章节重写 | §9.1 | 0.5h |
| 低 | P2-* | 安全杂项（§2.4）、性能杂项（§3.6）、可维护性杂项（§6.4/§7.3）、死代码清理、CSV BOM、字体本地化等 | 各节 | 共约 1-1.5d |

### 10.2 建议实施批次（每批 = 一个版本，符合"一版本一提交"铁律）

1. **v1.18.0「安全与数据正确性」**：P0-1 + P0-2 + P1-2 + P1-3。主题统一为"写路径可信"，互相独立、可单独验证。
2. **v1.19.0「前端体验与反馈」**：P0-3 + P0-4 + P1-9（+ toast 替代 alert）。主题"看得见的失败"。
3. **v1.20.0「重复收敛 I：后端」**：P1-6 + P1-4/§6.1-a 状态常量 + P1-10。产出 `constants.py` / `crud_utils.py` / `stats_service.py`。
4. **v1.21.0「重复收敛 II：前端」**：P1-7 + P1-8（ModalShell → 拆 Products.vue）。
5. **测试与性能项穿插**：P0-5 建议在批次 1 前先落 parser 纯函数部分（零依赖、立即可写）；P1-1/P1-5 可任选版本搭车。

> 每批完成后按 AGENTS.md 流程：本地验证 → `git push gitee master` → rsync 同步 WSL → `systemctl restart printflow`；涉及 `mcp/server.py` 的批次（P1-10）需额外重载 Hermes gateway。

---

## 附录 A：历史 code-review.md 遗留问题对照

2026-08-01 复查确认"仍存在"的 23 项中，本报告的处置情况：

| 历史编号 | 问题 | 本报告状态 |
|----------|------|-----------|
| H1 | DELETE 订单实为"取消"且写 completed_time，语义混乱 | 仍在（`orders.py:531-551`）；归入 §6.4-c 低优先级语义化改造，单用户下功能无损 |
| H2 | `_fill_order_defaults` 就地修改 Pydantic 请求对象 | 仍在（`orders.py:89`）；风险低（对象不复用），随 §6.1 重构顺带处理 |
| H4 | 多商品订单公益费率只取首个商品 | 仍在（`orders.py:117-122`）；业务上"取首个非空"尚可接受，建议至少补注释说明取舍 |
| H5 | 空字符串买家昵称断开订单-买家关联 | 仍在（`orders.py:462`）；影响面小，低优先级 |
| H7 | 状态常量散落 5 处 | 仍在；本报告 §6.1-a 给出收敛方案（P1-6） |
| H8 | `_add_column_safe` f-string SQL | 复核确认表名/列名均为调用点硬编码常量（`database.py:240-248`），**实际风险可忽略**，降级为信息项 |
| M1/M3/M5/M11 等 | N+1、日志全量读、空 catch 等 | 均已纳入本报告对应章节并更新行号 |
| M6/M8/M9/M12-14 | 见原报告 | 多数已随后续版本修复或并入本报告杂项清单 |

---

*报告完 · 生成于 2026-09-05 · 建议下次全量复审时间：v1.21.0 收敛批次完成后*
