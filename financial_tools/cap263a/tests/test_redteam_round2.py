"""Red-team round 2 regressions — every test pins a CONFIRMED bug fix
(docs/TAX_DECISIONS.md §16). Each docstring names the original failure."""

from datetime import date
from decimal import Decimal

import pytest

from financial_tools.cap263a.analysis import EntityProfile, analyze
from financial_tools.cap263a.model import (BookTaxDifference, CIPProject,
                                           CIPSnapshot, DebtInstrument,
                                           IntangibleItem, TBLine)
from financial_tools.cap263a.engines.interest import compute_263af
from financial_tools.cap263a.engines.inventory import compute_srm
from financial_tools.cap263a.engines.intangibles import compute_263a4_5
from financial_tools.cap263a.engines.qualified_expenditures import compute_59e
from financial_tools.cap263a.engines.re_capitalization import compute_174
from financial_tools.cap263a.engines.tax_basis_tb import compute_tax_basis_tb
from financial_tools.cap263a.interview import run_interview
from financial_tools.cap263a.model import REExpenditure, QualifiedExpenditureElection


def _result(mixed=Decimal("0"), deductible=Decimal("0")):
    return {"rows": [], "bucket_totals": {"Inventory §471": Decimal("0"),
                                          "§263A Additional": Decimal("0")},
            "mixed_total": mixed, "deductible_total": deductible}


def _unit(pid, apes, dates):
    return CIPProject(project_id=pid, snapshots=[
        CIPSnapshot(measurement_date=d, cumulative_ape=a)
        for d, a in zip(dates, apes)])


QDATES = [date(2026, 3, 31), date(2026, 6, 30),
          date(2026, 9, 30), date(2026, 12, 31)]


def test_partial_period_unit_averages_over_full_grid():
    """CONFIRMED 2x overstatement: a unit with snapshots on only 2 of the
    period's 4 measurement dates divided by ITS OWN count (2) instead of the
    grid's (4). [400k, 600k] over a 4-date grid must average 250,000 —
    (400k+600k+0+0)/4 per the §1.263A-9(f)(2)(iii) snapshot convention —
    not 500,000."""
    full = _unit("FULL", [Decimal("1000000")] * 4, QDATES)
    partial = _unit("PART", [Decimal("400000"), Decimal("600000")], QDATES[:2])
    nontraced = DebtInstrument(debt_id="L", principal=Decimal("10000000"),
                               interest_incurred=Decimal("1000000"))  # WAIR 10%
    out = compute_263af([full, partial], [nontraced])
    assert out["per_unit"]["PART"]["average_excess"] == Decimal("250000")
    assert out["per_unit"]["PART"]["excess_expenditure_amount"] == Decimal("25000.00")
    assert any("PARTIAL-PERIOD-UNIT" in w for w in out["warnings"])


def test_wair_inconsistent_data_refuses_instead_of_afr():
    """Nontraced interest with zero outstanding on every date fell back to
    the AFR while keeping the interest consumable — internally inconsistent.
    Must refuse with WAIR-DATA-INCONSISTENT, zero excess."""
    unit = _unit("U", [Decimal("1000000")] * 4, QDATES)
    weird = DebtInstrument(debt_id="W", principal=Decimal("0"),
                           interest_incurred=Decimal("50000"))
    out = compute_263af([unit], [weird], afr_highest=Decimal("0.05"))
    assert out["wair_source"] == "unavailable"
    assert any("WAIR-DATA-INCONSISTENT" in w for w in out["warnings"])
    assert out["total_excess"] == Decimal("0.00")


