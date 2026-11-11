"""Shared fixtures. Small, deterministic files live in tests/fixtures/.

Irradiance fixtures are synthetic (pvlib clear-sky × cloudiness, Stockholm); regenerate
with ``python tests/fixtures/make_fixtures.py``. Price and rate fixtures are small
extracts of public ENTSO-E / ECB data.

No real network calls in the test suite: HTTP is mocked with `responses`.
"""

from pathlib import Path

import pandas as pd
import pytest

from solkalk.core.models import Assumptions, PriceArea, Site, SystemSpec, Tariff
from solkalk.features.prices import ecb_exchange_rates, entsoe_day_ahead
from solkalk.features.weather import strang_irradiance

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures() -> Path:
    return FIXTURES


@pytest.fixture
def gothenburg() -> Site:
    return Site(latitude=57.71, longitude=11.97, price_area=PriceArea.SE3, name="Göteborg")


@pytest.fixture
def stockholm_site() -> Site:
    """The point the synthetic fixture strang_week_2024-06.csv was generated for."""
    return Site(latitude=59.33, longitude=18.07, price_area=PriceArea.SE3, name="Stockholm")


@pytest.fixture
def villa_10kw() -> SystemSpec:
    return SystemSpec(dc_kwp=10.0, ac_kw=8.0, tilt_deg=35.0, azimuth_deg=180.0)


@pytest.fixture
def tariff_2026() -> Tariff:
    return Tariff(
        energy_tax_per_kwh=0.36,
        supplier_markup_per_kwh=0.05,
        grid_fee_per_kwh=0.25,
    )


@pytest.fixture
def villa_assumptions() -> Assumptions:
    return Assumptions(capex=150_000, opex_per_year=1_000, annual_consumption_kwh=12_000)


@pytest.fixture
def strang_week() -> pd.DataFrame:
    """One synthetic week in STRÅNG format, 10–16 June 2024, 168 hours."""
    return strang_irradiance.read_csv(FIXTURES / "strang_week_2024-06.csv")


@pytest.fixture
def prices_transition() -> pd.DataFrame:
    """Real SE3 prices 30 Sep–1 Oct 2025: hourly → quarter-hourly transition."""
    return entsoe_day_ahead.read_csv(FIXTURES / "prices_SE3_2025-09-30_10-01.csv")


@pytest.fixture
def rates_flat() -> pd.Series:
    """Constant rate 11.0 SEK/EUR for all of 2025, so tests can be checked by hand."""
    days = pd.date_range("2025-01-01", "2025-12-31", freq="D", name="date")
    return pd.Series(11.0, index=days, name="rate")


@pytest.fixture
def ecb_xml() -> str:
    return (FIXTURES / "ecb_sek_2025-01.xml").read_text()


@pytest.fixture
def strang_json():
    import json

    def load(parameter: int) -> list[dict]:
        return json.loads((FIXTURES / f"strang_{parameter}_2024-06-10.json").read_text())

    return load


@pytest.fixture
def ecb_rates_jan() -> pd.Series:
    return ecb_exchange_rates.parse_rates((FIXTURES / "ecb_sek_2025-01.xml").read_text())
