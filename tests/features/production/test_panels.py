"""Tests for solkalk.features.production.panels."""

from solkalk.core.models import SystemSpec
from solkalk.features.production import panels


def test_build_array_uses_tilt_azimuth_and_rated_power():
    system = SystemSpec(dc_kwp=12.5, ac_kw=10.0, tilt_deg=20.0, azimuth_deg=90.0)
    array = panels.build_array(system)
    assert array.mount.surface_tilt == 20.0
    assert array.mount.surface_azimuth == 90.0
    assert array.module_parameters["pdc0"] == 12_500.0  # kWp → W
    assert array.module_parameters["gamma_pdc"] == panels.GAMMA_PDC_PER_C
    assert array.albedo == panels.ALBEDO
    assert array.temperature_model_parameters == panels.TEMPERATURE_PARAMETERS
