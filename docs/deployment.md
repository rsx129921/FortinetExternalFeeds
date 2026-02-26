# Fortinet External Feeds — Deployment Runbook

## Azure Resources

| Resource | Name | Location |
|---|---|---|
| Resource Group | eloinfra | North Central US |
| Container Registry | eloinfra.azurecr.io | North Central US |
| Container Apps Environment | eloinfra | North Central US |
| Container App | fortinet-external-feeds | North Central US |

**Live URL:** https://fortinet-external-feeds.thankfulpond-8b0a967e.northcentralus.azurecontainerapps.io

---

## Deploy an Update

### 1. Build and push to ACR

```bash
cd C:\Users\Trace.King\infra\repos\scripts\FortinetExternalFeeds
az acr build --registry eloinfra --image fortinet-external-feeds:latest .
```

### 2. Update the container app

```bash
az containerapp update \
  --name fortinet-external-feeds \
  --resource-group eloinfra \
  --image eloinfra.azurecr.io/fortinet-external-feeds:latest
```

### 3. Verify

```bash
curl https://fortinet-external-feeds.thankfulpond-8b0a967e.northcentralus.azurecontainerapps.io/health
```

Expected: `{"status":"ok","change_number":...,"last_refresh":"..."}`

---

## Environment Variables

Set via `az containerapp update --set-env-vars`:

| Variable | Default | Description |
|---|---|---|
| `REFRESH_INTERVAL_HOURS` | `24` | How often to re-download Microsoft JSON |
| `LISTEN_HOST` | `0.0.0.0` | Bind address |
| `LISTEN_PORT` | `8080` | Bind port |
| `LOG_LEVEL` | `info` | Logging level (`debug`, `info`, `warning`, `error`, `critical`) |
| `API_TOKEN` | *(unset)* | Set to enable token auth on /feeds/ and /tags (e.g. `?token=YOUR_TOKEN`) |

### Example: Enable API token auth

```bash
az containerapp update \
  --name fortinet-external-feeds \
  --resource-group eloinfra \
  --set-env-vars "API_TOKEN=your-secret-token-here"
```

FortiGate feed URL becomes: `https://.../feeds/AzureCloud?token=your-secret-token-here`

---

## FortiGate Configuration

### CLI — External Block List (Threat Feed)

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

> `refresh-rate 1440` = poll every 1440 minutes (24 hours), matching the server-side refresh.

### GUI — Fabric > External Connectors

1. Go to **Security Fabric > External Connectors**
2. Click **Create New > Threat Feed > IP Address**
3. Configure:
   - **Name:** `Azure-Cloud-IPs`
   - **URL:** `https://fortinet-external-feeds.thankfulpond-8b0a967e.northcentralus.azurecontainerapps.io/feeds/AzureCloud`
   - **Refresh Rate:** `1440` minutes
   - **Server Identity Check:** Disable (or configure TLS verification if using a custom cert)
4. Click **OK** and verify the feed shows entries under **View Entries**

### Using in Firewall Policies

Reference the external block list as an address object in policies:

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

### Multiple Region-Specific Feeds

Create separate connectors per region or service:

```
config firewall external-block-list
    edit "Azure-EastUS"
        set type ip-addr
        set server-identity-check none
        set url "https://fortinet-external-feeds.thankfulpond-8b0a967e.northcentralus.azurecontainerapps.io/feeds/AzureCloud.EastUS"
        set refresh-rate 1440
    next
    edit "Azure-WestUS2"
        set type ip-addr
        set server-identity-check none
        set url "https://fortinet-external-feeds.thankfulpond-8b0a967e.northcentralus.azurecontainerapps.io/feeds/AzureCloud.WestUS2"
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

| Feed URL Path | Description |
|---|---|
| `/feeds/AzureCloud` | All Azure public cloud IPs (~10,300 CIDRs) |
| `/feeds/AzureCloud.NorthCentralUS` | North Central US region only |
| `/feeds/AzureCloud.EastUS` | East US region |
| `/feeds/AzureCloud.WestUS2` | West US 2 region |
| `/feeds/Storage` | Azure Storage service IPs |
| `/feeds/Sql` | Azure SQL service IPs |
| `/feeds/AzureTrafficManager` | Traffic Manager IPs |

Browse all available tags at: https://fortinet-external-feeds.thankfulpond-8b0a967e.northcentralus.azurecontainerapps.io/

### With API Token Auth

If `API_TOKEN` is set on the container, append `?token=` to the URL:

```
set url "https://fortinet-external-feeds.thankfulpond-8b0a967e.northcentralus.azurecontainerapps.io/feeds/AzureCloud?token=your-secret-token-here"
```

---

## Troubleshooting

### Check container logs

```bash
az containerapp logs show --name fortinet-external-feeds --resource-group eloinfra --follow
```

### Check container status

```bash
az containerapp show --name fortinet-external-feeds --resource-group eloinfra --query "{state:properties.runningStatus, fqdn:properties.configuration.ingress.fqdn}" -o table
```

### Force restart

```bash
az containerapp revision restart --name fortinet-external-feeds --resource-group eloinfra --revision $(az containerapp revision list --name fortinet-external-feeds --resource-group eloinfra --query "[0].name" -o tsv)
```

### Rebuild from scratch

```bash
az acr build --registry eloinfra --image fortinet-external-feeds:latest .
az containerapp update --name fortinet-external-feeds --resource-group eloinfra --image eloinfra.azurecr.io/fortinet-external-feeds:latest
```
