---
name: python-krex-api
description: data.ex.co.kr와 data.go.kr로 제공되는 한국도로공사 OpenAPI Python client를 구현, 확장, test, troubleshooting할 때 사용한다.
---

# python-krex-api Skill

`python-krex-api` Python library에서 작업할 때 이 guide를 사용한다.

## Scope

이 프로젝트는 다음 한국도로공사 공개 API를 감싼다.

1. `data.ex.co.kr`: `key`와 `type=json` 사용
2. `data.go.kr` / `api.data.go.kr`: `serviceKey`와 JSON 응답 option 사용

공개 package import 이름은 `krex`, distribution 이름은 `python-krex-api`다.

## 문서 언어 정책

모든 Markdown/RST 문서는 한글로 작성한다. Provider field, code identifier, 명령어, URL, protocol literal은 그대로 보존할 수 있다.

## Repository rule

- Endpoint 동작 변경 전 `endpoints.md`, `codes.md`, `error-codes.md`를 읽는다.
- API 지원 또는 live verification을 주장하기 전 `API_COVERAGE.md`를 읽는다.
- 구현 구조는 `pykma`, `pyopinet`과 맞춘다: `src/krex/client.py`, `_http.py`, `_convert.py`, `codes.py`, `models.py`, `catalog.py`, `exceptions.py`, `debug.py`.
- 일반 test에 live network call을 넣지 않는다.
- API key나 generated cache를 commit하지 않는다.
- 문서 file location은 프로젝트 기준 상대 경로로 쓴다.
- Python docstring과 설명 주석은 한글로 쓴다.
- Windows에서 `rg.exe`가 막히면 PowerShell `Get-ChildItem -Recurse -File | Select-String -Pattern "..."`로 전환한다.
- Markdown/UTF-8 text는 PowerShell에서 `-Encoding utf8`로 읽는다.
- 공개 반환 model은 immutable Pydantic model, 안정 code는 `StrEnum`을 선호한다.
- Endpoint path가 불확실하면 stable schema인 척하지 말고 `Page[dict]`로 노출하고 불확실성을 문서화한다.
- Sibling library에 검증된 구현이 있으면 standalone wrapper를 만들지 말고 기존 `KrexClient` namespace로 port한다.

## API key rule

- `KEX_EX_API_KEY`: `data.ex.co.kr` key
- `DATA_GO_KR_SERVICE_KEY`: `data.go.kr` key. `httpx` query params에는 decoded key를 선호한다.
- `KrexClient()`는 환경 변수가 없을 때 가까운 local `.env`를 fallback으로 읽고 key의 copy-paste whitespace를 정리한다.
- 사용자가 key를 chat이나 file에 붙여넣으면 rotate하고 working tree에서 제거하도록 안내한다.

## URL과 parameter rule

`data.ex.co.kr`:

- Base URL: `http://data.ex.co.kr`
- 인증 parameter: `key`
- JSON parameter: `type=json`
- Pagination: `numOfRows`, `pageNo`
- 흔한 result shape: `{"code": "SUCCESS", "list": [...]}`

`data.go.kr`:

- 인증 parameter: `serviceKey`
- 많은 service API는 `_type=json`을 사용한다.
- 일부 standard data API는 `type=json`을 사용한다.
- 흔한 result shape: `{"response": {"header": {"resultCode": "00"}, "body": {"items": {"item": [...]}}}}`

## Error mapping

HTTP status만 믿지 말고 body-level result code를 확인한다.

- Auth: `INVALID_KEY`, `EXPIRED_KEY`, `NO_REGISTERED_KEY`, `20`, `21`, `30`, `31`, `32`, `33`
- Quota: `EXCEEDED_LIMIT`, `22`, HTTP `429`
- Missing parameter: `INVALID_REQUEST_PARAMETER`, `11`
- Invalid parameter: `INVALID_PARAMETER_VALUE`, `10`
- No data: `NO_DATA`, `03`
- Server/transient: `SYSTEM_ERROR`, `SERVICE_TIMEOUT`, `SERVICE_UNAVAILABLE`, `01`, `02`, `04`, `05`, HTTP `5xx`

