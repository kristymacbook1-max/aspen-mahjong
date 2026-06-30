"""Example: build the streamlined §266/§263(a)/§263A cost capitalization calc.

Most trial-balance lines are left provision="auto" so the fuzzy classifier
labels each department/cost-center + account combo. Run from financial_tools:
    python -m cost_capitalization.example_usage
"""

import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from financial_tools.cost_capitalization.analyzer import (
    CostCenter, TrialBalanceLine, Section263AInputs, Section266Election,
    Section263aElection, SmallBusinessTest, CostCapitalizationInput, PROV_AUTO,
)
from financial_tools.cost_capitalization.run_analysis import CostCapitalizationPipeline


def build_example_input() -> CostCapitalizationInput:
    cost_centers = [
        CostCenter("100", "Manufacturing", type="production", is_263a_subject=True),
        CostCenter("200", "Warehouse / Storage", type="resale", is_263a_subject=True),
        CostCenter("300", "Land Held for Development", type="development", is_263a_subject=False),
        CostCenter("400", "Corporate G&A", type="g&a", is_263a_subject=False),
        CostCenter("500", "R&D", type="service", is_263a_subject=False),
    ]

    # provision="auto" -> the classifier decides; a few left explicit to show overrides
    A = PROV_AUTO
    tb = [
        TrialBalanceLine("5000", "Direct labor", "100", Decimal("1200000"), "labor", A),
        TrialBalanceLine("5100", "Factory overhead", "100", Decimal("800000"), "overhead", A),
        TrialBalanceLine("5150", "Construction in progress", "100", Decimal("500000"), "asset", A),
        TrialBalanceLine("5200", "Equipment install costs", "100", Decimal("150000"), "acq", A),
        TrialBalanceLine("6000", "Warehouse storage & handling", "200", Decimal("400000"), "overhead", A),
        TrialBalanceLine("6100", "Purchasing department", "200", Decimal("250000"), "overhead", A),
        TrialBalanceLine("7000", "Property taxes - land", "300", Decimal("90000"), "taxes", A),
        TrialBalanceLine("7100", "Mortgage interest - land", "300", Decimal("120000"), "interest", A),
        TrialBalanceLine("8000", "Office salaries", "400", Decimal("600000"), "sga", A),
        TrialBalanceLine("8050", "Accounting department", "400", Decimal("300000"), "sga", A),
        TrialBalanceLine("8100", "Acquisition transaction costs", "400", Decimal("300000"), "txn", A),
        TrialBalanceLine("8200", "Advertising", "400", Decimal("180000"), "selling", A),
        TrialBalanceLine("9000", "Domestic R&E", "500", Decimal("500000"), "rd", A),
        TrialBalanceLine("9100", "Acquired customer list", "400", Decimal("450000"), "intangible", A),
        TrialBalanceLine("9200", "Start-up costs", "400", Decimal("60000"), "startup", A),
    ]

    section_263a = Section263AInputs(
        method="simplified_production",
        section_471_costs=Decimal("10000000"),
        additional_263a_costs=Decimal("1000000"),
        ending_inventory_471=Decimal("3000000"),
        beginning_inventory_471=Decimal("2500000"),
        accumulated_production_expenditures=Decimal("2000000"),
        avoided_cost_rate=Decimal("0.06"),
        designated_property=True,
    )

    return CostCapitalizationInput(
        company_name="Acme Manufacturing Inc",
        tax_year=2026,
        entity_type="c_corp",
        cost_centers=cost_centers,
        trial_balance=tb,
        section_263a=section_263a,
        section_266=Section266Election(unimproved_real_property=True),
        section_263a_elections=Section263aElection(
            de_minimis_safe_harbor=True, has_afs=True),
        small_business=SmallBusinessTest(
            tax_year=2026, avg_annual_gross_receipts=Decimal("75000000")),
    )


def main():
    inp = build_example_input()
    pipeline = CostCapitalizationPipeline()
    results = pipeline.run(inp, company_tag="Acme", style="lean")

    print(f"Workbook: {results['_output_path']}\n")
    print(f"{'Account':32} {'Cost center':14} {'Provision':16} {'Conf':6}")
    print("-" * 78)
    for pl in results["per_line"]:
        ln = pl["line"]
        print(f"{ln.account_name[:31]:32} {ln.cost_center_code:14} "
              f"{ln.provision:16} {ln.confidence:6}")
    t = results["totals"]
    print("\nTotals:")
    print(f"  §266            ${t['266']:>14,.2f}")
    print(f"  §263(a)         ${t['263(a)']:>14,.2f}")
    print(f"  §263A           ${t['263A']:>14,.2f}")
    print(f"  Other cap       ${t['other']:>14,.2f}")
    print(f"  Book-capitalized${t['book']:>14,.2f}")
    print(f"  Deductible      ${t['deductible']:>14,.2f}")
    print(f"  ---------------------------------")
    print(f"  M-1 addback     ${results['total_capitalized_tax']:>14,.2f}")
    print(f"  TB total        ${results['total_trial_balance']:>14,.2f}")
    u = results["unicap"]
    print(f"\n§263A absorption ratio {u['absorption_ratio']:.4f} -> "
          f"additional cap to ending inv ${u['additional_263a_capitalized']:,.2f}")


if __name__ == "__main__":
    main()
