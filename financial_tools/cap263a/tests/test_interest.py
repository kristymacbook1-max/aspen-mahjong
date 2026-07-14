"""Phase D — §263A(f) avoided-cost engine (engines/interest.py).

Golden fixture is BUILD_PLAN.md Phase D's corrected worked table (quarterly
APE 3.5M/5M/6.5M/8M, traced $3M @ 6%, nontraced pool $2.8M avg outstanding /
$200K interest), plus the (c)(7) proration branch, the (c)(5)(iii)(D) WAIR
AFR fallback, the (a)(4) eligible-debt screens, and Runtime Pipeline Step 3b
basis reconciliation. Hand arithmetic in each test's docstring."""

from datetime import date
from decimal import Decimal

from financial_tools.cap263a.model import CIPProject, CIPSnapshot, DebtInstrument
from financial_tools.cap263a.engines.interest import compute_263af


def _snap(y, m, d, ape):
    return CIPSnapshot(measurement_date=date(y, m, d),
                       cumulative_ape=Decimal(ape))


def _golden_inputs():
    """BUILD_PLAN.md Phase D corrected worked test, verbatim."""
    tower = CIPProject(
        project_id="TOWER", description="Office tower CIP",
        is_real_property=True,
        snapshots=[_snap(2025, 3, 31, "3500000"),
                   _snap(2025, 6, 30, "5000000"),
                   _snap(2025, 9, 30, "6500000"),
                   _snap(2025, 12, 31, "8000000")])
    traced = DebtInstrument(
        debt_id="TL", description="Construction loan",
        principal=Decimal("3000000"), rate=Decimal("0.06"),
        interest_incurred=Decimal("180000"), traced_to="TOWER")
    nontraced = DebtInstrument(
        debt_id="NT", description="Revolver (nontraced pool)",
        principal=Decimal("2800000"),           # average outstanding
        interest_incurred=Decimal("200000"))
    return [tower], [traced, nontraced]


def test_golden_fixture():
    """The plan's own corrected table.

    excess_d = APE_d - 3,000,000 traced at every date (APE > $3M throughout):
      Q1 500,000 / Q2 2,000,000 / Q3 3,500,000 / Q4 5,000,000
    average_excess = 11,000,000 / 4 = 2,750,000
    WAIR = 200,000 / 2,800,000 = 1/14 exactly (exact Decimal, never rounded)
    excess amount = 2,750,000 x (1/14) = 196,428.5714... -> 196,428.57
    traced interest = ACTUAL 180,000.00 (never prorated)
    total = 180,000.00 + 196,428.57 = 376,428.57
    cap: 196,428.57 <= 200,000 nontraced available -> no proration
    consumption: 196,428.57 from nontraced; 200,000 - 196,428.57 = 3,571.43
    stays ordinary deductible interest."""
    projects, debts = _golden_inputs()
    r = compute_263af(projects, debts)

    assert r["wair"] == Decimal("200000") / Decimal("2800000")
    assert r["wair_source"] == "nontraced"

    unit = r["per_unit"]["TOWER"]
    assert unit["excess_by_date"] == {
        "2025-03-31": Decimal("500000"),
        "2025-06-30": Decimal("2000000"),
        "2025-09-30": Decimal("3500000"),
        "2025-12-31": Decimal("5000000")}
    assert unit["average_excess"] == Decimal("2750000")
    assert unit["traced_interest"] == Decimal("180000.00")
    assert unit["excess_expenditure_amount"] == Decimal("196428.57")
    assert unit["total_capitalized"] == Decimal("376428.57")

    assert r["total_traced"] == Decimal("180000.00")
    assert r["total_excess"] == Decimal("196428.57")
    assert r["total_capitalized"] == Decimal("376428.57")
    assert r["prorated"] is False

    c = r["consumption"]
    assert c["nontraced_consumed"] == Decimal("196428.57")
    assert c["nontraced_remaining_deductible"] == Decimal("3571.43")
    assert c["below_afr_consumed"] == Decimal("0")
    assert c["guaranteed_payments_consumed"] == Decimal("0")
    assert c["unsourced_excess"] == Decimal("0")

    # no book-capitalized interest on the fixture -> gross posts as the delta
    assert unit["tax_delta_to_post"] == Decimal("376428.57")


def test_golden_fixture_traced_debt_snapshots():
    """traced_debt_d = full $3M principal at every measurement date (APE
    exceeds the loan at every date; principal is the per-date fallback)."""
    projects, debts = _golden_inputs()
    r = compute_263af(projects, debts)
    unit = r["per_unit"]["TOWER"]
    assert unit["traced_debt_by_date"] == {
        d: Decimal("3000000") for d in unit["measurement_dates"]}
    assert unit["ape_snapshots"]["2025-12-31"] == Decimal("8000000")


