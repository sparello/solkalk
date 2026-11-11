from solkalk import PriceArea, Site, SystemSpec


def test_site_is_immutable(gothenburg: Site):
    import dataclasses

    import pytest

    with pytest.raises(dataclasses.FrozenInstanceError):
        gothenburg.latitude = 0.0  # type: ignore[misc]


def test_price_area_values():
    assert [e.value for e in PriceArea] == ["SE1", "SE2", "SE3", "SE4"]


def test_system_defaults(villa_10kw: SystemSpec):
    assert 0 < villa_10kw.system_losses_frac < 0.3


def test_tariff_vat_private_vs_business(tariff_2026):
    import dataclasses

    from solkalk import CustomerType

    assert tariff_2026.vat_multiplier == 1.25
    foretag = dataclasses.replace(tariff_2026, customer_type=CustomerType.BUSINESS)
    assert foretag.vat_multiplier == 1.0


def test_tariff_has_no_country_specific_fields():
    """Country values (reductions, municipality lists) live in solkalk.country, not here."""
    import dataclasses

    from solkalk.core.models import Tariff

    names = {f.name for f in dataclasses.fields(Tariff)}
    assert not any("sweden" in n or "se_" in n for n in names)
    assert {"energy_tax_per_kwh", "vat_frac", "export_tax_credit_per_kwh"} <= names


def test_customer_type_as_plain_string_still_works(tariff_2026):
    import dataclasses

    from solkalk.core.models import Tariff

    privat = dataclasses.replace(tariff_2026, customer_type="private")  # type: ignore[arg-type]
    assert privat.vat_multiplier == 1.25
    assert Tariff(0.36, customer_type="business").vat_multiplier == 1.0  # type: ignore[arg-type]
