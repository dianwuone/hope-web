from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from .models import AdminUser, Article, ContentCategory, ContentTag, PageConfig, SiteConfig


DEFAULT_SITE_CONFIGS = [
    {
        "configKey": "hero_title",
        "configValue": json.dumps({"value": "QUENTIN WINDOW"}, ensure_ascii=False),
        "groupName": "home",
        "remark": "首页主标题",
    },
    {
        "configKey": "hero_subtitle",
        "configValue": json.dumps({"value": "独立开发者的窗口 — 产品、内容与实验"}, ensure_ascii=False),
        "groupName": "home",
        "remark": "首页主副标题",
    },
    {
        "configKey": "contact_email",
        "configValue": json.dumps({"value": ""}, ensure_ascii=False),
        "groupName": "contact",
        "remark": "联系邮箱",
    },
    {
        "configKey": "community_wechat",
        "configValue": json.dumps({"value": ""}, ensure_ascii=False),
        "groupName": "community",
        "remark": "社区微信号",
    },
]

DEFAULT_PAGE_CONFIGS = [
    {
        "pageKey": "home",
        "title": "首页配置",
        "configJson": json.dumps(
            {
                "hero": {
                    "badge": "AI x 产品 x 游戏",
                    "title": "用 AI 提升工作与生活，用产品与游戏解决真实问题",
                    "subtitle": "我是 Quentin，一名独立开发者与产品探索者。",
                },
                "community": {
                    "title": "加入我的私域社区",
                    "subtitle": "获取最新动态、产品内测资格、限时福利与深度交流。",
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        "status": "active",
        "remark": "首页 Hero 与社区配置",
    },
    {
        "pageKey": "community",
        "title": "社区页配置",
        "configJson": json.dumps(
            {
                "title": "加入我的私域社区",
                "subtitle": "和我一起，持续探索 AI 提效与产品创造。",
                "benefits": ["获取最新动态", "产品内测资格", "限时福利", "深度交流"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        "status": "active",
        "remark": "加入社区页基础配置",
    },
]


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def seed_if_empty(db: Session, seed_file: Path) -> None:
    has_data = db.query(ContentCategory).first()
    if not has_data:
        payload = json.loads(seed_file.read_text(encoding="utf-8"))

        for item in payload.get("adminUsers", []):
            db.add(AdminUser(**item))

        columns_by_id: dict[int, ContentCategory] = {}
        for item in payload.get("columns", []):
            model = ContentCategory(**item)
            columns_by_id[item["id"]] = model
            db.add(model)

        tags_by_id: dict[int, ContentTag] = {}
        for item in payload.get("tags", []):
            model = ContentTag(**item)
            tags_by_id[item["id"]] = model
            db.add(model)

        db.flush()

        for source in payload.get("articles", []):
            item = dict(source)
            tag_ids = item.pop("tagIds", [])
            item.pop("publishedAt", None)
            item.pop("createdAt", None)
            item.pop("updatedAt", None)
            article = Article(
                **item,
                publishedAt=parse_datetime(source.get("publishedAt")),
                createdAt=parse_datetime(source["createdAt"]),
                updatedAt=parse_datetime(source["updatedAt"]),
            )
            article.tags = [tags_by_id[tag_id] for tag_id in tag_ids if tag_id in tags_by_id]
            article.column = columns_by_id[item["columnId"]]
            db.add(article)

    now = datetime.utcnow()
    existing_site_keys = {item.configKey for item in db.query(SiteConfig).all()}
    for item in DEFAULT_SITE_CONFIGS:
        if item["configKey"] not in existing_site_keys:
            db.add(SiteConfig(**item, updatedAt=now))

    existing_page_keys = {item.pageKey for item in db.query(PageConfig).all()}
    for item in DEFAULT_PAGE_CONFIGS:
        if item["pageKey"] not in existing_page_keys:
            db.add(PageConfig(**item, updatedAt=now))

    db.commit()
