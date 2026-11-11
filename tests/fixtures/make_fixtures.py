"""Regenerate the synthetic irradiance fixtures. Run from the repo root:

    python tests/fixtures/make_fixtures.py

The fixtures are NOT real measurements. They are pvlib Ineichen clear-sky values
for Stockholm (59.33 N, 18.07 E), June 2024, scaled by a deterministic
"cloudiness" factor so the week contains clear, partly cloudy and overcast
hours. DNI is reduced more than GHI, and DHI is recomputed so that
GHI = DNI·cos(zenith) + DHI holds, which keeps the three components physically
consistent for the transposition step.

Outputs (all UTC, start-of-hour stamps, same formats as the real sources):
    strang_week_2024-06.csv          10–16 June, 168 rows, STRÅNG CSV format
    strang_{117,118,122}_2024-06-10.json   10–11 June as STRÅNG JSON; DNI (118) is
                                     missing 12:00 on 10 June on purpose
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from pvlib.location import Location

LAT, LON = 59.33, 18.07
HERE = Path(__file__).parent


def synthetic_week() -> pd.DataFrame:
    index = pd.date_range("2024-06-10", "2024-06-17", freq="h", tz="UTC", inclusive="left")
    location = Location(LAT, LON, tz="UTC")
    centre = index + pd.Timedelta(minutes=30)
    clear = location.get_clearsky(centre, model="ineichen")
    zenith = np.radians(location.get_solarposition(centre)["apparent_zenith"].to_numpy())

    # Deterministic cloudiness: one value per hour, varying smoothly over the week
    hours = np.arange(len(index))
    cloud = 0.55 + 0.45 * np.cos(hours / 11.0) * np.cos(hours / 37.0)  # in (0.1, 1.0]
    cloud = np.clip(cloud, 0.15, 1.0)

    ghi = clear["ghi"].to_numpy() * cloud
    dni = clear["dni"].to_numpy() * cloud**1.8
    dhi = np.clip(ghi - dni * np.cos(zenith), 0.0, None)
    dhi = np.where(ghi > 0, dhi, 0.0)

    frame = pd.DataFrame({"ghi": ghi, "dni": dni, "dhi": dhi}, index=index).round(1)
    frame.index.name = "timestamp_utc"
    return frame


def write_csv(frame: pd.DataFrame) -> None:
    out = frame.rename(columns={"ghi": "ghi_wm2", "dni": "dni_wm2", "dhi": "dhi_wm2"}).copy()
    out.index = out.index.strftime("%Y-%m-%dT%H:%M:%SZ")
    out.index.name = "timestamp_utc"
    out.to_csv(HERE / "strang_week_2024-06.csv")


def write_json(frame: pd.DataFrame) -> None:
    two_days = frame.loc["2024-06-10":"2024-06-11"]
    for column, parameter in {"ghi": 117, "dni": 118, "dhi": 122}.items():
        points = [
            {"date_time": ts.strftime("%Y-%m-%dT%H:%M:%SZ"), "value": float(v)}
            for ts, v in two_days[column].items()
        ]
        if parameter == 118:  # simulate one missing hour in DNI
            points = [p for p in points if p["date_time"] != "2024-06-10T12:00:00Z"]
        (HERE / f"strang_{parameter}_2024-06-10.json").write_text(json.dumps(points))


if __name__ == "__main__":
    week = synthetic_week()
    write_csv(week)
    write_json(week)
    print(f"wrote fixtures for ({LAT}, {LON}); weekly GHI {week['ghi'].sum() / 1000:.2f} kWh/m²")
