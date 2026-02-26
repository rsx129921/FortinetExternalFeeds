# Fortinet External Feeds API — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a FastAPI web service that fetches Microsoft Azure ServiceTags JSON and serves individual service tags as plain-text IP/CIDR feeds for FortiGate external connectors.

**Architecture:** Single FastAPI app with in-memory cache. Downloads the Microsoft ServiceTags JSON on startup, refreshes every 24 hours via background task. Each service tag is served as a plain-text endpoint at `/feeds/{tag_name}` with one CIDR per line.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, httpx (async HTTP), Docker

---

### Task 1: Initialize git repo and project scaffolding

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `CLAUDE.md`
- Create: `app/__init__.py`

**Step 1: Initialize git repo**

Run: `git init`

**Step 2: Create `.gitignore`**

```
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
.env
.venv/
venv/
*.log
.idea/
.vscode/
```

**Step 3: Create `requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
httpx==0.28.0
```

**Step 4: Create `.env.example`**

```
REFRESH_INTERVAL_HOURS=24
LISTEN_HOST=0.0.0.0
LISTEN_PORT=8080
LOG_LEVEL=info
```

**Step 5: Create `CLAUDE.md`**

```markdown
# Fortinet External Feeds API

## Project
FastAPI app serving Microsoft Azure IP ranges as plain-text feeds for FortiGate external connectors.

## Commands
- Run dev: `uvicorn app.main:app --reload --port 8080`
- Run tests: `pytest -v`
- Build Docker: `docker build -t fortinet-external-feeds .`
- Run Docker: `docker run -p 8080:8080 fortinet-external-feeds`

## Structure
- `app/main.py` — FastAPI app, routes, lifespan
- `app/config.py` — Settings from env vars
- `app/fetcher.py` — Download + parse Microsoft ServiceTags JSON
- `app/cache.py` — In-memory cache management

## Conventions
- Python 3.12, type hints on all functions
- async endpoints and HTTP calls (httpx)
- Plain text responses for /feeds/ endpoints (one CIDR per line)
```

**Step 6: Create `app/__init__.py`**

Empty file.

**Step 7: Commit**

```bash
git add .gitignore requirements.txt .env.example CLAUDE.md app/__init__.py
git commit -m "chore: initialize project scaffolding"
```

---

### Task 2: Config module

**Files:**
- Create: `app/config.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`

**Step 1: Write the failing test**

Create `tests/__init__.py` (empty) and `tests/test_config.py`:

```python
from app.config import Settings


def test_default_settings():
    settings = Settings()
    assert settings.refresh_interval_hours == 24
    assert settings.listen_host == "0.0.0.0"
    assert settings.listen_port == 8080
    assert settings.log_level == "info"


def test_custom_settings(monkeypatch):
    monkeypatch.setenv("REFRESH_INTERVAL_HOURS", "12")
    monkeypatch.setenv("LISTEN_PORT", "9090")
    settings = Settings()
    assert settings.refresh_interval_hours == 12
    assert settings.listen_port == 9090
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `app.config` doesn't exist yet

**Step 3: Write minimal implementation**

Create `app/config.py`:

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    refresh_interval_hours: int = 24
    listen_host: str = "0.0.0.0"
    listen_port: int = 8080
    log_level: str = "info"


settings = Settings()
```

Also add `pydantic-settings==2.6.0` to `requirements.txt`.

**Step 4: Install deps and run test to verify it passes**

Run: `pip install -r requirements.txt && pytest tests/test_config.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add app/config.py tests/ requirements.txt
git commit -m "feat: add config module with env var settings"
```

---

### Task 3: Cache module

**Files:**
- Create: `app/cache.py`
- Create: `tests/test_cache.py`

**Step 1: Write the failing test**

Create `tests/test_cache.py`:

```python
from app.cache import FeedCache


def test_empty_cache():
    cache = FeedCache()
    assert cache.get_tag("AzureCloud") is None
    assert cache.get_all_tags() == []
    assert cache.change_number is None
    assert cache.last_refresh is None


def test_load_data():
    cache = FeedCache()
    sample_data = {
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
                    "addressPrefixes": [
                        "10.0.0.0/8",
                        "172.16.0.0/12",
                        "2001:db8::/32",
                    ],
                    "networkFeatures": ["API", "NSG"],
                },
            },
        ],
    }
    cache.load(sample_data)
    assert cache.change_number == 100
    assert cache.last_refresh is not None
    assert cache.get_all_tags() == ["AzureCloud"]


def test_get_tag_ipv4_only():
    cache = FeedCache()
    cache.load({
        "changeNumber": 1,
        "cloud": "Public",
        "values": [
            {
                "name": "TestTag",
                "id": "TestTag",
                "properties": {
                    "changeNumber": 1,
                    "region": "",
                    "regionId": 0,
                    "platform": "Azure",
                    "systemService": "",
                    "addressPrefixes": [
                        "10.0.0.0/8",
                        "192.168.1.0/24",
                        "2001:db8::/32",
                    ],
                    "networkFeatures": [],
                },
            },
        ],
    })
    result = cache.get_tag("TestTag", include_ipv6=False)
    assert result == ["10.0.0.0/8", "192.168.1.0/24"]


def test_get_tag_with_ipv6():
    cache = FeedCache()
    cache.load({
        "changeNumber": 1,
        "cloud": "Public",
        "values": [
            {
                "name": "TestTag",
                "id": "TestTag",
                "properties": {
                    "changeNumber": 1,
                    "region": "",
                    "regionId": 0,
                    "platform": "Azure",
                    "systemService": "",
                    "addressPrefixes": [
                        "10.0.0.0/8",
                        "2001:db8::/32",
                    ],
                    "networkFeatures": [],
                },
            },
        ],
    })
    result = cache.get_tag("TestTag", include_ipv6=True)
    assert result == ["10.0.0.0/8", "2001:db8::/32"]


def test_get_nonexistent_tag():
    cache = FeedCache()
    cache.load({
        "changeNumber": 1,
        "cloud": "Public",
        "values": [],
    })
    assert cache.get_tag("DoesNotExist") is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cache.py -v`
