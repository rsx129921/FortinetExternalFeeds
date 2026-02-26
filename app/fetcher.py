import re
import logging
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

DOWNLOAD_PAGE_URL = "https://www.microsoft.com/en-us/download/details.aspx?id=56519"
DOWNLOAD_URL_PATTERN = re.compile(
    r'https://download\.microsoft\.com/download/[^"]+ServiceTags_Public_\d+\.json'
)
ALLOWED_DOWNLOAD_HOST = "download.microsoft.com"
TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=5.0)
MAX_RESPONSE_BYTES = 20 * 1024 * 1024  # 20 MB safety ceiling


def _validate_download_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"Expected HTTPS URL, got scheme: {parsed.scheme!r}")
    if parsed.hostname != ALLOWED_DOWNLOAD_HOST:
        raise ValueError(f"Unexpected download host: {parsed.hostname!r}")
    return url


async def discover_download_url() -> str:
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=TIMEOUT,
        max_redirects=3,
    ) as client:
        response = await client.get(DOWNLOAD_PAGE_URL)
        response.raise_for_status()
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise RuntimeError("Response too large from Microsoft download page")
        match = DOWNLOAD_URL_PATTERN.search(response.text)
        if not match:
            raise RuntimeError("Could not find ServiceTags download URL on Microsoft page")
        url = _validate_download_url(match.group(0))
        logger.info("Discovered download URL: %s", url)
        return url


async def fetch_service_tags(url: str) -> dict:
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=TIMEOUT,
        max_redirects=3,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise RuntimeError("ServiceTags response too large")
        data = response.json()
        logger.info("Fetched ServiceTags: changeNumber=%s, %d tags",
                     data.get("changeNumber"), len(data.get("values", [])))
        return data
