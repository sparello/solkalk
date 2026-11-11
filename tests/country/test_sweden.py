"""Tests for solkalk.country.sweden."""

import pytest

from solkalk.core.models import CustomerType, PriceArea
from solkalk.country import sweden


def test_default_year_is_latest():
    assert sweden.LATEST_YEAR == 2026
    assert sweden.tariff(price_area=PriceArea.SE3).energy_tax_per_kwh == pytest.approx(0.36)


def test_energy_tax_per_year_matches_skatteverket():
    expected = {2023: 0.392, 2024: 0.428, 2025: 0.439, 2026: 0.360}
    for year, tax in expected.items():
        t = sweden.tariff(price_area=PriceArea.SE3, year=year)
        assert t.energy_tax_per_kwh == pytest.approx(tax), year


def test_no_export_tax_credit_from_2026():
    t = sweden.tariff(price_area=PriceArea.SE3, year=2026)
    assert t.export_tax_credit_per_kwh == 0.0
    assert t.export_tax_credit_cap_kwh is None
    assert t.export_tax_credit_limited_by_import is False


def test_private_export_tax_credit_up_to_2025():
    t = sweden.tariff(price_area=PriceArea.SE3, year=2025)
    assert t.currency == "SEK"
    assert t.vat_multiplier == 1.25
    assert t.export_tax_credit_per_kwh == pytest.approx(0.60)
    assert t.export_tax_credit_cap_kwh == sweden.EXPORT_TAX_CREDIT_CAP_KWH
    assert t.export_tax_credit_limited_by_import is True


def test_business_has_no_credit_and_no_vat():
    t = sweden.tariff(price_area=PriceArea.SE3, year=2024, customer_type=CustomerType.BUSINESS)
    assert t.vat_multiplier == 1.0
    assert t.export_tax_credit_per_kwh == 0.0
    assert t.export_tax_credit_cap_kwh is None


def test_reduced_energy_tax_flag():
    t = sweden.tariff(price_area=PriceArea.SE1, reduced_energy_tax=True)
    assert t.energy_tax_per_kwh == pytest.approx(0.36 - 0.096)


def test_unknown_year_rejected():
    with pytest.raises(ValueError, match="2019"):
        sweden.tariff(price_area=PriceArea.SE3, year=2019)


def test_pass_through_fees():
    t = sweden.tariff(
        price_area=PriceArea.SE4,
        supplier_markup_per_kwh=0.05,
        grid_fee_per_kwh=0.25,
        feed_in_compensation_per_kwh=0.04,
    )
    assert (t.supplier_markup_per_kwh, t.grid_fee_per_kwh, t.feed_in_compensation_per_kwh) == (
        0.05,
        0.25,
        0.04,
    )
