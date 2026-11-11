"""Tests for solkalk.features.profitability.npv."""

import pytest

from solkalk.features.profitability import npv


def test_npv_of_zero_rate_is_sum():
    assert npv.npv([-100, 60, 60], 0.0) == 20


def test_npv_known_value():
    # -100 + 110/1.1 = 0
    assert abs(npv.npv([-100, 110], 0.10)) < 1e-9


def test_npv_discounts_each_year_correctly():
    """Non-trivial rate and non-zero result: -100 + 50/1.1 + 50/1.21 = -13.223..."""
    assert npv.npv([-100, 50, 50], 0.10) == pytest.approx(-100 + 50 / 1.1 + 50 / 1.21)
