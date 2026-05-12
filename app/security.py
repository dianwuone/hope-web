from __future__ import annotations

import asyncio
import html
import random
import time
from collections import deque
from dataclasses import dataclass, field
from secrets import token_urlsafe

from fastapi import HTTPException, status


CAPTCHA_TTL_SECONDS = 5 * 60
FAILURE_WINDOW_SECONDS = 15 * 60
CAPTCHA_AFTER_FAILURES = 3
MAX_FAILURE_HISTORY = 20


@dataclass
class CaptchaChallenge:
    key: str
    answer: str
    scope: str
    created_at: float
    expires_at: float


@dataclass
class AttemptState:
    failures: deque[float] = field(default_factory=deque)
    cooldown_until: float = 0.0


captcha_store: dict[str, CaptchaChallenge] = {}
attempt_store: dict[str, AttemptState] = {}


def _now() -> float:
    return time.time()


def cleanup_security_state() -> None:
    now = _now()
    expired_captchas = [key for key, item in captcha_store.items() if item.expires_at <= now]
    for key in expired_captchas:
        captcha_store.pop(key, None)

    stale_attempts: list[str] = []
    for key, state in attempt_store.items():
        while state.failures and now - state.failures[0] > FAILURE_WINDOW_SECONDS:
            state.failures.popleft()
        if not state.failures and state.cooldown_until <= now:
            stale_attempts.append(key)
    for key in stale_attempts:
        attempt_store.pop(key, None)


def _attempt_key(scope: str, ip: str, account: str) -> str:
    normalized_account = (account or "").strip().lower()[:80]
    normalized_ip = (ip or "unknown").strip().lower()[:64]
    return f"{scope}:{normalized_ip}:{normalized_account}"


def _get_state(scope: str, ip: str, account: str) -> AttemptState:
    cleanup_security_state()
    key = _attempt_key(scope, ip, account)
    state = attempt_store.get(key)
    if not state:
        state = AttemptState()
        attempt_store[key] = state
    return state


def _delay_seconds_for_failures(failure_count: int) -> int:
    if failure_count >= 8:
        return 60
    if failure_count >= 5:
        return 10
    if failure_count >= 3:
        return 1
    return 0


async def apply_login_delay(scope: str, ip: str, account: str) -> None:
    state = _get_state(scope, ip, account)
    now = _now()
    remaining = max(0.0, state.cooldown_until - now)
    if remaining > 0:
        await asyncio.sleep(remaining)


def needs_captcha(scope: str, ip: str, account: str) -> bool:
    state = _get_state(scope, ip, account)
    return len(state.failures) >= CAPTCHA_AFTER_FAILURES


def mark_login_failure(scope: str, ip: str, account: str) -> dict:
    state = _get_state(scope, ip, account)
    now = _now()
    state.failures.append(now)
    while len(state.failures) > MAX_FAILURE_HISTORY:
        state.failures.popleft()
    delay_seconds = _delay_seconds_for_failures(len(state.failures))
    state.cooldown_until = max(state.cooldown_until, now + delay_seconds)
    return {
        "failureCount": len(state.failures),
        "delaySeconds": delay_seconds,
        "captchaRequired": len(state.failures) >= CAPTCHA_AFTER_FAILURES,
    }


def clear_login_failures(scope: str, ip: str, account: str) -> None:
    attempt_store.pop(_attempt_key(scope, ip, account), None)


def create_captcha(scope: str) -> dict:
    cleanup_security_state()
    answer = "".join(random.choice("23456789ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(4))
    now = _now()
    key = token_urlsafe(24)
    captcha_store[key] = CaptchaChallenge(
        key=key,
        answer=answer,
        scope=scope,
        created_at=now,
        expires_at=now + CAPTCHA_TTL_SECONDS,
    )
    return {
        "captchaKey": key,
        "captchaSvg": render_captcha_svg(answer),
        "expiresIn": CAPTCHA_TTL_SECONDS,
    }


def verify_captcha(scope: str, captcha_key: str, captcha_code: str) -> None:
    cleanup_security_state()
    key = (captcha_key or "").strip()
    code = (captcha_code or "").strip().upper()
    challenge = captcha_store.get(key)
    if not challenge or challenge.scope != scope:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码已失效，请刷新后重试")
    if challenge.expires_at <= _now():
        captcha_store.pop(key, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码已过期，请刷新后重试")
    if code != challenge.answer:
        captcha_store.pop(key, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误，请重新输入")
    captcha_store.pop(key, None)


def build_auth_error_payload(message_text: str, scope: str, ip: str, account: str) -> dict:
    payload = mark_login_failure(scope, ip, account)
    detail = {
        "code": "AUTH_FAILED",
        "message": message_text,
        "captchaRequired": payload["captchaRequired"],
        "retryDelaySeconds": payload["delaySeconds"],
        "failureCount": payload["failureCount"],
    }
    if payload["captchaRequired"]:
        detail["captcha"] = create_captcha(scope)
    return detail


def render_captcha_svg(code: str) -> str:
    width = 132
    height = 44
    rng = random.Random(token_urlsafe(8))
    backgrounds = []
    for _ in range(8):
        x1 = rng.randint(0, width)
        x2 = rng.randint(0, width)
        y1 = rng.randint(0, height)
        y2 = rng.randint(0, height)
        backgrounds.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="rgba(148,163,184,0.38)" stroke-width="1"/>'
        )
    dots = []
    for _ in range(18):
        dots.append(
            f'<circle cx="{rng.randint(4, width - 4)}" cy="{rng.randint(4, height - 4)}" r="{rng.randint(1, 2)}" fill="rgba(71,85,105,0.28)"/>'
        )
    letters = []
    for index, char in enumerate(code):
        x = 18 + index * 26 + rng.randint(-2, 2)
        y = 29 + rng.randint(-3, 3)
        rotate = rng.randint(-20, 20)
        color = rng.choice(["#7C3AED", "#0F766E", "#B45309", "#1D4ED8", "#BE123C"])
        letters.append(
            f'<text x="{x}" y="{y}" font-size="24" font-family="Verdana, Arial, sans-serif" font-weight="700" '
            f'fill="{color}" transform="rotate({rotate} {x} {y})">{html.escape(char)}</text>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        '<rect width="100%" height="100%" rx="10" fill="#F8FAFC"/>'
        + "".join(backgrounds)
        + "".join(dots)
        + "".join(letters)
        + "</svg>"
    )
