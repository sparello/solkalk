"""Tests for solkalk.features.prices.entsoe_day_ahead. Mirrors the module 1:1."""

from datetime import UTC, datetime

import pandas as pd
import pytest
import responses

from solkalk.features.prices import entsoe_day_ahead


@pytest.fixture
def mixed(fixtures):
    return entsoe_day_ahead.parse_prices((fixtures / "entsoe_a44_mixed.xml").read_text())


def test_parse_forward_fills_omitted_positions(mixed):
    hourly = mixed[mixed["resolution_min"] == 60]
    assert len(hourly) == 24
    # position 3 is missing in the XML → inherits the price of position 2
    assert hourly["eur_per_mwh"].iloc[2] == 20.0
    # positions 6–23 are missing → inherit the price of position 5 (negative price)
    assert hourly["eur_per_mwh"].iloc[5] == -5.0
    assert hourly["eur_per_mwh"].iloc[22] == -5.0
    assert hourly["eur_per_mwh"].iloc[23] == 24.0


def test_parse_handles_pt15m(mixed):
    quarter = mixed[mixed["resolution_min"] == 15]
    assert len(quarter) == 4
    assert quarter.index[0] == pd.Timestamp("2025-09-30T22:00:00Z")
    assert quarter.index[1] == pd.Timestamp("2025-09-30T22:15:00Z")
    assert quarter["eur_per_mwh"].tolist() == [50.37, 47.04, 45.0, 44.0]


def test_parse_index_is_utc_sorted_unique(mixed):
    assert str(mixed.index.tz) == "UTC"
    assert mixed.index.is_monotonic_increasing
    assert mixed.index.is_unique


def test_parse_acknowledgement_raises(fixtures):
    with pytest.raises(ValueError, match="No matching data"):
        entsoe_day_ahead.parse_prices((fixtures / "entsoe_ack_nodata.xml").read_text())


def test_clip_to_year_keeps_year_and_complete_days(mixed):
    today = datetime(2025, 9, 30, 15, 0, tzinfo=UTC)
    clipped = entsoe_day_ahead.clip_to_year(mixed, 2025, today=today)
    assert clipped.index.max() < pd.Timestamp("2025-09-30T00:00:00Z")
    assert len(clipped) == 2  # only 29 Sep 22:00 and 23:00 lie before today 00:00


def test_clip_to_year_drops_other_years(mixed):
    assert entsoe_day_ahead.clip_to_year(mixed, 2024, today=datetime(2026, 1, 1, tzinfo=UTC)).empty


def test_build_url_caps_current_year_at_today():
    url = entsoe_day_ahead.build_url(
        "10Y1001A1001A46L", 2026, "KEY", today=datetime(2026, 3, 15, tzinfo=UTC)
    )
    assert "periodStart=202601010000" in url
    assert "periodEnd=202603150000" in url
    assert "securityToken=KEY" in url


def test_build_url_past_year_ends_next_jan_1():
    url = entsoe_day_ahead.build_url("X", 2024, "KEY", today=datetime(2026, 3, 15, tzinfo=UTC))
    assert "periodEnd=202501010000" in url


def test_api_key_from_env(monkeypatch):
    monkeypatch.delenv(entsoe_day_ahead.ENV_VAR, raising=False)
    with pytest.raises(entsoe_day_ahead.MissingApiKeyError):
        entsoe_day_ahead.api_key_from_env()
    monkeypatch.setenv(entsoe_day_ahead.ENV_VAR, "abc")
    assert entsoe_day_ahead.api_key_from_env() == "abc"


def test_fetch_year_unknown_area():
    with pytest.raises(KeyError):
        entsoe_day_ahead.fetch_year("NO1", 2024, api_key="x")


@responses.activate
def test_fetch_year_mocked(fixtures):
    responses.get(entsoe_day_ahead.BASE_URL, body=(fixtures / "entsoe_a44_mixed.xml").read_text())
    frame = entsoe_day_ahead.fetch_year("se3", 2025, api_key="x")
    assert "securityToken=x" in responses.calls[0].request.url
    assert not frame.empty
    assert set(frame.columns) == {"eur_per_mwh", "resolution_min"}


def test_validate_low_coverage(mixed):
    warnings = entsoe_day_ahead.validate(mixed, 2025, today=datetime(2026, 1, 1, tzinfo=UTC))
    assert any("coverage" in w for w in warnings)


def test_read_csv_real_transition(prices_transition):
    assert prices_transition.loc["2025-09-30T21:00:00Z", "resolution_min"] == 60
    assert prices_transition.loc["2025-09-30T22:00:00Z", "resolution_min"] == 15
    assert prices_transition["eur_per_mwh"].dtype == float


