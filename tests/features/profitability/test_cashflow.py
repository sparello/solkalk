"""Tests for solkalk.features.profitability.cashflow."""

from solkalk.core.models import Assumptions
from solkalk.features.profitability import cashflow


def test_annual_cashflows_shape_and_degradation():
    a = Assumptions(capex=1000, opex_per_year=10, lifetime_years=3)
    flows = cashflow.annual_cashflows(100.0, a, degradation_frac_per_year=0.1)
    assert flows[0] == -1000
    assert len(flows) == 4
    assert flows[1] == 90.0
    assert abs(flows[2] - (100 * 0.9 - 10)) < 1e-9
    assert abs(flows[3] - (100 * 0.81 - 10)) < 1e-9


def test_price_escalation_increases_revenue():
    a = Assumptions(capex=0, opex_per_year=0, lifetime_years=2, price_escalation_frac_per_year=0.05)
    flows = cashflow.annual_cashflows(100.0, a, degradation_frac_per_year=0.0)
    assert abs(flows[2] - 105.0) < 1e-9
