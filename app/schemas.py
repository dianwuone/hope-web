from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UserLoginRequest(BaseModel):
    username: str
    password: str


class AdminUserOut(ApiModel):
    id: int
    username: str
    displayName: str
    role: str
    loginAt: datetime | None = None


class LoginResponse(ApiModel):
    token: str
    user: AdminUserOut


class ColumnOut(ApiModel):
    id: int
    name: str
    slug: str
    categoryType: str
    description: str | None = None
    sortOrder: int
    status: str


class TagOut(ApiModel):
    id: int
    name: str
    slug: str
    tagType: str
    status: str


class ArticleWrite(BaseModel):
    title: str
    slug: str
    summary: str
    contentBody: str
    authorName: str
    columnId: int
    tagIds: list[int] = Field(default_factory=list)
    status: str = "draft"
    sourceType: str = "original"
    coverImage: str = ""
    heroTone: str = "warm"


class ArticleOut(ApiModel):
    id: int
    title: str
    slug: str
    summary: str
    contentBody: str
    authorName: str
    columnId: int
    tagIds: list[int]
    coverImage: str
    heroTone: str
    status: str
    sourceType: str
    publishedAt: datetime | None = None
    viewCount: int
    likeCount: int
    createdAt: datetime
    updatedAt: datetime
    column: ColumnOut | None = None
    tags: list[TagOut] = Field(default_factory=list)


class ListResponse(ApiModel):
    items: list
    total: int


class DeleteResponse(ApiModel):
    ok: bool
    deletedId: int


class HealthResponse(ApiModel):
    ok: bool
    service: str
    time: datetime


class SiteConfigWrite(BaseModel):
    configKey: str
    configValue: str
    groupName: str = "general"
    remark: str = ""


class SiteConfigOut(ApiModel):
    id: int
    configKey: str
    configValue: str
    groupName: str
    remark: str | None = None
    updatedAt: datetime


class PageConfigWrite(BaseModel):
    pageKey: str
    title: str
    configJson: str
    status: str = "active"
    remark: str = ""


class PageConfigOut(ApiModel):
    id: int
    pageKey: str
    title: str
    configJson: str
    status: str
    remark: str | None = None
    updatedAt: datetime


class ProjectWrite(BaseModel):
    slug: str
    name: str
    projectType: str
    title: str = ""
    subtitle: str = ""
    shortDesc: str = ""
    summary: str = ""
    description: str = ""
    coverImage: str = ""
    bannerImage: str = ""
    status: str = "draft"
    stage: str = ""
    supportStatus: str = ""
    price: str = ""
    originalPrice: str = ""
    tags: list = Field(default_factory=list)
    features: list = Field(default_factory=list)
    highlights: list = Field(default_factory=list)
    faq: list = Field(default_factory=list)
    testimonials: list = Field(default_factory=list)
    extra: dict = Field(default_factory=dict)


class OfferWrite(BaseModel):
    slug: str
    title: str
    subtitle: str
    category: str = ""
    status: str = ""
    statusTone: str = ""
    price: str
    originalPrice: str = ""
    bannerImage: str = ""
    summary: str = ""
    ctaLabel: str = ""
    benefits: list = Field(default_factory=list)
    meta: list = Field(default_factory=list)
    extra: dict = Field(default_factory=dict)


class ProjectOut(ApiModel):
    id: int
    slug: str
    name: str
    projectType: str
    title: str | None = None
    subtitle: str | None = None
    shortDesc: str | None = None
    summary: str | None = None
    description: str | None = None
    coverImage: str
    bannerImage: str
    status: str
    stage: str | None = None
    supportStatus: str | None = None
    price: str | None = None
    originalPrice: str | None = None
    tags: list = Field(default_factory=list)
    features: list = Field(default_factory=list)
    highlights: list = Field(default_factory=list)
    faq: list = Field(default_factory=list)
    testimonials: list = Field(default_factory=list)
    extra: dict = Field(default_factory=dict)
    createdAt: datetime
    updatedAt: datetime


class OfferOut(ApiModel):
    id: int
    slug: str
    title: str
    subtitle: str
    category: str | None = None
    status: str | None = None
    statusTone: str | None = None
    price: str
    originalPrice: str | None = None
    bannerImage: str
    summary: str | None = None
    ctaLabel: str | None = None
    benefits: list = Field(default_factory=list)
    meta: list = Field(default_factory=list)
    extra: dict = Field(default_factory=dict)
    createdAt: datetime
    updatedAt: datetime


class AdItemWrite(BaseModel):
    slotKey: str
    title: str
    pageKey: str = ""
    imageUrl: str = ""
    targetUrl: str = ""
    description: str = ""
    ctaLabel: str = ""
    status: str = "draft"
    sortOrder: int = 0
    startAt: datetime | None = None
    endAt: datetime | None = None
    payload: dict = Field(default_factory=dict)


class AdItemOut(ApiModel):
    id: int
    slotKey: str
    title: str
    pageKey: str | None = None
    imageUrl: str
    targetUrl: str
    description: str | None = None
    ctaLabel: str | None = None
    status: str
    sortOrder: int
    startAt: datetime | None = None
    endAt: datetime | None = None
    payload: dict = Field(default_factory=dict)
    createdAt: datetime
    updatedAt: datetime


class WishlistWrite(BaseModel):
    visitorId: str = ""
    projectSlug: str = ""
    projectName: str = ""
    category: str = ""
    wishState: str = "want_try"
    sourcePage: str = "wishlist"
    contactType: str = ""
    contactValue: str = ""
    note: str = ""
    isActive: bool = True


class WishlistUpdate(BaseModel):
    wishState: str = "want_try"
    isActive: bool = True
    contactType: str = ""
    contactValue: str = ""
    note: str = ""


class WishlistOut(ApiModel):
    id: int
    visitorId: str
    projectSlug: str | None = None
    projectName: str | None = None
    category: str | None = None
    wishState: str
    sourcePage: str | None = None
    contactType: str | None = None
    contactValue: str | None = None
    note: str | None = None
    isActive: int
    createdAt: datetime
    updatedAt: datetime


class CommunityLeadWrite(BaseModel):
    leadType: str = "community"
    intentReason: str = "latest_updates"
    name: str = ""
    contactType: str = "wechat"
    contactValue: str
    message: str = ""


class CommunityLeadUpdate(BaseModel):
    status: str = "new"
    message: str = ""


class CommunityLeadOut(ApiModel):
    id: int
    leadType: str
    intentReason: str
    name: str | None = None
    contactType: str
    contactValue: str
    message: str | None = None
    status: str
    createdAt: datetime
    updatedAt: datetime


class BetaApplicationWrite(BaseModel):
    projectSlug: str = ""
    sourcePage: str = "lab"
    roleType: str = "explorer"
    name: str
    contactType: str = "wechat"
    contactValue: str
    city: str = ""
    experienceNote: str = ""
    status: str = "pending"


class BetaApplicationUpdate(BaseModel):
    status: str = "pending"
    followUpNote: str = ""


class BetaApplicationOut(ApiModel):
    id: int
    projectSlug: str | None = None
    sourcePage: str
    roleType: str
    name: str
    contactType: str
    contactValue: str
    city: str | None = None
    experienceNote: str | None = None
    status: str
    followUpNote: str | None = None
    createdAt: datetime
    updatedAt: datetime


class DashboardResponse(ApiModel):
    overview: dict
    wishlist: dict
    leads: dict
    beta: dict
