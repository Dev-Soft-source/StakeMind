# BitTensor staking flows

StakeMind Phase 1 reference for delegate, undelegate, redelegate, rewards, and subnet exposure. This document is read-only research input for dashboard and transaction design in later phases.

## Actors and objects

- **TAO holder (delegator):** coldkey wallet that owns liquid or staked TAO.
- **Validator / delegate:** hotkey registered on a subnet that can receive delegated stake.
- **Subnet:** independent incentive market identified by `netuid`.
- **Stake:** TAO delegated from a coldkey to a validator hotkey, usually scoped to a subnet.
- **Rewards:** emissions and delegation returns that accrue to staked positions and are realized through claim or compounding flows.

## Delegate (stake)

1. User connects a non-custodial wallet and selects a validator and subnet context.
2. Client builds a delegate extrinsic with amount, destination hotkey, and subnet parameters.
3. User previews fees, slippage or take settings, and expected post-stake exposure.
4. Wallet signs; client submits to subtensor and tracks inclusion.
5. Backend ingests chain state and records stake snapshots by block watermark.

**Read surfaces for StakeMind:** validator catalog, current stake by coldkey, subnet exposure, delegate take, and historical delegation trend.

## Undelegate (unstake)

1. User selects an existing delegation and amount to remove.
2. Client builds an undelegate extrinsic for the hotkey and subnet.
3. User confirms unlock or waiting-period rules if applicable on the target network.
4. Wallet signs and submits; client monitors confirmation and balance changes.
5. Backend refreshes stake balances and reward baselines from chain head.

**Read surfaces:** remaining stake, pending unlock state, realized rewards since last snapshot.

## Redelegate (move stake)

1. User chooses source validator and destination validator, often within the same subnet.
2. Client builds a redelegate or equivalent remove-and-add sequence depending on network capabilities.
3. User reviews concentration and diversification impact before signing.
4. Wallet signs; backend records old and new delegation edges at the inclusion block.

**Read surfaces:** before/after allocation, concentration metrics, and redelegation history.

## Rewards

1. Chain emissions and validator performance drive reward accrual to delegated stake.
2. Users may claim, restake, or leave rewards to compound depending on wallet workflow.
3. StakeMind tracks reward snapshots over time rather than recomputing from live RPC on every page load.

**Read surfaces:** cumulative rewards, APY windows, consistency, and subnet-level contribution.

## Subnets

1. Each subnet has its own validator set, emissions schedule, and registration rules.
2. Delegation and performance metrics are subnet-scoped; portfolio views must aggregate across `netuid` values.
3. Ingestion jobs should treat subnet catalog and validator membership as first-class dimensions.

**Read surfaces:** subnet list, active validator counts, stake distribution, and exposure by subnet.

## Phase 1 boundaries

- No transaction signing or private key storage in StakeMind services.
- Integration spike is read-only: chain head, bounded catalog fetches, and idempotent ingestion runs.
- Write flows belong to Phase 3 after analytics trust is established.
