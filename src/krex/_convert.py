"""API 응답 경계에서 쓰는 작은 변환 헬퍼."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any


def strip_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def to_int_or_none(value: Any) -> int | None:
    text = strip_or_none(value)
    if text is None:
        return None
    if text.upper() in {"X", "-", "N/A", "NA"}:
        return None
    normalized = text.replace(",", "")
    match = re.fullmatch(r"([-+]?\d+)(?:\D+)?", normalized)
    if match is None:
        raise ValueError(f"expected integer-compatible value, got {value!r}")
    return int(match.group(1))


def to_float_or_none(value: Any) -> float | None:
    text = strip_or_none(value)
    if text is None:
        return None
    if text.upper() in {"X", "-", "N/A", "NA"}:
        return None
    normalized = text.replace(",", "")
    match = re.fullmatch(r"([-+]?\d+(?:\.\d+)?)(?:\D+)?", normalized)
    if match is None:
        raise ValueError(f"expected float-compatible value, got {value!r}")
    return float(match.group(1))


def to_date_or_none(value: Any) -> date | None:
    text = strip_or_none(value)
    if text is None:
        return None
    if len(text) == 8 and text.isdigit():
        return date(int(text[:4]), int(text[4:6]), int(text[6:8]))
    return date.fromisoformat(text)


def to_bool_yn(value: Any) -> bool | None:
    text = strip_or_none(value)
    if text is None:
        return None
    upper = text.upper()
    if upper in {"Y", "YES", "TRUE", "1", "O"}:
        return True
    if upper in {"N", "NO", "FALSE", "0", "X"}:
        return False
    raise ValueError(f"expected Y/N or O/X value, got {value!r}")


def normalize_items(value: Any, field: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return value
    raise TypeError(f"{field} must be an object or list of objects")


def parse_datetime_text(value: Any) -> datetime | None:
    text = strip_or_none(value)
    if text is None:
        return None
    if text.isdigit():
        if len(text) == 14:
            return datetime.strptime(text, "%Y%m%d%H%M%S")
        if len(text) == 12:
            return datetime.strptime(text, "%Y%m%d%H%M")
    for fmt in ("%Y%m%d%H%M%S", "%Y%m%d%H%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None
