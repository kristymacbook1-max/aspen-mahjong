"""Authoritative CLI: classify a trial balance and emit the FTA workbook.

    python -m financial_tools.cap263a.cli TB.xlsx \
        --entity "Acme Inc" --gross-receipts 75000000 --tax-year 2026
"""

import argparse
import sys
import zipfile
from decimal import Decimal

from .analysis import EntityProfile
from .pipeline import CapitalizationPipeline


def main(argv=None):
    ap = argparse.ArgumentParser(description="§263A/§263(a)/§266 capitalization tool")
    ap.add_argument("tb_path", help="trial balance .xlsx")
    ap.add_argument("--entity", default="")
    ap.add_argument("--entity-type", default="c_corp")
    ap.add_argument("--tax-year", type=int, default=2026)
    ap.add_argument("--gross-receipts", type=float, default=0.0)
    ap.add_argument("--no-afs", action="store_true")
    ap.add_argument("--ending-inventory", type=float, default=0.0)
    ap.add_argument("--ape", type=float, default=0.0, help="accumulated production expenditures")
    ap.add_argument("--avoided-rate", type=float, default=0.0)
    ap.add_argument("--designated", action="store_true", help="has §263A(f) designated property")
    ap.add_argument("--method", default="SPM", choices=["SPM", "MSPM", "SRM"])
    ap.add_argument("--out-dir", default="output/cap263a")
    args = ap.parse_args(argv)

    for flag, val in [("--gross-receipts", args.gross_receipts),
                      ("--ending-inventory", args.ending_inventory),
                      ("--ape", args.ape), ("--avoided-rate", args.avoided_rate)]:
        if val < 0:
            print(f"error: {flag} must be >= 0 (got {val})", file=sys.stderr)
            return 1

    profile = EntityProfile(
        entity_name=args.entity, entity_type=args.entity_type,
        tax_year=args.tax_year, avg_gross_receipts=Decimal(str(args.gross_receipts)),
        has_afs=not args.no_afs, method=args.method,
        ending_inventory_471=Decimal(str(args.ending_inventory)),
        accumulated_production_expenditures=Decimal(str(args.ape)),
        avoided_cost_rate=Decimal(str(args.avoided_rate)),
        has_designated_property=args.designated,
    )
    try:
        result = CapitalizationPipeline(args.out_dir).run(args.tb_path, profile,
                                                          company_tag=args.entity or None)
    except (FileNotFoundError, ValueError, zipfile.BadZipFile) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    b = result["bucket_totals"]
    print(f"Workbook: {result['_output_path']}")
    print(f"Lines: {len(result['rows'])}  |  IS total: ${result['is_total']:,.0f}  "
          f"|  review-flagged: {result['review_count']}")
    print(f"Capitalized: ${result['capitalized_total']:,.0f}  "
          f"Mixed: ${result['mixed_total']:,.0f}  "
          f"Deductible: ${result['deductible_total']:,.0f}")
    for bucket in b:
        if b[bucket]:
            print(f"  {bucket:22} ${b[bucket]:>14,.0f}")
    print(f"Tie check (must be 0): ${result['tie_check']:,.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
