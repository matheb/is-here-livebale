import respx
from fastapi.testclient import TestClient
from httpx import Response

from app.config import get_settings
from app.main import app

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
