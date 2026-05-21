# API coverage

Snapshot date: 2026-05-07

이 문서는 섞이기 쉬운 세 가지 상태를 분리한다.

- **이 저장소에 문서화됨**: `endpoints.md`에 등재됨.
- **구현됨**: `KrexClient` method로 노출됨.
- **Live 검증됨**: `tests/test_live_ex.py`에서 실제 provider를 호출해 확인함.

이 프로젝트는 `data.ex.co.kr`와 `data.go.kr`에 흩어진 한국도로공사 API 전체를 아직 완전히 감싼 wrapper가 아니다. 현재 저장소에 문서화된 endpoint set을 typed client로 제공하고, 더 넓은 공식 coverage는 backlog로 명시한다.

## 현재 저장소 coverage

| Method | Source | Return | 구현 | Live 검증 | 메모 |
|---|---|---|---:|---:|---|
| `traffic.by_ic()` | `data.ex.co.kr` | `Page[TrafficByIc]` | Yes | Yes | 실제 응답은 top-level `trafficIc`와 `trafficAmout` 같은 field variant를 사용한다. |
| `traffic.by_route()` | `data.ex.co.kr` | `Page[dict]` | Yes | Yes | Empty success가 `count=0`, `list=[]`일 수 있다. |
| `traffic.flow()` | `data.ex.co.kr` | `Page[TrafficFlow]` | Yes | No | 과거 live probe에서 404가 반환되어 portal UI 확인 전까지 unverified로 둔다. |
| `traffic.incident()` | `data.ex.co.kr` | `Page[Incident]` | Yes | No | Unit-tested wrapper, live path unverified. |
| `traffic.vds_raw()` | `data.ex.co.kr` | `Page[dict]` | Yes | No | High-volume raw endpoint이므로 live test는 date/time range를 좁힌다. |
| `traffic.avc_raw()` | `data.ex.co.kr` | `Page[dict]` | Yes | No | `vds_id`, `std_date`가 필요하다. |
| `tollfee.between_tollgates()` | `data.ex.co.kr` | `Page[TollFee]` | Yes | No | 과거 live probe에서 404. Path 보정 필요 가능성이 있다. |
| `tollfee.tollgate_list()` | `data.ex.co.kr` | `Page[Tollgate]` | Yes | No | Public model은 있으나 live path는 unverified. |
| `restarea.route_facilities()` | `data.ex.co.kr` | `Page[RestAreaRouteFacility]` | Yes | Yes | Krex OpenAPI guide URL: `/openapi/business/serviceAreaRoute`. |
| `restarea.list_all()` | `data.go.kr` | `Page[RestArea]` | Yes | No | Standard-data endpoint는 `_type=json`이 아니라 `type=json`을 쓴다. |
| `restarea.weather()` / `latest_weather()` | `data.ex.co.kr` | `Page[RestAreaWeather]` | Yes | No | `pykma` expressway weather support에서 port함. |
| `restarea.fuel_prices()` | `data.ex.co.kr` | `Page[RestAreaFuelPrice]` | Yes | Yes | 실제 price에는 `원` suffix가 포함될 수 있다. |
| `restarea.convenience_facilities()` | `data.ex.co.kr` | `Page[dict]` | Yes | Yes | Schema promotion 전까지 raw로 유지한다. |
| `restarea.food_price()` | `data.ex.co.kr` | `Page[FoodPrice]` | Yes | No | 과거 live probe에서 404. |
| `restarea.parking()` | `data.ex.co.kr` | `Page[dict]` | Yes | No | Unit-tested wrapper. |
| `restarea.wifi()` | `data.ex.co.kr` | `Page[dict]` | Yes | No | Unit-tested wrapper. |
| `restarea.restroom()` | `data.ex.co.kr` | `Page[dict]` | Yes | No | Unit-tested wrapper. |
| `restarea.disabled_facility()` | `data.ex.co.kr` | `Page[dict]` | Yes | No | 실제 응답 확보 전까지 raw wrapper. |
| `restarea.bus_transit()` | `data.ex.co.kr` | `Page[dict]` | Yes | No | 실제 응답 확보 전까지 raw wrapper. |
| `facility.tollgate_info()` | `data.go.kr` | `Page[dict]` | Yes | No | Typed model 승격 전 현재 data.go.kr guide 확인 필요. |
| `facility.drowsy_shelter()` | `data.ex.co.kr` | `Page[dict]` | Yes | No | `endpoints.md`에 representative로 표시. |
| `facility.shoulder_lane()` | `data.go.kr` | `Page[dict]` | Yes | No | Typed model 승격 전 URL 확인 필요. |
| `admin.procurement_contracts()` | `data.go.kr` | `Page[dict]` | Yes | No | Dataset ID `15128076`; raw wrapper. |
| `reference.api_catalog()` / `get_api_catalog()` | local | `tuple[ApiCatalogItem, ...]` | Yes | N/A | 구현 method의 dataset name, provider, endpoint, service-key 신청 링크. |
| `reference.common_codes()` | local | `dict[str, dict[str, str]]` | Yes | N/A | Live API가 아닌 local enum label. |
| `reference.routes()` | local | `tuple[Route, ...]` | Yes | N/A | 전체 route master가 아닌 작은 built-in sample. |

## 요약

| Category | Count |
|---|---:|
| `endpoints.md`에 문서화된 method | 26 |
| `KrexClient` namespace에 구현된 method | 27 |
| Typed public model을 반환하는 method | 10 |
| Raw `dict` record를 반환하는 method | 13 |
| Local reference helper | 3 |
| Provider live 검증 완료 method | 5 |

## 더 넓은 공식 API backlog

한국도로공사 공식 데이터는 여러 portal에 존재한다.

- [고속도로 공공데이터 포털](https://data.ex.co.kr/link/linkList?linkId=1&pn=1)
- [공공데이터포털: 한국도로공사_LCS 운영이력](https://www.data.go.kr/data/15076799/openapi.do)
- [공공데이터포털: 한국도로공사_실시간 문자정보](https://www.data.go.kr/data/15076693/openapi.do)
- [공공데이터포털: 한국도로공사_전자조달 계약공개현황](https://www.data.go.kr/data/15128076/openapi.do)

“모든 KEX API를 지원한다”고 주장하려면 provider catalog pass가 필요하다. 최소한 dataset title, provider portal, dataset ID, 현재 request URL, 필수 parameter, response sample, 구현 상태, unit-test fixture 상태, live verification date를 기록해야 한다.

## 승격 규칙

| State | 의미 |
|---|---|
| `planned` | 공식 dataset은 확인했지만 wrapper가 아직 없다. |
| `raw-wrapper` | Method는 있고 `Page[dict]`를 반환한다. Path live verification이 남았을 수 있다. |
| `typed-wrapper` | Public Pydantic model/enum을 반환하고 parsing test가 있다. |
| `live-verified` | 실제 provider 호출이 통과했고 응답 특이점을 문서화했다. |
| `deprecated-or-broken` | Provider path가 404/405/HTML을 반환하거나 대체된 것으로 확인됐다. |

새 endpoint는 realistic fixture가 없는 한 `raw-wrapper`에서 시작한다. Response field가 test로 고정된 뒤에만 `typed-wrapper`로 승격한다.
