from __future__ import annotations

import asyncio
import json
from datetime import datetime
from hashlib import sha256
import re
from secrets import randbelow
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.schema import CreateColumn

from .auth import login as do_login
from .auth import get_frontend_session, hash_password, login_frontend, require_auth, require_frontend_auth
from .database import BASE_DIR, Base, SessionLocal, engine, get_db
from .models import (
    AdItem,
    Article,
    ArticleComment,
    ArticleInteraction,
    BetaApplication,
    CommunityLead,
    ContentCategory,
    ContentTag,
    EmailVerificationCode,
    FrontendUser,
    Offer,
    PageConfig,
    Project,
    ReadingHistory,
    SiteConfig,
    WishlistItem,
)
from .schemas import (
    AdItemOut,
    AdItemWrite,
    AiContentPublishRequest,
    AiContentPublishResponse,
    AdminEmailNotificationRequest,
    ArticleCommentListResponse,
    ArticleCommentOut,
    ArticleCommentWrite,
    ArticleEngagementResponse,
    ArticleInteractionRequest,
    ArticleInteractionResponse,
    ArticleOut,
    ArticleWrite,
    BetaApplicationOut,
    BetaApplicationUpdate,
    BetaApplicationWrite,
    CaptchaResponse,
    CommunityLeadOut,
    CommunityLeadUpdate,
    CommunityLeadWrite,
    DashboardResponse,
    DatabaseSyncRequest,
    DatabaseSyncResponse,
    DeleteResponse,
    EmailVerificationSendResponse,
    FrontendAuthResponse,
    FrontendUserListItem,
    FrontendUserLoginRequest,
    FrontendProfileSummary,
    FrontendUserPasswordChangeRequest,
    FrontendUserPasswordResetRequest,
    FrontendUserProfileUpdate,
    FrontendUserPasswordResetCodeRequest,
    FrontendUserProfileOut,
    FrontendUserRegisterRequest,
    FrontendUserUpdate,
    HealthResponse,
    LoginResponse,
    OfferOut,
    OfferWrite,
    PageConfigOut,
    PageConfigWrite,
    ProjectOut,
    ProjectWrite,
    ReadingHistoryOut,
    ReadingHistoryWrite,
    SearchResponse,
    SiteConfigOut,
    SiteConfigWrite,
    UserLoginRequest,
    WishlistOut,
    WishlistUpdate,
    WishlistWrite,
)
from .mail import get_mail_settings, send_email
from .timeutils import current_time, current_timestamp_ms
from .seed import seed_if_empty
from .security import (
    apply_login_delay,
    build_auth_error_payload,
    cleanup_security_state,
    clear_login_failures,
    create_captcha,
    needs_captcha,
    verify_captcha,
)


app = FastAPI(title="Quentin Window Backend", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ADMIN_DIST_DIR = BASE_DIR / "admin" / "dist"
ADMIN_DIST_INDEX = ADMIN_DIST_DIR / "index.html"
ADMIN_DIST_STATIC = ADMIN_DIST_DIR / "static"
ADMIN_DIST_PLATFORM_CONFIG = ADMIN_DIST_DIR / "platform-config.json"
ADMIN_DIST_FAVICON = ADMIN_DIST_DIR / "favicon.ico"
ADMIN_DIST_LOGO = ADMIN_DIST_DIR / "logo.svg"
SEED_FILE = BASE_DIR / "data" / "content.json"
AUTH_INPUT_MAX_LENGTH = 128

FRONTEND_USER_TABLE_PATCHES = {
    "frontend_users": [
        "CREATE TABLE frontend_users (id INTEGER PRIMARY KEY, username VARCHAR(50) NOT NULL UNIQUE, email VARCHAR(100) NOT NULL UNIQUE, passwordHash VARCHAR(255) NOT NULL, nickname VARCHAR(50) NOT NULL, avatar VARCHAR(255) NOT NULL DEFAULT '', bio TEXT, status VARCHAR(20) NOT NULL DEFAULT 'active', lastLoginAt DATETIME, createdAt DATETIME NOT NULL, updatedAt DATETIME NOT NULL)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_frontend_users_username ON frontend_users (username)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_frontend_users_email ON frontend_users (email)",
    ],
    "wishlist_items.userId": [
        "ALTER TABLE wishlist_items ADD COLUMN userId INTEGER",
        "CREATE INDEX IF NOT EXISTS ix_wishlist_items_userId ON wishlist_items (userId)",
    ],
    "community_leads.userId": [
        "ALTER TABLE community_leads ADD COLUMN userId INTEGER",
        "CREATE INDEX IF NOT EXISTS ix_community_leads_userId ON community_leads (userId)",
    ],
    "beta_applications.userId": [
        "ALTER TABLE beta_applications ADD COLUMN userId INTEGER",
        "CREATE INDEX IF NOT EXISTS ix_beta_applications_userId ON beta_applications (userId)",
    ],
    "article_interactions.userId": [
        "ALTER TABLE article_interactions ADD COLUMN userId INTEGER",
        "CREATE INDEX IF NOT EXISTS ix_article_interactions_userId ON article_interactions (userId)",
    ],
    "article_interactions.isCanceled": [
        "ALTER TABLE article_interactions ADD COLUMN isCanceled BOOLEAN NOT NULL DEFAULT 0",
    ],
    "article_comments.userId": [
        "ALTER TABLE article_comments ADD COLUMN userId INTEGER",
        "CREATE INDEX IF NOT EXISTS ix_article_comments_userId ON article_comments (userId)",
    ],
    "email_verification_codes": [
        "CREATE TABLE email_verification_codes (id INTEGER PRIMARY KEY, userId INTEGER, email VARCHAR(100) NOT NULL, purpose VARCHAR(50) NOT NULL, codeHash VARCHAR(255) NOT NULL, expiresAt DATETIME NOT NULL, usedAt DATETIME, createdAt DATETIME NOT NULL)",
        "CREATE INDEX IF NOT EXISTS ix_email_verification_codes_userId ON email_verification_codes (userId)",
        "CREATE INDEX IF NOT EXISTS ix_email_verification_codes_email ON email_verification_codes (email)",
        "CREATE INDEX IF NOT EXISTS ix_email_verification_codes_purpose ON email_verification_codes (purpose)",
        "CREATE INDEX IF NOT EXISTS ix_email_verification_codes_expiresAt ON email_verification_codes (expiresAt)",
    ],
    "frontend_users.signature": [
        "ALTER TABLE frontend_users ADD COLUMN signature TEXT NOT NULL DEFAULT ''",
    ],
    "reading_histories": [
        "CREATE TABLE reading_histories (id INTEGER PRIMARY KEY, userId INTEGER NOT NULL, articleSlug VARCHAR(150) NOT NULL, articleTitle VARCHAR(200) NOT NULL DEFAULT '', articleSummary TEXT, coverImage VARCHAR(255) NOT NULL DEFAULT '', authorName VARCHAR(50) NOT NULL DEFAULT '', categoryName VARCHAR(100) NOT NULL DEFAULT '', viewedAt DATETIME NOT NULL, createdAt DATETIME NOT NULL, updatedAt DATETIME NOT NULL)",
        "CREATE INDEX IF NOT EXISTS ix_reading_histories_userId ON reading_histories (userId)",
        "CREATE INDEX IF NOT EXISTS ix_reading_histories_articleSlug ON reading_histories (articleSlug)",
        "CREATE INDEX IF NOT EXISTS ix_reading_histories_viewedAt ON reading_histories (viewedAt)",
    ],
}

EMAIL_CODE_EXPIRES_SECONDS = 10 * 60
EMAIL_CODE_PURPOSE_RESET_PASSWORD = "reset_password"


def serialize_column(column: ContentCategory | None) -> dict | None:
    if not column:
        return None
    return {
        "id": column.id,
        "name": column.name,
        "slug": column.slug,
        "categoryType": column.categoryType,
        "description": column.description,
        "sortOrder": column.sortOrder,
        "status": column.status,
    }


def serialize_tag(tag: ContentTag) -> dict:
    return {
        "id": tag.id,
        "name": tag.name,
        "slug": tag.slug,
        "tagType": tag.tagType,
        "status": tag.status,
    }


def serialize_article(article: Article) -> dict:
    favorite_count = len(
        [item for item in getattr(article, "interactions", []) if item.interactionType == "favorite"]
    )
    comment_count = len(
        [item for item in getattr(article, "comments", []) if item.status == "published"]
    )
    return {
        "id": article.id,
        "title": article.title,
        "slug": article.slug,
        "summary": article.summary,
        "contentBody": article.contentBody,
        "authorName": article.authorName,
        "columnId": article.columnId,
        "tagIds": [tag.id for tag in article.tags],
        "coverImage": article.coverImage,
        "heroTone": article.heroTone,
        "status": article.status,
        "sourceType": article.sourceType,
        "publishedAt": article.publishedAt,
        "viewCount": article.viewCount,
        "likeCount": article.likeCount,
        "favoriteCount": favorite_count,
        "commentCount": comment_count,
        "createdAt": article.createdAt,
        "updatedAt": article.updatedAt,
        "column": serialize_column(article.column),
        "tags": [serialize_tag(tag) for tag in article.tags],
    }


def serialize_site_config(item: SiteConfig) -> dict:
    return {
        "id": item.id,
        "configKey": item.configKey,
        "configValue": item.configValue,
        "groupName": item.groupName,
        "remark": item.remark,
        "updatedAt": item.updatedAt,
    }


def serialize_page_config(item: PageConfig) -> dict:
    return {
        "id": item.id,
        "pageKey": item.pageKey,
        "title": item.title,
        "configJson": item.configJson,
        "status": item.status,
        "remark": item.remark,
        "updatedAt": item.updatedAt,
    }


def parse_json_list(value: str) -> list:
    try:
        data = json.loads(value or "[]")
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def parse_json_dict(value: str) -> dict:
    try:
        data = json.loads(value or "{}")
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def parse_config_value(value: str, fallback):
    raw_value = (value or "").strip()
    if not raw_value:
        return fallback

    parsed = parse_json_dict(value)
    if parsed:
        if isinstance(parsed, dict) and set(parsed.keys()) == {"value"}:
            return parsed["value"]
        return parsed
    parsed_list = parse_json_list(value)
    if parsed_list:
        return parsed_list
    return raw_value


def is_public_status(value: str | None) -> bool:
    normalized = (value or "").strip().lower()
    return normalized not in {"draft", "inactive", "archived", "disabled", "deleted"}


EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_RE = re.compile(r"^\+?[0-9][0-9\s-]{6,18}[0-9]$")
WECHAT_RE = re.compile(r"^[a-zA-Z][-_a-zA-Z0-9]{5,19}$")


def validate_contact_value(contact_type: str, contact_value: str) -> None:
    value = contact_value.strip()
    if not value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="联系方式不能为空")
    if contact_type == "email" and not EMAIL_RE.match(value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱格式不正确")
    if contact_type == "phone" and not PHONE_RE.match(value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="电话号码格式不正确")
    if contact_type == "wechat" and not WECHAT_RE.match(value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="微信号格式不正确")


def serialize_project(item: Project) -> dict:
    return {
        "id": item.id,
        "slug": item.slug,
        "name": item.name,
        "projectType": item.projectType,
        "title": item.title,
        "subtitle": item.subtitle,
        "shortDesc": item.shortDesc,
        "summary": item.summary,
        "description": item.description,
        "coverImage": item.coverImage,
        "bannerImage": item.bannerImage,
        "status": item.status,
        "stage": item.stage,
        "supportStatus": item.supportStatus,
        "price": item.price,
        "originalPrice": item.originalPrice,
        "tags": parse_json_list(item.tagsJson),
        "features": parse_json_list(item.featuresJson),
        "highlights": parse_json_list(item.highlightsJson),
        "faq": parse_json_list(item.faqJson),
        "testimonials": parse_json_list(item.testimonialsJson),
        "extra": parse_json_dict(item.extraJson),
        "createdAt": item.createdAt,
        "updatedAt": item.updatedAt,
    }


def serialize_offer(item: Offer) -> dict:
    return {
        "id": item.id,
        "slug": item.slug,
        "title": item.title,
        "subtitle": item.subtitle,
        "category": item.category,
        "status": item.status,
        "statusTone": item.statusTone,
        "price": item.price,
        "originalPrice": item.originalPrice,
        "bannerImage": item.bannerImage,
        "summary": item.summary,
        "ctaLabel": item.ctaLabel,
        "benefits": parse_json_list(item.benefitsJson),
        "meta": parse_json_list(item.metaJson),
        "extra": parse_json_dict(item.extraJson),
        "createdAt": item.createdAt,
        "updatedAt": item.updatedAt,
    }


def resolve_project_route(item: Project) -> str:
    extra = parse_json_dict(item.extraJson)
    route = ""
    if isinstance(extra, dict):
        route = (extra.get("route") or "").strip()
    if route:
        return route
    if item.projectType == "product":
        return f"/products/{item.slug}"
    if item.projectType == "lab":
        return f"/lab/{item.slug}"
    if item.projectType == "game":
        return f"/games/{item.slug}"
    return f"/projects/{item.slug}"


def normalize_search_text(*parts: object) -> str:
    values: list[str] = []
    for part in parts:
        if isinstance(part, str) and part.strip():
            values.append(part.strip().lower())
        elif isinstance(part, list):
            for item in part:
                if isinstance(item, str) and item.strip():
                    values.append(item.strip().lower())
    return "\n".join(values)


def build_search_result_items(db: Session, keyword: str) -> list[dict]:
    article_items: list[dict] = []
    project_items: list[dict] = []
    offer_items: list[dict] = []

    article_query = (
        db.query(Article)
        .options(joinedload(Article.column), joinedload(Article.tags))
        .filter(Article.status == "published")
        .order_by(Article.publishedAt.desc(), Article.id.desc())
    )
    for article in article_query.all():
        haystack = normalize_search_text(
            article.title,
            article.summary,
            article.contentBody,
            article.authorName,
            article.column.name if article.column else "",
            [tag.name for tag in article.tags],
        )
        if keyword and keyword not in haystack:
            continue
        article_items.append(
            {
                "type": "文章",
                "title": article.title,
                "summary": article.summary or "",
                "slug": article.slug,
                "to": f"/articles/{article.slug}",
                "image": article.coverImage or "",
                "source": article.column.name if article.column else "文章中心",
                "publishedAt": article.publishedAt,
            }
        )

    project_query = db.query(Project).order_by(Project.updatedAt.desc(), Project.id.desc())
    for project in project_query.all():
        if not is_public_status(project.status):
            continue
        haystack = normalize_search_text(
            project.name,
            project.title,
            project.subtitle,
            project.shortDesc,
            project.summary,
            project.description,
            parse_json_list(project.tagsJson),
            parse_json_list(project.featuresJson),
            parse_json_list(project.highlightsJson),
        )
        if keyword and keyword not in haystack:
            continue
        type_label = {"product": "产品", "game": "游戏", "lab": "实验室"}.get(project.projectType, "项目")
        source_label = {"product": "产品中心", "game": "游戏中心", "lab": "实验室"}.get(project.projectType, "项目")
        project_items.append(
            {
                "type": type_label,
                "title": project.name or project.title,
                "summary": project.summary or project.shortDesc or project.description or "",
                "slug": project.slug,
                "to": resolve_project_route(project),
                "image": project.coverImage or project.bannerImage or "",
                "source": source_label,
                "publishedAt": None,
            }
        )

    offer_query = db.query(Offer).order_by(Offer.updatedAt.desc(), Offer.id.desc())
    for offer in offer_query.all():
        if not is_public_status(offer.status):
            continue
        haystack = normalize_search_text(
            offer.title,
            offer.subtitle,
            offer.summary,
            offer.category,
            parse_json_list(offer.benefitsJson),
            parse_json_list(offer.metaJson),
        )
        if keyword and keyword not in haystack:
            continue
        offer_items.append(
            {
                "type": "快来尝鲜",
                "title": offer.title,
                "summary": offer.summary or offer.subtitle or "",
                "slug": offer.slug,
                "to": f"/try/{offer.slug}",
                "image": offer.bannerImage or "",
                "source": "快来尝鲜",
                "publishedAt": None,
            }
        )

    return [*article_items, *project_items, *offer_items]


def serialize_ad_item(item: AdItem) -> dict:
    return {
        "id": item.id,
        "slotKey": item.slotKey,
        "title": item.title,
        "pageKey": item.pageKey,
        "imageUrl": item.imageUrl,
        "targetUrl": item.targetUrl,
        "description": item.description,
        "ctaLabel": item.ctaLabel,
        "status": item.status,
        "sortOrder": item.sortOrder,
        "startAt": item.startAt,
        "endAt": item.endAt,
        "payload": parse_json_dict(item.payloadJson),
        "createdAt": item.createdAt,
        "updatedAt": item.updatedAt,
    }


def serialize_wishlist_item(item: WishlistItem) -> dict:
    return {
        "id": item.id,
        "userId": item.userId,
        "visitorId": item.visitorId,
        "projectSlug": item.projectSlug,
        "projectName": item.projectName,
        "category": item.category,
        "wishState": item.wishState,
        "sourcePage": item.sourcePage,
        "contactType": item.contactType,
        "contactValue": item.contactValue,
        "note": item.note,
        "isActive": item.isActive,
        "createdAt": item.createdAt,
        "updatedAt": item.updatedAt,
    }


def serialize_article_comment(item: ArticleComment) -> dict:
    return {
        "id": item.id,
        "articleId": item.articleId,
        "nickname": item.nickname,
        "content": item.content,
        "status": item.status,
        "createdAt": item.createdAt,
        "updatedAt": item.updatedAt,
    }


def get_request_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for.strip():
        return forwarded_for.split(",")[0].strip()[:64]
    real_ip = request.headers.get("x-real-ip", "").strip()
    if real_ip:
        return real_ip[:64]
    client_host = request.client.host if request.client else ""
    return (client_host or "unknown")[:64]


def serialize_frontend_user(user: FrontendUser) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "nickname": user.nickname,
        "avatar": user.avatar or "",
        "bio": user.bio,
        "signature": getattr(user, "signature", "") or "",
        "status": user.status,
        "lastLoginAt": user.lastLoginAt,
        "createdAt": user.createdAt,
        "updatedAt": user.updatedAt,
    }


