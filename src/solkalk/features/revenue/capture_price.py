"""Capture price: the average price the plant actually gets, and how it compares
with the period's mean price.

Input : the DataFrame from ``price_matching.match`` and the raw price DataFrame

Depends on: nothing else in solkalk (operates on the output of price_matching)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def capture_price_per_kwh(matched: pd.DataFrame) -> float:
    """Export-weighted average price: what the plant actually "captures".

    Equal to the production-weighted price when there is no consumption.
    Compared with the year's time-weighted mean price, the ratio (capture rate)
    shows solar cannibalisation: the sun produces when prices are low.
    """
    exported = matched["export_kwh"].sum()
    if exported <= 0:
        return 0.0
    revenue = (matched["export_kwh"] * matched["price_per_kwh"]).sum(skipna=True)
    return float(revenue) / float(exported)


def time_weighted_mean_price_per_kwh(matched: pd.DataFrame, prices: pd.DataFrame) -> float:
    """Time-weighted mean price: quarter-hour prices weigh 1/4 of hourly ones,
    otherwise mixed years are skewed."""
    weights = prices["resolution_min"].reindex(matched.index).to_numpy() / 60.0
    price = matched["price_per_kwh"].to_numpy()
    valid = ~np.isnan(price)
    if not valid.any():
        return 0.0
    return float((price[valid] * weights[valid]).sum() / weights[valid].sum())


def capture_rate(matched: pd.DataFrame, prices: pd.DataFrame) -> float:
    """Capture price / time-weighted mean price. 1.0 = production captures the average."""
    mean_price = time_weighted_mean_price_per_kwh(matched, prices)
    if mean_price == 0:
        return 0.0
    return capture_price_per_kwh(matched) / mean_price
