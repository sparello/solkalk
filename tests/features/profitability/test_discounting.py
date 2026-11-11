"""Tests for solkalk.features.profitability.discounting."""

import pytest

from solkalk.features.profitability import discounting, lcoe, npv


def test_check_rate_accepts_normal_rates():
    discounting.check_rate(0.05)
    discounting.check_rate(-0.5)


@pytest.mark.parametrize("rate", [-1.0, -2.0])
def test_rate_at_or_below_minus_one_is_rejected(rate):
    with pytest.raises(ValueError, match="discount_rate"):
        discounting.check_rate(rate)
    with pytest.raises(ValueError, match="discount_rate"):
        npv.npv([-100, 110], rate)
    with pytest.raises(ValueError, match="discount_rate"):
        lcoe.lcoe_per_kwh([1000, 10], [100], rate)
