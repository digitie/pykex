# python-krex-api

한국도로공사(Korea Expressway Corporation, KEX) 공공데이터 OpenAPI를 Python에서 편하게 쓰기 위한 비공식 클라이언트 라이브러리입니다.

`python-krex-api`는 `data.ex.co.kr`와 `data.go.kr`에 흩어진 고속도로 교통량, 실시간 소통, 통행료, 영업소, 휴게소, 휴게소별 날씨, 기준정보 API를 한 인터페이스로 감싸고, 응답을 Pydantic 모델과 enum으로 변환합니다.

> 현재 저장소는 초기 구현 단계입니다. 세부 엔드포인트 명세는 [endpoints.md](endpoints.md), 지원 상태표는 [API_COVERAGE.md](API_COVERAGE.md), 코드표는 [codes.md](codes.md), 에러 매핑은 [error-codes.md](error-codes.md), 구현 규칙은 [SKILL.md](SKILL.md)와 [AGENTS.md](AGENTS.md)를 참고하세요.

---

## 핵심 특징

- **네임스페이스형 클라이언트**: `client.traffic.flow()`, `client.tollfee.between_tollgates()`처럼 문서의 API 범주와 같은 구조로 호출합니다.
- **두 포털 동시 지원**: `data.ex.co.kr` 키(`KEX_EX_API_KEY`)와 `data.go.kr` 키(`KEX_GO_API_KEY`)를 분리해 사용합니다.
- **로컬 `.env` 기본 로딩**: 환경변수가 없으면 현재 작업 디렉터리부터 부모 디렉터리의 `.env`를 찾아 키를 읽고, 복붙 과정에서 섞인 공백 문자를 제거합니다.
- **API 카탈로그**: 구현된 API의 함수명, 데이터셋명, 포털, 엔드포인트, 서비스키 발급/활용신청 링크를 `get_api_catalog()`로 조회할 수 있습니다.
- **Python 타입 변환**: 날짜, 숫자, Y/N 플래그, 코드값을 `date`, `int`, `float`, `bool`, `StrEnum`으로 변환합니다.
- **Pydantic 응답 모델**: 공개 모델은 불변 `BaseModel` 기반이라 `model_dump()`, `model_validate()`, `model_json_schema()`를 외부 프로그램에서 바로 사용할 수 있습니다.
- **명확한 예외 계층**: 인증, 한도 초과, 파라미터 오류, 데이터 없음, 서버 오류, 파싱 오류, 네트워크 오류를 구분합니다.
- **본문 에러 코드 검사**: `data.go.kr`가 HTTP 200으로 반환하는 애플리케이션 에러도 놓치지 않습니다.
- **네트워크 없는 테스트**: fake session 기반으로 URL/쿼리/파싱/에러 매핑을 검증합니다.

---

## 시작하기

### 1단계: 인증키 준비

```bash
export KEX_EX_API_KEY="data.ex.co.kr에서_발급받은_키"
export KEX_GO_API_KEY="data.go.kr에서_발급받은_decoding_키"
```

Windows PowerShell:

```powershell
$env:KEX_EX_API_KEY="data.ex.co.kr에서_발급받은_키"
$env:KEX_GO_API_KEY="data.go.kr에서_발급받은_decoding_키"
```

또는 프로젝트 루트의 `.env`에 저장해도 됩니다. `KexClient()`와 `KexClient.from_env()`는 명시 인자가 없으면 환경변수를 먼저 보고, 없으면 가장 가까운 `.env`를 자동으로 읽습니다.

```dotenv
KEX_EX_API_KEY=data.ex.co.kr에서_발급받은_키
KEX_GO_API_KEY=data.go.kr에서_발급받은_decoding_키
```

웹 화면에서 키를 복사하며 줄바꿈, 탭, 앞뒤 공백이 섞여도 호출 전에 제거됩니다.

`requests.get(..., params=...)`로 전달하므로 `data.go.kr` 키는 Decoding 값을 권장합니다.

### 2단계: 설치

개발 중인 로컬 저장소:

```bash
pip install -e ".[dev]"
```

