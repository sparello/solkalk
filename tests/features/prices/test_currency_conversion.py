"""Tests for solkalk.features.prices.currency_conversion."""

import pandas as pd
import pytest

from solkalk.features.prices import currency_conversion


def test_to_local_per_kwh(prices_transition, rates_flat):
    local = currency_conversion.to_local_per_kwh(prices_transition, rates_flat)
    # 50.37 EUR/MWh × 11 SEK/EUR / 1000 = 0.55407 SEK/kWh
    assert local.loc["2025-09-30T22:00:00Z"] == pytest.approx(0.55407)
    assert local.name == "price_per_kwh"


def test_missing_rate_gives_nan(prices_transition, rates_flat):
    rates = rates_flat.drop(pd.Timestamp("2025-10-01"))
    local = currency_conversion.to_local_per_kwh(prices_transition, rates)
    assert local.loc["2025-10-01"].isna().all()
    assert local.loc["2025-09-30"].notna().all()


def test_naive_prices_rejected(prices_transition, rates_flat):
    with pytest.raises(ValueError, match="UTC"):
        currency_conversion.to_local_per_kwh(prices_transition.tz_localize(None), rates_flat)


def test_prices_to_local_per_kwh(prices_transition, rates_flat):
    sek = currency_conversion.to_local_per_kwh(prices_transition, rates_flat)
    # 50.37 EUR/MWh × 11 SEK/EUR / 1000 = 0.55407 SEK/kWh
    assert abs(sek.loc["2025-09-30T22:00:00Z"] - 0.55407) < 1e-9


def test_prices_without_rate_become_nan(prices_transition):
    no_rates = pd.Series(dtype=float, index=pd.DatetimeIndex([], name="date"))
    assert currency_conversion.to_local_per_kwh(prices_transition, no_rates).isna().all()


def test_tz_aware_rates_are_accepted(prices_transition, rates_flat):
    aware = rates_flat.tz_localize("UTC")
    a = currency_conversion.to_local_per_kwh(prices_transition, aware)
    b = currency_conversion.to_local_per_kwh(prices_transition, rates_flat)
    pd.testing.assert_series_equal(a, b)


def test_rates_duplicates_keep_last(prices_transition, rates_flat):
    doubled = pd.concat([rates_flat, rates_flat.loc[["2025-09-30"]] * 2])
    sek = currency_conversion.to_local_per_kwh(prices_transition, doubled)
    base = currency_conversion.to_local_per_kwh(prices_transition, rates_flat)
    assert sek.loc["2025-09-30T10:00:00Z"] == pytest.approx(2 * base.loc["2025-09-30T10:00:00Z"])
    assert sek.loc["2025-10-01T10:00:00Z"] == pytest.approx(base.loc["2025-10-01T10:00:00Z"])
