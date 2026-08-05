import logging

import httpx
import pytest
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
async def test_client_includes_response_body_in_error_message():
    # The response body usually contains the actual reason a third-party
    # API rejected a request (invalid key, bad param, quota, etc.) — make
    # sure it's not silently dropped in favor of just the status line.
    settings = Settings(external_api_base_url="https://geocoder.example.com")
    respx.get("https://geocoder.example.com/reverse").mock(
        return_value=Response(400, json={"error": "invalid format parameter"})
    )

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await ExternalAPIClient(settings=settings).get("/reverse")

    assert "invalid format parameter" in str(exc_info.value)


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


@respx.mock
async def test_client_logs_success_at_info_level(caplog):
    settings = Settings(external_api_base_url="https://geocoder.example.com")
    respx.get("https://geocoder.example.com/reverse").mock(return_value=Response(200, json={}))

    with caplog.at_level(logging.INFO, logger="app.services.external_api"):
        await ExternalAPIClient(settings=settings).get("/reverse")

    assert any("succeeded" in record.message for record in caplog.records)


@respx.mock
async def test_client_logs_warning_with_body_on_error_status(caplog):
    settings = Settings(external_api_base_url="https://geocoder.example.com")
    respx.get("https://geocoder.example.com/reverse").mock(
        return_value=Response(400, json={"error": "bad request"})
    )

    with (
        caplog.at_level(logging.WARNING, logger="app.services.external_api"),
        pytest.raises(httpx.HTTPStatusError),
    ):
        await ExternalAPIClient(settings=settings).get("/reverse")

    assert any(
        "bad request" in record.message and "400" in record.message for record in caplog.records
    )


@respx.mock
async def test_client_logs_error_on_network_failure(caplog):
    settings = Settings(external_api_base_url="https://geocoder.example.com")
    respx.get("https://geocoder.example.com/reverse").mock(side_effect=ConnectError("boom"))

    with (
        caplog.at_level(logging.ERROR, logger="app.services.external_api"),
        pytest.raises(ConnectError),
    ):
        await ExternalAPIClient(settings=settings).get("/reverse")

    assert any("failed" in record.message for record in caplog.records)


@respx.mock
async def test_client_logs_the_exact_request_method_url_and_params(caplog):
    # The whole point of building the request explicitly (rather than
    # reconstructing an approximate URL for logging) is that what's logged
    # is exactly what's sent — real method, real fully-encoded query string.
    settings = Settings(external_api_base_url="https://geocoder.example.com")
    respx.get("https://geocoder.example.com/reverse").mock(return_value=Response(200, json={}))

    with caplog.at_level(logging.DEBUG, logger="app.services.external_api"):
        await ExternalAPIClient(settings=settings).get(
            "/reverse", params={"lat": 47.07, "lon": 15.44, "format": "json"}
        )

    debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
    assert any(
        "GET" in m
        and "https://geocoder.example.com/reverse" in m
        and "lat=47.07" in m
        and "lon=15.44" in m
        and "format=json" in m
        for m in debug_messages
    )


@respx.mock
async def test_client_never_logs_the_raw_api_key(caplog):
    # The most important logging test: the API key must never appear in log
    # output in plain text, at any log level, in any of the three call paths
    # (request debug log, success info log, failure warning log).
    settings = Settings(
        external_api_base_url="https://geocoder.example.com",
        external_api_key="TOTALLY-SECRET-KEY",
        external_api_key_param_name="key",
    )
    respx.get("https://geocoder.example.com/reverse").mock(return_value=Response(200, json={}))

    with caplog.at_level(logging.DEBUG, logger="app.services.external_api"):
        await ExternalAPIClient(settings=settings).get("/reverse")

    all_log_text = "\n".join(record.message for record in caplog.records)
    assert "TOTALLY-SECRET-KEY" not in all_log_text
    assert "***redacted***" in all_log_text


@respx.mock
async def test_isochrone_provider_uses_isochrone_settings_not_geocoding_settings():
    # The two provider configs must be genuinely independent — using the
    # isochrone provider should never fall back to the geocoding provider's
    # base URL/key, even if both are configured.
    settings = Settings(
        external_api_base_url="https://geocoder.example.com",
        external_api_key="geocode-key",
        isochrone_api_base_url="https://isoline.example.com",
        isochrone_api_key="isochrone-key",
        isochrone_api_key_param_name="apiKey",
    )
    route = respx.get("https://isoline.example.com/isoline").mock(
        return_value=Response(200, json={"type": "FeatureCollection", "features": []})
    )

    await ExternalAPIClient(settings=settings, provider="isochrone").get_isochrone(
        latitude=1, longitude=2, mode="walk", range_seconds=600
    )

    assert route.called
    sent_request = route.calls.last.request
    assert sent_request.url.params["apiKey"] == "isochrone-key"
    assert "geocode-key" not in str(sent_request.url)


@respx.mock
async def test_isochrone_client_returns_result_immediately_on_200():
    settings = Settings(isochrone_api_base_url="https://isoline.example.com")
    respx.get("https://isoline.example.com/isoline").mock(
        return_value=Response(200, json={"type": "FeatureCollection", "features": []})
    )

    result = await ExternalAPIClient(settings=settings, provider="isochrone").get_isochrone(
        latitude=47.07, longitude=15.44, mode="walk", range_seconds=900
    )

    assert result == {"type": "FeatureCollection", "features": []}


@respx.mock
async def test_isochrone_client_polls_when_provider_responds_202():
    # Geoapify computes some isolines asynchronously: first response is 202
    # with a pending id, second (polled) response is the real 200 result.
    settings = Settings(isochrone_api_base_url="https://isoline.example.com")
    route = respx.get("https://isoline.example.com/isoline")
    route.side_effect = [
        Response(202, json={"properties": {"id": "abc123"}}),
        Response(200, json={"type": "FeatureCollection", "features": []}),
    ]

    result = await ExternalAPIClient(settings=settings, provider="isochrone").get_isochrone(
        latitude=47.07,
        longitude=15.44,
        mode="walk",
        range_seconds=900,
        poll_interval_seconds=0.01,  # keep the test fast
    )

    assert result == {"type": "FeatureCollection", "features": []}
    assert route.call_count == 2


@respx.mock
async def test_isochrone_client_raises_timeout_if_polling_never_resolves():
    settings = Settings(isochrone_api_base_url="https://isoline.example.com")
    respx.get("https://isoline.example.com/isoline").mock(
        return_value=Response(202, json={"properties": {"id": "abc123"}})
    )

    with pytest.raises(TimeoutError):
        await ExternalAPIClient(settings=settings, provider="isochrone").get_isochrone(
            latitude=47.07,
            longitude=15.44,
            mode="walk",
            range_seconds=900,
            max_poll_attempts=2,
            poll_interval_seconds=0.01,
        )


@respx.mock
async def test_isochrone_client_raises_value_error_if_202_has_no_id():
    settings = Settings(isochrone_api_base_url="https://isoline.example.com")
    respx.get("https://isoline.example.com/isoline").mock(
        return_value=Response(202, json={"properties": {}})
    )

    with pytest.raises(ValueError, match="no id to poll for"):
        await ExternalAPIClient(settings=settings, provider="isochrone").get_isochrone(
            latitude=47.07, longitude=15.44, mode="walk", range_seconds=900
        )

