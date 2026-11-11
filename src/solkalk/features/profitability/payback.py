"""Payback time of a cash flow.

Depends on: nothing else in solkalk
"""

from __future__ import annotations


def payback_years(cashflows: list[float]) -> float | None:
    """Simple (undiscounted) payback time with linear interpolation within the year.

    The first year the cumulative flow reaches zero; later negative years are ignored.
    """
    if not cashflows:
        return None
    cumulative = cashflows[0]
    if cumulative >= 0:
        return 0.0  # no net investment in year 0
    for year, flow in enumerate(cashflows[1:], start=1):
        previous = cumulative
        cumulative += flow
        if cumulative >= 0:
            if flow == 0:
                return float(year)
            return year - 1 + (-previous / flow)
    return None
