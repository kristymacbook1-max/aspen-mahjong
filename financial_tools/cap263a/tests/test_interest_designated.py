"""§1.263A-8(b) designated-property gate + §1.263A-11(c)/(f) APE adjustments
(engines/interest.py). Hand arithmetic in each test's docstring."""

from datetime import date
from decimal import Decimal

from financial_tools.cap263a.model import CIPProject, CIPSnapshot, DebtInstrument
from financial_tools.cap263a.engines.interest import compute_263af


def _snap(y, m, d, ape):
    return CIPSnapshot(measurement_date=date(y, m, d),
                       cumulative_ape=Decimal(ape))


def _nt(principal="3000000", interest="300000"):
    """Nontraced pool: WAIR = 300,000 / 3,000,000 = 0.10 exactly, with
    plenty of headroom so no test here trips the (c)(7) proration cap."""
    return DebtInstrument(debt_id="NT", principal=Decimal(principal),
                          interest_incurred=Decimal(interest))


# ---------------------------------------------------------------------------
# §1.263A-8(b) designated-property classification — the four inclusion prongs
# ---------------------------------------------------------------------------

def test_real_property_always_designated_silently():
    """A bare CIPProject (is_real_property defaults True) classifies
    real_property with NO designation warning — the backward-compat path
    every existing fixture rides."""
    unit = CIPProject(project_id="R", snapshots=[_snap(2025, 12, 31, "1000000")])
    r = compute_263af([unit], [_nt()])
    assert r["per_unit"]["R"]["designated_basis"] == "real_property"
    assert not any("DESIGNATED" in w for w in r["warnings"])
    # 1,000,000 avg excess x 0.10 = 100,000.00
    assert r["per_unit"]["R"]["excess_expenditure_amount"] == Decimal("100000.00")


def test_personal_property_class_life_20_designated():
    """Tangible personal property with class life 25 >= 20 years is
    designated on prong (i) even with a short production period."""
    unit = CIPProject(project_id="P", is_real_property=False,
                      class_life=Decimal("25"),
                      production_start=date(2025, 1, 1),
                      production_complete=date(2025, 6, 30),
                      snapshots=[_snap(2025, 12, 31, "500000")])
    r = compute_263af([unit], [_nt()])
    assert r["per_unit"]["P"]["designated_basis"] == "class_life_20"
    assert not any("DESIGNATED" in w for w in r["warnings"])


def test_personal_property_period_over_2yr_designated():
    """class life 10 < 20 but production period 911 days > 730 -> prong
    (ii). (2023-01-01 -> 2025-06-30 = 911 days.)"""
    unit = CIPProject(project_id="P", is_real_property=False,
                      class_life=Decimal("10"),
                      production_start=date(2023, 1, 1),
                      production_complete=date(2025, 6, 30),
                      snapshots=[_snap(2025, 12, 31, "500000")])
    assert (date(2025, 6, 30) - date(2023, 1, 1)).days == 911
    r = compute_263af([unit], [_nt()])
    assert r["per_unit"]["P"]["designated_basis"] == "period_over_2yr"
    assert not any("DESIGNATED" in w for w in r["warnings"])


def test_personal_property_period_1yr_cost_1m_designated():
    """2025-01-01 -> 2026-06-30 (between 1 and 2 years, asserted below)
    with $2M estimated cost -> prong (iii)."""
    start, complete = date(2025, 1, 1), date(2026, 6, 30)
    days = (complete - start).days
    assert 365 < days <= 730
    unit = CIPProject(project_id="P", is_real_property=False,
                      class_life=Decimal("10"),
                      total_estimated_cost=Decimal("2000000"),
                      production_start=start, production_complete=complete,
                      snapshots=[_snap(2025, 12, 31, "500000")])
    r = compute_263af([unit], [_nt()])
    assert r["per_unit"]["P"]["designated_basis"] == "period_1yr_cost_1m"
    assert not any("DESIGNATED" in w for w in r["warnings"])


