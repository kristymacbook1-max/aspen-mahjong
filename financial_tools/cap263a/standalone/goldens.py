"""Generate goldens.json — parity vectors for the standalone HTML calculator.

Each scenario is a pure-JSON input spec (the SAME spec test_parity.js and the
in-browser self-test feed to engines.js) plus the Python engines' serialized
output. Comparison is numeric-exact (Decimal string round-trip) plus
warning-prefix multisets — see test_parity.js.

Run from the repo root:  python financial_tools/cap263a/standalone/goldens.py
"""

import json
import os
import sys
from dataclasses import asdict, is_dataclass
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from financial_tools.cap263a import analysis
from financial_tools.cap263a.analysis import (BUCKETS, CAPITALIZED_BUCKETS,
                                              EntityProfile, bucket_of,
                                              compute_unicap)
from financial_tools.cap263a.engines.intangibles import (compute_263a4_5,
                                                         route_demolition)
from financial_tools.cap263a.engines.interest import compute_263af
from financial_tools.cap263a.engines.inventory import \
    compute_lifo_decrement_release
from financial_tools.cap263a.engines.purchase_price_allocation import \
    compute_1060_allocation
from financial_tools.cap263a.engines.qualified_expenditures import compute_59e
from financial_tools.cap263a.engines.re_capitalization import compute_174
from financial_tools.cap263a.engines.sca import compute_sca
from financial_tools.cap263a.engines.tangible_263a import (
    TangibleExpenditure, compute_tangible_263a)
from financial_tools.cap263a.engines.tax_basis_tb import compute_tax_basis_tb
from financial_tools.cap263a.model import (AmortizableItem, BookTaxDifference,
                                           CIPProject, CIPSnapshot,
                                           Classification, CostPool,
                                           DebtInstrument, IntangibleItem,
                                           PurchasePriceAllocation,
                                           QualifiedExpenditureElection,
                                           REExpenditure, SelfConstructedAsset,
                                           StartupOrgCostPool, TBLine,
                                           TransactionCostItem)

_NON_IS_TIERS = {"Balance Sheet", "Revenue"}


def _d(v):
    return Decimal(str(v)) if v is not None else Decimal("0")


def _date(s):
    return date.fromisoformat(s) if s else None


