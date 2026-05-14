# Security and trust

StakeMind is **non-custodial**: the backend never holds private keys, never signs extrinsics, and never submits transactions on a user’s behalf. Wallets remain the sole authority for signing.

## What the API does

- **Read APIs** return data derived from stored snapshots, chain-head ingestion, and configured RPC reads where applicable.
- **Staking APIs** return **unsigned** payloads and demo/simulated outcomes for MVP flows; broadcasting real extrinsics is out of scope unless you integrate it client-side with your own signer.
- **Automation** (optional) only enqueues **scans** and **informational incidents** under an explicit per-wallet policy (opt-in, kill switch, caps, allowlists). It does not execute stakes or moves.

## What we store

- Wallet address as an identifier for sessions, portfolio snapshots, rewards history, staking transaction records (unsigned payloads, hashes, statuses), intelligence rollups, premium entitlements, automation policy/jobs/incidents, and audit log metadata.
- No seed phrases, no mnemonic words, no private keys, no raw signed extrinsics beyond what you explicitly submit in API fields for MVP tracking (treat production signing paths as your own policy).

## What we never store

- Private keys, mnemonics, or any material that could spend funds without the user’s wallet.
- Passwords for on-chain accounts (there is no traditional password login tied to chain keys).

## Client responsibilities

- Send **`X-Wallet-Address`** only for the same wallet as the path when endpoints require scope; mismatches are rejected.
- Run the app behind **HTTPS** in production and enable **`SECURITY_HSTS_ENABLED`** only when TLS is correctly terminated.
- When behind a reverse proxy, set **`TRUST_X_FORWARDED_FOR=true`** only if the proxy strips untrusted `X-Forwarded-For` values; otherwise rate limits key off the proxy IP only.

## Rate limiting and headers

- Optional **`RATE_LIMIT_ENABLED`** with Redis counts requests per client IP per minute (skips health, docs, OpenAPI, and CORS `OPTIONS`).
- Responses include **`X-Content-Type-Options: nosniff`**, **`X-Frame-Options: DENY`**, **`Referrer-Policy: no-referrer`**, and a restrictive **`Permissions-Policy`**.

## Validation

- Request bodies and query parameters are validated with **Pydantic** / FastAPI; invalid input returns **422** with structured errors.
- SQL access goes through **SQLAlchemy** with bound parameters; do not concatenate user input into raw SQL in new code.

For implementation status, see **Cross-cutting → Security and trust** in `docs/BUILD_TODO.md`.
