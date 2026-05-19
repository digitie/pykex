from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from krex import DebugRun, KrexClient, jsonable, redact_sensitive, save_fixture


class FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.headers = {"content-type": "application/json"}
        self.text = str(payload)

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeSession:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def get(self, url: str, *, params: dict[str, Any], timeout: float) -> FakeResponse:
        return FakeResponse(self.payload)


def ex_payload(items: Any) -> dict[str, Any]:
    return {"code": "SUCCESS", "pageNo": "1", "numOfRows": "1000", "count": "1", "list": items}


def test_debug_call_returns_request_response_and_typed_result() -> None:
    session = FakeSession(
        ex_payload(
            [
                {
                    "conzoneId": "0010CZE010",
                    "conzoneName": "서울-수원",
                    "routeNo": "0010",
                    "routeName": "경부고속도로",
                    "dirType": "0",
                    "speed": "87.5",
                    "tmFreeFlow": "100",
                    "congestionLevel": "1",
                    "updTime": "202604301405",
                }
            ]
        )
    )
    client = KrexClient(ex_api_key="secret-key", retry_backoff=0, session=session)

    run = client.debug_call("traffic.flow", route_no="0010")

    assert isinstance(run, DebugRun)
    assert run.error is None
    assert run.request["method"] == "GET"
    assert run.request["url"].endswith("/openapi/trafficapi/realFlow")
    assert run.request["query"]["key"] == "secr..."
    assert run.response["status_code"] == 200
    assert jsonable(run.processed)["items"][0]["speed"] == 87.5
    assert run.catalog is not None
    assert run.catalog["dataset_name"] == "한국도로공사_실시간 소통정보"
    assert run.catalog["service_key_url"] == "https://data.ex.co.kr/openapi/apikey/requestKey"
    assert any(line.startswith("service key URL:") for line in run.trace)


def test_async_debug_call_returns_result() -> None:
    client = KrexClient(
        ex_api_key="secret-key",
        retry_backoff=0,
        session=FakeSession(ex_payload([{"conzoneId": "A", "speed": "1"}])),
    )

    run = asyncio.run(client.adebug_call("traffic.flow", route_no="0010"))

    assert run.error is None
    assert run.request["query"]["key"] == "secr..."


def test_debug_call_keeps_validation_error_in_result() -> None:
    client = KrexClient(
        ex_api_key="secret-key",
        retry_backoff=0,
        session=FakeSession(ex_payload([])),
    )

    run = client.debug_call("traffic.flow", direction="bad")

    assert run.error is not None
    assert run.error["type"] == "KrexInvalidParameterError"
    assert run.request == {}
    assert "KrexInvalidParameterError" in run.trace[-1]


def test_save_fixture_redacts_sensitive_values_and_prevents_overwrite(tmp_path: Any) -> None:
    path = save_fixture(
        base_dir=tmp_path,
        function_name="traffic.flow",
        case_name="Secret Case!",
        description="민감정보 마스킹 확인",
        input_data={"api_key": "secret"},
        request_data={"query": {"key": "secret-key", "routeNo": "0010"}},
        response_data={"headers": {"Authorization": "Bearer secret"}, "body": {"ok": True}},
        parsed_result={"value": 1},
        processed_result={"updated_at": "ignored", "count": 1},
        assertion={"mode": "schema_only", "exclude_fields": [], "required_fields": []},
        library_version="0.1.0",
    )

    assert path.name == "secret-case.json"
    fixture = json.loads(path.read_text(encoding="utf-8"))
    assert fixture["input"]["api_key"] == "<REDACTED>"
    assert fixture["request"]["query"]["key"] == "<REDACTED>"
    assert fixture["response"]["headers"]["Authorization"] == "<REDACTED>"
    assert fixture["meta"]["library_version"] == "0.1.0"
    with pytest.raises(FileExistsError):
        save_fixture(
            base_dir=tmp_path,
            function_name="traffic.flow",
            case_name="Secret Case!",
            description="중복 저장",
            input_data={},
            request_data={},
            response_data={},
            parsed_result={},
            processed_result={},
        )


def test_redact_sensitive_recurses_through_lists() -> None:
    redacted = redact_sensitive({"items": [{"serviceKey": "secret"}, {"value": "ok"}]})

    assert redacted == {"items": [{"serviceKey": "<REDACTED>"}, {"value": "ok"}]}