def serialize_reading_history(item: ReadingHistory) -> dict:
    return {
        "id": item.id,
        "userId": item.userId,
        "articleSlug": item.articleSlug,
        "articleTitle": item.articleTitle,
        "articleSummary": item.articleSummary,
        "coverImage": item.coverImage or "",
        "authorName": item.authorName or "",
        "categoryName": item.categoryName or "",
        "viewedAt": item.viewedAt,
        "createdAt": item.createdAt,
        "updatedAt": item.updatedAt,
    }


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    cleanup_security_state()
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store"
    return response


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _apply_legacy_schema_patches(conn, execute: bool) -> tuple[list[str], list[str]]:
    table_rows = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
    tables = {row[0] for row in table_rows}
    executed_sql: list[str] = []
    added_columns: list[str] = []

    def has_column(table_name: str, column_name: str) -> bool:
        rows = conn.execute(text(f"PRAGMA table_info({_quote_identifier(table_name)})")).fetchall()
        return any(row[1] == column_name for row in rows)

    for key, statements in FRONTEND_USER_TABLE_PATCHES.items():
        needs_patch = False
        if "." in key:
            table_name, column_name = key.split(".", 1)
            needs_patch = table_name not in tables or not has_column(table_name, column_name)
            if needs_patch:
                added_columns.append(key)
        else:
            needs_patch = key not in tables
        if not needs_patch:
            continue
        if execute:
            for sql in statements:
                conn.execute(text(sql))
                executed_sql.append(sql)
            if "." not in key:
                tables.add(key)
    return executed_sql, added_columns


def _build_missing_model_column_sql(conn, execute: bool) -> tuple[list[str], list[str], list[str]]:
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())
    missing_tables: list[str] = []
    added_columns: list[str] = []
    executed_sql: list[str] = []

    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            missing_tables.append(table_name)
            continue

        existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        for column in table.columns:
            if column.name in existing_columns:
                continue
            if column.primary_key:
                continue
            sql = f"ALTER TABLE {_quote_identifier(table_name)} ADD COLUMN {CreateColumn(column).compile(dialect=engine.dialect)}"
            added_columns.append(f"{table_name}.{column.name}")
            if execute:
                conn.execute(text(sql))
                executed_sql.append(sql)

    return missing_tables, added_columns, executed_sql


def sync_database_schema(*, apply_changes: bool = True, seed_defaults: bool = False) -> dict[str, Any]:
    missing_tables = sorted(set(Base.metadata.tables) - set(inspect(engine).get_table_names()))
    executed_sql: list[str] = []
    added_columns: list[str] = []

    if apply_changes:
        Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        legacy_sql, legacy_columns = _apply_legacy_schema_patches(conn, execute=apply_changes)
        model_missing_tables, model_columns, model_sql = _build_missing_model_column_sql(conn, execute=apply_changes)
        executed_sql.extend(legacy_sql)
        executed_sql.extend(model_sql)
        added_columns.extend(legacy_columns)
        added_columns.extend(model_columns)
        if not apply_changes:
            missing_tables = sorted(set(missing_tables) | set(model_missing_tables))

    seeded = False
    if apply_changes and seed_defaults:
        with SessionLocal() as db:
            seed_if_empty(db, SEED_FILE)
        seeded = True

    return {
        "ok": True,
        "applied": apply_changes,
        "seeded": seeded,
        "missingTables": missing_tables,
        "addedColumns": added_columns,
        "executedSql": executed_sql,
    }


def sanitize_frontend_register_input(payload: FrontendUserRegisterRequest) -> dict:
    username = payload.username.strip().lower()
    email = payload.email.strip().lower()
    password = payload.password.strip()
    nickname = payload.nickname.strip() or username

    if not username or len(username) < 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名至少 3 位")
    if not re.fullmatch(r"[a-z0-9][-_a-z0-9]{2,49}", username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名仅支持字母、数字、-、_")
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱格式不正确")
    if len(password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="密码至少 6 位")
    if len(nickname) > 50:
        nickname = nickname[:50]

    return {"username": username, "email": email, "password": password, "nickname": nickname}


def sanitize_frontend_password_reset_input(payload: FrontendUserPasswordResetRequest) -> dict:
    account = payload.account.strip().lower()
    email = payload.email.strip().lower()
    email_code = payload.emailCode.strip()
    new_password = payload.newPassword.strip()

    if not account:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="账号不能为空")
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱格式不正确")
    if not re.fullmatch(r"\d{6}", email_code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱验证码为 6 位数字")
    if len(new_password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码至少 6 位")

    return {
        "account": account,
        "email": email,
        "emailCode": email_code,
        "newPassword": new_password,
    }


def sanitize_frontend_password_reset_code_input(payload: FrontendUserPasswordResetCodeRequest) -> dict:
    account = payload.account.strip().lower()
    email = payload.email.strip().lower()
    if not account:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="账号不能为空")
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱格式不正确")
    return {
        "account": account,
        "email": email,
    }


def sanitize_frontend_profile_update_input(payload: FrontendUserProfileUpdate) -> dict:
    nickname = payload.nickname.strip()
    email = payload.email.strip().lower()
    avatar = payload.avatar.strip()
    bio = payload.bio.strip()
    signature = payload.signature.strip()
    if not nickname:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="昵称不能为空")
    if len(nickname) > 50:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="昵称长度不能超过 50 个字符")
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱格式不正确")
    if len(avatar) > 255:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="头像地址过长")
    if len(signature) > 120:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="签名长度不能超过 120 个字符")
    if len(bio) > 500:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="个人简介长度不能超过 500 个字符")
    return {
        "nickname": nickname,
        "email": email,
        "avatar": avatar,
        "bio": bio,
        "signature": signature,
    }


def sanitize_frontend_password_change_input(payload: FrontendUserPasswordChangeRequest) -> dict:
    current_password = payload.currentPassword.strip()
    new_password = payload.newPassword.strip()
    if not current_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码不能为空")
    if len(new_password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码至少需要 6 位")
    if len(new_password) > AUTH_INPUT_MAX_LENGTH:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码长度不能超过 128 个字符")
    return {"currentPassword": current_password, "newPassword": new_password}


def sanitize_reading_history_input(payload: ReadingHistoryWrite) -> dict:
    article_slug = payload.articleSlug.strip()
    if not article_slug:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文章标识不能为空")
    return {
        "articleSlug": article_slug[:150],
        "articleTitle": payload.articleTitle.strip()[:200],
        "articleSummary": payload.articleSummary.strip()[:1000],
        "coverImage": payload.coverImage.strip()[:255],
        "authorName": payload.authorName.strip()[:50],
        "categoryName": payload.categoryName.strip()[:100],
    }


def validate_auth_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field_name}不能为空")
    if len(normalized) > AUTH_INPUT_MAX_LENGTH:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field_name}长度不能超过 {AUTH_INPUT_MAX_LENGTH}")
    return normalized


def hash_email_verification_code(email: str, purpose: str, code: str) -> str:
    normalized = f"{email.strip().lower()}::{purpose.strip().lower()}::{code.strip()}"
    return sha256(normalized.encode("utf-8")).hexdigest()


def generate_email_code() -> str:
    return f"{randbelow(1000000):06d}"


