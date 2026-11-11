"""Tests for solkalk.features.production.hourly_production (pvlib)."""

import pandas as pd
import pytest
from pvlib.temperature import TEMPERATURE_MODEL_PARAMETERS

from solkalk.core.models import PriceArea, Site, SystemSpec
from solkalk.features.production import hourly_production, inverter, panels
from solkalk.features.weather import complete_weather_year


@pytest.fixture
def week_weather(strang_week):
    """Only the fixture week (168 h): fast to simulate."""
    return complete_weather_year.build(strang_week, 2024).loc[strang_week.index]


def test_simulate_shape_and_sign(stockholm_site, villa_10kw, week_weather):
    ac = hourly_production.simulate(stockholm_site, villa_10kw, week_weather)
    assert len(ac) == 168
    assert ac.index.equals(week_weather.index)
    assert (ac >= 0).all()
    assert ac.loc["2024-06-12T00:00:00Z"] == 0.0  # night (00 UTC = 02 local)


def test_simulate_week_in_june_is_plausible(stockholm_site, villa_10kw, week_weather):
    """10 kWp in June: ~25–70 kWh/day is plausible for a mixed week in central Sweden."""
    ac = hourly_production.simulate(stockholm_site, villa_10kw, week_weather)
    per_day = ac.sum() / 7
    assert 25 < per_day < 80, per_day


def test_ac_never_exceeds_inverter_rating(stockholm_site, week_weather):
    small_inverter = SystemSpec(dc_kwp=10.0, ac_kw=5.0, tilt_deg=35.0, azimuth_deg=180.0)
    ac = hourly_production.simulate(stockholm_site, small_inverter, week_weather)
    assert ac.max() <= 5.0 + 1e-9
    # 10 kWp on a 5 kW inverter in June must clip: nominal AC is reached exactly
    assert ac.max() == pytest.approx(5.0, abs=1e-6)


def test_south_beats_north(stockholm_site, week_weather):
    south = SystemSpec(dc_kwp=10.0, ac_kw=10.0, tilt_deg=35.0, azimuth_deg=180.0)
    north = SystemSpec(dc_kwp=10.0, ac_kw=10.0, tilt_deg=35.0, azimuth_deg=0.0)
    assert hourly_production.simulate(stockholm_site, south, week_weather).sum() > (
        hourly_production.simulate(stockholm_site, north, week_weather).sum()
    )


def test_losses_reduce_output(stockholm_site, week_weather):
    base = SystemSpec(
        dc_kwp=10.0, ac_kw=10.0, tilt_deg=35.0, azimuth_deg=180.0, system_losses_frac=0.0
    )
    lossy = SystemSpec(
        dc_kwp=10.0, ac_kw=10.0, tilt_deg=35.0, azimuth_deg=180.0, system_losses_frac=0.2
    )
    a = hourly_production.simulate(stockholm_site, base, week_weather).sum()
    b = hourly_production.simulate(stockholm_site, lossy, week_weather).sum()
    assert 0.75 < b / a < 0.85


def test_empty_weather(stockholm_site, villa_10kw):
    empty = pd.DataFrame(
        columns=complete_weather_year.COLUMNS, index=pd.DatetimeIndex([], tz="UTC")
    )
    assert hourly_production.simulate(stockholm_site, villa_10kw, empty).empty


def test_model_choices_are_locked(stockholm_site, villa_10kw):
    """docs/CONVENTIONS.md: model choices change deliberately, are documented and get a new test."""
    chain = hourly_production.build_model_chain(stockholm_site, villa_10kw)
    assert chain.transposition_model == "haydavies"
    assert chain.temperature_model.__name__ == "pvsyst_temp"
    assert chain.dc_model.__name__ == "pvwatts_dc"
    assert chain.aoi_model.__name__ == "physical_aoi_loss"
    assert panels.TEMPERATURE_PARAMETERS == TEMPERATURE_MODEL_PARAMETERS["pvsyst"]["freestanding"]
    assert panels.ALBEDO == 0.2
    assert inverter.INVERTER_EFFICIENCY_NOM == 0.96


def test_irregular_index_rejected(stockholm_site, villa_10kw, week_weather):
    gappy = week_weather.drop(week_weather.index[10:20])
    with pytest.raises(ValueError, match="regular"):
        hourly_production.simulate(stockholm_site, villa_10kw, gappy)


def test_quarter_hour_weather_gives_similar_energy(stockholm_site, villa_10kw, week_weather):
    """Centering offset and energy conversion follow the time step, not a fixed 1 h."""
    quarter = week_weather.resample("15min").ffill()
    hourly = hourly_production.simulate(stockholm_site, villa_10kw, week_weather).sum()
    fine = hourly_production.simulate(stockholm_site, villa_10kw, quarter).sum()
    assert abs(fine / hourly - 1.0) < 0.05


def test_regression_fixture_week_total(stockholm_site, villa_10kw, week_weather):
    """Numerical anchor for the whole model chain (centering, albedo, inverter, losses).

    Change deliberately when a model choice changes: update the value and the
    module docstrings in features/production/ together.
    Reference: 244.66 kWh, synthetic week, 10 kWp / 8 kW AC.
    """
    ac = hourly_production.simulate(stockholm_site, villa_10kw, week_weather)
    assert ac.sum() == pytest.approx(244.658, rel=2e-3)
    assert ac.loc["2024-06-12T11:00:00Z"] == pytest.approx(3.9805, rel=5e-3)


def test_interval_centering_matters():
    """Synthetic clear-sky weather (evaluated at interval centres) at longitude 15 °E,
    where solar noon falls at ~11:00 UTC in mid-June, so hours equidistant from
    11:00 must give equal production for a south-facing array. Without the
    +½-step centering the 05/16 ratio becomes ≈ 0.40 instead of ≈ 1.0."""
    from pvlib.location import Location

    site = Site(latitude=59.33, longitude=15.0, price_area=PriceArea.SE3)
    system = SystemSpec(dc_kwp=10.0, ac_kw=10.0, tilt_deg=35.0, azimuth_deg=180.0)
    index = pd.date_range("2024-06-12", periods=24, freq="h", tz="UTC")
    clear = Location(site.latitude, site.longitude, tz="UTC").get_clearsky(
        index + pd.Timedelta(minutes=30)
    )
    synthetic = pd.DataFrame(
        {
            "ghi": clear["ghi"].to_numpy(),
            "dni": clear["dni"].to_numpy(),
            "dhi": clear["dhi"].to_numpy(),
            "temp_air": 15.0,
            "wind_speed": 2.0,
        },
        index=index,
    )
    ac = hourly_production.simulate(site, system, synthetic)
    assert ac.loc[index[7]] / ac.loc[index[14]] == pytest.approx(1.0, abs=0.05)
    assert ac.loc[index[5]] / ac.loc[index[16]] == pytest.approx(1.0, abs=0.08)
