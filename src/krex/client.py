"""한국도로공사 OpenAPI 고수준 클라이언트."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, TypeVar, cast

from kraddr.base import Address, PlaceCoordinate

from ._convert import (
    strip_or_none,
    to_bool_yn,
    to_date_or_none,
    to_float_or_none,
    to_int_or_none,
)
from ._env import get_local_env_value
from ._http import KrexHttp, NormalizedPayload, normalize_api_key
from .catalog import get_api_catalog, get_api_catalog_item
from .codes import (
    ROUTE_NAMES,
    CarType,
    CongestionLevel,
    CoordinateSystem,
    Direction,
    DiscountType,
    IOType,
    KrexCode,
    RoadOperator,
    TCSType,
    TimeUnit,
    coerce_code,
)
from .debug import DebugRun, exception_to_debug_error, jsonable
from .exceptions import KrexInvalidParameterError, KrexNotFoundError, KrexParseError
from .models import (
    ApiCatalogItem,
    FoodPrice,
    Incident,
    Page,
    RawCoordinate,
    RestArea,
    RestAreaFuelPrice,
    RestAreaRouteFacility,
    RestAreaWeather,
    Route,
    TollFee,
    Tollgate,
    TrafficByIc,
    TrafficFlow,
)

T = TypeVar("T")
E = TypeVar("E", bound=KrexCode)
KST = timezone(timedelta(hours=9), "KST")


class KrexClient:
    """Krex OpenAPI 호출 진입점.

    엔드포인트 문서(`endpoints.md`)와 메서드 이름이 비슷하게 보이도록
    `traffic`, `tollfee`, `restarea`, `facility`, `admin`, `reference`
    네임스페이스를 제공합니다.
    """

    def __init__(
        self,
        ex_api_key: str | None = None,
        go_api_key: str | None = None,
        *,
        timeout: float = 10.0,
        strict_no_data: bool = True,
        max_retries: int = 2,
        retry_backoff: float = 0.5,
        session: Any | None = None,
    ) -> None:
        self.ex_api_key = normalize_api_key(ex_api_key) or normalize_api_key(
            get_local_env_value("KEX_EX_API_KEY")
        )
        self.go_api_key = normalize_api_key(go_api_key) or normalize_api_key(
            get_local_env_value("DATA_GO_KR_SERVICE_KEY")
        )
        self.strict_no_data = strict_no_data
        self._http = KrexHttp(
            self.ex_api_key,
            self.go_api_key,
            timeout=timeout,
            max_retries=max_retries,
            retry_backoff=retry_backoff,
            session=session,
        )
        self.traffic = TrafficService(self)
        self.tollfee = TollfeeService(self)
        self.restarea = RestareaService(self)
        self.facility = FacilityService(self)
        self.admin = AdminService(self)
        self.reference = ReferenceService(self)
        self.closed = False

    @classmethod
    def from_env(cls, **kwargs: Any) -> KrexClient:
        return cls(**kwargs)

    @classmethod
    def aio(cls, **kwargs: Any) -> AsyncKrexClient:
        return AsyncKrexClient(**kwargs)

    async def adebug_call(self, function: str, **params: Any) -> DebugRun:
        """Async wrapper for debug execution in asyncio applications."""

        return await asyncio.to_thread(self.debug_call, function, **params)

    def debug_call(self, function: str, **params: Any) -> DebugRun:
        """외부 Debug UI가 사용할 수 있는 단일 함수 실행 정보를 반환합니다."""

        trace = [f"resolve {function}"]
        catalog_item = get_api_catalog_item(function)
        catalog = jsonable(catalog_item) if catalog_item is not None else None
        if catalog_item is not None:
            trace.append(f"catalog dataset: {catalog_item.dataset_name}")
            if catalog_item.service_key_url:
                trace.append(f"service key URL: {catalog_item.service_key_url}")
        parsed: Any = None
        processed: Any = None
        error: dict[str, Any] | None = None
        self._http.last_request = None
        self._http.last_response = None
        try:
            method = self._resolve_debug_function(function)
            trace.append("call public client method")
            parsed = method(**params)
            processed = parsed
            trace.append("call completed")
        except Exception as exc:  # noqa: BLE001 - 디버그 UI는 예외를 화면에 보여줘야 합니다.
            error = exception_to_debug_error(exc)
            trace.append(f"error: {type(exc).__name__}")
        return DebugRun(
            function=function,
            input=dict(params),
            request=self._http.last_request or {},
            response=self._http.last_response or {},
            parsed=parsed,
            processed=processed,
            trace=trace,
            catalog=catalog,
            error=error,
        )

    def _resolve_debug_function(self, function: str) -> Callable[..., Any]:
        parts = function.split(".")
        if len(parts) != 2 or any(part.startswith("_") or not part for part in parts):
            raise KrexInvalidParameterError("function must look like 'namespace.method'")
        namespace = getattr(self, parts[0], None)
        method = getattr(namespace, parts[1], None)
        if not callable(method):
            raise KrexInvalidParameterError(f"unknown debug function: {function}")
        return cast(Callable[..., Any], method)

    async def aclose(self) -> None:
        await self._http.aclose()
        self.closed = True

    def close(self) -> None:
        self._http.close()
        self.closed = True

    async def __aenter__(self) -> KrexClient:
        return self

    async def __aexit__(self, *_exc_info: Any) -> None:
        await self.aclose()

    def __enter__(self) -> KrexClient:
        return self

    def __exit__(self, *_exc_info: Any) -> None:
        self.close()

    def _page_ex(
        self,
        path: str,
        params: dict[str, Any],
        parser: Callable[[dict[str, Any]], T],
    ) -> Page[T]:
        try:
            payload = self._http.get_ex(path, _clean(params))
        except KrexNotFoundError:
            if self.strict_no_data:
                raise
            return Page(items=())
        return _parse_page(payload, parser)

    async def _apage_ex(
        self,
        path: str,
        params: dict[str, Any],
        parser: Callable[[dict[str, Any]], T],
    ) -> Page[T]:
        try:
            payload = await self._http.aget_ex(path, _clean(params))
        except KrexNotFoundError:
            if self.strict_no_data:
                raise
            return Page(items=())
        return _parse_page(payload, parser)

    def _page_go(
        self,
        url: str,
        params: dict[str, Any],
        parser: Callable[[dict[str, Any]], T],
        *,
        standard: bool = False,
    ) -> Page[T]:
        try:
            payload = self._http.get_go(url, _clean(params), standard=standard)
        except KrexNotFoundError:
            if self.strict_no_data:
                raise
            return Page(items=())
        return _parse_page(payload, parser)

    async def _apage_go(
        self,
        url: str,
        params: dict[str, Any],
        parser: Callable[[dict[str, Any]], T],
        *,
        standard: bool = False,
    ) -> Page[T]:
        try:
            payload = await self._http.aget_go(url, _clean(params), standard=standard)
        except KrexNotFoundError:
            if self.strict_no_data:
                raise
            return Page(items=())
        return _parse_page(payload, parser)


class AsyncKrexClient:
    """Asynchronous facade matching the `KrexClient.aio()` construction style."""

    def __init__(
        self,
        ex_api_key: str | None = None,
        go_api_key: str | None = None,
        *,
        timeout: float = 10.0,
        strict_no_data: bool = True,
        max_retries: int = 2,
        retry_backoff: float = 0.5,
        session: Any | None = None,
    ) -> None:
        self._sync_client = KrexClient(
            ex_api_key=ex_api_key,
            go_api_key=go_api_key,
            timeout=timeout,
            strict_no_data=strict_no_data,
            max_retries=max_retries,
            retry_backoff=retry_backoff,
            session=session,
        )
        self.traffic = _AsyncServiceProxy(self._sync_client.traffic)
        self.tollfee = _AsyncServiceProxy(self._sync_client.tollfee)
        self.restarea = _AsyncServiceProxy(self._sync_client.restarea)
        self.facility = _AsyncServiceProxy(self._sync_client.facility)
        self.admin = _AsyncServiceProxy(self._sync_client.admin)
        self.reference = _AsyncServiceProxy(self._sync_client.reference)
        self.closed = False

    @property
    def ex_api_key(self) -> str | None:
        return self._sync_client.ex_api_key

    @property
    def go_api_key(self) -> str | None:
        return self._sync_client.go_api_key

    async def debug_call(self, function: str, **params: Any) -> DebugRun:
        return await self._sync_client.adebug_call(function, **params)

    async def adebug_call(self, function: str, **params: Any) -> DebugRun:
        return await self.debug_call(function, **params)

    async def aclose(self) -> None:
        await self._sync_client.aclose()
        self.closed = True

    async def __aenter__(self) -> AsyncKrexClient:
        return self

    async def __aexit__(self, *_exc_info: Any) -> None:
        await self.aclose()


class _AsyncServiceProxy:
    def __init__(self, service: Any) -> None:
        self._service = service

    def __getattr__(self, name: str) -> Any:
        value = getattr(self._service, name)
        if not callable(value):
            return value

        async def call(*args: Any, **kwargs: Any) -> Any:
            return await asyncio.to_thread(value, *args, **kwargs)

        return call


@dataclass(frozen=True, slots=True)
class TrafficService:
    _client: KrexClient

    def by_ic(
        self,
        *,
        ex_div_code: RoadOperator | str,
        unit_code: str,
        in_out: IOType | str,
        time_unit: TimeUnit | str,
        tcs_type: TCSType | str,
        car_type: CarType | str,
        num_of_rows: int = 1000,
        page_no: int = 1,
    ) -> Page[TrafficByIc]:
        _require(unit_code, "unit_code")
        return self._client._page_ex(
            "/openapi/trafficapi/trafficIc",
            {
                "exDivCode": coerce_code(RoadOperator, ex_div_code, "ex_div_code"),
                "unitCode": unit_code,
                "inOutType": coerce_code(IOType, in_out, "in_out"),
                "tmType": coerce_code(TimeUnit, time_unit, "time_unit"),
                "tcsType": coerce_code(TCSType, tcs_type, "tcs_type"),
                "carType": coerce_code(CarType, car_type, "car_type"),
                "numOfRows": num_of_rows,
                "pageNo": page_no,
            },
            _traffic_by_ic,
        )

    def by_route(
        self,
        *,
        route_no: str,
        time_unit: TimeUnit | str,
        direction: Direction | str | None = None,
        car_type: CarType | str | None = None,
        std_date: str | None = None,
        num_of_rows: int = 1000,
        page_no: int = 1,
    ) -> Page[dict[str, Any]]:
        _require(route_no, "route_no")
        return self._client._page_ex(
            "/openapi/trafficapi/trafficRoute",
            {
                "routeNo": route_no,
                "tmType": coerce_code(TimeUnit, time_unit, "time_unit"),
                "dirType": _optional_code(Direction, direction, "direction"),
                "carType": _optional_code(CarType, car_type, "car_type"),
                "stdDate": std_date,
                "numOfRows": num_of_rows,
                "pageNo": page_no,
            },
            dict,
        )

    def flow(
        self,
        *,
        route_no: str | None = None,
        conzone_id: str | None = None,
        direction: Direction | str | None = None,
        num_of_rows: int = 1000,
        page_no: int = 1,
    ) -> Page[TrafficFlow]:
        return self._client._page_ex(
            "/openapi/trafficapi/realFlow",
            {
                "routeNo": route_no,
                "conzoneId": conzone_id,
                "dirType": _optional_code(Direction, direction, "direction"),
                "numOfRows": num_of_rows,
                "pageNo": page_no,
            },
            _traffic_flow,
        )

    def incident(
        self,
        *,
        route_no: str | None = None,
        incident_type: str | None = None,
        num_of_rows: int = 1000,
        page_no: int = 1,
    ) -> Page[Incident]:
        return self._client._page_ex(
            "/openapi/trafficapi/incident",
            {
                "routeNo": route_no,
                "incidentType": incident_type,
                "numOfRows": num_of_rows,
                "pageNo": page_no,
            },
            _incident,
        )

    def vds_raw(self, **params: Any) -> Page[dict[str, Any]]:
        return self._client._page_ex("/openapi/trafficapi/vdsRaw", params, dict)

    def avc_raw(self, *, vds_id: str, std_date: str, **params: Any) -> Page[dict[str, Any]]:
        _require(vds_id, "vds_id")
        _require(std_date, "std_date")
        query = {"vdsId": vds_id, "stdDate": std_date}
        query.update(params)
        return self._client._page_ex("/openapi/trafficapi/avcRaw", query, dict)


@dataclass(frozen=True, slots=True)
class TollfeeService:
    _client: KrexClient

    def between_tollgates(
        self,
        *,
        start_unit_code: str,
        end_unit_code: str,
        car_type: CarType | str,
        discount_type: DiscountType | str | None = None,
        num_of_rows: int = 100,
        page_no: int = 1,
    ) -> Page[TollFee]:
        _require(start_unit_code, "start_unit_code")
        _require(end_unit_code, "end_unit_code")
        return self._client._page_ex(
            "/openapi/tollfee/tollFeeBetweenTcs",
            {
                "startUnitCode": start_unit_code,
                "endUnitCode": end_unit_code,
                "carType": coerce_code(CarType, car_type, "car_type"),
                "discountType": _optional_code(DiscountType, discount_type, "discount_type"),
                "numOfRows": num_of_rows,
                "pageNo": page_no,
            },
            _toll_fee,
        )

    def tollgate_list(self, *, num_of_rows: int = 1000, page_no: int = 1) -> Page[Tollgate]:
        return self._client._page_ex(
            "/openapi/business/openapibusinessunit",
            {"numOfRows": num_of_rows, "pageNo": page_no},
            _tollgate,
        )


@dataclass(frozen=True, slots=True)
class RestareaService:
    _client: KrexClient

    def route_facilities(
        self,
        *,
        route_name: str | None = None,
        direction: str | None = None,
        service_area_name: str | None = None,
        route_code: str | None = None,
        service_area_code: str | None = None,
        num_of_rows: int = 1000,
        page_no: int = 1,
    ) -> Page[RestAreaRouteFacility]:
        return self._client._page_ex(
            "/openapi/business/serviceAreaRoute",
            {
                "routeName": route_name,
                "direction": direction,
                "serviceAreaName": service_area_name,
                "routeCode": route_code,
                "serviceAreaCode": service_area_code,
                "numOfRows": num_of_rows,
                "pageNo": page_no,
            },
            _rest_area_route_facility,
        )

    def list_all(
        self,
        *,
        rest_area_name: str | None = None,
        route_name: str | None = None,
        num_of_rows: int = 1000,
        page_no: int = 1,
    ) -> Page[RestArea]:
        return self._client._page_go(
            "https://api.data.go.kr/openapi/tn_pubr_public_rest_area_api",
            {
                "restAreaNm": rest_area_name,
                "routeNm": route_name,
                "numOfRows": num_of_rows,
                "pageNo": page_no,
            },
            _rest_area,
            standard=True,
        )

    def weather(
        self,
        *,
        sdate: str | date | datetime,
        std_hour: str | int,
    ) -> Page[RestAreaWeather]:
        return self._client._page_ex(
            "/openapi/restinfo/restWeatherList",
            {"sdate": _format_sdate(sdate), "stdHour": _format_hour(std_hour)},
            _rest_area_weather,
        )

    def latest_weather(
        self,
        *,
        when: datetime | None = None,
        lookback_hours: int = 48,
    ) -> Page[RestAreaWeather]:
        if lookback_hours < 0:
            raise ValueError("lookback_hours must be >= 0")
        base = _as_kst(when) if when is not None else datetime.now(KST)
        base = base.replace(minute=0, second=0, microsecond=0)
        last_raw: dict[str, Any] | None = None
        for offset in range(lookback_hours + 1):
            target = base - timedelta(hours=offset)
            try:
                page = self.weather(sdate=target, std_hour=target.hour)
            except KrexNotFoundError:
                continue
            if page.items:
                return page
            last_raw = page.raw
        return Page(items=(), raw=last_raw)

    def food_price(self, **params: Any) -> Page[FoodPrice]:
        return self._client._page_ex("/openapi/restinfo/restMenuList", params, _food_price)

    def fuel_prices(
        self,
        *,
        route_name: str | None = None,
        direction: str | None = None,
        oil_company: str | None = None,
        service_area_name: str | None = None,
        route_code: str | None = None,
        service_area_code: str | None = None,
        num_of_rows: int = 1000,
        page_no: int = 1,
    ) -> Page[RestAreaFuelPrice]:
        return self._client._page_ex(
            "/openapi/business/curStateStation",
            {
                "routeName": route_name,
                "direction": direction,
                "oilCompany": oil_company,
                "serviceAreaName": service_area_name,
                "routeCode": route_code,
                "serviceAreaCode": service_area_code,
                "numOfRows": num_of_rows,
                "pageNo": page_no,
            },
            _rest_area_fuel_price,
        )

    def convenience_facilities(
        self,
        *,
        direction: str | None = None,
        service_area_name: str | None = None,
        route_code: str | None = None,
        service_area_code: str | None = None,
        num_of_rows: int = 1000,
        page_no: int = 1,
    ) -> Page[dict[str, Any]]:
        return self._client._page_ex(
            "/openapi/business/conveniServiceArea",
            {
                "direction": direction,
                "serviceAreaName": service_area_name,
                "routeCode": route_code,
                "serviceAreaCode": service_area_code,
                "numOfRows": num_of_rows,
                "pageNo": page_no,
            },
            dict,
        )

    def parking(self, **params: Any) -> Page[dict[str, Any]]:
        return self._client._page_ex("/openapi/restinfo/restParking", params, dict)

    def wifi(self, **params: Any) -> Page[dict[str, Any]]:
        return self._client._page_ex("/openapi/restinfo/restWifi", params, dict)

    def restroom(self, **params: Any) -> Page[dict[str, Any]]:
        return self._client._page_ex("/openapi/restinfo/restRestroom", params, dict)

    def disabled_facility(self, **params: Any) -> Page[dict[str, Any]]:
        return self._client._page_ex("/openapi/restinfo/restDisabled", params, dict)

    def bus_transit(self, **params: Any) -> Page[dict[str, Any]]:
        return self._client._page_ex("/openapi/restinfo/restBus", params, dict)


@dataclass(frozen=True, slots=True)
class FacilityService:
    _client: KrexClient

    def tollgate_info(self, **params: Any) -> Page[dict[str, Any]]:
        return self._client._page_go(
            "https://apis.data.go.kr/B552061/TollgateInfoService/getTollgateInfo",
            params,
            dict,
        )

    def drowsy_shelter(self, **params: Any) -> Page[dict[str, Any]]:
        return self._client._page_ex("/openapi/restinfo/drowsyShelter", params, dict)

    def shoulder_lane(self, **params: Any) -> Page[dict[str, Any]]:
        return self._client._page_go(
            "https://apis.data.go.kr/B552061/ShoulderLaneService/getShoulderLane",
            params,
            dict,
        )


@dataclass(frozen=True, slots=True)
class AdminService:
    _client: KrexClient

    def procurement_contracts(self, **params: Any) -> Page[dict[str, Any]]:
        return self._client._page_go(
            "https://apis.data.go.kr/B552061/ProcurementContractService/getContracts",
            params,
            dict,
        )


@dataclass(frozen=True, slots=True)
class ReferenceService:
    _client: KrexClient

    def api_catalog(
        self,
        *,
        provider: str | None = None,
        namespace: str | None = None,
    ) -> tuple[ApiCatalogItem, ...]:
        return get_api_catalog(provider=provider, namespace=namespace)

    def routes(self) -> tuple[Route, ...]:
        return tuple(
            Route(route_no=code, route_name=name, short_name=name.replace("고속도로", "선"))
            for code, name in ROUTE_NAMES.items()
        )

    def common_codes(self) -> dict[str, dict[str, str]]:
        return {
            "car_type": {item.value: item.label for item in CarType},
            "tcs_type": {item.value: item.label for item in TCSType},
            "road_operator": {item.value: item.label for item in RoadOperator},
            "in_out": {item.value: item.label for item in IOType},
            "time_unit": {item.value: item.label for item in TimeUnit},
            "direction": {item.value: item.label for item in Direction},
            "congestion": {item.value: item.label for item in CongestionLevel},
            "discount": {item.value: item.label for item in DiscountType},
        }


def _parse_page(payload: NormalizedPayload, parser: Callable[[dict[str, Any]], T]) -> Page[T]:
    parsed = []
    for row in payload.items:
        try:
            parsed.append(parser(row))
        except (KeyError, TypeError, ValueError) as exc:
            raise KrexParseError(f"failed to parse response record: {exc}", response=row) from exc
    return Page(
        items=tuple(parsed),
        page_no=payload.page_no,
        num_of_rows=payload.num_of_rows,
        total_count=payload.total_count,
        raw=payload.raw,
    )


def _traffic_by_ic(row: dict[str, Any]) -> TrafficByIc:
    return TrafficByIc(
        collected_date=to_date_or_none(_get(row, "stdDate", "collectedDate", "sumDate")),
        collected_time=strip_or_none(_get(row, "stdTime", "collectedTime", "sumTm")),
        unit_code=str(_required(row, "unitCode")).strip(),
        unit_name=strip_or_none(_get(row, "unitName")),
        in_out=_enum_or_none(IOType, _get(row, "inOutType", "inoutType")),
        tcs_type=_enum_or_none(TCSType, _get(row, "tcsType")),
        car_type=_enum_or_none(CarType, _get(row, "carType")),
        traffic_volume=to_int_or_none(_get(row, "trafficVol", "trafficVolume", "trafficAmout")),
        raw=row,
    )


def _traffic_flow(row: dict[str, Any]) -> TrafficFlow:
    return TrafficFlow(
        conzone_id=strip_or_none(_get(row, "conzoneId", "conzoneID")),
        conzone_name=strip_or_none(_get(row, "conzoneName")),
        route_no=strip_or_none(_get(row, "routeNo")),
        route_name=strip_or_none(_get(row, "routeName")),
        direction=_enum_or_none(Direction, _get(row, "dirType", "directionCode")),
        speed=to_float_or_none(_get(row, "speed", "avgSpeed")),
        free_flow_speed=to_float_or_none(_get(row, "tmFreeFlow", "freeFlowSpeed")),
        congestion_level=_enum_or_none(
            CongestionLevel,
            _get(row, "congestionLevel", "conzoneGrade"),
        ),
        updated_at=strip_or_none(_get(row, "updTime", "updateTime", "updatedAt")),
        raw=row,
    )


def _incident(row: dict[str, Any]) -> Incident:
    return Incident(
        route_no=strip_or_none(_get(row, "routeNo")),
        route_name=strip_or_none(_get(row, "routeName")),
        direction=_enum_or_none(Direction, _get(row, "dirType", "directionCode")),
        incident_type=strip_or_none(_get(row, "incidentType", "eventType")),
        message=strip_or_none(_get(row, "message", "contents", "incidentContent")),
        started_at=strip_or_none(_get(row, "startDate", "startTime")),
        ended_at=strip_or_none(_get(row, "endDate", "endTime")),
        raw=row,
    )


def _toll_fee(row: dict[str, Any]) -> TollFee:
    return TollFee(
        start_unit_code=str(_required(row, "startUnitCode")),
        start_unit_name=strip_or_none(_get(row, "startUnitName")),
        end_unit_code=str(_required(row, "endUnitCode")),
        end_unit_name=strip_or_none(_get(row, "endUnitName")),
        car_type=_enum_or_none(CarType, _get(row, "carType")),
        discount_type=_enum_or_none(DiscountType, _get(row, "discountType")),
        route_count=to_int_or_none(_get(row, "routeCount")),
        total_length_km=to_float_or_none(_get(row, "totalLength", "totalLengthKm")),
        travel_time_min=to_int_or_none(_get(row, "travelTime", "travelTimeMin")),
        toll_fee=to_int_or_none(_get(row, "tollFee")),
        toll_fee_night=to_int_or_none(_get(row, "tollFeeNight")),
        toll_fee_rush=to_int_or_none(_get(row, "tollFeeRush")),
        raw=row,
    )


def _tollgate(row: dict[str, Any]) -> Tollgate:
    x = to_float_or_none(_get(row, "xValue", "x"))
    y = to_float_or_none(_get(row, "yValue", "y"))
    raw_coordinate = _raw_coordinate(x, y)
    return Tollgate(
        unit_code=str(_required(row, "unitCode")),
        unit_name=str(_required(row, "unitName")),
        route_no=strip_or_none(_get(row, "routeNo")),
        route_name=strip_or_none(_get(row, "routeName")),
        ex_div_code=strip_or_none(_get(row, "exDivCode")),
        x=x,
        y=y,
        head_office_code=strip_or_none(_get(row, "headOfficeCode")),
        branch_office_code=strip_or_none(_get(row, "branchOfficeCode")),
        raw=row,
        coordinate=_place_coordinate_from_row(row) or _place_coordinate_from_xy(x, y),
        raw_coordinate=raw_coordinate,
    )


def _rest_area(row: dict[str, Any]) -> RestArea:
    coordinate = _place_coordinate_from_row(row)
    return RestArea(
        name=str(_required(row, "restAreaNm", "serviceAreaName")),
        route_name=strip_or_none(_get(row, "routeNm", "routeName")),
        direction=strip_or_none(_get(row, "directionContent", "direction")),
        lat=coordinate.lat if coordinate else to_float_or_none(_get(row, "lcLatitude", "latitude")),
        lon=(
            coordinate.lon
            if coordinate
            else to_float_or_none(_get(row, "lcLongitude", "longitude"))
        ),
        has_gas_station=to_bool_yn(_get(row, "gasStnYn")),
        has_lpg_station=to_bool_yn(_get(row, "lpgStnYn")),
        has_ev_charger=to_bool_yn(_get(row, "evChargYn")),
        phone_number=strip_or_none(_get(row, "phoneNumber", "tel")),
        reference_date=to_date_or_none(_get(row, "referenceDate")),
        raw=row,
        coordinate=coordinate,
    )


def _rest_area_route_facility(row: dict[str, Any]) -> RestAreaRouteFacility:
    return RestAreaRouteFacility(
        route_code=strip_or_none(_get(row, "routeCode")),
        service_area_code=str(_required(row, "serviceAreaCode")),
        service_area_code2=strip_or_none(_get(row, "serviceAreaCode2")),
        route_name=strip_or_none(_get(row, "routeName")),
        direction=strip_or_none(_get(row, "direction")),
        service_area_name=strip_or_none(_get(row, "serviceAreaName")),
        phone_number=strip_or_none(_get(row, "telNo", "phoneNumber", "tel")),
        address=Address.from_mapping(row),
        brand=strip_or_none(_get(row, "brand")),
        convenience=strip_or_none(_get(row, "convenience")),
        has_maintenance=to_bool_yn(_get(row, "maintenanceYn")),
        is_truck_rest_area=to_bool_yn(_get(row, "truckSaYn")),
        representative_food=strip_or_none(_get(row, "batchMenu", "representativeFood")),
        raw=row,
    )


def _rest_area_fuel_price(row: dict[str, Any]) -> RestAreaFuelPrice:
    return RestAreaFuelPrice(
        route_code=strip_or_none(_get(row, "routeCode")),
        service_area_code=str(_required(row, "serviceAreaCode")),
        service_area_code2=strip_or_none(_get(row, "serviceAreaCode2")),
        route_name=strip_or_none(_get(row, "routeName")),
        direction=strip_or_none(_get(row, "direction")),
        oil_company=strip_or_none(_get(row, "oilCompany")),
        has_lpg=to_bool_yn(_get(row, "lpgYn")),
        service_area_name=strip_or_none(_get(row, "serviceAreaName")),
        phone_number=strip_or_none(_get(row, "telNo", "phoneNumber", "tel")),
        address=Address.from_mapping(row),
        gasoline_price=to_int_or_none(_get(row, "gasolinePrice")),
        diesel_price=to_int_or_none(_get(row, "diselPrice", "dieselPrice")),
        lpg_price=to_int_or_none(_get(row, "lpgPrice")),
        raw=row,
    )


def _rest_area_weather(row: dict[str, Any]) -> RestAreaWeather:
    x = _weather_float_or_none(_get(row, "xValue", "x"))
    y = _weather_float_or_none(_get(row, "yValue", "y"))
    coordinate = _place_coordinate_from_xy(x, y)
    return RestAreaWeather(
        observed_at=_parse_rest_area_weather_observed_at(
            _required(row, "sdate"),
            _required(row, "stdHour"),
        ),
        sdate=_format_sdate(_required(row, "sdate")),
        std_hour=_format_hour(_required(row, "stdHour")),
        unit_code=str(_required(row, "unitCode")).strip(),
        unit_name=str(_required(row, "unitName")).strip(),
        route_no=strip_or_none(_get(row, "routeNo")),
        route_name=strip_or_none(_get(row, "routeName")),
        direction_code=strip_or_none(_get(row, "updownTypeCode", "directionCode")),
        lat=coordinate.lat if coordinate else None,
        lon=coordinate.lon if coordinate else None,
        address=Address.from_mapping(row),
        measurement_station=strip_or_none(_get(row, "measurement", "measurementStation")),
        weather=strip_or_none(_get(row, "weatherContents", "weather")),
        temperature=_weather_float_or_none(_get(row, "tempValue", "temperature")),
        humidity=_weather_float_or_none(_get(row, "humidityValue", "humidity")),
        wind_speed=_weather_float_or_none(_get(row, "windValue", "windSpeed")),
        wind_direction_code=strip_or_none(_get(row, "windContents", "windDirectionCode")),
        rainfall=_weather_float_or_none(_get(row, "rainfallValue", "rainfall")),
        rainfall_strength=_weather_float_or_none(
            _get(row, "rainfallstrengthValue", "rainfallStrengthValue", "rainfallStrength"),
        ),
        new_snow=_weather_float_or_none(_get(row, "newsnowValue", "newSnow")),
        snow=_weather_float_or_none(_get(row, "snowValue", "snow")),
        cloud=_weather_float_or_none(_get(row, "cloudValue", "cloud")),
        dew_point=_weather_float_or_none(_get(row, "dewValue", "dewPoint")),
        raw=row,
        coordinate=coordinate,
        raw_coordinate=_raw_coordinate(x, y),
    )


def _food_price(row: dict[str, Any]) -> FoodPrice:
    return FoodPrice(
        service_area_code=strip_or_none(_get(row, "serviceAreaCode")),
        service_area_name=strip_or_none(_get(row, "serviceAreaName")),
        store_code=strip_or_none(_get(row, "storeCode")),
        store_name=strip_or_none(_get(row, "storeName")),
        food_code=strip_or_none(_get(row, "foodCode")),
        food_name=str(_required(row, "foodName")),
        price=to_int_or_none(_get(row, "price")),
        is_recommended=to_bool_yn(_get(row, "recommendYn")),
        raw=row,
    )


def _clean(params: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in params.items() if value is not None}


def _require(value: str | None, field: str) -> None:
    if not value:
        raise KrexInvalidParameterError(f"{field} must not be empty")


def _as_kst(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=KST)
    return value.astimezone(KST)


def _format_sdate(value: Any) -> str:
    if isinstance(value, datetime):
        return _as_kst(value).strftime("%Y%m%d")
    if isinstance(value, date):
        return value.strftime("%Y%m%d")
    text = str(value).strip()
    if len(text) != 8 or not text.isdigit():
        raise ValueError("sdate must be YYYYMMDD")
    return text


def _format_hour(value: Any) -> str:
    text = str(value).strip()
    if text == "":
        raise ValueError("std_hour must not be empty")
    hour = int(text)
    if not 0 <= hour <= 23:
        raise ValueError("std_hour must be between 0 and 23")
    return f"{hour:02d}"


def _parse_rest_area_weather_observed_at(sdate: Any, std_hour: Any) -> datetime:
    raw = f"{_format_sdate(sdate)}{_format_hour(std_hour)}"
    return datetime.strptime(raw, "%Y%m%d%H").replace(tzinfo=KST)


def _weather_float_or_none(value: Any) -> float | None:
    try:
        number = to_float_or_none(value)
    except ValueError:
        return None
    if number is None or number <= -99.0:
        return None
    return number


def _optional_code(enum_type: type[E], value: E | str | None, field: str) -> str | None:
    if value is None:
        return None
    return coerce_code(enum_type, value, field)


def _enum_or_none(enum_type: type[T], value: Any) -> T | None:
    text = strip_or_none(value)
    if text is None:
        return None
    return enum_type(text)  # type: ignore[call-arg]


def _get(row: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in row:
            return row[name]
    return None


def _required(row: dict[str, Any], *names: str) -> Any:
    value = _get(row, *names)
    if strip_or_none(value) is None:
        joined = "/".join(names)
        raise ValueError(f"{joined} is required")
    return value


def _place_coordinate_from_row(row: dict[str, Any]) -> PlaceCoordinate | None:
    try:
        coordinate = PlaceCoordinate.from_mapping(row)
    except ValueError:
        coordinate = None
    if coordinate is not None:
        return coordinate
    lon = to_float_or_none(_get(row, "lon", "longitude", "lng", "lcLongitude", "경도", "xcoord"))
    lat = to_float_or_none(_get(row, "lat", "latitude", "lcLatitude", "위도", "ycoord"))
    if lon is None or lat is None:
        return None
    return _place_coordinate_from_lon_lat(lon, lat)


def _place_coordinate_from_xy(x: float | None, y: float | None) -> PlaceCoordinate | None:
    if x is None or y is None:
        return None
    return _place_coordinate_from_lon_lat(x, y)


def _place_coordinate_from_lon_lat(lon: float, lat: float) -> PlaceCoordinate | None:
    if 124 <= lon <= 132 and 33 <= lat <= 39:
        return PlaceCoordinate(lat=lat, lon=lon)
    return None


def _raw_coordinate(x: float | None, y: float | None) -> RawCoordinate | None:
    if x is None or y is None:
        return None
    system = (
        CoordinateSystem.WGS84
        if _place_coordinate_from_xy(x, y) is not None
        else CoordinateSystem.UNKNOWN
    )
    return RawCoordinate(x=x, y=y, system=system)