def test_not_designated_excluded_entirely():
    """Every prong affirmatively fails (class life 5, 180-day period,
    $500K cost) -> the unit leaves the computation: no per-unit worksheet,
    its traced debt's $50,000 interest is NOT capitalized and does NOT
    join the WAIR pool.

    R (real): excess 1,000,000 at the single date -> 1,000,000 x 0.10 =
    100,000.00 excess; total_capitalized = 100,000.00 exactly (nothing from
    NP's traced loan). WAIR stays 300,000/3,000,000 = 0.10 (NP's traced
    debt never falls into the nontraced pool)."""
    r_unit = CIPProject(project_id="R", snapshots=[_snap(2025, 12, 31, "1000000")])
    np_unit = CIPProject(project_id="NP", is_real_property=False,
                         class_life=Decimal("5"),
                         total_estimated_cost=Decimal("500000"),
                         production_start=date(2025, 1, 1),
                         production_complete=date(2025, 6, 30),
                         snapshots=[_snap(2025, 12, 31, "800000")])
    traced_np = DebtInstrument(debt_id="TNP", principal=Decimal("600000"),
                               interest_incurred=Decimal("50000"),
                               traced_to="NP")
    r = compute_263af([r_unit, np_unit], [traced_np, _nt()])

    assert "NP" not in r["per_unit"]
    excl = [w for w in r["warnings"] if w.startswith("NOT-DESIGNATED-EXCLUDED [NP]")]
    assert len(excl) == 1
    # the warning names the failed prongs
    assert "class life 5" in excl[0] and "365" in excl[0]
    # traced interest on the excluded unit is neither traced nor WAIR
    assert r["wair"] == Decimal("300000") / Decimal("3000000")
    assert r["total_traced"] == Decimal("0.00")
    assert r["total_capitalized"] == Decimal("100000.00")
    # and NOT consumed as nontraced either
    assert r["consumption"]["nontraced_remaining_deductible"] == Decimal("200000.00")


def test_not_designated_boundary_730_days_cost_at_1m():
    """Boundary: exactly 730 days is NOT > 2 years, and cost exactly
    $1,000,000 is NOT > $1,000,000 — prong (iii) fails too -> excluded.
    (2024-01-01 -> 2025-12-31 = 730 days across the 2024 leap year.)"""
    assert (date(2025, 12, 31) - date(2024, 1, 1)).days == 730
    unit = CIPProject(project_id="B", is_real_property=False,
                      class_life=Decimal("19"),
                      total_estimated_cost=Decimal("1000000"),
                      production_start=date(2024, 1, 1),
                      production_complete=date(2025, 12, 31),
                      snapshots=[_snap(2025, 12, 31, "900000")])
    r = compute_263af([unit], [_nt()])
    assert r["per_unit"] == {}
    assert any(w.startswith("NOT-DESIGNATED-EXCLUDED [B]") for w in r["warnings"])


def test_unknown_facts_include_conservatively():
    """Personal property with NO class life and NO production dates: the
    tri-state posture — included as designated with basis
    assumed_conservative and a DESIGNATED-STATUS-UNKNOWN warning listing
    the missing facts. Computation identical to a designated unit:
    400,000 avg excess x 0.10 = 40,000.00."""
    unit = CIPProject(project_id="U", is_real_property=False,
                      snapshots=[_snap(2025, 12, 31, "400000")])
    r = compute_263af([unit], [_nt()])
    assert r["per_unit"]["U"]["designated_basis"] == "assumed_conservative"
    unk = [w for w in r["warnings"] if w.startswith("DESIGNATED-STATUS-UNKNOWN [U]")]
    assert len(unk) == 1
    assert "class_life" in unk[0] and "production" in unk[0]
    assert r["per_unit"]["U"]["excess_expenditure_amount"] == Decimal("40000.00")


def test_missing_dates_but_qualifying_class_life_is_silent():
    """class life 30 >= 20 designates on prong (i) alone — missing
    production dates draw NO unknown warning (explicit qualification)."""
    unit = CIPProject(project_id="Q", is_real_property=False,
                      class_life=Decimal("30"),
                      snapshots=[_snap(2025, 12, 31, "100000")])
    r = compute_263af([unit], [_nt()])
    assert r["per_unit"]["Q"]["designated_basis"] == "class_life_20"
    assert not any("DESIGNATED-STATUS-UNKNOWN" in w for w in r["warnings"])


# ---------------------------------------------------------------------------
# §1.263A-11(c) contract payments / (f) mid-production purchase
# ---------------------------------------------------------------------------

