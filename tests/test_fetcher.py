import pytest
from unittest.mock import AsyncMock, patch

from app.fetcher import discover_download_url, fetch_service_tags


FAKE_DOWNLOAD_PAGE = """
<html><body>
<a href="https://download.microsoft.com/download/7/1/d/71d86715-5596-4529-9b13-da13a5de5b63/ServiceTags_Public_20260223.json"
   class="btn">Download</a>
</body></html>
"""

FAKE_SERVICE_TAGS = {
    "changeNumber": 200,
    "cloud": "Public",
    "values": [
        {
            "name": "AzureCloud",
            "id": "AzureCloud",
            "properties": {
                "changeNumber": 10,
                "region": "",
                "regionId": 0,
                "platform": "Azure",
                "systemService": "",
                "addressPrefixes": ["10.0.0.0/8"],
                "networkFeatures": [],
            },
        }
    ],
}


@pytest.mark.asyncio
async def test_discover_download_url():
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = FAKE_DOWNLOAD_PAGE
    mock_response.raise_for_status = lambda: None

    with patch("app.fetcher.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        url = await discover_download_url()
        assert "ServiceTags_Public" in url
        assert url.endswith(".json")


@pytest.mark.asyncio
async def test_fetch_service_tags():
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = lambda: FAKE_SERVICE_TAGS
    mock_response.raise_for_status = lambda: None

    with patch("app.fetcher.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        data = await fetch_service_tags("https://example.com/fake.json")
        assert data["changeNumber"] == 200
        assert len(data["values"]) == 1
