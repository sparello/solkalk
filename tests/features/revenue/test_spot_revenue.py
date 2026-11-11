"""Tests for solkalk.features.revenue.spot_revenue."""

import pytest

from solkalk.features.revenue import price_matching, spot_revenue


def test_spot_revenue_from_raw_inputs(prices_transition, rates_flat, hourly_production):
    """Revenue computed straight from raw data (EUR/MWh × 11 / 1000 × kWh per step)."""
    m = price_matching.match(hourly_production, prices_transition, rates_flat)
    step_h = prices_transition["resolution_min"] / 60.0
    expected = (prices_transition["eur_per_mwh"] * 11.0 / 1000.0 * step_h).sum()
    assert spot_revenue.spot_revenue(m) == pytest.approx(expected)
