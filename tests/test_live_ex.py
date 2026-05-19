from __future__ import annotations

import os
from pathlib import Path

import pytest

from krex import CarType, KrexClient, RoadOperator, TCSType, TimeUnit


def _load_local_env() -> None:
    env_file = Path(".env")
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8-sig").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _live_client() -> KrexClient:
    _load_local_env()
    if os.getenv("KEX_LIVE") != "1":
        pytest.skip("set KEX_LIVE=1 to run live data.ex.co.kr tests")
    if not os.getenv("KEX_EX_API_KEY"):
        pytest.skip("KEX_EX_API_KEY is not set")
    return KrexClient.from_env(timeout=10, max_retries=1, retry_backoff=0)


@pytest.mark.live
def test_live_data_ex_traffic_by_ic_parses_real_payload() -> None:
    client = _live_client()

    page = client.traffic.by_ic(
        ex_div_code=RoadOperator.KEC,
        unit_code="101",
        in_out="0",
        time_unit=TimeUnit.HOUR,
        tcs_type=TCSType.HIPASS,
        car_type=CarType.LIGHT,
        num_of_rows=2,
        page_no=1,
    )

    assert page.total_count is not None
    assert page.raw is not None
    assert page.raw["code"] == "SUCCESS"
    assert page.items
    first = page.items[0]
    assert first.unit_code == "101"
    assert first.unit_name
    assert first.collected_date is not None
    assert first.collected_time is not None
    assert first.traffic_volume is not None
    assert first.traffic_volume >= 0


@pytest.mark.live
def test_live_data_ex_traffic_route_accepts_valid_key_even_when_empty() -> None:
    client = _live_client()

    page = client.traffic.by_route(
        route_no="0010",
        time_unit=TimeUnit.HOUR,
        num_of_rows=1,
        page_no=1,
    )

    assert page.raw is not None
    assert page.raw["code"] == "SUCCESS"
    assert page.total_count is not None


@pytest.mark.live
def test_live_restarea_route_facilities_accepts_real_payload_shape() -> None:
    client = _live_client()

    page = client.restarea.route_facilities(num_of_rows=1, page_no=1)

    assert page.raw is not None
    assert page.raw["code"] == "SUCCESS"
    assert page.total_count is not None
    assert page.items
    first = page.items[0]
    assert first.service_area_code
    assert first.has_maintenance in {True, False, None}
    assert first.is_truck_rest_area in {True, False, None}


@pytest.mark.live
def test_live_restarea_fuel_prices_parse_won_prices() -> None:
    client = _live_client()

    page = client.restarea.fuel_prices(num_of_rows=1, page_no=1)

    assert page.raw is not None
    assert page.raw["code"] == "SUCCESS"
    assert page.total_count is not None
    assert page.items
    first = page.items[0]
    assert first.service_area_code
    assert first.gasoline_price is None or first.gasoline_price >= 0
    assert first.diesel_price is None or first.diesel_price >= 0
    assert first.lpg_price is None or first.lpg_price >= 0


@pytest.mark.live
def test_live_restarea_convenience_facilities_keeps_raw_payload() -> None:
    client = _live_client()

    page = client.restarea.convenience_facilities(num_of_rows=1, page_no=1)

    assert page.raw is not None
    assert page.raw["code"] == "SUCCESS"
    assert page.total_count is not None
    assert page.items
    assert "serviceAreaCode" in page.items[0]
