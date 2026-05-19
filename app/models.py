from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text
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


class FrontendUser(Base):
    __tablename__ = "frontend_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    email = Column(String(100), nullable=False, unique=True, index=True)
    passwordHash = Column(String(255), nullable=False)
    nickname = Column(String(50), nullable=False)
    avatar = Column(String(255), nullable=False, default="")
    bio = Column(Text, nullable=True)
    signature = Column(Text, nullable=False, default="")
    status = Column(String(20), nullable=False, default="active")
    lastLoginAt = Column(DateTime(timezone=False), nullable=True)
    createdAt = Column(DateTime(timezone=False), nullable=False)
    updatedAt = Column(DateTime(timezone=False), nullable=False)

    wishlistItems = relationship("WishlistItem", back_populates="user")
    articleInteractions = relationship("ArticleInteraction", back_populates="user")
    articleComments = relationship("ArticleComment", back_populates="user")
    communityLeads = relationship("CommunityLead", back_populates="user")
    betaApplications = relationship("BetaApplication", back_populates="user")
    emailVerificationCodes = relationship("EmailVerificationCode", back_populates="user")
    readingHistories = relationship("ReadingHistory", back_populates="user")


class EmailVerificationCode(Base):
    __tablename__ = "email_verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("frontend_users.id"), nullable=True, index=True)
    email = Column(String(100), nullable=False, index=True)
    purpose = Column(String(50), nullable=False, index=True)
    codeHash = Column(String(255), nullable=False)
    expiresAt = Column(DateTime(timezone=False), nullable=False, index=True)
    usedAt = Column(DateTime(timezone=False), nullable=True)
    createdAt = Column(DateTime(timezone=False), nullable=False)

    user = relationship("FrontendUser", back_populates="emailVerificationCodes")


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


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(120), nullable=False, unique=True, index=True)
    name = Column(String(120), nullable=False)
    projectType = Column(String(20), nullable=False)
    title = Column(String(200), nullable=True)
    subtitle = Column(Text, nullable=True)
    shortDesc = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    coverImage = Column(String(255), nullable=False, default="")
    bannerImage = Column(String(255), nullable=False, default="")
    status = Column(String(30), nullable=False, default="draft")
    stage = Column(String(30), nullable=True)
    supportStatus = Column(String(30), nullable=True)
    price = Column(String(30), nullable=True)
    originalPrice = Column(String(30), nullable=True)
    tagsJson = Column(Text, nullable=False, default="[]")
    featuresJson = Column(Text, nullable=False, default="[]")
    highlightsJson = Column(Text, nullable=False, default="[]")
    faqJson = Column(Text, nullable=False, default="[]")
    testimonialsJson = Column(Text, nullable=False, default="[]")
    extraJson = Column(Text, nullable=False, default="{}")
    createdAt = Column(DateTime(timezone=False), nullable=False)
    updatedAt = Column(DateTime(timezone=False), nullable=False)


class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(120), nullable=False, unique=True, index=True)
    title = Column(String(200), nullable=False)
    subtitle = Column(Text, nullable=False)
    category = Column(String(50), nullable=True)
    status = Column(String(50), nullable=True)
    statusTone = Column(String(30), nullable=True)
    price = Column(String(30), nullable=False)
    originalPrice = Column(String(30), nullable=True)
    bannerImage = Column(String(255), nullable=False, default="")
    summary = Column(Text, nullable=True)
    ctaLabel = Column(String(50), nullable=True)
    benefitsJson = Column(Text, nullable=False, default="[]")
    metaJson = Column(Text, nullable=False, default="[]")
    extraJson = Column(Text, nullable=False, default="{}")
    createdAt = Column(DateTime(timezone=False), nullable=False)
    updatedAt = Column(DateTime(timezone=False), nullable=False)


class AdItem(Base):
    __tablename__ = "ad_items"

    id = Column(Integer, primary_key=True, index=True)
    slotKey = Column(String(100), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    pageKey = Column(String(100), nullable=True, index=True)
    imageUrl = Column(String(255), nullable=False, default="")
    targetUrl = Column(String(255), nullable=False, default="")
    description = Column(Text, nullable=True)
    ctaLabel = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, default="draft")
    sortOrder = Column(Integer, nullable=False, default=0)
    startAt = Column(DateTime(timezone=False), nullable=True)
    endAt = Column(DateTime(timezone=False), nullable=True)
    payloadJson = Column(Text, nullable=False, default="{}")
    createdAt = Column(DateTime(timezone=False), nullable=False)
    updatedAt = Column(DateTime(timezone=False), nullable=False)


