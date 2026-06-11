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


def _load_httpx() -> Any:
    try:
        import httpx
    except ModuleNotFoundError as exc:
        raise KrexConfigError("httpx is required; install python-krex-api dependencies") from exc
    return httpx


def _run_sync(coroutine: Coroutine[Any, Any, T]) -> T:
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
    thread.join()
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
        return _run_sync(self.aget_ex(path, params))

    async def aget_ex(self, path: str, params: dict[str, Any] | None = None) -> NormalizedPayload:
        key = normalize_api_key(self.ex_api_key)
        if not key:
            raise KrexAuthError("KEX_EX_API_KEY is not set and ex_api_key was not provided")
        query = {"key": key, "type": "json"}
        if params:
            query.update(params)
        url = f"{self.ex_base_url.rstrip('/')}/{path.lstrip('/')}"
        return await self._get(url, query, provider="ex")

    def get_go(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        *,
        standard: bool = False,
    ) -> NormalizedPayload:
        return _run_sync(self.aget_go(url, params, standard=standard))

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
        query = {"serviceKey": key}
        query["type" if standard else "_type"] = "json"
        if params:
            query.update(params)
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
                except httpx.HTTPError as exc:
                    last_error = KrexConnectionError(str(exc), url=url, params=_mask_params(params))
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
            await asyncio.sleep(self.retry_backoff * (2**attempt))

    async def aclose(self) -> None:
        if self.session is not None:
            await _close_session(self.session)

    def close(self) -> None:
        _run_sync(self.aclose())

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
        if status in (401, 403):
            self.last_response = _debug_response(status, headers, response.text[:200])
            raise KrexAuthError(
                f"HTTP {status}: {response.text[:200]}",
                http_status=status,
                params=masked_params,
            )
        if status == 400:
            self.last_response = _debug_response(status, headers, response.text[:200])
            raise KrexBadRequestError(response.text[:200], http_status=status, params=masked_params)
        if status == 404:
            self.last_response = _debug_response(status, headers, response.text[:200])
            raise KrexBadRequestError(
                "endpoint not found",
                http_status=status,
                params=masked_params,
            )
        if status == 429:
            self.last_response = _debug_response(status, headers, response.text[:200])
            raise KrexQuotaExceededError(
                response.text[:200],
                http_status=status,
                params=masked_params,
            )
        if 500 <= status < 600:
            self.last_response = _debug_response(status, headers, response.text[:200])
            raise KrexServerError(
                f"HTTP {status}: {response.text[:200]}",
                http_status=status,
                params=masked_params,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            self.last_response = _debug_response(status, headers, response.text[:200])
            raise KrexParseError(
                f"JSON parse failure: {exc}",
                http_status=status,
                params=masked_params,
            ) from exc
        self.last_response = _debug_response(status, headers, payload)
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
    code = str(payload.get("code") or payload.get("resultCode") or "SUCCESS")
    message = str(payload.get("message") or payload.get("resultMsg") or "")
    if code not in {"SUCCESS", "INFO-000", "00"}:
        _raise_ex_code(code, message, payload, params)

    raw_items = _ex_items(payload)
    try:
        items = normalize_items(raw_items, "items")
    except TypeError as exc:
        raise KrexParseError(str(exc), response=payload, params=params) from exc
    return NormalizedPayload(
        items=items,
        page_no=to_int_or_none(payload.get("pageNo")),
        num_of_rows=to_int_or_none(payload.get("numOfRows")),
        total_count=to_int_or_none(_first_present(payload, "count", "totalCount")),
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
    return NormalizedPayload(
        items=items,
        page_no=to_int_or_none(body.get("pageNo")),
        num_of_rows=to_int_or_none(body.get("numOfRows")),
        total_count=to_int_or_none(body.get("totalCount")),
        raw=payload,
    )


def _ex_items(payload: dict[str, Any]) -> Any:
    for key in ("list", "List", "data", "items", "item", "realTimeSMSList"):
        if key in payload:
            return payload[key]
    for key, value in payload.items():
        metadata_keys = {"code", "message", "count", "pageNo", "numOfRows", "pageSize"}
        if key not in metadata_keys and isinstance(value, list):
            return value
    return []


def _first_present(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
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


def _mask_params(params: dict[str, Any]) -> dict[str, Any]:
    masked = dict(params)
    for key in ("key", "serviceKey"):
        if key in masked:
            value = str(masked[key])
            masked[key] = value[:4] + "..." if len(value) > 4 else "***"
    return masked


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
