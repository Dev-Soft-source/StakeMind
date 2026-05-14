# StakeMind — project review guide

Use this document when you want to **see how the system fits together**, **read the dashboard top to bottom**, and **run tests in a sensible order**.

---

## 1. How the project works

### Big picture

StakeMind is a **monorepo**: a **Next.js** frontend talks to a **FastAPI** backend over HTTP. The backend uses **PostgreSQL** for durable data and **Redis** for caching, sessions, and optional rate limiting. Optional jobs (ingestion, intelligence rollups, automation) run as **Python scripts** or workers against the same database.

```text
Browser  →  Next.js (frontend/)  →  REST JSON  →  FastAPI (backend/app/)
                                              ↘
                                    PostgreSQL + Redis
                                              ↘
                              BitTensor RPC (read-only chain metadata)
```

### Repository layout (high signal paths)

| Area | Path | Role |
|------|------|------|
| API routes | `backend/app/api/v1/` | HTTP handlers: `dashboard`, `staking`, `intelligence`, `integrations`, `health`, `premium`, `automation`, … |
| Route registration | `backend/app/api/v1/router.py` | Mounts all v1 routers under `/api/v1` |
| App factory | `backend/app/main.py` | FastAPI app, CORS, security headers, rate limit, lifespan (DB engine + Redis) |
| Config | `backend/app/core/config.py` | `Settings` from environment (see `.env.example`) |
| Domain / DB | `backend/app/database/models/` | SQLAlchemy models |
| Ingestion | `backend/app/ingestion/` | Chain head sync, MVP catalog/portfolio sync, intelligence recompute |
| Intelligence math | `backend/app/services/intelligence/` | Scoring, rollups, queries |
| Frontend shell | `frontend/app/` | Next.js App Router pages |
| Dashboard UI | `frontend/components/dashboard/` | Panels composed in `Dashboard.tsx` |
| API client | `frontend/lib/api/` | Fetch helpers and types |

### Typical request flow (dashboard)

1. User opens the app; **WalletBar** may set or clear a wallet context (`WalletProvider`).
2. Panels use **TanStack Query** with keys such as `validators`, `staking`, `wallet-risk`.
3. Wallet-scoped calls send **`X-Wallet-Address`** so the API can enforce that the path wallet matches the header (see `docs/security-and-trust.md`).
4. Validator list and details are served from **`GET /api/v1/validators`** and related dashboard routes; intelligence features use **`/api/v1/intelligence/...`** and premium routes where gated.

### Local run (short)

1. Copy `.env.example` → `.env` (repo root).
2. `docker compose up --build` **or** run Postgres/Redis locally and `uvicorn` + `npm run dev` (see `README.md`).

---

## 2. How to understand the dashboard

The dashboard is a **vertical stack of rows**. Each row is one full-width module or a **responsive grid** of modules. The source of truth for order is `DASHBOARD_ROWS` in:

`frontend/components/dashboard/Dashboard.tsx`

### Row map (top → bottom)

| Row | Module(s) | What you are looking at |
|-----|-----------|-------------------------|
| 1 | **WalletBar** | Connect or enter a wallet address; drives which wallet-scoped queries run and when caches invalidate. |
| 2 | **PremiumPanel** | Entitlements / premium entry points (APIs under premium + entitlements). |
| 3 | **AutomationPanel** | Automation policy, jobs, incidents (opt-in background-style features). |
| 4 | **ValidatorExplorer** · **StakingPanel** · **RewardsDashboard** | Explorer: paginated validators and detail. Staking: positions and flows tied to `X-Wallet-Address`. Rewards: summary/history for the active wallet. |
| 5 | **ValidatorRankingsPanel** · **RiskPanel** · **ValidatorComparePanel** · **ForecastPanel** | Rankings: intelligence rollups. Risk: concentration / volatility-style signals. Compare: multi-hotkey comparison. Forecast: reward forecast with explicit “estimate” labeling. |

### Layout mechanics

