# Quentin Window Backend MVP

这是根据 [数据说明与后台规划](../hope/docs/数据说明与后台规划.md) 落地的第一版最小可用后台。

## 当前目标

这一版只先承接一期里最适合先做通的内容域：

1. 管理员登录
2. 栏目读取
3. 标签读取
4. 文章列表、详情读取
5. 后台文章新增、编辑、删除
6. 全站配置管理
7. 页面配置管理

这样做的原因很直接：

1. 文档里明确建议优先从 `articles`、`content_categories`、`content_tags` 开始
2. 当前前端 `src/api/index.js` 还在用假请求，文章数据最容易先替换成真实接口
3. 先用 SQLite 跑通“后台管理 -> 数据落盘 -> 前台读取”的闭环，再平滑切 PostgreSQL

## 目录结构

```txt
kuntin/
├── backend/
│   ├── data/
│   │   └── content.json
│   ├── public/
│   │   └── admin.html
│   ├── app/
│   ├── public/
│   ├── data/
│   ├── requirements.txt
│   └── .venv/
├── hope/
└── shucai/
```

## 启动方式

```bash
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 4100
```

默认端口：`4100`

启动后可访问：

1. 后台页面：`http://localhost:4100/admin`
2. 健康检查：`http://localhost:4100/health`

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

`GET /api/articles` 支持：

- `q`：关键词搜索
- `column`：按栏目 slug 过滤
- `tag`：按标签 slug 或名称过滤

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

除登录外，后台接口都需要 `Authorization: Bearer <token>`。

## 数据说明

当前数据层策略是：

1. 开发环境默认使用 `SQLite`，数据库文件是 `backend/data/app.db`
2. 首次启动时会从 `backend/data/content.json` 导入种子数据
3. 生产环境可通过 `DATABASE_URL` 切换到 `PostgreSQL`
4. `site_configs` 用于全站通用配置
5. `page_configs` 用于页面级 JSON 配置

例如：

```bash
$env:DATABASE_URL='postgresql+psycopg://user:password@host:5432/quentin_window'
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
