"""Tests for solkalk.features.revenue.price_matching."""

import pandas as pd
import pytest

from solkalk.features.revenue import price_matching


def test_distribute_splits_hour_over_quarters(prices_transition, hourly_production):
    kwh = price_matching.distribute_to_price_steps(hourly_production, prices_transition)
    assert kwh.loc["2025-09-30T21:00:00Z"] == 1.0  # hourly price: whole hour
    quarters = kwh.loc["2025-09-30T22:00:00Z":"2025-09-30T22:45:00Z"]
    assert len(quarters) == 4 and (quarters == 0.25).all()
    # total energy is conserved
    assert abs(kwh.sum() - hourly_production.sum()) < 1e-9


def test_distribute_missing_hours_are_zero(prices_transition):
    partial = pd.Series([2.0], index=pd.DatetimeIndex(["2025-09-30T21:00:00Z"]))
    kwh = price_matching.distribute_to_price_steps(partial, prices_transition)
    assert kwh.loc["2025-09-30T21:00:00Z"] == 2.0
    assert (kwh.drop(pd.Timestamp("2025-09-30T21:00:00Z")) == 0.0).all()


def test_match_solar_park_exports_everything(prices_transition, rates_flat, hourly_production):
    m = price_matching.match(hourly_production, prices_transition, rates_flat)
    assert (m["export_kwh"] == m["production_kwh"]).all()
    assert (m["self_consumption_kwh"] == 0).all()
    assert m.index.equals(prices_transition.index)


def test_match_with_consumption(prices_transition, rates_flat, hourly_production):
    consumption = hourly_production * 0.4  # 0.4 kWh/h consumption
    m = price_matching.match(hourly_production, prices_transition, rates_flat, consumption)
    assert abs(m["self_consumption_kwh"].sum() - 0.4 * len(hourly_production)) < 1e-9
    assert abs(m["export_kwh"].sum() - 0.6 * len(hourly_production)) < 1e-9
    assert (m["import_kwh"] == 0).all()
    # energy balance per row
    assert ((m["production_kwh"] - m["self_consumption_kwh"] - m["export_kwh"]).abs() < 1e-12).all()


def test_missing_rate_day_raises(prices_transition, rates_flat, hourly_production):
    rates = rates_flat.drop(pd.Timestamp("2025-10-01"))
    with pytest.raises(ValueError, match="2025-10-01"):
        price_matching.match(hourly_production, prices_transition, rates)
    m = price_matching.match(hourly_production, prices_transition, rates, allow_missing_rates=True)
    assert m["price_per_kwh"].isna().sum() == 96  # 24 h × 4 quarters


def test_naive_production_index_rejected(prices_transition):
    naive = pd.Series(1.0, index=pd.date_range("2025-09-30", periods=48, freq="h"))
    with pytest.raises(ValueError, match="UTC"):
        price_matching.distribute_to_price_steps(naive, prices_transition)


def test_local_timezone_production_is_converted(prices_transition, hourly_production):
    local = hourly_production.tz_convert("Europe/Stockholm")
    a = price_matching.distribute_to_price_steps(local, prices_transition)
    b = price_matching.distribute_to_price_steps(hourly_production, prices_transition)
    pd.testing.assert_series_equal(a, b)


def test_duplicate_price_timestamps_rejected(prices_transition, hourly_production):
    dup = pd.concat([prices_transition, prices_transition.iloc[:2]])
    with pytest.raises(ValueError, match="duplicate"):
        price_matching.distribute_to_price_steps(hourly_production, dup)


def test_quarter_hour_production_is_summed_not_dropped(prices_transition, hourly_production):
    quarter_index = pd.date_range(
        hourly_production.index.min(),
        hourly_production.index.max() + pd.Timedelta(minutes=45),
        freq="15min",
    )
    quarter = pd.Series(0.25, index=quarter_index)  # same energy (1 kWh/h) in 15-min steps
    assert quarter.sum() == pytest.approx(hourly_production.sum())
    a = price_matching.distribute_to_price_steps(hourly_production, prices_transition)
    b = price_matching.distribute_to_price_steps(quarter, prices_transition)
    assert b.sum() == pytest.approx(a.sum())
