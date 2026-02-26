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