Expected: FAIL — `app.cache` doesn't exist yet

**Step 3: Write minimal implementation**

Create `app/cache.py`:

```python
import ipaddress
from datetime import datetime, timezone


class FeedCache:
    def __init__(self):
        self._tags: dict[str, list[str]] = {}
        self.change_number: int | None = None
        self.last_refresh: datetime | None = None

    def load(self, data: dict) -> None:
        self.change_number = data["changeNumber"]
        self.last_refresh = datetime.now(timezone.utc)
        self._tags = {}
        for entry in data.get("values", []):
            name = entry["name"]
            prefixes = entry.get("properties", {}).get("addressPrefixes", [])
            self._tags[name] = prefixes

    def get_all_tags(self) -> list[str]:
        return sorted(self._tags.keys())

    def get_tag(self, name: str, include_ipv6: bool = False) -> list[str] | None:
        prefixes = self._tags.get(name)
        if prefixes is None:
            return None
        if include_ipv6:
            return prefixes
        return [p for p in prefixes if _is_ipv4(p)]


def _is_ipv4(prefix: str) -> bool:
    try:
        return isinstance(ipaddress.ip_network(prefix, strict=False), ipaddress.IPv4Network)
    except ValueError:
        return False
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cache.py -v`
Expected: 5 passed

**Step 5: Commit**

```bash
git add app/cache.py tests/test_cache.py
git commit -m "feat: add in-memory feed cache with IPv4/IPv6 filtering"
```

---

### Task 4: Fetcher module

**Files:**
- Create: `app/fetcher.py`
- Create: `tests/test_fetcher.py`

**Step 1: Write the failing test**

Create `tests/test_fetcher.py`:

```python
import httpx
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


@pytest.mark.anyio
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


@pytest.mark.anyio
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
```

Also add to `requirements.txt`:
```
anyio==4.7.0
pytest==8.3.0
pytest-anyio==0.0.0
```

Wait — use `pytest-asyncio` instead:
```
pytest==8.3.0
anyio==4.7.0
pytest-asyncio==0.24.0
```

And use `@pytest.mark.asyncio` instead of `@pytest.mark.anyio`. Update the test markers accordingly.

**Step 2: Run test to verify it fails**

Run: `pip install -r requirements.txt && pytest tests/test_fetcher.py -v`
Expected: FAIL — `app.fetcher` doesn't exist

**Step 3: Write minimal implementation**

Create `app/fetcher.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_fetcher.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add app/fetcher.py tests/test_fetcher.py requirements.txt
git commit -m "feat: add fetcher module to discover and download ServiceTags JSON"
```

---

### Task 5: FastAPI app with routes

**Files:**
- Create: `app/main.py`
- Create: `tests/test_main.py`

**Step 1: Write the failing test**

Create `tests/test_main.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py -v`
Expected: FAIL — `app.main` doesn't exist

**Step 3: Write minimal implementation**

Create `app/main.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py -v`
Expected: 6 passed

**Step 5: Commit**

```bash
git add app/main.py tests/test_main.py
git commit -m "feat: add FastAPI app with feed, health, tags, and index endpoints"
```

---

### Task 6: Dockerfile and docker-compose

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`

**Step 1: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=60s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Step 2: Create `docker-compose.yml`**

```yaml
services:
  feeds:
    build: .
    ports:
      - "8080:8080"
    environment:
      - REFRESH_INTERVAL_HOURS=24
      - LOG_LEVEL=info
    restart: unless-stopped
```

**Step 3: Build and verify**

Run: `docker build -t fortinet-external-feeds .`
Expected: Build succeeds

**Step 4: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "feat: add Dockerfile and docker-compose for containerized deployment"
```

---

### Task 7: Run all tests and verify end-to-end

**Step 1: Run full test suite**

Run: `pytest -v`
Expected: All tests pass

**Step 2: Start the app locally and test**

Run: `uvicorn app.main:app --port 8080 &`
Then:
- `curl http://localhost:8080/health` — should return JSON with status ok
- `curl http://localhost:8080/tags` — should return JSON array of tag names
- `curl http://localhost:8080/feeds/AzureCloud` — should return plain-text IP list
- `curl http://localhost:8080/` — should return HTML index page

**Step 3: Stop the app and commit any fixes**

If any fixes were needed, commit them.

**Step 4: Final commit**

```bash
git add -A
git commit -m "chore: finalize project, all tests passing"
```
