"""Tests for solkalk.features.profitability.lcoe."""

import pytest

from solkalk.features.profitability import lcoe


def test_lcoe_simple():
    # CAPEX 1000, no OPEX, 100 kWh/year for 10 years, 0 % rate → 1.0 per kWh
    assert lcoe.lcoe_per_kwh([1000] + [0] * 10, [100] * 10, 0.0) == pytest.approx(1.0)


def test_lcoe_requires_production():
    with pytest.raises(ValueError):
        lcoe.lcoe_per_kwh([1000], [], 0.05)


def test_lcoe_with_positive_rate():
    # CAPEX 1000, OPEX 10/year, 100 kWh/year, 2 years, 10 %:
    # kostnader = 1000 + 10/1.1 + 10/1.21 ; energi = 100/1.1 + 100/1.21
    costs = 1000 + 10 / 1.1 + 10 / 1.21
    energy = 100 / 1.1 + 100 / 1.21
    assert lcoe.lcoe_per_kwh([1000, 10, 10], [100, 100], 0.10) == pytest.approx(costs / energy)
