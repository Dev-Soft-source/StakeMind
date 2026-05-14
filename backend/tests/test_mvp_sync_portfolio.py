"""Unit tests for MVP portfolio sync reward/stake write counts (deterministic, mocked DB)."""

import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from unittest.mock import AsyncMock, MagicMock  # noqa: E402

import pytest  # noqa: E402

from app.database.models import RewardSnapshot, Validator  # noqa: E402
from app.ingestion.mvp_sync import _build_validator_metadata, sync_wallet_portfolio  # noqa: E402
from app.integrations.bittensor.rpc import ChainHead  # noqa: E402


def _validator_stub(subnet_id: int, index: int) -> Validator:
    return Validator(
        hotkey=f"5StakeMind{subnet_id:03d}{index:02d}deadbeef",
        subnet_id=subnet_id,
        uid=index,
        is_active=True,
        metadata_json={"display_name": f"V-{subnet_id}-{index}"},
        last_seen_block=1,
    )


def test_build_validator_metadata_shape_and_determinism() -> None:
    a = _build_validator_metadata(3, 2)
    b = _build_validator_metadata(3, 2)
    assert a == b
    assert set(a.keys()) >= {
        "display_name",
        "reliability_score",
        "apy_estimate",
        "uptime_percent",
        "reward_consistency",
        "delegated_stake_rao",
    }
    assert isinstance(a["reliability_score"], int)
    assert isinstance(a["apy_estimate"], float)


@pytest.mark.asyncio
async def test_sync_wallet_portfolio_reward_points_match_formula() -> None:
    """Each day writes one snapshot per validator in selected[:3]."""
    validators = [_validator_stub(0, i) for i in range(5)]
    added: list[object] = []

    session = AsyncMock()
    session.scalars = AsyncMock(return_value=AsyncMock(all=lambda: validators))
    session.scalar = AsyncMock(return_value=None)
    session.add = MagicMock(side_effect=added.append)
    session.commit = AsyncMock()

    history_days = 7
    result = await sync_wallet_portfolio(
        session,
        "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
        ChainHead(block_number=1_000, block_hash="0xabc"),
        history_days=history_days,
    )

    reward_snapshots = [x for x in added if isinstance(x, RewardSnapshot)]
    assert len(reward_snapshots) == history_days * 3
    assert result.reward_points_written == history_days * 3
    assert result.chain_head == 1_000


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
