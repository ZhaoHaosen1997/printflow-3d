# PrintFlow-3D

个人闲鱼 3D 打印副业管理系统，覆盖商品/耗材/订单/买家/库存/打印任务/销售统计全链路。

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | Python 3.11+ / FastAPI / SQLAlchemy ORM / Pydantic |
| 前端 | Vue 3 (Composition API) / Vite / TailwindCSS 3 / Lucide Icons |
| 数据库 | SQLite（`data/app.db`），预留 PostgreSQL 切换 |
| 部署 | Nginx + systemd（WSL2 / 云服务器通用） |

## 快速开始（Windows 开发）

```bash
# 1. 后端
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r ../requirements.txt
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8848

# 2. 前端（新终端）
cd frontend
npm install
npx vite --host
```

浏览器访问 `http://localhost:5173`（Vite 开发服务器，自动代理 API 到 `:8848`）。

或一键启动：双击 `start.bat`。

## 目录结构

```
printflow-3d/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── database.py          # 数据库初始化 + 种子数据
│   ├── models.py            # SQLAlchemy 模型
│   ├── schemas.py           # Pydantic 校验
│   ├── routers/             # API 路由（products, orders, ...）
│   ├── services/            # 业务逻辑层
│   └── middleware/          # 日志中间件
├── frontend/
│   └── src/
│       ├── views/           # 页面组件
│       ├── components/      # 公共组件
│       └── composables/     # 组合式 API（useApi, useOrders, ...）
├── data/
│   ├── app.db               # SQLite 数据库（运行后生成）
│   ├── images/              # 商品图片
│   └── logs/                # 业务日志
├── nginx.conf               # Nginx 站点配置
├── printflow.service        # systemd 服务文件
├── deploy.sh                # 一键部署脚本
├── setup_wsl.sh             # WSL 首次初始化脚本
├── start.sh / stop.sh       # WSL 服务启停
└── requirements.txt
```

---

## WSL2 部署

WSL2 Debian 作为本地生产环境，与云服务器配置一致。

### 首次部署

```bash
# WSL 中执行
cd /mnt/c/mycode/printflow-3d
./setup_wsl.sh
```

脚本自动完成：系统依赖安装 → Python venv → 前端构建 → Nginx 配置 → systemd 服务注册 → 启用 WSL systemd。

完成后在 Windows PowerShell 中重启 WSL：

```powershell
wsl --shutdown
```

重新打开 WSL Debian，服务自动启动。浏览器访问 `http://localhost:18848`。

### 日常更新

Windows 开发完成后，WSL 中一键同步：

```bash
cd /home/zhaohaosen/applications/printflow-3d
./deploy.sh
```

脚本自动完成：
1. rsync 从 `/mnt/c/mycode/printflow-3d/` 同步代码（保护运行时数据：db/logs/images）
2. 检测 backend 变更 → 自动重启后端
3. 检测 frontend 变更 → 自动重新构建
4. 检测 nginx/systemd 配置变更 → 自动更新并 reload

### 服务管理

```bash
./start.sh      # 启动所有服务
./stop.sh       # 停止所有服务

# 查看状态
sudo systemctl status printflow nginx

# 查看后端日志
sudo journalctl -u printflow -f
```

### 架构

```
Windows 浏览器 → http://localhost:18848 (Nginx in WSL2)
  ├── /           → frontend/dist/ 静态文件（SPA fallback）
  ├── /api/*      → proxy_pass http://127.0.0.1:8848
  └── /images/*   → 静态文件服务
```

---

## 云服务器部署

与 WSL 部署模式一致，差异仅在代码来源。

### 首次部署

```bash
# 1. 克隆仓库
git clone https://github.com/ZhaoHaosen1997/printflow-3d.git /opt/printflow-3d
cd /opt/printflow-3d

# 2. 修改部署脚本中的路径（如需要）
#    将 /home/zhaohaosen 替换为实际用户目录

# 3. 初始化
./setup_wsl.sh

# 4. 配置防火墙
sudo ufw allow 18848/tcp
```

### 配置域名 + HTTPS（可选）

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

修改 `nginx.conf` 添加 `server_name your-domain.com;`，重新运行 `./deploy.sh`。

### 更新

```bash
cd /opt/printflow-3d
git pull origin master
./deploy.sh
```

---

## 核心功能

- **粘贴导入**：正则引擎解析闲鱼订单文本，自动匹配商品、展开合集、创建买家
- **打印任务管理**：关联配方，完成时自动更新打印计数 + 成品库存
- **成本实时计算**：配方成本由耗材克数 × 单价实时算出，不持久化
- **销售统计**：利润报表、月度趋势图、商品排行、CSV 导出
- **买家管理**：昵称去重、自动聚合、标签系统
- **合集商品**：Token 合集包下单自动展开子商品，联动扣减库存

## 版本历史

| 版本 | 内容 |
|------|------|
| v1.5.0 | 打印任务管理 |
| v1.6.0 | 买家管理 + 标签 + 统计 |
| v1.7.0 | 销售统计 + 利润报表 + CSV 导出 |
| v1.7.3 | 代码质量修复 + 订单导出增强 |
| v1.8.0 | Nginx + systemd 生产部署（WSL2 / 云服务器） |
| v1.8.1 | 合集价修复 + 订单表单增强 + 买家好评标签 + Pi 部署迁移 |
| v1.9.0 | 商品长图生成（Jinja2 + Playwright 截图，羊皮纸/暗金双主题） |
| v1.9.1 | 图片上传裁剪 + 弹窗拖拽修复 + 不单卖标识 + 配色预览分组 + 表单样式优化 |
| v1.10.0 | 商品自定义排序（sort_order + 拖拽排序 + 长图排序联动） |
| v1.11.0 | 仪表盘首页 + 销售统计查询优化 |
| v1.12.0 | 移动端适配 |
| v1.13.0 | 游戏大类 + 商品分类双层配置 |
| v1.14.0 | MCP 录单工具层 |
| v1.14.1 | 配色修复：组合色 swatches 自动推导 + 中文颜色名分词翻译（新增 100+ 颜色词库） |
| v1.15.0 | 自动生成商品介绍（固定合集 Token合集包 / 自选合集，配色说明自动生成 + 商品页一键复制） |
| v1.15.1 | UI 修复：主题色改通道式定义（/opacity 恢复生效）+ 语义色 token（success/danger/warning/info）+ LogViewer 接入主题 + 浅色主题对比度提升 |

> 当前生产环境已迁移至 Raspberry Pi（内网 `http://192.168.10.10:8848`），部署/版本迭代细节见 AGENTS.md。
