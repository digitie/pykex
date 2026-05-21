"""Streamlit 기반 KREX API 디버그 카탈로그 뷰어."""
# ruff: noqa: E402,I001

from __future__ import annotations

import inspect
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
for module_name, module in list(sys.modules.items()):
    if module_name != "krex" and not module_name.startswith("krex."):
        continue
    module_file = getattr(module, "__file__", None)
    if module_file is not None and not Path(module_file).resolve().is_relative_to(SRC):
        del sys.modules[module_name]

try:
    import streamlit as st
except ModuleNotFoundError as exc:  # pragma: no cover - 선택 실행 도구
    raise SystemExit('Streamlit UI를 쓰려면 `pip install -e ".[debug-ui]"`를 실행하세요.') from exc

from krex import ApiCatalogItem, KrexClient, get_api_catalog, get_api_catalog_item, jsonable
from krex._env import load_local_env
from krex._http import normalize_api_key


@dataclass(frozen=True)
class ParameterSpec:
    """디버그 UI에서 요청 파라미터 입력 폼을 만들기 위한 최소 명세."""

    name: str
    required: bool
    label: str
    placeholder: str = ""
    help: str = ""
    default: Any = ""
    value_type: type = str


DEFAULT_PARAMS: dict[str, dict[str, Any]] = {
    "traffic.by_ic": {
        "ex_div_code": "00",
        "unit_code": "101",
        "in_out": "0",
        "time_unit": "1",
        "tcs_type": "2",
        "car_type": "1",
        "num_of_rows": 10,
        "page_no": 1,
    },
    "traffic.by_route": {
        "route_no": "0010",
        "time_unit": "1",
        "num_of_rows": 10,
        "page_no": 1,
    },
    "traffic.flow": {"route_no": "0010", "num_of_rows": 10, "page_no": 1},
    "traffic.incident": {"route_no": "0010", "num_of_rows": 10, "page_no": 1},
    "traffic.avc_raw": {"vds_id": "V001", "std_date": "20260430"},
    "tollfee.between_tollgates": {
        "start_unit_code": "101",
        "end_unit_code": "105",
        "car_type": "1",
        "num_of_rows": 10,
        "page_no": 1,
    },
    "tollfee.tollgate_list": {"num_of_rows": 10, "page_no": 1},
    "restarea.route_facilities": {"num_of_rows": 10, "page_no": 1},
    "restarea.list_all": {"num_of_rows": 10, "page_no": 1},
    "restarea.weather": {"sdate": "20210507", "std_hour": 12},
    "restarea.latest_weather": {"lookback_hours": 48},
    "restarea.fuel_prices": {"num_of_rows": 10, "page_no": 1},
    "restarea.convenience_facilities": {"num_of_rows": 10, "page_no": 1},
}


def main() -> None:
    st.set_page_config(page_title="KREX API Debug", layout="wide")
    st.title("KREX API Debug")

    source = st.sidebar.selectbox("Data source", ["all", "data.ex.co.kr", "data.go.kr"])
    catalog_rows = _catalog_rows(source)
    if not catalog_rows:
        st.warning("선택한 source에 표시할 API가 없습니다.")
        return

    labels = [_api_label(row) for row in catalog_rows]
    selected_label = st.sidebar.selectbox("API", labels)
    selected = catalog_rows[labels.index(selected_label)]

    st.sidebar.caption("API full name")
    st.sidebar.write(_api_full_name(selected))
    st.sidebar.caption(selected.description)

    env_names = _env_names_for_provider(selected.provider)
    env_sources = _env_key_sources(selected.provider)
    environment = "manual"
    if env_sources:
        st.sidebar.subheader("Environment")
        environment = st.sidebar.selectbox("Environment", ["env", "manual"])
        if environment == "env":
            source_info = env_sources[0]
            st.sidebar.caption(
                f"{source_info['name']} 값을 사용합니다. Source: {source_info['source']}"
            )

    st.sidebar.subheader("Auth")
    api_key = ""
    if selected.provider == "local":
        st.sidebar.caption("로컬 참조 항목은 인증키를 사용하지 않습니다.")
    elif environment == "manual":
        api_key = st.sidebar.text_input(
            _credential_param(selected.provider),
            value="",
            type="password",
            placeholder="직접 입력",
            help=f"사용 가능한 env 이름: {', '.join(env_names)}",
        )
    _service_key_links(selected)

    timeout = st.sidebar.number_input(
        "Timeout",
        min_value=1.0,
        max_value=60.0,
        value=10.0,
        step=1.0,
        help="API 요청 timeout seconds입니다.",
    )
    fixture_base_dir = _fixture_base_dir_sidebar()

    tabs = st.tabs(
        [
            "Raw Response",
            "Pydantic Model",
            "Processed Result",
            "Validation Errors",
            "Debug Trace",
            "Fixture / Testcase",
        ]
    )

    with tabs[0]:
        _raw_response_tab(selected, api_key, environment=environment, timeout=float(timeout))
    with tabs[1]:
        _pydantic_model_tab(selected)
    with tabs[2]:
        _processed_result_tab(selected)
    with tabs[3]:
        _validation_errors_tab(selected)
    with tabs[4]:
        _debug_trace_tab(catalog_rows, selected, env_names)
    with tabs[5]:
        _fixture_tab(selected, fixture_base_dir)


