"""The inverter: DC power in, AC power out, clipped at the inverter's rating.

Model choice: PVWatts inverter with nominal efficiency 0.96; nominal AC power is
``SystemSpec.ac_kw``. A system with more panel power than inverter power
(dc_kwp > ac_kw) is clipped at ``ac_kw``.

Depends on: core, pvlib
"""

from __future__ import annotations

import pandas as pd
from pvlib.inverter import pvwatts

from solkalk.core.models import SystemSpec

INVERTER_EFFICIENCY_NOM = 0.96


def inverter_parameters(system: SystemSpec) -> dict[str, float]:
    """pvlib PVWatts inverter parameters. ``pdc0`` is the DC input that gives ``ac_kw`` out."""
    return {
        "pdc0": system.ac_kw * 1000.0 / INVERTER_EFFICIENCY_NOM,
        "eta_inv_nom": INVERTER_EFFICIENCY_NOM,
    }


def dc_to_ac_w(dc_w: pd.Series, system: SystemSpec) -> pd.Series:
    """AC power [W] for a DC power series [W], never above ``ac_kw``."""
    return pvwatts(dc_w, **inverter_parameters(system))
