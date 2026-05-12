# StakeMind — Build Todo

Tracked implementation checklist derived from [stakemind_updated_business_and_technical_workflow.md](../stakemind_updated_business_and_technical_workflow.md).

**Stack:** Next.js · TypeScript · Tailwind CSS · FastAPI · PostgreSQL · Redis

**Principles:** trust before automation · non-custodial · modular monolith · cache and async at the edges

---

## Phase 0 — Foundation and repository

- [x] Monorepo layout: `backend/`, `frontend/`, `infrastructure/`, `docker/`, `docs/`, `scripts/`, `tests/`
- [x] Backend scaffold: FastAPI app factory, env-based settings, structured logging, health checks, OpenAPI
- [x] Frontend scaffold: Next.js App Router, TypeScript, Tailwind, shared layout, env handling, API client layer
- [x] PostgreSQL: Docker Compose locally, migrations (Alembic), connection pooling (async SQLAlchemy)
- [x] Redis: cache and optional rate-limit/session backing; document TTL and invalidation rules
- [x] Docker Compose: API, Postgres, Redis, frontend dev proxy; one-command local start
- [x] CI: GitHub Actions — lint, typecheck, unit tests, image build; branch protection on `main` (enable protection in GitHub settings)
- [x] Secrets and config: `.env.example`, no secrets in repo, separate dev/staging/prod config
- [x] API contract: versioned REST (`/api/v1/...`), consistent errors, pagination and filter conventions

### Quality

- [ ] CI passes on the default branch: lint, typecheck, tests, and image build (runs in GitHub Actions after push)
- [ ] `docker compose up` yields healthy API, Postgres, Redis, and frontend dev proxy (verify locally with Docker installed)
- [x] OpenAPI documents versioned `/api/v1` error and pagination shapes
- [x] `.env.example` covers required variables; no secrets committed to the repo
- [x] New developer can run the stack locally from documented steps without ad hoc fixes

**Success:** one-command local stack, green CI, and API/frontend shells ready for feature work.

---

## Phase 1 — Research and validation

- [x] Map BitTensor staking flows: delegate, undelegate, redelegate, rewards, subnets
- [x] Competitive scan: dashboards, explorers, wallets; document pain points and gaps
- [x] Deliverables: competitor matrix, pain-point summary, positioning one-pager, architecture diagram
- [x] Draft data model: validators, subnets, stakes, rewards, wallet sessions (no private keys), audit events
- [x] Integration spike: read-only RPC/indexer calls with retries, timeouts, idempotent ingestion jobs

### Quality

- [x] Competitor matrix and pain-point summary reviewed and signed off
- [x] Architecture diagram and draft data model reviewed (stakes, sessions, audit events; no private keys)
- [x] Read-only RPC spike demonstrates retries, timeouts, and bounded ingestion behavior
- [x] Staking flows documented end to end: delegate, undelegate, redelegate, rewards, subnets

**Success:** build scope, integrations, and data shape are validated before dashboard implementation.

---

## Phase 2 — MVP dashboard (first milestone)

### Backend

- [x] API layer: BitTensor RPC client, aggregation, retry/backoff, sync jobs for validators and staking state
- [x] Read APIs: validators list/detail, staking positions by address, rewards summary, basic history
- [x] Persistence: normalized tables and indexes for list/filter/sort; summary tables if needed for list endpoints
- [x] Caching: Redis for validator catalog and heavy aggregates; keys tied to chain height or job watermark

### Frontend

- [x] Wallet connection: connect/disconnect, session UX, supported wallets; address visible, no key storage
- [x] Validator explorer: search, sort, filters, detail view
- [x] Staking visibility: positions, delegation breakdown, subnet exposure summary
- [x] Rewards dashboard: totals, trends (Recharts), time range selection
- [x] Historical tracking: charts and tables from stored snapshots, not live RPC on every page load

### Quality

- [x] AuthZ model: wallet address as identity; server never signs; scoped read access only
- [x] E2E smoke: connect wallet (or test address) → dashboard → validator detail → rewards

**Success:** users compare validators and track rewards without executing transactions.

---

## Phase 3 — Core staking actions

- [x] Transaction building API: unsigned payloads for stake, unstake, redelegate; simulation where supported
- [x] Signing UX: preview, fees/params, explicit confirm; hardware wallet path if in scope
- [x] Submission and tracking: hash status, confirmations, failure reasons, idempotent submit handling
- [x] Audit logging: who, what, when, tx hash, outcome (no secrets)
- [x] Integration tests: full lifecycle on testnet or mocked RPC; timeout and partial-failure cases

### Quality

- [x] Signing remains wallet-side only; backend returns unsigned payloads and never stores plaintext keys
- [x] Transaction preview and simulation run before every sign prompt; hardware wallet path covered if in scope
- [x] Audit log records every transaction attempt: who, what, when, hash, and outcome
- [x] Submit handling is idempotent; integration tests cover success, failure, and timeout paths

