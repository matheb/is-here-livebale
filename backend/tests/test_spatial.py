import respx
from fastapi.testclient import TestClient
from httpx import ConnectError, Response

from app.config import get_settings
from app.main import app
from app.services import spatial_service

client = TestClient(app)
settings = get_settings()


def test_sample_features_endpoint_returns_feature_collection():
    response = client.get("/spatial/sample")
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 3
    names = {f["properties"]["name"] for f in body["features"]}
    assert "Graz" in names


@respx.mock
def test_poi_endpoint_returns_point_feature_enriched_with_address():
    respx.get(f"{settings.external_api_base_url}/reverse").mock(
        return_value=Response(
            200,
            json={
                "name": "Uhrturm",
                "display_name": "Uhrturm, Schlossberg, Graz, Styria, Austria",
                "address": {"city": "Graz", "country": "Austria"},
            },
        )
    )

    payload = {"latitude": 47.0707, "longitude": 15.4395}
    response = client.post("/spatial/poi", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["geometry"]["type"] == "Point"
    assert body["geometry"]["coordinates"] == [15.4395, 47.0707]
    assert body["properties"]["name"] == "Uhrturm"
    assert body["properties"]["address"] == "Uhrturm, Schlossberg, Graz, Styria, Austria"
    assert body["properties"]["address_details"]["city"] == "Graz"


@respx.mock
def test_poi_endpoint_still_returns_point_when_reverse_geocode_unresolvable():
    # Nominatim responds 200 with an "error" key for coordinates it can't resolve.
    respx.get(f"{settings.external_api_base_url}/reverse").mock(
        return_value=Response(200, json={"error": "Unable to geocode"})
    )

    payload = {"latitude": 0, "longitude": 0}
    response = client.post("/spatial/poi", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["geometry"]["type"] == "Point"
    assert body["properties"]["name"] is None
    assert body["properties"]["address"] is None


@respx.mock
def test_poi_endpoint_still_returns_point_when_reverse_geocode_call_fails():
    respx.get(f"{settings.external_api_base_url}/reverse").mock(side_effect=ConnectError("boom"))

    payload = {"latitude": 47.0707, "longitude": 15.4395}
    response = client.post("/spatial/poi", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["geometry"]["coordinates"] == [15.4395, 47.0707]
    assert body["properties"]["name"] is None


@respx.mock
def test_poi_endpoint_still_returns_point_when_reverse_geocode_returns_invalid_json():
    # Regression test: a non-JSON response body (e.g. an HTML error/block
    # page from the third-party API) previously raised an uncaught
    # json.JSONDecodeError, surfacing as a 500 instead of degrading
    # gracefully like every other reverse-geocode failure mode.
    respx.get(f"{settings.external_api_base_url}/reverse").mock(
        return_value=Response(200, content="<html>not json</html>")
    )

    payload = {"latitude": 47.0707, "longitude": 15.4395}
    response = client.post("/spatial/poi", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["geometry"]["coordinates"] == [15.4395, 47.0707]
    assert body["properties"]["name"] is None
    assert body["properties"]["address"] is None


def test_poi_endpoint_rejects_invalid_longitude():
    payload = {"latitude": 47.0707, "longitude": 999}
    response = client.post("/spatial/poi", json=payload)
    assert response.status_code == 422


@respx.mock
def test_poi_endpoint_does_not_buffer():
    respx.get(f"{settings.external_api_base_url}/reverse").mock(
        return_value=Response(200, json={})
    )
    payload = {"latitude": 47.0707, "longitude": 15.4395}
    response = client.post("/spatial/poi", json=payload)
    body = response.json()
    assert "buffer_distance_meters" not in body["properties"]


def test_buffer_endpoint_returns_polygon():
    payload = {"latitude": 47.0707, "longitude": 15.4395, "distance_meters": 500}
    response = client.post("/spatial/buffer", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["geometry"]["type"] == "Polygon"
    assert body["properties"]["buffer_distance_meters"] == 500


def test_buffer_endpoint_rejects_invalid_latitude():
    payload = {"latitude": 999, "longitude": 15.4395, "distance_meters": 500}
    response = client.post("/spatial/buffer", json=payload)
    assert response.status_code == 422


def test_poi_point_service_returns_unbuffered_point():
    feature = spatial_service.poi_point(47.0707, 15.4395)
    assert feature["geometry"]["type"] == "Point"
    assert feature["geometry"]["coordinates"] == [15.4395, 47.0707]


def test_buffer_point_service_produces_valid_geometry():
    feature = spatial_service.buffer_point(47.0707, 15.4395, 1000)
    assert feature["geometry"]["type"] == "Polygon"
    coords = feature["geometry"]["coordinates"][0]
    assert len(coords) > 3  # a real polygon ring, not a degenerate shape


@respx.mock
def test_isochrone_endpoint_returns_feature_collection():
    respx.get(f"{settings.isochrone_api_base_url}/isoline").mock(
        return_value=Response(
            200,
            json={
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [[15.0, 47.0], [15.1, 47.0], [15.1, 47.1], [15.0, 47.0]]
                            ],
                        },
                        "properties": {},
                    }
                ],
            },
        )
    )

    payload = {"latitude": 47.0707, "longitude": 15.4395, "mode": "walk", "range_minutes": 15}
    response = client.post("/spatial/isochrone", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 1


def test_isochrone_endpoint_rejects_invalid_mode():
    payload = {"latitude": 47.0707, "longitude": 15.4395, "mode": "teleport", "range_minutes": 15}
    response = client.post("/spatial/isochrone", json=payload)
    assert response.status_code == 422


def test_isochrone_endpoint_rejects_range_over_60_minutes():
    payload = {"latitude": 47.0707, "longitude": 15.4395, "mode": "walk", "range_minutes": 90}
    response = client.post("/spatial/isochrone", json=payload)
    assert response.status_code == 422


@respx.mock
def test_isochrone_endpoint_defaults_to_walk_mode_and_15_minutes():
    # mode and range_minutes are both optional with defaults — confirm the
    # request validates and reaches the upstream call (rather than 422ing)
    # with only lat/lon provided.
    route = respx.get(f"{settings.isochrone_api_base_url}/isoline").mock(
        return_value=Response(200, json={"type": "FeatureCollection", "features": []})
    )

    payload = {"latitude": 47.0707, "longitude": 15.4395}
    response = client.post("/spatial/isochrone", json=payload)

    assert response.status_code == 200
    assert route.called
    sent_params = route.calls.last.request.url.params
    assert sent_params["mode"] == "walk"
    assert sent_params["range"] == "900"  # 15 minutes * 60


@respx.mock
def test_isochrone_endpoint_surfaces_upstream_error_status():
    respx.get(f"{settings.isochrone_api_base_url}/isoline").mock(
        return_value=Response(400, json={"error": "bad request"})
    )

    payload = {"latitude": 47.0707, "longitude": 15.4395, "mode": "walk", "range_minutes": 15}
    response = client.post("/spatial/isochrone", json=payload)

    assert response.status_code == 400


@respx.mock
def test_isochrone_endpoint_returns_502_on_network_failure():
    respx.get(f"{settings.isochrone_api_base_url}/isoline").mock(side_effect=ConnectError("boom"))

    payload = {"latitude": 47.0707, "longitude": 15.4395, "mode": "walk", "range_minutes": 15}
    response = client.post("/spatial/isochrone", json=payload)

    assert response.status_code == 502