## Conversion rule

- Route, tollgate, office, code 값은 문자열로 보존한다.
- API date는 model boundary에서만 변환한다.
- `speed`, `tollFee`, `trafficVol` 같은 numeric metric은 `float` 또는 `int`로 변환한다.
- Y/N field는 `bool | None`으로 변환한다.
- 공개 model은 `KrexModel` 기반으로 유지해 `model_dump()`, `model_validate()`, `model_json_schema()`를 안정적으로 제공한다.
- 명확한 WGS84 위치는 모델의 `lat`/`lon` field로 노출한다.
- 주소 데이터는 provider 원문 문자열로 보존한다. 법정동 코드는 free-form 주소에서 추측하지 않는다.
- 모호한 raw coordinate는 `CoordinateSystem`을 포함한 `RawCoordinate`로 보존한다.
- 단일 item `dict`와 다중 item `list[dict]`는 내부 list 형태로 정규화한다.

## 새 endpoint test 요구사항

- Query parameter와 enum raw API code conversion
- 문자열 numeric/date input의 성공 parsing
- 단일 item `dict` normalization
- Body-level provider error mapping
- Malformed response shape
- Missing required local parameter

## 새 endpoint 문서 요구사항

- `README.md`: endpoint가 사용자 public API라면 사용법 추가
- `endpoints.md`: source portal, path, method, parameter, known response field
- `API_COVERAGE.md`: implementation state와 live verification status
- `src/krex/catalog.py`: dataset name, provider, endpoint, fixture status, service-key request URL
- `codes.md`: public parameter/model이 쓰는 stable code table
- `error-codes.md`: 새 provider error code
- `AGENTS.md` 또는 `SKILL.md`: 반복 실수나 workflow rule
- 문서 style rule은 `CONTRIBUTING.md`, `AGENTS.md`, `SKILL.md`를 함께 갱신

## 반복 실수

- `tn_pubr_public_rest_area_api`에 `_type`을 쓰지 않는다. 이 endpoint는 `type`을 쓴다.
- `routeNo="0010"`, `unitCode="101"`을 int로 바꾸지 않는다.
- `strict_no_data=False`가 아닌 한 `NO_DATA`를 success로 처리하지 않는다.
- 안정 code value를 raw API string으로 흘리지 않는다.
- 추측한 endpoint path를 문서화 없이 추가하지 않는다.
- Test가 현재 public portal data에 의존하지 않게 한다.
- Streamlit/debug UI dependency를 library에 추가하지 않는다.
- Saved API case마다 pytest file을 생성하지 않는다. JSON fixture를 replay한다.
- API key, Authorization header, token field redaction 확인 전 fixture를 commit하지 않는다.
- Money/traffic parsing은 call site가 아니라 `src/krex/_convert.py` 또는 model parser helper에 둔다.
- Realistic fixture나 fake response가 field name을 고정하기 전 Pydantic model을 공개하지 않는다.
- Public model에 ad-hoc `(lat, lon)` tuple을 추가하지 않는다.
- `data.ex.co.kr` 응답이 항상 `list`라고 가정하지 않는다.
- `payload.get("count") or ...`를 쓰지 않는다. Empty response의 `count=0`은 0으로 남아야 한다.
- API key가 model repr에 나오지 않게 한다.
- `rg` access-denied 후 반복 시도하지 말고 PowerShell fallback으로 전환한다.

## Release checklist

```bash
python -m compileall src/krex tests
python -m pytest
python -m pytest --cov=krex --cov-fail-under=90
python -m mypy src/krex
```

환경에 Ruff가 있으면 `ruff check .`도 실행한다.

Live `data.ex.co.kr` test:

```powershell
$env:KEX_LIVE="1"
python -m pytest -m live -vv
```

## Verification

최소 실행:

```bash
python -m compileall src/krex tests
python -m pytest
```

Type/lint 도구가 설치되어 있으면:

```bash
python -m mypy src/krex
ruff check .
```
