import asyncio
import html
import logging
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request, Depends, Security
from fastapi.responses import PlainTextResponse, HTMLResponse, Response
from fastapi.security.api_key import APIKeyQuery
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.cache import FeedCache
from app.config import settings
from app.fetcher import discover_download_url, fetch_service_tags

logger = logging.getLogger(__name__)

cache = FeedCache()
limiter = Limiter(key_func=get_remote_address)

SERVICE_TAG_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
MAX_STARTUP_RETRIES = 5
STARTUP_RETRY_DELAY_SECONDS = 30


# --- Authentication ---

api_key_query = APIKeyQuery(name="token", auto_error=False)


async def verify_token(token: str | None = Security(api_key_query)) -> str | None:
    if settings.api_token is None:
        return None
    if token != settings.api_token:
        raise HTTPException(status_code=403, detail="Forbidden")
    return token


# --- Security Headers Middleware ---


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'none'"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Cache-Control"] = "no-store"
        return response


# --- Cache Refresh ---


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


# --- Lifespan ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.getLogger().setLevel(settings.log_level.upper())
    for attempt in range(1, MAX_STARTUP_RETRIES + 1):
        try:
            await refresh_cache()
            break
        except Exception:
            logger.exception(
                "Startup cache refresh attempt %d/%d failed",
                attempt,
                MAX_STARTUP_RETRIES,
            )
            if attempt < MAX_STARTUP_RETRIES:
                await asyncio.sleep(STARTUP_RETRY_DELAY_SECONDS)
    task = asyncio.create_task(periodic_refresh())
    yield
    task.cancel()


# --- App ---

app = FastAPI(
    title="Fortinet External Feeds",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SecurityHeadersMiddleware)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "change_number": cache.change_number,
        "last_refresh": cache.last_refresh.isoformat() if cache.last_refresh else None,
    }


@app.get("/tags")
@limiter.limit("30/minute")
async def tags(request: Request, _: str | None = Depends(verify_token)) -> list[str]:
    return cache.get_all_tags()


@app.get("/feeds/{service_tag:path}")
@limiter.limit("60/minute")
async def feed(
    request: Request,
    service_tag: str,
    ipv6: bool = Query(False),
    _: str | None = Depends(verify_token),
) -> PlainTextResponse:
    if not SERVICE_TAG_PATTERN.match(service_tag):
        raise HTTPException(status_code=404, detail="Not found")
    prefixes = cache.get_tag(service_tag, include_ipv6=ipv6)
    if prefixes is None:
        raise HTTPException(status_code=404, detail="Not found")
    return PlainTextResponse("\n".join(prefixes) + "\n")


@app.get("/", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def index(request: Request) -> HTMLResponse:
    tag_names = cache.get_all_tags()
    links = "\n".join(
        f'<li><a href="/feeds/{html.escape(name)}">{html.escape(name)}</a></li>'
        for name in tag_names
    )
    return HTMLResponse(f"""<!DOCTYPE html>
<html>
<head><title>Fortinet External Feeds</title></head>
<body>
<h1>Available Service Tags</h1>
<p>{len(tag_names)} service tags available. Each link returns a plain-text list of IP/CIDR prefixes.</p>
<ul>{links}</ul>
</body>
</html>""")
