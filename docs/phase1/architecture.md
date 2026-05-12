# Phase 1 architecture

High-level view of research outputs, ingestion spike, and draft persistence for StakeMind.

```mermaid
flowchart TB
  subgraph clients [Clients]
    Web[Next.js dashboard]
  end

  subgraph api [FastAPI]
    V1["/api/v1/*"]
    Health[health]
    Contracts[contracts]
    Integrations[integrations / ingestion]
  end

  subgraph domain [Domain services]
    Rpc[Subtensor RPC client]
    Ingest[Ingestion jobs]
    Models[Draft ORM models]
  end

  subgraph data [Data]
    Pg[(PostgreSQL)]
    Redis[(Redis cache)]
  end

  subgraph external [External]
    Subtensor[Subtensor JSON-RPC]
  end

  Web --> V1
  V1 --> Health
  V1 --> Contracts
  V1 --> Integrations
  Integrations --> Rpc
  Integrations --> Ingest
  Ingest --> Models
  Ingest --> Rpc
  Models --> Pg
  Rpc --> Subtensor
  V1 --> Redis
```

## Module responsibilities

| Module | Phase 1 responsibility |
| --- | --- |
| `integrations/bittensor` | Read-only JSON-RPC client with retries, timeouts, and typed responses |
| `ingestion` | Bounded, idempotent spike jobs keyed by chain watermark |
| `database/models` | Draft schema for validators, subnets, stakes, rewards, sessions, audit events |
| `docs/phase1` | Staking flows, competitor matrix, pain points, positioning, data model |

## Security boundaries

- No private keys or signing in backend services.
- Wallet sessions store address metadata and expiry only.
- Audit events capture actor, action, and outcome without secret material.

## Phase 2 handoff

- Promote ingestion spike into scheduled sync jobs.
- Expose read APIs on top of normalized tables and Redis-backed aggregates.
- Connect the frontend dashboard to versioned API responses.