def test_parallel_pt60m_and_pt15m_keeps_only_quarters(fixtures):
    """After 2025-10-01 ENTSO-E often publishes hourly and quarter-hourly series in parallel."""
    xml = (fixtures / "entsoe_a44_mixed.xml").read_text()
    hourly_dup = """
  <TimeSeries><mRID>3</mRID><curveType>A03</curveType>
    <Period>
      <timeInterval><start>2025-09-30T22:00Z</start><end>2025-09-30T23:00Z</end></timeInterval>
      <resolution>PT60M</resolution>
      <Point><position>1</position><price.amount>46.60</price.amount></Point>
    </Period>
  </TimeSeries>
</Publication_MarketDocument>"""
    xml = xml.replace("</Publication_MarketDocument>", hourly_dup)
    frame = entsoe_day_ahead.parse_prices(xml)
    hour = frame.loc["2025-09-30T22:00:00Z":"2025-09-30T22:59:59Z"]
    assert len(hour) == 4
    assert (hour["resolution_min"] == 15).all()
    assert hour["resolution_min"].sum() == 60


def test_keep_finest_resolution_empty():
    empty = entsoe_day_ahead.parse_prices(
        '<Publication_MarketDocument xmlns="x"><TimeSeries/></Publication_MarketDocument>'
    )
    assert empty.empty and empty["resolution_min"].dtype == int


def test_validate_flags_over_coverage():
    index = pd.date_range("2025-01-01", periods=24, freq="h", tz="UTC")
    bad = pd.DataFrame({"eur_per_mwh": 50.0, "resolution_min": 240}, index=index)  # 4× coverage
    warnings = entsoe_day_ahead.validate(bad, 2025, today=datetime(2025, 1, 2, tzinfo=UTC))
    assert any("above 100" in w for w in warnings)


def test_validate_flags_implausible_price(prices_transition):
    bad = prices_transition.copy()
    bad.iloc[0, bad.columns.get_loc("eur_per_mwh")] = 9999.0
    warnings = entsoe_day_ahead.validate(bad, 2025, today=datetime(2026, 1, 1, tzinfo=UTC))
    assert any("plausible range" in w for w in warnings)


def _period_xml(mrid: int, start: str, end: str, resolution: str, prices: list[float]) -> str:
    points = "".join(
        f"<Point><position>{i}</position><price.amount>{p}</price.amount></Point>"
        for i, p in enumerate(prices, start=1)
    )
    return (
        f"<TimeSeries><mRID>{mrid}</mRID><curveType>A03</curveType><Period>"
        f"<timeInterval><start>{start}</start><end>{end}</end></timeInterval>"
        f"<resolution>{resolution}</resolution>{points}</Period></TimeSeries>"
    )


def _doc(*series: str) -> str:
    return (
        '<Publication_MarketDocument xmlns="urn:x">'
        + "".join(series)
        + "</Publication_MarketDocument>"
    )


def test_overlapping_publications_last_wins_for_every_slot():
    """Two series for the same 96 quarters: the later one must win for ALL slots."""
    first = _period_xml(1, "2025-10-01T22:00Z", "2025-10-02T22:00Z", "PT15M", list(range(1, 97)))
    second = _period_xml(
        2, "2025-10-01T22:00Z", "2025-10-02T22:00Z", "PT15M", list(range(1001, 1097))
    )
    frame = entsoe_day_ahead.parse_prices(_doc(first, second))
    assert len(frame) == 96
    assert (frame["eur_per_mwh"] >= 1001).all()


def test_pt30m_and_pt15m_keep_quarters_only():
    half = _period_xml(1, "2025-10-01T22:00Z", "2025-10-01T23:00Z", "PT30M", [10.0, 20.0])
    quarter = _period_xml(
        2, "2025-10-01T22:00Z", "2025-10-01T23:00Z", "PT15M", [1.0, 2.0, 3.0, 4.0]
    )
    frame = entsoe_day_ahead.parse_prices(_doc(half, quarter))
    assert frame["resolution_min"].tolist() == [15, 15, 15, 15]


@responses.activate
def test_fetch_year_error_does_not_leak_key():
    responses.get(entsoe_day_ahead.BASE_URL, status=403)
    from solkalk.core.http import FetchError

    with pytest.raises(FetchError) as info:
        entsoe_day_ahead.fetch_year("SE3", 2024, api_key="HEMLIG-NYCKEL")
    assert "HEMLIG-NYCKEL" not in str(info.value)


def test_missing_position_one_uses_first_available_price():
    """If position 1 is missing, earlier slots get the first available price, not 0."""
    xml = _doc(
        "<TimeSeries><mRID>1</mRID><curveType>A03</curveType><Period>"
        "<timeInterval><start>2025-10-01T22:00Z</start><end>2025-10-02T22:00Z</end></timeInterval>"
        "<resolution>PT60M</resolution>"
        "<Point><position>3</position><price.amount>30.0</price.amount></Point>"
        "<Point><position>5</position><price.amount>50.0</price.amount></Point>"
        "</Period></TimeSeries>"
    )
    frame = entsoe_day_ahead.parse_prices(xml)
    assert len(frame) == 24
    assert frame["eur_per_mwh"].iloc[0] == 30.0
    assert frame["eur_per_mwh"].iloc[3] == 30.0
    assert frame["eur_per_mwh"].iloc[4] == 50.0
