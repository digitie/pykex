"""Implemented API catalog."""

from __future__ import annotations

from .models import ApiCatalogItem

EX_SERVICE_KEY_URL = "https://data.ex.co.kr/openapi/apikey/requestKey"
DATA_GO_SERVICE_KEY_URL = "https://www.data.go.kr/ugs/selectPublicDataUseGuideView.do"


def _ex(
    function: str,
    dataset_name: str,
    endpoint: str,
    return_type: str,
    description: str,
    *,
    live_verified: bool,
    fixture_supported: bool = False,
) -> ApiCatalogItem:
    return ApiCatalogItem(
        function=function,
        dataset_name=dataset_name,
        provider="data.ex.co.kr",
        service_key_url=EX_SERVICE_KEY_URL,
        endpoint=endpoint,
        return_type=return_type,
        description=description,
        live_verified=live_verified,
        fixture_supported=fixture_supported,
    )


def _go(
    function: str,
    dataset_name: str,
    endpoint: str,
    return_type: str,
    description: str,
    *,
    dataset_id: str | None = None,
    service_key_url: str | None = None,
    live_verified: bool = False,
) -> ApiCatalogItem:
    return ApiCatalogItem(
        function=function,
        dataset_name=dataset_name,
        provider="data.go.kr",
        service_key_url=service_key_url or DATA_GO_SERVICE_KEY_URL,
        endpoint=endpoint,
        return_type=return_type,
        description=description,
        dataset_id=dataset_id,
        live_verified=live_verified,
    )


