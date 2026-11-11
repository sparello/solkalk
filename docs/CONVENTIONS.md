# Conventions

How this repository is organised and the rules every change must follow.

- Install: `pip install -e ".[dev]"`. Tests: `pytest`. Lint: `ruff check . && ruff format --check .`
- Python ≥ 3.11. src layout: code in `src/solkalk/`, tests in `tests/` mirroring the package
  (one test file per module with code), small fixtures in `tests/fixtures/` (never whole-year files). Irradiance fixtures are
  synthetic and regenerated with `python tests/fixtures/make_fixtures.py`; price and rate fixtures
  are small extracts of public ENTSO-E/ECB data.
- Language: English everywhere in code, docstrings, comments and docs. Swedish only inside
  string literals that quote Swedish law or official terms.

## Layout and dependency rule

```
core/        data types (models), HTTP, cache          imports nothing from solkalk
country/     country values and eligibility rules      imports core
features/    the pipeline                               imports core, country, and features to its LEFT:
               weather → prices → production → revenue → profitability
cli.py       command line                               imports anything
```

`core/models.py` is country-neutral: it describes what a tariff, site or system
*consists of*. Every country-specific value or rule (Swedish energy tax, municipality
lists, export tax credit) lives in `country/<name>.py` and nowhere else. Features apply
generic mechanisms parameterised by `Tariff`.

File granularity: in `revenue/` and `profitability/` one concept per file, named after the
concept (`npv.py`, `payback.py`, `capture_price.py`); a new metric gets a new file. In
`production/` one file per part of the plant (`panels.py`, `system_losses.py`, `inverter.py`),
put together in `hourly_production.py`. In
`weather/` and `prices/` one file per data source, because fetching, parsing and validating
one source read as a single chain. Call functions through their module
(`npv.npv(flows, rate)`, `price_matching.match(...)`) so the call site shows where the code lives.

Public API is exported in `src/solkalk/__init__.py`; external code imports from there.
Pipeline features may be imported as subpackages (`solkalk.features.weather` etc.).

## Conventions

- Time series: pandas with a tz-aware DatetimeIndex in **UTC**, start-of-interval stamps.
  Exception: ECB rates are naive daily dates. Rate lookup in `prices.currency_conversion` is per UTC
  date (deliberate).
- Units: energy kWh, power kW, irradiance W/m², prices raw EUR/MWh in `prices.entsoe_day_ahead`,
  local currency per kWh from `prices.currency_conversion` onwards. Money excl. VAT unless stated.
- Weather/production have a regular step (normally 1 h; 15 min supported). Prices are 15 min
  after 2025-10-01 and 60 min before. ENTSO-E may deliver hourly and quarter-hourly series in
  parallel; `entsoe_day_ahead.keep_finest_resolution` keeps one resolution per hour.
  `price_matching.distribute_to_price_steps` spreads hourly production evenly over quarters.
- Missing irradiance hours become 0 (`weather.complete_weather_year.build`), no interpolation; if one
  component is missing or negative the whole hour is zeroed.
- Naive indexes raise ValueError in `weather`, `prices.currency_conversion` and `revenue.price_matching` (they used to
  give silent zeros). A missing exchange rate for a price day raises in `price_matching.match`.
- Azimuth follows pvlib: 180 = south, 90 = east, 270 = west.
- All HTTP goes through `core.http.get_text` and is mocked in tests with `responses`. No real
  network calls in the test suite. API keys only via environment variables; `core.http.redact_url`
  masks them in every error message. Never print a URL containing a key.
- Model choices live in the file for the part they describe, documented in that file's module
  docstring: `features/production/panels.py` (transposition, cell temperature, DC model),
  `system_losses.py`, `inverter.py`; solar-position timing in `hourly_production.py`. They are
  locked by the regression test in `tests/features/production/test_hourly_production.py`.
