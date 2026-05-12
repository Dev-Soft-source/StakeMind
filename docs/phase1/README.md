# Phase 1 — Research and validation

Phase 1 validates BitTensor staking scope, competitor positioning, draft persistence, and a read-only integration spike before dashboard work in Phase 2.

## Artifacts

| Document | Purpose |
| --- | --- |
| [staking-flows.md](staking-flows.md) | Delegate, undelegate, redelegate, rewards, subnets |
| [competitor-matrix.md](competitor-matrix.md) | Competitive scan and feature gaps |
| [pain-points.md](pain-points.md) | User pain points and product gaps |
| [positioning.md](positioning.md) | Product positioning one-pager |
| [architecture.md](architecture.md) | Phase 1 architecture and module boundaries |
| [data-model.md](data-model.md) | Draft PostgreSQL schema |
| [validation.md](validation.md) | Acceptance evidence and sign-off checklist |

## Technical spike

- `GET /api/v1/integrations/subtensor/chain-head`
- `POST /api/v1/integrations/subtensor/ingestion/chain-head-sync`
- `python backend/scripts/check_db_connection.py`
- `python backend/scripts/run_chain_head_sync.py`
- Alembic revision `0002_phase1`

## Success

Build scope, integrations, and data shape are validated before dashboard implementation.
