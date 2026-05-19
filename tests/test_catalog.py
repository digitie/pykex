from __future__ import annotations

from krex import (
    ApiCatalogItem,
    KrexClient,
    api_catalog,
    api_catalog_item,
    get_api_catalog,
    get_api_catalog_item,
)


def test_api_catalog_exposes_human_readable_names_and_key_links() -> None:
    items = get_api_catalog()
    assert items

    traffic = get_api_catalog_item("traffic.flow")

    assert isinstance(traffic, ApiCatalogItem)
    assert traffic.dataset_name == "한국도로공사_실시간 소통정보"
    assert traffic.service_key_url == "https://data.ex.co.kr/openapi/apikey/requestKey"
    assert traffic.endpoint == "/openapi/trafficapi/realFlow"
    assert all(item.dataset_name and item.dataset_name != item.function for item in items)
    assert all(item.service_key_url for item in items if item.provider != "local")


def test_api_catalog_can_be_filtered_from_library_or_reference_namespace() -> None:
    restarea = get_api_catalog(namespace="restarea")
    data_go = get_api_catalog(provider="data.go.kr")
    client_catalog = KrexClient(ex_api_key="unused").reference.api_catalog(namespace="restarea")
    weather = get_api_catalog_item("restarea.weather")

    assert weather is not None
    assert api_catalog(namespace="restarea") == restarea
    assert api_catalog_item("restarea.weather") == weather
    assert {item.function for item in restarea} == {item.function for item in client_catalog}
    assert {item.provider for item in data_go} == {"data.go.kr"}
    assert weather.fixture_supported is True