def send_password_reset_email(email: str, code: str) -> None:
    app_name = get_mail_settings()["app_name"]
    subject = f"{app_name} 密码重置验证码"
    text = (
        f"你好，\n\n"
        f"你正在进行密码重置，本次验证码为：{code}\n"
        f"验证码 {EMAIL_CODE_EXPIRES_SECONDS // 60} 分钟内有效，请勿泄露给他人。\n"
        f"如果不是你本人操作，可以忽略这封邮件。\n"
    )
    html = (
        "<div style=\"font-family:Arial,'PingFang SC','Microsoft YaHei',sans-serif;line-height:1.7;color:#1f2937;\">"
        f"<p>你好，</p><p>你正在进行密码重置，本次验证码为：</p>"
        f"<p style=\"font-size:28px;font-weight:700;letter-spacing:4px;color:#c2410c;\">{code}</p>"
        f"<p>验证码 {EMAIL_CODE_EXPIRES_SECONDS // 60} 分钟内有效，请勿泄露给他人。</p>"
        "<p>如果不是你本人操作，可以忽略这封邮件。</p></div>"
    )
    send_email(email, subject, text, html)


def verify_email_code(db: Session, email: str, purpose: str, code: str) -> None:
    now = current_time()
    code_hash = hash_email_verification_code(email, purpose, code)
    record = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == email,
            EmailVerificationCode.purpose == purpose,
            EmailVerificationCode.codeHash == code_hash,
            EmailVerificationCode.usedAt.is_(None),
        )
        .order_by(EmailVerificationCode.id.desc())
        .first()
    )
    if not record:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱验证码错误")
    if record.expiresAt <= now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱验证码已过期，请重新获取")
    record.usedAt = now


def create_email_code_record(db: Session, email: str, purpose: str, user_id: int | None = None) -> str:
    now = current_time()
    db.query(EmailVerificationCode).filter(
        EmailVerificationCode.email == email,
        EmailVerificationCode.purpose == purpose,
        EmailVerificationCode.usedAt.is_(None),
    ).update({"usedAt": now}, synchronize_session=False)

    code = generate_email_code()
    record = EmailVerificationCode(
        userId=user_id,
        email=email,
        purpose=purpose,
        codeHash=hash_email_verification_code(email, purpose, code),
        expiresAt=datetime.fromtimestamp(now.timestamp() + EMAIL_CODE_EXPIRES_SECONDS),
        usedAt=None,
        createdAt=now,
    )
    db.add(record)
    return code


def resolve_frontend_user(session: dict | None, db: Session) -> FrontendUser | None:
    if not session:
        return None
    return db.query(FrontendUser).filter(FrontendUser.id == session["id"]).first()


def get_article_engagement(article: Article, db: Session) -> dict:
    favorite_count = (
        db.query(ArticleInteraction)
        .filter(
            ArticleInteraction.articleId == article.id,
            ArticleInteraction.interactionType == "favorite",
            ArticleInteraction.isCanceled == False,
        )
        .count()
    )
    comment_count = (
        db.query(ArticleComment)
        .filter(
            ArticleComment.articleId == article.id,
            ArticleComment.status == "published",
        )
        .count()
    )
    return {
        "likeCount": article.likeCount,
        "favoriteCount": favorite_count,
        "commentCount": comment_count,
    }


def fetch_active_ads(db: Session, page_key: str = "", slot_key: str = "") -> list[dict]:
    now = datetime.utcnow()
    query = db.query(AdItem).order_by(AdItem.sortOrder.asc(), AdItem.id.asc()).filter(AdItem.status == "active")
    if page_key.strip():
        query = query.filter((AdItem.pageKey == page_key.strip()) | (AdItem.pageKey.is_(None)))
    if slot_key.strip():
        query = query.filter(AdItem.slotKey == slot_key.strip())
    items = [
        item
        for item in query.all()
        if (item.startAt is None or item.startAt <= now) and (item.endAt is None or item.endAt >= now)
    ]
    return [serialize_ad_item(item) for item in items]


def serialize_community_lead(item: CommunityLead) -> dict:
    return {
        "id": item.id,
        "userId": item.userId,
        "leadType": item.leadType,
        "intentReason": item.intentReason,
        "name": item.name,
        "contactType": item.contactType,
        "contactValue": item.contactValue,
        "message": item.message,
        "status": item.status,
        "createdAt": item.createdAt,
        "updatedAt": item.updatedAt,
    }


def serialize_beta_application(item: BetaApplication) -> dict:
    return {
        "id": item.id,
        "userId": item.userId,
        "projectSlug": item.projectSlug,
        "sourcePage": item.sourcePage,
        "roleType": item.roleType,
        "name": item.name,
        "contactType": item.contactType,
        "contactValue": item.contactValue,
        "city": item.city,
        "experienceNote": item.experienceNote,
        "status": item.status,
        "followUpNote": item.followUpNote,
        "createdAt": item.createdAt,
        "updatedAt": item.updatedAt,
    }


def sanitize_article_input(payload: ArticleWrite, db: Session) -> dict:
    data = payload.model_dump()
    data["title"] = data["title"].strip()
    data["slug"] = data["slug"].strip()
    data["summary"] = data["summary"].strip()
    data["contentBody"] = data["contentBody"].strip()
    data["authorName"] = data["authorName"].strip() or "匿名"
    data["status"] = data["status"].strip() or "draft"
    data["sourceType"] = data["sourceType"].strip() or "original"
    data["coverImage"] = data["coverImage"].strip()
    data["heroTone"] = data["heroTone"].strip() or "warm"

    if not data["title"] or not data["slug"] or not data["summary"] or not data["contentBody"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="标题、slug、摘要和正文不能为空")

    column = db.query(ContentCategory).filter(ContentCategory.id == data["columnId"]).first()
    if not column:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="columnId 不存在")

    tags = []
    for tag_id in data["tagIds"]:
        tag = db.query(ContentTag).filter(ContentTag.id == tag_id).first()
        if not tag:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"tagId {tag_id} 不存在")
        tags.append(tag)

    data["column"] = column
    data["tags"] = tags
    return data


def sanitize_site_config_input(payload: SiteConfigWrite) -> dict:
    data = payload.model_dump()
    data["configKey"] = data["configKey"].strip()
    data["configValue"] = data["configValue"].strip()
    data["groupName"] = data["groupName"].strip() or "general"
    data["remark"] = data["remark"].strip()
    if not data["configKey"] or not data["configValue"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="配置键和值不能为空")
    return data


def sanitize_page_config_input(payload: PageConfigWrite) -> dict:
    data = payload.model_dump()
    data["pageKey"] = data["pageKey"].strip()
    data["title"] = data["title"].strip()
    data["configJson"] = data["configJson"].strip()
    data["status"] = data["status"].strip() or "active"
    data["remark"] = data["remark"].strip()
    if not data["pageKey"] or not data["title"] or not data["configJson"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="页面键、标题和配置内容不能为空")
    return data


def sanitize_project_input(payload: ProjectWrite) -> dict:
    data = payload.model_dump()
    data["slug"] = data["slug"].strip()
    data["name"] = data["name"].strip()
    data["projectType"] = data["projectType"].strip()
    data["title"] = data["title"].strip()
    data["subtitle"] = data["subtitle"].strip()
    data["shortDesc"] = data["shortDesc"].strip()
    data["summary"] = data["summary"].strip()
    data["description"] = data["description"].strip()
    data["coverImage"] = data["coverImage"].strip()
    data["bannerImage"] = data["bannerImage"].strip()
    data["status"] = data["status"].strip() or "draft"
    data["stage"] = data["stage"].strip()
    data["supportStatus"] = data["supportStatus"].strip()
    data["price"] = data["price"].strip()
    data["originalPrice"] = data["originalPrice"].strip()

    if not data["slug"] or not data["name"] or not data["projectType"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="slug、name、projectType 不能为空")

    if data["projectType"] not in {"product", "game", "lab"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projectType 仅支持 product / game / lab")

    return data


def sanitize_offer_input(payload: OfferWrite) -> dict:
    data = payload.model_dump()
    data["slug"] = data["slug"].strip()
    data["title"] = data["title"].strip()
    data["subtitle"] = data["subtitle"].strip()
    data["category"] = data["category"].strip()
    data["status"] = data["status"].strip()
    data["statusTone"] = data["statusTone"].strip()
    data["price"] = data["price"].strip()
    data["originalPrice"] = data["originalPrice"].strip()
    data["bannerImage"] = data["bannerImage"].strip()
    data["summary"] = data["summary"].strip()
    data["ctaLabel"] = data["ctaLabel"].strip()

    if not data["slug"] or not data["title"] or not data["subtitle"] or not data["price"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="slug、title、subtitle、price 不能为空")

    return data


def build_article_write_from_ai_payload(payload: dict[str, Any], auto_publish: bool, db: Session) -> ArticleWrite:
    data = dict(payload)
    if not data.get("status") and auto_publish:
        data["status"] = "published"
    data.setdefault("authorName", "AI 助手")
    data.setdefault("sourceType", "ai")

    if not data.get("columnId"):
        column_slug = str(data.pop("columnSlug", "")).strip()
        column_name = str(data.pop("columnName", "")).strip()
        query = db.query(ContentCategory)
        if column_slug:
            column = query.filter(ContentCategory.slug == column_slug).first()
        elif column_name:
            column = query.filter(ContentCategory.name == column_name).first()
        else:
            column = None
        if not column:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文章发布需要 columnId 或有效的 columnSlug/columnName")
        data["columnId"] = column.id

    if not data.get("tagIds"):
        tag_ids: list[int] = []
        for slug in data.pop("tagSlugs", []) or []:
            text_slug = str(slug).strip()
            if not text_slug:
                continue
            tag = db.query(ContentTag).filter(ContentTag.slug == text_slug).first()
            if not tag:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"标签 slug 不存在: {text_slug}")
            tag_ids.append(tag.id)
        for name in data.pop("tagNames", []) or []:
            text_name = str(name).strip()
            if not text_name:
                continue
            tag = db.query(ContentTag).filter(ContentTag.name == text_name).first()
            if not tag:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"标签名称不存在: {text_name}")
            tag_ids.append(tag.id)
        data["tagIds"] = list(dict.fromkeys(tag_ids))

    return ArticleWrite(**data)


def build_project_write_from_ai_payload(payload: dict[str, Any], auto_publish: bool) -> ProjectWrite:
    data = dict(payload)
    if not data.get("status") and auto_publish:
        data["status"] = "published"
    return ProjectWrite(**data)


def build_offer_write_from_ai_payload(payload: dict[str, Any]) -> OfferWrite:
    return OfferWrite(**dict(payload))


