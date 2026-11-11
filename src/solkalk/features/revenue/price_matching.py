"""Match production against consumption and spot price per time step.

Decision: hourly resolution for production, quarter-hour valuation for revenue.
Hourly production is split evenly over the four quarters where quarter-hour
prices exist (after 2025-10-01); before that only hourly prices exist.

Input : production (kWh per step), prices (eur_per_mwh + resolution_min),
        daily rates, optional consumption (kWh per step)
Output: DataFrame per price step with production_kwh, price_per_kwh and, with
        consumption: consumption_kwh, self_consumption_kwh, export_kwh, import_kwh

Depends on: prices.currency_conversion (operates on outputs of production and prices)
"""

from __future__ import annotations

import pandas as pd

from solkalk.features.prices.currency_conversion import require_utc_index, to_local_per_kwh


def _require_unique(obj: pd.Series | pd.DataFrame, name: str) -> None:
    if not obj.index.is_unique:
        raise ValueError(f"{name} has duplicate timestamps")


def distribute_to_price_steps(hourly_kwh: pd.Series, prices: pd.DataFrame) -> pd.Series:
    """Spread hourly kWh evenly over the price steps.

    An hour with four quarter-hour prices gets kWh/4 per quarter; an hour with
    an hourly price gets the whole value. Steps without a matching hour get 0.
    Production finer than hourly (e.g. 15 min) is summed to hours first,
    otherwise the reindex would hit only the :00 rows and energy would vanish.
    """
    hourly_kwh = require_utc_index(hourly_kwh, "hourly_kwh")
    prices = require_utc_index(prices, "prices")
    _require_unique(hourly_kwh, "hourly_kwh")
    _require_unique(prices, "prices")
    hourly_kwh = hourly_kwh.resample("h").sum()
    hour_of_step = prices.index.floor("h")
    fraction = prices["resolution_min"].to_numpy() / 60.0
    per_hour = hourly_kwh.reindex(hour_of_step).fillna(0.0).to_numpy()
    return pd.Series(per_hour * fraction, index=prices.index, name="kwh")


def match(
    production_kwh: pd.Series,
    prices: pd.DataFrame,
    rates_per_eur: pd.Series,
    consumption_kwh: pd.Series | None = None,
    *,
    allow_missing_rates: bool = False,
) -> pd.DataFrame:
    """Put production (and optional consumption) on the price time axis in currency/kWh.

    ``production_kwh`` and ``consumption_kwh`` are kWh series with a UTC index at
    hourly or finer resolution (finer is summed to hours). Coarser than hourly
    (daily values) would land on a single hour: do not pass that here.
    Price steps without an exchange rate raise ValueError, because the revenue
    would otherwise silently drop out; ``allow_missing_rates=True`` leaves NaN.
    Without consumption (solar park) everything is exported. With consumption,
    self-consumption is min(production, consumption) per step, no storage;
    storage is not modelled.
    """
    prices = require_utc_index(prices, "prices")
    _require_unique(prices, "prices")
    frame = pd.DataFrame(index=prices.index)
    frame["production_kwh"] = distribute_to_price_steps(production_kwh, prices)
    frame["price_per_kwh"] = to_local_per_kwh(prices, rates_per_eur)
    missing = frame["price_per_kwh"].isna()
    if missing.any() and not allow_missing_rates:
        days = sorted({d.date().isoformat() for d in frame.index[missing]})
        suffix = "…" if len(days) > 5 else ""
        raise ValueError(f"Exchange rate missing for {len(days)} day(s): {days[:5]}{suffix}")

    if consumption_kwh is None:
        frame["consumption_kwh"] = 0.0
        frame["self_consumption_kwh"] = 0.0
        frame["export_kwh"] = frame["production_kwh"]
        frame["import_kwh"] = 0.0
        return frame

    frame["consumption_kwh"] = distribute_to_price_steps(consumption_kwh, prices)
    frame["self_consumption_kwh"] = frame[["production_kwh", "consumption_kwh"]].min(axis=1)
    frame["export_kwh"] = frame["production_kwh"] - frame["self_consumption_kwh"]
    frame["import_kwh"] = frame["consumption_kwh"] - frame["self_consumption_kwh"]
    return frame
