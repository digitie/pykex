import pytest
from pydantic import ValidationError

from krex import CoordinateSystem, Page, RawCoordinate


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


def test_pydantic_models_are_frozen_and_schema_ready() -> None:
    coord = RawCoordinate(x=127.104, y=37.332)
    schema = RawCoordinate.model_json_schema()

    with pytest.raises(ValidationError):
        coord.x = 1

    assert schema["properties"]["x"]["type"] == "number"
    assert schema["properties"]["y"]["type"] == "number"


def test_raw_coordinate_defaults_to_unknown_system() -> None:
    coord = RawCoordinate(x=1, y=2)

    assert coord.system is CoordinateSystem.UNKNOWN
