"""Tests for solkalk.features.weather.strang_irradiance. Mirrors the module 1:1."""

import re

import pandas as pd
import responses

from solkalk.features.weather import strang_irradiance


def test_parse_parameter_gives_utc_series(strang_json):
    series = strang_irradiance.parse_parameter(strang_json(117))
    assert str(series.index.tz) == "UTC"
    assert len(series) == 48
    assert series.index.is_monotonic_increasing
    assert series.loc["2024-06-10T12:00:00Z"] > 300  # midday in June


def test_parse_parameter_empty():
    series = strang_irradiance.parse_parameter([])
    assert series.empty and str(series.index.tz) == "UTC"


def test_build_url_contains_coordinate_and_parameter():
    url = strang_irradiance.build_url(
        59.33, 18.07, 117, "2024-06-01T00:00:00", "2024-07-01T00:00:00"
    )
    assert "/lon/18.07/lat/59.33/parameter/117/" in url
    assert "from=2024-06-01T00:00:00&to=2024-07-01T00:00:00" in url


@responses.activate
def test_fetch_parameter_parses_mocked_response(strang_json):
    responses.get(
        "https://opendata-download-metanalys.smhi.se/api/category/strang1g/version/1"
        "/geotype/point/lon/18.07/lat/59.33/parameter/118/data.json",
        json=strang_json(118),
    )
    series = strang_irradiance.fetch_parameter(
        59.33, 18.07, 118, "2024-06-10T00:00:00", "2024-06-12T00:00:00"
    )
    assert len(series) == 47  # one hour is missing in the fixture
    assert pd.Timestamp("2024-06-10T12:00:00Z") not in series.index


def test_read_csv_roundtrip(strang_week, tmp_path):
    out = tmp_path / "sol.csv"
    strang_irradiance.write_csv(strang_week, out)
    again = strang_irradiance.read_csv(out)
    pd.testing.assert_frame_equal(strang_week, again)


def test_read_csv_shape_and_columns(strang_week):
    assert list(strang_week.columns) == ["ghi", "dni", "dhi"]
    assert len(strang_week) == 168
    assert str(strang_week.index.tz) == "UTC"


def test_validate_flags_short_year(strang_week):
    warnings = strang_irradiance.validate(strang_week, 2024)
    assert any("8784" in w for w in warnings)


def test_validate_passes_plausible_full_year():
    index = pd.date_range("2023-01-01", "2024-01-01", freq="h", inclusive="left", tz="UTC")
    frame = pd.DataFrame({"ghi": 115.0, "dni": 50.0, "dhi": 60.0}, index=index)  # ~1007 kWh/m2
    assert strang_irradiance.validate(frame, 2023) == []


def test_expected_hours():
    assert strang_irradiance.expected_hours(2024) == 8784
    assert strang_irradiance.expected_hours(2023) == 8760
    assert strang_irradiance.expected_hours(2100) == 8760


def test_parse_parameter_dedupes_keep_last():
    points = [
        {"date_time": "2024-06-10T12:00:00Z", "value": 100.0},
        {"date_time": "2024-06-10T12:00:00Z", "value": 200.0},
    ]
    series = strang_irradiance.parse_parameter(points)
    assert len(series) == 1 and series.iloc[0] == 200.0


def test_clip_to_year_drops_overlap_into_next_year():
    index = pd.date_range("2024-12-31T22:00Z", periods=4, freq="h")
    frame = pd.DataFrame({"ghi": 1.0, "dni": 1.0, "dhi": 1.0}, index=index)
    clipped = strang_irradiance.clip_to_year(frame, 2024)
    assert len(clipped) == 2
    assert (clipped.index.year == 2024).all()


@responses.activate
def test_fetch_year_merges_months_and_clips_overlap():
    """36 calls (12 months × 3 parameters); the API's end-inclusive ranges give a
    row on 1 Jan of the next year that must be clipped."""
    url_pattern = re.compile(
        r"https://opendata-download-metanalys\.smhi\.se/.*parameter/(\d+)/data\.json.*"
    )

    def callback(request):
        parameter = int(re.search(r"parameter/(\d+)/", request.url).group(1))
        start = re.search(r"from=([0-9T:-]+)", request.url).group(1)
        end = re.search(r"to=([0-9T:-]+)", request.url).group(1)
        points = [
            {"date_time": start + "Z", "value": float(parameter)},
            {"date_time": end + "Z", "value": float(parameter)},  # slutinklusivt
        ]
        return 200, {}, __import__("json").dumps(points)

    responses.add_callback(responses.GET, url_pattern, callback=callback)
    frame = strang_irradiance.fetch_year(59.33, 18.07, 2024)
    assert len(responses.calls) == 36
    assert (frame.index.year == 2024).all()
    assert pd.Timestamp("2025-01-01T00:00:00Z") not in frame.index
    assert frame.loc["2024-03-01T00:00:00Z", "ghi"] == 117.0
    assert frame.loc["2024-03-01T00:00:00Z", "dhi"] == 122.0
    assert len(frame) == 12  # month boundaries, duplicates merged
