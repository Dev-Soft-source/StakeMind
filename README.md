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

3. Open the app at `http://localhost:3000`.
4. API docs live at `http://localhost:8000/api/v1/docs`.

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
cd frontend && npm run lint && npm run build
```
