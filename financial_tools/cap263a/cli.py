"""Authoritative CLI: classify a trial balance and emit the FTA workbook.

    python -m financial_tools.cap263a.cli TB.xlsx \
        --entity "Acme Inc" --gross-receipts 75000000 --tax-year 2026

Full-engagement mode (Runtime Pipeline — any supported upload shape:
one multi-sheet .xlsx, one engagement .json, or a directory of schedule
files; every engine whose schedules are present runs):

    python -m financial_tools.cap263a.cli --engagement engagement.json \
        --answers answers.json --entity "Acme Inc"

--answers is a Phase E interview answers file (question id -> answer);
it builds the EntityProfile and carries elections into the engines.
"""

import argparse
import sys
import zipfile
import xml.etree.ElementTree as ET
from decimal import Decimal

from .analysis import EntityProfile
from .pipeline import CapitalizationPipeline


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="§263A/§263(a)/§266/§174/§59(e) capitalization tool")
    ap.add_argument("tb_path", nargs="?", default=None,
                    help="trial balance .xlsx (TB-only mode)")
    ap.add_argument("--engagement", default=None, metavar="SOURCE",
                    help="full-engagement source: multi-sheet .xlsx, "
                         "engagement .json, or a directory of schedule files")
    ap.add_argument("--answers", default=None, metavar="JSON",
                    help="Phase E interview answers file (builds the profile "
                         "and carries elections into the engines)")
    ap.add_argument("--force", action="store_true",
                    help="compute despite blocking ingestion errors")
    ap.add_argument("--amt-exposure", action="store_true",
                    help="owners face individual AMT (§59(e) gate)")
    ap.add_argument("--afr-highest", type=float, default=None,
                    help="highest §1274(d) AFR for the WAIR fallback")
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
    ap.add_argument("--sheet", default=None,
                    help="worksheet name when the workbook has several TB-shaped sheets")
    ap.add_argument("--out-dir", default="output/cap263a")
    args = ap.parse_args(argv)

    if not args.tb_path and not args.engagement:
        ap.error("supply a trial balance path or --engagement SOURCE")
    if args.tb_path and args.engagement:
        ap.error("give either a bare TB path or --engagement, not both")

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
    source = args.tb_path or args.engagement
    try:
        pipe = CapitalizationPipeline(args.out_dir)
        if args.engagement:
            answers = None
            if args.answers:
                import json
                with open(args.answers, encoding="utf-8-sig") as f:
                    answers = json.load(f)
            result = pipe.run_engagement(
                args.engagement,
                None if answers else profile, answers=answers,
                individual_amt_exposure=args.amt_exposure,
                afr_highest=(Decimal(str(args.afr_highest))
                             if args.afr_highest is not None else None),
                force=args.force, company_tag=args.entity or None,
                tb_sheet=args.sheet)
        else:
            result = pipe.run(args.tb_path, profile,
                              company_tag=args.entity or None,
                              sheet=args.sheet)
    except (FileNotFoundError, ValueError, zipfile.BadZipFile, OSError,
            ET.ParseError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except Exception as e:                    # never dump a raw traceback at the CLI boundary
        print(f"error: unexpected failure processing {source}: "
              f"{type(e).__name__}: {e}", file=sys.stderr)
        return 1
    for w in (result.get("all_warnings")
              or ((result["unicap"].get("warnings") or [])
                  + (result.get("bucket_warnings") or [])
                  + (result.get("data_quality") or []))):
        print(f"WARNING: {w}", file=sys.stderr)
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
    # Structural partition invariant (0 by construction) — NOT a correctness
    # check. It confirms every dollar landed in exactly one bucket; it does not
    # validate the classifications.
    print(f"Partition invariant (structural, 0): ${result['tie_check']:,.0f}")
    # engagement-mode engine summaries
    if result.get("interest_263af"):
        print(f"§263A(f) capitalized: "
              f"${result['interest_263af']['total_capitalized']:,.2f}")
    if result.get("re_174"):
        print(f"§174 capitalized: ${result['re_174']['capitalized_total']:,.2f}  "
              f"deduction: ${result['re_174']['current_year_deduction']:,.2f}")
    if result.get("intangibles_263a45"):
        ig = result["intangibles_263a45"]
        print(f"§1.263(a)-4/-5 + start-up capitalized: "
              f"${ig['capitalized_total']:,.2f}  deductible: "
              f"${ig['deductible_total']:,.2f}")
    if result.get("qualified_59e") and result["qualified_59e"]["items"]:
        print(f"§59(e) elections scheduled: {len(result['qualified_59e']['items'])}")
    if result.get("basis_amortization"):
        print(f"Basis & Amortization rows: {len(result['basis_amortization'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
