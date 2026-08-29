"""디버그 실행 결과와 fixture 저장 유틸리티."""

from __future__ import annotations

import json
import traceback as _traceback
import unicodedata
from collections.abc import Mapping
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from .exceptions import KrexError

SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "x_api_key",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "key",
        "servicekey",
        "service_key",
    }
)
DEFAULT_EXCLUDE_FIELDS = ("fetched_at", "request_id", "updated_at")


@dataclass(frozen=True, slots=True)
class DebugRun:
    """UI나 fixture writer가 사용할 수 있는 단일 디버그 실행 결과."""

    function: str
    input: dict[str, Any]
    request: dict[str, Any]
    response: dict[str, Any]
    parsed: Any
    processed: Any
    trace: list[str]
    catalog: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    def to_fixture_dict(
        self,
        *,
        name: str,
        description: str = "",
        assertion: dict[str, Any] | None = None,
        library_version: str | None = None,
        source: str = "debug_ui",
    ) -> dict[str, Any]:
        """현재 실행 결과를 fixture JSON에 가까운 dict로 변환합니다."""

        return build_fixture(
            name=name,
            function=self.function,
            description=description,
            input_data=self.input,
            request_data=self.request,
            response_data=self.response,
            parsed_result=self.parsed,
            processed_result=self.processed,
            catalog=self.catalog,
            assertion=assertion,
            library_version=library_version,
            source=source,
        )


def jsonable(obj: Any) -> Any:
    """Pydantic v2 모델과 날짜/enum을 JSON 저장 가능한 값으로 변환합니다."""

    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if is_dataclass(obj) and not isinstance(obj, type):
        return jsonable(asdict(obj))
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, Mapping):
        return {str(key): jsonable(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [jsonable(value) for value in obj]
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    return obj


def redact_sensitive(obj: Any) -> Any:
    """fixture 저장 전에 API 키와 토큰 계열 값을 재귀적으로 마스킹합니다."""

    if isinstance(obj, Mapping):
        result: dict[str, Any] = {}
        for key, value in obj.items():
            text_key = str(key)
            if _sensitive_key(text_key):
                result[text_key] = "<REDACTED>"
            else:
                result[text_key] = redact_sensitive(value)
        return result
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [redact_sensitive(value) for value in obj]
    return obj


def build_fixture(
    *,
    name: str,
    function: str,
    description: str,
    input_data: dict[str, Any],
    request_data: dict[str, Any],
    response_data: dict[str, Any],
    parsed_result: Any,
    processed_result: Any,
    catalog: dict[str, Any] | None = None,
    assertion: dict[str, Any] | None = None,
    library_version: str | None = None,
    source: str = "debug_ui",
) -> dict[str, Any]:
    """DebugRun 구성요소를 표준 fixture dict로 조립합니다."""

    safe_name = slugify(name)
    fixture = {
        "name": safe_name,
        "function": function,
        "description": description,
        "input": redact_sensitive(jsonable(input_data)),
        "request": redact_sensitive(jsonable(request_data)),
        "response": redact_sensitive(jsonable(response_data)),
        "parsed": jsonable(parsed_result),
        "processed": jsonable(processed_result),
        "assertion": assertion or {
            "mode": "snapshot",
            "exclude_fields": list(DEFAULT_EXCLUDE_FIELDS),
            "required_fields": [],
        },
        "meta": {
            "created_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
            "library_version": library_version,
            "source": source,
        },
    }
    if catalog is not None:
        fixture["catalog"] = redact_sensitive(jsonable(catalog))
    return fixture


def save_fixture(
    *,
    base_dir: str | Path,
    function_name: str,
    case_name: str,
    description: str,
    input_data: dict[str, Any],
    request_data: dict[str, Any],
    response_data: dict[str, Any],
    parsed_result: Any,
    processed_result: Any,
    catalog: dict[str, Any] | None = None,
    assertion: dict[str, Any] | None = None,
    library_version: str | None = None,
    overwrite: bool = False,
) -> Path:
    """디버그 실행 결과를 `tests/fixtures/{function}/{case}.json` 형태로 저장합니다."""

    safe_case_name = slugify(case_name)
    fixture_dir = Path(base_dir) / slugify(function_name)
    fixture_dir.mkdir(parents=True, exist_ok=True)
    fixture_path = fixture_dir / f"{safe_case_name}.json"
    if fixture_path.exists() and not overwrite:
        raise FileExistsError(f"Fixture already exists: {fixture_path}")

    fixture = build_fixture(
        name=safe_case_name,
        function=function_name,
        description=description,
        input_data=input_data,
        request_data=request_data,
        response_data=response_data,
        parsed_result=parsed_result,
        processed_result=processed_result,
        catalog=catalog,
        assertion=assertion,
        library_version=library_version,
    )
    with fixture_path.open("w", encoding="utf-8") as file:
        json.dump(fixture, file, ensure_ascii=False, indent=2)
        file.write("\n")
    return fixture_path


def slugify(value: str) -> str:
    """한글을 보존하면서 파일명으로 쓰기 좋은 slug를 만듭니다."""

    normalized = unicodedata.normalize("NFKC", value).strip().lower()
    chars: list[str] = []
    previous_sep = False
    for char in normalized:
        if char.isalnum():
            chars.append(char)
            previous_sep = False
        elif not previous_sep:
            chars.append("-")
            previous_sep = True
    slug = "".join(chars).strip("-")
    return slug or "case"


def exception_to_debug_error(exc: BaseException) -> dict[str, Any]:
    """예외를 DebugRun.error에 저장할 수 있는 구조화된 dict로 변환합니다.

    `type`/`message`/`traceback`은 모든 예외에 대해 채워지고, `KrexError`
    계열이면 `code`/`http_status`/`retry_after`/`url`/`params` 같은
    provider 세부 필드도 함께 채워집니다. 반환값은 fixture나 UI에 그대로
    노출되므로 `redact_sensitive()`를 거쳐 API 키 계열 값을 마스킹합니다.
    """

    payload: dict[str, Any] = {
        "type": type(exc).__name__,
        "message": str(exc),
        "traceback": "".join(
            _traceback.format_exception(type(exc), exc, exc.__traceback__)
        ),
    }
    if isinstance(exc, KrexError):
        payload.update(
            {
                "code": exc.code,
                "http_status": exc.http_status,
                "retry_after": exc.retry_after,
                "url": exc.url,
                "params": exc.params,
            }
        )
    return cast(dict[str, Any], redact_sensitive(payload))


def _sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return normalized in SENSITIVE_KEYS