def publish_ai_content(payload: AiContentPublishRequest, db: Session) -> dict[str, Any]:
    content_type = payload.contentType.strip().lower()
    mode = payload.mode.strip().lower() or "upsert"
    if mode not in {"create", "update", "upsert"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mode 仅支持 create / update / upsert")

    raw = dict(payload.payload)
    slug = str(raw.get("slug", "")).strip()
    if not slug:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payload.slug 不能为空")

    if content_type == "article":
        article_payload = build_article_write_from_ai_payload(raw, payload.autoPublish, db)
        data = sanitize_article_input(article_payload, db)
        item = (
            db.query(Article)
            .options(joinedload(Article.column), joinedload(Article.tags))
            .filter(Article.slug == data["slug"])
            .first()
        )
        if not item and mode == "update":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文章不存在，无法更新")
        if item and mode == "create":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="文章 slug 已存在")

        action = "updated" if item else "created"
        now = datetime.utcnow()
        if not item:
            item = Article(
                title=data["title"],
                slug=data["slug"],
                summary=data["summary"],
                contentBody=data["contentBody"],
                authorName=data["authorName"],
                columnId=data["columnId"],
                coverImage=data["coverImage"],
                heroTone=data["heroTone"],
                status=data["status"],
                sourceType=data["sourceType"],
                publishedAt=now if data["status"] == "published" else None,
                viewCount=0,
                likeCount=0,
                createdAt=now,
                updatedAt=now,
            )
            item.column = data["column"]
            item.tags = data["tags"]
            db.add(item)
        else:
            item.title = data["title"]
            item.slug = data["slug"]
            item.summary = data["summary"]
            item.contentBody = data["contentBody"]
            item.authorName = data["authorName"]
            item.columnId = data["columnId"]
            item.coverImage = data["coverImage"]
            item.heroTone = data["heroTone"]
            item.status = data["status"]
            item.sourceType = data["sourceType"]
            if data["status"] == "published" and not item.publishedAt:
                item.publishedAt = now
            item.updatedAt = now
            item.column = data["column"]
            item.tags = data["tags"]

        db.commit()
        db.refresh(item)
        return {
            "ok": True,
            "contentType": content_type,
            "action": action,
            "itemId": item.id,
            "slug": item.slug,
            "item": serialize_article(item),
        }

    if content_type == "project":
        project_payload = build_project_write_from_ai_payload(raw, payload.autoPublish)
        data = sanitize_project_input(project_payload)
        item = db.query(Project).filter(Project.slug == data["slug"]).first()
        if not item and mode == "update":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在，无法更新")
        if item and mode == "create":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="项目 slug 已存在")

        action = "updated" if item else "created"
        now = datetime.utcnow()
        if not item:
            item = Project(
                slug=data["slug"],
                name=data["name"],
                projectType=data["projectType"],
                title=data["title"] or None,
                subtitle=data["subtitle"] or None,
                shortDesc=data["shortDesc"] or None,
                summary=data["summary"] or None,
                description=data["description"] or None,
                coverImage=data["coverImage"],
                bannerImage=data["bannerImage"],
                status=data["status"],
                stage=data["stage"] or None,
                supportStatus=data["supportStatus"] or None,
                price=data["price"] or None,
                originalPrice=data["originalPrice"] or None,
                tagsJson=json.dumps(data["tags"], ensure_ascii=False),
                featuresJson=json.dumps(data["features"], ensure_ascii=False),
                highlightsJson=json.dumps(data["highlights"], ensure_ascii=False),
                faqJson=json.dumps(data["faq"], ensure_ascii=False),
                testimonialsJson=json.dumps(data["testimonials"], ensure_ascii=False),
                extraJson=json.dumps(data["extra"], ensure_ascii=False),
                createdAt=now,
                updatedAt=now,
            )
            db.add(item)
        else:
            item.slug = data["slug"]
            item.name = data["name"]
            item.projectType = data["projectType"]
            item.title = data["title"] or None
            item.subtitle = data["subtitle"] or None
            item.shortDesc = data["shortDesc"] or None
            item.summary = data["summary"] or None
            item.description = data["description"] or None
            item.coverImage = data["coverImage"]
            item.bannerImage = data["bannerImage"]
            item.status = data["status"]
            item.stage = data["stage"] or None
            item.supportStatus = data["supportStatus"] or None
            item.price = data["price"] or None
            item.originalPrice = data["originalPrice"] or None
            item.tagsJson = json.dumps(data["tags"], ensure_ascii=False)
            item.featuresJson = json.dumps(data["features"], ensure_ascii=False)
            item.highlightsJson = json.dumps(data["highlights"], ensure_ascii=False)
            item.faqJson = json.dumps(data["faq"], ensure_ascii=False)
            item.testimonialsJson = json.dumps(data["testimonials"], ensure_ascii=False)
            item.extraJson = json.dumps(data["extra"], ensure_ascii=False)
            item.updatedAt = now

        db.commit()
        db.refresh(item)
        return {
            "ok": True,
            "contentType": content_type,
            "action": action,
            "itemId": item.id,
            "slug": item.slug,
            "item": serialize_project(item),
        }

    if content_type == "offer":
        offer_payload = build_offer_write_from_ai_payload(raw)
        data = sanitize_offer_input(offer_payload)
        item = db.query(Offer).filter(Offer.slug == data["slug"]).first()
        if not item and mode == "update":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="优惠内容不存在，无法更新")
        if item and mode == "create":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="优惠内容 slug 已存在")

        action = "updated" if item else "created"
        now = datetime.utcnow()
        if not item:
            item = Offer(
                slug=data["slug"],
                title=data["title"],
                subtitle=data["subtitle"],
                category=data["category"] or None,
                status=data["status"] or None,
                statusTone=data["statusTone"] or None,
                price=data["price"],
                originalPrice=data["originalPrice"] or None,
                bannerImage=data["bannerImage"],
                summary=data["summary"] or None,
                ctaLabel=data["ctaLabel"] or None,
                benefitsJson=json.dumps(data["benefits"], ensure_ascii=False),
                metaJson=json.dumps(data["meta"], ensure_ascii=False),
                extraJson=json.dumps(data["extra"], ensure_ascii=False),
                createdAt=now,
                updatedAt=now,
            )
            db.add(item)
        else:
            item.slug = data["slug"]
            item.title = data["title"]
            item.subtitle = data["subtitle"]
            item.category = data["category"] or None
            item.status = data["status"] or None
            item.statusTone = data["statusTone"] or None
            item.price = data["price"]
            item.originalPrice = data["originalPrice"] or None
            item.bannerImage = data["bannerImage"]
            item.summary = data["summary"] or None
            item.ctaLabel = data["ctaLabel"] or None
            item.benefitsJson = json.dumps(data["benefits"], ensure_ascii=False)
            item.metaJson = json.dumps(data["meta"], ensure_ascii=False)
            item.extraJson = json.dumps(data["extra"], ensure_ascii=False)
            item.updatedAt = now

        db.commit()
        db.refresh(item)
        return {
            "ok": True,
            "contentType": content_type,
            "action": action,
            "itemId": item.id,
            "slug": item.slug,
            "item": serialize_offer(item),
        }

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="contentType 仅支持 article / project / offer")


def sanitize_ad_item_input(payload: AdItemWrite) -> dict:
    data = payload.model_dump()
    data["slotKey"] = data["slotKey"].strip()
    data["title"] = data["title"].strip()
    data["pageKey"] = data["pageKey"].strip()
    data["imageUrl"] = data["imageUrl"].strip()
    data["targetUrl"] = data["targetUrl"].strip()
    data["description"] = data["description"].strip()
    data["ctaLabel"] = data["ctaLabel"].strip()
    data["status"] = data["status"].strip() or "draft"
    if not data["slotKey"] or not data["title"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="slotKey 和 title 不能为空")
    return data