_CATALOG: tuple[ApiCatalogItem, ...] = (
    _ex(
        "traffic.by_ic",
        "한국도로공사_영업소별 교통량",
        "/openapi/trafficapi/trafficIc",
        "Page[TrafficByIc]",
        "영업소 입출구 시간 단위, 차종별 교통량입니다.",
        live_verified=True,
    ),
    _ex(
        "traffic.by_route",
        "한국도로공사_노선별 교통량",
        "/openapi/trafficapi/trafficRoute",
        "Page[dict]",
        "노선 단위 교통량 원천 row입니다.",
        live_verified=True,
    ),
    _ex(
        "traffic.flow",
        "한국도로공사_실시간 소통정보",
        "/openapi/trafficapi/realFlow",
        "Page[TrafficFlow]",
        "콘존별 실시간 속도와 정체 상태입니다.",
        live_verified=False,
    ),
    _ex(
        "traffic.incident",
        "한국도로공사_실시간 사고·공사정보",
        "/openapi/trafficapi/incident",
        "Page[Incident]",
        "사고, 공사, 이벤트 안내 정보입니다.",
        live_verified=False,
    ),
    _ex(
        "traffic.vds_raw",
        "한국도로공사_VDS 원시자료",
        "/openapi/trafficapi/vdsRaw",
        "Page[dict]",
        "VDS 원시 교통 데이터입니다.",
        live_verified=False,
    ),
    _ex(
        "traffic.avc_raw",
        "한국도로공사_AVC 원시자료",
        "/openapi/trafficapi/avcRaw",
        "Page[dict]",
        "AVC 원시 교통 데이터입니다.",
        live_verified=False,
    ),
    _ex(
        "tollfee.between_tollgates",
        "한국도로공사_영업소간 통행요금",
        "/openapi/tollfee/tollFeeBetweenTcs",
        "Page[TollFee]",
        "출발/도착 영업소와 차종별 통행요금입니다.",
        live_verified=False,
    ),
    _ex(
        "tollfee.tollgate_list",
        "한국도로공사_영업소 목록",
        "/openapi/business/openapibusinessunit",
        "Page[Tollgate]",
        "영업소 코드, 명칭, 좌표 기본 정보입니다.",
        live_verified=False,
    ),
    _ex(
        "restarea.route_facilities",
        "한국도로공사_노선별 휴게소시설 현황",
        "/openapi/business/serviceAreaRoute",
        "Page[RestAreaRouteFacility]",
        "노선별 휴게소 시설, 주소, 편의시설 정보입니다.",
        live_verified=True,
    ),
    _go(
        "restarea.list_all",
        "한국도로공사_전국 휴게소 정보",
        "https://api.data.go.kr/openapi/tn_pubr_public_rest_area_api",
        "Page[RestArea]",
        "공공데이터포털 표준 휴게소 정보입니다.",
        dataset_id="15025446",
        service_key_url="https://www.data.go.kr/data/15025446/standard.do",
    ),
    _ex(
        "restarea.weather",
        "한국도로공사_휴게소별 날씨",
        "/openapi/restinfo/restWeatherList",
        "Page[RestAreaWeather]",
        "휴게소별 관측 시각의 날씨 정보입니다.",
        live_verified=False,
        fixture_supported=True,
    ),
    _ex(
        "restarea.latest_weather",
        "한국도로공사_휴게소별 최신 날씨",
        "/openapi/restinfo/restWeatherList",
        "Page[RestAreaWeather]",
        "지정 시각부터 과거 방향으로 조회 가능한 최신 휴게소 날씨입니다.",
        live_verified=False,
    ),
    _ex(
        "restarea.fuel_prices",
        "한국도로공사_주유소별 가격·영업업체 현황",
        "/openapi/business/curStateStation",
        "Page[RestAreaFuelPrice]",
        "휴게소 주유소 업체, 유종별 가격, LPG 여부입니다.",
        live_verified=True,
    ),
    _ex(
        "restarea.convenience_facilities",
        "한국도로공사_휴게소 편의시설 현황",
        "/openapi/business/conveniServiceArea",
        "Page[dict]",
        "노선/방향별 휴게소 편의시설 원천 row입니다.",
        live_verified=True,
    ),
    _ex(
        "restarea.food_price",
        "한국도로공사_휴게소 음식가격",
        "/openapi/restinfo/restMenuList",
        "Page[FoodPrice]",
        "휴게소 음식 메뉴와 가격입니다.",
        live_verified=False,
    ),
    _ex(
        "restarea.parking",
        "한국도로공사_휴게소 주차장 정보",
        "/openapi/restinfo/restParking",
        "Page[dict]",
        "휴게소 주차 대수 원천 row입니다.",
        live_verified=False,
    ),
    _ex(
        "restarea.wifi",
        "한국도로공사_휴게소 와이파이 정보",
        "/openapi/restinfo/restWifi",
        "Page[dict]",
        "휴게소 와이파이 제공 여부 원천 row입니다.",
        live_verified=False,
    ),
    _ex(
        "restarea.restroom",
        "한국도로공사_휴게소 화장실 정보",
        "/openapi/restinfo/restRestroom",
        "Page[dict]",
        "휴게소 화장실 시설 원천 row입니다.",
        live_verified=False,
    ),
    _ex(
        "restarea.disabled_facility",
        "한국도로공사_휴게소 장애인 편의시설",
        "/openapi/restinfo/restDisabled",
        "Page[dict]",
        "휴게소 장애인 편의시설 원천 row입니다.",
        live_verified=False,
    ),
    _ex(
        "restarea.bus_transit",
        "한국도로공사_휴게소 환승버스 정보",
        "/openapi/restinfo/restBus",
        "Page[dict]",
        "휴게소 환승버스 원천 row입니다.",
        live_verified=False,
    ),
    _go(
        "facility.tollgate_info",
        "한국도로공사_영업소 위치정보",
        "https://apis.data.go.kr/B552061/TollgateInfoService/getTollgateInfo",
        "Page[dict]",
        "영업소 위치와 상세 메타데이터 원천 row입니다.",
    ),
    _ex(
        "facility.drowsy_shelter",
        "한국도로공사_졸음쉼터 정보",
        "/openapi/restinfo/drowsyShelter",
        "Page[dict]",
        "졸음쉼터 원천 row입니다.",
        live_verified=False,
    ),
    _go(
        "facility.shoulder_lane",
        "한국도로공사_갓길차로제 정보",
        "https://apis.data.go.kr/B552061/ShoulderLaneService/getShoulderLane",
        "Page[dict]",
        "갓길차로제 운영 정보 원천 row입니다.",
    ),
    _go(
        "admin.procurement_contracts",
        "한국도로공사_전자조달 계약공개현황",
        "https://apis.data.go.kr/B552061/ProcurementContractService/getContracts",
        "Page[dict]",
        "전자조달 계약공개 현황 원천 row입니다.",
        dataset_id="15128076",
        service_key_url="https://www.data.go.kr/data/15128076/openapi.do",
    ),
    ApiCatalogItem(
        function="reference.api_catalog",
        dataset_name="python-krex-api_API 카탈로그",
        provider="local",
        return_type="tuple[ApiCatalogItem, ...]",
        description="라이브러리에 구현된 API와 로컬 참조 함수 목록입니다.",
        live_verified=None,
    ),
    ApiCatalogItem(
        function="reference.common_codes",
        dataset_name="python-krex-api_공통 코드",
        provider="local",
        return_type="dict[str, dict[str, str]]",
        description="라이브러리에 내장된 enum 라벨입니다.",
        live_verified=None,
    ),
    ApiCatalogItem(
        function="reference.routes",
        dataset_name="python-krex-api_노선 기초정보",
        provider="local",
        return_type="tuple[Route, ...]",
        description="라이브러리에 내장된 소량의 노선 기초정보입니다.",
        live_verified=None,
    ),
)


def get_api_catalog(
    *,
    provider: str | None = None,
    namespace: str | None = None,
) -> tuple[ApiCatalogItem, ...]:
    """Return the implemented API catalog."""

    items = _CATALOG
    if provider is not None:
        items = tuple(item for item in items if item.provider == provider)
    if namespace is not None:
        prefix = f"{namespace}."
        items = tuple(item for item in items if item.function.startswith(prefix))
    return items


def api_catalog(
    *,
    provider: str | None = None,
    namespace: str | None = None,
) -> tuple[ApiCatalogItem, ...]:
    """Return the implemented API catalog.

    This mirrors the public helper name used by python-krheritage-api.
    """

    return get_api_catalog(provider=provider, namespace=namespace)


def get_api_catalog_item(function: str) -> ApiCatalogItem | None:
    """Find one catalog item by a public function name such as traffic.flow."""

    for item in _CATALOG:
        if item.function == function:
            return item
    return None


def api_catalog_item(function: str) -> ApiCatalogItem | None:
    """Find one catalog item by public function name."""

    return get_api_catalog_item(function)
