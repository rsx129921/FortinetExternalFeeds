import re
import logging

import httpx

logger = logging.getLogger(__name__)

DOWNLOAD_PAGE_URL = "https://www.microsoft.com/en-us/download/details.aspx?id=56519"
DOWNLOAD_URL_PATTERN = re.compile(
    r'https://download\.microsoft\.com/download/[^"]+ServiceTags_Public_\d+\.json'
)


async def discover_download_url() -> str:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(DOWNLOAD_PAGE_URL)
        response.raise_for_status()
        match = DOWNLOAD_URL_PATTERN.search(response.text)
        if not match:
            raise RuntimeError("Could not find ServiceTags download URL on Microsoft page")
        url = match.group(0)
        logger.info("Discovered download URL: %s", url)
        return url


async def fetch_service_tags(url: str) -> dict:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        logger.info("Fetched ServiceTags: changeNumber=%s, %d tags",
                     data.get("changeNumber"), len(data.get("values", [])))
        return data