class BetaApplication(Base):
    __tablename__ = "beta_applications"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("frontend_users.id"), nullable=True, index=True)
    projectSlug = Column(String(120), nullable=True, index=True)
    sourcePage = Column(String(50), nullable=False, default="lab")
    roleType = Column(String(30), nullable=False)
    name = Column(String(50), nullable=False)
    contactType = Column(String(20), nullable=False)
    contactValue = Column(String(100), nullable=False)
    city = Column(String(50), nullable=True)
    experienceNote = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    followUpNote = Column(Text, nullable=True)
    createdAt = Column(DateTime(timezone=False), nullable=False)
    updatedAt = Column(DateTime(timezone=False), nullable=False)

    user = relationship("FrontendUser", back_populates="betaApplications")


class CommunityLead(Base):
    __tablename__ = "community_leads"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("frontend_users.id"), nullable=True, index=True)
    leadType = Column(String(20), nullable=False, default="community")
    intentReason = Column(String(30), nullable=False)
    name = Column(String(50), nullable=True)
    contactType = Column(String(20), nullable=False)
    contactValue = Column(String(100), nullable=False)
    message = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="new")
    createdAt = Column(DateTime(timezone=False), nullable=False)
    updatedAt = Column(DateTime(timezone=False), nullable=False)

    user = relationship("FrontendUser", back_populates="communityLeads")


class WishlistItem(Base):
    __tablename__ = "wishlist_items"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("frontend_users.id"), nullable=True, index=True)
    visitorId = Column(String(64), nullable=False, index=True)
    projectSlug = Column(String(120), nullable=True, index=True)
    projectName = Column(String(120), nullable=True)
    category = Column(String(30), nullable=True)
    wishState = Column(String(20), nullable=False, default="want_try")
    sourcePage = Column(String(50), nullable=True)
    contactType = Column(String(20), nullable=True)
    contactValue = Column(String(100), nullable=True)
    note = Column(Text, nullable=True)
    isActive = Column(Integer, nullable=False, default=1)
    createdAt = Column(DateTime(timezone=False), nullable=False)
    updatedAt = Column(DateTime(timezone=False), nullable=False)

    user = relationship("FrontendUser", back_populates="wishlistItems")


class ArticleInteraction(Base):
    __tablename__ = "article_interactions"

    id = Column(Integer, primary_key=True, index=True)
    articleId = Column(Integer, ForeignKey("articles.id"), nullable=False, index=True)
    userId = Column(Integer, ForeignKey("frontend_users.id"), nullable=True, index=True)
    interactionType = Column(String(20), nullable=False, index=True)
    clientIp = Column(String(64), nullable=False, index=True)
    isCanceled = Column(Boolean, nullable=False, default=False)
    createdAt = Column(DateTime(timezone=False), nullable=False)
    updatedAt = Column(DateTime(timezone=False), nullable=False)

    article = relationship("Article", back_populates="interactions")
    user = relationship("FrontendUser", back_populates="articleInteractions")


class ArticleComment(Base):
    __tablename__ = "article_comments"

    id = Column(Integer, primary_key=True, index=True)
    articleId = Column(Integer, ForeignKey("articles.id"), nullable=False, index=True)
    userId = Column(Integer, ForeignKey("frontend_users.id"), nullable=True, index=True)
    nickname = Column(String(50), nullable=False, default="访客")
    content = Column(Text, nullable=False)
    clientIp = Column(String(64), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="published")
    createdAt = Column(DateTime(timezone=False), nullable=False)
    updatedAt = Column(DateTime(timezone=False), nullable=False)

    article = relationship("Article", back_populates="comments")
    user = relationship("FrontendUser", back_populates="articleComments")


class ReadingHistory(Base):
    __tablename__ = "reading_histories"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("frontend_users.id"), nullable=False, index=True)
    articleSlug = Column(String(150), nullable=False, index=True)
    articleTitle = Column(String(200), nullable=False, default="")
    articleSummary = Column(Text, nullable=True)
    coverImage = Column(String(255), nullable=False, default="")
    authorName = Column(String(50), nullable=False, default="")
    categoryName = Column(String(100), nullable=False, default="")
    viewedAt = Column(DateTime(timezone=False), nullable=False, index=True)
    createdAt = Column(DateTime(timezone=False), nullable=False)
    updatedAt = Column(DateTime(timezone=False), nullable=False)

    user = relationship("FrontendUser", back_populates="readingHistories")


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
    interactions = relationship("ArticleInteraction", back_populates="article", cascade="all, delete-orphan")
    comments = relationship("ArticleComment", back_populates="article", cascade="all, delete-orphan")
