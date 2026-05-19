from __future__ import annotations

import asyncio
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest

from krex import (
    Address,
    AsyncKrexClient,
    CarType,
    CongestionLevel,
    CoordinateSystem,
    Direction,
    KrexAuthError,
    KrexClient,
    KrexInvalidParameterError,
    KrexNotFoundError,
    KrexParseError,
    PlaceCoordinate,
    RestAreaWeather,
    RoadOperator,
    TCSType,
    TimeUnit,
)


class FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeSession:
    def __init__(self, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    @property
    def last_params(self) -> dict[str, Any]:
        return self.calls[-1]["params"]

    @property
    def last_url(self) -> str:
        return self.calls[-1]["url"]

    def get(self, url: str, *, params: dict[str, Any], timeout: float) -> FakeResponse:
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        if isinstance(self.payload, list):
            index = min(len(self.calls) - 1, len(self.payload) - 1)
            return FakeResponse(self.payload[index])
        return FakeResponse(self.payload)


def ex_payload(items: Any) -> dict[str, Any]:
    return {"code": "SUCCESS", "pageNo": "1", "numOfRows": "1000", "count": "1", "list": items}


def go_payload(items: Any) -> dict[str, Any]:
    return {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
            "body": {"items": {"item": items}, "pageNo": "1", "numOfRows": "10", "totalCount": "1"},
        }
    }


def test_client_loads_local_dotenv_keys_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("KEX_EX_API_KEY", raising=False)
    monkeypatch.delenv("KEX_GO_API_KEY", raising=False)
    (tmp_path / ".env").write_text(
        "KEX_EX_API_KEY= ex key \nKEX_GO_API_KEY=' go key '\n",
        encoding="utf-8",
    )

    client = KrexClient(retry_backoff=0, session=FakeSession(ex_payload([])))

    assert client.ex_api_key == "exkey"
    assert client.go_api_key == "gokey"


def test_explicit_client_keys_are_normalized_before_env_fallback(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("KEX_EX_API_KEY=env-key\n", encoding="utf-8")

    client = KrexClient(ex_api_key=" pasted \r\n key ", session=FakeSession(ex_payload([])))

    assert client.ex_api_key == "pastedkey"


def test_aio_client_matches_sync_service_shape() -> None:
    session = FakeSession(ex_payload([{"conzoneId": "0010CZE010", "speed": "87.5"}]))
    client = KrexClient.aio(ex_api_key="ex-key", retry_backoff=0, session=session)

    page = asyncio.run(client.traffic.flow(route_no="0010"))

    assert isinstance(client, AsyncKrexClient)
    assert page.items[0].conzone_id == "0010CZE010"
    assert session.last_url.endswith("/openapi/trafficapi/realFlow")


def rest_weather_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "sdate": "20210507",
        "stdHour": "12",
        "unitCode": "002 ",
        "unitName": "죽전휴게소",
        "routeNo": "0010",
        "routeName": "경부선",
        "updownTypeCode": "E",
        "xValue": "127.104165",
        "yValue": "37.332651",
        "addr": "경기도 용인시 수지구 풍덕천동 42-1",
        "measurement": "연천",
        "weatherContents": "비끝남",
        "tempValue": "14.500000",
        "humidityValue": "66.000000",
        "windValue": "4.400000",
        "windContents": "23",
        "rainfallValue": "8.900000",
        "rainfallstrengthValue": "-99.000000",
        "newsnowValue": "-99.000000",
        "snowValue": "-99.000000",
        "cloudValue": "9.000000",
        "dewValue": "8.200000",
    }
    row.update(overrides)
    return row


def test_traffic_by_ic_builds_query_and_parses_types() -> None:
    session = FakeSession(
        ex_payload(
            [
                {
                    "stdDate": "20260430",
                    "stdTime": "1400",
                    "unitCode": "101",
                    "unitName": "서울",
                    "inoutType": "0",
                    "tcsType": "2",
                    "carType": "1",
                    "trafficAmout": "1,234",
                    "sumTm": "1400",
                    "sumDate": "20260430",
                }
            ]
        )
    )
    client = KrexClient(ex_api_key="ex-key", retry_backoff=0, session=session)

    page = client.traffic.by_ic(
        ex_div_code=RoadOperator.KEC,
        unit_code="101",
        in_out="0",
        time_unit=TimeUnit.HOUR,
        tcs_type=TCSType.HIPASS,
        car_type=CarType.LIGHT,
    )

    assert session.last_url.endswith("/openapi/trafficapi/trafficIc")
    assert session.last_params["exDivCode"] == "00"
    assert session.last_params["inOutType"] == "0"
    assert session.last_params["tmType"] == "1"
    assert session.last_params["tcsType"] == "2"
    assert page.total_count == 1
    item = page.items[0]
    assert item.collected_date == date(2026, 4, 30)
    assert item.in_out is not None
    assert item.tcs_type is TCSType.HIPASS
    assert item.car_type is CarType.LIGHT
    assert item.traffic_volume == 1234


