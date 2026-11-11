"""Tests for solkalk.features.revenue.capture_price."""

import pandas as pd
import pytest

from solkalk.features.revenue import capture_price, price_matching


def test_capture_rate_is_exactly_one_for_flat_production(
    prices_transition, rates_flat, hourly_production
):
    """Flat production captures exactly the time-weighted mean price, also across
    the hourly → quarter-hourly transition where an arithmetic mean would give ≠ 1."""
    m = price_matching.match(hourly_production, prices_transition, rates_flat)
    assert capture_price.capture_rate(m, prices_transition) == pytest.approx(1.0, abs=1e-9)
    arithmetic = m["price_per_kwh"].mean()
    assert capture_price.time_weighted_mean_price_per_kwh(m, prices_transition) != pytest.approx(
        arithmetic, abs=1e-4
    )


def test_capture_price_zero_without_export(prices_transition, rates_flat):
    nothing = pd.Series(0.0, index=pd.DatetimeIndex(["2025-09-30T21:00:00Z"]))
    m = price_matching.match(nothing, prices_transition, rates_flat)
    assert capture_price.capture_price_per_kwh(m) == 0.0


def test_capture_rate_zero_not_nan_when_prices_missing(
    prices_transition, rates_flat, hourly_production
):
    empty_rates = rates_flat.iloc[0:0]
    m = price_matching.match(
        hourly_production, prices_transition, empty_rates, allow_missing_rates=True
    )
    assert capture_price.capture_rate(m, prices_transition) == 0.0
