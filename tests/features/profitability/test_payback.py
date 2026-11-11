"""Tests for solkalk.features.profitability.payback."""

import pytest

from solkalk.features.profitability import payback


def test_payback_interpolates():
    assert payback.payback_years([-100, 40, 40, 40]) == pytest.approx(2.5)
    assert payback.payback_years([-100, 100]) == pytest.approx(1.0)


def test_payback_zero_without_investment():
    assert payback.payback_years([0, 50, 50]) == 0.0
    assert payback.payback_years([10, -5, 50]) == 0.0


def test_payback_none_when_never_recovered():
    assert payback.payback_years([-100, 10, 10]) is None