PyPI 배포 후:

```bash
pip install python-krex-api
```

### 3단계: 사용

```python
from krex import CarType, KexClient

client = KexClient.from_env()

# 실시간 소통
flows = client.traffic.flow(route_no="0010")
for item in flows.items[:5]:
    print(item.route_name, item.conzone_name, item.speed, item.congestion_level)

# 영업소간 통행료
fees = client.tollfee.between_tollgates(
    start_unit_code="101",
    end_unit_code="105",
    car_type=CarType.LIGHT,
)
print(fees.items[0].toll_fee)

# 휴게소 표준데이터(data.go.kr)
areas = client.restarea.list_all(route_name="경부고속도로")
print(areas.items[0].name, areas.items[0].has_ev_charger)

# 노선별 휴게시설과 휴게소 주유소 가격(data.ex.co.kr)
facilities = client.restarea.route_facilities(route_code="0010")
fuel_prices = client.restarea.fuel_prices(service_area_code=facilities.items[0].service_area_code)
print(facilities.items[0].service_area_name, fuel_prices.items[0].gasoline_price)

# 휴게소별 날씨(data.ex.co.kr)
weather = client.restarea.latest_weather(lookback_hours=72)
if weather.first:
    print(weather.first.unit_name, weather.first.weather, weather.first.temperature)
```

### 키를 직접 넘기는 방식

환경변수 대신 명시적으로 키를 주입할 수도 있습니다. 테스트나 배치 작업에서는 이 방식이 더 읽기 쉽습니다.

```python
from krex import KexClient

client = KexClient(
    ex_api_key="data.ex.co.kr 키",
    go_api_key="data.go.kr Decoding 키",
    timeout=5.0,
    max_retries=2,
)
```

실제 운영 코드에서는 키를 코드에 직접 적지 말고 Secret Manager, `.env`, CI/CD secret 같은 외부 설정에서 읽어오세요. 로컬 개발에서는 `.env`가 기본값으로 로드되지만, 배포 환경에서는 Secret Manager나 배포 플랫폼의 secret을 권장합니다.

---

## 제공 API

| 범주 | 메서드 | 원본 포털 | 반환 |
|---|---|---|---|
| 교통 | `traffic.by_ic()` | `data.ex.co.kr` | `Page[TrafficByIc]` |
| 교통 | `traffic.by_route()` | `data.ex.co.kr` | `Page[dict]` |
| 교통 | `traffic.flow()` | `data.ex.co.kr` | `Page[TrafficFlow]` |
| 교통 | `traffic.incident()` | `data.ex.co.kr` | `Page[Incident]` |
| 교통 | `traffic.vds_raw()`, `traffic.avc_raw()` | `data.ex.co.kr` | `Page[dict]` |
| 통행료 | `tollfee.between_tollgates()` | `data.ex.co.kr` | `Page[TollFee]` |
| 통행료 | `tollfee.tollgate_list()` | `data.ex.co.kr` | `Page[Tollgate]` |
| 휴게소 | `restarea.route_facilities()` | `data.ex.co.kr` | `Page[RestAreaRouteFacility]` |
| 휴게소 | `restarea.list_all()` | `data.go.kr` | `Page[RestArea]` |
| 휴게소 | `restarea.weather()`, `latest_weather()` | `data.ex.co.kr` | `Page[RestAreaWeather]` |
| 휴게소 | `restarea.fuel_prices()` | `data.ex.co.kr` | `Page[RestAreaFuelPrice]` |
| 휴게소 | `restarea.convenience_facilities()` | `data.ex.co.kr` | `Page[dict]` |
| 휴게소 | `restarea.food_price()` | `data.ex.co.kr` | `Page[FoodPrice]` |
| 휴게소 | `restarea.parking()`, `wifi()`, `restroom()` | `data.ex.co.kr` | `Page[dict]` |
| 휴게소 | `restarea.disabled_facility()`, `bus_transit()` | `data.ex.co.kr` | `Page[dict]` |
| 시설 | `facility.tollgate_info()` | `data.go.kr` | `Page[dict]` |
| 시설 | `facility.drowsy_shelter()` | `data.ex.co.kr` | `Page[dict]` |
| 시설 | `facility.shoulder_lane()` | `data.go.kr` | `Page[dict]` |
| 행정 | `admin.procurement_contracts()` | `data.go.kr` | `Page[dict]` |
| 기준정보 | `reference.api_catalog()` | 내장 카탈로그 | `tuple[ApiCatalogItem, ...]` |
| 기준정보 | `reference.routes()` | 내장 코드표 | `tuple[Route, ...]` |
| 기준정보 | `reference.common_codes()` | 내장 코드표 | `dict[str, dict[str, str]]` |

