"""The panels: how they are mounted and how they turn sunlight into DC power.

Model choices (change them here, and update the regression test in
``tests/features/production/test_hourly_production.py``):
- Irradiance on the tilted panel (transposition): Hay-Davies with albedo 0.2
  (set explicitly; Perez needs air mass and is more sensitive to noise in DNI).
- DC power: PVWatts (pdc0 = ``SystemSpec.dc_kwp``, gamma_pdc = -0.4 %/°C).
- Cell temperature: PVsyst, "freestanding" parameters (ground-mounted / open
  rack). Roof-mounted with a small air gap runs hotter; "insulated" fits better.

Depends on: core, pvlib
"""

from __future__ import annotations

from pvlib.pvsystem import Array, FixedMount
from pvlib.temperature import TEMPERATURE_MODEL_PARAMETERS

from solkalk.core.models import SystemSpec

ALBEDO = 0.2
GAMMA_PDC_PER_C = -0.004
TRANSPOSITION_MODEL = "haydavies"
TEMPERATURE_MODEL = "pvsyst"
TEMPERATURE_PARAMETERS = TEMPERATURE_MODEL_PARAMETERS["pvsyst"]["freestanding"]


def build_array(system: SystemSpec) -> Array:
    """The pvlib description of the panels: fixed tilt and azimuth, rated DC power."""
    mount = FixedMount(surface_tilt=system.tilt_deg, surface_azimuth=system.azimuth_deg)
    return Array(
        mount=mount,
        albedo=ALBEDO,
        module_parameters={"pdc0": system.dc_kwp * 1000.0, "gamma_pdc": GAMMA_PDC_PER_C},
        temperature_model_parameters=TEMPERATURE_PARAMETERS,
    )
