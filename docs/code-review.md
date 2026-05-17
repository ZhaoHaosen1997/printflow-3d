# PrintFlow-3D 代码审查报告

> 审查日期：2026-05-16
> 审查范围：backend/ + frontend/ 全量源码
> 发现问题：43 项（严重 6 项、高危 12 项、中危 14 项、低危 11 项）
> 备注：本应用为单用户本地部署，无服务端并发场景，已排除竞态相关问题

---

## 一、严重问题（CRITICAL）—— 必须立即修复

### C1. 订单更新时库存未联动

**文件**：`backend/routers/orders.py` 第 342-356 行

当 `items_data` 变更时，旧明细被删除、新明细被插入，但**库存不调整**。原订单 3 件改 2 件后，被删那件的库存永远不恢复，新件的库存也不扣减，造成永久性库存偏差。

---

### C2. `useApi` 并行请求 loading 状态逻辑错误

**文件**：`frontend/src/composables/useApi.js`

多个并行请求（如 `Promise.all`）共享同一个 `loading` ref，第一个完成的请求在 `finally` 中设 `loading = false`，其他请求仍在进行中但 UI 已停止加载动画。

**修复方案**：用计数器追踪并发请求数：

```javascript
let pendingCount = 0
async function request(endpoint, options = {}) {
  pendingCount++
  loading.value = true
  try { /* ... */ }
  finally {
    pendingCount--
    if (pendingCount === 0) loading.value = false
  }
}
```

---

### C3. `ArchivedData.vue` DELETE 请求 body 被静默丢弃

**文件**：`frontend/src/views/ArchivedData.vue` 第 70 行

```javascript
await del(`/api/admin/archived`, { type, ids })  // { type, ids } 被忽略！
```

`useApi.del()` 只接受 `endpoint`，第二个参数被忽略。服务端收到无 body 的 DELETE，无法知道要删什么。

**修复**：`del()` 需支持 body 参数。

---

### C4. `PasteImport.vue` Set 响应性失效

**文件**：`frontend/src/views/PasteImport.vue` 第 89 行

```javascript
const savedIds = ref(new Set())
savedIds.value.add(index)  // Vue 3 无法检测 Set 变化！
```

`Set.prototype.add()` 不触发 Vue 响应式追踪，模板中的 `savedIds.has(idx)` 永远不更新，"已保存"状态永远不可见。

**修复**：每次 add 后替换整个 Set：`savedIds.value = new Set(savedIds.value).add(index)`，或改用数组。

---

### C5. Sales 页面缺少 chart.js / vue-chartjs 依赖

`package.json` 中只有根目录的 `chart.js` 和 `vue-chartjs`，但 `frontend/node_modules` 未安装。Sales.vue 会运行时崩溃。

**修复**：`cd frontend && npm install chart.js vue-chartjs`

---

### C6. 导出 CSV 利润计算对多商品订单有误

**文件**：`backend/routers/sales.py` 第 155-162 行

```python
item_profit = (
    (o.actual_amount or Decimal("0"))
    - (item.material_cost or Decimal("0")) * (item.quantity or 1)
    - (o.shipping_fee or Decimal("0"))       # 整单费用×每行
    - (o.packaging_fee or Decimal("0"))       # 整单费用×每行
    - (o.service_fee or Decimal("0"))         # 整单费用×每行
    - (o.charity_fee or Decimal("0"))         # 整单费用×每行
)
```

3 件商品的订单，运费/包装费/服务费被减了 3 次。整单费用应只减一次，不应逐行扣除。

---

## 二、高危问题（HIGH）—— 本迭代应修复

### H1. DELETE 订单实际是取消，语义混乱

**文件**：`backend/routers/orders.py` 第 369-389 行

DELETE 端点将状态改为 `cancelled` 并设 `completed_time`，但"取消"和"删除"是完全不同的业务语义。`completed_time` 也不应在取消时设置。

---

### H2. `_fill_order_defaults` 就地修改 Pydantic 输入模型

**文件**：`backend/routers/orders.py` 第 84-116 行