상세 파라미터와 응답 필드는 [endpoints.md](endpoints.md)를 기준으로 관리합니다.

---

## API 카탈로그

구현된 API 목록은 라이브러리에서 바로 조회할 수 있습니다. `dataset_name`은 UI에 사람이 읽기 좋은 데이터셋명으로 표시하기 위한 값이고, `service_key_url`은 해당 포털의 인증키 발급 또는 활용신청 화면으로 연결됩니다.

```python
from krex import get_api_catalog, get_api_catalog_item

for item in get_api_catalog(namespace="restarea"):
    print(item.function, item.dataset_name, item.service_key_url)

weather = get_api_catalog_item("restarea.weather")
if weather:
    print(weather.dataset_name)
```

Streamlit 같은 외부 디버그 UI에서는 `debug_call()` 결과의 `catalog` 필드를 Debug Trace 탭에 그대로 표시할 수 있습니다.

```python
run = client.debug_call("restarea.weather", sdate="20210507", std_hour=12)

if run.catalog:
    st.write("데이터셋", run.catalog["dataset_name"])
    if run.catalog.get("service_key_url"):
        st.link_button("서비스키 발급/활용신청", run.catalog["service_key_url"])
    st.dataframe([run.catalog])
```

이 저장소에는 같은 흐름을 바로 확인할 수 있는 예제 UI가 있습니다.

```powershell
pip install -e ".[debug-ui]"
python -m streamlit run examples/streamlit_debug_ui.py --server.port 8504
```

예제 UI는 API 선택 시 데이터셋명과 서비스키 받기 링크를 보여주고, 실행 시 `Debug Trace` 탭에서 `DebugRun.catalog`를 함께 표시합니다. 키 입력칸을 비워두면 `KexClient()`와 동일하게 환경변수 또는 로컬 `.env`의 값을 기본으로 사용합니다.

---

## 구현 상태

현재 구현은 “공통 호출 기반 + 핵심 모델 우선” 단계입니다.

| 영역 | 상태 | 비고 |
|---|---|---|
| HTTP transport | 구현됨 | 5xx/네트워크 retry, 키 마스킹, JSON 파싱 |
| `data.ex.co.kr` envelope | 구현됨 | `SUCCESS`, `NO_DATA`, 인증/한도/서버 코드 매핑 |
| `data.go.kr` envelope | 구현됨 | `response.header.resultCode` 검사 |
| 교통 핵심 모델 | 부분 구현 | `TrafficByIc`, `TrafficFlow`, `Incident` |
| 통행료 핵심 모델 | 구현됨 | `TollFee`, `Tollgate` |
| 휴게소 핵심 모델 | 부분 구현 | 노선별 휴게시설, 표준 휴게소, 휴게소별 날씨, 주유소 가격, 음식가격 |
| 시설/행정 상세 모델 | 원시 dict 반환 | 경로 검증 후 Pydantic 모델 승격 예정 |
| 라이브 호출 테스트 | 미포함 | 기본 테스트는 네트워크를 쓰지 않음 |

검증되지 않은 포털 경로나 데이터셋은 무리해서 모델로 고정하지 않고 `Page[dict]`로 반환합니다. 실제 응답 fixture가 쌓이면 Pydantic 모델로 승격합니다.

전체 지원/미지원/실서버 검증 상태는 [API_COVERAGE.md](API_COVERAGE.md)를 기준으로 관리합니다.

