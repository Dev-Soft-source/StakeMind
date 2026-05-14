import sys
from pathlib import Path

# Same as tests/conftest.py — needed when running this file directly (not via pytest discovery).
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

import pytest  # noqa: E402

from app.database.models import AutomationPolicy  # noqa: E402
from app.services.automation.policy import assert_payload_within_policy  # noqa: E402


def _policy(**kwargs) -> AutomationPolicy:
    base = dict(
        wallet_address="5W",
        opt_in=True,
        kill_switch_active=False,
        max_amount_rao_per_action=1000,
        max_daily_jobs=10,
        allowed_validator_hotkeys=[],
        allowed_subnet_ids=[],
        compound_threshold_rao=0,
    )
    base.update(kwargs)
    return AutomationPolicy(**base)


def test_policy_blocks_amount_over_cap() -> None:
    p = _policy(max_amount_rao_per_action=500)
    with pytest.raises(ValueError, match="amount_exceeds_policy_cap"):
        assert_payload_within_policy(p, {"amount_rao": 501})


def test_policy_allowlist_validator() -> None:
    p = _policy(allowed_validator_hotkeys=["5Abc"])
    assert_payload_within_policy(p, {"validator_hotkey": "5Abc", "amount_rao": 100})
    with pytest.raises(ValueError, match="validator_not_allowlisted"):
        assert_payload_within_policy(p, {"validator_hotkey": "5Xxx"})


def test_policy_allowlist_subnet() -> None:
    p = _policy(allowed_subnet_ids=[1, 2])
    assert_payload_within_policy(p, {"subnet_id": 1})
    with pytest.raises(ValueError, match="subnet_not_allowlisted"):
        assert_payload_within_policy(p, {"subnet_id": 99})


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
