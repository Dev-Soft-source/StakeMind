# StakeMind

Validator intelligence and staking optimization platform for the BitTensor ecosystem.

## Stack

- Frontend: Next.js, TypeScript, Tailwind CSS
- Backend: FastAPI
- Data: PostgreSQL, Redis

## Local development

1. Copy `.env.example` to `.env` and adjust values if needed.
2. Start the full stack:

```bash
docker compose up --build
```

On Windows PowerShell you can also run `scripts/start-stack.ps1 -Build`.

3. Open the app at `http://localhost:3000`.
4. API docs live at `http://localhost:8000/api/v1/docs`.
5. Shared API contracts are documented at `http://localhost:8000/api/v1/contracts/pagination`.

## Environment files

- `.env.example` for local development
- `.env.staging.example` for staging deployments
- `.env.production.example` for production deployments

Do not commit real secrets. `.env` files stay local and are ignored by git.

For API hardening and the non-custodial trust model, see [docs/security-and-trust.md](docs/security-and-trust.md).

For staging/production topology, TLS, backups, monitoring, and runbooks, see [docs/deployment-and-operations.md](docs/deployment-and-operations.md).

For post-MVP growth (landing, public docs, validator research, community channels), see [docs/growth-post-mvp.md](docs/growth-post-mvp.md).

## Run services without Docker

### Database migrations

`DATABASE_URL` must match a real PostgreSQL role. The app and Alembic load `.env` from the repo root and from `backend/.env`.

If you use the default Compose credentials, bootstrap a local database once:

```bash
psql -U postgres -f scripts/init-local-postgres.sql
```

On Windows PowerShell:

```powershell
.\scripts\bootstrap-local-postgres.ps1
```

If you use an existing PostgreSQL installation, set `DATABASE_URL` in `.env` to that role instead. `postgresql://` and `postgresql+asyncpg://` both work; the app normalizes to `asyncpg`. You do not need `psycopg2` for migrations.

```text
postgresql+asyncpg://USER:PASSWORD@localhost:5432/DATABASE
```

Then run migrations from `backend/`:

```bash
cd backend
python scripts/check_db_connection.py
alembic upgrade head
```

On Windows PowerShell you can also run `backend/scripts/run_migrations.ps1` from any directory.

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Tests and lint

```bash
cd backend && ruff check . && pytest
cd frontend && npm run lint && npm run typecheck && npm run build
```

## Phase 1 artifacts

Research and validation outputs live in `docs/phase1/`.

Optional live RPC verification:

```bash
cd backend
python scripts/verify_phase1.py
```

Read-only integration spike:

- `GET /api/v1/integrations/subtensor/chain-head`
- `POST /api/v1/integrations/subtensor/ingestion/chain-head-sync`
- `python backend/scripts/run_chain_head_sync.py` after migrations

## CI and branch protection

GitHub Actions runs backend lint/tests, frontend lint/typecheck/build, and Docker image builds on pushes and pull requests.

Enable branch protection on `main` in GitHub repository settings so pull requests must pass the `CI` workflow before merge.
