"""Profitability: cash flow and investment metrics.

One module per concept: ``cashflow``, ``npv``, ``payback``, ``lcoe``;
``discounting`` holds what they share.

Conventions:
- ``cashflows[0]`` is year 0 (investment, negative), ``cashflows[1:]`` operating years.
- Nominal discounting; price escalation is applied to revenue per year.
- Degradation is applied to production per year: (1 - d) ** (year - 1).

Depends on: core (takes yearly revenue from ``revenue`` as input)
"""

from solkalk.features.profitability import cashflow, discounting, lcoe, npv, payback

__all__ = ["cashflow", "discounting", "lcoe", "npv", "payback"]
