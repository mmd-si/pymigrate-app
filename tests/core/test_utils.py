from datetime import timezone

from app.core.utils import EST, clamp, estnow, utcnow


def test_clamp_returns_value_within_bounds():
    assert clamp(5, 0, 10) == 5


def test_clamp_clamps_below_lower_bound():
    assert clamp(-5, 0, 10) == 0


def test_clamp_clamps_above_upper_bound():
    assert clamp(15, 0, 10) == 10


def test_clamp_boundary_values_unchanged():
    assert clamp(0, 0, 10) == 0
    assert clamp(10, 0, 10) == 10


def test_utcnow_is_timezone_aware_utc():
    now = utcnow()
    assert now.tzinfo is not None
    assert now.utcoffset() == timezone.utc.utcoffset(now)


def test_estnow_is_timezone_aware_est():
    now = estnow()
    assert now.tzinfo is not None
    assert now.tzinfo == EST
