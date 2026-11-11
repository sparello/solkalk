"""Tests for solkalk.features.production.inverter."""

import pandas as pd
import pytest

from solkalk.core.models import SystemSpec
from solkalk.features.production import inverter

SYSTEM = SystemSpec(dc_kwp=10.0, ac_kw=5.0, tilt_deg=35.0, azimuth_deg=180.0)


def test_parameters_give_rated_ac_at_nominal_input():
    params = inverter.inverter_parameters(SYSTEM)
    assert params["eta_inv_nom"] == inverter.INVERTER_EFFICIENCY_NOM
    assert params["pdc0"] * params["eta_inv_nom"] == pytest.approx(5000.0)


def test_ac_is_clipped_at_rating_and_zero_without_input():
    dc_w = pd.Series([0.0, 2000.0, 5208.0, 9000.0])
    ac_w = inverter.dc_to_ac_w(dc_w, SYSTEM)
    assert ac_w.iloc[0] == 0.0
    assert 0.0 < ac_w.iloc[1] < 2000.0  # conversion loses a little
    assert ac_w.iloc[2] == pytest.approx(5000.0, rel=1e-3)  # nominal input → rated output
    assert ac_w.iloc[3] == pytest.approx(5000.0)  # more DC than the inverter can take
