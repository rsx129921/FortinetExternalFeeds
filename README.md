# Fortinet External Feeds

A lightweight FastAPI web service that downloads [Microsoft Azure IP Ranges and Service Tags](https://www.microsoft.com/en-us/download/details.aspx?id=56519) and serves them as plain-text IP/CIDR feeds compatible with FortiGate External Block List (Threat Feed) connectors.

## How It Works

1. On startup, the app fetches the latest Azure ServiceTags JSON from Microsoft (~4 MB, ~3,100 service tags)
2. The data is cached in memory and refreshed every 24 hours (configurable)
3. Each service tag is available as a plain-text endpoint returning one IP/CIDR per line

Microsoft updates the file weekly. New ranges are not used in Azure for at least one week after publication.

## Quick Start

### Docker (recommended)

```bash
docker compose up -d
```

### Local

```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows
# source .venv/bin/activate    # Linux/macOS
pip install -r requirements.txt
uvicorn app.main:app --port 8080
```

The app will be available at `http://localhost:8080`.

## API Endpoints

| Endpoint | Content-Type | Description |
|---|---|---|
| `GET /` | `text/html` | Browseable index of all available service tags |
| `GET /feeds/{service_tag}` | `text/plain` | IP/CIDR list, one per line (IPv4 only by default) |
| `GET /feeds/{service_tag}?ipv6=true` | `text/plain` | Include IPv6 prefixes |
| `GET /tags` | `application/json` | JSON array of all service tag names |
| `GET /health` | `application/json` | Health check with data version and last refresh time |

## FortiGate Configuration

Create an External Block List object pointing at your server:

```
config firewall external-block-list
    edit "Azure-IPs"
        set type ip-addr
        set server-identity-check none
        set url "http://your-server:8080/feeds/AzureCloud"
        set refresh-rate 1440
    next
end
```

### Common Feed URLs

| URL | Description |
|---|---|
| `/feeds/AzureCloud` | All Azure public cloud IPs |
| `/feeds/AzureCloud.eastus` | Azure East US region only |
| `/feeds/AzureCloud.westeurope` | Azure West Europe region only |
| `/feeds/Storage` | Azure Storage service IPs |
| `/feeds/Sql` | Azure SQL service IPs |
| `/feeds/AzureTrafficManager` | Azure Traffic Manager IPs |

Browse `http://your-server:8080/` for the full list of 3,100+ available service tags.

## Configuration

Environment variables:

| Variable | Default | Description |
|---|---|---|
| `REFRESH_INTERVAL_HOURS` | `24` | How often to re-download the Microsoft JSON |
| `LISTEN_HOST` | `0.0.0.0` | Bind address |
| `LISTEN_PORT` | `8080` | Bind port |
| `LOG_LEVEL` | `info` | Logging level |

## Running Tests

```bash
pip install pytest pytest-asyncio
pytest -v -o asyncio_mode=auto
```

## Data Source

[Azure IP Ranges and Service Tags - Public Cloud](https://www.microsoft.com/en-us/download/details.aspx?id=56519)
