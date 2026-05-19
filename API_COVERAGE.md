# API Coverage

Snapshot date: 2026-05-07

This document separates three different ideas that are easy to mix up:

- **Documented in this repo**: listed in `endpoints.md`.
- **Implemented**: exposed as a `KrexClient` method.
- **Verified live**: called against the real provider in `tests/test_live_ex.py`.

The project is **not yet a complete wrapper for every Korea Expressway
Corporation API** published across `data.ex.co.kr` and `data.go.kr`. It is a
typed client for the endpoint set currently documented in this repository, with
an explicit backlog for broader official coverage.

## Current Repository Coverage

| Method | Source | Return | Implemented | Live verified | Notes |
|---|---|---|---:|---:|---|
| `traffic.by_ic()` | `data.ex.co.kr` | `Page[TrafficByIc]` | Yes | Yes | Real response uses top-level `trafficIc` and field variants such as `trafficAmout`. |
| `traffic.by_route()` | `data.ex.co.kr` | `Page[dict]` | Yes | Yes | Real empty success can be `count=0`, `list=[]`. |
| `traffic.flow()` | `data.ex.co.kr` | `Page[TrafficFlow]` | Yes | No | Path returned 404 in an earlier live probe; keep path unverified until portal UI confirms it. |
| `traffic.incident()` | `data.ex.co.kr` | `Page[Incident]` | Yes | No | Unit-tested wrapper, live path unverified. |
| `traffic.vds_raw()` | `data.ex.co.kr` | `Page[dict]` | Yes | No | Raw high-volume endpoint; live tests should constrain date/time ranges. |
| `traffic.avc_raw()` | `data.ex.co.kr` | `Page[dict]` | Yes | No | Raw high-volume endpoint; requires `vds_id` and `std_date`. |
| `tollfee.between_tollgates()` | `data.ex.co.kr` | `Page[TollFee]` | Yes | No | Path returned 404 in an earlier live probe; likely needs portal path correction. |
| `tollfee.tollgate_list()` | `data.ex.co.kr` | `Page[Tollgate]` | Yes | No | Path returned 404 in an earlier live probe; public model exists but path is unverified. |
| `restarea.route_facilities()` | `data.ex.co.kr` | `Page[RestAreaRouteFacility]` | Yes | Yes | Request URL from Krex OpenAPI guide: `/openapi/business/serviceAreaRoute`; real payload can include `serviceAreaName=None` and O/X flags. |
| `restarea.list_all()` | `data.go.kr` | `Page[RestArea]` | Yes | No | Standard-data endpoint uses `type=json`, not `_type=json`. |
| `restarea.weather()` / `restarea.latest_weather()` | `data.ex.co.kr` | `Page[RestAreaWeather]` | Yes | No | Ported from `pykma` expressway weather support; `latest_weather()` looks back over `/openapi/restinfo/restWeatherList`. |
| `restarea.fuel_prices()` | `data.ex.co.kr` | `Page[RestAreaFuelPrice]` | Yes | Yes | Request URL from Krex OpenAPI guide: `/openapi/business/curStateStation`; real prices include `원` suffix. |
| `restarea.convenience_facilities()` | `data.ex.co.kr` | `Page[dict]` | Yes | Yes | Request URL from Krex OpenAPI guide: `/openapi/business/conveniServiceArea`; kept raw until schema is promoted. |
| `restarea.food_price()` | `data.ex.co.kr` | `Page[FoodPrice]` | Yes | No | Path returned 404 in an earlier live probe; keep as unverified. |
| `restarea.parking()` | `data.ex.co.kr` | `Page[dict]` | Yes | No | Unit-tested wrapper, live path unverified. |
| `restarea.wifi()` | `data.ex.co.kr` | `Page[dict]` | Yes | No | Unit-tested wrapper, live path unverified. |
| `restarea.restroom()` | `data.ex.co.kr` | `Page[dict]` | Yes | No | Unit-tested wrapper, live path unverified. |
| `restarea.disabled_facility()` | `data.ex.co.kr` | `Page[dict]` | Yes | No | Implemented as raw wrapper until a real response is captured. |
| `restarea.bus_transit()` | `data.ex.co.kr` | `Page[dict]` | Yes | No | Implemented as raw wrapper until a real response is captured. |
| `facility.tollgate_info()` | `data.go.kr` | `Page[dict]` | Yes | No | URL must be checked against the current data.go.kr guide before promoting to typed model. |
| `facility.drowsy_shelter()` | `data.ex.co.kr` | `Page[dict]` | Yes | No | Path marked representative in `endpoints.md`. |
| `facility.shoulder_lane()` | `data.go.kr` | `Page[dict]` | Yes | No | URL must be checked against the current data.go.kr guide before promoting to typed model. |
| `admin.procurement_contracts()` | `data.go.kr` | `Page[dict]` | Yes | No | Dataset ID `15128076`; implemented as raw wrapper. |
| `reference.api_catalog()` / `get_api_catalog()` | local | `tuple[ApiCatalogItem, ...]` | Yes | N/A | Human-readable dataset names, provider, endpoint, and service-key request links for implemented methods. |
| `reference.common_codes()` | local | `dict[str, dict[str, str]]` | Yes | N/A | Local enum labels, not a live API. |
| `reference.routes()` | local | `tuple[Route, ...]` | Yes | N/A | Small built-in route sample, not a full route master. |

## Summary

| Category | Count |
|---|---:|
| Methods documented in `endpoints.md` | 26 |
| Methods implemented in `KrexClient` namespaces | 27 |
| Methods with typed public models | 10 |
| Methods returning raw `dict` records | 13 |
| Local reference helpers | 3 |
| Methods live-verified against provider | 5 |

## Broader Official API Backlog

Official Korea Expressway Corporation data appears in multiple places:

- [고속도로 공공데이터 포털](https://data.ex.co.kr/link/linkList?linkId=1&pn=1)
- [공공데이터포털: 한국도로공사_LCS 운영이력](https://www.data.go.kr/data/15076799/openapi.do)
- [공공데이터포털: 한국도로공사_실시간 문자정보](https://www.data.go.kr/data/15076693/openapi.do)
- [공공데이터포털: 한국도로공사_전자조달 계약공개현황](https://www.data.go.kr/data/15128076/openapi.do)

These examples show that the official API universe is wider than the current
repository endpoint set. Before claiming "all KEX APIs are supported", we need
a provider catalog pass that records:

- dataset title and provider portal;
- dataset ID where available;
- current request URL from the provider guide;
- required parameters and response sample;
- implementation status;
- unit-test fixture status;
- live verification date.

## Promotion Rules

Use these states while expanding coverage:

| State | Meaning |
|---|---|
| `planned` | Known official dataset, no wrapper yet. |
| `raw-wrapper` | Method exists and returns `Page[dict]`; path may still need live verification. |
| `typed-wrapper` | Method returns public Pydantic models/enums and has unit tests for parsing. |
| `live-verified` | Real provider call passed and response quirks are documented. |
| `deprecated-or-broken` | Provider path is known to return 404/405/HTML or has been replaced. |

New endpoints should start as `raw-wrapper` unless a realistic fixture is
available. Promote to `typed-wrapper` only after response fields are locked by
tests.