def test_proration_across_units():
    """§1.263A-9(c)(7): cap applies ONLY to the excess pool, pro rata.

    Unit A: traced $1,000,000 loan ($60,000 actual interest); APE snapshots
      3,000,000 / 5,000,000 -> excess 2,000,000 / 4,000,000 -> avg 3,000,000
    Unit B: no traced debt; APE 500,000 / 1,500,000 -> avg excess 1,000,000
    Nontraced: $2,000,000 avg outstanding, $200,000 interest -> WAIR = 0.10
    Raw excess amounts: A = 300,000; B = 100,000; sum 400,000
    total_available = 200,000 nontraced (+0 +0) < 400,000 -> prorate by
    factor 200,000/400,000 = 0.5: A -> 150,000.00, B -> 50,000.00
    Traced interest untouched: total = 60,000 + 200,000 = 260,000.00
    consumption: all 200,000 of nontraced consumed, 0 remaining."""
    unit_a = CIPProject(project_id="A", snapshots=[
        _snap(2025, 6, 30, "3000000"), _snap(2025, 12, 31, "5000000")])
    unit_b = CIPProject(project_id="B", snapshots=[
        _snap(2025, 6, 30, "500000"), _snap(2025, 12, 31, "1500000")])
    debts = [
        DebtInstrument(debt_id="TA", principal=Decimal("1000000"),
                       rate=Decimal("0.06"),
                       interest_incurred=Decimal("60000"), traced_to="A"),
        DebtInstrument(debt_id="NT", principal=Decimal("2000000"),
                       interest_incurred=Decimal("200000")),
    ]
    r = compute_263af([unit_a, unit_b], debts)

    assert r["wair"] == Decimal("200000") / Decimal("2000000")
    assert r["per_unit"]["A"]["average_excess"] == Decimal("3000000")
    assert r["per_unit"]["B"]["average_excess"] == Decimal("1000000")

    assert r["prorated"] is True
    assert any(w.startswith("PRORATED") for w in r["warnings"])
    assert r["per_unit"]["A"]["excess_expenditure_amount"] == Decimal("150000.00")
    assert r["per_unit"]["B"]["excess_expenditure_amount"] == Decimal("50000.00")

    # traced interest is NEVER prorated or capped
    assert r["per_unit"]["A"]["traced_interest"] == Decimal("60000.00")
    assert r["per_unit"]["A"]["total_capitalized"] == Decimal("210000.00")
    assert r["per_unit"]["B"]["total_capitalized"] == Decimal("50000.00")
    assert r["total_excess"] == Decimal("200000.00")
    assert r["total_capitalized"] == Decimal("260000.00")

    c = r["consumption"]
    assert c["nontraced_consumed"] == Decimal("200000.00")
    assert c["nontraced_remaining_deductible"] == Decimal("0.00")
    assert c["unsourced_excess"] == Decimal("0")


def test_wair_afr_fallback():
    """§1.263A-9(c)(5)(iii)(D): no eligible nontraced debt -> WAIR = highest
    AFR, with the WAIR-AFR-FALLBACK warning.

    Unit: no traced debt; APE 400,000 / 600,000 -> excess = APE at each date
    -> avg excess = 500,000. WAIR = afr_highest = 0.05.
    excess amount = 500,000 x 0.05 = 25,000.00
    total_available = 0 nontraced + 50,000 below-AFR -> no proration.
    consumption skips the empty nontraced source: 25,000 consumed from the
    below-AFR related-party source; 25,000 of it stays deductible."""
    unit = CIPProject(project_id="U", snapshots=[
        _snap(2025, 6, 30, "400000"), _snap(2025, 12, 31, "600000")])
    r = compute_263af([unit], [], afr_highest=Decimal("0.05"),
                      below_afr_interest=Decimal("50000"))

    assert r["wair"] == Decimal("0.05")
    assert r["wair_source"] == "afr_fallback"
    assert any(w.startswith("WAIR-AFR-FALLBACK") for w in r["warnings"])

    assert r["per_unit"]["U"]["average_excess"] == Decimal("500000")
    assert r["per_unit"]["U"]["excess_expenditure_amount"] == Decimal("25000.00")
    assert r["total_capitalized"] == Decimal("25000.00")
    assert r["prorated"] is False

    c = r["consumption"]
    assert c["nontraced_consumed"] == Decimal("0")
    assert c["below_afr_consumed"] == Decimal("25000.00")
    assert c["below_afr_remaining_deductible"] == Decimal("25000.00")


def test_wair_unavailable_no_afr_no_fault():
    """No nontraced debt AND no afr_highest -> WAIR-UNAVAILABLE error flag,
    zero excess amounts, no exception (never a divide-by-zero).

    Only traced interest survives: 12,000.00."""
    unit = CIPProject(project_id="U", snapshots=[
        _snap(2025, 6, 30, "400000"), _snap(2025, 12, 31, "600000")])
    traced = DebtInstrument(debt_id="T", principal=Decimal("200000"),
                            interest_incurred=Decimal("12000"), traced_to="U")
    r = compute_263af([unit], [traced])   # must not raise

    assert r["wair"] == Decimal("0")
    assert r["wair_source"] == "unavailable"
    assert any(w.startswith("WAIR-UNAVAILABLE") for w in r["warnings"])
    assert r["per_unit"]["U"]["excess_expenditure_amount"] == Decimal("0.00")
    assert r["total_capitalized"] == Decimal("12000.00")
    assert r["consumption"]["nontraced_consumed"] == Decimal("0")


