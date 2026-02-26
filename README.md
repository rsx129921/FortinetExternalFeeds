# Fortinet External Feeds

A lightweight FastAPI web service that downloads [Microsoft Azure IP Ranges and Service Tags](https://www.microsoft.com/en-us/download/details.aspx?id=56519) and serves them as plain-text IP/CIDR feeds compatible with FortiGate External Block List (Threat Feed) connectors.

Deployed to Azure Container Apps at:
**https://fortinet-external-feeds.thankfulpond-8b0a967e.northcentralus.azurecontainerapps.io**

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
| `GET /feeds/{service_tag}` | `text/plain` | IP/CIDR list, one per line (IPv4 only by default, rate limited: 60/min) |
| `GET /feeds/{service_tag}?ipv6=true` | `text/plain` | Include IPv6 prefixes |
| `GET /tags` | `application/json` | JSON array of all service tag names (rate limited: 30/min) |
| `GET /health` | `application/json` | Health check with data version and last refresh time |

## FortiGate Configuration

### CLI

Create an External Block List object pointing at the service:

```
config firewall external-block-list
    edit "Azure-Cloud-IPs"
        set type ip-addr
        set server-identity-check none
        set url "https://fortinet-external-feeds.thankfulpond-8b0a967e.northcentralus.azurecontainerapps.io/feeds/AzureCloud"
        set refresh-rate 1440
    next
end
```

`refresh-rate 1440` = poll every 1440 minutes (24 hours).

### GUI

1. Go to **Security Fabric > External Connectors**
2. Click **Create New > Threat Feed > IP Address**
3. Set **Name** to `Azure-Cloud-IPs`, paste the feed URL, set **Refresh Rate** to `1440`
4. Click **OK** and verify entries under **View Entries**

### Use in Firewall Policies

Reference the external block list as a destination address:

```
config firewall policy
    edit 0
        set name "Allow-to-Azure"
        set srcintf "internal"
        set dstintf "wan1"
        set srcaddr "all"
        set dstaddr "Azure-Cloud-IPs"
        set action accept
        set schedule "always"
        set service "ALL"
        set logtraffic all
    next
end
```

### Multiple Region/Service Feeds

```
config firewall external-block-list
    edit "Azure-EastUS"
        set type ip-addr
        set server-identity-check none
        set url "https://fortinet-external-feeds.thankfulpond-8b0a967e.northcentralus.azurecontainerapps.io/feeds/AzureCloud.EastUS"
        set refresh-rate 1440
    next
    edit "Azure-Storage"
        set type ip-addr
        set server-identity-check none
        set url "https://fortinet-external-feeds.thankfulpond-8b0a967e.northcentralus.azurecontainerapps.io/feeds/Storage"
        set refresh-rate 1440
    next
end
```

### Common Feed URLs

| Path | Description |
|---|---|
| `/feeds/AzureCloud` | All Azure public cloud IPs (~10,300 CIDRs) |
| `/feeds/AzureCloud.NorthCentralUS` | North Central US region |
| `/feeds/AzureCloud.EastUS` | East US region |
| `/feeds/AzureCloud.WestUS2` | West US 2 region |
| `/feeds/Storage` | Azure Storage service IPs |
| `/feeds/Sql` | Azure SQL service IPs |
| `/feeds/AzureTrafficManager` | Traffic Manager IPs |

Browse the full list of 3,100+ service tags at the root URL.

## Configuration

Environment variables:

| Variable | Default | Description |
|---|---|---|
| `REFRESH_INTERVAL_HOURS` | `24` | How often to re-download the Microsoft JSON |
| `LISTEN_HOST` | `0.0.0.0` | Bind address |
| `LISTEN_PORT` | `8080` | Bind port |
| `LOG_LEVEL` | `info` | Logging level (`debug`, `info`, `warning`, `error`, `critical`) |
| `API_TOKEN` | *(unset)* | Set to enable `?token=` auth on `/feeds/` and `/tags` |

## Security

The app is hardened for internet-facing deployment:

- Optional API key auth via `?token=` query parameter
- Security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy)
- Rate limiting (60/min on feeds, 30/min on tags/index)
- Input validation on service tag names
- XSS prevention via HTML escaping
- Swagger UI / OpenAPI disabled
- Startup retry with backoff
- httpx timeouts and response size limits
- Download URL hostname validation

## Azure Deployment

| Resource | Name |
|---|---|
| Resource Group | `eloinfra` |
| Container Registry | `eloinfra.azurecr.io` |
| Container Apps Environment | `eloinfra` |
| Container App | `fortinet-external-feeds` |
| Region | North Central US |

### Deploy an Update

```bash
# Build and push to ACR
az acr build --registry eloinfra --image fortinet-external-feeds:latest .

# Update the container app
az containerapp update \
  --name fortinet-external-feeds \
  --resource-group eloinfra \
  --image eloinfra.azurecr.io/fortinet-external-feeds:latest
```

See [docs/deployment.md](docs/deployment.md) for the full runbook including troubleshooting.

## Running Tests

```bash
pip install pytest pytest-asyncio
pytest -v
```

23 tests covering endpoints, security headers, auth, input validation, and URL verification.

## Data Source

[Azure IP Ranges and Service Tags - Public Cloud](https://www.microsoft.com/en-us/download/details.aspx?id=56519)
