# Phase 4 scoring and risk methodology

Methodology version: `mvp-v1`.

## Validator composite score

Inputs come from stored validator catalog metadata and stake snapshots:

- Uptime percent (0–100), normalized to 0–1.
- Reward consistency (0–1).
- APY estimate, normalized against a 20% reference cap.
- Delegated stake versus pool median stake (log-scaled).

Composite score (0–100):

`0.35 * uptime + 0.30 * consistency + 0.25 * apy + 0.10 * delegation`

Delegation trend is stake versus median, clamped to [-1, 1]. Reputation signal blends consistency and uptime.

## Wallet risk bands

Inputs:

- Validator and subnet allocation weights (sums to 1).
- Daily reward totals over the recompute window.
- Downtime proxy percent from stored metadata.

Derived metrics include max concentration, HHI, reward volatility (population stdev / mean), and downtime proxy.

Bands:

- **High** when validator concentration exceeds 70% or reward volatility exceeds 60%.
- **Low** when validator concentration is at most 40% and volatility is at most 35%.
- **Medium** otherwise.

## Reward forecast

Forecasts use a simple linear regression over the trailing daily reward window (up to 14 days). Implied APY annualizes mean daily rewards against total stake. Responses set `is_estimate: true` and include shared limitations.

## Limitations

- Scores use stored snapshot metadata, not live chain performance feeds.
- Wallet reward history is synthetic in local MVP sync flows.
- Forecasts are estimates and are not guarantees of future rewards.

## Freshness

Run `backend/scripts/run_mvp_sync.py` (includes intelligence recompute) or `backend/scripts/run_intelligence_recompute.py` after catalog and portfolio sync. Rankings reads are cached in Redis with `INTELLIGENCE_CACHE_TTL_SECONDS` and invalidated on recompute.
