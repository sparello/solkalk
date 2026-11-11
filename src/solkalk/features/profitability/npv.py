"""Net present value of a cash flow.

Depends on: profitability.discounting
"""

from __future__ import annotations

from solkalk.features.profitability.discounting import check_rate


def npv(cashflows: list[float], discount_rate: float) -> float:
    """Sum of the flows discounted to year 0; ``cashflows[0]`` is year 0."""
    check_rate(discount_rate)
    return sum(flow / (1.0 + discount_rate) ** year for year, flow in enumerate(cashflows))
