"""Yield per kWp ("specific yield"): yearly production per installed kWp.

The number installers and customers compare, independent of system size;
roughly 800–1 000 kWh/kWp for a well-oriented system in Sweden.

Depends on: core (takes the output of ``hourly_production.simulate`` as input)
"""

from __future__ import annotations

import pandas as pd

from solkalk.core.models import SystemSpec


def yield_kwh_per_kwp(ac_kwh: pd.Series, system: SystemSpec) -> float:
    """Total production divided by installed DC power [kWh/kWp]."""
    if system.dc_kwp <= 0:
        raise ValueError("dc_kwp must be > 0")
    return float(ac_kwh.sum()) / system.dc_kwp
