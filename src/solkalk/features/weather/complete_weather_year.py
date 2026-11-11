"""Builds the pvlib-compatible weather dataset from STRÅNG irradiance.

Input : DataFrame ghi/dni/dhi (W/m², UTC, hourly) from ``strang_irradiance``
Output: DataFrame with columns ghi, dni, dhi, temp_air, wind_speed for a
        complete calendar year (8760/8784 rows), UTC index.

Decision: missing hours become 0, no interpolation. Zero production is a
conservative error (underestimates revenue); interpolation can err either way.
If any one of ghi/dni/dhi is missing or negative (a fill value) the whole hour
is zeroed, because GHI without DNI/DHI would be physically inconsistent in the
transposition step.

STRÅNG has no temperature or wind. ``temp_air``/``wind_speed`` can be given as
Series (forward/back-filled onto the yearly index) or as constants (default).

Depends on: weather.strang_irradiance
"""

from __future__ import annotations

import pandas as pd

from solkalk.features.weather import strang_irradiance

DEFAULT_TEMP_AIR_C = 10.0  # rough yearly mean for southern Sweden
DEFAULT_WIND_SPEED_MS = 2.0

COLUMNS = ["ghi", "dni", "dhi", "temp_air", "wind_speed"]


def full_year_index(year: int) -> pd.DatetimeIndex:
    """Hourly UTC index for the whole calendar year, start-of-hour convention."""
    return pd.date_range(
        start=pd.Timestamp(year=year, month=1, day=1, tz="UTC"),
        end=pd.Timestamp(year=year + 1, month=1, day=1, tz="UTC"),
        freq="h",
        inclusive="left",
        name="timestamp_utc",
    )


def build(
    irradiance: pd.DataFrame,
    year: int,
    *,
    temp_air: float | pd.Series = DEFAULT_TEMP_AIR_C,
    wind_speed: float | pd.Series = DEFAULT_WIND_SPEED_MS,
) -> pd.DataFrame:
    """Reindex to a complete year, zero missing/negative irradiance, add temperature/wind."""
    index = full_year_index(year)
    source = _require_utc(irradiance, "irradiance")
    source = source[~source.index.duplicated(keep="last")]
    frame = source[strang_irradiance.COLUMNS].reindex(index)
    components = frame[strang_irradiance.COLUMNS]
    incomplete = components.isna().any(axis=1) | (components < 0).any(axis=1)
    frame.loc[incomplete, strang_irradiance.COLUMNS] = 0.0
    frame["temp_air"] = _broadcast(temp_air, index, DEFAULT_TEMP_AIR_C)
    frame["wind_speed"] = _broadcast(wind_speed, index, DEFAULT_WIND_SPEED_MS)
    return frame[COLUMNS]


def coverage(irradiance: pd.DataFrame, year: int) -> float:
    """Fraction of the year's hours with complete irradiance data (0–1)."""
    present = irradiance[strang_irradiance.COLUMNS].dropna()
    present = present[present.index.year == year]
    return len(present.index.unique()) / len(full_year_index(year))


def _require_utc(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is None:
        raise ValueError(f"{name} must have a tz-aware DatetimeIndex (UTC)")
    if str(frame.index.tz) != "UTC":
        frame = frame.tz_convert("UTC")
    return frame


def _broadcast(value: float | pd.Series, index: pd.DatetimeIndex, default: float) -> pd.Series:
    if isinstance(value, pd.Series):
        if not isinstance(value.index, pd.DatetimeIndex) or value.index.tz is None:
            raise ValueError("temp_air/wind_speed series must have a tz-aware DatetimeIndex")
        value = value.tz_convert("UTC")
        value = value[~value.index.duplicated(keep="last")].sort_index()
        return value.reindex(index).ffill().bfill().fillna(default)
    return pd.Series(float(value), index=index)
