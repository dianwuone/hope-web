from __future__ import annotations

import json
from datetime import datetime
import re

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, joinedload

from .auth import login as do_login
from .auth import require_auth
from .database import BASE_DIR, Base, SessionLocal, engine, get_db
from .models import (
    AdItem,
    Article,
    BetaApplication,
    CommunityLead,
    ContentCategory,
    ContentTag,
    Offer,
    PageConfig,
    Project,
    SiteConfig,
    WishlistItem,
)
from .schemas import (
    AdItemOut,
    AdItemWrite,
    ArticleOut,
    ArticleWrite,
    BetaApplicationOut,
    BetaApplicationUpdate,
    BetaApplicationWrite,
    CommunityLeadOut,
    CommunityLeadUpdate,
    CommunityLeadWrite,
    DashboardResponse,
    DeleteResponse,
    HealthResponse,
    LoginResponse,
    OfferOut,
    OfferWrite,
    PageConfigOut,
    PageConfigWrite,
    ProjectOut,
    ProjectWrite,
    SiteConfigOut,
    SiteConfigWrite,
    UserLoginRequest,
    WishlistOut,
    WishlistUpdate,
    WishlistWrite,
)
from .timeutils import current_time, current_timestamp_ms
from .seed import seed_if_empty


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
    parsed = parse_json_dict(value)
    if parsed:
        if isinstance(parsed, dict) and set(parsed.keys()) == {"value"}:
            return parsed["value"]
        return parsed
    parsed_list = parse_json_list(value)
    if parsed_list:
        return parsed_list
    return fallback


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
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_if_empty(db, SEED_FILE)

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


@app.post("/api/admin/login", response_model=LoginResponse)
def admin_login(payload: UserLoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    return LoginResponse.model_validate(do_login(payload.username, payload.password, db))


@app.get("/api/columns")
def list_columns(db: Session = Depends(get_db)) -> dict:
    items = db.query(ContentCategory).order_by(ContentCategory.sortOrder.asc(), ContentCategory.id.asc()).all()
    return {"items": [serialize_column(item) for item in items], "total": len(items)}


@app.get("/api/tags")
def list_tags(db: Session = Depends(get_db)) -> dict:
    items = db.query(ContentTag).order_by(ContentTag.id.asc()).all()
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
        .options(joinedload(Article.column), joinedload(Article.tags))
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
        .options(joinedload(Article.column), joinedload(Article.tags))
        .filter(Article.slug == slug)
        .first()
    )
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return ArticleOut.model_validate(serialize_article(article))


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
    items = [serialize_project(item) for item in query.all()]
    return {"items": items, "total": len(items)}


@app.get("/api/projects/{slug}", response_model=ProjectOut)
def get_project(slug: str, db: Session = Depends(get_db)) -> ProjectOut:
    item = db.query(Project).filter(Project.slug == slug).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return ProjectOut.model_validate(serialize_project(item))


@app.get("/api/offers")
def list_offers(db: Session = Depends(get_db)) -> dict:
    items = [serialize_offer(item) for item in db.query(Offer).order_by(Offer.id.asc()).all()]
    return {"items": items, "total": len(items)}


@app.get("/api/offers/{slug}", response_model=OfferOut)
def get_offer(slug: str, db: Session = Depends(get_db)) -> OfferOut:
    item = db.query(Offer).filter(Offer.slug == slug).first()
    if not item:
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
    page_configs = db.query(PageConfig).order_by(PageConfig.pageKey.asc()).all()
    site_configs = {item.configKey: item for item in db.query(SiteConfig).all()}
    active_ads = fetch_active_ads(db)
    columns = [serialize_column(item) for item in db.query(ContentCategory).order_by(ContentCategory.sortOrder.asc(), ContentCategory.id.asc()).all()]
    tags = [serialize_tag(item) for item in db.query(ContentTag).order_by(ContentTag.id.asc()).all()]
    articles = [
        serialize_article(item)
        for item in db.query(Article).options(joinedload(Article.column), joinedload(Article.tags)).order_by(Article.publishedAt.desc(), Article.id.desc()).all()
    ]
    projects = [serialize_project(item) for item in db.query(Project).order_by(Project.id.asc()).all()]
    offers = [serialize_offer(item) for item in db.query(Offer).order_by(Offer.id.asc()).all()]

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
    return PageConfigOut.model_validate(serialize_page_config(item))


@app.post("/api/wishlist", response_model=WishlistOut, status_code=status.HTTP_201_CREATED)
def create_wishlist_item(payload: WishlistWrite, db: Session = Depends(get_db)) -> WishlistOut:
    data = sanitize_wishlist_input(payload)
    now = current_time()
    item = WishlistItem(
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
