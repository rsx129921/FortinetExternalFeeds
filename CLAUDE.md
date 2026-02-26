# Fortinet External Feeds API

## Project
FastAPI app serving Microsoft Azure IP ranges as plain-text feeds for FortiGate external connectors. Deployed to Azure Container Apps.

## Commands
- Run dev: `uvicorn app.main:app --reload --port 8080`
- Run tests: `pytest -v`
- Build Docker: `docker build -t fortinet-external-feeds .`
- Run Docker: `docker run -p 8080:8080 fortinet-external-feeds`
- Build & push to ACR: `az acr build --registry eloinfra --image fortinet-external-feeds:latest .`
- Deploy update: `az containerapp update --name fortinet-external-feeds --resource-group eloinfra --image eloinfra.azurecr.io/fortinet-external-feeds:latest`

## Azure Deployment
- **Resource Group:** eloinfra (North Central US)
- **Container Registry:** eloinfra.azurecr.io
- **Container App:** fortinet-external-feeds
- **Environment:** eloinfra
- **Live URL:** https://fortinet-external-feeds.thankfulpond-8b0a967e.northcentralus.azurecontainerapps.io
- **Feed example:** https://fortinet-external-feeds.thankfulpond-8b0a967e.northcentralus.azurecontainerapps.io/feeds/AzureCloud

## Structure
- `app/main.py` — FastAPI app, routes, lifespan, security middleware, auth, rate limiting
- `app/config.py` — Settings from env vars (Literal-validated log_level, optional api_token)
- `app/fetcher.py` — Download + parse Microsoft ServiceTags JSON (with timeouts, URL validation, size limits)
- `app/cache.py` — In-memory cache management (atomic swap on refresh)

## Security
- Optional API key auth via `?token=` query param (set `API_TOKEN` env var to enable)
- Security headers middleware (HSTS, CSP, X-Frame-Options, nosniff, no-store)
- Rate limiting: 60/min on /feeds/, 30/min on /tags and /
- Input validation regex on service_tag path parameter
- Swagger UI / OpenAPI disabled in production
- Startup retry with backoff (5 attempts, 30s delay)
- httpx timeouts (connect=10s, read=60s) and 20MB response size ceiling
- Download URL hostname validation against download.microsoft.com

## Conventions
- Python 3.12, type hints on all functions
- async endpoints and HTTP calls (httpx)
- Plain text responses for /feeds/ endpoints (one CIDR per line)
- 23 unit tests (pytest -v)
