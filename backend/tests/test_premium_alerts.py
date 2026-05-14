from datetime import UTC, datetime

import pytest

from app.services.premium.alerts import is_within_quiet_hours, utc_hour_bucket


def test_utc_hour_bucket_format() -> None:
    now = datetime(2026, 5, 13, 14, 30, tzinfo=UTC)
    assert utc_hour_bucket(now) == "2026-05-13T14"


def test_quiet_hours_simple_range() -> None:
    now = datetime(2026, 5, 13, 23, 0, tzinfo=UTC)
    assert is_within_quiet_hours(now, 22, 6) is True
    now_ok = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
    assert is_within_quiet_hours(now_ok, 22, 6) is False


def test_quiet_hours_disabled_when_partial() -> None:
    now = datetime(2026, 5, 13, 23, 0, tzinfo=UTC)
    assert is_within_quiet_hours(now, None, 6) is False
    assert is_within_quiet_hours(now, 22, None) is False
