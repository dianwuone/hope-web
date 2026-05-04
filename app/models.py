from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import relationship

from .database import Base


article_tag_relations = Table(
    "article_tag_relations",
    Base.metadata,
    Column("article_id", ForeignKey("articles.id"), primary_key=True),
    Column("tag_id", ForeignKey("content_tags.id"), primary_key=True),
)


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    password = Column(String(255), nullable=False)
    displayName = Column(String(50), nullable=False)
    role = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)


class ContentCategory(Base):
    __tablename__ = "content_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    categoryType = Column(String(20), nullable=False)
    description = Column(String(255), nullable=True)
    sortOrder = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False)

    articles = relationship("Article", back_populates="column")


class ContentTag(Base):
    __tablename__ = "content_tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    slug = Column(String(50), nullable=False, unique=True, index=True)
    tagType = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)

    articles = relationship("Article", secondary=article_tag_relations, back_populates="tags")


class SiteConfig(Base):
    __tablename__ = "site_configs"

    id = Column(Integer, primary_key=True, index=True)
    configKey = Column(String(100), nullable=False, unique=True, index=True)
    configValue = Column(Text, nullable=False)
    groupName = Column(String(50), nullable=False, default="general")
    remark = Column(String(255), nullable=True)
    updatedAt = Column(DateTime(timezone=False), nullable=False)


class PageConfig(Base):
    __tablename__ = "page_configs"

    id = Column(Integer, primary_key=True, index=True)
    pageKey = Column(String(100), nullable=False, unique=True, index=True)
    title = Column(String(150), nullable=False)
    configJson = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="active")
    remark = Column(String(255), nullable=True)
    updatedAt = Column(DateTime(timezone=False), nullable=False)


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    slug = Column(String(150), nullable=False, unique=True, index=True)
    summary = Column(Text, nullable=False)
    contentBody = Column(Text, nullable=False)
    authorName = Column(String(50), nullable=False)
    columnId = Column(Integer, ForeignKey("content_categories.id"), nullable=False)
    coverImage = Column(String(255), nullable=False, default="")
    heroTone = Column(String(20), nullable=False, default="warm")
    status = Column(String(20), nullable=False, default="draft")
    sourceType = Column(String(20), nullable=False, default="original")
    publishedAt = Column(DateTime(timezone=False), nullable=True)
    viewCount = Column(Integer, nullable=False, default=0)
    likeCount = Column(Integer, nullable=False, default=0)
    createdAt = Column(DateTime(timezone=False), nullable=False)
    updatedAt = Column(DateTime(timezone=False), nullable=False)

    column = relationship("ContentCategory", back_populates="articles")
    tags = relationship("ContentTag", secondary=article_tag_relations, back_populates="articles")