def test_traffic_flow_accepts_single_dict_response() -> None:
    session = FakeSession(
        ex_payload(
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
        )
    )
    client = KrexClient(ex_api_key="ex-key", retry_backoff=0, session=session)

    page = client.traffic.flow(route_no="0010", direction=Direction.UP)

    assert session.last_params["routeNo"] == "0010"
    assert session.last_params["dirType"] == "0"
    flow = page.items[0]
    assert flow.congestion_level is CongestionLevel.SMOOTH
    assert flow.speed == pytest.approx(87.5)
    assert flow.free_flow_speed == pytest.approx(100.0)


def test_tollfee_between_tollgates_parses_money_and_distance() -> None:
    session = FakeSession(
        ex_payload(
            [
                {
                    "startUnitCode": "101",
                    "startUnitName": "서울",
                    "endUnitCode": "105",
                    "endUnitName": "수원",
                    "carType": "1",
                    "discountType": "0",
                    "routeCount": "1",
                    "totalLength": "31.2",
                    "travelTime": "28",
                    "tollFee": "2,300",
                    "tollFeeNight": "1,800",
                    "tollFeeRush": "2,100",
                }
            ]
        )
    )
    client = KrexClient(ex_api_key="ex-key", retry_backoff=0, session=session)

    page = client.tollfee.between_tollgates(
        start_unit_code="101",
        end_unit_code="105",
        car_type="1",
    )

    assert session.last_params["startUnitCode"] == "101"
    assert session.last_params["endUnitCode"] == "105"
    assert page.items[0].total_length_km == pytest.approx(31.2)
    assert page.items[0].toll_fee == 2300


def test_tollgate_list_preserves_code_strings() -> None:
    session = FakeSession(
        ex_payload(
            [
                {
                    "unitCode": "007",
                    "unitName": "테스트TG",
                    "routeNo": "0010",
                    "routeName": "경부고속도로",
                    "xValue": "127.1",
                    "yValue": "37.2",
                }
            ]
        )
    )
    client = KrexClient(ex_api_key="ex-key", retry_backoff=0, session=session)

    tollgate = client.tollfee.tollgate_list().items[0]

    assert tollgate.unit_code == "007"
    assert tollgate.x == pytest.approx(127.1)
    assert tollgate.coordinate is not None
    assert isinstance(tollgate.coordinate, PlaceCoordinate)
    assert tollgate.coordinate.lonlat == pytest.approx((127.1, 37.2))
    assert tollgate.raw_coordinate is not None
    assert tollgate.raw_coordinate.system is CoordinateSystem.WGS84


def test_restarea_standard_data_uses_go_key_and_parses_bool() -> None:
    session = FakeSession(
        go_payload(
            [
                {
                    "restAreaNm": "죽전휴게소",
                    "routeNm": "경부고속도로",
                    "directionContent": "서울방향",
                    "lcLatitude": "37.332",
                    "lcLongitude": "127.104",
                    "gasStnYn": "Y",
                    "lpgStnYn": "N",
                    "evChargYn": "Y",
                    "phoneNumber": "031-000-0000",
                    "referenceDate": "2026-04-30",
                }
            ]
        )
    )
    client = KrexClient(go_api_key="go-key", retry_backoff=0, session=session)

    rest_area = client.restarea.list_all(route_name="경부고속도로").items[0]

    assert session.last_url == "https://api.data.go.kr/openapi/tn_pubr_public_rest_area_api"
    assert session.last_params["serviceKey"] == "go-key"
    assert session.last_params["type"] == "json"
    assert "_type" not in session.last_params
    assert rest_area.name == "죽전휴게소"
    assert rest_area.has_gas_station is True
    assert rest_area.has_lpg_station is False
    assert rest_area.reference_date == date(2026, 4, 30)
    assert rest_area.coordinate is not None
    assert isinstance(rest_area.coordinate, PlaceCoordinate)
    assert rest_area.coordinate.lonlat == pytest.approx((127.104, 37.332))


