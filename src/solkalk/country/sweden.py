"""Sweden: every Swedish value and eligibility rule lives here, nowhere else.

The rest of the package is country-neutral and only reads ``core.models.Tariff``.
Keep this module's sources up to date: Skatteverket (energy tax per year,
export tax credit), the DSO's price list (grid fee, feed-in compensation),
Elpriskollen (supplier markups).

Depends on: core
"""

from __future__ import annotations

from solkalk.core.models import CustomerType, PriceArea, Tariff

PRICE_AREAS = (PriceArea.SE1, PriceArea.SE2, PriceArea.SE3, PriceArea.SE4)

# --- Values per year, SEK per kWh excluding VAT ------------------------------
# Source: Skatteverket, "Skatt på el" (skattesatser per år).
ENERGY_TAX_BY_YEAR: dict[int, float] = {
    2023: 0.392,
    2024: 0.428,
    2025: 0.439,
    2026: 0.360,
}
# Reduction for municipalities with reduced energy tax (Lag 1994:1776, 11 kap. 4 §).
# Defined per municipality, not per price area: every municipality in the counties of
# Norrbotten, Västerbotten and Jämtland, plus Sollefteå, Ånge, Örnsköldsvik, Ljusdal,
# Malung-Sälen, Mora, Orsa, Älvdalen and Torsby. 9.6 öre per kWh (Skatteverket, 2026).
# Households and the service sector only.
ENERGY_TAX_REDUCTION = 0.096
VAT = 0.25

# Tax credit for micro-producers ("skattereduktion för mikroproduktion av förnybar el"):
# 0.60 SEK per exported kWh, at most 30 000 kWh/year and at most the kWh imported during
# the year. Abolished from 1 January 2026 (prop. 2024/25:109): no credit for electricity
# delivered after 31 December 2025.
EXPORT_TAX_CREDIT_BY_YEAR: dict[int, float] = {
    2023: 0.60,
    2024: 0.60,
    2025: 0.60,
    2026: 0.0,
}
EXPORT_TAX_CREDIT_CAP_KWH = 30_000.0

LATEST_YEAR = max(ENERGY_TAX_BY_YEAR)


def tariff(
    *,
    price_area: PriceArea,
    year: int = LATEST_YEAR,
    customer_type: CustomerType = CustomerType.PRIVATE,
    reduced_energy_tax: bool = False,
    supplier_markup_per_kwh: float = 0.0,
    grid_fee_per_kwh: float = 0.0,
    feed_in_compensation_per_kwh: float = 0.0,
) -> Tariff:
    """Build a Swedish ``Tariff`` with the values that applied in ``year``.

    ``reduced_energy_tax`` is the caller's responsibility: it applies to the
    municipalities listed in 11 kap. 4 § of the energy tax act (see above).
    The export tax credit applies to private customers only, and only up to 2025.
    """
    if price_area not in PRICE_AREAS:
        raise ValueError(f"{price_area} is not a Swedish price area")
    if year not in ENERGY_TAX_BY_YEAR:
        raise ValueError(
            f"No Swedish tariff values for {year}; known: {sorted(ENERGY_TAX_BY_YEAR)}"
        )
    energy_tax = ENERGY_TAX_BY_YEAR[year] - (ENERGY_TAX_REDUCTION if reduced_energy_tax else 0.0)
    credit = EXPORT_TAX_CREDIT_BY_YEAR[year]
    has_credit = customer_type == CustomerType.PRIVATE and credit > 0
    return Tariff(
        energy_tax_per_kwh=energy_tax,
        currency="SEK",
        vat_frac=VAT,
        customer_type=customer_type,
        supplier_markup_per_kwh=supplier_markup_per_kwh,
        grid_fee_per_kwh=grid_fee_per_kwh,
        feed_in_compensation_per_kwh=feed_in_compensation_per_kwh,
        export_tax_credit_per_kwh=credit if has_credit else 0.0,
        export_tax_credit_cap_kwh=EXPORT_TAX_CREDIT_CAP_KWH if has_credit else None,
        export_tax_credit_limited_by_import=has_credit,
    )
