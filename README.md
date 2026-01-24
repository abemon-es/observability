# abemon.es Observability Stack

Self-hosted observability platform for abemon.es infrastructure.

## Architecture

```
status.abemon.es  →  Uptime Kuma (public status page)
logs.abemon.es    →  Grafana + Loki + Prometheus (internal)
```

## Components

| Service | Purpose | Port |
|---------|---------|------|
| Uptime Kuma | Status page, uptime monitoring | 3001 |
| Grafana | Dashboards, alerting | 3000 |
| Loki | Log aggregation | 3100 |
| Prometheus | Metrics collection | 9090 |
| Vector | Log shipping | 8686 |

## Quick Start

### Local Development

```bash
# Clone and start
cd ~/desarrollos/observability
docker-compose up -d

# Access services
open http://localhost:3001  # Uptime Kuma
open http://localhost:3000  # Grafana
```

### CLI Tool

```bash
# Install logcli
brew install loki

# Symlink obs-turbo
ln -sf ~/desarrollos/observability/cli/obs-turbo ~/bin/obs-turbo

# Configure
obs-turbo config

# Usage
obs-turbo logs abemon --last 1h
obs-turbo tail bm --filter error
obs-turbo status
obs-turbo incidents
```

## Deployment (Railway)

1. Link to Railway:
   ```bash
   railway link
   ```

2. Set environment variables:
   ```bash
   railway variables set GOOGLE_CLIENT_ID=xxx
   railway variables set GOOGLE_CLIENT_SECRET=xxx
   railway variables set GRAFANA_ADMIN_PASSWORD=xxx
   ```

3. Deploy:
   ```bash
   railway up
   ```

## DNS (Cloudflare)

| Subdomain | Target |
|-----------|--------|
| status.abemon.es | Railway Uptime Kuma |
| logs.abemon.es | Railway Grafana |

## Authentication

- **status.abemon.es**: Public (read-only status page)
- **logs.abemon.es**: Google OAuth (whitelisted users)

## Monitored Services

### Railway
- abemon.es
- bm.consulting
- codex.abemon.es
- foodplan.pro

### Hostinger
- blue-mountain.es
- concursal.consulting
- dev.fundacionojusa.com
- logisticsexpress.es

### External
- EnvioXEnvio API
- Zoho APIs
- Google APIs
- SSL certificates
- DNS resolution

## Branding

Colors match abemon.es:
- Primary: #1a1a2e
- Secondary: #16213e
- Accent: #0f3460
- Highlight: #e94560

## License

Private - abemon.es
