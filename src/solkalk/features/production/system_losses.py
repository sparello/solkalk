"""System losses between the panels and the inverter.

Model choice: one factor, ``SystemSpec.system_losses_frac`` (default 14 %: wiring,
soiling, mismatch, availability ...), applied to DC power before the inverter.
It replaces the PVWatts default of 14.08 %.

Depends on: core
"""

from __future__ import annotations

import pandas as pd

from solkalk.core.models import SystemSpec


def apply_system_losses(dc_w: pd.Series, system: SystemSpec) -> pd.Series:
    """DC power [W] left after system losses."""
    return dc_w * (1.0 - system.system_losses_frac)
