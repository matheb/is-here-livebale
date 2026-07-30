from fastapi.testclient import TestClient

from app.main import app
from app.services import spatial_service

client = TestClient(app)


def test_sample_features_endpoint_returns_feature_collection():
    response = client.get("/spatial/sample")
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 3
    names = {f["properties"]["name"] for f in body["features"]}
    assert "Graz" in names

def test_poi_endpoint_returns_point_feature():
    payload = {"latitude": 47.0707, "longitude": 15.4395}
    response = client.post("/spatial/poi", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["geometry"]["type"] == "Point"
    assert body["geometry"]["coordinates"] == [15.4395, 47.0707]
    assert body["properties"]["latitude"] == 47.0707
    assert body["properties"]["longitude"] == 15.4395

def test_poi_endpoint_rejects_invalid_longitude():
    payload = {"latitude": 47.0707, "longitude": 999}
    response = client.post("/spatial/poi", json=payload)
    assert response.status_code == 422


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


def test_buffer_point_service_produces_valid_geometry():
    feature = spatial_service.buffer_point(47.0707, 15.4395, 1000)
    assert feature["geometry"]["type"] == "Polygon"
    coords = feature["geometry"]["coordinates"][0]
    assert len(coords) > 3  # a real polygon ring, not a degenerate shape
