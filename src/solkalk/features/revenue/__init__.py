"""Revenue: production placed on the price time axis and valued at spot price.

One module per concept: ``price_matching`` (production → price steps),
``spot_revenue``, ``capture_price``.
Depends on: core, prices (operates on the outputs of production and prices)
"""

from solkalk.features.revenue import capture_price, price_matching, spot_revenue

__all__ = ["capture_price", "price_matching", "spot_revenue"]