- **Single module in a row** → full width.
- **Multiple modules** → CSS grid (`rowGridClass`): 2, 3, or 4 columns at `lg` / `xl` breakpoints so panels stay readable on large screens.

### Context: `CompareHotkeysProvider`

The dashboard tree is wrapped in **`CompareHotkeysProvider`** so compare / selection state can be shared where needed (e.g. validator compare flows).

### After changing wallet

`DashboardContent` **invalidates** TanStack Query keys when `walletAddress` changes so staking, rewards, risk, forecast, automation, and entitlements refetch for the new wallet.

### APIs to cross-check while reviewing UI

| Concern | Example endpoints |
|---------|-------------------|
| Validators / session / sync | `GET /api/v1/validators`, `POST /api/v1/wallets/session`, `POST /api/v1/ingestion/portfolio-sync` |
| Wallet staking / rewards | `GET /api/v1/wallets/{addr}/staking`, rewards summary/history (dashboard router) |
| Intelligence | `GET /api/v1/intelligence/validators/rankings`, wallet risk, rewards forecast, compare |
| Health | `GET /api/v1/health` |

OpenAPI: `GET /api/v1/openapi.json` when the API is running.

---

## 3. Testing stages

Run stages **in order** when reviewing or before a release; each stage assumes the previous one passed.

### Stage 0 — Environment

- [ ] `.env` (or CI secrets) present; `DATABASE_URL` and `REDIS_URL` reachable for integration-style tests.
- [ ] Migrations applied: `alembic upgrade head` from `backend/` when using a real DB.

### Stage 1 — Backend unit / pure logic

Fast, no HTTP server required for most files.

```bash
cd backend
pytest tests/test_intelligence_scoring.py tests/test_mvp_sync_portfolio.py tests/test_portfolio_reward_summary.py tests/test_premium_alerts.py tests/test_automation_policy.py -q
```

Covers: scoring math, MVP portfolio write counts, reward summary aggregation, alert helpers, automation policy rules.

### Stage 2 — Backend API & integration (ASGI + mocks)

```bash
pytest tests/test_health.py tests/test_dashboard.py tests/test_integrations.py tests/test_integration_chain_sync.py tests/test_intelligence_api.py tests/test_staking.py tests/test_staking_lifecycle.py tests/test_premium_api.py tests/test_automation_api.py -q
```

Covers: health + pagination contract, dashboard smoke, Subtensor integration + chain sync, intelligence + premium + automation HTTP surfaces.

### Stage 3 — Security & trust

```bash
pytest tests/test_security_trust.py -q
```

Covers: security headers, rate limit behavior (with fake Redis), invalid JSON → 422, wallet header mismatch → 403.

### Stage 4 — Ingestion & failure drills

```bash
pytest tests/test_ingestion.py tests/test_failure_drills.py -q
```

Covers: chain head sync idempotency / integrity path, RPC failures surfacing at API boundary, stale indexer reuse behavior.

### Stage 5 — Full backend suite

```bash
cd backend
ruff check .
pytest -q
```

Use this before merge when any backend code changed.

### Stage 6 — Frontend

```bash
cd frontend
npm run lint
npm run typecheck
npm run build
```

### Stage 7 — Docker image build (optional smoke)

From repo root:

```bash
docker compose build
```

### Running a single test file by path

Many tests under `backend/tests/` prepend `backend` to `sys.path` and support:

```bash
cd backend/tests
python test_dashboard.py
```

Prefer **`pytest tests/<file>.py`** from `backend/` for CI parity.

---

## Related docs

| Doc | Topic |
|-----|--------|
| [BUILD_TODO.md](BUILD_TODO.md) | Phases and cross-cutting checklist |
| [security-and-trust.md](security-and-trust.md) | Non-custodial model, headers, rate limits |
| [deployment-and-operations.md](deployment-and-operations.md) | Staging/production, backups, monitoring |
| [phase4/scoring-and-risk.md](phase4/scoring-and-risk.md) | Scoring methodology (if present in your tree) |
