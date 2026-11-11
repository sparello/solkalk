"""Spot revenue of the exported energy.

Input : the DataFrame from ``price_matching.match``

Depends on: nothing else in solkalk (operates on the output of price_matching)
"""

from __future__ import annotations

import pandas as pd


def spot_revenue(matched: pd.DataFrame) -> float:
    """Pure spot revenue for exported energy (before feed-in compensation, tax credits...)."""
    return float((matched["export_kwh"] * matched["price_per_kwh"]).sum())
