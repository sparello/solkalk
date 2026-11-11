"""Shared by the discounted metrics (``npv``, ``lcoe``).

Depends on: nothing else in solkalk
"""

from __future__ import annotations


def check_rate(discount_rate: float) -> None:
    """A rate of -100 % or lower makes the discount factor undefined."""
    if discount_rate <= -1.0:
        raise ValueError("discount_rate must be > -1")
