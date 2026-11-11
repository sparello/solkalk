"""Tests for solkalk.features.production.system_losses."""

import dataclasses

import pandas as pd

from solkalk.features.production import system_losses


def test_default_losses_remove_14_percent(villa_10kw):
    dc_w = pd.Series([0.0, 1000.0, 5000.0])
    out = system_losses.apply_system_losses(dc_w, villa_10kw)
    pd.testing.assert_series_equal(out, pd.Series([0.0, 860.0, 4300.0]))


def test_zero_losses_leave_power_unchanged(villa_10kw):
    lossless = dataclasses.replace(villa_10kw, system_losses_frac=0.0)
    dc_w = pd.Series([1000.0, 5000.0])
    pd.testing.assert_series_equal(system_losses.apply_system_losses(dc_w, lossless), dc_w)
