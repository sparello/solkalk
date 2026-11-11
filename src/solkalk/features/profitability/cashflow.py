"""Yearly cash flow of the investment.

``cashflows[0]`` is year 0 (investment, negative), ``cashflows[1:]`` operating years.

Depends on: core (takes yearly revenue from ``revenue`` as input)
"""

from __future__ import annotations

from solkalk.core.models import Assumptions


def annual_cashflows(
    revenue_year1: float,
    assumptions: Assumptions,
    degradation_frac_per_year: float,
) -> list[float]:
    """Cash flow years 0..lifetime: -CAPEX, then revenue·degradation·escalation - OPEX."""
    if assumptions.lifetime_years < 1:
        raise ValueError("lifetime_years must be ≥ 1")
    flows = [-assumptions.capex]
    for year in range(1, assumptions.lifetime_years + 1):
        production_factor = (1.0 - degradation_frac_per_year) ** (year - 1)
        price_factor = (1.0 + assumptions.price_escalation_frac_per_year) ** (year - 1)
        revenue = revenue_year1 * production_factor * price_factor
        flows.append(revenue - assumptions.opex_per_year)
    return flows
