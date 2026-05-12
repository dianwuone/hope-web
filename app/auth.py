from __future__ import annotations

from hashlib import sha256
from secrets import token_urlsafe

from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from .models import AdminUser, FrontendUser
from .timeutils import current_time


sessions: dict[str, dict] = {}
frontend_sessions: dict[str, dict] = {}


def hash_password(password: str) -> str:
    return sha256(password.encode("utf-8")).hexdigest()


def login(username: str, password: str, db: Session) -> dict:
    user = (
        db.query(AdminUser)
        .filter(
            AdminUser.username == username,
            AdminUser.password == password,
            AdminUser.status == "active",
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    token = token_urlsafe(32)
    sessions[token] = {
        "id": user.id,
        "username": user.username,
        "displayName": user.displayName,
        "role": user.role,
        "loginAt": current_time(),
    }
    return {"token": token, "user": sessions[token]}


def login_frontend(account: str, password: str, db: Session) -> dict:
    normalized = account.strip().lower()
    password_hash = hash_password(password)
    user = (
        db.query(FrontendUser)
        .filter(
            ((FrontendUser.username == normalized) | (FrontendUser.email == normalized)),
            FrontendUser.passwordHash == password_hash,
            FrontendUser.status == "active",
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")

    token = token_urlsafe(32)
    now = current_time()
    user.lastLoginAt = now
    user.updatedAt = now
    db.commit()
    db.refresh(user)
    frontend_sessions[token] = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "nickname": user.nickname,
        "avatar": user.avatar or "",
        "status": user.status,
        "loginAt": now,
    }
    return {"token": token, "user": user}


def require_auth(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    token = authorization[7:]
    session = sessions.get(token)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return session


def get_frontend_session(authorization: str | None = Header(default=None)) -> dict | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    return frontend_sessions.get(token)


def require_frontend_auth(authorization: str | None = Header(default=None)) -> dict:
    session = get_frontend_session(authorization)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    return session
