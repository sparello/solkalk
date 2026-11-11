"""Weather input for the simulation: STRÅNG irradiance plus temperature/wind.

Public: ``strang_irradiance`` (fetch/read), ``complete_weather_year.build`` (complete yearly frame).
Depends on: core
"""

from solkalk.features.weather import complete_weather_year, strang_irradiance

__all__ = ["strang_irradiance", "complete_weather_year"]
