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
async def test_index_page(app, preloaded_cache):
    with patch("app.main.cache", preloaded_cache):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            assert "AzureCloud" in response.text
