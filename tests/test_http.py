from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from krex._http import KrexHttp
from krex.exceptions import (
    KrexAuthError,
    KrexBadRequestError,
    KrexConfigError,
    KrexConnectionError,
    KrexInvalidParameterError,
    KrexNotFoundError,
    KrexParseError,
    KrexQuotaExceededError,
    KrexServerError,
)


class FakeResponse:
    def __init__(self, payload: Any = None, *, status_code: int = 200, text: str = "") -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def json(self) -> Any:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeSession:
    def __init__(self, *responses: Any) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, *, params: dict[str, Any], timeout: float) -> Any:
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_get_ex_adds_key_and_normalizes_list() -> None:
    session = FakeSession(
        FakeResponse(
            {
                "code": "SUCCESS",
                "pageNo": "2",
                "numOfRows": "1",
                "count": "9",
                "list": {"a": "1"},
            }
        )
    )
    http = KrexHttp(ex_api_key="secret-key", retry_backoff=0, session=session)

    payload = http.get_ex("/openapi/test", {"pageNo": 2})

    assert session.calls[0]["url"] == "https://data.ex.co.kr/openapi/test"
    assert session.calls[0]["params"]["key"] == "secret-key"
    assert session.calls[0]["params"]["type"] == "json"
    assert payload.items == [{"a": "1"}]
    assert payload.page_no == 2
    assert payload.num_of_rows == 1
    assert payload.total_count == 9


def test_none_session_uses_real_session_factory_and_repr_hides_keys() -> None:
    http = KrexHttp(ex_api_key="secret-key", go_api_key="go-key", session=None)

    assert http.session is None
    assert "secret-key" not in repr(http)
    assert "go-key" not in repr(http)


def test_async_get_ex_awaits_async_session() -> None:
    class AsyncFakeSession(FakeSession):
        async def get(self, url: str, *, params: dict[str, Any], timeout: float) -> Any:
            return super().get(url, params=params, timeout=timeout)

    session = AsyncFakeSession(FakeResponse({"code": "SUCCESS", "list": [{"ok": "yes"}]}))
    http = KrexHttp(ex_api_key="secret-key", retry_backoff=0, session=session)

    payload = asyncio.run(http.aget_ex("/openapi/test"))

    assert payload.items == [{"ok": "yes"}]
    assert session.calls[0]["params"]["key"] == "secret-key"


def test_get_go_standard_uses_type_not_underscore_type() -> None:
    session = FakeSession(
        FakeResponse(
            {
                "response": {
                    "header": {"resultCode": "00", "resultMsg": "OK"},
                    "body": {"items": {"item": [{"name": "x"}]}, "totalCount": "1"},
                }
            }
        )
    )
    http = KrexHttp(go_api_key="go-key", retry_backoff=0, session=session)

    payload = http.get_go("https://api.example.test/rest", {"pageNo": 1}, standard=True)

    assert session.calls[0]["params"]["serviceKey"] == "go-key"
    assert session.calls[0]["params"]["type"] == "json"
    assert "_type" not in session.calls[0]["params"]
    assert payload.items == [{"name": "x"}]
    assert payload.total_count == 1


def test_api_keys_strip_copy_paste_whitespace() -> None:
    session = FakeSession(
        FakeResponse({"code": "SUCCESS", "list": [{"ok": "ex"}]}),
        FakeResponse(
            {
                "response": {
                    "header": {"resultCode": "00", "resultMsg": "OK"},
                    "body": {"items": {"item": [{"ok": "go"}]}},
                }
            }
        ),
    )
    http = KrexHttp(
        ex_api_key=" secret\r\n-key\t ",
        go_api_key=" go \n key ",
        retry_backoff=0,
        session=session,
    )

    assert http.get_ex("/openapi/test").items == [{"ok": "ex"}]
    assert http.get_go("https://api.example.test/rest").items == [{"ok": "go"}]

    assert session.calls[0]["params"]["key"] == "secret-key"
    assert session.calls[1]["params"]["serviceKey"] == "gokey"


def test_get_ex_accepts_endpoint_named_top_level_list() -> None:
    session = FakeSession(
        FakeResponse(
            {
                "code": "SUCCESS",
                "message": "인증키가 유효합니다.",
                "count": 1,
                "trafficIc": [{"unitCode": "101 "}],
            }
        )
    )
    http = KrexHttp(ex_api_key="secret-key", retry_backoff=0, session=session)

    payload = http.get_ex("/openapi/trafficapi/trafficIc")

    assert payload.items == [{"unitCode": "101 "}]
    assert payload.total_count == 1