---

## 응답과 페이지 처리

모든 목록형 API는 `Page[T]`를 반환합니다.

```python
page = client.traffic.flow(route_no="0010")

page.items        # tuple[TrafficFlow, ...]
page.first        # TrafficFlow | None
len(page)         # 현재 페이지 item 수
bool(page)        # item이 있으면 True
page.page_no      # int | None
page.num_of_rows  # int | None
page.total_count  # int | None
page.raw          # 원본 응답 dict | None
```

`Page`는 바로 순회할 수 있고, `Page.items`는 tuple입니다. 호출 이후 결과가 의도치 않게 바뀌는 일을 줄이기 위한 선택입니다.

```python
for flow in page:
    print(flow.conzone_name, flow.speed)
```

공개 응답 모델은 Pydantic v2 모델입니다. 라이브러리 밖에서는 dict 변환, JSON schema 생성, 입력 검증을 별도 래퍼 없이 사용할 수 있습니다.

```python
from krex import TrafficFlow

flow = page.first
if flow:
    flow.model_dump()
    TrafficFlow.model_json_schema()
```

---

## 휴게소별 날씨

한국도로공사 `data.ex.co.kr`의 휴게소별 날씨 정보는 `restarea.weather()`로 특정 기준일/시각을 조회하고, `restarea.latest_weather()`로 최근 비어 있지 않은 시간대를 찾습니다.

```python
page = client.restarea.weather(sdate="20210507", std_hour=12)
latest = client.restarea.latest_weather(lookback_hours=72)

for row in latest.items[:3]:
    print(row.unit_name, row.route_name, row.weather, row.temperature)
```

`-99`, `-99.000000` 같은 한국도로공사 결측값은 `RestAreaWeather`의 typed 필드에서 `None`으로 정규화하고, 원문은 `raw`에 보존합니다.

---

## Enum과 타입 표준화

코드값은 `StrEnum` 기반 enum으로 제공합니다. 문자열처럼 API 파라미터에 쓸 수 있으면서, 라벨과 선택지를 함께 제공합니다.

```python
from krex import CarType, TCSType

CarType.LIGHT.value      # "1"
CarType.LIGHT.label      # "1종"
CarType.from_label("1종")
CarType.choices()        # (("1", "1종"), ...)
CarType.values()         # ("1", "2", ...)

client.traffic.by_ic(
    ex_div_code="00",
    unit_code="101",
    in_out="0",
    time_unit="1",
    tcs_type=TCSType.HIPASS,
    car_type=CarType.LIGHT,
)
```

외부 프로그램의 폼, CLI, OpenAPI schema, Pydantic validator에서는 `choices()`나 `values()`를 그대로 사용할 수 있습니다.

---

## 위경도 표준화

라이브러리에서 표준 위경도 DTO는 `kraddr.base.PlaceCoordinate(lat=..., lon=...)`로 표현합니다. GeoJSON, WKT, 외부 GIS 전송 경계에서는 각 표준에 맞춰 `(lon, lat)` 순서로 변환합니다.

```python
rest_area = client.restarea.list_all().first
if rest_area and rest_area.coordinate:
    rest_area.coordinate.lonlat              # (lon, lat)
    rest_area.coordinate.latlon              # (lat, lon)
    rest_area.coordinate.as_geojson_position()  # (lon, lat)
```

기존 호환성을 위해 `RestArea.lat`/`RestArea.lon`, `Tollgate.x`/`Tollgate.y`도 유지합니다. 다만 신규 코드에서는 가능한 한 `coordinate: PlaceCoordinate | None`을 우선 사용하세요.

영업소처럼 원본 좌표계가 불명확한 데이터는 `raw_coordinate`도 함께 제공합니다.

```python
tollgate = client.tollfee.tollgate_list().first
if tollgate and tollgate.raw_coordinate:
    print(tollgate.raw_coordinate.x, tollgate.raw_coordinate.y, tollgate.raw_coordinate.system)
```

---

## 주소

