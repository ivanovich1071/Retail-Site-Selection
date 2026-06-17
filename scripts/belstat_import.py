"""
One-time (or manual) Belstat demographics import.

Usage (from project root, with venv active):
    python scripts/belstat_import.py
    python scripts/belstat_import.py --years 2022 2023 2024
    python scripts/belstat_import.py --codes 919071 919167 919168

Writes results to console and (if DB is available) persists to demographics_zones table.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


async def main(region_codes: list[str], years: list[int]) -> None:
    from app.integrations.belstat_client import BelstatClient, REGIONS

    print(f"Fetching Belstat data for {len(region_codes)} regions, years {years}…")

    async with BelstatClient(timeout=60.0) as client:
        print("  → population (10101100003)…")
        pop = await client.get_population(region_codes, years)
        print("  → density (10101100012)…")
        density = await client.get_density(region_codes, years)

    print("\n=== Population (persons) ===")
    header = f"{'Code':<10} {'Region':<35}" + "".join(f"{y:>12}" for y in years)
    print(header)
    print("-" * len(header))
    for code in region_codes:
        name = REGIONS.get(code, code)[:34]
        row = f"{code:<10} {name:<35}"
        for y in years:
            val = pop.get(code, {}).get(y)
            row += f"{int(val):>12,}" if val is not None else f"{'—':>12}"
        print(row)

    print("\n=== Density (persons/km²) ===")
    print(header)
    print("-" * len(header))
    for code in region_codes:
        name = REGIONS.get(code, code)[:34]
        row = f"{code:<10} {name:<35}"
        for y in years:
            val = density.get(code, {}).get(y)
            row += f"{val:>12.1f}" if val is not None else f"{'—':>12}"
        print(row)

    # Save raw to file for debugging
    out = Path("belstat_import_result.json")
    out.write_text(
        json.dumps({"population": pop, "density": density}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nRaw results saved to {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import demographics from Belstat")
    parser.add_argument(
        "--codes", nargs="*", help="Region codes (default: all registered)"
    )
    parser.add_argument(
        "--years", nargs="*", type=int, help="Years (default: last 3)"
    )
    args = parser.parse_args()

    from app.integrations.belstat_client import DEFAULT_REGION_CODES

    codes = args.codes or DEFAULT_REGION_CODES
    current_year = date.today().year
    years = args.years or [current_year - 2, current_year - 1, current_year]

    asyncio.run(main(codes, years))
