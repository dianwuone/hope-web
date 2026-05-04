from __future__ import annotations

from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from .auth import login as do_login
from .auth import require_auth
from .database import BASE_DIR, Base, SessionLocal, engine, get_db
from .models import Article, ContentCategory, ContentTag, PageConfig, SiteConfig
from .schemas import (
    ArticleOut,
    ArticleWrite,
    DeleteResponse,
    HealthResponse,
    LoginResponse,
    PageConfigOut,
    PageConfigWrite,
    SiteConfigOut,
    SiteConfigWrite,
    UserLoginRequest,
)
from .seed import seed_if_empty


app = FastAPI(title="Quentin Window Backend", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PUBLIC_DIR = BASE_DIR / "public"
ADMIN_HTML = PUBLIC_DIR / "admin.html"
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


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_if_empty(db, SEED_FILE)


@app.get("/", include_in_schema=False)
@app.get("/admin", include_in_schema=False)
def admin_page() -> FileResponse:
    return FileResponse(ADMIN_HTML)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(ok=True, service="quentin-window-backend", time=datetime.utcnow())


@app.post("/api/admin/login", response_model=LoginResponse)
def admin_login(payload: UserLoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    return LoginResponse.model_validate(do_login(payload.username, payload.password, db))


@app.get("/api/columns")
def list_columns(db: Session = Depends(get_db)) -> dict:
    items = db.query(ContentCategory).order_by(ContentCategory.sortOrder.asc(), ContentCategory.id.asc()).all()
    return {"items": items, "total": len(items)}


@app.get("/api/tags")
def list_tags(db: Session = Depends(get_db)) -> dict:
    items = db.query(ContentTag).order_by(ContentTag.id.asc()).all()
    return {"items": items, "total": len(items)}


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


@app.get("/api/page-configs/{page_key}", response_model=PageConfigOut)
def get_page_config(page_key: str, db: Session = Depends(get_db)) -> PageConfigOut:
    item = db.query(PageConfig).filter(PageConfig.pageKey == page_key).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return PageConfigOut.model_validate(serialize_page_config(item))


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
