"""Tests for solkalk.features.production.yield_per_kwp."""

import dataclasses

import pandas as pd
import pytest

from solkalk.features.production import yield_per_kwp


def test_yield_requires_capacity(villa_10kw):
    zero = dataclasses.replace(villa_10kw, dc_kwp=0.0)
    with pytest.raises(ValueError):
        yield_per_kwp.yield_kwh_per_kwp(pd.Series(dtype=float), zero)


def test_yield_is_energy_per_kwp(villa_10kw):
    ac_kwh = pd.Series([4000.0, 6000.0])
    assert yield_per_kwp.yield_kwh_per_kwp(ac_kwh, villa_10kw) == pytest.approx(1000.0)
