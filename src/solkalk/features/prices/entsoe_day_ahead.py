"""ENTSO-E Transparency Platform: day-ahead prices (document type A44) per price area.

Prices are stored raw in EUR/MWh with a UTC index; currency and local time are
handled downstream (``currency_conversion``, ``revenue.price_matching``). Parsing:
resolutions PT15M/PT30M/PT60M, position-based timestamps and forward-fill of
omitted positions (curveType A03 = "same price as the previous point"). If
position 1 is missing, the first available price is also used backwards.

The API key is read from the environment variable ENTSOE_API_KEY unless given
explicitly. The key must never end up in a file or on stdout.

Output: DataFrame with columns eur_per_mwh, resolution_min and a UTC index.

Depends on: core
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from solkalk.core.http import get_text

BASE_URL = "https://web-api.tp.entsoe.eu/api"

# EIC codes for bidding zones. Extend when adding countries.
AREA_CODES: dict[str, str] = {
    "SE1": "10Y1001A1001A44P",
    "SE2": "10Y1001A1001A45N",
    "SE3": "10Y1001A1001A46L",
    "SE4": "10Y1001A1001A47J",
}

RESOLUTION_MINUTES: dict[str, int] = {"PT15M": 15, "PT30M": 30, "PT60M": 60}
COLUMNS = ["eur_per_mwh", "resolution_min"]

PLAUSIBLE_PRICE_RANGE_EUR_MWH = (-600.0, 5000.0)
ENV_VAR = "ENTSOE_API_KEY"


class MissingApiKeyError(RuntimeError):
    pass


def api_key_from_env() -> str:
    key = os.environ.get(ENV_VAR, "")
    if not key:
        raise MissingApiKeyError(
            f"Set the environment variable {ENV_VAR} (export {ENV_VAR}=your-key)"
        )
    return key


def build_url(area_code: str, year: int, api_key: str, today: datetime | None = None) -> str:
    """URL for one calendar year. The current year is capped at today 00:00 UTC
    so the dataset only contains complete days."""
    today = today or datetime.now(UTC)
    period_end = min(f"{year + 1}0101", today.strftime("%Y%m%d")) + "0000"
    return (
        f"{BASE_URL}?documentType=A44"
        f"&in_Domain={area_code}&out_Domain={area_code}"
        f"&periodStart={year}01010000&periodEnd={period_end}"
        f"&securityToken={api_key}"
    )


def _local(tag: str) -> str:
    return tag.split("}")[-1]


def parse_prices(xml_text: str) -> pd.DataFrame:
    """A44 XML → DataFrame(eur_per_mwh, resolution_min) with UTC index.

    Omitted positions inherit the previous price. One resolution is kept per
    hour (the finest). For overlapping publications the last row per timestamp
    wins (stable sort, so document order decides).
    """
    root = ET.fromstring(xml_text)
    if _local(root.tag) == "Acknowledgement_MarketDocument":
        reason = root.findtext(".//{*}text") or "no data returned"
        raise ValueError(f"ENTSO-E acknowledgement: {reason}")

    timestamps: list[datetime] = []
    prices: list[float] = []
    steps: list[int] = []

    for period in root.iter():
        if _local(period.tag) != "Period":
            continue
        start_text = period.findtext("./{*}timeInterval/{*}start")
        end_text = period.findtext("./{*}timeInterval/{*}end")
        step = RESOLUTION_MINUTES.get(period.findtext("./{*}resolution") or "")
        if not start_text or not end_text or step is None:
            continue

        start = datetime.fromisoformat(start_text.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_text.replace("Z", "+00:00"))
        slots = int((end - start).total_seconds() / 60 / step)

        by_position: dict[int, float] = {}
        for point in period.findall("./{*}Point"):
            position = point.findtext("./{*}position")
            amount = point.findtext("./{*}price.amount")
            if position is not None and amount is not None:
                by_position[int(position)] = float(amount)
        if not by_position:
            continue

        last_price = by_position[min(by_position)]
        for slot in range(1, slots + 1):
            last_price = by_position.get(slot, last_price)
            timestamps.append(start + timedelta(minutes=(slot - 1) * step))
            prices.append(last_price)
            steps.append(step)

    frame = pd.DataFrame(
        {
            "eur_per_mwh": np.asarray(prices, dtype=float),
            "resolution_min": np.asarray(steps, dtype=int),
        },
        index=pd.DatetimeIndex(timestamps, tz="UTC", name="timestamp_utc"),
    )
    frame = keep_finest_resolution(frame.sort_index(kind="stable"))
    return frame[~frame.index.duplicated(keep="last")]


def keep_finest_resolution(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep one resolution per hour: the finest.

    After 2025-10-01 ENTSO-E often publishes a PT60M series alongside PT15M for
    the same period. Without this, :00 would get resolution 60 and :15/:30/:45
    resolution 15, and matching would distribute 1.75 h of energy per hour.
    Must run BEFORE deduplication on exact timestamps, otherwise the hourly row
    can overwrite the quarter-hour row at :00.
    """
    if frame.empty:
        return frame
    finest_per_hour = frame.groupby(frame.index.floor("h"))["resolution_min"].transform("min")
    return frame[frame["resolution_min"] == finest_per_hour]