def test_ineligible_debt_screens():
    """§1.263A-9(a)(4) screens via DebtInstrument.is_eligible_debt.

    Excluded (each named in a warning): RP1, a related-party below-AFR loan;
    AP1, a non-interest-bearing UNtraced payable. Eligible: TAP, a
    non-interest-bearing payable that IS traced (eligible only because it is
    itself traced debt); NT1, the ordinary nontraced loan.

    WAIR pool = NT1 only: 80,000 / 1,000,000 = 0.08 (RP1's $1M principal and
    $10,000 interest and AP1's $500,000 principal all stay OUT).
    traced_debt at 2025-12-31 = TAP's $200,000 -> excess = 1,000,000 -
    200,000 = 800,000 = average excess (single date).
    excess amount = 800,000 x 0.08 = 64,000.00 <= 80,000 -> no proration."""
    unit = CIPProject(project_id="U1",
                      snapshots=[_snap(2025, 12, 31, "1000000")])
    rp = DebtInstrument(debt_id="RP1", principal=Decimal("1000000"),
                        interest_incurred=Decimal("10000"),
                        related_party_below_afr=True)
    ap = DebtInstrument(debt_id="AP1", principal=Decimal("500000"),
                        interest_incurred=Decimal("0"),
                        non_interest_bearing=True)
    tap = DebtInstrument(debt_id="TAP", principal=Decimal("200000"),
                         interest_incurred=Decimal("0"),
                         non_interest_bearing=True, traced_to="U1")
    nt = DebtInstrument(debt_id="NT1", principal=Decimal("1000000"),
                        interest_incurred=Decimal("80000"))
    r = compute_263af([unit], [rp, ap, tap, nt])

    # WAIR from the eligible nontraced debt only
    assert r["wair"] == Decimal("80000") / Decimal("1000000")
    assert r["wair_source"] == "nontraced"

    # each excluded instrument named, with its (a)(4) screen
    rp_warns = [w for w in r["warnings"] if "RP1" in w]
    ap_warns = [w for w in r["warnings"] if "AP1" in w]
    assert len(rp_warns) == 1 and "below-AFR" in rp_warns[0]
    assert len(ap_warns) == 1 and "non-interest-bearing" in ap_warns[0]
    # the TRACED non-interest-bearing payable is eligible — no warning
    assert not any("TAP" in w for w in r["warnings"])

    u = r["per_unit"]["U1"]
    assert u["traced_debt_by_date"] == {"2025-12-31": Decimal("200000")}
    assert u["average_excess"] == Decimal("800000")
    assert u["excess_expenditure_amount"] == Decimal("64000.00")
    assert u["traced_interest"] == Decimal("0.00")
    assert r["prorated"] is False


def _recon_inputs(book):
    """Traced-only unit for the Step-3b reconciliation tests.

    APE 1,000,000 = traced principal 1,000,000 at the single date -> excess 0.
    Nontraced $1,000,000 / $50,000 keeps WAIR real (0.05) but has nothing to
    multiply. Computed unit total = traced interest 120,000.00 exactly."""
    unit = CIPProject(project_id="U", book_capitalized_interest=book,
                      snapshots=[_snap(2025, 12, 31, "1000000")])
    debts = [
        DebtInstrument(debt_id="T", principal=Decimal("1000000"),
                       interest_incurred=Decimal("120000"), traced_to="U"),
        DebtInstrument(debt_id="NT", principal=Decimal("1000000"),
                       interest_incurred=Decimal("50000")),
    ]
    return [unit], debts


def test_book_capitalized_interest_delta_posts():
    """ASC 835-20 book interest 50,000 already in basis; computed 120,000
    -> tax_delta_to_post = 120,000 - 50,000 = 70,000, BASIS-RECONCILED
    warning from the shared reconcile() helper; gross figure stays visible."""
    projects, debts = _recon_inputs(Decimal("50000"))
    r = compute_263af(projects, debts)
    u = r["per_unit"]["U"]
    assert u["total_capitalized"] == Decimal("120000.00")   # gross visible
    assert u["book_capitalized_interest"] == Decimal("50000")
    assert u["tax_delta_to_post"] == Decimal("70000.00")
    assert any(w.startswith("BASIS-RECONCILED") for w in r["warnings"])


def test_book_exceeds_tax_required_flags_no_negative():
    """Book 200,000 EXCEEDS computed 120,000 -> delta 0 (never a negative
    posting) + BOOK-EXCEEDS-TAX-REQUIRED flag, via the shared helper."""
    projects, debts = _recon_inputs(Decimal("200000"))
    r = compute_263af(projects, debts)
    u = r["per_unit"]["U"]
    assert u["total_capitalized"] == Decimal("120000.00")
    assert u["tax_delta_to_post"] == Decimal("0")
    assert any(w.startswith("BOOK-EXCEEDS-TAX-REQUIRED") for w in r["warnings"])
