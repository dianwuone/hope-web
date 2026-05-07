# Quentin Window Backend MVP

这是根据 [数据说明与后台规划](../hope/docs/数据说明与后台规划.md) 落地的第一版最小可用后台。

## 当前目标

这一版只先承接一期里最适合先做通的内容域：

1. 管理员登录
2. 栏目读取
3. 标签读取
4. 文章列表、详情读取
5. 后台文章新增、编辑、删除
6. 项目管理：产品 / 游戏 / 实验室 的增删改查
7. 商品管理：尝鲜商品的增删改查
8. 全站配置管理
9. 页面配置管理
10. 产品、实验室、尝鲜商品等前端模拟数据入库

这样做的原因很直接：

1. 文档里明确建议优先从 `articles`、`content_categories`、`content_tags` 开始
2. 当前前端 `src/api/index.js` 还在用假请求，文章数据最容易先替换成真实接口
3. 先用 SQLite 跑通“后台管理 -> 数据落盘 -> 前台读取”的闭环，并继续以 SQLite 作为生产数据库

## 目录结构

```txt
kuntin/
├── backend/
│   ├── admin/            # pure-admin 管理前端
│   ├── app/              # FastAPI 服务
│   ├── data/
│   │   ├── app.db
│   │   └── content.json
│   ├── requirements.txt
│   ├── .venv/
│   ├── start.ps1
│   ├── stop.ps1
│   ├── start-admin.ps1
│   └── build-admin.ps1
├── hope/
└── shucai/
```

## 启动方式

### 启动后端 API

```bash
cd backend
.\start.ps1
```

### 启动 pure-admin 管理前端（开发模式）

```bash
cd backend
.\start-admin.ps1
```

### 构建 pure-admin 管理前端（供 FastAPI `/admin` 使用）

```bash
cd backend
.\build-admin.ps1
```

启动后可访问：

1. 后端健康检查：`http://127.0.0.1:4100/health`
2. FastAPI 托管后台：`http://127.0.0.1:4100/admin`
3. pure-admin 开发服务：`http://127.0.0.1:8848`

默认账号：

- 用户名：`admin`
- 密码：`admin123`

## 已提供接口

### 公共读取接口

1. `GET /api/columns`
2. `GET /api/tags`
3. `GET /api/articles`
4. `GET /api/articles/:slug`
5. `GET /api/site-configs`
6. `GET /api/page-configs/:pageKey`
7. `GET /api/projects`
8. `GET /api/projects/:slug`
9. `GET /api/offers`
10. `GET /api/offers/:slug`
11. `GET /api/bootstrap`

`GET /api/articles` 支持：

- `q`：关键词搜索
- `column`：按栏目 slug 过滤
- `tag`：按标签 slug 或名称过滤

`GET /api/bootstrap` 会一次性返回站点公共配置、页面配置和核心内容列表，适合用户前端的全局初始化与菜单渲染。

### 后台管理接口

1. `POST /api/admin/login`
2. `GET /api/admin/articles`
3. `POST /api/admin/articles`
4. `PUT /api/admin/articles/:id`
5. `DELETE /api/admin/articles/:id`
6. `GET /api/admin/site-configs`
7. `POST /api/admin/site-configs`
8. `PUT /api/admin/site-configs/:id`
9. `DELETE /api/admin/site-configs/:id`
10. `GET /api/admin/page-configs`
11. `POST /api/admin/page-configs`
12. `PUT /api/admin/page-configs/:id`
13. `DELETE /api/admin/page-configs/:id`
14. `GET /api/admin/projects`
15. `POST /api/admin/projects`
16. `PUT /api/admin/projects/:id`
17. `DELETE /api/admin/projects/:id`
18. `GET /api/admin/offers`
19. `POST /api/admin/offers`
20. `PUT /api/admin/offers/:id`
21. `DELETE /api/admin/offers/:id`

除登录外，后台接口都需要 `Authorization: Bearer <token>`。

## 数据说明

当前数据层策略是：

1. 开发环境默认使用 `SQLite`，数据库文件是 `backend/data/app.db`
2. 首次启动时会从 `backend/data/content.json` 导入种子数据
3. 生产环境继续使用 SQLite，数据库文件默认是 `backend/data/app.db`
4. 可通过 `SQLITE_DB_PATH` 指定数据库文件路径
5. `site_configs` 用于全站通用配置
6. `page_configs` 用于页面级 JSON 配置
7. `projects` 用于承接 `hope/src/data/products/products.js` 与 `hope/src/data/lab/labs.js`
8. `offers` 用于承接 `hope/src/data/products/products.js` 中的 `tryOffers`

## 当前已收敛的 hope 模拟数据

下面这些前端静态数据已经在 `backend` 的 SQLite 中有对应落点：

1. `articles.js`、`columns.js`
2. `products.js` 中的 `products`
3. `products.js` 中的 `tryOffers`
4. `labs.js`
5. `navigation.js`
6. `pages.js` 中的主要页面基础配置
7. 游戏数据已开始收敛到 `projects`，当前已包含 `pinyin-adventure`

说明：

1. 当前是“数据已入库、接口已提供”
2. 管理后台已切换为 pure-admin 前端为主，旧 `public/admin.html` 已移除
3. 管理后台已支持文章、项目、商品、配置的基本 CRUD
4. `hope` 前端本身还没有全部切换到读取这些接口
5. 下一步应逐步把 `hope/src/api/index.js` 从本地模拟实现改为真实 HTTP 请求

例如：

```bash
$env:SQLITE_DB_PATH='D:\code\AI\kuntin\backend\data\app.db'
```

后续扩展时，优先顺序建议保持和规划文档一致：

1. 先把 `projects` 接进来
2. 再补 `beta_applications`、`community_leads`、`wishlist_items`
3. 再做 `offers`、`orders`
4. 最后做 `analytics_events`

## 下一步建议

如果继续往正式后台推进，建议按下面顺序升级：

1. 把明文密码改成哈希存储
2. 把内存 token 改成 JWT
3. 增加 Alembic 迁移
4. 接入 `projects`、报名、心愿单
5. 让前端 `src/api/index.js` 优先接入文章读取接口

## 自动部署

如果你把 `backend/` 推到第三方 GitHub 仓库，并希望服务器每天自动拉取最新代码并部署，可以直接使用：

```bash
bash deploy.sh
```

这个脚本会做这些事：

1. `git fetch` + `reset --hard` 到指定分支
2. 更新 Python 依赖
3. 构建 `backend/admin`
4. 重启后端服务（如果你配置了服务名或自定义命令）

### 推荐 cron

每天凌晨 3 点执行一次：

```cron
0 3 * * * cd /www/wwwroot/code/kuntin/backend && bash deploy.sh >> /www/wwwroot/code/kuntin/backend/deploy.log 2>&1
```

### 可选环境变量

1. `BRANCH`：默认 `main`
2. `PYTHON_BIN`：默认 `python3`
3. `BACKEND_SERVICE_NAME`：例如 `quentin-window-backend`
4. `RESTART_CMD`：自定义重启命令，优先于服务名