def serialize(obj):
    """Decimal -> str, date -> iso, dataclass -> dict, recursively."""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, date):
        return obj.isoformat()
    if is_dataclass(obj) and not isinstance(obj, type):
        d = asdict(obj)
        if isinstance(obj, AmortizableItem):
            d["first_year_amortization"] = str(obj.first_year_amortization())
        return serialize(d)
    if isinstance(obj, dict):
        return {str(k): serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [serialize(x) for x in obj]
    return obj


# --------------------------------------------------------------------------
# analyze() with MANUALLY-ASSIGNED classifications — mirrors analysis.analyze
# line-for-line but skips the keyword classifier (the standalone HTML has no
# taxonomy; the analyst assigns tiers, which is analyze()'s downstream shape).
# --------------------------------------------------------------------------
def analyze_assigned(rows_spec, profile):
    totals = {b: Decimal("0") for b in BUCKETS}
    is_total = Decimal("0")
    rows = []
    btd_warnings = []
    for spec in rows_spec:
        ln = TBLine(acct_num=spec.get("acct_num", ""),
                    acct_desc=spec.get("acct_desc", ""),
                    cc_num=spec.get("cc_num", ""), cc_desc=spec.get("cc_desc", ""),
                    amount=_d(spec.get("amount")))
        cl = Classification(code=spec.get("code", ""),
                            tier1=spec.get("tier1", "Excluded"),
                            cap_vs_deduct=spec.get("cap_vs_deduct"),
                            is_labor=bool(spec.get("is_labor")))
        is_is = cl.tier1 not in _NON_IS_TIERS
        ln.statement_type = "IS" if is_is else "BS"
        bucket = bucket_of(cl, profile) if is_is else ""
        if ln.acct_desc.startswith("[BTD]"):
            if is_is and bucket != "Deductible":
                btd_warnings.append(
                    f"UNMATCHED-BTD-HELD-DEDUCTIBLE: {ln.acct_desc!r} "
                    f"(${ln.amount:,.0f}) would have classified into "
                    f"{bucket!r} on keywords alone — held in Deductible "
                    f"pending the account mapping fix; do not leave "
                    f"unmatched BTDs in a filing workpaper.")
            bucket = "Deductible" if is_is else ""
            if "REVIEW" not in cl.flags:
                cl.flags.append("REVIEW")
        if is_is:
            totals[bucket] += ln.amount
            is_total += ln.amount
        rows.append(analysis.ClassifiedLine(ln, cl, bucket, is_is))

    capitalized = sum((totals[b] for b in CAPITALIZED_BUCKETS), Decimal("0"))
    mixed = totals["Mixed (allocable)"]
    deductible = totals["Deductible"] + totals["Non-Operating"]
    bucket_warnings = list(btd_warnings)
    for b in CAPITALIZED_BUCKETS:
        if totals[b] < 0:
            bucket_warnings.append(
                f"NEGATIVE '{b}' BUCKET (${totals[b]:,.0f}): capitalization cannot be "
                f"negative — contra/reversal lines classified here need review.")
    if capitalized < 0:
        bucket_warnings.append(
            f"TOTAL CAPITALIZED IS NEGATIVE (${capitalized:,.0f}) — the workbook would "
            f"show a negative addition to basis. Review the contributing lines.")
    result = {"profile": profile, "rows": rows, "bucket_totals": totals,
              "is_total": is_total, "capitalized_total": capitalized,
              "mixed_total": mixed, "deductible_total": deductible,
              "bucket_warnings": bucket_warnings,
              "tie_check": is_total - (capitalized + mixed + deductible)}
    result["unicap"] = compute_unicap(result, profile)
    return result


def run_unicap(inp):
    # EntityProfile.__post_init__ coerces string dollar/ratio inputs itself.
    profile = EntityProfile(**inp.get("profile", {}))
    r = analyze_assigned(inp.get("rows", []), profile)
    return {"bucket_totals": r["bucket_totals"], "is_total": r["is_total"],
            "capitalized_total": r["capitalized_total"],
            "mixed_total": r["mixed_total"],
            "deductible_total": r["deductible_total"],
            "tie_check": r["tie_check"],
            "bucket_warnings": r["bucket_warnings"], "unicap": r["unicap"]}


def run_lifo_decrement(inp):
    layers = [dict(l, layer_471=_d(l["layer_471"]),
                   layer_additional_263a=_d(l["layer_additional_263a"]))
              for l in inp["layers"]]
    return compute_lifo_decrement_release(layers, _d(inp["decrement"]))


def run_interest(inp):
    projects = []
    for p in inp.get("projects", []):
        projects.append(CIPProject(
            project_id=p.get("project_id", ""),
            is_common_feature=bool(p.get("is_common_feature")),
            book_capitalized_interest=_d(p.get("book_capitalized_interest")),
            snapshots=[CIPSnapshot(measurement_date=_date(s.get("measurement_date")),
                                   cumulative_ape=_d(s.get("cumulative_ape")))
                       for s in p.get("snapshots", [])]))
    debts = []
    for d in inp.get("debts", []):
        debts.append(DebtInstrument(
            debt_id=d.get("debt_id", ""), description=d.get("description", ""),
            principal=_d(d.get("principal")),
            interest_incurred=_d(d.get("interest_incurred")),
            traced_to=d.get("traced_to", ""),
            outstanding_by_date={k: _d(v) for k, v in
                                 (d.get("outstanding_by_date") or {}).items()},
            related_party_below_afr=bool(d.get("related_party_below_afr")),
            non_interest_bearing=bool(d.get("non_interest_bearing")),
            personal_or_qualified_residence=bool(d.get("personal_or_qualified_residence")),
            tax_exempt_org_nonbusiness=bool(d.get("tax_exempt_org_nonbusiness")),
            disallowed_163_8T=bool(d.get("disallowed_163_8T")),
            reserve_or_deferred_tax=bool(d.get("reserve_or_deferred_tax")),
            tax_liability_453a_460b=bool(d.get("tax_liability_453a_460b")),
            sale_leaseback_purchase_money=bool(d.get("sale_leaseback_purchase_money"))))
    opts = inp.get("opts", {})
    return compute_263af(
        projects, debts,
        afr_highest=(_d(opts["afr_highest"]) if opts.get("afr_highest")
                     not in (None, "") else None),
        below_afr_interest=_d(opts.get("below_afr_interest")),
        guaranteed_payments=_d(opts.get("guaranteed_payments")))


def run_174(inp):
    exps = [REExpenditure(re_id=e.get("re_id", ""),
                          description=e.get("description", ""),
                          amount=_d(e.get("amount")),
                          domestic=bool(e.get("domestic", True)),
                          tax_year=e.get("tax_year", 0),
                          book_capitalized_amount=_d(e.get("book_capitalized_amount")))
            for e in inp.get("expenditures", [])]
    opts = inp.get("opts", {})
    return compute_174(
        exps, current_tax_year=opts.get("current_tax_year", 2026),
        domestic_capitalization_election=bool(opts.get("domestic_capitalization_election")),
        elected_period_months=opts.get("elected_period_months", 60),
        catchup_method=opts.get("catchup_method"),
        remaining_2022_2024_basis=_d(opts.get("remaining_2022_2024_basis")),
        small_business_retroactive=bool(opts.get("small_business_retroactive")),
        disposal_events=opts.get("disposal_events"))


def run_intangibles(inp):
    tcs = [TransactionCostItem(
        item_id=t.get("item_id", ""), transaction_id=t.get("transaction_id", ""),
        description=t.get("description", ""), amount=_d(t.get("amount")),
        covered_transaction=bool(t.get("covered_transaction")),
        inherently_facilitative=bool(t.get("inherently_facilitative")),
        incurred_date=_date(t.get("incurred_date")),
        bright_line_date=_date(t.get("bright_line_date")),
        success_based=bool(t.get("success_based")),
        transaction_abandoned=bool(t.get("transaction_abandoned")))
        for t in inp.get("transaction_costs", [])]
    its = [IntangibleItem(
        item_id=i.get("item_id", ""), description=i.get("description", ""),
        amount=_d(i.get("amount")),
        acquired_with_business=bool(i.get("acquired_with_business")),
        benefit_start=_date(i.get("benefit_start")),
        benefit_end=_date(i.get("benefit_end")),
        payment_year=i.get("payment_year", 0),
        facilitative_costs=_d(i.get("facilitative_costs")),
        facilitative_commissions=_d(i.get("facilitative_commissions")),
        prior_capitalized_basis=_d(i.get("prior_capitalized_basis")))
        for i in inp.get("intangibles", [])]
    pools = [StartupOrgCostPool(
        pool_id=p.get("pool_id", ""), kind=p.get("kind", "startup"),
        total=_d(p.get("total")),
        business_commencement=_date(p.get("business_commencement")))
        for p in inp.get("startup_pools", [])]
    opts = inp.get("opts", {})
    return compute_263a4_5(
        tcs, its, pools,
        success_fee_elections=frozenset(opts.get("success_fee_elections", [])),
        current_tax_year=opts.get("current_tax_year", 2026))


def run_demolition(inp):
    return route_demolition(_d(inp.get("demolition_cost")),
                            _d(inp.get("remaining_structure_basis")),
                            casualty=bool(inp.get("casualty")))


def run_59e(inp):
    els = [QualifiedExpenditureElection(
        item_id=e.get("item_id", ""), category=e.get("category", ""),
        amount=_d(e.get("amount")), elected=bool(e.get("elected")),
        election_year=e.get("election_year", 0))
        for e in inp.get("elections", [])]
    opts = inp.get("opts", {})
    return compute_59e(els, entity_type=opts.get("entity_type", "c_corp"),
                       individual_amt_exposure=bool(opts.get("individual_amt_exposure")),
                       overlapping_174A_items=frozenset(
                           opts.get("overlapping_174A_items", [])))


def run_1060(inp):
    ppa = PurchasePriceAllocation(
        transaction_id=inp.get("transaction_id", ""),
        aggregate_consideration=_d(inp.get("aggregate_consideration")),
        class_fmv={k: _d(v) for k, v in (inp.get("class_fmv") or {}).items()})
    return compute_1060_allocation(ppa)


def run_sca(inp):
    pools = [CostPool(pool_id=p.get("pool_id", ""),
                      description=p.get("description", ""),
                      amount=_d(p.get("amount")), driver=p.get("driver", ""),
                      is_mixed_service=bool(p.get("is_mixed_service")),
                      targets={k: _d(v) for k, v in (p.get("targets") or {}).items()})
             for p in inp.get("pools", [])]
    assets = [SelfConstructedAsset(asset_id=a.get("asset_id", ""),
                                   description=a.get("description", ""),
                                   book_cost=_d(a.get("book_cost")),
                                   sscm_eligible=bool(a.get("sscm_eligible")))
              for a in inp.get("assets", [])]
    return compute_sca(pools, assets, _d(inp.get("sscm_ratio")),
                       book_capitalized_indirect={
                           k: _d(v) for k, v in
                           (inp.get("book_capitalized_indirect") or {}).items()})


def run_taxtb(inp):
    lines = [TBLine(acct_num=l.get("acct_num", ""), acct_desc=l.get("acct_desc", ""),
                    cc_num=l.get("cc_num", ""), cc_desc=l.get("cc_desc", ""),
                    amount=_d(l.get("amount")))
             for l in inp.get("tb_lines", [])]
    btds = [BookTaxDifference(btd_id=b.get("btd_id", ""),
                              acct_num=b.get("acct_num", ""),
                              cc_num=b.get("cc_num", ""),
                              description=b.get("description", ""),
                              adjustment=_d(b.get("adjustment")))
            for b in inp.get("btds", [])]
    out = compute_tax_basis_tb(lines, btds)
    return {"tax_lines": [{"acct_num": l.acct_num, "acct_desc": l.acct_desc,
                           "cc_num": l.cc_num, "amount": l.amount}
                          for l in out["tax_lines"]],
            "m1_reconciliation": out["m1_reconciliation"],
            "cc_rollup": out["cc_rollup"], "warnings": out["warnings"]}


def run_tangible(inp):
    profile = EntityProfile(**inp.get("profile", {}))
    items = [TangibleExpenditure(
        item_id=i.get("item_id", ""), description=i.get("description", ""),
        amount=_d(i.get("amount")),
        invoice_or_item_cost=(None if i.get("invoice_or_item_cost") is None
                              else _d(i.get("invoice_or_item_cost"))),
        unit_of_property=i.get("unit_of_property", ""),
        is_building=bool(i.get("is_building")),
        building_unadjusted_basis=_d(i.get("building_unadjusted_basis")),
        is_material_or_supply=bool(i.get("is_material_or_supply")),
        ms_unit_cost_200_or_less=i.get("ms_unit_cost_200_or_less"),
        ms_economic_life_12mo_or_less=i.get("ms_economic_life_12mo_or_less"),
        routine_maintenance_expected_more_than_once=i.get(
            "routine_maintenance_expected_more_than_once"),
        betterment=i.get("betterment"), adaptation=i.get("adaptation"),
        restoration=i.get("restoration"),
        book_capitalized=bool(i.get("book_capitalized")))
        for i in inp.get("items", [])]
    opts = inp.get("opts", {})
    tbrmi = opts.get("total_building_repairs_maintenance_improvements")
    return compute_tangible_263a(
        items, profile,
        de_minimis_election=bool(opts.get("de_minimis_election")),
        small_taxpayer_building_election=bool(
            opts.get("small_taxpayer_building_election")),
        capitalize_repairs_following_books=bool(
            opts.get("capitalize_repairs_following_books")),
        total_building_repairs_maintenance_improvements=(
            {k: _d(v) for k, v in tbrmi.items()} if tbrmi else None))


RUNNERS = {"unicap": run_unicap, "lifo_decrement": run_lifo_decrement,
           "interest": run_interest, "s174": run_174,
           "intangibles": run_intangibles, "demolition": run_demolition,
           "s59e": run_59e, "s1060": run_1060, "sca": run_sca,
           "taxtb": run_taxtb, "tangible": run_tangible}


# --------------------------------------------------------------------------
# Scenario specs (pure JSON — shared verbatim with the JS side)
# --------------------------------------------------------------------------
def L(amount, tier1, **kw):
    return dict(amount=amount, tier1=tier1, **kw)


TAXPAYER_P = {  # §1.263A-2(c)(3)(vi) Example 1 facts
    "avg_gross_receipts": "75000000", "method": "MSPM",
    "pre_production_471": "2500000", "production_471": "7500000",
    "pre_production_additional_263A": "200000",
    "production_additional_263A": "800000",
    "pre_production_471_on_hand": "1000000",
    "production_471_on_hand": "2000000",
    "beginning_DM_not_yet_in_production": "400000",
    "ending_DM_not_yet_in_production": "800000",
    "DM_purchased_during_year": "1900000",
}

SPM_ROWS = [
    L("1000000", "§471 Cost", is_labor=True, acct_desc="Direct labor"),
    L("500000", "§471 Cost", acct_desc="Direct materials"),
    L("300000", "Additional §263A", is_labor=True, acct_desc="Purchasing salaries"),
    L("400000", "Mixed Service", is_labor=True, acct_desc="HR - plant"),
    L("200000", "Excluded", acct_desc="Advertising"),
    L("600000", "Excluded", is_labor=True, acct_desc="Sales commissions"),
]

SCENARIOS = [
    # ---------------- UNICAP: SPM ----------------
    {"name": "spm_basic", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "75000000", "method": "SPM",
                           "ending_inventory_471": "200000"},
               "rows": SPM_ROWS}},
    {"name": "spm_exempt_small_business", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "1000000"},
               "rows": SPM_ROWS}},
    {"name": "spm_exempt_tax_shelter_not_exempt", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "1000000", "is_tax_shelter": True,
                           "ending_inventory_471": "100000"},
               "rows": SPM_ROWS}},
    {"name": "spm_200k_de_minimis", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "75000000",
                           "producer_de_minimis_200k": True,
                           "ending_inventory_471": "500000"},
               "rows": SPM_ROWS}},
    {"name": "spm_warnings_absorption_estimate_method", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "75000000", "method": "FACTS",
                           "tax_year": 2027, "ending_inventory_471": "900000"},
               "rows": [L("100000", "§471 Cost", is_labor=True),
                        L("500000", "Additional §263A")]}},
    {"name": "spm_negative_pool_large_producer", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "60000000",
                           "ending_inventory_471": "100000"},
               "rows": [L("1000000", "§471 Cost", is_labor=True),
                        L("-500000", "Additional §263A")]}},
    {"name": "spm_btd_forced_deductible", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "75000000"},
               "rows": [L("1000000", "§471 Cost", is_labor=True),
                        L("250000", "§471 Cost", acct_desc="[BTD] deferred rent")]}},
    {"name": "negative_266_bucket", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "75000000"},
               "rows": [L("100000", "§471 Cost"),
                        L("-500000", "§266 Carrying Charges")]}},
    {"name": "tangible_cap_vs_deduct_branches", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "75000000"},
               "rows": [L("100", "§263(a) Tangible", cap_vs_deduct="capitalize"),
                        L("200", "§263(a) Tangible", cap_vs_deduct="elective"),
                        L("400", "§263(a) Tangible"),
                        L("800", "§263(a) Transaction/Intangible"),
                        L("1600", "§263A(f) Interest"),
                        L("3200", "Non-Operating"),
                        L("6400", "Balance Sheet"),
                        L("12800", "Revenue")]}},
    # ---------------- SSCM variants ----------------
    {"name": "sscm_production_cost_ratio", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "75000000",
                           "sscm_ratio_method": "production_cost",
                           "acquires_for_resale": False,
                           "ending_inventory_471": "100000"},
               "rows": [L("1000000", "§471 Cost", is_labor=True),
                        L("300000", "Additional §263A"),
                        L("200000", "Excluded"),
                        L("400000", "Mixed Service", is_labor=True),
                        L("100000", "Non-Operating", code="NO-INCTAX")]}},
    {"name": "sscm_production_cost_reseller_fallback", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "75000000",
                           "sscm_ratio_method": "production_cost",
                           "produces": False, "acquires_for_resale": True},
               "rows": [L("100000", "§471 Cost", is_labor=True),
                        L("50000", "Mixed Service", is_labor=True)]}},
    {"name": "sscm_override_out_of_range", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "75000000",
                           "mixed_alloc_ratio": "1.5"},
               "rows": [L("100000", "§471 Cost", is_labor=True),
                        L("50000", "Mixed Service")]}},
    {"name": "msc_90_10_not_implemented", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "75000000",
                           "msc_90_10_election": True},
               "rows": [L("100000", "§471 Cost", is_labor=True),
                        L("50000", "Mixed Service", is_labor=True),
                        L("50000", "Excluded", is_labor=True)]}},
    # ---------------- MSPM ----------------
    {"name": "mspm_example1_nonlifo", "engine": "unicap",
     "input": {"profile": TAXPAYER_P, "rows": []}},
    {"name": "mspm_lifo_example3_combined_ratio", "engine": "unicap",
     "input": {"profile": {**TAXPAYER_P, "inventory_method": "lifo_dollar_value",
                           "lifo_current_year_increment_471": "1500000"},
               "rows": []}},
    {"name": "mspm_lifo_increment_missing", "engine": "unicap",
     "input": {"profile": {**TAXPAYER_P, "inventory_method": "lifo_dollar_value"},
               "rows": []}},
    {"name": "mspm_lifo_decrement_flagged", "engine": "unicap",
     "input": {"profile": {**TAXPAYER_P, "inventory_method": "lifo_dollar_value",
                           "lifo_current_year_increment_471": "-100000"},
               "rows": []}},
    {"name": "mspm_har_frozen", "engine": "unicap",
     "input": {"profile": {**TAXPAYER_P, "har_election": True,
                           "har_preprod_ratio": "0.09",
                           "har_production_ratio": "0.11",
                           "har_qualifying_year_index": 2},
               "rows": []}},
    {"name": "mspm_har_missing_ratios", "engine": "unicap",
     "input": {"profile": {**TAXPAYER_P, "har_election": True}, "rows": []}},
    {"name": "mspm_har_recomputation_pass", "engine": "unicap",
     "input": {"profile": {**TAXPAYER_P, "har_election": True,
                           "har_qualifying_year_index": 6,
                           "har_preprod_ratio": "0.0790",
                           "har_production_ratio": "0.1050"},
               "rows": []}},
    {"name": "mspm_har_recomputation_fail", "engine": "unicap",
     "input": {"profile": {**TAXPAYER_P, "har_election": True,
                           "har_qualifying_year_index": 6,
                           "har_preprod_ratio": "0.0730",
                           "har_production_ratio": "0.1050"},
               "rows": []}},
    {"name": "mspm_har_lifo_combined", "engine": "unicap",
     "input": {"profile": {**TAXPAYER_P, "inventory_method": "lifo_dollar_value",
                           "lifo_current_year_increment_471": "1500000",
                           "har_election": True, "har_combined_ratio": "0.0950"},
               "rows": []}},
    {"name": "mspm_200k_bars_har", "engine": "unicap",
     "input": {"profile": {**TAXPAYER_P, "producer_de_minimis_200k": True,
                           "har_election": True},
               "rows": [L("50000", "Mixed Service", is_labor=True),
                        L("10000", "Excluded")]}},
    {"name": "mspm_mixed_split_direct_material", "engine": "unicap",
     "input": {"profile": TAXPAYER_P,
               "rows": [L("500000", "§471 Cost", is_labor=True),
                        L("100000", "Mixed Service", is_labor=True)]}},
    {"name": "mspm_labor_split", "engine": "unicap",
     "input": {"profile": {**TAXPAYER_P, "mspm_mixed_split_method": "labor",
                           "mspm_labor_split_proportion": "0.3"},
               "rows": [L("500000", "§471 Cost", is_labor=True),
                        L("100000", "Mixed Service", is_labor=True)]}},
    {"name": "mspm_labor_split_missing_falls_back", "engine": "unicap",
     "input": {"profile": {**TAXPAYER_P, "mspm_mixed_split_method": "labor"},
               "rows": [L("500000", "§471 Cost", is_labor=True),
                        L("100000", "Mixed Service", is_labor=True)]}},
    {"name": "mspm_90pct_split_election", "engine": "unicap",
     "input": {"profile": {**TAXPAYER_P, "mspm_90pct_split_election": True,
                           "mspm_mixed_split_method": "labor",
                           "mspm_labor_split_proportion": "0.95"},
               "rows": [L("500000", "§471 Cost", is_labor=True),
                        L("100000", "Mixed Service", is_labor=True)]}},
    {"name": "mspm_negative_dm_denominator", "engine": "unicap",
     "input": {"profile": {**TAXPAYER_P, "production_471": "100000",
                           "ending_DM_not_yet_in_production": "3000000"},
               "rows": []}},
    {"name": "mspm_negative_on_hand_floored", "engine": "unicap",
     "input": {"profile": {**TAXPAYER_P, "pre_production_471_on_hand": "-50000"},
               "rows": []}},
    {"name": "mspm_zero_denominators", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "75000000", "method": "MSPM",
                           "pre_production_additional_263A": "10000"},
               "rows": []}},
    # ---------------- SRM ----------------
    {"name": "srm_basic_reseller", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "75000000", "method": "SRM",
                           "produces": False, "acquires_for_resale": True,
                           "purchasing_costs": "300000",
                           "current_year_471_costs": "2000000",
                           "storage_handling_costs": "150000",
                           "beginning_inventory_471": "500000",
                           "ending_inventory_471": "400000"},
               "rows": [L("300000", "Additional §263A", is_labor=True,
                          acct_desc="Purchasing salaries"),
                        L("200000", "Excluded")]}},
    {"name": "srm_variation_a", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "75000000", "method": "SRM",
                           "produces": False, "acquires_for_resale": True,
                           "purchasing_costs": "300000",
                           "current_year_471_costs": "2000000",
                           "storage_handling_costs": "150000",
                           "beginning_inventory_471": "500000",
                           "ending_inventory_471": "400000",
                           "srm_variation_a": True},
               "rows": []}},
    {"name": "srm_variation_b", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "75000000", "method": "SRM",
                           "produces": False, "acquires_for_resale": True,
                           "inventory_method": "lifo_dollar_value",
                           "purchasing_costs": "300000",
                           "current_year_471_costs": "2000000",
                           "storage_handling_costs": "150000",
                           "beginning_inventory_471": "500000",
                           "ending_inventory_471": "400000",
                           "srm_variation_b": True,
                           "ending_inventory_471_total_lifo": "1800000"},
               "rows": []}},
    {"name": "srm_variation_b_missing_input", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "75000000", "method": "SRM",
                           "produces": False, "acquires_for_resale": True,
                           "purchasing_costs": "300000",
                           "current_year_471_costs": "2000000",
                           "storage_handling_costs": "150000",
                           "beginning_inventory_471": "500000",
                           "ending_inventory_471": "400000",
                           "srm_variation_b": True},
               "rows": []}},
    {"name": "srm_variations_a_plus_b", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "75000000", "method": "SRM",
                           "produces": False, "acquires_for_resale": True,
                           "purchasing_costs": "300000",
                           "current_year_471_costs": "2000000",
                           "storage_handling_costs": "150000",
                           "beginning_inventory_471": "500000",
                           "ending_inventory_471": "400000",
                           "srm_variation_a": True, "srm_variation_b": True,
                           "ending_inventory_471_total_lifo": "1800000"},
               "rows": []}},
    {"name": "srm_method_conflict_producer", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "75000000", "method": "SRM",
                           "produces": True,
                           "production_activity_level": "more_than_de_minimis",
                           "purchasing_costs": "100000",
                           "current_year_471_costs": "1000000",
                           "ending_inventory_471": "200000"},
               "rows": []}},
    {"name": "srm_de_minimis_not_incident", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "75000000", "method": "SRM",
                           "produces": True,
                           "production_activity_level": "de_minimis",
                           "production_incident_to_resale": False,
                           "current_year_471_costs": "1000000",
                           "ending_inventory_471": "200000"},
               "rows": []}},
    {"name": "srm_production_level_unknown_and_msc_contract", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "75000000", "method": "SRM",
                           "produces": True,
                           "current_year_471_costs": "1000000",
                           "ending_inventory_471": "200000"},
               "rows": [L("80000", "Mixed Service", is_labor=True)]}},
    {"name": "srm_private_label", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "75000000", "method": "SRM",
                           "produces": True, "private_label_goods": True,
                           "current_year_471_costs": "1000000",
                           "purchasing_costs": "50000",
                           "ending_inventory_471": "200000"},
               "rows": []}},
    {"name": "srm_negative_pools_and_inventory", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "75000000", "method": "SRM",
                           "produces": False, "acquires_for_resale": True,
                           "purchasing_costs": "-50000",
                           "current_year_471_costs": "1000000",
                           "storage_handling_costs": "-20000",
                           "ending_inventory_471": "-300"},
               "rows": []}},
    {"name": "srm_zero_denominators", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "75000000", "method": "SRM",
                           "produces": False, "acquires_for_resale": True,
                           "purchasing_costs": "10000",
                           "storage_handling_costs": "5000",
                           "srm_variation_a": True},
               "rows": []}},
    # ---------------- LIFO decrement ----------------
    {"name": "lifo_decrement_release", "engine": "lifo_decrement",
     "input": {"layers": [{"year": 2024, "layer_471": "100000",
                           "layer_additional_263a": "8000"},
                          {"year": 2025, "layer_471": "200000",
                           "layer_additional_263a": "25000"}],
               "decrement": "250000"}},
    {"name": "lifo_decrement_exceeds_layers", "engine": "lifo_decrement",
     "input": {"layers": [{"year": 2024, "layer_471": "100000",
                           "layer_additional_263a": "8000"},
                          {"year": 2025, "layer_471": "200000",
                           "layer_additional_263a": "25000"}],
               "decrement": "400000"}},
    {"name": "lifo_decrement_invalid_layer", "engine": "lifo_decrement",
     "input": {"layers": [{"year": 2024, "layer_471": "0",
                           "layer_additional_263a": "8000"},
                          {"year": 2025, "layer_471": "200000",
                           "layer_additional_263a": "25000"}],
               "decrement": "250000"}},
    # ---------------- §263A(f) interest ----------------
    {"name": "interest_debt_screens", "engine": "interest",
     "input": {"projects": [{"project_id": "U",
                             "snapshots": [{"measurement_date": "2026-03-31",
                                            "cumulative_ape": "1000000"}]}],
               "debts": [
                   {"debt_id": "DTL", "principal": "100", "interest_incurred": "5",
                    "reserve_or_deferred_tax": True},
                   {"debt_id": "453A", "principal": "100", "interest_incurred": "5",
                    "tax_liability_453a_460b": True},
                   {"debt_id": "SLB", "principal": "100", "interest_incurred": "5",
                    "sale_leaseback_purchase_money": True},
                   {"debt_id": "RP", "principal": "100", "interest_incurred": "5",
                    "related_party_below_afr": True},
                   {"debt_id": "AP", "principal": "100", "interest_incurred": "0",
                    "non_interest_bearing": True},
                   {"debt_id": "OK", "principal": "1000000",
                    "interest_incurred": "50000"}],
               "opts": {}}},
    {"name": "interest_traced_and_excess_quarterly", "engine": "interest",
     "input": {"projects": [
         {"project_id": "PLANT", "book_capitalized_interest": "10000",
          "snapshots": [
              {"measurement_date": "2026-03-31", "cumulative_ape": "1000000"},
              {"measurement_date": "2026-06-30", "cumulative_ape": "1600000"},
              {"measurement_date": "2026-09-30", "cumulative_ape": "2200000"},
              {"measurement_date": "2026-12-31", "cumulative_ape": "3000000"}]}],
         "debts": [
             {"debt_id": "TR1", "principal": "800000", "interest_incurred": "48000",
              "traced_to": "PLANT",
              "outstanding_by_date": {"2026-03-31": "600000", "06/30/2026": "800000",
                                      "2026/09/30": "800000", "12-31-2026": "800000"}},
             {"debt_id": "NT1", "principal": "2800000",
              "interest_incurred": "200000"}],
         "opts": {"below_afr_interest": "0", "guaranteed_payments": "0"}}},
    {"name": "interest_proration_and_consumption", "engine": "interest",
     "input": {"projects": [
         {"project_id": "A", "snapshots": [
             {"measurement_date": "2026-06-30", "cumulative_ape": "4000000"},
             {"measurement_date": "2026-12-31", "cumulative_ape": "6000000"}]},
         {"project_id": "B", "snapshots": [
             {"measurement_date": "2026-06-30", "cumulative_ape": "2000000"},
             {"measurement_date": "2026-12-31", "cumulative_ape": "2000000"}]}],
         "debts": [{"debt_id": "NT", "principal": "1000000",
                    "interest_incurred": "120000"}],
         "opts": {"below_afr_interest": "30000", "guaranteed_payments": "20000"}}},
    {"name": "interest_afr_fallback", "engine": "interest",
     "input": {"projects": [{"project_id": "U", "snapshots": [
         {"measurement_date": "2026-12-31", "cumulative_ape": "500000"}]}],
         "debts": [{"debt_id": "TR", "principal": "200000",
                    "interest_incurred": "12000", "traced_to": "U"}],
         "opts": {"afr_highest": "0.06"}}},
    {"name": "interest_wair_unavailable", "engine": "interest",
     "input": {"projects": [{"project_id": "U", "snapshots": [
         {"measurement_date": "2026-12-31", "cumulative_ape": "500000"}]}],
         "debts": [], "opts": {}}},
    {"name": "interest_wair_data_inconsistent", "engine": "interest",
     "input": {"projects": [{"project_id": "U", "snapshots": [
         {"measurement_date": "2026-06-30", "cumulative_ape": "500000"},
         {"measurement_date": "2026-12-31", "cumulative_ape": "700000"}]}],
         "debts": [{"debt_id": "NT", "principal": "0", "interest_incurred": "9000",
                    "outstanding_by_date": {"2026-06-30": "0",
                                            "2026-12-31": "0"}}],
         "opts": {}}},
    {"name": "interest_mixed_grid_no_padding", "engine": "interest",
     "input": {"projects": [
         {"project_id": "M", "snapshots": [
             {"measurement_date": "2026-03-31", "cumulative_ape": "100000"},
             {"measurement_date": "2026-04-30", "cumulative_ape": "200000"}]},
         {"project_id": "Q", "snapshots": [
             {"measurement_date": "2026-06-30", "cumulative_ape": "400000"},
             {"measurement_date": "2026-12-31", "cumulative_ape": "400000"}]}],
         "debts": [{"debt_id": "NT", "principal": "1000000",
                    "interest_incurred": "50000"}],
         "opts": {}}},
    {"name": "interest_partial_period_unit", "engine": "interest",
     "input": {"projects": [
         {"project_id": "FULL", "snapshots": [
             {"measurement_date": "2026-03-31", "cumulative_ape": "400000"},
             {"measurement_date": "2026-06-30", "cumulative_ape": "400000"},
             {"measurement_date": "2026-09-30", "cumulative_ape": "400000"},
             {"measurement_date": "2026-12-31", "cumulative_ape": "400000"}]},
         {"project_id": "PART", "snapshots": [
             {"measurement_date": "2026-09-30", "cumulative_ape": "800000"},
             {"measurement_date": "2026-12-31", "cumulative_ape": "800000"}]}],
         "debts": [{"debt_id": "NT", "principal": "5000000",
                    "interest_incurred": "250000"}],
         "opts": {}}},
    {"name": "interest_edge_warnings", "engine": "interest",
     "input": {"projects": [
         {"project_id": "CF", "is_common_feature": True,
          "book_capitalized_interest": "99999",
          "snapshots": [
              {"measurement_date": "2026-06-30", "cumulative_ape": "-100"},
              {"measurement_date": "2026-06-30", "cumulative_ape": "50000"},
              {"measurement_date": "2026-12-31", "cumulative_ape": "60000"}]},
         {"project_id": "ND", "snapshots": []}],
         "debts": [
             {"debt_id": "NEG", "principal": "100000", "interest_incurred": "-500"},
             {"debt_id": "GHOST", "principal": "100000", "interest_incurred": "5000",
              "traced_to": "NOWHERE"},
             {"debt_id": "MISS", "principal": "400000", "interest_incurred": "20000",
              "outstanding_by_date": {"2026-06-30": "400000"}}],
         "opts": {}}},
    # ---------------- §174 ----------------
    {"name": "s174_mixed_portfolio", "engine": "s174",
     "input": {"expenditures": [
         {"re_id": "F1", "description": "Foreign lab", "amount": "900000",
          "domestic": False, "tax_year": 2026,
          "book_capitalized_amount": "200000"},
         {"re_id": "D1", "description": "US software", "amount": "600000",
          "domestic": True, "book_capitalized_amount": "50000"},
         {"re_id": "D2", "description": "US bench", "amount": "150000",
          "domestic": True}],
         "opts": {"current_tax_year": 2026}}},
    {"name": "s174_domestic_election_floored_disposals", "engine": "s174",
     "input": {"expenditures": [
         {"re_id": "F1", "description": "Foreign lab", "amount": "500000",
          "domestic": False, "tax_year": 2025},
         {"re_id": "D1", "description": "US software", "amount": "300000",
          "domestic": True},
         {"re_id": "D2", "description": "US expensed prior law", "amount": "100000",
          "domestic": True}],
         "opts": {"domestic_capitalization_election": True,
                  "elected_period_months": 48,
                  "disposal_events": ["F1", "D1", "ZZZ"]}}},
    {"name": "s174_catchup_one_year", "engine": "s174",
     "input": {"expenditures": [],
               "opts": {"catchup_method": "one_year",
                        "remaining_2022_2024_basis": "240000"}}},
    {"name": "s174_catchup_two_year_odd_cent", "engine": "s174",
     "input": {"expenditures": [],
               "opts": {"catchup_method": "two_year",
                        "remaining_2022_2024_basis": "1000.01"}}},
    {"name": "s174_retroactive_conflict", "engine": "s174",
     "input": {"expenditures": [],
               "opts": {"catchup_method": "one_year",
                        "remaining_2022_2024_basis": "240000",
                        "small_business_retroactive": True}}},
    {"name": "s174_catchup_unknown_method", "engine": "s174",
     "input": {"expenditures": [],
               "opts": {"catchup_method": "lump", "remaining_2022_2024_basis": "1"}}},
    # ---------------- §1.263(a)-4/-5 ----------------
    {"name": "intangibles_transaction_costs", "engine": "intangibles",
     "input": {"transaction_costs": [
         {"item_id": "T1", "transaction_id": "DEAL1", "description": "Success fee",
          "amount": "1000.01", "covered_transaction": True, "success_based": True},
         {"item_id": "T2", "transaction_id": "DEAL1", "description": "Fairness opinion",
          "amount": "250000", "covered_transaction": True,
          "inherently_facilitative": True},
         {"item_id": "T3", "transaction_id": "DEAL1", "description": "Market study",
          "amount": "40000", "covered_transaction": True,
          "incurred_date": "2026-01-15", "bright_line_date": "2026-03-01"},
         {"item_id": "T4", "transaction_id": "DEAL1", "description": "Diligence",
          "amount": "60000", "covered_transaction": True,
          "incurred_date": "2026-04-15", "bright_line_date": "2026-03-01"},
         {"item_id": "T5", "transaction_id": "DEAL2", "description": "Covered no dates",
          "amount": "10000", "covered_transaction": True},
         {"item_id": "T6", "transaction_id": "DEAL3", "description": "Routine legal",
          "amount": "5000"},
         {"item_id": "T7", "transaction_id": "DEAL4", "description": "Abandoned banker fee",
          "amount": "75000", "covered_transaction": True,
          "inherently_facilitative": True, "transaction_abandoned": True},
         {"item_id": "T8", "transaction_id": "DEAL5", "description": "Credit memo",
          "amount": "-2500"}],
         "intangibles": [], "startup_pools": [],
         "opts": {"success_fee_elections": ["DEAL1"]}}},
    {"name": "intangibles_12mo_cliff_197", "engine": "intangibles",
     "input": {"transaction_costs": [], "intangibles": [
         {"item_id": "I1", "description": "9-month license", "amount": "24000",
          "benefit_start": "2026-02-01", "benefit_end": "2026-10-31",
          "payment_year": 2026, "facilitative_commissions": "3000"},
         {"item_id": "I2", "description": "18-month contract", "amount": "90000",
          "benefit_start": "2026-03-01", "benefit_end": "2027-08-31",
          "payment_year": 2026, "facilitative_costs": "4000"},
         {"item_id": "I3", "description": "over-cliff facilitative", "amount": "50000",
          "benefit_start": "2026-01-01", "benefit_end": "2028-01-01",
          "payment_year": 2026, "facilitative_costs": "5001"},
         {"item_id": "I4", "description": "acquired customer list", "amount": "400000",
          "acquired_with_business": True, "prior_capitalized_basis": "100000"},
         {"item_id": "I5", "description": "indefinite franchise right",
          "amount": "80000"},
         {"item_id": "I6", "description": "sub-month benefit", "amount": "1200",
          "benefit_start": "2027-01-05", "benefit_end": "2027-01-20",
          "payment_year": 2025},
         {"item_id": "I7", "description": "reversed dates", "amount": "10",
          "benefit_start": "2026-06-01", "benefit_end": "2026-01-01"},
         {"item_id": "I8", "description": "bad payment year", "amount": "10",
          "benefit_start": "2026-01-01", "benefit_end": "2026-06-01",
          "payment_year": 26}],
         "startup_pools": [], "opts": {}}},
    {"name": "intangibles_startup_pools", "engine": "intangibles",
     "input": {"transaction_costs": [], "intangibles": [], "startup_pools": [
         {"pool_id": "S1", "kind": "startup", "total": "45000",
          "business_commencement": "2026-04-10"},
         {"pool_id": "S2", "kind": "org_corp", "total": "52000",
          "business_commencement": "2026-07-01"},
         {"pool_id": "S3", "kind": "startup", "total": "60000"},
         {"pool_id": "S4", "kind": "syndication", "total": "30000"},
         {"pool_id": "S5", "kind": "startup", "total": "-100"}],
         "opts": {}}},
    {"name": "demolition_normal", "engine": "demolition",
     "input": {"demolition_cost": "120000", "remaining_structure_basis": "480000"}},
    {"name": "demolition_casualty", "engine": "demolition",
     "input": {"demolition_cost": "120000", "remaining_structure_basis": "480000",
               "casualty": True}},
    # ---------------- §59(e) ----------------
    {"name": "s59e_c_corp_gated", "engine": "s59e",
     "input": {"elections": [{"item_id": "Q1", "category": "idc",
                              "amount": "100000", "elected": True,
                              "election_year": 2026}],
               "opts": {"entity_type": "c_corp"}}},
    {"name": "s59e_scorp_no_exposure_gated", "engine": "s59e",
     "input": {"elections": [{"item_id": "Q1", "category": "idc",
                              "amount": "100000", "elected": True,
                              "election_year": 2026}],
               "opts": {"entity_type": "s_corp"}}},
    {"name": "s59e_sole_prop_full", "engine": "s59e",
     "input": {"elections": [
         {"item_id": "Q1", "category": "circulation", "amount": "36000",
          "elected": True, "election_year": 2026},
         {"item_id": "Q2", "category": "idc", "amount": "600000",
          "elected": True, "election_year": 2026},
         {"item_id": "Q3", "category": "mining_exploration", "amount": "240000",
          "elected": True, "election_year": 2026},
         {"item_id": "Q4", "category": "re_domestic", "amount": "120000",
          "elected": True, "election_year": 2026},
         {"item_id": "Q5", "category": "bogus", "amount": "10", "elected": True,
          "election_year": 2026},
         {"item_id": "Q6", "category": "idc", "amount": "-5", "elected": True,
          "election_year": 2026},
         {"item_id": "Q7", "category": "idc", "amount": "999", "elected": False,
          "election_year": 2026}],
         "opts": {"entity_type": "sole_prop",
                  "overlapping_174A_items": ["Q4"]}}},
    # ---------------- §1060 ----------------
    {"name": "s1060_full_waterfall_residual", "engine": "s1060",
     "input": {"transaction_id": "ACQ1", "aggregate_consideration": "10000000",
               "class_fmv": {"I": "500000", "II": "1000000", "III": "750000",
                             "IV": "2000000", "V": "3000000", "VI": "1250000"}}},
    {"name": "s1060_shortfall_mid_class", "engine": "s1060",
     "input": {"transaction_id": "ACQ2", "aggregate_consideration": "3000000",
               "class_fmv": {"I": "500000", "II": "1000000", "III": "750000",
                             "IV": "2000000", "V": "3000000"}}},
    {"name": "s1060_negative_consideration", "engine": "s1060",
     "input": {"transaction_id": "ACQ3", "aggregate_consideration": "-1",
               "class_fmv": {"I": "100"}}},
    {"name": "s1060_unknown_and_negative_class", "engine": "s1060",
     "input": {"transaction_id": "ACQ4", "aggregate_consideration": "1000000",
               "class_fmv": {"I": "100000", "VII": "50000", "X": "1",
                             "III": "-200000", "IV": "300000"}}},
    # ---------------- SCA ----------------
    {"name": "sca_plain_and_mixed", "engine": "sca",
     "input": {"pools": [
         {"pool_id": "P1", "description": "Depreciation - Building",
          "amount": "90000", "driver": "square_footage",
          "targets": {"A1": "6000", "A2": "3000", "NON_PRODUCTION": "1000"}},
         {"pool_id": "P2", "description": "HR department", "amount": "60000",
          "driver": "headcount", "is_mixed_service": True,
          "targets": {"A1": "40", "A2": "40", "NON_PRODUCTION": "20"}}],
         "assets": [
             {"asset_id": "A1", "book_cost": "1000000", "sscm_eligible": True},
             {"asset_id": "A2", "book_cost": "500000", "sscm_eligible": False}],
         "sscm_ratio": "0.75"}},
    {"name": "sca_guardrails", "engine": "sca",
     "input": {"pools": [
         {"pool_id": "B1", "description": "HR payroll services", "amount": "10000",
          "driver": "machine_hours", "targets": {"A1": "10"}},
         {"pool_id": "B2", "description": "Mystery pool", "amount": "10000",
          "driver": "teleportation", "targets": {"A1": "10"}},
         {"pool_id": "B3", "description": "Facilities rent", "amount": "10000",
          "driver": "direct_labor", "targets": {"A1": "10"}},
         {"pool_id": "B4", "description": "Utilities", "amount": "-5000",
          "driver": "square_footage", "targets": {"A1": "10"}},
         {"pool_id": "B5", "description": "Utilities", "amount": "5000",
          "driver": "square_footage", "targets": {"A1": "-10", "A2": "20"}},
         {"pool_id": "B6", "description": "Utilities", "amount": "5000",
          "driver": "square_footage", "targets": {"A1": "0", "A2": "0"}},
         {"pool_id": "B7", "description": "Utilities", "amount": "5000",
          "driver": "square_footage", "targets": {"GHOST": "10", "A1": "10"}}],
         "assets": [{"asset_id": "A1", "book_cost": "100000",
                     "sscm_eligible": True},
                    {"asset_id": "A2", "book_cost": "50000",
                     "sscm_eligible": True}],
         "sscm_ratio": "1.4",
         "book_capitalized_indirect": {"A1": "12345"}}},
    {"name": "sca_penny_plug", "engine": "sca",
     "input": {"pools": [{"pool_id": "P", "description": "Utilities",
                          "amount": "100", "driver": "square_footage",
                          "targets": {"A1": "1", "A2": "1", "A3": "1"}}],
               "assets": [{"asset_id": "A1", "book_cost": "0"},
                          {"asset_id": "A2", "book_cost": "0"},
                          {"asset_id": "A3", "book_cost": "0"}],
               "sscm_ratio": "0"}},
    # ---------------- tax-basis TB ----------------
    {"name": "taxtb_matching_and_unmatched", "engine": "taxtb",
     "input": {"tb_lines": [
         {"acct_num": "5000", "acct_desc": "Direct labor", "cc_num": "100",
          "amount": "100000"},
         {"acct_num": "6000", "acct_desc": "Rent", "cc_num": "200",
          "amount": "50000"},
         {"acct_num": "6000", "acct_desc": "Rent", "cc_num": "300",
          "amount": "70000"},
         {"acct_num": "7000", "acct_desc": "Depreciation", "cc_num": "100",
          "amount": "20000"},
         {"acct_num": "7000", "acct_desc": "Depreciation", "cc_num": "100",
          "amount": "5000"}],
         "btds": [
             {"btd_id": "B1", "acct_num": "5000", "cc_num": "100",
              "description": "…", "adjustment": "-1500"},
             {"btd_id": "B2", "acct_num": "6000", "description": "multi-cc",
              "adjustment": "999"},
             {"btd_id": "B3", "acct_num": "7000", "cc_num": "100",
              "description": "dup-key target", "adjustment": "250"},
             {"btd_id": "B4", "acct_num": "9999", "description": "orphan reserve",
              "adjustment": "4321"}]}},
]


