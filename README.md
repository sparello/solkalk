# solkalk

Solar production and profitability engine for Sweden, built on
[pvlib](https://github.com/pvlib/pvlib-python). pvlib does the physics; solkalk adds
what it lacks: SMHI STRÅNG irradiance, ENTSO-E day-ahead prices per price area at
quarter-hour resolution, matching of production against prices, and investment metrics
(NPV, payback, LCOE). Country-specific tariff values live in one module per country.

## Installation

```bash
pip install -e ".[dev]"
pytest
```

## Usage

```python
from solkalk import Assumptions, PriceArea, Site, SystemSpec
from solkalk.country import sweden
from solkalk.features.prices import ecb_exchange_rates, entsoe_day_ahead
from solkalk.features.production import simulate
from solkalk.features.profitability import cashflow, npv, payback
from solkalk.features.revenue import price_matching, spot_revenue
from solkalk.features.weather import strang_irradiance, complete_weather_year

site = Site(latitude=59.33, longitude=18.07, price_area=PriceArea.SE3)
system = SystemSpec(dc_kwp=10, ac_kw=8, tilt_deg=35, azimuth_deg=180)
tariff = sweden.tariff(price_area=PriceArea.SE3, grid_fee_per_kwh=0.25)
assumptions = Assumptions(capex=150_000, opex_per_year=1_000, lifetime_years=30)

irradiance = strang_irradiance.read_csv("solar_2024.csv")  # or .fetch_year(lat, lon, 2024)
weather = complete_weather_year.build(irradiance, 2024)
ac_kwh = simulate(site, system, weather)  # hourly kWh

prices = entsoe_day_ahead.read_csv("prices_SE3_2024.csv")  # or .fetch_year("SE3", 2024)
rates = ecb_exchange_rates.read_csv("rates_SEK.csv")  # or .fetch_daily("SEK", ...)
matched = price_matching.match(ac_kwh, prices, rates)
revenue = (
    spot_revenue.spot_revenue(matched)
    + matched["export_kwh"].sum() * tariff.feed_in_compensation_per_kwh
)

flows = cashflow.annual_cashflows(revenue, assumptions, system.degradation_frac_per_year)
print(npv.npv(flows, 0.05), payback.payback_years(flows))
```

## Command line

```bash
solkalk strang --lat 59.33 --lon 18.07 --year 2024 --out solar_2024.csv
export ENTSOE_API_KEY=...   # never in a file
solkalk entsoe --areas SE3 --from-year 2023 --to-year 2026 --out-dir data/
solkalk ecb --currency SEK --from-date 2023-01-01 --out rates_SEK.csv
```

## Layout

```
src/solkalk/
├── core/            models.py  http.py  cache.py        country-neutral building blocks
├── country/         sweden.py                           Swedish values and tariff factory
├── features/
│   ├── weather/        strang_irradiance.py  complete_weather_year.py
│   │                       irradiance → pvlib weather frame
│   ├── prices/         entsoe_day_ahead.py  ecb_exchange_rates.py  currency_conversion.py
│   │                       day-ahead prices → local currency/kWh
│   ├── production/     panels.py  system_losses.py  inverter.py  hourly_production.py
│   │                   yield_per_kwp.py
│   │                       pvlib model chain → kWh per hour
│   ├── revenue/        price_matching.py  spot_revenue.py  capture_price.py
│   │                       production × price
│   └── profitability/  cashflow.py  npv.py  payback.py  lcoe.py  discounting.py
│                           cash flow and investment metrics
└── cli.py
```

Dependency rule: `core → country → features`, and inside features
`weather → prices → production → revenue → profitability` (a feature imports only features to
its left). `core/models.py` imports nothing from solkalk. Details in `docs/CONVENTIONS.md`.

## Model choices

- Solar position NREL SPA at interval centres; Hay-Davies transposition, albedo 0.2
- PVWatts DC and inverter models, PVsyst cell temperature (open rack)
- System losses as a single factor on DC (default 14 %), then AC clipping
- Hourly production, quarter-hour price valuation; one price resolution per hour

With a full year of STRÅNG data the chain gives roughly 1 000 kWh/kWp for a 35°
south-facing system in southern Sweden, in line with PVGIS.

## Data sources and references

- SMHI STRÅNG, modelled solar irradiance for Scandinavia, CC BY 4.0:
  <https://www.smhi.se/data/meteorologi/stralning>. Credit "Solar data: SMHI (STRÅNG)".
- ENTSO-E Transparency Platform, day-ahead prices (document type A44):
  <https://transparency.entsoe.eu/>. Check the platform's terms before redistributing price data.
- ECB euro foreign exchange reference rates: <https://data.ecb.europa.eu/>.
- pvlib python: Anderson, K. S. et al. (2023), *pvlib python: 2023 project update*,
  Journal of Open Source Software 8(92), 5994. <https://doi.org/10.21105/joss.05994>
- PVWatts: Dobos, A. P. (2014), *PVWatts Version 5 Manual*, NREL/TP-6A20-62641.
- Hay-Davies transposition: Hay, J. E. & Davies, J. A. (1980), *Calculation of the solar
  radiation incident on an inclined surface*, Proc. First Canadian Solar Radiation Data Workshop.
- Swedish energy tax and reduced-tax municipalities: Lag (1994:1776) om skatt på energi, 11 kap.
- Export tax credit for micro-producers: Inkomstskattelag (1999:1229), 67 kap. 27–33 §§;
  abolished from 1 January 2026 (prop. 2024/25:109). Applied in `country/sweden.py` for 2023–2025 only.
- Energy tax rates per year: Skatteverket, "Skatt på el".

## Licence

MIT.
