import pytest

from krex import CarType, CongestionLevel, CoordinateSystem, Direction, TCSType
from krex.codes import coerce_code
from krex.exceptions import KrexInvalidParameterError


def test_enum_labels_are_stable() -> None:
    assert CarType.LIGHT.label == "1종"
    assert TCSType.HIPASS.label == "하이패스"
    assert Direction.UP.label == "상행"
    assert CongestionLevel.STOP.label == "정체"


def test_car_type_from_label_accepts_label_or_code() -> None:
    assert CarType.from_label("1종") is CarType.LIGHT
    assert CarType.from_label("1") is CarType.LIGHT


def test_coerce_code_rejects_unknown_values() -> None:
    with pytest.raises(KrexInvalidParameterError):
        coerce_code(CarType, "9", "car_type")


def test_code_enums_expose_choices_for_external_forms() -> None:
    assert CarType.values() == ("1", "2", "3", "4", "5", "6")
    assert ("1", "1종") in CarType.choices()
    assert CarType.labels()["6"] == "경차"
    assert TCSType.from_label("하이패스") is TCSType.HIPASS
    assert CoordinateSystem.WGS84.label == "WGS84 위경도"
