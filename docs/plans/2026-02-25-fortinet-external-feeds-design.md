# Fortinet External Feeds API — Design

## Problem

FortiGate firewalls need to consume Microsoft Azure IP ranges as External Block List (Threat Feed) objects. Microsoft publishes these as a single JSON file at https://www.microsoft.com/en-us/download/details.aspx?id=56519 which updates weekly. FortiGate threat feeds expect plain-text lists of IP/CIDR prefixes, one per line, served over HTTP.

## Solution

A Python FastAPI application that downloads the Microsoft ServiceTags JSON, caches it in memory, and serves individual service tags as plain-text IP/CIDR feeds compatible with FortiGate external connectors.

## Architecture

- **Framework:** Python 3.12 + FastAPI + Uvicorn
- **Caching:** In-memory dict keyed by service tag name
- **Refresh:** Background task every 24 hours (configurable via `REFRESH_INTERVAL_HOURS` env var)
- **Startup:** Initial download completes before the app serves requests
- **Deployment:** Docker container

### Data Flow

1. On startup, scrape the Microsoft download page to discover the current JSON URL
2. Download and parse the JSON, store in memory keyed by service tag name
3. Every 24 hours, repeat steps 1-2 in a background task
4. On `GET /feeds/{tag}`, look up the tag, filter to IPv4 by default, return one prefix per line

### API Endpoints

| Endpoint | Content-Type | Purpose |
|---|---|---|
| `GET /` | `text/html` | Index page listing all available service tags as links |
| `GET /feeds/{service_tag}` | `text/plain` | IP/CIDR list, one per line (IPv4 only by default) |
| `GET /feeds/{service_tag}?ipv6=true` | `text/plain` | Include IPv6 prefixes |
| `GET /health` | `application/json` | Health check, last refresh time, changeNumber |
| `GET /tags` | `application/json` | List of all available service tag names |

### IP Version Handling

- Default: IPv4 only (FortiGate threat feeds typically only support IPv4)
- `?ipv6=true` query parameter includes IPv6 prefixes (future-proofing; MS plans to add IPv6)

## Project Structure

```
FortinetExternalFeeds/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, routes, lifespan
│   ├── config.py         # Settings via env vars
│   ├── fetcher.py        # Download + parse Microsoft JSON
│   └── cache.py          # In-memory cache management
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .gitignore
├── .env.example
└── CLAUDE.md
```

## Configuration (environment variables)

| Variable | Default | Description |
|---|---|---|
| `REFRESH_INTERVAL_HOURS` | `24` | How often to re-download the JSON |
| `LISTEN_HOST` | `0.0.0.0` | Bind address |
| `LISTEN_PORT` | `8080` | Bind port |
| `LOG_LEVEL` | `info` | Logging level |

## Docker

- Base image: `python:3.12-slim`
- Exposed port: 8080
- Non-root user
- Health check: `GET /health`

## Key Notes from Microsoft

- File updates weekly; new ranges not used in Azure for at least one week
- Currently IPv4 only; IPv6 schema extension planned
- Platform addresses (168.63.129.16, FE80::1234:5678:9ABC/128) are NOT in the JSON
- `changeNumber` field tracks the version of the data