휴게소 주소가 있는 모델은 `address`에 `kraddr.base.Address`를 제공합니다. 원문 주소
문자열은 `address.display_address`나 `address.address`로 확인하고, 함께 사용할 수 있는
행정구역은 `address.effective_region`에서 확인합니다.

```python
facility = client.restarea.route_facilities().first
if facility and facility.address:
    facility.address.display_address
    facility.address.legal_dong_code
```

KEX 응답의 주소 문자열만으로는 10자리 법정동코드를 안전하게 확정하지 않습니다.
원문 row에 `legal_dong_code`, `ADM_CD` 같은 코드가 있으면 `Address`에 보존하고,
코드가 없으면 시도/시군구/읍면동 이름까지만 채웁니다. 좌표 기반 법정동코드가 필요하면
`python-vworld-api`의 법정동 경계 데이터(`LT_C_ADEMD_INFO`) 조회 결과를 별도로 결합하세요.

---

## 로컬 테스트 예제

실제 포털 호출 없이 fake session을 주입할 수 있습니다.

```python
from krex import KexClient

class Session:
    def get(self, url, *, params, timeout):
        ...

client = KexClient(ex_api_key="test-key", session=Session())
```

새 엔드포인트를 추가할 때는 이 방식으로 쿼리 파라미터와 파싱 결과를 먼저 고정한 뒤, 필요하면 별도의 `@pytest.mark.live` 테스트를 추가합니다.

### DebugRun과 fixture replay

디버그 UI나 임시 확인 도구는 라이브러리를 직접 호출하되, Streamlit 같은 UI 의존성을 이 패키지에 넣지 않습니다. 대신 `debug_call()`로 실행 정보를 모으고 `save_fixture()`로 replay 가능한 JSON fixture를 저장합니다.

```python
from krex import KexClient, save_fixture

client = KexClient.from_env()
run = client.debug_call("restarea.weather", sdate="20210507", std_hour=12)

print(run.catalog["dataset_name"])       # 한국도로공사_휴게소별 날씨
print(run.catalog["service_key_url"])    # 서비스키 발급/활용신청 링크

save_fixture(
    base_dir="tests/fixtures",
    function_name=run.function,
    case_name="weather_normal",
    description="휴게소 날씨 정상 응답",
    input_data=run.input,
    request_data=run.request,
    response_data=run.response,
    parsed_result=run.parsed,
    processed_result=run.processed,
)
```

Fixture 저장 전 `key`, `serviceKey`, `Authorization`, `api_key`, token 계열 필드는 `<REDACTED>`로 마스킹됩니다. 저장된 fixture는 `tests/test_generated_fixtures.py`가 외부 API 호출 없이 raw response를 다시 파싱해 회귀 테스트로 실행합니다.

현재 `DebugRun.parsed`와 `DebugRun.processed`는 같은 값입니다. 특정 엔드포인트에 별도 가공 단계가 생기면 `tests/runners.py`의 `process` 함수와 fixture의 `processed` 기대값을 함께 갱신하세요.

### 실제 data.ex.co.kr 테스트

실제 서버 테스트는 기본 테스트에서 자동 실행되지 않습니다. 로컬 `.env`에 키를 저장하고 `KEX_LIVE=1`을 명시했을 때만 실행됩니다.

```powershell
# .env
KEX_EX_API_KEY=발급받은_key

# PowerShell
$env:KEX_LIVE="1"
python -m pytest -m live -vv
```

현재 live 테스트는 `trafficIc`와 `trafficRoute`를 소량 호출해 인증키, 실제 응답 shape, 빈 결과의 `count=0` 처리를 검증합니다.

---

## 에러 처리

```python
from krex import KexAuthError, KexClient, KexQuotaExceededError, KexServerError

client = KexClient.from_env()

try:
    client.traffic.flow(route_no="0010")
except KexAuthError:
    print("인증키를 확인하세요.")
except KexQuotaExceededError:
    print("일일 호출 한도를 초과했습니다.")
except KexServerError:
    print("포털 장애 가능성이 있어 재시도 대상입니다.")
```

예외 계층과 원본 코드 매핑은 [error-codes.md](error-codes.md)에 정리되어 있습니다.