def test_get_ex_preserves_zero_count() -> None:
    http = KrexHttp(
        ex_api_key="secret-key",
        retry_backoff=0,
        session=FakeSession(FakeResponse({"code": "SUCCESS", "count": 0, "list": []})),
    )

    payload = http.get_ex("/openapi/trafficapi/trafficRoute")

    assert payload.items == []
    assert payload.total_count == 0


@pytest.mark.parametrize(
    ("code", "exc_type"),
    [
        ("INVALID_KEY", KrexAuthError),
        ("EXCEEDED_LIMIT", KrexQuotaExceededError),
        ("INVALID_PARAMETER_VALUE", KrexInvalidParameterError),
        ("NO_DATA", KrexNotFoundError),
        ("SYSTEM_ERROR", KrexServerError),
    ],
)
def test_data_ex_error_codes_are_typed(code: str, exc_type: type[Exception]) -> None:
    http = KrexHttp(
        ex_api_key="key",
        retry_backoff=0,
        session=FakeSession(FakeResponse({"code": code})),
    )

    with pytest.raises(exc_type):
        http.get_ex("/openapi/test")


@pytest.mark.parametrize(
    ("code", "exc_type"),
    [
        ("03", KrexNotFoundError),
        ("10", KrexInvalidParameterError),
        ("11", KrexBadRequestError),
        ("22", KrexQuotaExceededError),
        ("30", KrexAuthError),
    ],
)
def test_data_go_error_codes_are_typed(code: str, exc_type: type[Exception]) -> None:
    payload = {"response": {"header": {"resultCode": code, "resultMsg": "ERR"}, "body": {}}}
    http = KrexHttp(go_api_key="key", retry_backoff=0, session=FakeSession(FakeResponse(payload)))

    with pytest.raises(exc_type):
        http.get_go("https://api.example.test")


def test_5xx_retries_then_succeeds() -> None:
    session = FakeSession(
        FakeResponse(status_code=500, text="down"),
        FakeResponse({"code": "SUCCESS", "list": [{"ok": "yes"}]}),
    )
    http = KrexHttp(ex_api_key="key", retry_backoff=0, max_retries=1, session=session)

    payload = http.get_ex("/openapi/test")

    assert len(session.calls) == 2
    assert payload.items == [{"ok": "yes"}]


def test_connection_error_retries_then_raises() -> None:
    session = FakeSession(httpx.ConnectError("offline"), httpx.ConnectError("offline"))
    http = KrexHttp(ex_api_key="secret-key", retry_backoff=0, max_retries=1, session=session)

    with pytest.raises(KrexConnectionError) as raised:
        http.get_ex("/openapi/test")

    assert raised.value.params is not None
    assert raised.value.params["key"] == "secr..."
    assert len(session.calls) == 2


def test_json_parse_failure_maps_to_parse_error() -> None:
    http = KrexHttp(
        ex_api_key="key",
        retry_backoff=0,
        session=FakeSession(FakeResponse(ValueError("bad json"))),
    )

    with pytest.raises(KrexParseError):
        http.get_ex("/openapi/test")


def test_missing_keys_raise_auth_errors() -> None:
    with pytest.raises(KrexAuthError):
        KrexHttp(session=FakeSession()).get_ex("/openapi/test")
    with pytest.raises(KrexAuthError):
        KrexHttp(session=FakeSession()).get_go("https://api.example.test")


@pytest.mark.parametrize(
    ("status", "exc_type"),
    [
        (400, KrexBadRequestError),
        (401, KrexAuthError),
        (403, KrexAuthError),
        (404, KrexBadRequestError),
        (429, KrexQuotaExceededError),
        (500, KrexServerError),
    ],
)
def test_http_status_codes_are_typed(status: int, exc_type: type[Exception]) -> None:
    http = KrexHttp(
        ex_api_key="key",
        retry_backoff=0,
        max_retries=0,
        session=FakeSession(FakeResponse(status_code=status, text="problem")),
    )

    with pytest.raises(exc_type):
        http.get_ex("/openapi/test")


def test_malformed_go_envelope_is_parse_error() -> None:
    http = KrexHttp(
        go_api_key="key",
        retry_backoff=0,
        session=FakeSession(FakeResponse({"response": {}})),
    )

    with pytest.raises(KrexParseError):
        http.get_go("https://api.example.test")


def test_load_httpx_missing_is_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "httpx":
            raise ModuleNotFoundError("httpx")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(KrexConfigError):
        KrexHttp(ex_api_key="key", session=FakeSession()).get_ex("/openapi/test")
