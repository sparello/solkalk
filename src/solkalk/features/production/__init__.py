"""PV production from weather via pvlib.

One module per part of the plant: ``panels``, ``system_losses``, ``inverter``;
``hourly_production`` puts them together; ``yield_per_kwp`` is the key figure.

Public: ``simulate(site, system, weather)`` → Series ac_kwh, and
``yield_kwh_per_kwp(ac_kwh, system)``.
Depends on: core, weather (takes its output as input)
"""

from solkalk.features.production.hourly_production import simulate
from solkalk.features.production.yield_per_kwp import yield_kwh_per_kwp

__all__ = ["simulate", "yield_kwh_per_kwp"]
