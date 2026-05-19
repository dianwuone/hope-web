from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

from fastapi import HTTPException, status


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name, "")
    if not value:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_mail_settings() -> dict:
    return {
        "host": os.getenv("SMTP_HOST", "").strip(),
        "port": int(os.getenv("SMTP_PORT", "465").strip() or "465"),
        "username": os.getenv("SMTP_USERNAME", "").strip(),
        "password": os.getenv("SMTP_PASSWORD", "").strip(),
        "from_email": os.getenv("SMTP_FROM_EMAIL", "").strip(),
        "from_name": os.getenv("SMTP_FROM_NAME", "Quentin Window").strip() or "Quentin Window",
        "use_tls": _bool_env("SMTP_USE_TLS"),
        "use_ssl": _bool_env("SMTP_USE_SSL", True),
        "timeout": int(os.getenv("SMTP_TIMEOUT_SECONDS", "15").strip() or "15"),
        "app_name": os.getenv("APP_NAME", "Quentin Window").strip() or "Quentin Window",
    }


def ensure_mail_configured() -> dict:
    settings = get_mail_settings()
    required_fields = {
        "SMTP_HOST": settings["host"],
        "SMTP_FROM_EMAIL": settings["from_email"],
    }
    missing = [key for key, value in required_fields.items() if not value]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"邮件服务未配置，请先设置环境变量：{', '.join(missing)}",
        )
    if not settings["use_ssl"] and not settings["use_tls"] and settings["port"] == 465:
        settings["use_ssl"] = True
    return settings


def send_email(to_email: str, subject: str, text: str, html: str = "") -> None:
    settings = ensure_mail_configured()
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings['from_name']} <{settings['from_email']}>"
    message["To"] = to_email
    message.set_content(text)
    if html.strip():
        message.add_alternative(html, subtype="html")

    try:
        if settings["use_ssl"]:
            with smtplib.SMTP_SSL(settings["host"], settings["port"], timeout=settings["timeout"]) as server:
                if settings["username"]:
                    server.login(settings["username"], settings["password"])
                server.send_message(message)
            return

        with smtplib.SMTP(settings["host"], settings["port"], timeout=settings["timeout"]) as server:
            if settings["use_tls"]:
                server.starttls()
            if settings["username"]:
                server.login(settings["username"], settings["password"])
            server.send_message(message)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"邮件发送失败：{exc}",
        ) from exc
