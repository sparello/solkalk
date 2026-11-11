"""Tests for solkalk.features.prices.ecb_exchange_rates. Mirrors the module 1:1."""

import pandas as pd
import responses

from solkalk.features.prices import ecb_exchange_rates


def test_parse_rates(ecb_rates_jan):
    assert len(ecb_rates_jan) == 3
    assert ecb_rates_jan.loc["2025-01-03"] == 11.499
    assert ecb_rates_jan.index.is_monotonic_increasing


def test_forward_fill_covers_weekend_and_holiday(ecb_rates_jan):
    daily = ecb_exchange_rates.forward_fill(ecb_rates_jan, "2025-01-02", "2025-01-08")
    assert len(daily) == 7
    # Sat 4, Sun 5, Mon 6 (ECB holiday) inherit Friday's rate
    assert daily.loc["2025-01-04"] == 11.499
    assert daily.loc["2025-01-06"] == 11.499
    assert daily.loc["2025-01-07"] == 11.4875
    assert daily.loc["2025-01-08"] == 11.4875  # after the last known rate


def test_forward_fill_skips_days_before_first_rate(ecb_rates_jan):
    daily = ecb_exchange_rates.forward_fill(ecb_rates_jan, "2024-12-30", "2025-01-02")
    assert daily.index.min() == pd.Timestamp("2025-01-02")


def test_build_url():
    url = ecb_exchange_rates.build_url("sek", "2025-01-01", "2025-01-31")
    assert url.endswith("/D.SEK.EUR.SP00.A?startPeriod=2025-01-01&endPeriod=2025-01-31")


@responses.activate
def test_fetch_daily_mocked(ecb_xml):
    responses.get(ecb_exchange_rates.build_url("SEK", "2024-12-26", "2025-01-08"), body=ecb_xml)
    daily = ecb_exchange_rates.fetch_daily("SEK", "2025-01-02", "2025-01-08")
    assert responses.calls[0].request.headers["Accept"] == ecb_exchange_rates.ACCEPT_HEADER
    assert len(daily) == 7


@responses.activate
def test_fetch_daily_range_starting_on_holiday_gets_earlier_rate(ecb_xml):
    """Sat 4 Jan has no rate of its own: the fetch must reach back to Fri 3 Jan."""
    responses.get(ecb_exchange_rates.build_url("SEK", "2024-12-28", "2025-01-08"), body=ecb_xml)
    daily = ecb_exchange_rates.fetch_daily("SEK", "2025-01-04", "2025-01-08")
    assert daily.index.min() == pd.Timestamp("2025-01-04")
    assert daily.loc["2025-01-04"] == 11.499
    assert len(daily) == 5


def test_read_csv_roundtrip(ecb_rates_jan, tmp_path):
    daily = ecb_exchange_rates.forward_fill(ecb_rates_jan, "2025-01-02", "2025-01-08")
    path = tmp_path / "kurs.csv"
    daily.to_csv(path, date_format="%Y-%m-%d")
    again = ecb_exchange_rates.read_csv(path)
    pd.testing.assert_series_equal(daily, again, check_freq=False)


def test_forward_fill_stops_after_max_gap(ecb_rates_jan):
    """A range far after the last known rate must not silently get today's rate."""
    future = ecb_exchange_rates.forward_fill(ecb_rates_jan, "2025-01-07", "2025-01-20")
    assert future.index.max() == pd.Timestamp("2025-01-14")  # 7 dagar efter 7 jan
    unlimited = ecb_exchange_rates.forward_fill(
        ecb_rates_jan, "2025-01-07", "2025-01-20", max_gap_days=None
    )
    assert len(unlimited) == 14


def test_parse_rates_dedupes():
    obs = (
        '<generic:Obs><generic:ObsDimension value="2025-01-02"/>'
        '<generic:ObsValue value="{v}"/></generic:Obs>'
    )
    xml = (
        '<message:GenericData xmlns:message="m" xmlns:generic="g"><message:DataSet><generic:Series>'
        + obs.format(v="11.1")
        + obs.format(v="11.2")
        + "</generic:Series></message:DataSet></message:GenericData>"
    )
    rates = ecb_exchange_rates.parse_rates(xml)
    assert len(rates) == 1 and rates.iloc[0] == 11.2


def test_forward_fill_accepts_tz_aware_rates(ecb_rates_jan):
    aware = ecb_rates_jan.tz_localize("UTC")
    a = ecb_exchange_rates.forward_fill(aware, "2025-01-02", "2025-01-08")
    b = ecb_exchange_rates.forward_fill(ecb_rates_jan, "2025-01-02", "2025-01-08")
    pd.testing.assert_series_equal(a, b)
