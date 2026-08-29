"""한국도로공사 API용 HTTP 헬퍼."""

from __future__ import annotations

import asyncio
import inspect
import threading
from collections.abc import Awaitable, Coroutine
from dataclasses import dataclass, field
from typing import Any, TypeVar, cast

from ._convert import normalize_items, to_int_or_none
from .exceptions import (
    KrexAuthError,
    KrexBadRequestError,
    KrexConfigError,
    KrexConnectionError,
    KrexError,
    KrexInvalidParameterError,
    KrexMissingParameterError,
    KrexNetworkError,
    KrexNotFoundError,
    KrexParseError,
    KrexQuotaExceededError,
    KrexServerError,
    KrexServiceUnavailableError,
    KrexTimeoutError,
)

T = TypeVar("T")

_MAX_BACKOFF_SECONDS = 30.0


def _load_httpx() -> Any:
    try:
        import httpx
    except ModuleNotFoundError as exc:
        raise KrexConfigError("httpx is required; install python-krex-api dependencies") from exc
    return httpx


def _run_sync(coroutine: Coroutine[Any, Any, T], *, timeout: float | None = None) -> T:
    """Run async transport code from the sync public API.

    Streamlit, notebooks, and GUI apps may already have a running event loop. In that case the
    coroutine is executed in a short-lived worker thread with its own loop so the sync API remains
    usable without nesting event loops.
    """

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)

    result: list[T] = []
    errors: list[BaseException] = []

    def runner() -> None:
        try:
            result.append(asyncio.run(coroutine))
        except BaseException as exc:  # noqa: BLE001 - propagate the original transport error.
            errors.append(exc)

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    if thread.is_alive():
        raise KrexTimeoutError("sync API call timed out waiting for background event loop thread")
    if errors:
        raise errors[0]
    return result[0]


async def _maybe_await(value: T | Awaitable[T]) -> T:
    if inspect.isawaitable(value):
        return await cast(Awaitable[T], value)
    return value


@dataclass(frozen=True, slots=True)
class NormalizedPayload:
    items: list[dict[str, Any]]
    page_no: int | None
    num_of_rows: int | None
    total_count: int | None
    raw: dict[str, Any]