def _catalog_rows(source: str) -> list[ApiCatalogItem]:
    rows = [item for item in get_api_catalog() if item.provider != "local"]
    if source == "all":
        return rows
    return [item for item in rows if item.provider == source]


def _api_label(item: ApiCatalogItem) -> str:
    return f"{item.dataset_name} / {item.function}"


def _api_full_name(item: ApiCatalogItem) -> str:
    endpoint = item.endpoint or "-"
    return f"{item.dataset_name} / {item.function} / {endpoint}"


def _raw_response_tab(
    selected: ApiCatalogItem,
    api_key: str,
    *,
    environment: str,
    timeout: float,
) -> None:
    st.subheader(selected.dataset_name)
    st.caption(f"{selected.provider} / {selected.function} / {selected.endpoint or '-'}")

    try:
        submitted, params, extra_params, missing = _request_form(selected)
    except ValueError as exc:
        st.error(str(exc))
        return

    preview = {**params, **extra_params}
    st.subheader("Request params preview")
    st.json(preview)

    if not submitted:
        return
    if missing:
        st.error("필수 파라미터를 입력하세요: " + ", ".join(missing))
        return

    try:
        client = _client_for_run(selected, api_key, environment=environment, timeout=timeout)
        run = client.debug_call(selected.function, **preview)
    except Exception as exc:  # pragma: no cover - UI 표시
        st.error(str(exc))
        return

    _store_run(selected, run)
    if run.error:
        st.error(run.error["message"])
    st.json(jsonable(run.response))


def _request_form(
    selected: ApiCatalogItem,
) -> tuple[bool, dict[str, Any], dict[str, Any], list[str]]:
    specs = _parameter_specs(selected)
    required_specs = [spec for spec in specs if spec.required]
    optional_specs = [spec for spec in specs if not spec.required]
    key_prefix = f"{selected.provider}:{selected.function}"

    with st.form(f"request-form:{key_prefix}"):
        st.subheader("Required parameters")
        if required_specs:
            required_values = _render_param_grid(required_specs, key_prefix=key_prefix)
        else:
            st.caption("이 API에 대해 로컬에 정리된 필수 파라미터 명세가 없습니다.")
            required_values = {}

        st.subheader("Optional parameters")
        optional_values = _render_param_grid(optional_specs, key_prefix=key_prefix)

        extra_text = st.text_area(
            "Extra params JSON",
            value="{}",
            height=110,
            help="폼에 없는 provider 파라미터를 JSON object로 추가합니다.",
            key=f"{key_prefix}:extra",
        )
        submitted = st.form_submit_button("Run selected API")

    params = {**required_values, **optional_values}
    missing = [spec.name for spec in required_specs if _is_blank(params.get(spec.name))]
    extra_params = _parse_extra_params(extra_text)
    clean_params = {key: value for key, value in params.items() if not _is_blank(value)}
    return submitted, clean_params, extra_params, missing


def _parameter_specs(selected: ApiCatalogItem) -> tuple[ParameterSpec, ...]:
    method = _resolve_client_method(selected.function)
    if method is None:
        return ()

    defaults = DEFAULT_PARAMS.get(selected.function, {})
    specs: list[ParameterSpec] = []
    signature = inspect.signature(method)
    for name, parameter in signature.parameters.items():
        if name == "self" or parameter.kind == inspect.Parameter.VAR_KEYWORD:
            continue
        if name == "when":
            continue
        required = parameter.default is inspect.Parameter.empty
        fallback_default = "" if required or parameter.default is None else parameter.default
        default = defaults.get(name, fallback_default)
        specs.append(
            ParameterSpec(
                name=name,
                required=required,
                label=_param_label(name),
                default=default,
                value_type=_value_type(name, default),
            )
        )
    for name, default in defaults.items():
        if any(spec.name == name for spec in specs):
            continue
        specs.append(
            ParameterSpec(
                name=name,
                required=False,
                label=_param_label(name),
                default=default,
                value_type=_value_type(name, default),
            )
        )
    return tuple(specs)