---

## 반복 실수 방지 체크리스트

- `data.go.kr`는 HTTP 200이어도 `response.header.resultCode`가 실패일 수 있습니다.
- `data.ex.co.kr` 인증키는 `key`, `data.go.kr` 인증키는 `serviceKey`입니다.
- `data.ex.co.kr`는 HTTPS를 사용합니다. HTTP로 호출하면 리다이렉트될 수 있습니다.
- `data.ex.co.kr` 응답은 `list` 대신 endpoint 이름(`trafficIc` 등)을 top-level 배열 키로 사용할 수 있습니다.
- 표준데이터 API는 `_type`이 아니라 `type=json`을 쓰는 경우가 있습니다.
- 영업소/노선/기관 코드는 선행 0이 의미 있으므로 `int`로 바꾸지 않습니다.
- 외부 표준 좌표 DTO는 `kraddr.base.PlaceCoordinate(lat=..., lon=...)`입니다. GeoJSON/GIS 경계용 `(lon, lat)`은 `point.lonlat` 또는 명시 변환 메서드를 사용하세요.
- 응답의 `items.item`, `list`, `data`는 단일 `dict` 또는 `list[dict]` 양쪽을 처리합니다.
- `count=0`은 `None`이 아니라 정수 `0`으로 보존해야 합니다.
- `NO_DATA`는 기본적으로 `KexNotFoundError`입니다. 빈 결과로 받고 싶으면 `KexClient(strict_no_data=False)`를 사용합니다.
- 테스트 fixture의 숫자값은 실제 API처럼 문자열로 유지합니다. 그래야 변환 경계가 검증됩니다.

---

## 개발

```bash
python -m compileall src/krex tests
python -m pytest
python -m pytest --cov=krex --cov-fail-under=90
python -m mypy src/krex
ruff check .
```

기본 테스트는 실제 API를 호출하지 않아야 합니다. 실제 호출 테스트는 `@pytest.mark.live`로 분리하고 인증키가 없으면 skip하세요.

---

## 패키지 설계

`python-krex-api`는 얇은 계층을 선호합니다.

| 모듈 | 책임 |
|---|---|
| `src/krex/client.py` | 사용자용 `KexClient`, 엔드포인트 네임스페이스, 모델 파싱 |
| `src/krex/catalog.py` | 구현 API 카탈로그, 데이터셋명, 서비스키 발급/활용신청 링크 |
| `src/krex/_env.py` | 로컬 `.env` 키 로딩 |
| `src/krex/_http.py` | HTTP 호출, retry, 포털별 envelope 정규화, 에러 매핑 |
| `src/krex/_convert.py` | 문자열 기반 API 응답을 Python 타입으로 변환 |
| `src/krex/codes.py` | 안정적인 코드값 enum과 라벨 |
| `src/krex/models.py` | public Pydantic 반환 모델 |
| `src/krex/exceptions.py` | 예외 계층 |
| `src/krex/debug.py` | `DebugRun`, JSON 변환, 민감정보 마스킹, fixture 저장 |

새 기능을 넣을 때는 보통 `src/krex/codes.py`와 `src/krex/models.py`를 먼저 보강하고, `src/krex/client.py`에서 메서드를 연결한 뒤, `tests/`에서 fake 응답으로 쿼리와 변환을 잠급니다.

---

## 프로젝트 파일

```text
src/krex/
├── __init__.py
├── _env.py
├── catalog.py
├── client.py
├── _http.py
├── _convert.py
├── codes.py
├── exceptions.py
├── debug.py
├── models.py
└── py.typed
tests/
├── fixtures/
├── runners.py
├── utils.py
└── test_*.py
```

---

## 라이선스

GPL-3.0-or-later. 자세한 조건은 [LICENSE](LICENSE)를 참고하세요.

원천 데이터의 저작권과 이용조건은 한국도로공사, 공공데이터포털, 각 데이터 제공기관 정책을 따릅니다. 이 프로젝트는 비공식 라이브러리이며 한국도로공사와 무관합니다.