def test_restarea_weather_builds_query_and_parses_typed_rows() -> None:
    session = FakeSession(ex_payload([rest_weather_row()]))
    client = KrexClient(ex_api_key="road-key", retry_backoff=0, session=session)

    page = client.restarea.weather(sdate="20210507", std_hour=12)

    assert session.last_url.endswith("/openapi/restinfo/restWeatherList")
    assert session.last_params["key"] == "road-key"
    assert session.last_params["sdate"] == "20210507"
    assert session.last_params["stdHour"] == "12"
    item = page.items[0]
    assert isinstance(item, RestAreaWeather)
    assert item.observed_at.isoformat() == "2021-05-07T12:00:00+09:00"
    assert item.unit_code == "002"
    assert item.unit_name == "죽전휴게소"
    assert item.route_no == "0010"
    assert item.route_name == "경부선"
    assert isinstance(item.address, Address)
    assert item.address.display_address == "경기도 용인시 수지구 풍덕천동 42-1"
    assert item.address.effective_region is not None
    assert item.address.effective_region.sido_name == "경기도"
    assert item.address.effective_region.sigungu_name == "용인시 수지구"
    assert item.address.effective_region.eup_myeon_dong_name == "풍덕천동"
    assert item.address.legal_dong_code is None
    assert item.weather == "비끝남"
    assert item.temperature == 14.5
    assert item.humidity == 66.0
    assert item.wind_speed == 4.4
    assert item.rainfall == 8.9
    assert item.rainfall_strength is None
    assert item.new_snow is None
    assert item.snow is None
    assert item.coordinate is not None
    assert isinstance(item.coordinate, PlaceCoordinate)
    assert item.coordinate.lonlat == pytest.approx((127.104165, 37.332651))
    assert item.longitude == pytest.approx(127.104165)
    assert item.latitude == pytest.approx(37.332651)
    assert item.raw["xValue"] == "127.104165"


def test_restarea_weather_accepts_single_object_and_missing_sentinel() -> None:
    session = FakeSession(
        ex_payload(rest_weather_row(xValue="-99.000000", yValue="-99.000000"))
    )
    client = KrexClient(ex_api_key="road-key", retry_backoff=0, session=session)

    item = client.restarea.weather(sdate="20210507", std_hour="12").items[0]

    assert item.coordinate is None
    assert item.raw_coordinate is None
    assert item.longitude is None
    assert item.latitude is None


def test_restarea_latest_weather_looks_back_until_non_empty() -> None:
    session = FakeSession([ex_payload([]), ex_payload([rest_weather_row(stdHour="11")])])
    client = KrexClient(ex_api_key="road-key", retry_backoff=0, session=session)

    page = client.restarea.latest_weather(
        when=datetime(2021, 5, 7, 12, 30),
        lookback_hours=2,
    )

    assert page.items[0].std_hour == "11"
    assert session.calls[0]["params"]["stdHour"] == "12"
    assert session.calls[1]["params"]["stdHour"] == "11"


def test_restarea_weather_validates_date_and_hour() -> None:
    client = KrexClient(ex_api_key="road-key", retry_backoff=0, session=FakeSession(ex_payload([])))

    with pytest.raises(ValueError):
        client.restarea.weather(sdate="2021-05-07", std_hour=12)
    with pytest.raises(ValueError):
        client.restarea.weather(sdate="20210507", std_hour=24)
    with pytest.raises(ValueError):
        client.restarea.latest_weather(lookback_hours=-1)


def test_restarea_weather_error_code_and_shape_errors() -> None:
    auth_client = KrexClient(
        ex_api_key="bad-key",
        retry_backoff=0,
        session=FakeSession(
            {"code": "INVALID_KEY", "message": "인증키가 유효하지 않습니다.", "list": None}
        ),
    )
    shape_client = KrexClient(
        ex_api_key="road-key",
        retry_backoff=0,
        session=FakeSession({"code": "SUCCESS", "list": "bad"}),
    )

    with pytest.raises(KrexAuthError) as raised:
        auth_client.restarea.weather(sdate="20210507", std_hour=12)
    assert "bad-key" not in str(raised.value)
    with pytest.raises(KrexParseError):
        shape_client.restarea.weather(sdate="20210507", std_hour=12)