直接修改请求数据 `data.shipping_fee = s["shipping_fee"]`，隐藏副作用，后续验证逻辑可能产生意外结果。

---

### H3. 三个销售端点利润计算不一致

| 端点 | 利润公式 | 问题 |
|------|---------|------|
| `sales_overview` | revenue - material - shipping - packaging - service - charity | ✅ 正确 |
| `sales_monthly` | revenue - material_cost | ❌ 未扣各项费用 |
| `sales_by_product` | revenue - material_cost | ❌ 未扣各项费用 |

---

### H4. 多商品订单仅取首个商品的公益费率

**文件**：`backend/routers/orders.py` 第 107-112 行

```python
for item in data.items:
    product = db.query(Product).filter(Product.id == item.product_id).first()
    if product and product.charity_rate is not None:
        data.charity_fee_rate = product.charity_rate
        break  # 只取第一个
```

如果订单含不同公益费率商品，只用第一个的费率，公益费计算有误。

---

### H5. 空字符串买家昵称会断开订单-买家关联

**文件**：`backend/routers/orders.py` 第 38-49、314 行

```python
if not nickname:  # "" 也是 falsy
    return None
# update_order 中：
order.buyer_id = _upsert_buyer(db, buyer_nickname if buyer_nickname else None)
```

传空字符串时 `buyer_id` 被设为 `None`，订单与买家断开关联。

---

### H6. `_ensure_inventory` 重复定义（DRY 违反）

定义在 `inventories.py` 和 `orders.py` 两处，应提取到 `services/` 层。

---

### H7. 状态常量散落四处

| 位置 | 变量名 |
|------|--------|
| `models.py` 第 116 行 | `ORDER_STATUS` |
| `database.py` 第 99 行 | `STATUS_MIGRATION` |
| `parser_service.py` 第 10 行 | `STATUS_MAP` |
| `orders.py` 第 19 行 | `TERMINAL_STATUSES` |

应统一为 Enum 或常量模块。

---

### H8. `_add_column_safe` 存在 SQL 注入风险

**文件**：`backend/database.py` 第 138-152 行

```python
conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
```

f-string 拼接 SQL，虽然当前调用点参数硬编码，但作为通用工具函数不安全。

---

### H9. `list_inventories` GET 端点有写副作用

**文件**：`backend/routers/inventories.py` 第 36-61 行

GET 请求调用 `_ensure_inventory` 可能创建新记录并 `commit()`，读接口不应有写操作。

---

### H10. LogViewer 硬编码浅色主题，在深色主题下完全不可用

**文件**：`frontend/src/views/LogViewer.vue`

整页使用 `bg-white`、`text-gray-700`、`border-gray-200` 等浅色类，与全站深色主题冲突。应改用 CSS 变量。

---

### H11. PasteImport 示例文本包含真实个人隐私信息

**文件**：`frontend/src/views/PasteImport.vue` 第 36-37 行

包含真实姓名、手机号、详细地址，应替换为虚构数据。

---

### H12. Modal 代码在 9+ 个视图中大量重复

每个视图重复 ~30-50 行模态框代码（Teleport + 遮罩 + 卡片 + 表单 + 按钮），已有的 `FormModal.vue` 组件完全未被使用。

---

## 三、中危问题（MEDIUM）—— 推荐修复

### M1. N+1 查询（7 处）

| # | 文件 | 场景 |
|---|------|------|
| 1 | `product_service.py:6` | `calculate_recipe_cost` 逐个查 filament |
| 2 | `products.py:23` | `list_products` 逐个懒加载 recipes |
| 3 | `orders.py:220` | `list_orders` 逐个懒加载 buyer |
| 4 | `sales.py:115` | `sales_by_product` 逐个查 product |
| 5 | `orders.py:98-112` | `_fill_order_defaults` 两次循环逐个查 product |
| 6 | `orders.py:128-149` | `_deduct_order_inventory` 重复查 inventory |
| 7 | `Products.vue:311` | 配方更新逐个删除/添加 filament（前端 N+1 API 调用） |