def test_customer_contract_payments_raise_ape():
    """§1.263A-11(c): the customer's APE includes cumulative contract
    payments on/before each measurement date.

    Baseline APE 1,000,000 / 2,000,000 (no traced debt) -> avg excess
    1,500,000. A $500,000 payment on 2025-03-15 (keyed mm/dd/yyyy to
    exercise date-key normalization) is cumulative at BOTH dates:
    effective APE 1,500,000 / 2,500,000 -> avg excess 2,000,000.
    Excess amount = 2,000,000 x 0.10 = 200,000.00 (was 150,000.00)."""
    unit = CIPProject(project_id="C", contract_role="customer",
                      contract_payments_by_date={"03/15/2025": Decimal("500000")},
                      snapshots=[_snap(2025, 6, 30, "1000000"),
                                 _snap(2025, 12, 31, "2000000")])
    r = compute_263af([unit], [_nt()])
    u = r["per_unit"]["C"]
    assert u["ape_snapshots"] == {"2025-06-30": Decimal("1500000"),
                                  "2025-12-31": Decimal("2500000")}
    assert u["average_excess"] == Decimal("2000000")
    assert u["excess_expenditure_amount"] == Decimal("200000.00")
    added = [w for w in r["warnings"] if w.startswith("CONTRACT-PAYMENTS-ADDED [C]")]
    assert len(added) == 1 and "$500,000.00" in added[0]


def test_customer_payment_after_date_not_yet_cumulative():
    """A payment dated between the two measurement dates joins only the
    LATER snapshot: 300,000 paid 2025-09-30 -> APE 1,000,000 then
    2,300,000 -> avg excess 1,650,000 -> 165,000.00."""
    unit = CIPProject(project_id="C", contract_role="customer",
                      contract_payments_by_date={"2025-09-30": Decimal("300000")},
                      snapshots=[_snap(2025, 6, 30, "1000000"),
                                 _snap(2025, 12, 31, "2000000")])
    r = compute_263af([unit], [_nt()])
    u = r["per_unit"]["C"]
    assert u["ape_snapshots"] == {"2025-06-30": Decimal("1000000"),
                                  "2025-12-31": Decimal("2300000")}
    assert u["excess_expenditure_amount"] == Decimal("165000.00")


def test_contractor_warns_and_computes_unchanged():
    """§1.263A-11(c)'s CONTRACTOR-side APE reduction is not implemented:
    CONTRACTOR-APE-NOT-REDUCED warning, computation identical to the
    role-less baseline (avg excess 1,500,000 -> 150,000.00)."""
    unit = CIPProject(project_id="K", contract_role="contractor",
                      contract_payments_by_date={"2025-03-15": Decimal("500000")},
                      snapshots=[_snap(2025, 6, 30, "1000000"),
                                 _snap(2025, 12, 31, "2000000")])
    r = compute_263af([unit], [_nt()])
    u = r["per_unit"]["K"]
    assert u["average_excess"] == Decimal("1500000")
    assert u["excess_expenditure_amount"] == Decimal("150000.00")
    assert any(w.startswith("CONTRACTOR-APE-NOT-REDUCED [K]") for w in r["warnings"])
    assert not any(w.startswith("CONTRACT-PAYMENTS-ADDED") for w in r["warnings"])


def test_mid_production_purchase_price_added_every_date():
    """§1.263A-11(f) with no purchase date on the schedule: the $400,000
    price joins APE at EVERY measurement date (earliest-inclusion proxy)
    with the MID-PRODUCTION-PURCHASE-DATE-MISSING warning.

    APE 600,000 / 1,000,000 -> effective 1,000,000 / 1,400,000 ->
    avg excess 1,200,000 -> 120,000.00 (was 80,000.00)."""
    unit = CIPProject(project_id="M",
                      mid_production_purchase_price=Decimal("400000"),
                      snapshots=[_snap(2025, 6, 30, "600000"),
                                 _snap(2025, 12, 31, "1000000")])
    r = compute_263af([unit], [_nt()])
    u = r["per_unit"]["M"]
    assert u["ape_snapshots"] == {"2025-06-30": Decimal("1000000"),
                                  "2025-12-31": Decimal("1400000")}
    assert u["excess_expenditure_amount"] == Decimal("120000.00")
    warns = [w for w in r["warnings"]
             if w.startswith("MID-PRODUCTION-PURCHASE-DATE-MISSING [M]")]
    assert len(warns) == 1 and "$400,000.00" in warns[0]
