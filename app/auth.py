from __future__ import annotations

from datetime import datetime
from secrets import token_urlsafe

from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from .models import AdminUser


sessions: dict[str, dict] = {}


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
        "loginAt": datetime.utcnow(),
    }
    return {"token": token, "user": sessions[token]}


def require_auth(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    token = authorization[7:]
    session = sessions.get(token)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return session
