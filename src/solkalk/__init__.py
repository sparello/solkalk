"""solkalk: solar production and profitability engine for Sweden (and beyond).

Public API. External code should import from here, not from submodules, so the
internal layout can change without breaking anything. Pipeline features may be
imported as subpackages (``solkalk.features.weather`` etc.).
"""

from solkalk.core.models import (
    Assumptions,
    BatterySpec,
    CalculationResult,
    CustomerType,
    PriceArea,
    Site,
    SystemSpec,
    Tariff,
)
from solkalk.features.production import simulate

__version__ = "0.1.0"

__all__ = [
    "Assumptions",
    "BatterySpec",
    "CalculationResult",
    "CustomerType",
    "PriceArea",
    "Site",
    "SystemSpec",
    "Tariff",
    "simulate",
]