def test_restarea_route_facilities_parse_service_area_master_fields() -> None:
    session = FakeSession(
        ex_payload(
            {
                "routeCode": "0010",
                "serviceAreaCode": "A0001",
                "routeName": "경부고속도로",
                "direction": "서울",
                "serviceAreaName": "죽전휴게소",
                "telNo": "031-000-0000",
                "serviceAreaCode2": "000139",
                "svarAddr": "경기 용인시 수지구",
                "ADM_CD": "4146510100",
                "brand": "투썸플레이스",
                "convenience": "수유실|쉼터",
                "maintenanceYn": "X",
                "truckSaYn": "N",
                "batchMenu": "죽전라면",
            }
        )
    )
    client = KrexClient(ex_api_key="ex-key", retry_backoff=0, session=session)

    facility = client.restarea.route_facilities(
        route_code="0010",
        service_area_code="A0001",
    ).items[0]

    assert session.last_url.endswith("/openapi/business/serviceAreaRoute")
    assert session.last_params["routeCode"] == "0010"
    assert session.last_params["serviceAreaCode"] == "A0001"
    assert facility.service_area_code == "A0001"
    assert facility.service_area_code2 == "000139"
    assert facility.service_area_name == "죽전휴게소"
    assert facility.address is not None
    assert facility.address.display_address == "경기 용인시 수지구"
    assert facility.address.effective_region is not None
    assert facility.address.effective_region.sido_name == "경기도"
    assert facility.address.effective_region.sigungu_name == "용인시 수지구"
    assert facility.address.legal_dong_code == "4146510100"
    assert facility.address.sigungu_code == "41465"
    assert facility.brand == "투썸플레이스"
    assert facility.convenience == "수유실|쉼터"
    assert facility.has_maintenance is False
    assert facility.is_truck_rest_area is False
    assert facility.representative_food == "죽전라면"


def test_restarea_fuel_prices_parse_money_and_lpg_flag() -> None:
    session = FakeSession(
        ex_payload(
            [
                {
                    "routeCode": "0010",
                    "serviceAreaCode": "A0001",
                    "routeName": "경부고속도로",
                    "direction": "서울",
                    "oilCompany": "EX-OIL",
                    "lpgYn": "Y",
                    "serviceAreaName": "죽전휴게소",
                    "telNo": "031-000-0000",
                    "serviceAreaCode2": "000139",
                    "svarAddr": "경기 용인시 수지구",
                    "gasolinePrice": "1,710원",
                    "diselPrice": "1,599원",
                    "lpgPrice": "1,010원",
                }
            ]
        )
    )
    client = KrexClient(ex_api_key="ex-key", retry_backoff=0, session=session)

    fuel = client.restarea.fuel_prices(oil_company="EX-OIL").items[0]

    assert session.last_url.endswith("/openapi/business/curStateStation")
    assert session.last_params["oilCompany"] == "EX-OIL"
    assert fuel.service_area_code == "A0001"
    assert fuel.service_area_code2 == "000139"
    assert fuel.oil_company == "EX-OIL"
    assert fuel.has_lpg is True
    assert fuel.address is not None
    assert fuel.address.display_address == "경기 용인시 수지구"
    assert fuel.address.effective_region is not None
    assert fuel.address.effective_region.sido_name == "경기도"
    assert fuel.address.effective_region.sigungu_name == "용인시 수지구"
    assert fuel.gasoline_price == 1710
    assert fuel.diesel_price == 1599
    assert fuel.lpg_price == 1010


def test_restarea_convenience_facilities_stays_raw_until_schema_is_verified() -> None:
    session = FakeSession(ex_payload([{"serviceAreaCode": "A0001", "unknownFacility": "Y"}]))
    client = KrexClient(ex_api_key="ex-key", retry_backoff=0, session=session)

    page = client.restarea.convenience_facilities(service_area_name="죽전휴게소")

    assert session.last_url.endswith("/openapi/business/conveniServiceArea")
    assert session.last_params["serviceAreaName"] == "죽전휴게소"
    assert page.items[0] == {"serviceAreaCode": "A0001", "unknownFacility": "Y"}


