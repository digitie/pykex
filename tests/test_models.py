import pytest
from pydantic import ValidationError

from krex import CoordinateSystem, Page, PlaceCoordinate, RawCoordinate


def test_page_behaves_like_read_only_sequence() -> None:
    page = Page(items=["a", "b"], total_count=2)

    assert list(page) == ["a", "b"]
    assert page.items == ("a", "b")
    assert len(page) == 2
    assert page
    assert page.first == "a"
    assert page.is_empty is False
    assert page.model_dump()["items"] == ("a", "b")


def test_empty_page_helpers() -> None:
    page: Page[str] = Page(items=())

    assert list(page) == []
    assert len(page) == 0
    assert not page
    assert page.first is None
    assert page.is_empty is True


def test_place_coordinate_standardizes_lon_lat_and_aliases() -> None:
    point = PlaceCoordinate(lat="37.332", lon="127.104")

    assert point.lonlat == (127.104, 37.332)
    assert point.latlon == (37.332, 127.104)
    assert point.as_geojson_position() == (127.104, 37.332)
    assert point.longitude == point.lon
    assert point.latitude == point.lat
    assert point.model_dump()["lon"] == 127.104
    assert point.model_dump()["lat"] == 37.332


def test_pydantic_models_are_frozen_and_schema_ready() -> None:
    point = PlaceCoordinate(lat=37.332, lon=127.104)
    schema = PlaceCoordinate.model_json_schema()

    with pytest.raises(ValidationError):
        point.lon = 1

    assert schema["properties"]["lon"]["type"] == "number"
    assert schema["properties"]["lat"]["type"] == "number"


def test_place_coordinate_validates_ranges() -> None:
    with pytest.raises(ValueError):
        PlaceCoordinate(lat=37, lon=181)
    with pytest.raises(ValueError):
        PlaceCoordinate(lat=91, lon=127)


def test_raw_coordinate_defaults_to_unknown_system() -> None:
    coord = RawCoordinate(x=1, y=2)

    assert coord.system is CoordinateSystem.UNKNOWN
