# Deployment and operations

This document describes how to run StakeMind in **staging** and **production**, harden the edge, back up data, observe health, and execute common **runbooks**. It complements [security-and-trust.md](security-and-trust.md).

## Topology

Recommended layout (staging should mirror production, with smaller pools and non-prod secrets):

| Tier | Components |
|------|------------|
| Edge | TLS terminator + reverse proxy (Caddy, nginx, Traefik, or cloud load balancer) |
| App | FastAPI (`api` service), Next.js (`frontend` service) |
| Data | PostgreSQL (primary), Redis (cache / sessions / rate limits) |
| Jobs | Workers: ingestion sync, intelligence recompute, automation worker (see `backend/scripts/`) |

Local parity is provided by [docker-compose.yml](../docker-compose.yml): `postgres`, `redis`, `api`, `frontend`.

### Staging

- Use the **same service graph** as production (API, frontend, Postgres, Redis, workers).
- Use **separate** databases, Redis instances, DNS names, and secrets from production.
- Point `CORS_ORIGINS`, `NEXT_PUBLIC_API_URL`, and public API URLs at staging hostnames.
- Copy [.env.staging.example](../.env.staging.example) to `.env.staging` and pass it to Compose or your orchestrator (`docker compose --env-file .env.staging` where supported, or merge `env_file` into the API service).
- Prefer **realistic** BitTensor RPC endpoints and timeouts so RPC latency and failure modes match production.

### Production

- **Never** expose Postgres or Redis ports on the public internet; only the reverse proxy should be reachable on `443` (and `80` only for ACME redirects if applicable).
- Terminate **TLS** at the proxy or load balancer; forward to the API over HTTP on a private network, or re-encrypt to HTTPS upstream as your platform requires.
- Set `TRUST_X_FORWARDED_FOR=true` on the API **only** when the proxy strips client spoofing and sets `X-Forwarded-For` correctly.
- Enable `SECURITY_HSTS_ENABLED=true` once you are sure all clients use HTTPS on the canonical host.
- Enable `RATE_LIMIT_ENABLED=true` in production when Redis is reliable; tune `RATE_LIMIT_PER_MINUTE`.

#### Reverse proxy sketch (nginx)

The API listens on port `8000` inside the Docker network. Example upstream (adjust names and TLS certificates):

```nginx
upstream stakemind_api {
    server api:8000;
    keepalive 32;
}

server {
    listen 443 ssl http2;
    server_name api.stakemind.example;
    ssl_certificate     /etc/ssl/certs/stakemind.crt;
    ssl_certificate_key /etc/ssl/private/stakemind.key;

    location / {
        proxy_pass http://stakemind_api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Serve the Next.js app on a separate `server_name` (e.g. `app.stakemind.example`) or use your platform’s static/hosting integration.

#### PostgreSQL backups

- Schedule **logical dumps** (e.g. nightly `pg_dump`) for portability and restores to dev.
- For production, add **continuous archiving / PITR** (WAL archiving, managed RDS backups, etc.) per your cloud provider; the repo includes a simple Compose-oriented helper:

```bash
# From repository root (Compose stack running)
./scripts/backup-postgres.sh
```

PowerShell: `.\scripts\backup-postgres.ps1`

Store artifacts off-host (object storage, encrypted volume) and test restores quarterly.

#### Redis persistence

- Default Compose Redis is **ephemeral** unless you mount data and enable persistence.
- For production, prefer **managed Redis** with an explicit persistence and eviction policy, or enable **AOF** (`appendonly yes`) and disk backups if self-hosted.
- Rate-limit and session keys are safe to lose on failover, but expect brief UX impact (re-login, softer rate limits until Redis repopulates).

## Monitoring

| Signal | Suggested approach |
|--------|---------------------|
| Uptime | Synthetic `GET /api/v1/health` from your probe (UptimeRobot, Pingdom, k8s liveness, etc.) |
| API / DB / Redis | Parse `checks` in the health JSON (`database`, `redis`) |
| RPC latency | Log structured timings around Subtensor calls; alert on p95 timeout rate; track `BITTENSOR_RPC_TIMEOUT_SECONDS` tuning |
| Job lag | Monitor worker logs / queue depth (PostgreSQL job tables for automation; ingestion `ingestion_runs` freshness) |
| Transaction success | Metrics from `staking_transactions` status counts (dashboard or SQL) |
| Errors | Ship logs to your aggregator; optional **Sentry** (`SENTRY_DSN` in env when you wire the SDK) |

## Runbooks

### Dependency updates (Python / Node)

1. On a branch, update `backend/requirements.txt` or `frontend/package.json` / lockfile in a single concern (security patch vs major bump).
2. Run `ruff check .` and `pytest` in `backend/`; `npm run lint`, `typecheck`, and `build` in `frontend/`.
3. Run Docker image builds locally (`docker compose build`).
4. Deploy to **staging** first; smoke-test wallet session, validator list, health, and one write path if applicable.
5. Deploy to production during a window with rollback ready (see below).

### BitTensor RPC upgrades

1. Confirm new endpoint URL and TLS roots from the provider.
2. Update `BITTENSOR_RPC_URL` (and timeouts/retries if needed) in staging `.env`.
3. Restart API and workers; verify `GET /api/v1/integrations/subtensor/chain-head` and ingestion scripts.
4. Roll the same change to production after staging soak.

### Rollback

1. **Containers**: redeploy the previous image digest or Git tag your release pipeline recorded.
2. **Database**: avoid destructive migrations without backups; if a migration ran, restore from pre-deploy snapshot or forward-fix with a new migration (prefer forward-fix for short outages).
3. **Redis**: flushing is acceptable only if you accept session/rate-limit reset; prefer TTL-based keys as today.
4. **Frontend**: revert to previous static build or container tag; purge CDN cache if used.

## Related files

- [.env.staging.example](../.env.staging.example), [.env.production.example](../.env.production.example)
- [docker-compose.yml](../docker-compose.yml)
- [scripts/backup-postgres.sh](../scripts/backup-postgres.sh), [scripts/backup-postgres.ps1](../scripts/backup-postgres.ps1)