def _resolve_client_method(function: str) -> Any | None:
    client = KrexClient(ex_api_key="unused", go_api_key="unused")
    parts = function.split(".")
    if len(parts) != 2:
        return None
    namespace = getattr(client, parts[0], None)
    return getattr(namespace, parts[1], None)


def _render_param_grid(specs: list[ParameterSpec], *, key_prefix: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for index in range(0, len(specs), 2):
        columns = st.columns(2)
        for column, spec in zip(columns, specs[index : index + 2], strict=False):
            with column:
                widget_key = f"{key_prefix}:param:{spec.name}"
                if spec.value_type is int:
                    values[spec.name] = st.number_input(
                        spec.label,
                        min_value=0 if spec.name != "page_no" else 1,
                        value=int(spec.default or 0),
                        step=1,
                        help=spec.help or None,
                        key=widget_key,
                    )
                else:
                    values[spec.name] = st.text_input(
                        spec.label,
                        value="" if spec.default is None else str(spec.default),
                        placeholder=spec.placeholder,
                        help=spec.help or None,
                        key=widget_key,
                    )
    return values


def _parse_extra_params(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Extra params JSON is invalid: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Extra params JSON must be an object")
    blocked = {"key", "serviceKey", "ServiceKey", "pageNo", "numOfRows", "type", "_type"}
    return {key: value for key, value in payload.items() if key not in blocked}


def _client_for_run(
    selected: ApiCatalogItem,
    api_key: str,
    *,
    environment: str,
    timeout: float,
) -> KrexClient:
    if environment == "env":
        return KrexClient(timeout=timeout, retry_backoff=0)
    normalized = normalize_api_key(api_key)
    if selected.provider == "data.ex.co.kr":
        return KrexClient(ex_api_key=normalized, timeout=timeout, retry_backoff=0)
    if selected.provider == "data.go.kr":
        return KrexClient(go_api_key=normalized, timeout=timeout, retry_backoff=0)
    return KrexClient(timeout=timeout, retry_backoff=0)


def _pydantic_model_tab(selected: ApiCatalogItem) -> None:
    run = _current_run(selected)
    if run is None:
        st.info("Raw Response 탭에서 선택한 API를 실행하면 여기에서 Pydantic 모델을 확인합니다.")
        return
    if run.error:
        st.warning("모델 파싱 중 확인할 내용이 있습니다. Validation Errors 탭을 확인하세요.")
    if run.parsed is None:
        st.info("표시할 Pydantic 모델이 없습니다.")
        return
    st.caption(selected.return_type)
    st.json(jsonable(run.parsed))


def _processed_result_tab(selected: ApiCatalogItem) -> None:
    run = _current_run(selected)
    if run is None:
        st.info("Raw Response 탭에서 API를 실행하면 처리된 row preview를 표시합니다.")
        return
    processed = jsonable(run.processed)
    rows = processed.get("items") if isinstance(processed, dict) else None
    if isinstance(rows, list) and rows:
        st.dataframe(rows, width="stretch", hide_index=True)
        return
    if processed:
        st.json(processed)
        return
    st.info("표시할 처리 결과가 없습니다.")


def _validation_errors_tab(selected: ApiCatalogItem) -> None:
    run = _current_run(selected)
    if run is None:
        st.info("아직 실행된 API가 없습니다.")
        return
    if not run.error:
        st.success("현재 실행 결과에서 validation error가 없습니다.")
        return
    st.error(run.error["message"])
    st.json(run.error)


def _debug_trace_tab(
    rows: list[ApiCatalogItem],
    selected: ApiCatalogItem,
    env_names: tuple[str, ...],
) -> None:
    st.subheader("Catalog")
    st.dataframe(
        [row.model_dump(mode="json") for row in rows],
        width="stretch",
        hide_index=True,
    )

    st.subheader("Selected API")
    selected_catalog = get_api_catalog_item(selected.function) or selected
    st.json(selected_catalog.model_dump(mode="json"))
    if selected_catalog.service_key_url:
        st.link_button(
            f"{_credential_param(selected.provider)} 발급/확인",
            selected_catalog.service_key_url,
        )
    st.caption(f"credential env: {', '.join(env_names)}")

    run = _current_run(selected)
    if run is None:
        return
    st.divider()
    st.subheader("Trace")
    st.code("\n".join(run.trace), language="text")
    if run.catalog:
        st.subheader("DebugRun.catalog")
        st.dataframe([run.catalog], width="stretch", hide_index=True)


def _fixture_tab(selected: ApiCatalogItem, fixture_base_dir: str) -> None:
    run = _current_run(selected)
    st.caption("Fixture base dir")
    st.code(fixture_base_dir, language=None)
    if run is None:
        st.info("Raw Response 탭에서 API를 실행하면 fixture 초안을 확인합니다.")
        return
    st.json(run.to_fixture_dict(name=f"{selected.function}-debug"))


def _store_run(selected: ApiCatalogItem, run: Any) -> None:
    st.session_state["last_run"] = {
        "selection_key": _selection_key(selected),
        "run": run,
    }


def _current_run(selected: ApiCatalogItem) -> Any | None:
    payload = st.session_state.get("last_run")
    if not isinstance(payload, dict):
        return None
    if payload.get("selection_key") != _selection_key(selected):
        return None
    return payload.get("run")


def _selection_key(selected: ApiCatalogItem) -> str:
    return f"{selected.provider}:{selected.function}"


def _service_key_links(selected: ApiCatalogItem) -> None:
    st.sidebar.caption("Service key links")
    if selected.service_key_url:
        st.sidebar.link_button(
            f"{_credential_param(selected.provider)} 발급/확인",
            selected.service_key_url,
        )
    if selected.provider == "data.ex.co.kr":
        st.sidebar.link_button("data.ex.co.kr 포털", "https://data.ex.co.kr")
    elif selected.provider == "data.go.kr":
        st.sidebar.link_button("data.go.kr 카탈로그", selected.service_key_url or "https://www.data.go.kr")


def _env_key_sources(provider: str) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    for name in _env_names_for_provider(provider):
        value = normalize_api_key(_process_env_value(name))
        if value:
            sources.append({"name": name, "source": "process env"})
            return sources

    local_env = load_local_env()
    for name in _env_names_for_provider(provider):
        value = normalize_api_key(local_env.get(name))
        if value:
            sources.append({"name": name, "source": ".env"})
            return sources
    return sources


def _process_env_value(name: str) -> str | None:
    import os

    return os.getenv(name)


def _fixture_base_dir_sidebar() -> str:
    st.sidebar.subheader("Fixtures")
    candidates = _fixture_dir_candidates()
    options = [str(path) for path in candidates]
    custom_label = "Custom..."
    selected = st.sidebar.selectbox("Fixture base dir", [*options, custom_label])
    if selected == custom_label:
        selected = st.sidebar.text_input(
            "Custom fixture base dir",
            value=str((ROOT / "tests" / "fixtures").resolve()),
        )
    st.sidebar.caption(selected)
    return selected


def _fixture_dir_candidates() -> list[Path]:
    preferred = [
        ROOT / "tests" / "fixtures",
        ROOT / "tests",
        ROOT / "examples",
        ROOT,
    ]
    candidates: list[Path] = []
    for path in preferred:
        resolved = path.resolve()
        if resolved not in candidates:
            candidates.append(resolved)
    return candidates


def _env_names_for_provider(provider: str) -> tuple[str, ...]:
    if provider == "data.ex.co.kr":
        return ("KEX_EX_API_KEY",)
    if provider == "data.go.kr":
        return ("DATA_GO_KR_SERVICE_KEY",)
    return ()


def _credential_param(provider: str) -> str:
    if provider == "data.ex.co.kr":
        return "key"
    if provider == "data.go.kr":
        return "serviceKey"
    return "credential"


def _param_label(name: str) -> str:
    labels = {
        "page_no": "page_no",
        "num_of_rows": "num_of_rows",
        "std_hour": "std_hour (HH)",
        "sdate": "sdate (YYYYMMDD)",
        "std_date": "std_date (YYYYMMDD)",
    }
    return labels.get(name, name)


def _value_type(name: str, default: Any) -> type:
    if isinstance(default, int):
        return int
    if name in {"num_of_rows", "page_no", "lookback_hours", "std_hour"}:
        return int
    return str


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


if __name__ == "__main__":
    main()
