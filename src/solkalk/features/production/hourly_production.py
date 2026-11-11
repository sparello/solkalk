"""Hourly production: puts the panels, the losses and the inverter together and
runs them over the weather with pvlib (PVWatts-style model chain).

Input : Site, SystemSpec, weather DataFrame from ``weather.complete_weather_year.build``
Output: Series ac_kwh, energy per time step, same index as the weather

The chain, and where each model choice lives:
1. Solar position: pvlib default (NREL SPA), evaluated at the MIDDLE of each
   interval (+half a step) because STRÅNG values are interval means stamped at
   the interval start. (this file)
2. Irradiance on the panel, cell temperature, DC power: ``panels``.
3. System losses on DC: ``system_losses``.
4. DC → AC with clipping: ``inverter``.

Change a model choice in the file that owns it, never at the call sites, and
update the regression test.

Depends on: core, pvlib (takes the weather DataFrame as input)
"""

from __future__ import annotations

import pandas as pd
from pvlib.location import Location
from pvlib.modelchain import ModelChain
from pvlib.pvsystem import PVSystem

from solkalk.core.models import Site, SystemSpec
from solkalk.features.production import inverter, panels, system_losses


def build_model_chain(site: Site, system: SystemSpec) -> ModelChain:
    """The pvlib model chain for this site and system."""
    location = Location(
        latitude=site.latitude,
        longitude=site.longitude,
        altitude=site.altitude_m,
        tz="UTC",
        name=site.name or None,
    )
    pv_system = PVSystem(
        arrays=[panels.build_array(system)],
        inverter_parameters=inverter.inverter_parameters(system),
    )
    return ModelChain(
        pv_system,
        location,
        transposition_model=panels.TRANSPOSITION_MODEL,
        dc_model="pvwatts",
        ac_model="pvwatts",
        aoi_model="physical",
        spectral_model="no_loss",
        temperature_model=panels.TEMPERATURE_MODEL,
        losses_model="no_loss",
    )


def simulate(site: Site, system: SystemSpec, weather: pd.DataFrame) -> pd.Series:
    """Return AC production in kWh per time step (Series with the weather's index)."""
    if weather.empty:
        return pd.Series(dtype=float, index=weather.index, name="ac_kwh")

    chain = build_model_chain(site, system)
    hours = step_hours(weather.index)
    centred = weather.copy()
    centred.index = weather.index + pd.Timedelta(hours=hours / 2)
    chain.run_model(centred)

    # DC losses before the inverter: rerun the AC step on reduced DC
    dc_w = system_losses.apply_system_losses(chain.results.dc, system)
    ac_w = inverter.dc_to_ac_w(dc_w, system)

    ac_kwh = ac_w.clip(lower=0.0).fillna(0.0) / 1000.0 * hours
    ac_kwh.index = weather.index
    ac_kwh.name = "ac_kwh"
    return ac_kwh


def step_hours(index: pd.DatetimeIndex) -> float:
    """Time step in hours. Requires a regular index; gaps raise instead of
    silently changing the energy conversion."""
    if len(index) < 2:
        return 1.0
    diffs = pd.Series(index[1:] - index[:-1])
    if diffs.nunique() != 1:
        raise ValueError(
            "Weather index must be regular without gaps (use complete_weather_year.build)"
        )
    return float(diffs.iloc[0] / pd.Timedelta(hours=1))
