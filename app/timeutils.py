from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def current_time() -> datetime:
    return datetime.now(tz=SHANGHAI_TZ).replace(tzinfo=None)


def current_timestamp_ms() -> int:
    return int(datetime.now(tz=SHANGHAI_TZ).timestamp() * 1000)
