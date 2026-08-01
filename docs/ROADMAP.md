# PrintFlow-3D 后续规划

> 更新日期：2026-08-01。v1.11.0 ~ v1.14.0 已全部发布，规划详情移入文末「已发布」表；后续仅剩 v2.0.0 未实施。

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
| v1.14.0 | MCP 录单工具层（search_products / parse_order_text / create_order / get_product_detail，服务 Hermes 与 Web 双入口） |
| v1.13.0 | 游戏大类 + 商品分类双层配置（games / categories 表 + product_games 关联，商品 category 迁移为 category_id 外键） |
| v1.12.0 | 移动端适配（侧边栏抽屉、DataTable 卡片模式、表单弹窗全屏化） |
| v1.11.0 | 仪表盘首页 + 销售统计查询优化（SQL 聚合消除 N+1 与全表扫描） |
| v1.10.0 | 商品自定义排序（sort_order + 拖拽排序 + 长图排序联动） |
| v1.9.1 | 图片上传裁剪 + 弹窗拖拽修复 + 不单卖标识 + 配色预览分组 + 表单样式优化 |
| v1.9.0 | 商品长图生成（Jinja2 + Playwright 截图，羊皮纸/暗金双主题） |
| v1.8.1 | 合集价修复 + 订单表单增强（闲鱼号/自动费用/公益按需）+ 买家好评标签 + Pi 部署迁移 |
| v1.8.0 | Nginx + systemd 生产部署（WSL2）→ 后迁移至 Raspberry Pi |
