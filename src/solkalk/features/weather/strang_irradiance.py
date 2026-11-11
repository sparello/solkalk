"""SMHI STRÅNG: modelled hourly solar irradiance for any point in Scandinavia.

Parameters (physically consistent with each other: GHI ≈ DNI·cos(zenith) + DHI):
    117 = GHI (global horizontal), 118 = DNI (direct normal), 122 = DHI (diffuse)
Values are hourly means in W/m², timestamps in UTC. Free, no API key.
Licence CC BY 4.0: credit "Solar data: SMHI (STRÅNG)" in reports.

Output: DataFrame with columns ghi, dni, dhi [W/m²] and a tz-aware UTC
DatetimeIndex. Timestamp convention assumed: start of hour; the production
feature centres the solar position inside the interval.

Depends on: core
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from solkalk.core.http import get_text

BASE_URL = (
    "https://opendata-download-metanalys.smhi.se/api/category/strang1g/version/1"
    "/geotype/point/lon/{lon}/lat/{lat}/parameter/{parameter}/data.json"
    "?from={start}&to={end}"
)

PARAMETERS: dict[str, int] = {"ghi": 117, "dni": 118, "dhi": 122}
COLUMNS = list(PARAMETERS)

PLAUSIBLE_YEARLY_GHI_KWH_M2 = (700.0, 1300.0)


def build_url(lat: float, lon: float, parameter: int, start: str, end: str) -> str:
    return BASE_URL.format(lat=lat, lon=lon, parameter=parameter, start=start, end=end)


def parse_parameter(json_points: list[dict]) -> pd.Series:
    """STRÅNG JSON (``[{"date_time": ..., "value": ...}, ...]``) → Series (UTC)."""
    if not json_points:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([], tz="UTC"))
    frame = pd.DataFrame(json_points)
    index = pd.to_datetime(frame["date_time"], utc=True)
    series = pd.Series(frame["value"].astype(float).to_numpy(), index=index)
    return series[~series.index.duplicated(keep="last")].sort_index()


def fetch_parameter(lat: float, lon: float, parameter: int, start: str, end: str) -> pd.Series:
    """Fetch one parameter for a time range (ISO strings without timezone = UTC)."""
    text = get_text(build_url(lat, lon, parameter, start, end))
    return parse_parameter(json.loads(text))


def _month_ranges(year: int) -> list[tuple[str, str]]:
    ranges = []
    for month in range(1, 13):
        start = f"{year}-{month:02d}-01T00:00:00"
        end = f"{year + 1}-01-01T00:00:00" if month == 12 else f"{year}-{month + 1:02d}-01T00:00:00"
        ranges.append((start, end))
    return ranges


def fetch_year(lat: float, lon: float, year: int) -> pd.DataFrame:
    """Fetch GHI/DNI/DHI for a whole calendar year, month by month.

    The API's ranges are end-inclusive, so the overlap into the next year is
    clipped. Missing hours stay NaN here; ``complete_weather_year.build`` decides what to do.
    """
    parts: dict[str, list[pd.Series]] = {column: [] for column in COLUMNS}
    for start, end in _month_ranges(year):
        for column, parameter in PARAMETERS.items():
            parts[column].append(fetch_parameter(lat, lon, parameter, start, end))

    frame = pd.DataFrame({column: pd.concat(series) for column, series in parts.items()})
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    frame.index.name = "timestamp_utc"
    return clip_to_year(frame, year)


def clip_to_year(frame: pd.DataFrame, year: int) -> pd.DataFrame:
    return frame[frame.index.year == year]


def expected_hours(year: int) -> int:
    return 8784 if pd.Timestamp(year=year, month=1, day=1).is_leap_year else 8760


def validate(frame: pd.DataFrame, year: int) -> list[str]:
    """Sanity checks. Returns a list of warnings (empty = all good)."""
    warnings: list[str] = []
    if len(frame) != expected_hours(year):
        warnings.append(f"Expected {expected_hours(year)} hours, got {len(frame)}")

    missing = int(frame[COLUMNS].isna().any(axis=1).sum())
    if missing:
        warnings.append(f"{missing} hours are missing at least one component")

    yearly_ghi = float(frame["ghi"].fillna(0).sum()) / 1000
    low, high = PLAUSIBLE_YEARLY_GHI_KWH_M2
    if not low <= yearly_ghi <= high:
        warnings.append(
            f"Yearly GHI {yearly_ghi:.0f} kWh/m² outside plausible range {low:.0f}–{high:.0f}"
        )
    return warnings


def read_csv(path: str | Path) -> pd.DataFrame:
    """Read a CSV with columns timestamp_utc, ghi_wm2, dni_wm2, dhi_wm2."""
    frame = pd.read_csv(path, parse_dates=["timestamp_utc"], index_col="timestamp_utc")
    frame.index = pd.DatetimeIndex(frame.index, tz="UTC") if frame.index.tz is None else frame.index
    frame = frame.rename(columns={"ghi_wm2": "ghi", "dni_wm2": "dni", "dhi_wm2": "dhi"})
    return frame[COLUMNS].astype(float)


def write_csv(frame: pd.DataFrame, path: str | Path) -> None:
    out = frame[COLUMNS].rename(columns={"ghi": "ghi_wm2", "dni": "dni_wm2", "dhi": "dhi_wm2"})
    out.index = out.index.strftime("%Y-%m-%dT%H:%M:%SZ")
    out.index.name = "timestamp_utc"
    out.to_csv(path)