def test_srm_variation_b_splits_the_ratios():
    """CONFIRMED: variation (d)(3)(iii)(B) applies ONLY the S&H ratio to
    total ending inventory; combined×total overstated by purchasing-ratio ×
    prior-year layers. purchasing 0.03 × 500,000 + S&H 0.04375 × 800,000
    = 15,000 + 35,000 = 50,000 (not 0.07375 × 800,000 = 59,000)."""
    p = EntityProfile(avg_gross_receipts=Decimal("75000000"), method="SRM",
                      produces=False, acquires_for_resale=True,
                      purchasing_costs=Decimal("60000"),
                      current_year_471_costs=Decimal("2000000"),
                      storage_handling_costs=Decimal("105000"),
                      beginning_inventory_471=Decimal("400000"),
                      ending_inventory_471=Decimal("500000"),
                      srm_variation_b=True,
                      ending_inventory_471_total_lifo=Decimal("800000"))
    u = compute_srm(_result(), p)
    assert u["additional_capitalized_to_inventory"] == Decimal("50000.00")

    p2 = EntityProfile(avg_gross_receipts=Decimal("75000000"), method="SRM",
                       produces=False, acquires_for_resale=True,
                       purchasing_costs=Decimal("60000"),
                       current_year_471_costs=Decimal("2000000"),
                       storage_handling_costs=Decimal("105000"),
                       beginning_inventory_471=Decimal("400000"),
                       ending_inventory_471=Decimal("500000"),
                       srm_variation_b=True)   # multiplicand missing
    u2 = compute_srm(_result(), p2)
    assert any("SRM-VARIATION-B-INPUT-MISSING" in w for w in u2["warnings"])
    assert u2["additional_capitalized_to_inventory"] == Decimal("36875.00")


def test_srm_gate_incident_to_resale_and_unknown_level():
    """CONFIRMED gate holes: a de-minimis producer whose production is NOT
    incident to resale was silently blessed ((a)(4)(ii) requires incident-
    to-resale); an unknown activity level passed silently."""
    base = dict(avg_gross_receipts=Decimal("75000000"), method="SRM",
                current_year_471_costs=Decimal("1000000"),
                ending_inventory_471=Decimal("100000"))
    not_incident = EntityProfile(produces=True,
                                 production_activity_level="de_minimis",
                                 production_incident_to_resale=False, **base)
    u = compute_srm(_result(), not_incident)
    assert u["method_conflict"] is True
    assert any("(a)(4)(ii)" in w for w in u["warnings"])

    unknown = EntityProfile(produces=True, **base)
    u2 = compute_srm(_result(), unknown)
    assert any("SRM-PRODUCTION-LEVEL-UNKNOWN" in w for w in u2["warnings"])


def test_srm_mixed_not_fabricated_from_aggregate_ratio():
    """CONFIRMED: SRM published the aggregate SSCM split as mixed_capitalized
    while its own input contract says the (F) shares live inside the pool
    inputs — zeroing real deductions out of adjusted_deductible_post."""
    p = EntityProfile(avg_gross_receipts=Decimal("75000000"), method="SRM",
                      produces=False, acquires_for_resale=True,
                      current_year_471_costs=Decimal("1000000"),
                      ending_inventory_471=Decimal("100000"),
                      mixed_alloc_ratio=Decimal("1"))
    u = compute_srm(_result(mixed=Decimal("200000"),
                            deductible=Decimal("50000")), p)
    assert u["mixed_capitalized"] == Decimal("0")
    assert u["mixed_deductible"] == Decimal("200000")
    assert u["adjusted_deductible_post"] == Decimal("250000")
    assert any("SRM-MSC-INPUT-CONTRACT" in w for w in u["warnings"])


def test_interview_no_string_is_false():
    """CONFIRMED: bool("no") is True — a dictated "no" to the tax-shelter
    question set is_tax_shelter=True and switched ALL of UNICAP on for a
    $1M-receipts taxpayer."""
    res = run_interview({"Q0.1": "c_corp", "Q0.2": 2026, "Q0.3": "no",
                         "Q0.4": "1000000", "Q0.5": "false"})
    assert res.profile.is_tax_shelter is False
    assert res.profile.small_business_exempt is True


def test_interview_out_of_menu_not_applied_and_unknown_key_warns():
    """CONFIRMED: an out-of-menu enum answer flowed into the profile
    (entity_type='TOTALLY_BOGUS' reached engine gating); a typo'd answer key
    silently un-answered its question."""
    res = run_interview({"Q0.1": "TOTALLY_BOGUS", "Q0.2": 2026, "Q0.3": False,
                         "Q0.4": "1000000", "Q0.5": True, "QX.99": 1})
    assert res.profile.entity_type == "c_corp"      # dataclass default kept
    assert any("ANSWER-OUT-OF-MENU" in w for w in res.warnings)
    assert any("UNRECOGNIZED-ANSWER-KEY" in w and "QX.99" in w
               for w in res.warnings)


