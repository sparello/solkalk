"""Fixtures shared by the revenue tests."""

import pandas as pd
import pytest


@pytest.fixture
def hourly_production(prices_transition):
    """1 kWh every hour over the price fixture's period."""
    hours = pd.date_range(
        prices_transition.index.min().floor("h"),
        prices_transition.index.max().floor("h"),
        freq="h",
    )
    return pd.Series(1.0, index=hours)
