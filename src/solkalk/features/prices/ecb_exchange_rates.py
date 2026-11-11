"""ECB: official daily reference rates EUR → currency (series EXR/D.{currency}.EUR.SP00.A).

The ECB publishes banking days only. ``forward_fill`` fills weekends and
holidays with the latest known rate so every calendar day has a value.

Output: Series of rate (currency per EUR) with a naive daily DatetimeIndex.

Depends on: core
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import pandas as pd

from solkalk.core.http import get_text

BASE_URL = "https://data-api.ecb.europa.eu/service/data/EXR"
ACCEPT_HEADER = "application/vnd.sdmx.genericdata+xml;version=2.1"
MAX_GAP_DAYS = 7  # longest ECB gap to fill (Christmas/New Year ≈ 4–5 days)


def build_url(currency: str, from_date: str, to_date: str) -> str:
    return f"{BASE_URL}/D.{currency.upper()}.EUR.SP00.A?startPeriod={from_date}&endPeriod={to_date}"


def parse_rates(xml_text: str) -> pd.Series:
    """SDMX GenericData XML → Series {date: rate} for banking days."""
    days: list[str] = []
    values: list[float] = []
    root = ET.fromstring(xml_text)
    for obs in root.iter():
        if not obs.tag.endswith("}Obs"):
            continue
        day = value = None
        for child in obs:
            if child.tag.endswith("}ObsDimension"):
                day = child.get("value")
            elif child.tag.endswith("}ObsValue"):
                value = child.get("value")
        if day and value:
            days.append(day)
            values.append(round(float(value), 4))
    series = pd.Series(values, index=pd.to_datetime(days), dtype=float, name="rate")
    series.index.name = "date"
    series = series[~series.index.duplicated(keep="last")]
    return series.sort_index()


def fetch_rates(currency: str, from_date: str, to_date: str) -> pd.Series:
    """Official rates (banking days) for a date range (ISO dates)."""
    text = get_text(build_url(currency, from_date, to_date), headers={"Accept": ACCEPT_HEADER})
    return parse_rates(text)


def forward_fill(
    rates: pd.Series,
    from_date: str | date,
    to_date: str | date,
    *,
    max_gap_days: int | None = MAX_GAP_DAYS,
) -> pd.Series:
    """Fill every calendar day in [from_date, to_date] with the latest known rate.

    Days before the first published rate get no value (they are omitted). Days
    more than ``max_gap_days`` after the latest known rate are omitted too,
    otherwise a range in the future would silently get today's rate. ``None``
    disables the limit.
    """
    rates = _as_naive_daily(rates)
    days = pd.date_range(pd.Timestamp(from_date), pd.Timestamp(to_date), freq="D", name="date")
    filled = rates.reindex(rates.index.union(days)).sort_index().ffill()
    filled = filled.reindex(days).dropna()
    if max_gap_days is not None and not rates.empty:
        filled = filled[filled.index <= rates.index.max() + pd.Timedelta(days=max_gap_days)]
    filled.name = "rate"
    return filled


def fetch_daily(currency: str, from_date: str, to_date: str) -> pd.Series:
    """Fetch and forward-fill in one step.

    The fetch starts ``MAX_GAP_DAYS`` before ``from_date``: if the range starts on
    a weekend or holiday (1 January always is one) the first days would otherwise
    have no earlier rate to inherit and be dropped.
    """
    lookback = (pd.Timestamp(from_date) - pd.Timedelta(days=MAX_GAP_DAYS)).date().isoformat()
    return forward_fill(fetch_rates(currency, lookback, to_date), from_date, to_date)


def read_csv(path: str | Path) -> pd.Series:
    """Read a CSV with columns date, rate."""
    frame = pd.read_csv(path, parse_dates=["date"], index_col="date")
    series = frame["rate"].astype(float)
    series.name = "rate"
    return series.sort_index()


def _as_naive_daily(rates: pd.Series) -> pd.Series:
    """Normalise to a naive daily index without duplicates (the cache may give tz-aware)."""
    index = pd.DatetimeIndex(rates.index)
    if index.tz is not None:
        index = index.tz_convert("UTC").tz_localize(None)
    out = pd.Series(rates.to_numpy(), index=index.normalize(), name="rate", dtype=float)
    out.index.name = "date"
    return out[~out.index.duplicated(keep="last")].sort_index()
