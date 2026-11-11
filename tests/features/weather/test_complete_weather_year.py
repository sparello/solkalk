"""Tests for solkalk.features.weather.complete_weather_year."""

import pandas as pd
import pytest

from solkalk.features.weather import complete_weather_year


def test_full_year_index_lengths():
    assert len(complete_weather_year.full_year_index(2024)) == 8784
    assert len(complete_weather_year.full_year_index(2025)) == 8760


def test_build_fills_missing_with_zero(strang_week):
    frame = complete_weather_year.build(strang_week, 2024)
    assert len(frame) == 8784
    assert list(frame.columns) == complete_weather_year.COLUMNS
    assert frame.loc["2024-01-15T12:00:00Z", "ghi"] == 0.0  # outside the fixture week
    assert frame.loc["2024-06-12T12:00:00Z", "ghi"] > 0.0
    assert frame[["ghi", "dni", "dhi"]].isna().sum().sum() == 0


def test_build_constant_temp_and_wind(strang_week):
    frame = complete_weather_year.build(strang_week, 2024, temp_air=5.0, wind_speed=3.0)
    assert (frame["temp_air"] == 5.0).all()
    assert (frame["wind_speed"] == 3.0).all()


def test_build_accepts_temperature_series(strang_week):
    temps = pd.Series([20.0], index=pd.DatetimeIndex(["2024-06-12T00:00:00Z"]))
    frame = complete_weather_year.build(strang_week, 2024, temp_air=temps)
    assert frame.loc["2024-06-12T06:00:00Z", "temp_air"] == 20.0  # ffill
    assert frame.loc["2024-01-01T00:00:00Z", "temp_air"] == 20.0  # bfill


def test_coverage(strang_week):
    assert abs(complete_weather_year.coverage(strang_week, 2024) - 168 / 8784) < 1e-9


def test_partial_nan_hour_is_zeroed_entirely(strang_week):
    broken = strang_week.copy()
    broken.loc["2024-06-12T12:00:00Z", "dni"] = float("nan")
    frame = complete_weather_year.build(broken, 2024)
    row = frame.loc["2024-06-12T12:00:00Z"]
    assert row["ghi"] == 0.0 and row["dni"] == 0.0 and row["dhi"] == 0.0


def test_duplicate_timestamps_keep_last(strang_week):
    noon = pd.Timestamp("2024-06-12T12:00:00Z")
    original = strang_week.loc[noon, "ghi"]
    assert original > 0
    dup = pd.concat([strang_week, strang_week.loc[[noon]] * 2])
    frame = complete_weather_year.build(dup, 2024)
    assert frame.loc[noon, "ghi"] == pytest.approx(original * 2)


def test_naive_index_rejected(strang_week):
    naive = strang_week.tz_localize(None)
    with pytest.raises(ValueError, match="UTC"):
        complete_weather_year.build(naive, 2024)


def test_other_timezone_is_converted(strang_week):
    local = strang_week.tz_convert("Europe/Stockholm")
    a = complete_weather_year.build(local, 2024)
    b = complete_weather_year.build(strang_week, 2024)
    pd.testing.assert_frame_equal(a, b)


def test_naive_temperature_series_rejected(strang_week):
    naive = pd.Series([25.0], index=pd.DatetimeIndex(["2024-06-12"]))
    with pytest.raises(ValueError):
        complete_weather_year.build(strang_week, 2024, temp_air=naive)


def test_negative_irradiance_zeroes_the_whole_hour(strang_week):
    """A negative value is a fill value: same rule as a missing component."""
    broken = strang_week.copy()
    broken.loc["2024-06-12T12:00:00Z", "dhi"] = -40.0
    frame = complete_weather_year.build(broken, 2024)
    assert (frame.loc["2024-06-12T12:00:00Z", ["ghi", "dni", "dhi"]] == 0.0).all()
    assert frame.loc["2024-06-12T11:00:00Z", "ghi"] > 0.0  # neighbouring hour untouched


def test_coverage_ignores_duplicates(strang_week):
    dup = pd.concat([strang_week, strang_week.iloc[:10]])
    assert complete_weather_year.coverage(dup, 2024) == pytest.approx(168 / 8784)
