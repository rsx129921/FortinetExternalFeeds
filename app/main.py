import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse, HTMLResponse

from app.cache import FeedCache
from app.config import settings
from app.fetcher import discover_download_url, fetch_service_tags

logger = logging.getLogger(__name__)

cache = FeedCache()


async def refresh_cache() -> None:
    url = await discover_download_url()
    data = await fetch_service_tags(url)
    cache.load(data)
    logger.info("Cache refreshed: changeNumber=%s", cache.change_number)


async def periodic_refresh() -> None:
    interval = settings.refresh_interval_hours * 3600
    while True:
        await asyncio.sleep(interval)
        try:
            await refresh_cache()
        except Exception:
            logger.exception("Failed to refresh cache")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=settings.log_level.upper())
    await refresh_cache()
    task = asyncio.create_task(periodic_refresh())
    yield
    task.cancel()


app = FastAPI(title="Fortinet External Feeds", lifespan=lifespan)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "change_number": cache.change_number,
        "last_refresh": cache.last_refresh.isoformat() if cache.last_refresh else None,
    }


@app.get("/tags")
async def tags():
    return cache.get_all_tags()


@app.get("/feeds/{service_tag:path}")
async def feed(service_tag: str, ipv6: bool = Query(False)):
    prefixes = cache.get_tag(service_tag, include_ipv6=ipv6)
    if prefixes is None:
        raise HTTPException(status_code=404, detail=f"Service tag '{service_tag}' not found")
    return PlainTextResponse("\n".join(prefixes) + "\n")


@app.get("/", response_class=HTMLResponse)
async def index():
    tag_names = cache.get_all_tags()
    links = "\n".join(
        f'<li><a href="/feeds/{name}">{name}</a></li>' for name in tag_names
    )
    return f"""<!DOCTYPE html>
<html>
<head><title>Fortinet External Feeds</title></head>
<body>
<h1>Available Service Tags</h1>
<p>{len(tag_names)} service tags available. Each link returns a plain-text list of IP/CIDR prefixes.</p>
<ul>{links}</ul>
</body>
</html>"""