def sanitize_wishlist_input(payload: WishlistWrite) -> dict:
    data = payload.model_dump()
    data["userId"] = data.get("userId")
    data["visitorId"] = data["visitorId"].strip() or f"guest-{current_timestamp_ms()}"
    data["projectSlug"] = data["projectSlug"].strip()
    data["projectName"] = data["projectName"].strip()
    data["category"] = data["category"].strip()
    data["wishState"] = data["wishState"].strip() or "want_try"
    data["sourcePage"] = data["sourcePage"].strip() or "wishlist"
    data["contactType"] = data["contactType"].strip()
    data["contactValue"] = data["contactValue"].strip()
    data["note"] = data["note"].strip()
    if not data["projectSlug"] and not data["projectName"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projectSlug 或 projectName 至少填写一个")
    validate_contact_value(data["contactType"] or "wechat", data["contactValue"])
    return data


def sanitize_community_lead_input(payload: CommunityLeadWrite) -> dict:
    data = payload.model_dump()
    data["userId"] = data.get("userId")
    data["leadType"] = data["leadType"].strip() or "community"
    data["intentReason"] = data["intentReason"].strip() or "latest_updates"
    data["name"] = data["name"].strip()
    data["contactType"] = data["contactType"].strip() or "wechat"
    data["contactValue"] = data["contactValue"].strip()
    data["message"] = data["message"].strip()
    validate_contact_value(data["contactType"], data["contactValue"])
    return data


def sanitize_beta_application_input(payload: BetaApplicationWrite) -> dict:
    data = payload.model_dump()
    data["userId"] = data.get("userId")
    data["projectSlug"] = data["projectSlug"].strip()
    data["sourcePage"] = data["sourcePage"].strip() or "lab"
    data["roleType"] = data["roleType"].strip() or "explorer"
    data["name"] = data["name"].strip()
    data["contactType"] = data["contactType"].strip() or "wechat"
    data["contactValue"] = data["contactValue"].strip()
    data["city"] = data["city"].strip()
    data["experienceNote"] = data["experienceNote"].strip()
    data["status"] = data["status"].strip() or "pending"
    if not data["name"] or not data["contactValue"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="姓名和联系方式不能为空")
    validate_contact_value(data["contactType"], data["contactValue"])
    return data


@app.on_event("startup")
def startup() -> None:
    sync_database_schema(apply_changes=True, seed_defaults=True)

if ADMIN_DIST_STATIC.exists():
    app.mount("/admin/static", StaticFiles(directory=ADMIN_DIST_STATIC), name="admin-static")


@app.get("/", include_in_schema=False)
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/admin")


@app.get("/admin/platform-config.json", include_in_schema=False)
def admin_platform_config() -> FileResponse:
    if ADMIN_DIST_PLATFORM_CONFIG.exists():
        return FileResponse(ADMIN_DIST_PLATFORM_CONFIG, media_type="application/json")
    raise HTTPException(status_code=404, detail="platform-config.json not found")


@app.get("/admin/favicon.ico", include_in_schema=False)
def admin_favicon() -> FileResponse:
    if ADMIN_DIST_FAVICON.exists():
        return FileResponse(ADMIN_DIST_FAVICON)
    raise HTTPException(status_code=404, detail="favicon.ico not found")


@app.get("/admin/logo.svg", include_in_schema=False)
def admin_logo() -> FileResponse:
    if ADMIN_DIST_LOGO.exists():
        return FileResponse(ADMIN_DIST_LOGO, media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="logo.svg not found")


@app.get("/admin", include_in_schema=False)
@app.get("/admin/{path:path}", include_in_schema=False)
def admin_page(path: str = ""):
    if ADMIN_DIST_INDEX.exists():
        return FileResponse(ADMIN_DIST_INDEX)
    return JSONResponse(
        status_code=503,
        content={
            "message": "Admin frontend not built yet. Run pnpm build in backend/admin or pnpm dev for local development."
        }
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(ok=True, service="quentin-window-backend", time=datetime.utcnow())


@app.get("/api/security/captcha", response_model=CaptchaResponse)
def get_captcha(scope: str = Query(default="frontend")) -> CaptchaResponse:
    normalized_scope = scope.strip().lower()
    if normalized_scope not in {"admin", "frontend"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="scope 仅支持 admin 或 frontend")
    return CaptchaResponse.model_validate(create_captcha(normalized_scope))


@app.post("/api/admin/login", response_model=LoginResponse)
async def admin_login(payload: UserLoginRequest, request: Request, db: Session = Depends(get_db)) -> LoginResponse:
    username = validate_auth_text(payload.username, "账号")
    password = validate_auth_text(payload.password, "密码")
    ip = get_request_ip(request)
    scope = "admin"
    await apply_login_delay(scope, ip, username)
    if needs_captcha(scope, ip, username):
        verify_captcha(scope, payload.captchaKey, payload.captchaCode)
    try:
        result = do_login(username, password, db)
    except HTTPException:
        detail = build_auth_error_payload("用户名或密码错误", scope, ip, username)
        await asyncio.sleep(detail["retryDelaySeconds"])
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
    clear_login_failures(scope, ip, username)
    return LoginResponse.model_validate(result)


@app.post("/api/users/register", response_model=FrontendAuthResponse, status_code=status.HTTP_201_CREATED)
async def register_frontend_user(
    payload: FrontendUserRegisterRequest, request: Request, db: Session = Depends(get_db)
) -> FrontendAuthResponse:
    ip = get_request_ip(request)
    register_scope = "frontend"
    register_account = payload.username.strip().lower() or payload.email.strip().lower()
    if needs_captcha(register_scope, ip, register_account):
        verify_captcha(register_scope, payload.captchaKey, payload.captchaCode)
    data = sanitize_frontend_register_input(payload)
    duplicate = (
        db.query(FrontendUser)
        .filter((FrontendUser.username == data["username"]) | (FrontendUser.email == data["email"]))
        .first()
    )
    if duplicate:
        detail = build_auth_error_payload("用户名或邮箱已存在", register_scope, ip, register_account)
        await asyncio.sleep(detail["retryDelaySeconds"])
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    now = current_time()
    user = FrontendUser(
        username=data["username"],
        email=data["email"],
        passwordHash=hash_password(data["password"]),
        nickname=data["nickname"],
        avatar="",
        bio=None,
        status="active",
        lastLoginAt=now,
        createdAt=now,
        updatedAt=now,
    )
    db.add(user)
    db.commit()
    clear_login_failures(register_scope, ip, register_account)
    return FrontendAuthResponse.model_validate(login_frontend(data["username"], data["password"], db))


@app.post("/api/users/login", response_model=FrontendAuthResponse)
async def frontend_user_login(
    payload: FrontendUserLoginRequest, request: Request, db: Session = Depends(get_db)
) -> FrontendAuthResponse:
    account = validate_auth_text(payload.account, "账号").lower()
    password = validate_auth_text(payload.password, "密码")
    ip = get_request_ip(request)
    scope = "frontend"
    await apply_login_delay(scope, ip, account)
    if needs_captcha(scope, ip, account):
        verify_captcha(scope, payload.captchaKey, payload.captchaCode)
    try:
        result = login_frontend(account, password, db)
    except HTTPException:
        detail = build_auth_error_payload("账号或密码错误", scope, ip, account)
        await asyncio.sleep(detail["retryDelaySeconds"])
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
    clear_login_failures(scope, ip, account)
    return FrontendAuthResponse.model_validate(result)


@app.post("/api/users/reset-password/code", response_model=EmailVerificationSendResponse)
async def send_frontend_user_password_reset_code(
    payload: FrontendUserPasswordResetCodeRequest, request: Request, db: Session = Depends(get_db)
) -> EmailVerificationSendResponse:
    ip = get_request_ip(request)
    scope = "frontend"
    data = sanitize_frontend_password_reset_code_input(payload)
    account = data["account"]

    await apply_login_delay(scope, ip, account)
    verify_captcha(scope, payload.captchaKey, payload.captchaCode)

    user = (
        db.query(FrontendUser)
        .filter(
            ((FrontendUser.username == account) | (FrontendUser.email == account)),
            FrontendUser.email == data["email"],
            FrontendUser.status == "active",
        )
        .first()
    )
    if not user:
        detail = build_auth_error_payload("账号与邮箱不匹配", scope, ip, account)
        await asyncio.sleep(detail["retryDelaySeconds"])
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    code = create_email_code_record(db, user.email, EMAIL_CODE_PURPOSE_RESET_PASSWORD, user.id)
    send_password_reset_email(user.email, code)
    db.commit()
    clear_login_failures(scope, ip, account)
    return EmailVerificationSendResponse(
        ok=True,
        message="邮箱验证码已发送，请查收邮件",
        expiresIn=EMAIL_CODE_EXPIRES_SECONDS,
    )


@app.post("/api/users/reset-password")
async def reset_frontend_user_password(
    payload: FrontendUserPasswordResetRequest, request: Request, db: Session = Depends(get_db)
) -> dict:
    ip = get_request_ip(request)
    scope = "frontend"
    data = sanitize_frontend_password_reset_input(payload)
    account = data["account"]

    await apply_login_delay(scope, ip, account)

    user = (
        db.query(FrontendUser)
        .filter(
            ((FrontendUser.username == account) | (FrontendUser.email == account)),
            FrontendUser.email == data["email"],
            FrontendUser.status == "active",
        )
        .first()
    )
    if not user:
        detail = build_auth_error_payload("账号与邮箱不匹配", scope, ip, account)
        await asyncio.sleep(detail["retryDelaySeconds"])
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    verify_email_code(db, user.email, EMAIL_CODE_PURPOSE_RESET_PASSWORD, data["emailCode"])
    user.passwordHash = hash_password(data["newPassword"])
    user.updatedAt = current_time()
    db.commit()
    clear_login_failures(scope, ip, account)
    return {"ok": True, "message": "密码已重置，请使用新密码登录"}


@app.post("/api/admin/notifications/email")
def send_admin_email_notification(
    payload: AdminEmailNotificationRequest,
    _: dict = Depends(require_auth),
) -> dict:
    to_email = payload.toEmail.strip().lower()
    subject = payload.subject.strip()
    text = payload.text.strip()
    html = payload.html.strip()
    if not EMAIL_RE.match(to_email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="收件邮箱格式不正确")
    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮件主题不能为空")
    if not text and not html:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮件内容不能为空")
    send_email(to_email, subject, text or subject, html)
    return {"ok": True, "message": "邮件发送成功"}


@app.get("/api/users/me", response_model=FrontendUserProfileOut)
def frontend_user_me(session: dict = Depends(require_frontend_auth), db: Session = Depends(get_db)) -> FrontendUserProfileOut:
    user = db.query(FrontendUser).filter(FrontendUser.id == session["id"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return FrontendUserProfileOut.model_validate(serialize_frontend_user(user))


@app.put("/api/users/me", response_model=FrontendUserProfileOut)
def frontend_user_update_profile(
    payload: FrontendUserProfileUpdate,
    session: dict = Depends(require_frontend_auth),
    db: Session = Depends(get_db),
) -> FrontendUserProfileOut:
    user = db.query(FrontendUser).filter(FrontendUser.id == session["id"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    data = sanitize_frontend_profile_update_input(payload)
    duplicate = db.query(FrontendUser).filter(FrontendUser.email == data["email"], FrontendUser.id != user.id).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已存在")
    user.nickname = data["nickname"]
    user.email = data["email"]
    user.avatar = data["avatar"]
    user.bio = data["bio"] or None
    user.signature = data["signature"]
    user.updatedAt = current_time()
    db.commit()
    db.refresh(user)
    return FrontendUserProfileOut.model_validate(serialize_frontend_user(user))


@app.post("/api/users/me/password")
def frontend_user_change_password(
    payload: FrontendUserPasswordChangeRequest,
    session: dict = Depends(require_frontend_auth),
    db: Session = Depends(get_db),
) -> dict:
    user = db.query(FrontendUser).filter(FrontendUser.id == session["id"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    data = sanitize_frontend_password_change_input(payload)
    if user.passwordHash != hash_password(data["currentPassword"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码不正确")
    user.passwordHash = hash_password(data["newPassword"])
    user.updatedAt = current_time()
    db.commit()
    return {"ok": True, "message": "密码修改成功"}


@app.get("/api/users/me/summary", response_model=FrontendProfileSummary)
def frontend_user_profile_summary(
    session: dict = Depends(require_frontend_auth),
    db: Session = Depends(get_db),
) -> FrontendProfileSummary:
    user = db.query(FrontendUser).filter(FrontendUser.id == session["id"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    wishlist_items = (
        db.query(WishlistItem)
        .filter(WishlistItem.userId == user.id)
        .order_by(WishlistItem.updatedAt.desc(), WishlistItem.id.desc())
        .all()
    )
    reading_items = (
        db.query(ReadingHistory)
        .filter(ReadingHistory.userId == user.id)
        .order_by(ReadingHistory.viewedAt.desc(), ReadingHistory.id.desc())
        .limit(30)
        .all()
    )
    like_count = db.query(ArticleInteraction).filter(
        ArticleInteraction.userId == user.id,
        ArticleInteraction.interactionType == "like",
        ArticleInteraction.isCanceled == False,
    ).count()
    favorite_count = db.query(ArticleInteraction).filter(
        ArticleInteraction.userId == user.id,
        ArticleInteraction.interactionType == "favorite",
        ArticleInteraction.isCanceled == False,
    ).count()
    comment_count = db.query(ArticleComment).filter(ArticleComment.userId == user.id).count()
    beta_count = db.query(BetaApplication).filter(BetaApplication.userId == user.id).count()
    community_count = db.query(CommunityLead).filter(CommunityLead.userId == user.id).count()

    return FrontendProfileSummary.model_validate({
        "profile": serialize_frontend_user(user),
        "stats": {
            "wishlistCount": len(wishlist_items),
            "readingHistoryCount": len(reading_items),
            "likeCount": like_count,
            "favoriteCount": favorite_count,
            "commentCount": comment_count,
            "betaApplicationCount": beta_count,
            "communityLeadCount": community_count,
        },
        "wishlist": [serialize_wishlist_item(item) for item in wishlist_items],
        "readingHistory": [serialize_reading_history(item) for item in reading_items],
    })


@app.post("/api/users/me/reading-history", response_model=ReadingHistoryOut, status_code=status.HTTP_201_CREATED)
def create_frontend_reading_history(
    payload: ReadingHistoryWrite,
    session: dict = Depends(require_frontend_auth),
    db: Session = Depends(get_db),
) -> ReadingHistoryOut:
    user = db.query(FrontendUser).filter(FrontendUser.id == session["id"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    data = sanitize_reading_history_input(payload)
    now = current_time()
    item = (
        db.query(ReadingHistory)
        .filter(ReadingHistory.userId == user.id, ReadingHistory.articleSlug == data["articleSlug"])
        .first()
    )
    if item:
        item.articleTitle = data["articleTitle"] or item.articleTitle
        item.articleSummary = data["articleSummary"] or item.articleSummary
        item.coverImage = data["coverImage"] or item.coverImage
        item.authorName = data["authorName"] or item.authorName
        item.categoryName = data["categoryName"] or item.categoryName
        item.viewedAt = now
        item.updatedAt = now
    else:
        item = ReadingHistory(
            userId=user.id,
            articleSlug=data["articleSlug"],
            articleTitle=data["articleTitle"],
            articleSummary=data["articleSummary"] or None,
            coverImage=data["coverImage"],
            authorName=data["authorName"],
            categoryName=data["categoryName"],
            viewedAt=now,
            createdAt=now,
            updatedAt=now,
        )
        db.add(item)
    db.commit()
    db.refresh(item)
    return ReadingHistoryOut.model_validate(serialize_reading_history(item))


@app.delete("/api/users/me/reading-history", response_model=DeleteResponse)
def clear_frontend_reading_history(
    session: dict = Depends(require_frontend_auth),
    db: Session = Depends(get_db),
) -> DeleteResponse:
    user = db.query(FrontendUser).filter(FrontendUser.id == session["id"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    deleted = db.query(ReadingHistory).filter(ReadingHistory.userId == user.id).delete()
    db.commit()
    return DeleteResponse.model_validate({"ok": True, "deletedId": deleted})


@app.get("/api/columns")
def list_columns(db: Session = Depends(get_db)) -> dict:
    items = [
        item
        for item in db.query(ContentCategory).order_by(ContentCategory.sortOrder.asc(), ContentCategory.id.asc()).all()
        if is_public_status(item.status)
    ]
    return {"items": [serialize_column(item) for item in items], "total": len(items)}


@app.get("/api/tags")
def list_tags(db: Session = Depends(get_db)) -> dict:
    items = [item for item in db.query(ContentTag).order_by(ContentTag.id.asc()).all() if is_public_status(item.status)]
    return {"items": [serialize_tag(item) for item in items], "total": len(items)}


@app.get("/api/articles")
def list_articles(
    q: str = Query(default=""),
    column: str = Query(default=""),
    tag: str = Query(default=""),
    db: Session = Depends(get_db),
) -> dict:
    query = (
        db.query(Article)
        .options(
            joinedload(Article.column),
            joinedload(Article.tags),
            joinedload(Article.interactions),
            joinedload(Article.comments),
        )
        .filter(Article.status == "published")
        .order_by(Article.publishedAt.desc(), Article.id.desc())
    )

    if q.strip():
        keyword = f"%{q.strip()}%"
        query = query.filter((Article.title.like(keyword)) | (Article.summary.like(keyword)))

    items = query.all()
    serialized = [serialize_article(item) for item in items]

    if column.strip():
        serialized = [item for item in serialized if item["column"] and item["column"].slug == column.strip()]
    if tag.strip():
        tag_value = tag.strip()
        serialized = [
            item for item in serialized if any(entry.slug == tag_value or entry.name == tag_value for entry in item["tags"])
        ]
    if q.strip():
        keyword = q.strip().lower()
        serialized = [
            item for item in serialized
            if keyword in item["title"].lower()
            or keyword in item["summary"].lower()
            or any(keyword in entry.name.lower() for entry in item["tags"])
        ]

    return {"items": serialized, "total": len(serialized)}


@app.get("/api/articles/{slug}", response_model=ArticleOut)
def get_article(slug: str, db: Session = Depends(get_db)) -> ArticleOut:
    article = (
        db.query(Article)
        .options(
            joinedload(Article.column),
            joinedload(Article.tags),
            joinedload(Article.interactions),
            joinedload(Article.comments),
        )
        .filter(Article.slug == slug, Article.status == "published")
        .first()
    )
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return ArticleOut.model_validate(serialize_article(article))


@app.get("/api/articles/{slug}/engagement", response_model=ArticleEngagementResponse)
def get_article_engagement_summary(slug: str, db: Session = Depends(get_db)) -> ArticleEngagementResponse:
    article = db.query(Article).filter(Article.slug == slug, Article.status == "published").first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return ArticleEngagementResponse.model_validate(get_article_engagement(article, db))


@app.post("/api/articles/{slug}/interactions", response_model=ArticleInteractionResponse)
def create_article_interaction(
    slug: str,
    payload: ArticleInteractionRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ArticleInteractionResponse:
    article = db.query(Article).filter(Article.slug == slug, Article.status == "published").first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    interaction_type = payload.interactionType.strip().lower()
    if interaction_type not in {"like", "favorite"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="interactionType 仅支持 like / favorite")

    client_ip = get_request_ip(request)
    frontend_session = get_frontend_session(request.headers.get("authorization"))
    frontend_user = resolve_frontend_user(frontend_session, db)
    existing_query = db.query(ArticleInteraction).filter(
        ArticleInteraction.articleId == article.id,
        ArticleInteraction.interactionType == interaction_type,
    )
    if frontend_user:
        existing_query = existing_query.filter(ArticleInteraction.userId == frontend_user.id)
    else:
        existing_query = existing_query.filter(
            ArticleInteraction.userId.is_(None),
            ArticleInteraction.clientIp == client_ip,
        )
    existing = existing_query.first()

    applied = False
    active = True
    now = datetime.utcnow()
    if existing:
        if frontend_user:
            existing.isCanceled = not existing.isCanceled
            existing.updatedAt = now
            active = not existing.isCanceled
            applied = active
            if interaction_type == "like":
                article.likeCount = max(0, article.likeCount + (1 if active else -1))
            article.updatedAt = now
            db.commit()
            db.refresh(article)
        else:
            active = not existing.isCanceled
    else:
        db.add(
            ArticleInteraction(
                articleId=article.id,
                userId=frontend_user.id if frontend_user else None,
                interactionType=interaction_type,
                clientIp=client_ip,
                isCanceled=False,
                createdAt=now,
                updatedAt=now,
            )
        )
        if interaction_type == "like":
            article.likeCount += 1
        article.updatedAt = now
        db.commit()
        db.refresh(article)
        applied = True

    stats = get_article_engagement(article, db)
    return ArticleInteractionResponse.model_validate(
        {
            "ok": True,
            "interactionType": interaction_type,
            "applied": applied,
            "active": active,
            "articleSlug": article.slug,
            **stats,
        }
    )


@app.get("/api/articles/{slug}/comments", response_model=ArticleCommentListResponse)
def list_article_comments(slug: str, db: Session = Depends(get_db)) -> ArticleCommentListResponse:
    article = db.query(Article).filter(Article.slug == slug, Article.status == "published").first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    items = (
        db.query(ArticleComment)
        .filter(
            ArticleComment.articleId == article.id,
            ArticleComment.status == "published",
        )
        .order_by(ArticleComment.createdAt.desc(), ArticleComment.id.desc())
        .all()
    )
    serialized = [serialize_article_comment(item) for item in items]
    return ArticleCommentListResponse.model_validate({"items": serialized, "total": len(serialized)})


@app.post("/api/articles/{slug}/comments", response_model=ArticleCommentOut, status_code=status.HTTP_201_CREATED)
def create_article_comment(
    slug: str,
    payload: ArticleCommentWrite,
    request: Request,
    db: Session = Depends(get_db),
) -> ArticleCommentOut:
    article = db.query(Article).filter(Article.slug == slug, Article.status == "published").first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    nickname = payload.nickname.strip() or "访客"
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="评论内容不能为空")
    if len(content) > 500:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="评论内容不能超过 500 字")
    if len(nickname) > 50:
        nickname = nickname[:50]

    now = datetime.utcnow()
    frontend_session = get_frontend_session(request.headers.get("authorization"))
    frontend_user = resolve_frontend_user(frontend_session, db)
    item = ArticleComment(
        articleId=article.id,
        userId=frontend_user.id if frontend_user else None,
        nickname=frontend_user.nickname if frontend_user else nickname,
        content=content,
        clientIp=get_request_ip(request),
        status="published",
        createdAt=now,
        updatedAt=now,
    )
    article.updatedAt = now
    db.add(item)
    db.commit()
    db.refresh(item)
    return ArticleCommentOut.model_validate(serialize_article_comment(item))


@app.get("/api/site-configs")
def list_site_configs(group: str = Query(default=""), db: Session = Depends(get_db)) -> dict:
    query = db.query(SiteConfig).order_by(SiteConfig.groupName.asc(), SiteConfig.configKey.asc())
    if group.strip():
        query = query.filter(SiteConfig.groupName == group.strip())
    items = [serialize_site_config(item) for item in query.all()]
    return {"items": items, "total": len(items)}


@app.get("/api/projects")
def list_projects(projectType: str = Query(default=""), db: Session = Depends(get_db)) -> dict:
    query = db.query(Project).order_by(Project.id.asc())
    if projectType.strip():
        query = query.filter(Project.projectType == projectType.strip())
    items = [serialize_project(item) for item in query.all() if is_public_status(item.status)]
    return {"items": items, "total": len(items)}


@app.get("/api/projects/{slug}", response_model=ProjectOut)
def get_project(slug: str, db: Session = Depends(get_db)) -> ProjectOut:
    item = db.query(Project).filter(Project.slug == slug).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not is_public_status(item.status):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return ProjectOut.model_validate(serialize_project(item))


@app.get("/api/offers")
def list_offers(db: Session = Depends(get_db)) -> dict:
    items = [
        serialize_offer(item)
        for item in db.query(Offer).order_by(Offer.id.asc()).all()
        if is_public_status(item.status)
    ]
    return {"items": items, "total": len(items)}


@app.get("/api/search", response_model=SearchResponse)
def search_site(
    q: str = Query(default=""),
    typeValue: str = Query(default="", alias="type"),
    db: Session = Depends(get_db),
) -> SearchResponse:
    keyword = q.strip().lower()
    normalized_type = typeValue.strip()
    items = build_search_result_items(db, keyword)
    counts = {
        "全部": len(items),
        "文章": len([item for item in items if item["type"] == "文章"]),
        "产品": len([item for item in items if item["type"] == "产品"]),
        "游戏": len([item for item in items if item["type"] == "游戏"]),
        "实验室": len([item for item in items if item["type"] == "实验室"]),
        "快来尝鲜": len([item for item in items if item["type"] == "快来尝鲜"]),
    }

    if normalized_type and normalized_type != "全部":
        items = [item for item in items if item["type"] == normalized_type]

    return SearchResponse.model_validate(
        {
            "query": q.strip(),
            "items": items,
            "total": len(items),
            "counts": counts,
        }
    )


@app.get("/api/offers/{slug}", response_model=OfferOut)
def get_offer(slug: str, db: Session = Depends(get_db)) -> OfferOut:
    item = db.query(Offer).filter(Offer.slug == slug).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not is_public_status(item.status):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return OfferOut.model_validate(serialize_offer(item))


@app.get("/api/ads")
def list_ads(
    pageKey: str = Query(default=""),
    slotKey: str = Query(default=""),
    db: Session = Depends(get_db),
) -> dict:
    serialized = fetch_active_ads(db, pageKey=pageKey, slot_key=slotKey)
    return {"items": serialized, "total": len(serialized)}


@app.get("/api/bootstrap")
def bootstrap(db: Session = Depends(get_db)) -> dict:
    page_configs = [
        item
        for item in db.query(PageConfig).order_by(PageConfig.pageKey.asc()).all()
        if is_public_status(item.status)
    ]
    site_config_rows = db.query(SiteConfig).order_by(SiteConfig.updatedAt.desc(), SiteConfig.id.desc()).all()
    site_configs: dict[str, SiteConfig] = {}
    site_config_values: dict[str, object] = {}
    for item in site_config_rows:
        if item.configKey in site_configs:
            continue
        site_configs[item.configKey] = item
        site_config_values[item.configKey] = parse_config_value(item.configValue, "")
    active_ads = fetch_active_ads(db)
    columns = [
        serialize_column(item)
        for item in db.query(ContentCategory).order_by(ContentCategory.sortOrder.asc(), ContentCategory.id.asc()).all()
        if is_public_status(item.status)
    ]
    tags = [
        serialize_tag(item)
        for item in db.query(ContentTag).order_by(ContentTag.id.asc()).all()
        if is_public_status(item.status)
    ]
    articles = [
        serialize_article(item)
        for item in db.query(Article)
        .options(
            joinedload(Article.column),
            joinedload(Article.tags),
            joinedload(Article.interactions),
            joinedload(Article.comments),
        )
        .order_by(Article.publishedAt.desc(), Article.id.desc())
        .all()
        if item.status == "published"
    ]
    projects = [
        serialize_project(item)
        for item in db.query(Project).order_by(Project.id.asc()).all()
        if is_public_status(item.status)
    ]
    offers = [
        serialize_offer(item)
        for item in db.query(Offer).order_by(Offer.id.asc()).all()
        if is_public_status(item.status)
    ]

    return {
        "site": {
            "siteMeta": parse_config_value(site_configs.get("site_meta").configValue if site_configs.get("site_meta") else "", {}),
            "mainNav": parse_config_value(site_configs.get("main_nav").configValue if site_configs.get("main_nav") else "", []),
            "footerSections": parse_config_value(site_configs.get("footer_sections").configValue if site_configs.get("footer_sections") else "", []),
            "socialLinks": parse_config_value(site_configs.get("social_links").configValue if site_configs.get("social_links") else "", []),
            "articleCategories": parse_config_value(site_configs.get("article_categories").configValue if site_configs.get("article_categories") else "", []),
            "articleHotTopics": parse_config_value(site_configs.get("article_hot_topics").configValue if site_configs.get("article_hot_topics") else "", []),
            "contactEmail": parse_config_value(site_configs.get("contact_email").configValue if site_configs.get("contact_email") else "", ""),
            "communityWechat": parse_config_value(site_configs.get("community_wechat").configValue if site_configs.get("community_wechat") else "", ""),
            "siteConfigs": site_config_values,
        },
        "pages": {item.pageKey: parse_json_dict(item.configJson) for item in page_configs},
        "content": {
            "columns": columns,
            "tags": tags,
            "articles": articles,
            "projects": projects,
            "offers": offers,
            "ads": active_ads,
        },
        "pageConfigs": [serialize_page_config(item) for item in page_configs],
    }


@app.get("/api/page-configs/{page_key}", response_model=PageConfigOut)
def get_page_config(page_key: str, db: Session = Depends(get_db)) -> PageConfigOut:
    item = db.query(PageConfig).filter(PageConfig.pageKey == page_key).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not is_public_status(item.status):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return PageConfigOut.model_validate(serialize_page_config(item))


@app.post("/api/wishlist", response_model=WishlistOut, status_code=status.HTTP_201_CREATED)
def create_wishlist_item(payload: WishlistWrite, db: Session = Depends(get_db)) -> WishlistOut:
    data = sanitize_wishlist_input(payload)
    now = current_time()
    frontend_user = None
    if data.get("userId"):
        frontend_user = db.query(FrontendUser).filter(FrontendUser.id == data["userId"]).first()
    item = WishlistItem(
        userId=frontend_user.id if frontend_user else None,
        visitorId=data["visitorId"],
        projectSlug=data["projectSlug"] or None,
        projectName=data["projectName"] or None,
        category=data["category"] or None,
        wishState=data["wishState"],
        sourcePage=data["sourcePage"] or None,
        contactType=data["contactType"] or None,
        contactValue=data["contactValue"] or None,
        note=data["note"] or None,
        isActive=1 if data["isActive"] else 0,
        createdAt=now,
        updatedAt=now,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return WishlistOut.model_validate(serialize_wishlist_item(item))


@app.get("/api/wishlist/summary")
def wishlist_summary(visitorId: str = Query(default=""), db: Session = Depends(get_db)) -> dict:
    query = db.query(WishlistItem).order_by(WishlistItem.updatedAt.desc(), WishlistItem.id.desc())
    if visitorId.strip():
        query = query.filter(WishlistItem.visitorId == visitorId.strip())
    items = query.all()
    serialized = [serialize_wishlist_item(item) for item in items]
    state_counts: dict[str, int] = {}
    for item in serialized:
        state_counts[item["wishState"]] = state_counts.get(item["wishState"], 0) + 1
    return {"items": serialized, "total": len(serialized), "states": state_counts}


@app.post("/api/community-leads", response_model=CommunityLeadOut, status_code=status.HTTP_201_CREATED)
def create_community_lead(payload: CommunityLeadWrite, db: Session = Depends(get_db)) -> CommunityLeadOut:
    data = sanitize_community_lead_input(payload)
    now = current_time()
    item = CommunityLead(
        userId=data.get("userId"),
        leadType=data["leadType"],
        intentReason=data["intentReason"],
        name=data["name"] or None,
        contactType=data["contactType"],
        contactValue=data["contactValue"],
        message=data["message"] or None,
        status="new",
        createdAt=now,
        updatedAt=now,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return CommunityLeadOut.model_validate(serialize_community_lead(item))


@app.post("/api/beta-applications", response_model=BetaApplicationOut, status_code=status.HTTP_201_CREATED)
def create_beta_application(payload: BetaApplicationWrite, db: Session = Depends(get_db)) -> BetaApplicationOut:
    data = sanitize_beta_application_input(payload)
    now = current_time()
    item = BetaApplication(
        userId=data.get("userId"),
        projectSlug=data["projectSlug"] or None,
        sourcePage=data["sourcePage"],
        roleType=data["roleType"],
        name=data["name"],
        contactType=data["contactType"],
        contactValue=data["contactValue"],
        city=data["city"] or None,
        experienceNote=data["experienceNote"] or None,
        status=data["status"],
        followUpNote=None,
        createdAt=now,
        updatedAt=now,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return BetaApplicationOut.model_validate(serialize_beta_application(item))


@app.post("/api/admin/database/sync", response_model=DatabaseSyncResponse)
def admin_sync_database(
    payload: DatabaseSyncRequest,
    _: dict = Depends(require_auth),
) -> DatabaseSyncResponse:
    result = sync_database_schema(apply_changes=payload.apply, seed_defaults=payload.seedDefaults)
    return DatabaseSyncResponse.model_validate(result)


@app.post("/api/admin/content/publish", response_model=AiContentPublishResponse)
def admin_publish_content(
    payload: AiContentPublishRequest,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> AiContentPublishResponse:
    result = publish_ai_content(payload, db)
    return AiContentPublishResponse.model_validate(result)


@app.get("/api/admin/articles")
def list_admin_articles(_: dict = Depends(require_auth), db: Session = Depends(get_db)) -> dict:
    items = (
        db.query(Article)
        .options(joinedload(Article.column), joinedload(Article.tags))
        .order_by(Article.updatedAt.desc(), Article.id.desc())
        .all()
    )
    serialized = [serialize_article(item) for item in items]
    return {"items": serialized, "total": len(serialized)}


@app.post("/api/admin/articles", response_model=ArticleOut, status_code=status.HTTP_201_CREATED)
def create_article(
    payload: ArticleWrite,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> ArticleOut:
    data = sanitize_article_input(payload, db)
    duplicate = db.query(Article).filter(Article.slug == data["slug"]).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="slug 已存在")

    now = datetime.utcnow()
    article = Article(
        title=data["title"],
        slug=data["slug"],
        summary=data["summary"],
        contentBody=data["contentBody"],
        authorName=data["authorName"],
        columnId=data["columnId"],
        coverImage=data["coverImage"],
        heroTone=data["heroTone"],
        status=data["status"],
        sourceType=data["sourceType"],
        publishedAt=now if data["status"] == "published" else None,
        viewCount=0,
        likeCount=0,
        createdAt=now,
        updatedAt=now,
    )
    article.column = data["column"]
    article.tags = data["tags"]
    db.add(article)
    db.commit()
    db.refresh(article)
    return ArticleOut.model_validate(serialize_article(article))


@app.put("/api/admin/articles/{article_id}", response_model=ArticleOut)
def update_article(
    article_id: int,
    payload: ArticleWrite,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> ArticleOut:
    article = (
        db.query(Article)
        .options(joinedload(Article.column), joinedload(Article.tags))
        .filter(Article.id == article_id)
        .first()
    )
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    data = sanitize_article_input(payload, db)
    duplicate = db.query(Article).filter(Article.slug == data["slug"], Article.id != article_id).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="slug 已存在")

    article.title = data["title"]
    article.slug = data["slug"]
    article.summary = data["summary"]
    article.contentBody = data["contentBody"]
    article.authorName = data["authorName"]
    article.columnId = data["columnId"]
    article.coverImage = data["coverImage"]
    article.heroTone = data["heroTone"]
    article.status = data["status"]
    article.sourceType = data["sourceType"]
    if data["status"] == "published" and not article.publishedAt:
        article.publishedAt = datetime.utcnow()
    article.updatedAt = datetime.utcnow()
    article.column = data["column"]
    article.tags = data["tags"]

    db.commit()
    db.refresh(article)
    return ArticleOut.model_validate(serialize_article(article))


@app.delete("/api/admin/articles/{article_id}", response_model=DeleteResponse)
def delete_article(
    article_id: int,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> DeleteResponse:
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.delete(article)
    db.commit()
    return DeleteResponse(ok=True, deletedId=article_id)


@app.get("/api/admin/site-configs")
def list_admin_site_configs(_: dict = Depends(require_auth), db: Session = Depends(get_db)) -> dict:
    items = db.query(SiteConfig).order_by(SiteConfig.groupName.asc(), SiteConfig.configKey.asc()).all()
    return {"items": [serialize_site_config(item) for item in items], "total": len(items)}


@app.post("/api/admin/site-configs", response_model=SiteConfigOut, status_code=status.HTTP_201_CREATED)
def create_site_config(
    payload: SiteConfigWrite,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> SiteConfigOut:
    data = sanitize_site_config_input(payload)
    duplicate = db.query(SiteConfig).filter(SiteConfig.configKey == data["configKey"]).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="configKey 已存在")
    item = SiteConfig(**data, updatedAt=datetime.utcnow())
    db.add(item)
    db.commit()
    db.refresh(item)
    return SiteConfigOut.model_validate(serialize_site_config(item))


@app.put("/api/admin/site-configs/{config_id}", response_model=SiteConfigOut)
def update_site_config(
    config_id: int,
    payload: SiteConfigWrite,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> SiteConfigOut:
    item = db.query(SiteConfig).filter(SiteConfig.id == config_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    data = sanitize_site_config_input(payload)
    duplicate = db.query(SiteConfig).filter(SiteConfig.configKey == data["configKey"], SiteConfig.id != config_id).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="configKey 已存在")
    item.configKey = data["configKey"]
    item.configValue = data["configValue"]
    item.groupName = data["groupName"]
    item.remark = data["remark"]
    item.updatedAt = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return SiteConfigOut.model_validate(serialize_site_config(item))


@app.delete("/api/admin/site-configs/{config_id}", response_model=DeleteResponse)
def delete_site_config(
    config_id: int,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> DeleteResponse:
    item = db.query(SiteConfig).filter(SiteConfig.id == config_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.delete(item)
    db.commit()
    return DeleteResponse(ok=True, deletedId=config_id)


@app.get("/api/admin/page-configs")
def list_admin_page_configs(_: dict = Depends(require_auth), db: Session = Depends(get_db)) -> dict:
    items = db.query(PageConfig).order_by(PageConfig.pageKey.asc()).all()
    return {"items": [serialize_page_config(item) for item in items], "total": len(items)}


@app.get("/api/admin/projects")
def list_admin_projects(projectType: str = Query(default=""), _: dict = Depends(require_auth), db: Session = Depends(get_db)) -> dict:
    query = db.query(Project).order_by(Project.projectType.asc(), Project.id.asc())
    if projectType.strip():
        query = query.filter(Project.projectType == projectType.strip())
    items = query.all()
    return {"items": [serialize_project(item) for item in items], "total": len(items)}


@app.post("/api/admin/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectWrite,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> ProjectOut:
    data = sanitize_project_input(payload)
    duplicate = db.query(Project).filter(Project.slug == data["slug"]).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="slug 已存在")
    now = datetime.utcnow()
    item = Project(
        slug=data["slug"],
        name=data["name"],
        projectType=data["projectType"],
        title=data["title"] or None,
        subtitle=data["subtitle"] or None,
        shortDesc=data["shortDesc"] or None,
        summary=data["summary"] or None,
        description=data["description"] or None,
        coverImage=data["coverImage"],
        bannerImage=data["bannerImage"],
        status=data["status"],
        stage=data["stage"] or None,
        supportStatus=data["supportStatus"] or None,
        price=data["price"] or None,
        originalPrice=data["originalPrice"] or None,
        tagsJson=json.dumps(data["tags"], ensure_ascii=False),
        featuresJson=json.dumps(data["features"], ensure_ascii=False),
        highlightsJson=json.dumps(data["highlights"], ensure_ascii=False),
        faqJson=json.dumps(data["faq"], ensure_ascii=False),
        testimonialsJson=json.dumps(data["testimonials"], ensure_ascii=False),
        extraJson=json.dumps(data["extra"], ensure_ascii=False),
        createdAt=now,
        updatedAt=now,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return ProjectOut.model_validate(serialize_project(item))


@app.put("/api/admin/projects/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectWrite,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> ProjectOut:
    item = db.query(Project).filter(Project.id == project_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    data = sanitize_project_input(payload)
    duplicate = db.query(Project).filter(Project.slug == data["slug"], Project.id != project_id).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="slug 已存在")
    item.slug = data["slug"]
    item.name = data["name"]
    item.projectType = data["projectType"]
    item.title = data["title"] or None
    item.subtitle = data["subtitle"] or None
    item.shortDesc = data["shortDesc"] or None
    item.summary = data["summary"] or None
    item.description = data["description"] or None
    item.coverImage = data["coverImage"]
    item.bannerImage = data["bannerImage"]
    item.status = data["status"]
    item.stage = data["stage"] or None
    item.supportStatus = data["supportStatus"] or None
    item.price = data["price"] or None
    item.originalPrice = data["originalPrice"] or None
    item.tagsJson = json.dumps(data["tags"], ensure_ascii=False)
    item.featuresJson = json.dumps(data["features"], ensure_ascii=False)
    item.highlightsJson = json.dumps(data["highlights"], ensure_ascii=False)
    item.faqJson = json.dumps(data["faq"], ensure_ascii=False)
    item.testimonialsJson = json.dumps(data["testimonials"], ensure_ascii=False)
    item.extraJson = json.dumps(data["extra"], ensure_ascii=False)
    item.updatedAt = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return ProjectOut.model_validate(serialize_project(item))


@app.delete("/api/admin/projects/{project_id}", response_model=DeleteResponse)
def delete_project(
    project_id: int,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> DeleteResponse:
    item = db.query(Project).filter(Project.id == project_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.delete(item)
    db.commit()
    return DeleteResponse(ok=True, deletedId=project_id)


@app.get("/api/admin/offers")
def list_admin_offers(_: dict = Depends(require_auth), db: Session = Depends(get_db)) -> dict:
    items = db.query(Offer).order_by(Offer.id.asc()).all()
    return {"items": [serialize_offer(item) for item in items], "total": len(items)}


@app.get("/api/admin/ads")
def list_admin_ads(
    pageKey: str = Query(default=""),
    slotKey: str = Query(default=""),
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(AdItem).order_by(AdItem.sortOrder.asc(), AdItem.id.asc())
    if pageKey.strip():
        query = query.filter(AdItem.pageKey == pageKey.strip())
    if slotKey.strip():
        query = query.filter(AdItem.slotKey == slotKey.strip())
    items = query.all()
    return {"items": [serialize_ad_item(item) for item in items], "total": len(items)}


@app.post("/api/admin/ads", response_model=AdItemOut, status_code=status.HTTP_201_CREATED)
def create_ad_item(
    payload: AdItemWrite,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> AdItemOut:
    data = sanitize_ad_item_input(payload)
    now = datetime.utcnow()
    item = AdItem(
        slotKey=data["slotKey"],
        title=data["title"],
        pageKey=data["pageKey"] or None,
        imageUrl=data["imageUrl"],
        targetUrl=data["targetUrl"],
        description=data["description"] or None,
        ctaLabel=data["ctaLabel"] or None,
        status=data["status"],
        sortOrder=data["sortOrder"],
        startAt=data["startAt"],
        endAt=data["endAt"],
        payloadJson=json.dumps(data["payload"], ensure_ascii=False),
        createdAt=now,
        updatedAt=now,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return AdItemOut.model_validate(serialize_ad_item(item))


@app.put("/api/admin/ads/{ad_id}", response_model=AdItemOut)
def update_ad_item(
    ad_id: int,
    payload: AdItemWrite,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> AdItemOut:
    item = db.query(AdItem).filter(AdItem.id == ad_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    data = sanitize_ad_item_input(payload)
    item.slotKey = data["slotKey"]
    item.title = data["title"]
    item.pageKey = data["pageKey"] or None
    item.imageUrl = data["imageUrl"]
    item.targetUrl = data["targetUrl"]
    item.description = data["description"] or None
    item.ctaLabel = data["ctaLabel"] or None
    item.status = data["status"]
    item.sortOrder = data["sortOrder"]
    item.startAt = data["startAt"]
    item.endAt = data["endAt"]
    item.payloadJson = json.dumps(data["payload"], ensure_ascii=False)
    item.updatedAt = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return AdItemOut.model_validate(serialize_ad_item(item))


@app.delete("/api/admin/ads/{ad_id}", response_model=DeleteResponse)
def delete_ad_item(
    ad_id: int,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> DeleteResponse:
    item = db.query(AdItem).filter(AdItem.id == ad_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.delete(item)
    db.commit()
    return DeleteResponse(ok=True, deletedId=ad_id)


@app.post("/api/admin/offers", response_model=OfferOut, status_code=status.HTTP_201_CREATED)
def create_offer(
    payload: OfferWrite,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> OfferOut:
    data = sanitize_offer_input(payload)
    duplicate = db.query(Offer).filter(Offer.slug == data["slug"]).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="slug 已存在")
    now = datetime.utcnow()
    item = Offer(
        slug=data["slug"],
        title=data["title"],
        subtitle=data["subtitle"],
        category=data["category"] or None,
        status=data["status"] or None,
        statusTone=data["statusTone"] or None,
        price=data["price"],
        originalPrice=data["originalPrice"] or None,
        bannerImage=data["bannerImage"],
        summary=data["summary"] or None,
        ctaLabel=data["ctaLabel"] or None,
        benefitsJson=json.dumps(data["benefits"], ensure_ascii=False),
        metaJson=json.dumps(data["meta"], ensure_ascii=False),
        extraJson=json.dumps(data["extra"], ensure_ascii=False),
        createdAt=now,
        updatedAt=now,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return OfferOut.model_validate(serialize_offer(item))


@app.put("/api/admin/offers/{offer_id}", response_model=OfferOut)
def update_offer(
    offer_id: int,
    payload: OfferWrite,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> OfferOut:
    item = db.query(Offer).filter(Offer.id == offer_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    data = sanitize_offer_input(payload)
    duplicate = db.query(Offer).filter(Offer.slug == data["slug"], Offer.id != offer_id).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="slug 已存在")
    item.slug = data["slug"]
    item.title = data["title"]
    item.subtitle = data["subtitle"]
    item.category = data["category"] or None
    item.status = data["status"] or None
    item.statusTone = data["statusTone"] or None
    item.price = data["price"]
    item.originalPrice = data["originalPrice"] or None
    item.bannerImage = data["bannerImage"]
    item.summary = data["summary"] or None
    item.ctaLabel = data["ctaLabel"] or None
    item.benefitsJson = json.dumps(data["benefits"], ensure_ascii=False)
    item.metaJson = json.dumps(data["meta"], ensure_ascii=False)
    item.extraJson = json.dumps(data["extra"], ensure_ascii=False)
    item.updatedAt = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return OfferOut.model_validate(serialize_offer(item))


@app.delete("/api/admin/offers/{offer_id}", response_model=DeleteResponse)
def delete_offer(
    offer_id: int,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> DeleteResponse:
    item = db.query(Offer).filter(Offer.id == offer_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.delete(item)
    db.commit()
    return DeleteResponse(ok=True, deletedId=offer_id)


@app.post("/api/admin/page-configs", response_model=PageConfigOut, status_code=status.HTTP_201_CREATED)
def create_page_config(
    payload: PageConfigWrite,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> PageConfigOut:
    data = sanitize_page_config_input(payload)
    duplicate = db.query(PageConfig).filter(PageConfig.pageKey == data["pageKey"]).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="pageKey 已存在")
    item = PageConfig(**data, updatedAt=datetime.utcnow())
    db.add(item)
    db.commit()
    db.refresh(item)
    return PageConfigOut.model_validate(serialize_page_config(item))


@app.put("/api/admin/page-configs/{config_id}", response_model=PageConfigOut)
def update_page_config(
    config_id: int,
    payload: PageConfigWrite,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> PageConfigOut:
    item = db.query(PageConfig).filter(PageConfig.id == config_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    data = sanitize_page_config_input(payload)
    duplicate = db.query(PageConfig).filter(PageConfig.pageKey == data["pageKey"], PageConfig.id != config_id).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="pageKey 已存在")
    item.pageKey = data["pageKey"]
    item.title = data["title"]
    item.configJson = data["configJson"]
    item.status = data["status"]
    item.remark = data["remark"]
    item.updatedAt = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return PageConfigOut.model_validate(serialize_page_config(item))


@app.delete("/api/admin/page-configs/{config_id}", response_model=DeleteResponse)
def delete_page_config(
    config_id: int,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> DeleteResponse:
    item = db.query(PageConfig).filter(PageConfig.id == config_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.delete(item)
    db.commit()
    return DeleteResponse(ok=True, deletedId=config_id)


@app.get("/api/admin/dashboard", response_model=DashboardResponse)
def admin_dashboard(_: dict = Depends(require_auth), db: Session = Depends(get_db)) -> DashboardResponse:
    articles_total = db.query(Article).count()
    projects = db.query(Project).all()
    offers_total = db.query(Offer).count()
    ads_total = db.query(AdItem).count()
    site_configs_total = db.query(SiteConfig).count()
    page_configs_total = db.query(PageConfig).count()
    frontend_users_total = db.query(FrontendUser).count()
    wishlist_items = db.query(WishlistItem).all()
    community_leads = db.query(CommunityLead).all()
    beta_applications = db.query(BetaApplication).all()

    project_type_counts = {"product": 0, "game": 0, "lab": 0}
    for item in projects:
        if item.projectType in project_type_counts:
            project_type_counts[item.projectType] += 1

    wishlist_by_state: dict[str, int] = {}
    wishlist_by_source: dict[str, int] = {}
    wishlist_by_project: dict[str, int] = {}
    for item in wishlist_items:
        wishlist_by_state[item.wishState] = wishlist_by_state.get(item.wishState, 0) + 1
        if item.sourcePage:
            wishlist_by_source[item.sourcePage] = wishlist_by_source.get(item.sourcePage, 0) + 1
        label = item.projectName or item.projectSlug or "未命名心愿"
        wishlist_by_project[label] = wishlist_by_project.get(label, 0) + 1

    leads_by_status: dict[str, int] = {}
    leads_by_type: dict[str, int] = {}
    for item in community_leads:
        leads_by_status[item.status] = leads_by_status.get(item.status, 0) + 1
        leads_by_type[item.leadType] = leads_by_type.get(item.leadType, 0) + 1

    beta_by_status: dict[str, int] = {}
    beta_by_role: dict[str, int] = {}
    for item in beta_applications:
        beta_by_status[item.status] = beta_by_status.get(item.status, 0) + 1
        beta_by_role[item.roleType] = beta_by_role.get(item.roleType, 0) + 1

    return DashboardResponse.model_validate(
        {
            "overview": {
                "articles": articles_total,
                "products": project_type_counts["product"],
                "games": project_type_counts["game"],
                "labs": project_type_counts["lab"],
                "offers": offers_total,
                "ads": ads_total,
                "siteConfigs": site_configs_total,
                "pageConfigs": page_configs_total,
                "frontendUsers": frontend_users_total,
                "wishlistItems": len(wishlist_items),
                "communityLeads": len(community_leads),
                "betaApplications": len(beta_applications),
                "userInteractions": len(wishlist_items) + len(community_leads) + len(beta_applications),
            },
            "wishlist": {
                "byState": wishlist_by_state,
                "bySource": wishlist_by_source,
                "topProjects": sorted(
                    [{"name": key, "count": value} for key, value in wishlist_by_project.items()],
                    key=lambda item: item["count"],
                    reverse=True,
                )[:5],
            },
            "leads": {"byStatus": leads_by_status, "byType": leads_by_type},
            "beta": {"byStatus": beta_by_status, "byRole": beta_by_role},
        }
    )


@app.get("/api/admin/frontend-users")
def list_admin_frontend_users(
    q: str = Query(default=""),
    statusValue: str = Query(default=""),
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(FrontendUser).order_by(FrontendUser.createdAt.desc(), FrontendUser.id.desc())
    if q.strip():
        keyword = f"%{q.strip().lower()}%"
        query = query.filter(
            (FrontendUser.username.like(keyword))
            | (FrontendUser.email.like(keyword))
            | (FrontendUser.nickname.like(keyword))
        )
    if statusValue.strip():
        query = query.filter(FrontendUser.status == statusValue.strip())

    items = []
    for user in query.all():
        items.append(
            {
                **serialize_frontend_user(user),
                "wishlistCount": db.query(WishlistItem).filter(WishlistItem.userId == user.id).count(),
                "likeCount": db.query(ArticleInteraction).filter(
                    ArticleInteraction.userId == user.id,
                    ArticleInteraction.interactionType == "like",
                    ArticleInteraction.isCanceled == False,
                ).count(),
                "favoriteCount": db.query(ArticleInteraction).filter(
                    ArticleInteraction.userId == user.id,
                    ArticleInteraction.interactionType == "favorite",
                    ArticleInteraction.isCanceled == False,
                ).count(),
                "commentCount": db.query(ArticleComment).filter(ArticleComment.userId == user.id).count(),
                "betaApplicationCount": db.query(BetaApplication).filter(BetaApplication.userId == user.id).count(),
                "communityLeadCount": db.query(CommunityLead).filter(CommunityLead.userId == user.id).count(),
            }
        )
    return {"items": items, "total": len(items)}


@app.put("/api/admin/frontend-users/{user_id}", response_model=FrontendUserListItem)
def update_admin_frontend_user(
    user_id: int,
    payload: FrontendUserUpdate,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> FrontendUserListItem:
    user = db.query(FrontendUser).filter(FrontendUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    email = payload.email.strip().lower() or user.email
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱格式不正确")
    duplicate = db.query(FrontendUser).filter(FrontendUser.email == email, FrontendUser.id != user_id).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已存在")

    user.nickname = payload.nickname.strip() or user.nickname
    user.email = email
    user.avatar = payload.avatar.strip()
    user.bio = payload.bio.strip() or None
    user.status = payload.status.strip() or user.status
    user.updatedAt = current_time()
    db.commit()
    db.refresh(user)

    return FrontendUserListItem.model_validate(
        {
            **serialize_frontend_user(user),
            "wishlistCount": db.query(WishlistItem).filter(WishlistItem.userId == user.id).count(),
            "likeCount": db.query(ArticleInteraction).filter(
                ArticleInteraction.userId == user.id,
                ArticleInteraction.interactionType == "like",
                ArticleInteraction.isCanceled == False,
            ).count(),
            "favoriteCount": db.query(ArticleInteraction).filter(
                ArticleInteraction.userId == user.id,
                ArticleInteraction.interactionType == "favorite",
                ArticleInteraction.isCanceled == False,
            ).count(),
            "commentCount": db.query(ArticleComment).filter(ArticleComment.userId == user.id).count(),
            "betaApplicationCount": db.query(BetaApplication).filter(BetaApplication.userId == user.id).count(),
            "communityLeadCount": db.query(CommunityLead).filter(CommunityLead.userId == user.id).count(),
        }
    )


@app.get("/api/admin/wishlist-items")
def list_admin_wishlist_items(
    wishState: str = Query(default=""),
    sourcePage: str = Query(default=""),
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(WishlistItem).order_by(WishlistItem.updatedAt.desc(), WishlistItem.id.desc())
    if wishState.strip():
        query = query.filter(WishlistItem.wishState == wishState.strip())
    if sourcePage.strip():
        query = query.filter(WishlistItem.sourcePage == sourcePage.strip())
    items = [serialize_wishlist_item(item) for item in query.all()]
    return {"items": items, "total": len(items)}


@app.put("/api/admin/wishlist-items/{item_id}", response_model=WishlistOut)
def update_admin_wishlist_item(
    item_id: int,
    payload: WishlistUpdate,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> WishlistOut:
    item = db.query(WishlistItem).filter(WishlistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    data = payload.model_dump()
    item.wishState = data["wishState"].strip() or item.wishState
    item.isActive = 1 if data["isActive"] else 0
    item.contactType = data["contactType"].strip() or item.contactType
    item.contactValue = data["contactValue"].strip() or item.contactValue
    item.note = data["note"].strip() or item.note
    item.updatedAt = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return WishlistOut.model_validate(serialize_wishlist_item(item))


@app.get("/api/admin/community-leads")
def list_admin_community_leads(
    leadType: str = Query(default=""),
    statusValue: str = Query(default=""),
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(CommunityLead).order_by(CommunityLead.updatedAt.desc(), CommunityLead.id.desc())
    if leadType.strip():
        query = query.filter(CommunityLead.leadType == leadType.strip())
    if statusValue.strip():
        query = query.filter(CommunityLead.status == statusValue.strip())
    items = [serialize_community_lead(item) for item in query.all()]
    return {"items": items, "total": len(items)}


@app.put("/api/admin/community-leads/{item_id}", response_model=CommunityLeadOut)
def update_admin_community_lead(
    item_id: int,
    payload: CommunityLeadUpdate,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> CommunityLeadOut:
    item = db.query(CommunityLead).filter(CommunityLead.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    data = payload.model_dump()
    item.status = data["status"].strip() or item.status
    item.message = data["message"].strip() or item.message
    item.updatedAt = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return CommunityLeadOut.model_validate(serialize_community_lead(item))


@app.get("/api/admin/beta-applications")
def list_admin_beta_applications(
    statusValue: str = Query(default=""),
    roleType: str = Query(default=""),
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(BetaApplication).order_by(BetaApplication.updatedAt.desc(), BetaApplication.id.desc())
    if statusValue.strip():
        query = query.filter(BetaApplication.status == statusValue.strip())
    if roleType.strip():
        query = query.filter(BetaApplication.roleType == roleType.strip())
    items = [serialize_beta_application(item) for item in query.all()]
    return {"items": items, "total": len(items)}


@app.put("/api/admin/beta-applications/{item_id}", response_model=BetaApplicationOut)
def update_admin_beta_application(
    item_id: int,
    payload: BetaApplicationUpdate,
    _: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> BetaApplicationOut:
    item = db.query(BetaApplication).filter(BetaApplication.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    data = payload.model_dump()
    item.status = data["status"].strip() or item.status
    item.followUpNote = data["followUpNote"].strip() or item.followUpNote
    item.updatedAt = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return BetaApplicationOut.model_validate(serialize_beta_application(item))