SCENARIOS += [
    # 2023's real threshold is $29M: $30M receipts must NOT be exempt (the
    # old 2026-figure fallback wrongly exempted this taxpayer — regression).
    {"name": "threshold_2023_receipts_30m_not_exempt", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "30000000", "tax_year": 2023,
                           "ending_inventory_471": "100000"},
               "rows": [L("500000", "§471 Cost", is_labor=True),
                        L("100000", "Additional §263A")]}},
    {"name": "threshold_2022_boundary_exempt", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "27000000", "tax_year": 2022},
               "rows": [L("500000", "§471 Cost", is_labor=True)]}},
    # Pre-TCJA year: the §448(c) framework did not exist — hard warning both
    # in the exempt path and the computed path.
    {"name": "threshold_pre_tcja_exempt_warns", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "5000000", "tax_year": 2017},
               "rows": [L("500000", "§471 Cost", is_labor=True)]}},
    {"name": "threshold_pre_tcja_nonexempt_warns", "engine": "unicap",
     "input": {"profile": {"avg_gross_receipts": "50000000", "tax_year": 2017,
                           "ending_inventory_471": "100000"},
               "rows": [L("500000", "§471 Cost", is_labor=True),
                        L("100000", "Additional §263A")]}},
]


def T(item_id, amount, **kw):
    d = dict(item_id=item_id, description=item_id, amount=amount)
    d.update(kw)
    return d


