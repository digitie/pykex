"""한국도로공사 API에서 사용하는 enum과 코드 매핑."""

from __future__ import annotations

from enum import StrEnum
from typing import TypeVar

from .exceptions import KrexInvalidParameterError

E = TypeVar("E", bound="KrexCode")


class KrexCode(StrEnum):
    """안정적인 KEX API 코드값의 공통 enum 기반 클래스.

    외부 프로그램은 `values()`, `labels()`, `choices()`를 사용해 코드표를
    중복하지 않고 폼, validator, API 문서를 만들 수 있습니다.
    """

    @property
    def label(self) -> str:
        return self._label_map().get(self.value, self.value)

    @classmethod
    def values(cls) -> tuple[str, ...]:
        return tuple(item.value for item in cls)

    @classmethod
    def labels(cls) -> dict[str, str]:
        return dict(cls._label_map())

    @classmethod
    def choices(cls) -> tuple[tuple[str, str], ...]:
        labels = cls._label_map()
        return tuple((item.value, labels.get(item.value, item.value)) for item in cls)

    @classmethod
    def from_label(cls: type[E], label: str) -> E:
        return _from_label(cls, cls._label_map(), label)

    @classmethod
    def _label_map(cls) -> dict[str, str]:
        return {}


def coerce_code(enum_type: type[E], value: E | str, field: str) -> str:
    """Enum과 호환되는 입력을 검증한 뒤 원시 API 코드값을 반환합니다."""

    try:
        return enum_type(value).value
    except ValueError as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise KrexInvalidParameterError(f"{field} must be one of: {allowed}") from exc


class CoordinateSystem(KrexCode):
    """KEX 관련 API에서 노출되는 좌표계."""

    WGS84 = "WGS84"
    KATEC = "KATEC"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def _label_map(cls) -> dict[str, str]:
        return _COORDINATE_SYSTEM_LABELS


class CarType(KrexCode):
    LIGHT = "1"
    MEDIUM = "2"
    LARGE_3AXLE = "3"
    LARGE_4AXLE = "4"
    LARGE_5AXLE = "5"
    LIGHT_DISCOUNT = "6"

    @classmethod
    def _label_map(cls) -> dict[str, str]:
        return _CAR_TYPE_LABELS


class TCSType(KrexCode):
    ALL = "0"
    TCS = "1"
    HIPASS = "2"

    @classmethod
    def _label_map(cls) -> dict[str, str]:
        return _TCS_TYPE_LABELS


class RoadOperator(KrexCode):
    KEC = "00"
    PRIV_INCHEON_AIRPORT = "01"
    PRIV_CHEONAN_NONSAN = "02"
    PRIV_DAEGU_BUSAN = "08"
    PRIV_SEOUL_CHUNCHEON = "11"
    PRIV_GURIPOCHEON = "18"

    @classmethod
    def _label_map(cls) -> dict[str, str]:
        return _ROAD_OPERATOR_LABELS


class IOType(KrexCode):
    IN = "0"
    OUT = "1"

    @classmethod
    def _label_map(cls) -> dict[str, str]:
        return _IO_TYPE_LABELS


class TimeUnit(KrexCode):
    HOUR = "1"
    MIN_15 = "2"

    @classmethod
    def _label_map(cls) -> dict[str, str]:
        return _TIME_UNIT_LABELS


class Direction(KrexCode):
    UP = "0"
    DOWN = "1"
    EAST = "E"
    WEST = "W"
    SOUTH = "S"
    NORTH = "N"

    @classmethod
    def _label_map(cls) -> dict[str, str]:
        return _DIRECTION_LABELS


class CongestionLevel(KrexCode):
    SMOOTH = "1"
    SLOW = "2"
    DELAY = "3"
    STOP = "4"

    @classmethod
    def _label_map(cls) -> dict[str, str]:
        return _CONGESTION_LABELS


class DiscountType(KrexCode):
    NONE = "0"
    NIGHT = "1"
    RUSH_DISCOUNT = "2"
    LIGHT_CAR = "3"
    HYBRID = "4"
    DISABLED = "5"

    @classmethod
    def _label_map(cls) -> dict[str, str]:
        return _DISCOUNT_LABELS


_COORDINATE_SYSTEM_LABELS = {
    "WGS84": "WGS84 위경도",
    "KATEC": "KATEC 평면직각좌표",
    "UNKNOWN": "알 수 없음",
}
_CAR_TYPE_LABELS = {
    "1": "1종",
    "2": "2종",
    "3": "3종",
    "4": "4종",
    "5": "5종",
    "6": "경차",
}
_TCS_TYPE_LABELS = {"0": "전체", "1": "TCS", "2": "하이패스"}
_ROAD_OPERATOR_LABELS = {
    "00": "한국도로공사",
    "01": "신공항하이웨이",
    "02": "천안논산고속도로",
    "08": "대구부산고속도로",
    "11": "서울춘천고속도로",
    "18": "서울북부고속도로",
}
_IO_TYPE_LABELS = {"0": "진입", "1": "진출"}
_TIME_UNIT_LABELS = {"1": "1시간", "2": "15분"}
_DIRECTION_LABELS = {
    "0": "상행",
    "1": "하행",
    "E": "동쪽",
    "W": "서쪽",
    "S": "남쪽",
    "N": "북쪽",
}
_CONGESTION_LABELS = {"1": "원활", "2": "서행", "3": "지체", "4": "정체"}
_DISCOUNT_LABELS = {
    "0": "정상",
    "1": "심야",
    "2": "출퇴근",
    "3": "경차",
    "4": "친환경차",
    "5": "장애인",
}


def _from_label(enum_type: type[E], labels: dict[str, str], label: str) -> E:
    normalized = label.strip()
    for code, item_label in labels.items():
        if normalized in {code, item_label}:
            return enum_type(code)
    raise KrexInvalidParameterError(f"unknown {enum_type.__name__} label: {label!r}")


ROUTE_NAMES: dict[str, str] = {
    "0010": "경부고속도로",
    "0050": "영동고속도로",
    "0100": "남해고속도로",
    "0150": "서해안고속도로",
    "0200": "평택제천고속도로",
    "0250": "호남고속도로",
    "0270": "익산포항고속도로",
    "0300": "대전통영고속도로",
    "0350": "중부내륙고속도로",
    "0370": "중부고속도로",
    "0400": "평택파주고속도로",
    "0450": "중앙고속도로",
    "0500": "동해고속도로",
    "0550": "순천완주고속도로",
    "0600": "서울양양고속도로",
    "0650": "당진영덕고속도로",
}