@dataclass(slots=True)
class KrexHttp:
    ex_api_key: str | None = field(default=None, repr=False)
    go_api_key: str | None = field(default=None, repr=False)
    timeout: float = 10.0
    max_retries: int = 2
    retry_backoff: float = 0.5
    session: Any | None = field(default=None, repr=False)
    ex_base_url: str = "https://data.ex.co.kr"
    last_request: dict[str, Any] | None = field(default=None, init=False, repr=False)
    last_response: dict[str, Any] | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.ex_api_key = normalize_api_key(self.ex_api_key)
        self.go_api_key = normalize_api_key(self.go_api_key)

    def get_ex(self, path: str, params: dict[str, Any] | None = None) -> NormalizedPayload:
        return _run_sync(self.aget_ex(path, params), timeout=self._sync_join_timeout())

    async def aget_ex(self, path: str, params: dict[str, Any] | None = None) -> NormalizedPayload:
        key = normalize_api_key(self.ex_api_key)
        if not key:
            raise KrexAuthError("KEX_EX_API_KEY is not set and ex_api_key was not provided")
        query = dict(params) if params else {}
        query["key"] = key
        query["type"] = "json"
        url = f"{self.ex_base_url.rstrip('/')}/{path.lstrip('/')}"
        return await self._get(url, query, provider="ex")

    def get_go(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        *,
        standard: bool = False,
    ) -> NormalizedPayload:
        return _run_sync(
            self.aget_go(url, params, standard=standard), timeout=self._sync_join_timeout()
        )

    async def aget_go(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        *,
        standard: bool = False,
    ) -> NormalizedPayload:
        key = normalize_api_key(self.go_api_key)
        if not key:
            raise KrexAuthError("DATA_GO_KR_SERVICE_KEY is not set and go_api_key was not provided")
        query = dict(params) if params else {}
        query["serviceKey"] = key
        query["type" if standard else "_type"] = "json"
        return await self._get(url, query, provider="go")

    async def _get(self, url: str, params: dict[str, Any], *, provider: str) -> NormalizedPayload:
        httpx = _load_httpx()
        attempts = max(0, self.max_retries) + 1
        last_error: KrexNetworkError | None = None
        self.last_request = {"method": "GET", "url": url, "query": _mask_params(params)}
        self.last_response = None
        session = self.session
        close_after_request = False
        if session is None:
            session = httpx.AsyncClient(timeout=self.timeout, follow_redirects=True)
            close_after_request = True

        try:
            for attempt in range(attempts):
                try:
                    response = await self._request_get(session, url, params)
                except httpx.TimeoutException as exc:
                    last_error = KrexTimeoutError(str(exc), url=url, params=_mask_params(params))
                    if attempt < attempts - 1:
                        await self._sleep_before_retry(attempt)
                        continue
                    raise last_error from exc
                except httpx.NetworkError as exc:
                    last_error = KrexConnectionError(str(exc), url=url, params=_mask_params(params))
                    if attempt < attempts - 1:
                        await self._sleep_before_retry(attempt)
                        continue
                    raise last_error from exc
                except httpx.TooManyRedirects as exc:
                    raise KrexConnectionError(
                        str(exc), url=url, params=_mask_params(params)
                    ) from exc
                except httpx.HTTPError as exc:
                    last_error = KrexConnectionError(str(exc), url=url, params=_mask_params(params))
                    if attempt < attempts - 1:
                        await self._sleep_before_retry(attempt)
                        continue
                    raise last_error from exc
                except Exception as exc:  # noqa: BLE001 - normalize non-httpx session failures.
                    last_error = KrexNetworkError(str(exc), url=url, params=_mask_params(params))
                    if attempt < attempts - 1:
                        await self._sleep_before_retry(attempt)
                        continue
                    raise last_error from exc

                if 500 <= response.status_code < 600 and attempt < attempts - 1:
                    await self._sleep_before_retry(attempt)
                    continue

                return self._raise_for_response(response, provider=provider, params=params)
        finally:
            if close_after_request:
                await _close_session(session)

        if last_error is not None:
            raise last_error
        raise KrexServerError("request failed after retries", url=url, params=_mask_params(params))

    async def _request_get(self, session: Any, url: str, params: dict[str, Any]) -> Any:
        response = session.get(url, params=params, timeout=self.timeout)
        return await _maybe_await(response)

    async def _sleep_before_retry(self, attempt: int) -> None:
        if self.retry_backoff > 0:
            await asyncio.sleep(min(self.retry_backoff * (2**attempt), _MAX_BACKOFF_SECONDS))

    async def aclose(self) -> None:
        if self.session is not None:
            await _close_session(self.session)

    def close(self) -> None:
        _run_sync(self.aclose(), timeout=self.timeout)

    def _sync_join_timeout(self) -> float:
        return self.timeout * (max(0, self.max_retries) + 1) * 2

    async def __aenter__(self) -> KrexHttp:
        return self

    async def __aexit__(self, *_exc_info: Any) -> None:
        await self.aclose()

    def __enter__(self) -> KrexHttp:
        return self

    def __exit__(self, *_exc_info: Any) -> None:
        self.close()

    def _raise_for_response(
        self,
        response: Any,
        *,
        provider: str,
        params: dict[str, Any],
    ) -> NormalizedPayload:
        status = int(response.status_code)
        masked_params = _mask_params(params)
        headers = _response_headers(response)
        secrets = (self.ex_api_key, self.go_api_key)
        body_preview = _redact_secrets(response.text[:200], secrets)
        if status in (401, 403):
            self.last_response = _debug_response(status, headers, body_preview)
            raise KrexAuthError(
                f"HTTP {status}: {body_preview}",
                http_status=status,
                params=masked_params,
            )
        if status == 400:
            self.last_response = _debug_response(status, headers, body_preview)
            raise KrexBadRequestError(body_preview, http_status=status, params=masked_params)
        if status == 404:
            self.last_response = _debug_response(status, headers, body_preview)
            raise KrexBadRequestError(
                "endpoint not found",
                http_status=status,
                params=masked_params,
            )
        if status == 429:
            self.last_response = _debug_response(status, headers, body_preview)
            raise KrexQuotaExceededError(
                body_preview,
                http_status=status,
                params=masked_params,
            )
        if 500 <= status < 600:
            self.last_response = _debug_response(status, headers, body_preview)
            raise KrexServerError(
                f"HTTP {status}: {body_preview}",
                http_status=status,
                params=masked_params,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            self.last_response = _debug_response(status, headers, body_preview)
            raise KrexParseError(
                f"JSON parse failure: {exc}",
                http_status=status,
                params=masked_params,
            ) from exc
        self.last_response = _debug_response(status, headers, _redact_payload(payload, secrets))
        if not isinstance(payload, dict):
            raise KrexParseError(
                "response JSON must be an object",
                response=payload,
                params=masked_params,
            )

        if provider == "go" or "response" in payload:
            return _normalize_go_payload(payload, params=masked_params)
        return _normalize_ex_payload(payload, params=masked_params)


def _normalize_ex_payload(payload: dict[str, Any], *, params: dict[str, Any]) -> NormalizedPayload:
    if "code" in payload:
        code = str(payload.get("code"))
    elif "resultCode" in payload:
        code = str(payload.get("resultCode"))
    else:
        code = "SUCCESS"
    message = str(payload.get("message") or payload.get("resultMsg") or "")
    if code not in {"SUCCESS", "INFO-000", "00"}:
        _raise_ex_code(code, message, payload, params)

    raw_items = _ex_items(payload)
    try:
        items = normalize_items(raw_items, "items")
    except TypeError as exc:
        raise KrexParseError(str(exc), response=payload, params=params) from exc
    try:
        page_no = to_int_or_none(payload.get("pageNo"))
        num_of_rows = to_int_or_none(payload.get("numOfRows"))
        total_count = to_int_or_none(_first_present(payload, "count", "totalCount"))
    except ValueError as exc:
        raise KrexParseError(str(exc), response=payload, params=params) from exc
    return NormalizedPayload(
        items=items,
        page_no=page_no,
        num_of_rows=num_of_rows,
        total_count=total_count,
        raw=payload,
    )


def _normalize_go_payload(payload: dict[str, Any], *, params: dict[str, Any]) -> NormalizedPayload:
    try:
        response = payload["response"]
        header = response["header"]
        body = response.get("body", {})
    except (KeyError, TypeError) as exc:
        raise KrexParseError(
            "data.go.kr response did not contain response.header",
            response=payload,
        ) from exc
    if not isinstance(header, dict) or not isinstance(body, dict):
        raise KrexParseError("data.go.kr header/body must be objects", response=payload)

    code = str(header.get("resultCode", ""))
    message = str(header.get("resultMsg", ""))
    if code != "00":
        _raise_go_code(code, message, payload, params)

    raw_items = body.get("items", [])
    if isinstance(raw_items, dict) and "item" in raw_items:
        raw_items = raw_items["item"]
    try:
        items = normalize_items(raw_items, "response.body.items")
    except TypeError as exc:
        raise KrexParseError(str(exc), response=payload, params=params) from exc
    try:
        page_no = to_int_or_none(body.get("pageNo"))
        num_of_rows = to_int_or_none(body.get("numOfRows"))
        total_count = to_int_or_none(body.get("totalCount"))
    except ValueError as exc:
        raise KrexParseError(str(exc), response=payload, params=params) from exc
    return NormalizedPayload(
        items=items,
        page_no=page_no,
        num_of_rows=num_of_rows,
        total_count=total_count,
        raw=payload,
    )


def _ex_items(payload: dict[str, Any]) -> Any:
    for key in ("list", "List", "data", "items", "item", "realTimeSMSList"):
        value = payload.get(key)
        if value is not None:
            return value
    metadata_keys = {"code", "message", "count", "pageNo", "numOfRows", "pageSize"}
    candidates = [
        value
        for key, value in payload.items()
        if key not in metadata_keys and isinstance(value, list)
    ]
    if len(candidates) > 1:
        raise KrexParseError(
            "ambiguous EX payload: multiple top-level list fields", response=payload
        )
    return candidates[0] if candidates else []


def _first_present(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _raise_ex_code(
    code: str,
    message: str,
    payload: dict[str, Any],
    params: dict[str, Any],
) -> None:
    text = f"data.ex.co.kr returned {code}: {message}"
    kwargs: dict[str, Any] = {"code": code, "response": payload, "params": params}
    if code in {"INVALID_KEY", "EXPIRED_KEY", "NO_REGISTERED_KEY"}:
        raise KrexAuthError(text, **kwargs)
    if code == "EXCEEDED_LIMIT":
        raise KrexQuotaExceededError(text, **kwargs)
    if code == "INVALID_REQUEST_PARAMETER":
        raise KrexMissingParameterError(text, **kwargs)
    if code == "INVALID_PARAMETER_VALUE":
        raise KrexInvalidParameterError(text, **kwargs)
    if code == "NO_DATA":
        raise KrexNotFoundError(text, **kwargs)
    if code in {"SERVICE_TIMEOUT", "SERVICE_UNAVAILABLE"}:
        raise KrexServiceUnavailableError(text, **kwargs)
    if code == "SYSTEM_ERROR":
        raise KrexServerError(text, **kwargs)
    raise KrexError(text, **kwargs)


def _raise_go_code(
    code: str,
    message: str,
    payload: dict[str, Any],
    params: dict[str, Any],
) -> None:
    text = f"data.go.kr returned {code}: {message}"
    kwargs: dict[str, Any] = {"code": code, "response": payload, "params": params}
    if code in {"01", "02", "04"}:
        raise KrexServerError(text, **kwargs)
    if code == "03":
        raise KrexNotFoundError(text, **kwargs)
    if code == "05":
        raise KrexServiceUnavailableError(text, **kwargs)
    if code == "10":
        raise KrexInvalidParameterError(text, **kwargs)
    if code == "11":
        raise KrexMissingParameterError(text, **kwargs)
    if code == "12":
        raise KrexBadRequestError(text, **kwargs)
    if code in {"20", "21", "30", "31", "32", "33"}:
        raise KrexAuthError(text, **kwargs)
    if code == "22":
        raise KrexQuotaExceededError(text, **kwargs)
    raise KrexError(text, **kwargs)


def _mask_value(value: str) -> str:
    return value[:4] + "..." if len(value) > 4 else "***"


def _mask_params(params: dict[str, Any]) -> dict[str, Any]:
    masked = dict(params)
    for key in ("key", "serviceKey"):
        if key in masked:
            masked[key] = _mask_value(str(masked[key]))
    return masked


def _redact_secrets(text: str, secrets: tuple[str | None, ...]) -> str:
    for secret in secrets:
        if secret and len(secret) > 4:
            text = text.replace(secret, _mask_value(secret))
    return text


def _redact_payload(value: Any, secrets: tuple[str | None, ...]) -> Any:
    if isinstance(value, dict):
        return {key: _redact_payload(item, secrets) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_payload(item, secrets) for item in value]
    if isinstance(value, str) and value in secrets:
        return _mask_value(value)
    return value


def normalize_api_key(value: str | None) -> str | None:
    """복사/붙여넣기 과정에서 섞인 모든 공백 문자를 제거합니다."""

    if value is None:
        return None
    normalized = "".join(str(value).split())
    return normalized or None


def _response_headers(response: Any) -> dict[str, str]:
    headers = getattr(response, "headers", {})
    if not headers:
        return {}
    return {str(key): str(value) for key, value in dict(headers).items()}


def _debug_response(status_code: int, headers: dict[str, str], body: Any) -> dict[str, Any]:
    return {"status_code": status_code, "headers": headers, "body": body}


async def _close_session(session: Any) -> None:
    aclose = getattr(session, "aclose", None)
    if callable(aclose):
        await _maybe_await(aclose())
        return
    close = getattr(session, "close", None)
    if callable(close):
        await _maybe_await(close())
