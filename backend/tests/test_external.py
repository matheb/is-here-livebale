import respx
from fastapi.testclient import TestClient
from httpx import ConnectError, Response

from app.config import Settings, get_settings
from app.main import app
from app.services.external_api import ExternalAPIClient

client = TestClient(app)


@respx.mock
def test_geocode_proxies_and_transforms_third_party_response():
    settings = get_settings()
    route = respx.get(f"{settings.external_api_base_url}/search").mock(
        return_value=Response(
            200,
            json=[
                {"display_name": "Graz, Austria", "lat": "47.0707", "lon": "15.4395"},
            ],
        )
    )

    response = client.get("/external/geocode", params={"q": "Graz"})

    assert route.called
    assert response.status_code == 200
    body = response.json()
    assert body[0]["display_name"] == "Graz, Austria"
    assert body[0]["latitude"] == 47.0707


@respx.mock
def test_geocode_surfaces_upstream_error_status():
    settings = get_settings()
    respx.get(f"{settings.external_api_base_url}/search").mock(
        return_value=Response(503)
    )

    response = client.get("/external/geocode", params={"q": "Graz"})

    assert response.status_code == 503


@respx.mock
def test_geocode_returns_502_on_network_failure():
    settings = get_settings()
    respx.get(f"{settings.external_api_base_url}/search").mock(side_effect=ConnectError("boom"))

    response = client.get("/external/geocode", params={"q": "Graz"})

    assert response.status_code == 502


@respx.mock
def test_geocode_returns_502_on_invalid_json_response():
    # Regression test: a non-JSON upstream response previously raised an
    # uncaught exception, surfacing as a 500 instead of a clean 502.
    settings = get_settings()
    respx.get(f"{settings.external_api_base_url}/search").mock(
        return_value=Response(200, content="<html>not json</html>")
    )

    response = client.get("/external/geocode", params={"q": "Graz"})

    assert response.status_code == 502


@respx.mock
async def test_client_sends_api_key_as_query_param_when_configured():
    # e.g. LocationIQ/Geoapify/OpenCage style: ?key=...
    settings = Settings(
        external_api_base_url="https://geocoder.example.com",
        external_api_key="secret123",
        external_api_key_param_name="key",
    )
    route = respx.get("https://geocoder.example.com/reverse").mock(
        return_value=Response(200, json={})
    )

    await ExternalAPIClient(settings=settings).get("/reverse", params={"lat": 1, "lon": 2})

    assert route.called
    sent_request = route.calls.last.request
    assert sent_request.url.params["key"] == "secret123"


@respx.mock
async def test_client_sends_api_key_as_bearer_header_by_default():
    settings = Settings(
        external_api_base_url="https://geocoder.example.com",
        external_api_key="secret123",
    )
    route = respx.get("https://geocoder.example.com/reverse").mock(
        return_value=Response(200, json={})
    )

    await ExternalAPIClient(settings=settings).get("/reverse")

    assert route.called
    sent_request = route.calls.last.request
    assert sent_request.headers["Authorization"] == "Bearer secret123"
    assert "key" not in sent_request.url.params
