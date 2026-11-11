"""Convert raw ENTSO-E prices (EUR/MWh) to local currency per kWh with ECB rates.

The rate for each price step is the one for the step's UTC date. This is a
deliberate choice over CET: 22:00–23:59 UTC gets the previous day's rate, the
difference is negligible and it keeps the whole package in UTC.

Depends on: prices.entsoe_day_ahead, prices.ecb_exchange_rates (operates on their outputs)
"""

from __future__ import annotations

import pandas as pd

MWH_PER_KWH = 0.001


def to_local_per_kwh(prices: pd.DataFrame, rates_per_eur: pd.Series) -> pd.Series:
    """EUR/MWh → currency/kWh using the daily rate for each step's UTC date.

    ``rates_per_eur`` is daily (from ``ecb_exchange_rates.forward_fill``), naive or tz-aware.
    Days without a rate yield NaN; the caller decides whether that is an error.
    """
    prices = require_utc_index(prices, "prices")
    days = pd.DatetimeIndex(prices.index.normalize().tz_localize(None))
    rates = rates_per_eur
    if isinstance(rates.index, pd.DatetimeIndex) and rates.index.tz is not None:
        rates = rates.tz_convert("UTC").tz_localize(None)
    rates = rates[~rates.index.duplicated(keep="last")]
    rate = rates.reindex(days.normalize()).to_numpy()
    out = prices["eur_per_mwh"].to_numpy() * rate * MWH_PER_KWH
    return pd.Series(out, index=prices.index, name="price_per_kwh")


def require_utc_index(obj: pd.Series | pd.DataFrame, name: str) -> pd.Series | pd.DataFrame:
    """All time series downstream must be tz-aware; naive indexes gave silent zeros."""
    index = obj.index
    if not isinstance(index, pd.DatetimeIndex) or index.tz is None:
        raise ValueError(f"{name} must have a tz-aware DatetimeIndex (UTC)")
    if str(index.tz) != "UTC":
        obj = obj.tz_convert("UTC")
    return obj
