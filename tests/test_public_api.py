import solkalk

EXPECTED = {
    "Assumptions",
    "BatterySpec",
    "CalculationResult",
    "PriceArea",
    "CustomerType",
    "Site",
    "SystemSpec",
    "Tariff",
    "simulate",
}


def test_public_api_is_exactly_the_expected_set():
    """Change EXPECTED deliberately when the API changes: it is the contract with external code."""
    assert set(solkalk.__all__) == EXPECTED
    for name in EXPECTED:
        assert hasattr(solkalk, name)
