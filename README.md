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

## Run services without Docker

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

## CI and branch protection

GitHub Actions runs backend lint/tests, frontend lint/typecheck/build, and Docker image builds on pushes and pull requests.

Enable branch protection on `main` in GitHub repository settings so pull requests must pass the `CI` workflow before merge.
