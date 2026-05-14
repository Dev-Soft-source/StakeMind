"""Unit tests for portfolio reward aggregation (mocked session)."""

import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from unittest.mock import AsyncMock  # noqa: E402

import pytest  # noqa: E402

from app.services.portfolio import reward_summary  # noqa: E402


@pytest.mark.asyncio
async def test_reward_summary_coalesces_nulls_to_zero() -> None:
    session = AsyncMock()
    session.scalar = AsyncMock(side_effect=[None, None])
    out = await reward_summary(session, "5Alice")
    assert out == {"total_rewards_rao": 0, "total_stake_rao": 0}


@pytest.mark.asyncio
async def test_reward_summary_returns_integer_totals() -> None:
    session = AsyncMock()
    session.scalar = AsyncMock(side_effect=[12_345, 99_000_000_000_000_000])
    out = await reward_summary(session, "5Bob")
    assert out["total_rewards_rao"] == 12_345
    assert out["total_stake_rao"] == 99_000_000_000_000_000


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