**建议**：使用 `joinedload`/`selectinload` 预加载关联数据，或批量查询。

---

### M2. 缺少数据库索引

以下高频查询列无索引（SQLite 不自动为外键建索引）：

- `Order.status`、`Order.buyer_id`、`Order.order_time`、`Order.completed_time`
- `OrderItem.order_id`、`OrderItem.product_id`
- `PrintRecipe.product_id`、`PrintTask.status`、`PrintTask.recipe_id`
- `Buyer.nickname`（用于 `ilike` 搜索）

---

### M3. `_sync_buyer_stats` 全量加载订单到内存

**文件**：`backend/routers/orders.py` 第 52-70 行

应改用 `func.count()` + `func.sum()` SQL 聚合。

---

### M4. `sales_overview` / `sales_export` 全表扫描

**文件**：`backend/routers/sales.py` 第 29、148 行

加载所有已完成订单到内存后 Python 迭代。随数据量增长将越来越慢，应改用数据库聚合。

---

### M5. 日志端点读取所有日志文件到内存

**文件**：`backend/routers/logs.py` 第 34-52 行

全部轮转日志文件读入内存后再分页。10 × 5MB 日志 = 50MB 内存/请求。

---

### M6. `StatusBadge.vue` 中 `archived` 键重复

**文件**：`frontend/src/components/StatusBadge.vue`

`statusMap` 中 `archived` 出现两次（商品归档和订单归档），后者覆盖前者。若两者样式不同会丢样式。

---

### M7. `exportCSV` 无错误处理 + URL 过早释放

**文件**：`frontend/src/views/Sales.vue` 第 162-174 行

服务端错误时直接下载错误响应体；`URL.revokeObjectURL()` 在 `a.click()` 后同步调用，部分浏览器下载会被取消。

---

### M8. `useTheme` 每次调用创建不清理的 watchEffect

**文件**：`frontend/src/composables/useTheme.js`

5 个组件调用就创建 5 个并行 watchEffect，全部写 localStorage。应提取到模块级。

---

### M9. 无请求取消机制

**文件**：`frontend/src/composables/useApi.js`

组件卸载时在途请求仍会尝试更新状态，导致 Vue 警告。应集成 `AbortController`。

---

### M10. PrintTasks 无错误反馈

**文件**：`frontend/src/views/PrintTasks.vue`

`startTask`/`completeTask`/`failTask`/`cancelTask` 均无 try/catch，API 失败用户无感知。

---

### M11. 6 处空 catch 静默吞错

| 文件 | 函数 |
|------|------|
| `Colors.vue:63` | `confirmDelete` |
| `Filaments.vue:85` | `archiveFilament` |
| `Inventories.vue:83` | `ensureAll` |
| `LogViewer.vue:83` | `fetchInfo` |
| `Products.vue:313-314` | `deleteRecipeFilament` |
| `Products.vue:316` | `addRecipeFilament` |

---

### M12. 分页实现不统一

`Orders.vue` 有完整页码导航，`PrintTasks.vue` 和 `Buyers.vue` 只有上/下一页。应抽为共享组件。

---

### M13. Sales.vue chart 颜色硬编码，不随主题变化

**文件**：`frontend/src/views/Sales.vue`

图表 label/tooltip 颜色固定为深色值，浅色主题下不可见。

---

### M14. `theme.css` 用 `!important` 全局覆盖 Tailwind 灰色类

**文件**：`frontend/src/themes/theme.css`

```css
.text-gray-200 { color: var(--app-text) !important; }
.text-gray-300 { color: var(--app-text) !important; }
```

导致所有 `text-gray-*` 失去层次区分，且无法局部覆盖。这也是 LogViewer 显示异常的根因之一。

---

## 四、低危问题（LOW）—— 有空再修

### L1. `@app.on_event("startup")` 已弃用

**文件**：`backend/main.py` 第 50 行。应改用 `lifespan` 上下文管理器。

---

### L2. `datetime.utcnow()` 在 Python 3.12+ 已弃用