def test_commissions_never_shelter_in_e4_de_minimis():
    """CONFIRMED: a $4,000 commission inside the facilitative aggregate was
    deducted under the $5,000 cliff — commissions are categorically outside
    the (e)(4) de minimis and always capitalize."""
    it = IntangibleItem(item_id="I1", amount=Decimal("50000"),
                        facilitative_costs=Decimal("1000"),
                        facilitative_commissions=Decimal("4000"),
                        acquired_with_business=True)
    out = compute_263a4_5([], [it], [])
    row = out["intangible_items"][0]
    assert row["capitalized"] == Decimal("54000")   # amount + commissions
    assert row["deductible"] == Decimal("1000")     # de minimis on the rest
    assert "E4-COMMISSIONS-ALWAYS-CAPITALIZED" in row["flags"]


def test_reversed_benefit_dates_flag_not_negative_amortization():
    """CONFIRMED: benefit_end < benefit_start produced recovery_months=-17
    and NEGATIVE first-year amortization with zero warnings."""
    it = IntangibleItem(item_id="I2", amount=Decimal("120000"),
                        benefit_start=date(2026, 6, 1),
                        benefit_end=date(2025, 1, 1))
    out = compute_263a4_5([], [it], [])
    row = out["intangible_items"][0]
    assert row["treatment"] == "sme_review"
    assert not out["amortizable_items"]
    assert any("BENEFIT-DATES-REVERSED" in w for w in out["warnings"])


def test_59e_pass_through_without_exposure_is_gated():
    """CONFIRMED gate hole: an s_corp/partnership with NO stated individual
    AMT exposure was served a full §59(e) schedule."""
    els = [QualifiedExpenditureElection(item_id="Q1", category="idc",
                                        amount=Decimal("120000"),
                                        elected=True, election_year=2026)]
    out = compute_59e(els, entity_type="s_corp", individual_amt_exposure=False)
    assert out["items"] == []
    assert any("§59E-NO-AMT-EXPOSURE" in w for w in out["warnings"])


def test_catchup_retroactive_conflict_books_nothing():
    """CONFIRMED: the mutual-exclusivity warning was cosmetic — the
    conflicted catch-up dollars still landed in current_year_deduction."""
    out = compute_174([], catchup_method="one_year",
                      remaining_2022_2024_basis=Decimal("100000"),
                      small_business_retroactive=True)
    assert out["current_year_deduction"] == Decimal("0")
    assert out["catchup"]["conflicted_amount_not_deducted"] == Decimal("100000")
    assert any("MUTUALLY-EXCLUSIVE" in w for w in out["warnings"])


def test_unmatched_btd_lines_forced_deductible_with_review():
    """CONFIRMED: an unmatched '[BTD] Depreciation book-tax difference' line
    keyword-classified into the §263A Additional pool at confidence 70 and
    drove real UNICAP capitalization."""
    tb = [TBLine("5000", "Direct labor", "100", "Production",
                 amount=Decimal("500000"))]
    btds = [BookTaxDifference(acct_num="9998", description=
                              "Depreciation book-tax difference",
                              adjustment=Decimal("120000"))]
    out = compute_tax_basis_tb(tb, btds)
    r = analyze(out["tax_lines"],
                EntityProfile(avg_gross_receipts=Decimal("75000000")))
    btd_rows = [row for row in r["rows"] if row.line.acct_desc.startswith("[BTD]")]
    assert btd_rows and btd_rows[0].bucket == "Deductible"
    assert "REVIEW" in btd_rows[0].cls.flags
    assert r["bucket_totals"]["§263A Additional"] == Decimal("0")


def test_date_object_keys_in_outstanding_by_date_work():
    """CONFIRMED: date-object keys silently missed every lookup and fell back
    to principal."""
    d = DebtInstrument(debt_id="L", principal=Decimal("1000000"),
                       interest_incurred=Decimal("0"),
                       outstanding_by_date={date(2026, 6, 30): Decimal("1")})
    assert d.outstanding_by_date == {"2026-06-30": Decimal("1")}


def test_nan_and_bool_rejected_by_model():
    """CONFIRMED: a NaN amount silently poisoned every total AND defeated
    the tie-check; a bool crashed with a bare InvalidOperation."""
    with pytest.raises(ValueError, match="non-finite"):
        REExpenditure(amount="NaN")
    with pytest.raises(TypeError, match="bool"):
        REExpenditure(amount=True)


def test_foreign_string_reads_as_not_domestic():
    """CONFIRMED: a 'Domestic?' column populated 'foreign' coerced True via
    bool(str), flipping mandatory foreign capitalization into expensing."""
    from financial_tools.cap263a.readers import _to_bool
    assert _to_bool("foreign") is False
    assert _to_bool("domestic") is True