def clip_to_year(frame: pd.DataFrame, year: int, today: datetime | None = None) -> pd.DataFrame:
    """Keep only the requested UTC year, capped at the last complete day.

    ENTSO-E delivers whole market days (CET), so a calendar-year request spills
    into the next year; without clipping, concatenated year files would contain
    duplicate timestamps at the boundary.
    """
    today = (today or datetime.now(UTC)).replace(hour=0, minute=0, second=0, microsecond=0)
    mask = (frame.index.year == year) & (frame.index < pd.Timestamp(today))
    return frame[mask]


def fetch_year(area: str, year: int, api_key: str | None = None) -> pd.DataFrame:
    area = area.upper()
    if area not in AREA_CODES:
        raise KeyError(f"Unknown price area {area!r}. Available: {sorted(AREA_CODES)}")
    key = api_key or api_key_from_env()
    xml_text = get_text(build_url(AREA_CODES[area], year, key), timeout_s=300)
    return clip_to_year(parse_prices(xml_text), year)


def validate(frame: pd.DataFrame, year: int, today: datetime | None = None) -> list[str]:
    """Coverage and plausible price range. Returns warnings."""
    warnings: list[str] = []
    today = (today or datetime.now(UTC)).replace(hour=0, minute=0, second=0, microsecond=0)
    year_start = datetime(year, 1, 1, tzinfo=UTC)
    year_end = datetime(year + 1, 1, 1, tzinfo=UTC)
    expected_hours = (min(year_end, today) - year_start).total_seconds() / 3600
    if expected_hours <= 0:
        return [f"{year} is in the future"]

    hours_covered = float(frame["resolution_min"].sum()) / 60
    coverage = hours_covered / expected_hours * 100
    if coverage < 95:
        warnings.append(f"Low coverage: {coverage:.1f} %")
    elif coverage > 101:
        warnings.append(f"Coverage above 100 % ({coverage:.1f} %): duplicate resolutions or rows?")

    if len(frame):
        low, high = PLAUSIBLE_PRICE_RANGE_EUR_MWH
        lo, hi = float(frame["eur_per_mwh"].min()), float(frame["eur_per_mwh"].max())
        if lo < low or hi > high:
            warnings.append(f"Prices outside plausible range: min {lo:.1f}, max {hi:.1f} EUR/MWh")
    return warnings


def read_csv(path: str | Path) -> pd.DataFrame:
    """Read a CSV with columns timestamp_utc, resolution_min, eur_per_mwh (others ignored)."""
    frame = pd.read_csv(path, parse_dates=["timestamp_utc"], index_col="timestamp_utc")
    frame.index = pd.DatetimeIndex(frame.index, tz="UTC") if frame.index.tz is None else frame.index
    out = frame[COLUMNS].copy()
    out["eur_per_mwh"] = out["eur_per_mwh"].astype(float)
    out["resolution_min"] = out["resolution_min"].astype(int)
    return out