出现在 `models.py`（17+ 处）、`orders.py`、`print_tasks.py` 等。应改用 `datetime.now(timezone.utc)`。

---

### L3. 无认证/授权机制

所有 11 个路由器暴露 CRUD 操作且零鉴权，`admin.py` 的批量永久删除端点尤其危险。虽为单用户本地部署，但至少应加简单 token 认证。

---

### L4. `recalcTotal` 覆盖有意设为 0 的 actual_amount

**文件**：`frontend/src/views/Orders.vue` 第 209-218 行

免费样品订单 `actual_amount = 0` 会被自动填充为计算总额。

---

### L5. `editOrder` 使用 `.then()` 代替 `async/await`

**文件**：`frontend/src/views/Orders.vue` 第 131-154 行

唯一一处用 `.then()`，且无 `.catch()`。

---

### L6. 无 404 兜底路由

**文件**：`frontend/src/router/index.js`

无效路径显示空白页。应加 `/:pathMatch(.*)*` 兜底。

---

### L7. DataTable 骨架屏用 `Math.random()` 导致重渲染闪烁

**文件**：`frontend/src/components/DataTable.vue` 第 73 行

每次渲染产生不同宽度值，破坏虚拟 DOM diff。

---

### L8. 路由切换不重置滚动位置

**文件**：`frontend/src/router/index.js`

应加 `scrollBehavior() { return { top: 0 } }`。

---

### L9. 无全局错误处理器

**文件**：`frontend/src/main.js`

缺少 `app.config.errorHandler`，未捕获的异常只在控制台可见。

---

### L10. `FormModal.vue` 已定义但从未使用

应统一采用或删除。

---

### L11. `.btn-danger` CSS 在 4 个 scoped style 中重复

**文件**：`DataTable.vue`、`FormModal.vue`、`Products.vue`、`Colors.vue`

应提取到全局样式。

---

## 五、优化建议汇总

| 类别 | 建议 | 优先级 |
|------|------|--------|
| **查询性能** | 补充数据库索引（见 M2）| P0 |
| **查询性能** | N+1 改用 joinedload（见 M1）| P0 |
| **查询性能** | sales 聚合改 SQL 级别（见 M4）| P1 |
| **前端性能** | useApi 加 AbortController（见 M10）| P1 |
| **前端性能** | 引入 Pinia 缓存共享数据，避免重复请求 | P2 |
| **前端性能** | PrintTasks 配方选择器用轻量 API（见 L23）| P2 |
| **代码质量** | 统一状态枚举（见 H7）| P1 |
| **代码质量** | Modal 抽为共享组件（见 H12）| P1 |
| **代码质量** | 分页抽为共享组件（见 M13）| P2 |
| **代码质量** | 统一错误处理模式（见 M12）| P1 |
| **安全性** | 加简单 token 认证（见 L3）| P2 |
| **安全性** | 解析器输入加长度限制 | P2 |
| **安全性** | 替换示例文本中的 PII（见 H11）| P0 |
| **架构** | `del()` 支持 body 参数（见 C5）| P0 |
| **架构** | 生产环境 API 基地址可配置 | P2 |

---

## 六、修复优先级路线图

```
第一批（立即）：C1-C6 + H11
  ├── 订单更新库存联动（C1）
  ├── useApi loading 计数器 + del() body 支持（C2, C3）
  ├── Set 响应性修复（C4）
  ├── npm install chart.js vue-chartjs（C5）
  ├── 导出利润计算修正（C6）
  └── 替换示例文本 PII（H11）

第二批（本周）：H1-H5, H9, M1-M2
  ├── DELETE→取消语义修正（H1）
  ├── 利润计算统一（H3）
  ├── 公益费率多商品处理（H4）
  ├── 空字符串买家保护（H5）
  ├── N+1 查询批量优化（M1）
  └── 补充数据库索引（M2）

第三批（下周）：剩余 H 项 + M 项
  └── DRY 统一、Modal 组件化、错误处理统一等
```

---

> 本报告由代码审查自动生成，建议按优先级逐批修复，每批修复后回归测试。
