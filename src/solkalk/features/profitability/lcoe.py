"""Levelised cost of energy.

Depends on: profitability.discounting
"""

from __future__ import annotations

from solkalk.features.profitability.discounting import check_rate


def lcoe_per_kwh(
    costs: list[float],
    production_kwh_per_year: list[float],
    discount_rate: float,
) -> float:
    """LCOE = discounted costs / discounted production.

    ``costs[0]`` is CAPEX, then OPEX per year, as POSITIVE costs (unlike
    ``cashflow.annual_cashflows``, which are signed net flows).
    ``production_kwh_per_year[i]`` is the production in year i+1.
    """
    check_rate(discount_rate)
    if len(costs) != len(production_kwh_per_year) + 1:
        raise ValueError(
            "costs needs lifetime+1 elements (CAPEX + OPEX per year) and "
            "production_kwh_per_year lifetime elements"
        )
    discounted_costs = sum(cost / (1.0 + discount_rate) ** year for year, cost in enumerate(costs))
    discounted_energy = sum(
        kwh / (1.0 + discount_rate) ** (year + 1)
        for year, kwh in enumerate(production_kwh_per_year)
    )
    if discounted_energy <= 0:
        raise ValueError("No production: LCOE undefined")
    return discounted_costs / discounted_energy
