"""Example: build a §266/§263(a)/§263A cost capitalization workbook.

Run from the financial_tools directory:
    python -m cost_capitalization.example_usage
"""

import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from financial_tools.cost_capitalization.analyzer import (
    CostCenter, TrialBalanceLine, AllocationOverlay,
    Section263AInputs, Section266Election, Section263aElection, SmallBusinessTest,
    CostCapitalizationInput,
)
from financial_tools.cost_capitalization.run_analysis import CostCapitalizationPipeline


def build_example_input() -> CostCapitalizationInput:
    cost_centers = [
        CostCenter("100", "Manufacturing", type="production", is_263a_subject=True),
        CostCenter("200", "Warehouse / Storage", type="resale", is_263a_subject=True),
        CostCenter("300", "Land Held for Development", type="g&a", is_263a_subject=False),
        CostCenter("400", "Corporate G&A", type="g&a", is_263a_subject=False),
        CostCenter("500", "R&D", type="service", is_263a_subject=False),
    ]

    tb = [
        # Manufacturing — UNICAP production costs
        TrialBalanceLine("5000", "Direct labor", "100", Decimal("1200000"), "labor", "263A"),
        TrialBalanceLine("5100", "Factory overhead", "100", Decimal("800000"), "overhead", "mixed"),
        TrialBalanceLine("5200", "Equipment install costs", "100", Decimal("150000"), "acq", "263(a)"),
        # Warehouse — storage/handling (resale)
        TrialBalanceLine("6000", "Storage & handling", "200", Decimal("400000"), "overhead", "263A"),
        TrialBalanceLine("6100", "Purchasing dept", "200", Decimal("250000"), "overhead", "mixed"),
        # Land held for development — §266 carrying charges
        TrialBalanceLine("7000", "Property taxes - land", "300", Decimal("90000"), "taxes", "266"),
        TrialBalanceLine("7100", "Interest - land loan", "300", Decimal("120000"), "interest", "266"),
        # Corporate G&A — mostly deductible
        TrialBalanceLine("8000", "Office salaries", "400", Decimal("600000"), "sga", "deductible"),
        TrialBalanceLine("8100", "Acquisition transaction costs", "400", Decimal("300000"), "txn", "263(a)"),
        # R&D and other capitalization
        TrialBalanceLine("9000", "Domestic R&E", "500", Decimal("500000"), "rd", "other_cap",
                         other_cap_section="174A"),
        TrialBalanceLine("9100", "Acquired customer list", "400", Decimal("450000"), "intangible",
                         "other_cap", other_cap_section="197"),
        TrialBalanceLine("9200", "Start-up costs", "400", Decimal("60000"), "startup", "other_cap",
                         other_cap_section="195"),
    ]

    allocations = [
        # Factory overhead (CC 100): mostly UNICAP, some deductible
        AllocationOverlay("100", pct_266=Decimal("0"), pct_263a_acq=Decimal("10"),
                          pct_263A=Decimal("80"), pct_deductible=Decimal("10")),
        # Purchasing (CC 200): UNICAP resale
        AllocationOverlay("200", pct_266=Decimal("0"), pct_263a_acq=Decimal("0"),
                          pct_263A=Decimal("75"), pct_deductible=Decimal("25")),
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
        allocations=allocations,
        section_263a=section_263a,
        section_266=Section266Election(unimproved_real_property=True),
        section_263a_elections=Section263aElection(
            de_minimis_safe_harbor=True, has_afs=True, success_fee_70_safe_harbor=True),
        small_business=SmallBusinessTest(
            tax_year=2026, avg_annual_gross_receipts=Decimal("75000000")),
    )


def main():
    inp = build_example_input()
    pipeline = CostCapitalizationPipeline()
    results = pipeline.run(inp, company_tag="Acme")

    print(f"Workbook written to: {results['_output_path']}")
    print(f"Total trial balance:   ${results['total_trial_balance']:,.2f}")
    print(f"Total capitalized:     ${results['total_capitalized']:,.2f}")
    print(f"  §266:                ${results['tagged']['266']:,.2f}")
    print(f"  §263(a):             ${results['tagged']['263(a)']:,.2f}")
    print(f"  §263A (operating):   ${results['tagged']['263A']:,.2f}")
    print(f"  Other cap:           ${results['other_cap_total']:,.2f}")
    print(f"Total deductible:      ${results['total_deductible']:,.2f}")
    u = results["unicap"]
    print(f"§263A absorption ratio: {u['absorption_ratio']:.4f}  "
          f"(add'l cap to ending inv: ${u['additional_263a_capitalized']:,.2f})")
    print(f"Small-business exempt:  {results['small_business_exempt']}")
    print("\nReconciliation (account-tag vs allocation-overlay):")
    for prov, d in results["reconciliation"].items():
        print(f"  {prov:>12}: tag ${d['account_tag']:>14,.2f}  "
              f"overlay ${d['allocation_overlay']:>14,.2f}  var ${d['variance']:>12,.2f}")


if __name__ == "__main__":
    main()