def test_food_price_parses_recommend_flag() -> None:
    session = FakeSession(
        ex_payload(
            {
                "serviceAreaCode": "A001",
                "serviceAreaName": "죽전",
                "storeName": "푸드코트",
                "foodName": "우동",
                "price": "7,000",
                "recommendYn": "Y",
            }
        )
    )
    client = KrexClient(ex_api_key="ex-key", retry_backoff=0, session=session)

    food = client.restarea.food_price().items[0]

    assert food.food_name == "우동"
    assert food.price == 7000
    assert food.is_recommended is True


def test_no_data_can_return_empty_page_when_configured() -> None:
    session = FakeSession({"code": "NO_DATA", "message": "empty"})
    client = KrexClient(ex_api_key="ex-key", retry_backoff=0, strict_no_data=False, session=session)

    page = client.traffic.flow(route_no="9999")

    assert page.items == ()


def test_no_data_raises_by_default() -> None:
    session = FakeSession({"code": "NO_DATA", "message": "empty"})
    client = KrexClient(ex_api_key="ex-key", retry_backoff=0, session=session)

    with pytest.raises(KrexNotFoundError):
        client.traffic.flow(route_no="9999")


def test_invalid_public_params_fail_before_http_call() -> None:
    session = FakeSession(ex_payload([]))
    client = KrexClient(ex_api_key="ex-key", retry_backoff=0, session=session)

    with pytest.raises(KrexInvalidParameterError):
        client.tollfee.between_tollgates(start_unit_code="", end_unit_code="105", car_type="1")
    with pytest.raises(KrexInvalidParameterError):
        client.traffic.by_ic(
            ex_div_code="00",
            unit_code="101",
            in_out="0",
            time_unit="9",
            tcs_type="2",
            car_type="1",
        )
    assert session.calls == []


def test_malformed_model_record_raises_parse_error() -> None:
    session = FakeSession(ex_payload([{"unitName": "missing unit code"}]))
    client = KrexClient(ex_api_key="ex-key", retry_backoff=0, session=session)

    with pytest.raises(KrexParseError):
        client.tollfee.tollgate_list()


def test_reference_codes_are_local_and_preserve_leading_zero_routes() -> None:
    client = KrexClient(ex_api_key="unused")

    routes = client.reference.routes()
    codes = client.reference.common_codes()

    assert routes[0].route_no == "0010"
    assert codes["car_type"]["1"] == "1종"


def test_raw_and_generic_namespaces_build_expected_urls() -> None:
    session = FakeSession(ex_payload([{"any": "value"}]))
    client = KrexClient(ex_api_key="ex-key", go_api_key="go-key", retry_backoff=0, session=session)

    assert client.traffic.by_route(route_no="0010", time_unit="1").items[0] == {"any": "value"}
    assert session.last_url.endswith("/openapi/trafficapi/trafficRoute")

    client.traffic.vds_raw(vdsId="V001")
    assert session.last_url.endswith("/openapi/trafficapi/vdsRaw")

    client.traffic.avc_raw(vds_id="V001", std_date="20260430")
    assert session.last_params["vdsId"] == "V001"
    assert session.last_url.endswith("/openapi/trafficapi/avcRaw")

    client.restarea.parking(serviceAreaName="죽전")
    assert session.last_url.endswith("/openapi/restinfo/restParking")

    client.restarea.wifi()
    assert session.last_url.endswith("/openapi/restinfo/restWifi")

    client.restarea.restroom()
    assert session.last_url.endswith("/openapi/restinfo/restRestroom")

    client.restarea.disabled_facility()
    assert session.last_url.endswith("/openapi/restinfo/restDisabled")

    client.restarea.bus_transit()
    assert session.last_url.endswith("/openapi/restinfo/restBus")

    client.facility.drowsy_shelter()
    assert session.last_url.endswith("/openapi/restinfo/drowsyShelter")


def test_data_go_generic_namespaces_build_expected_urls() -> None:
    session = FakeSession(go_payload([{"any": "value"}]))
    client = KrexClient(go_api_key="go-key", retry_backoff=0, session=session)

    client.facility.tollgate_info()
    assert session.last_url.endswith("/TollgateInfoService/getTollgateInfo")
    assert session.last_params["_type"] == "json"

    client.facility.shoulder_lane()
    assert session.last_url.endswith("/ShoulderLaneService/getShoulderLane")

    client.admin.procurement_contracts()
    assert session.last_url.endswith("/ProcurementContractService/getContracts")
