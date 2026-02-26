import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport

from app.cache import FeedCache

SAMPLE_DATA = {
    "changeNumber": 100,
    "cloud": "Public",
    "values": [
        {
            "name": "AzureCloud",
            "id": "AzureCloud",
            "properties": {
                "changeNumber": 50,
                "region": "",
                "regionId": 0,
                "platform": "Azure",
                "systemService": "",
                "addressPrefixes": ["10.0.0.0/8", "172.16.0.0/12", "2001:db8::/32"],
                "networkFeatures": ["API", "NSG"],
            },
        },
        {
            "name": "AzureCloud.EastUS",
            "id": "AzureCloud.EastUS",
            "properties": {
                "changeNumber": 20,
                "region": "eastus",
                "regionId": 1,
                "platform": "Azure",
                "systemService": "",
                "addressPrefixes": ["20.0.0.0/16"],
                "networkFeatures": ["API"],
            },
        },
    ],
}


@pytest.fixture
def preloaded_cache():
    cache = FeedCache()
    cache.load(SAMPLE_DATA)
    return cache


@pytest.fixture
def app(preloaded_cache):
    """Create app with pre-loaded cache, skipping the real startup fetch."""
    with patch("app.main.cache", preloaded_cache):
        from app.main import app as fastapi_app
        yield fastapi_app


@pytest.mark.asyncio
async def test_health(app, preloaded_cache):
    with patch("app.main.cache", preloaded_cache):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["change_number"] == 100
            assert "last_refresh" in data


@pytest.mark.asyncio
async def test_health_has_security_headers(app, preloaded_cache):
    with patch("app.main.cache", preloaded_cache):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.headers["x-content-type-options"] == "nosniff"
            assert response.headers["x-frame-options"] == "DENY"
            assert response.headers["referrer-policy"] == "no-referrer"
            assert "strict-transport-security" in response.headers


@pytest.mark.asyncio
async def test_tags(app, preloaded_cache):
    with patch("app.main.cache", preloaded_cache):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/tags")
            assert response.status_code == 200
            tags = response.json()
            assert "AzureCloud" in tags
            assert "AzureCloud.EastUS" in tags


@pytest.mark.asyncio
async def test_feed_ipv4_only(app, preloaded_cache):
    with patch("app.main.cache", preloaded_cache):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/feeds/AzureCloud")
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/plain")
            lines = response.text.strip().split("\n")
            assert "10.0.0.0/8" in lines
            assert "172.16.0.0/12" in lines
            assert "2001:db8::/32" not in lines


@pytest.mark.asyncio
async def test_feed_with_ipv6(app, preloaded_cache):
    with patch("app.main.cache", preloaded_cache):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/feeds/AzureCloud?ipv6=true")
            assert response.status_code == 200
            lines = response.text.strip().split("\n")
            assert "2001:db8::/32" in lines


@pytest.mark.asyncio
async def test_feed_not_found(app, preloaded_cache):
    with patch("app.main.cache", preloaded_cache):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/feeds/NonexistentTag")
            assert response.status_code == 404


@pytest.mark.asyncio
async def test_feed_invalid_tag_rejected(app, preloaded_cache):
    """Path traversal and invalid characters return 404."""
    with patch("app.main.cache", preloaded_cache):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/feeds/../../etc/passwd")
            assert response.status_code == 404
            assert "passwd" not in response.json().get("detail", "")


@pytest.mark.asyncio
async def test_feed_with_token_auth(app, preloaded_cache):
    """When API_TOKEN is set, requests without valid token are rejected."""
    with (
        patch("app.main.cache", preloaded_cache),
        patch("app.main.settings") as mock_settings,
    ):
        mock_settings.api_token = "test-secret"
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # No token — forbidden
            response = await client.get("/feeds/AzureCloud")
            assert response.status_code == 403

            # Wrong token — forbidden
            response = await client.get("/feeds/AzureCloud?token=wrong")
            assert response.status_code == 403

            # Correct token — success
            response = await client.get("/feeds/AzureCloud?token=test-secret")
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_index_page(app, preloaded_cache):
    with patch("app.main.cache", preloaded_cache):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            assert "AzureCloud" in response.text


@pytest.mark.asyncio
async def test_swagger_ui_disabled(app, preloaded_cache):
    """Swagger/OpenAPI endpoints are disabled in production."""
    with patch("app.main.cache", preloaded_cache):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            assert (await client.get("/docs")).status_code == 404
            assert (await client.get("/redoc")).status_code == 404
            assert (await client.get("/openapi.json")).status_code == 404
