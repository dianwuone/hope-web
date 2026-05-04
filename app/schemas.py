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
