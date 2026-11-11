"""Data types shared by the whole package. Country-neutral by design.

Rule: this module imports NOTHING else from solkalk. Everything else may
import from here. That is what keeps the dependency graph acyclic.

Country-specific *values* and *eligibility rules* live in ``solkalk.country``;
this module only describes what a tariff, a site or a system *consists of*.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class PriceArea(StrEnum):
    """Day-ahead bidding zones. Swedish zones today; extend per country."""

    SE1 = "SE1"
    SE2 = "SE2"
    SE3 = "SE3"
    SE4 = "SE4"


class CustomerType(StrEnum):
    """Drives VAT treatment and eligibility for household-only schemes."""

    PRIVATE = "private"
    BUSINESS = "business"


@dataclass(frozen=True)
class Site:
    """Geographic location of the installation."""

    latitude: float
    longitude: float
    price_area: PriceArea
    altitude_m: float = 0.0
    name: str = ""


@dataclass(frozen=True)
class SystemSpec:
    """Physical description of the PV system."""

    dc_kwp: float
    ac_kw: float
    tilt_deg: float
    azimuth_deg: float  # pvlib convention: 180 = south, 90 = east, 270 = west
    system_losses_frac: float = 0.14  # wiring, soiling, mismatch, availability ...
    degradation_frac_per_year: float = 0.005


@dataclass(frozen=True)
class BatterySpec:
    """Optional battery attached to the system."""

    capacity_kwh: float
    power_kw: float
    roundtrip_efficiency: float = 0.90
    min_soc_frac: float = 0.10
    max_soc_frac: float = 0.95


@dataclass(frozen=True)
class Tariff:
    """Per-kWh fees and compensations, all in ``currency`` per kWh EXCLUDING VAT.

    Value of a self-consumed kWh = spot + supplier_markup + energy_tax + grid_fee
    (times (1 + vat) for private customers).
    Value of an exported kWh = spot + feed_in_compensation + export_tax_credit
    (tax credits are never subject to VAT).

    The fields are generic mechanisms. Which values apply, and whether a site is
    eligible for a reduced tax or a tax credit, is decided by the country module
    that builds the tariff (see ``solkalk.country.sweden.tariff``).
    """

    energy_tax_per_kwh: float  # effective tax: already reduced if the site qualifies
    currency: str = "SEK"
    vat_frac: float = 0.25
    customer_type: CustomerType = CustomerType.PRIVATE
    supplier_markup_per_kwh: float = 0.0  # retailer's fixed markup on spot
    grid_fee_per_kwh: float = 0.0  # DSO variable transfer fee
    feed_in_compensation_per_kwh: float = 0.0  # DSO payment for exported energy
    # Tax credit on exported energy, if the country has one. Cap in kWh/year; if
    # ``export_tax_credit_limited_by_import`` the credited kWh may also not exceed
    # the kWh imported during the year.
    export_tax_credit_per_kwh: float = 0.0
    export_tax_credit_cap_kwh: float | None = None
    export_tax_credit_limited_by_import: bool = False

    @property
    def vat_multiplier(self) -> float:
        """1 + VAT for private customers; 1.0 for businesses (VAT is deductible)."""
        return 1.0 + self.vat_frac if self.customer_type == CustomerType.PRIVATE else 1.0


@dataclass(frozen=True)
class Assumptions:
    """Economic assumptions for the calculation. Amounts in the tariff's currency."""

    capex: float
    opex_per_year: float
    lifetime_years: int = 30
    discount_rate: float = 0.05
    price_escalation_frac_per_year: float = 0.0
    annual_consumption_kwh: float | None = None  # None = pure export (solar park)
    battery: BatterySpec | None = None


@dataclass
class CalculationResult:
    """Outcome of a complete site calculation."""

    annual_production_kwh: float
    self_consumption_kwh: float
    export_kwh: float
    npv: float
    irr: float | None
    payback_years: float | None
    lcoe_per_kwh: float
    cashflows: list[float] = field(default_factory=list)
