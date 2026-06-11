"""python-krex-api가 반환하는 공개 Pydantic 모델."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from .codes import (
    CarType,
    CongestionLevel,
    CoordinateSystem,
    Direction,
    DiscountType,
    IOType,
    TCSType,
)

T = TypeVar("T")


class KrexModel(BaseModel):
    """불변 공개 응답 모델의 공통 기반 클래스."""

    model_config = ConfigDict(frozen=True, use_enum_values=False)


class Page(KrexModel, Generic[T]):
    items: tuple[T, ...]
    page_no: int | None = None
    num_of_rows: int | None = None
    total_count: int | None = None
    raw: dict[str, Any] | None = None

    def __iter__(self) -> Iterator[T]:  # type: ignore[override]
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __bool__(self) -> bool:
        return bool(self.items)

    @property
    def first(self) -> T | None:
        return self.items[0] if self.items else None

    @property
    def is_empty(self) -> bool:
        return not self.items


class ApiCatalogItem(KrexModel):
    function: str
    dataset_name: str
    provider: str
    service_key_url: str | None = None
    endpoint: str | None = None
    method: str = "GET"
    return_type: str
    description: str
    dataset_id: str | None = None
    live_verified: bool | None = None
    fixture_supported: bool = False


class RawCoordinate(KrexModel):
    x: float
    y: float
    system: CoordinateSystem = CoordinateSystem.UNKNOWN


class TrafficByIc(KrexModel):
    collected_date: date | None
    collected_time: str | None
    unit_code: str
    unit_name: str | None
    in_out: IOType | None
    tcs_type: TCSType | None
    car_type: CarType | None
    traffic_volume: int | None
    raw: dict[str, Any]


class TrafficFlow(KrexModel):
    conzone_id: str | None
    conzone_name: str | None
    route_no: str | None
    route_name: str | None
    direction: Direction | None
    speed: float | None
    free_flow_speed: float | None
    congestion_level: CongestionLevel | None
    updated_at: str | None
    raw: dict[str, Any]


class Incident(KrexModel):
    """0611 실시간 문자정보(`/openapi/burstInfo/realTimeSms`) 돌발 row.

    `direction`은 `startEndTypeCode` 키로 오는 "대구방향" 같은 한국어 텍스트라
    `Direction` enum이 아닌 일반 문자열로 둔다.
    """

    occurred_date: str | None
    occurred_time: str | None
    incident_type: str | None
    incident_type_code: str | None
    direction: str | None
    message: str | None
    point_name: str | None
    route_no: str | None
    route_name: str | None
    process_status: str | None
    process_status_code: str | None
    latitude: float | None
    longitude: float | None
    congestion_length: float | None
    series_no: int | None
    raw: dict[str, Any]


class TollFee(KrexModel):
    start_unit_code: str
    start_unit_name: str | None
    end_unit_code: str
    end_unit_name: str | None
    car_type: CarType | None
    discount_type: DiscountType | None
    route_count: int | None
    total_length_km: float | None
    travel_time_min: int | None
    toll_fee: int | None
    toll_fee_night: int | None
    toll_fee_rush: int | None
    raw: dict[str, Any]


class Tollgate(KrexModel):
    unit_code: str
    unit_name: str
    route_no: str | None
    route_name: str | None
    ex_div_code: str | None
    x: float | None
    y: float | None
    head_office_code: str | None
    branch_office_code: str | None
    raw: dict[str, Any]
    raw_coordinate: RawCoordinate | None = None


class RestArea(KrexModel):
    name: str
    route_name: str | None
    direction: str | None
    lat: float | None
    lon: float | None
    has_gas_station: bool | None
    has_lpg_station: bool | None
    has_ev_charger: bool | None
    phone_number: str | None
    reference_date: date | None
    raw: dict[str, Any]


class RestAreaRouteFacility(KrexModel):
    route_code: str | None
    service_area_code: str
    service_area_code2: str | None = None
    route_name: str | None
    direction: str | None
    service_area_name: str | None
    phone_number: str | None
    address: str | None = None
    brand: str | None = None
    convenience: str | None = None
    has_maintenance: bool | None
    is_truck_rest_area: bool | None
    representative_food: str | None
    raw: dict[str, Any]


class RestAreaFuelPrice(KrexModel):
    route_code: str | None
    service_area_code: str
    service_area_code2: str | None = None
    route_name: str | None
    direction: str | None
    oil_company: str | None
    has_lpg: bool | None
    service_area_name: str | None
    phone_number: str | None
    address: str | None = None
    gasoline_price: int | None
    diesel_price: int | None
    lpg_price: int | None
    raw: dict[str, Any]


class RestAreaWeather(KrexModel):
    observed_at: datetime
    sdate: str
    std_hour: str
    unit_code: str
    unit_name: str
    route_no: str | None
    route_name: str | None
    direction_code: str | None
    lat: float | None
    lon: float | None
    address: str | None
    measurement_station: str | None
    weather: str | None
    temperature: float | None
    humidity: float | None
    wind_speed: float | None
    wind_direction_code: str | None
    rainfall: float | None
    rainfall_strength: float | None
    new_snow: float | None
    snow: float | None
    cloud: float | None
    dew_point: float | None
    raw: dict[str, Any]
    raw_coordinate: RawCoordinate | None = None

    @property
    def longitude(self) -> float | None:
        return self.lon

    @property
    def latitude(self) -> float | None:
        return self.lat


class FoodPrice(KrexModel):
    service_area_code: str | None
    service_area_name: str | None
    store_code: str | None
    store_name: str | None
    food_code: str | None
    food_name: str
    price: int | None
    is_recommended: bool | None
    raw: dict[str, Any]


class Route(KrexModel):
    route_no: str
    route_name: str
    short_name: str | None = None
