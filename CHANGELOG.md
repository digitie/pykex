# 변경 기록

이 프로젝트의 주요 변경 사항을 기록한다.

## 0.1.0 - 2026-04-30

초기 package scaffold와 첫 구현 pass.

### 추가

- `traffic`, `tollfee`, `restarea`, `facility`, `admin`, `reference` namespace를 가진 `KrexClient`.
- Retry와 provider error-code mapping을 포함한 `data.ex.co.kr`/`data.go.kr` HTTP helper.
- `TrafficByIc`, `TrafficFlow`, `Incident`, `TollFee`, `Tollgate`, `RestArea`, `FoodPrice`, `Route`, `Page` 등 주요 response model.
- 차량 유형, TCS 유형, 도로 운영자, 방향, traffic time unit, congestion level, discount type을 위한 안정 enum code table.
- API 문자열 값 변환 helper: 날짜, 숫자, Y/N flag, 단일 item response normalization.
- Query construction, parsing, local validation, body-level provider error, retry behavior, malformed response를 다루는 network-free pytest suite.
- `README.md`, `endpoints.md`, `codes.md`, `error-codes.md`, `SKILL.md`, `AGENTS.md`, `CONTRIBUTING.md`, `CHANGELOG.md` 문서 세트.
- 기존 remote `LICENSE`를 보존하고 package metadata를 GPL-3.0-or-later에 맞춤.

### 검증

- `python -m compileall src/krex tests`
- `python -m pytest`
- `python -m pytest --cov=krex --cov-fail-under=90`
- `python -m mypy src/krex`

초기 local environment에는 `ruff`가 없었다.

## Unreleased

### 추가

- `KEX_LIVE=1`과 local `KEX_EX_API_KEY`로 opt-in되는 live `data.ex.co.kr` test.
- 외부 form/validator를 위한 `KrexCode.values()`, `labels()`, `choices()`, `from_label()` helper.
- `restarea.disabled_facility()`와 `restarea.bus_transit()` raw wrapper.
- 문서화, 구현, typed/raw, live verification 상태를 추적하는 `API_COVERAGE.md`.
- `CoordinateSystem`, `RawCoordinate` 공개 좌표 type.
- `Page`의 sequence-like helper: iteration, `len(page)`, truthiness, `first`, `is_empty`.
- Rest area와 rest-area weather에 `lat`/`lon` field를 제공하고, tollgate/rest-area weather의 모호한 원본 좌표는 `raw_coordinate`로 보존.
- Frozen instance, validation, `model_dump()`, JSON schema를 지원하는 Pydantic v2 공개 response model.
- 한글 Python docstring과 프로젝트 기준 상대 경로 문서 규칙.
- Windows `rg.exe` access-denied fallback과 PowerShell UTF-8 read 규칙.
- `restarea.route_facilities()`, `restarea.fuel_prices()`, `restarea.convenience_facilities()`.
- `RestAreaRouteFacility`, `RestAreaFuelPrice` Pydantic model.

### 수정

- `traffic.incident()`를 존재하지 않는 `/openapi/trafficapi/incident`(항상 404)에서 실시간 문자정보(apiId 0611) `/openapi/burstInfo/realTimeSms`로 repoint. 파라미터를 `acc_type_code` 선택값으로 교체하고, `Incident` 모델을 live 실측 row(accDate/accHour/accType/smsText/startEndTypeCode/위경도 등)에 맞춰 재정렬. 경도는 포털 명세상 `altitude` 키로 온다. `realTimeSMSList` 목록 키 추출 지원. (#8)
- `KrexClient`에서 `session=None`을 명시해도 `KrexHttp`가 실제 httpx client를 만들도록 수정.
- `KrexHttp` repr에서 API key를 숨김.
- `data.ex.co.kr` 기본 base URL을 HTTPS로 변경.
- `trafficIc` 같은 endpoint-named top-level array response를 정규화.
- 실제 `trafficIc` field variant(`sumDate`, `sumTm`, `inoutType`, `trafficAmout`) 처리.
- Empty success response의 `count=0`을 `Page.total_count == 0`으로 보존.
- `1,994원`, O/X boolean flag 같은 실제 Krex 휴게소 API 값을 변환 helper가 처리.
- Rest-area route facility parsing에서 `serviceAreaName`이 비어 있어도 code와 facility metadata가 있으면 허용.
- 4인 전문 리뷰어 서브에이전트의 적대적 코드 리뷰로 발견·검증된 버그 수정: `_parse_page`가 페이지의
  행 하나만 파싱에 실패해도 전체 페이지를 버려서, 실시간 사고정보(`traffic.incident()`) 응답 중
  무관한 필드 하나가 깨지면 나머지 정상 사고까지 전부 사라지던 문제(개별 행 파싱 실패는 건너뛰고,
  전부 실패했을 때만 예외를 던지도록 수정), `_get()`의 다중 키 fallback이 값이 아니라 키 존재
  여부만 확인해 `entrpsNm`이 빈 문자열이면 값이 채워진 `restAreaNm`으로 넘어가지 않고 전체 휴게소
  목록 조회가 실패하던 문제 등. GitHub Actions CI(`lint`/`typecheck`/`test`) 추가.
