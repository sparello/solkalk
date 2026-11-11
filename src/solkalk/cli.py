"""Command line for data fetching.

solkalk strang --lat 59.33 --lon 18.07 --year 2024 --out solar_2024.csv
solkalk entsoe --areas SE1,SE2,SE3,SE4 --from-year 2023 --to-year 2026 --out-dir data/
solkalk ecb --currency SEK --from-date 2023-01-01 --out rates_SEK.csv
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from solkalk.core.http import FetchError
from solkalk.features.prices import ecb_exchange_rates, entsoe_day_ahead
from solkalk.features.weather import strang_irradiance


def _cmd_strang(args: argparse.Namespace) -> int:
    try:
        frame = strang_irradiance.fetch_year(args.lat, args.lon, args.year)
    except FetchError as error:
        print(error)
        return 1
    for warning in strang_irradiance.validate(frame, args.year):
        print(f"⚠️  {warning}")
    out = args.out or f"solar_{args.lat}_{args.lon}_{args.year}.csv"
    strang_irradiance.write_csv(frame, out)
    print(f"Wrote {len(frame)} rows to {out}")
    return 0


def _cmd_entsoe(args: argparse.Namespace) -> int:
    try:
        api_key = entsoe_day_ahead.api_key_from_env()
    except entsoe_day_ahead.MissingApiKeyError as error:
        print(error)
        return 1
    areas = [a.strip().upper() for a in args.areas.split(",")]
    unknown = [a for a in areas if a not in entsoe_day_ahead.AREA_CODES]
    if unknown:
        print(f"Unknown price area(s) {unknown}. Available: {sorted(entsoe_day_ahead.AREA_CODES)}")
        return 1
    current_year = datetime.now(UTC).year
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for area in areas:
        for year in range(args.from_year, args.to_year + 1):
            out = out_dir / f"prices_{area}_{year}.csv"
            if out.exists() and year != current_year:
                print(f"  {area} {year}: exists, skipping")
                continue
            try:
                frame = entsoe_day_ahead.fetch_year(area, year, api_key)
            except (ValueError, FetchError) as error:
                print(f"  {area} {year}: {error}")
                continue
            for warning in entsoe_day_ahead.validate(frame, year):
                print(f"  ⚠️  {area} {year}: {warning}")
            frame.to_csv(out, date_format="%Y-%m-%dT%H:%M:%SZ")
            print(f"  {area} {year}: {len(frame)} rows → {out}")
    return 0


def _cmd_ecb(args: argparse.Namespace) -> int:
    try:
        series = ecb_exchange_rates.fetch_daily(args.currency, args.from_date, args.to_date)
    except FetchError as error:
        print(error)
        return 1
    if series.empty:
        print("No rates returned: check currency code and date range")
        return 1
    out = args.out or f"rates_{args.currency.upper()}.csv"
    series.to_csv(out, date_format="%Y-%m-%d")
    print(f"{len(series)} days → {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="solkalk", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("strang", help="Fetch STRÅNG irradiance for one year")
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--out")
    p.set_defaults(func=_cmd_strang)

    p = sub.add_parser("entsoe", help="Fetch day-ahead prices per price area and year")
    p.add_argument("--areas", default="SE1,SE2,SE3,SE4")
    p.add_argument("--from-year", type=int, default=2023)
    p.add_argument("--to-year", type=int, default=datetime.now(UTC).year)
    p.add_argument("--out-dir", default=".")
    p.set_defaults(func=_cmd_entsoe)

    p = sub.add_parser("ecb", help="Fetch daily EUR rates, forward-filled")
    p.add_argument("--currency", default="SEK")
    p.add_argument("--from-date", default="2023-01-01")
    p.add_argument("--to-date", default=(datetime.now(UTC).date() - timedelta(days=1)).isoformat())
    p.add_argument("--out")
    p.set_defaults(func=_cmd_ecb)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