SCENARIOS += [
    {"name": "tangible_de_minimis_afs_ceiling", "engine": "tangible",
     "input": {"profile": {"avg_gross_receipts": "5000000", "has_afs": True},
               "items": [T("D1", "5000", invoice_or_item_cost="5000"),
                        T("D2", "5000", invoice_or_item_cost="5000.01",
                          betterment=False, adaptation=False, restoration=False,
                          routine_maintenance_expected_more_than_once=False)],
               "opts": {"de_minimis_election": True}}},
    {"name": "tangible_de_minimis_no_afs_2500", "engine": "tangible",
     "input": {"profile": {"avg_gross_receipts": "5000000", "has_afs": False},
               "items": [T("D1", "2500", invoice_or_item_cost="2500"),
                        T("D2", "2500", invoice_or_item_cost="2500.01",
                          betterment=False, adaptation=False, restoration=False,
                          routine_maintenance_expected_more_than_once=False)],
               "opts": {"de_minimis_election": True}}},
    {"name": "tangible_de_minimis_cost_unknown_open_question", "engine": "tangible",
     "input": {"profile": {"avg_gross_receipts": "5000000"},
               "items": [T("U1", "3000", description="Shop equipment")],
               "opts": {"de_minimis_election": True}}},
    {"name": "tangible_materials_supplies_both_prongs", "engine": "tangible",
     "input": {"profile": {"avg_gross_receipts": "5000000"},
               "items": [T("M1", "150", is_material_or_supply=True,
                          ms_unit_cost_200_or_less=True),
                        T("M2", "500", is_material_or_supply=True,
                          ms_economic_life_12mo_or_less=True),
                        T("M3", "300", is_material_or_supply=True,
                          betterment=False, adaptation=False, restoration=False,
                          routine_maintenance_expected_more_than_once=False)],
               "opts": {}}},
    {"name": "tangible_stsh_at_and_over_ceiling", "engine": "tangible",
     "input": {"profile": {"avg_gross_receipts": "5000000"},
               "items": [T("B1", "8000", is_building=True,
                          unit_of_property="BLDG1",
                          building_unadjusted_basis="400000"),
                        T("B2", "8000.01", is_building=True,
                          unit_of_property="BLDG2",
                          building_unadjusted_basis="400000",
                          betterment=False, adaptation=False, restoration=False,
                          routine_maintenance_expected_more_than_once=False)],
               "opts": {"small_taxpayer_building_election": True}}},
    {"name": "tangible_stsh_ineligible_receipts", "engine": "tangible",
     "input": {"profile": {"avg_gross_receipts": "15000000"},
               "items": [T("B1", "1000", is_building=True,
                          unit_of_property="BLDG1",
                          building_unadjusted_basis="400000",
                          betterment=False, adaptation=False, restoration=False,
                          routine_maintenance_expected_more_than_once=False)],
               "opts": {"small_taxpayer_building_election": True}}},
    {"name": "tangible_stsh_explicit_aggregate", "engine": "tangible",
     "input": {"profile": {"avg_gross_receipts": "5000000"},
               "items": [T("B1", "5000", is_building=True,
                          unit_of_property="BLDG1",
                          building_unadjusted_basis="1000000")],
               "opts": {"small_taxpayer_building_election": True,
                        "total_building_repairs_maintenance_improvements":
                            {"BLDG1": "9999"}}}},
    {"name": "tangible_bar_each_prong_capitalizes", "engine": "tangible",
     "input": {"profile": {"avg_gross_receipts": "5000000"},
               "items": [T("I1", "10000", betterment=True, adaptation=False,
                          restoration=False),
                        T("I2", "20000", betterment=False, adaptation=True,
                          restoration=False),
                        T("I3", "30000", betterment=False, adaptation=False,
                          restoration=True)],
               "opts": {}}},
    {"name": "tangible_bar_missing_facts_conservative", "engine": "tangible",
     "input": {"profile": {"avg_gross_receipts": "5000000"},
               "items": [T("P1", "4000", description="Roof membrane replacement",
                          betterment=None, adaptation=False, restoration=None)],
               "opts": {}}},
    {"name": "tangible_routine_maintenance", "engine": "tangible",
     "input": {"profile": {"avg_gross_receipts": "5000000"},
               "items": [T("R1", "1500", betterment=False, adaptation=False,
                          restoration=False,
                          routine_maintenance_expected_more_than_once=True),
                        T("R2", "1600", betterment=False, adaptation=False,
                          restoration=False,
                          routine_maintenance_expected_more_than_once=None)],
               "opts": {}}},
    {"name": "tangible_repair_and_n_election", "engine": "tangible",
     "input": {"profile": {"avg_gross_receipts": "5000000"},
               "items": [T("N1", "700", betterment=False, adaptation=False,
                          restoration=False,
                          routine_maintenance_expected_more_than_once=False,
                          book_capitalized=True),
                        T("N2", "800", betterment=False, adaptation=False,
                          restoration=False,
                          routine_maintenance_expected_more_than_once=False,
                          book_capitalized=False)],
               "opts": {"capitalize_repairs_following_books": True}}},
    {"name": "tangible_negative_amount", "engine": "tangible",
     "input": {"profile": {"avg_gross_receipts": "5000000"},
               "items": [T("X1", "-500")], "opts": {}}},
]


def main():
    out = []
    for sc in SCENARIOS:
        result = RUNNERS[sc["engine"]](sc["input"])
        out.append({"name": sc["name"], "engine": sc["engine"],
                    "input": sc["input"], "expected": serialize(result)})
    path = os.path.join(os.path.dirname(__file__), "goldens.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"wrote {path}: {len(out)} scenarios")


if __name__ == "__main__":
    main()