**Success:** users can stake, unstake, and redelegate with preview, confirmation, and tracked outcomes without breaking read-only dashboard flows.

---

## Phase 4 — Intelligence layer

- [ ] Validator intelligence engine: scoring, ranking, historical rollups, delegation trends, reputation signals
- [ ] Reward analytics engine: APY, consistency, trend windows, historical reports
- [ ] Risk monitoring engine: concentration, downtime, volatility, subnet exposure, alert inputs
- [ ] Batch jobs: scheduled recompute of scores and aggregates; backfill scripts for history
- [ ] UI: rankings, risk panels, allocation insights, compare validators, forecasting (labeled as estimates)

### Quality

- [ ] Scoring and risk formulas are documented and covered by unit tests on fixed fixtures
- [ ] Batch jobs keep rankings and historical aggregates within agreed freshness SLOs
- [ ] UI labels estimates and limitations clearly; rankings match documented rules
- [ ] Cache and database design avoid full recompute on every page load

**Success:** users get validator comparison, risk context, allocation insights, and performance trends that go beyond a standard staking dashboard.

---

## Phase 5 — Premium

- [ ] Plans and entitlements: free vs premium feature flags; subscription or invite model
- [ ] Premium APIs: advanced scores, optimization hints, exports, deeper subnet analytics, priority refresh
- [ ] Smart alerts: rules engine, delivery (in-app/email/webhook), dedupe and quiet hours
- [ ] Reporting: CSV/PDF exports, portfolio recommendations with disclaimers; no auto-execution by default

### Quality

- [ ] Entitlements enforce free vs premium on the server, not only in the UI
- [ ] Alerts dedupe and respect quiet hours; exports and recommendations carry clear disclaimers
- [ ] Billing or invite flow is tested end to end; premium surfaces stay gated after refresh and re-login

**Success:** paying users unlock documented premium APIs and surfaces without changing the free-tier experience.

---

## Phase 6 — Automation (optional, post-trust)

- [ ] Policy engine: user limits, caps, allowlists, kill switch
- [ ] Job queue: durable workers (Celery, RQ, Arq, or similar), not in-process cron only
- [ ] Features: auto-compound, smart reallocation, schedules; legal copy and security review
- [ ] Failure modes: stuck txs, RPC drift, partial fills; user-visible incident states

### Quality

- [ ] Policy engine enforces limits, caps, allowlists, and a user-controlled kill switch before any autonomous action
- [ ] Durable workers handle queued jobs; stuck transactions and RPC drift surface clearly in the UI
- [ ] Automation is opt-in with explicit limits; security and legal review completed before release

**Success:** optional automation runs only within user policy, never bypasses wallet signing, and failures stay visible and bounded.

---

## Cross-cutting

### Security and trust

- [ ] Input validation on all APIs; rate limiting; CORS and security headers
- [ ] Security testing: sessions, injection, unauthorized reads, abuse of tx endpoints
- [ ] Public docs: non-custodial model, what is stored, what is never stored

### Testing

- [ ] Unit: reward math, scoring, RPC adapters (mocked)
- [ ] Integration: ingestion, API contracts, staking lifecycle
- [ ] Failure drills: RPC outage, stale indexer, inconsistent chain state

### Deployment and operations

- [ ] Staging environment mirroring production topology
- [ ] Production: API behind reverse proxy, TLS, DB backups, Redis persistence policy
- [ ] Monitoring: uptime, RPC latency, job lag, tx success rate, error tracking (e.g. Sentry)
- [ ] Runbooks: dependency updates, RPC upgrades, rollback

### Growth (post-MVP)

- [ ] Landing and docs; validator research content; community channels (X, Discord, GitHub, BitTensor)

---

## Suggested build order (first 4–6 weeks)

1. Phase 0 — monorepo, Docker, CI
2. Phase 1 — spike, data model, read-only ingestion
3. Phase 2 — wallet, validator explorer, rewards (read-only)
4. Hardening — caching, indexes, observability
5. Phase 3 — staking actions after Phase 2 trust signals look good
6. Phase 4 — scoring and risk once historical data supports it

---

## Scalability notes

| Area | Recommendation |
|------|----------------|
| Frontend | App Router; server components where they shrink client bundle; TanStack Query for server state; shared types from OpenAPI or a small shared package |
| Backend | Domain packages (`validator_intelligence`, `analytics`, `risk_engine`, `staking`, `wallets`); thin route handlers; background workers for ingestion and scoring |
| Database | Time-series-friendly reward tables; indexes on validator id, subnet, wallet, block/time; read replicas when read load dominates |
| Cache | Redis for catalog and aggregates; invalidate on job completion or chain watermark |
| Realtime | WebSockets or SSE later for tx status and alerts; polling is fine for MVP |
