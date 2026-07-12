"""§263(a) tangible-property capitalize-vs-deduct engine (repair regs,
Reg. §1.263(a)-1/-2/-3 and §1.162-3) — every treatment branch, the
conservative capitalize-on-missing-BAR path, open-question emission, and
the exact safe-harbor boundaries. Golden figures hand-computed in each
docstring."""

from decimal import Decimal

from financial_tools.cap263a.analysis import EntityProfile
from financial_tools.cap263a.engines.tangible_263a import (
    TangibleExpenditure, compute_tangible_263a)


def _p(**overrides):
    kw = dict(avg_gross_receipts=Decimal("5000000"))
    kw.update(overrides)
    return EntityProfile(**kw)


def _repair(item_id, amount, **overrides):
    """An item with all BAR prongs explicitly False (pure repair facts)."""
    kw = dict(item_id=item_id, description=item_id, amount=Decimal(str(amount)),
              betterment=False, adaptation=False, restoration=False)
    kw.update(overrides)
    return TangibleExpenditure(**kw)


# --- step 2: de minimis safe harbor (§1.263(a)-1(f)) -------------------------

def test_de_minimis_at_exact_afs_ceiling():
    """AFS ceiling $5,000 (profile.de_minimis_ceiling): invoice cost exactly
    5,000 deducts; 5,000.01 falls through to the repair path. Election +
    AFS also draws the written-policy condition reminder once per run."""
    items = [_repair("D1", 5000, invoice_or_item_cost=Decimal("5000")),
             _repair("D2", 5000, invoice_or_item_cost=Decimal("5000.01"),
                     routine_maintenance_expected_more_than_once=False)]
    out = compute_tangible_263a(items, _p(has_afs=True),
                                de_minimis_election=True)
    assert out["items"][0]["treatment"] == "de_minimis_deduct"
    assert "1.263(a)-1(f)" in out["items"][0]["authority"]
    assert "Notice 2015-82" in out["items"][0]["authority"]
    assert out["items"][1]["treatment"] == "repair_deduct"
    assert sum(1 for w in out["warnings"]
               if "DE-MINIMIS-POLICY-CONDITION" in w) == 1
    assert out["deductible_total"] == Decimal("10000")


def test_de_minimis_no_afs_ceiling_2500():
    """Without an AFS the ceiling is $2,500 (Notice 2015-82): 2,500 deducts,
    2,500.01 falls through. No AFS -> no written-policy warning."""
    items = [_repair("D1", 2500, invoice_or_item_cost=Decimal("2500")),
             _repair("D2", 2500, invoice_or_item_cost=Decimal("2500.01"),
                     routine_maintenance_expected_more_than_once=False)]
    out = compute_tangible_263a(items, _p(has_afs=False),
                                de_minimis_election=True)
    assert out["items"][0]["treatment"] == "de_minimis_deduct"
    assert out["items"][1]["treatment"] == "repair_deduct"
    assert not any("DE-MINIMIS-POLICY-CONDITION" in w for w in out["warnings"])


def test_de_minimis_cost_unknown_flags_asks_and_continues():
    """Election on, invoice_or_item_cost missing: DE-MINIMIS-COST-UNKNOWN +
    an open question, and the item continues down the tree — here BAR facts
    are also missing, so it lands in open_question_capitalize_pending."""
    it = TangibleExpenditure(item_id="U1", description="Shop equipment",
                             amount=Decimal("3000"))
    out = compute_tangible_263a([it], _p(), de_minimis_election=True)
    row = out["items"][0]
    assert "DE-MINIMIS-COST-UNKNOWN" in row["flags"]
    assert row["treatment"] == "open_question_capitalize_pending"
    questions = " ".join(q["question"] for q in out["open_questions"])
    assert "invoice_or_item_cost" in questions
    assert "$5,000" in questions


def test_de_minimis_not_applied_without_election():
    """No election -> a cheap item is NOT deducted under (f); with no BAR
    facts it capitalizes conservatively."""
    it = TangibleExpenditure(item_id="X1", amount=Decimal("100"),
                             invoice_or_item_cost=Decimal("100"))
    out = compute_tangible_263a([it], _p())
    assert out["items"][0]["treatment"] == "open_question_capitalize_pending"
    assert out["capitalized_total"] == Decimal("100")


# --- step 3: materials & supplies (§1.162-3) ---------------------------------

def test_materials_supplies_each_prong_and_single_timing_warning():
    """Either prong alone deducts, citing its own subparagraph; the
    incidental/non-incidental timing warning fires ONCE for the run, not
    per item."""
    items = [TangibleExpenditure(item_id="M1", amount=Decimal("180"),
                                 is_material_or_supply=True,
                                 ms_unit_cost_200_or_less=True),
             TangibleExpenditure(item_id="M2", amount=Decimal("900"),
                                 is_material_or_supply=True,
                                 ms_economic_life_12mo_or_less=True)]
    out = compute_tangible_263a(items, _p())
    assert out["items"][0]["treatment"] == "materials_supplies_deduct"
    assert "(c)(1)(iv)" in out["items"][0]["authority"]
    assert out["items"][1]["treatment"] == "materials_supplies_deduct"
    assert "(c)(1)(iii)" in out["items"][1]["authority"]
    assert all("MS-TIMING-NOT-DETERMINED" in r["flags"] for r in out["items"])
    assert sum(1 for w in out["warnings"]
               if "MS-TIMING-NOT-DETERMINED" in w) == 1
    assert out["deductible_total"] == Decimal("1080")


def test_materials_supplies_both_prongs_none_asks_and_falls_through():
    """Both §1.162-3 prongs unanswered -> open question + fall through; with
    BAR all False and routine maintenance True the item lands in the
    routine maintenance safe harbor instead."""
    it = _repair("M3", 750, is_material_or_supply=True,
                 routine_maintenance_expected_more_than_once=True)
    out = compute_tangible_263a([it], _p())
    assert out["items"][0]["treatment"] == "routine_maintenance_deduct"
    assert any("ms_unit_cost_200_or_less" in q["question"]
               for q in out["open_questions"])


# --- step 4: small taxpayer building safe harbor (§1.263(a)-3(h)) ------------

def test_stsh_boundary_exactly_at_2pct_ceiling():
    """Basis 400,000: 2% = 8,000, which is the LESSER of (10,000, 8,000).
    Aggregate exactly 8,000 passes; 8,000.01 fails and the item (pure
    repair facts) falls through to repair_deduct."""
    def item():
        return _repair("B1", 4000, is_building=True, unit_of_property="BLDG-A",
                       building_unadjusted_basis=Decimal("400000"),
                       routine_maintenance_expected_more_than_once=False)
    out = compute_tangible_263a(
        [item()], _p(), small_taxpayer_building_election=True,
        total_building_repairs_maintenance_improvements={
            "BLDG-A": Decimal("8000")})
    assert out["items"][0]["treatment"] == "small_taxpayer_sh_deduct"
    assert "1.263(a)-3(h)" in out["items"][0]["authority"]

    out2 = compute_tangible_263a(
        [item()], _p(), small_taxpayer_building_election=True,
        total_building_repairs_maintenance_improvements={
            "BLDG-A": Decimal("8000.01")})
    assert out2["items"][0]["treatment"] == "repair_deduct"
    assert "STSH-CEILING-EXCEEDED" in out2["items"][0]["flags"]


def test_stsh_lesser_of_uses_10k_for_larger_basis():
    """Basis 1,000,000 (exactly eligible): 2% = 20,000, so the $10,000
    prong binds. Aggregate 10,000 passes; 10,000.01 fails."""
    def item():
        return _repair("B2", 6000, is_building=True, unit_of_property="BLDG-B",
                       building_unadjusted_basis=Decimal("1000000"),
                       routine_maintenance_expected_more_than_once=False)
    out = compute_tangible_263a(
        [item()], _p(), small_taxpayer_building_election=True,
        total_building_repairs_maintenance_improvements={
            "BLDG-B": Decimal("10000")})
    assert out["items"][0]["treatment"] == "small_taxpayer_sh_deduct"

    out2 = compute_tangible_263a(
        [item()], _p(), small_taxpayer_building_election=True,
        total_building_repairs_maintenance_improvements={
            "BLDG-B": Decimal("10000.01")})
    assert out2["items"][0]["treatment"] == "repair_deduct"
    assert "STSH-CEILING-EXCEEDED" in out2["items"][0]["flags"]


def test_stsh_aggregate_from_schedule_warns_once():
    """No explicit dict: the per-building aggregate is summed from the
    supplied items sharing the UOP (3,000 + 4,000 = 7,000 <= 8,000 ceiling
    on a 400,000 basis) with the schedule-only warning ONCE."""
    items = [_repair("B3", 3000, is_building=True, unit_of_property="BLDG-C",
                     building_unadjusted_basis=Decimal("400000")),
             _repair("B4", 4000, is_building=True, unit_of_property="BLDG-C",
                     building_unadjusted_basis=Decimal("400000"))]
    out = compute_tangible_263a([items[0], items[1]], _p(),
                                small_taxpayer_building_election=True)
    assert all(r["treatment"] == "small_taxpayer_sh_deduct"
               for r in out["items"])
    assert sum(1 for w in out["warnings"]
               if "STSH-AGGREGATE-FROM-SCHEDULE-ONLY" in w) == 1
    assert out["deductible_total"] == Decimal("7000")


def test_stsh_ineligible_receipts_warns_and_item_continues():
    """Receipts $15M > $10M: run-level STSH-INELIGIBLE-RECEIPTS warning,
    item flagged STSH-NOT-ELIGIBLE and routed by BAR instead
    (restoration True -> improvement)."""
    it = TangibleExpenditure(item_id="B5", amount=Decimal("5000"),
                             is_building=True, unit_of_property="BLDG-D",
                             building_unadjusted_basis=Decimal("500000"),
                             restoration=True)
    out = compute_tangible_263a(
        [it], _p(avg_gross_receipts=Decimal("15000000")),
        small_taxpayer_building_election=True,
        total_building_repairs_maintenance_improvements={
            "BLDG-D": Decimal("5000")})
    assert any("STSH-INELIGIBLE-RECEIPTS" in w for w in out["warnings"])
    assert "STSH-NOT-ELIGIBLE" in out["items"][0]["flags"]
    assert out["items"][0]["treatment"] == "improvement_capitalize"


def test_stsh_basis_over_1m_not_eligible():
    """Unadjusted basis 1,000,000.01 > $1M: not an eligible building — the
    item falls through (pure repair facts -> repair_deduct)."""
    it = _repair("B6", 2000, is_building=True, unit_of_property="BLDG-E",
                 building_unadjusted_basis=Decimal("1000000.01"),
                 routine_maintenance_expected_more_than_once=False)
    out = compute_tangible_263a(
        [it], _p(), small_taxpayer_building_election=True,
        total_building_repairs_maintenance_improvements={
            "BLDG-E": Decimal("2000")})
    assert "STSH-NOT-ELIGIBLE" in out["items"][0]["flags"]
    assert out["items"][0]["treatment"] == "repair_deduct"


# --- step 5: BAR improvement tests -------------------------------------------

def test_bar_prongs_capitalize_citing_the_specific_prong():
    items = [TangibleExpenditure(item_id="I1", amount=Decimal("10000"),
                                 betterment=True),
             TangibleExpenditure(item_id="I2", amount=Decimal("20000"),
                                 adaptation=True),
             TangibleExpenditure(item_id="I3", amount=Decimal("30000"),
                                 restoration=True)]
    out = compute_tangible_263a(items, _p())
    assert all(r["treatment"] == "improvement_capitalize"
               for r in out["items"])
    assert "(j)" in out["items"][0]["authority"]
    assert "(l)" in out["items"][1]["authority"]
    assert "(k)" in out["items"][2]["authority"]
    assert out["capitalized_total"] == Decimal("60000")
    assert out["deductible_total"] == Decimal("0")


def test_bar_missing_facts_capitalize_conservatively_naming_prongs():
    """restoration unanswered (betterment/adaptation explicitly False):
    NEVER silently deducted — capitalized pending with BAR-FACTS-INCOMPLETE
    and an open question naming ONLY the missing prong."""
    it = TangibleExpenditure(item_id="R2",
                             description="Roof membrane replacement",
                             amount=Decimal("45000"), betterment=False,
                             adaptation=False, restoration=None)
    out = compute_tangible_263a([it], _p())
    row = out["items"][0]
    assert row["treatment"] == "open_question_capitalize_pending"
    assert "BAR-FACTS-INCOMPLETE" in row["flags"]
    assert row["capitalized"] == Decimal("45000")
    assert out["capitalized_total"] == Decimal("45000")
    q = next(q for q in out["open_questions"] if q["item_id"] == "R2")
    assert "restoration" in q["question"]
    assert "1.263(a)-3(k)" in q["question"]
    assert "betterment (§1.263(a)-3(j))" not in q["question"]


def test_identical_open_questions_not_duplicated():
    """Two identical rows produce ONE open question, not two."""
    def it():
        return TangibleExpenditure(item_id="DUP", description="HVAC work",
                                   amount=Decimal("1000"))
    out = compute_tangible_263a([it(), it()], _p())
    assert len(out["open_questions"]) == 1
    assert out["capitalized_total"] == Decimal("2000")


# --- steps 6/7: routine maintenance, repair, (n) election ---------------------

def test_routine_maintenance_deduct():
    it = _repair("RM1", 3200, routine_maintenance_expected_more_than_once=True)
    out = compute_tangible_263a([it], _p())
    assert out["items"][0]["treatment"] == "routine_maintenance_deduct"
    assert "1.263(a)-3(i)" in out["items"][0]["authority"]
    assert out["deductible_total"] == Decimal("3200")


def test_routine_maintenance_unanswered_asks_then_repair():
    """RMSH prong None with all BAR False: an open question about the
    more-than-once expectation, and the item deducts as a plain repair."""
    it = _repair("RM2", 800)
    out = compute_tangible_263a([it], _p())
    assert out["items"][0]["treatment"] == "repair_deduct"
    assert "§162" in out["items"][0]["authority"]
    assert any("1.263(a)-3(i)" in q["question"] for q in out["open_questions"])


def test_n_election_routes_and_warns_on_inconsistency():
    """(n) election on: book-capitalized repair -> elective_capitalize_books
    (elective_capitalized_total 2,000); book-expensed repair -> repair_deduct
    (600) — and the mixed book treatment draws N-ELECTION-CONSISTENCY."""
    items = [_repair("E1", 2000, book_capitalized=True,
                     routine_maintenance_expected_more_than_once=False),
             _repair("E2", 600,
                     routine_maintenance_expected_more_than_once=False)]
    out = compute_tangible_263a(items, _p(),
                                capitalize_repairs_following_books=True)
    assert out["items"][0]["treatment"] == "elective_capitalize_books"
    assert "1.263(a)-3(n)" in out["items"][0]["authority"]
    assert out["items"][1]["treatment"] == "repair_deduct"
    assert out["elective_capitalized_total"] == Decimal("2000")
    assert out["deductible_total"] == Decimal("600")
    assert any("N-ELECTION-CONSISTENCY" in w for w in out["warnings"])


def test_no_n_election_book_capitalized_still_deducts():
    """Without the (n) election, book capitalization does not control —
    a repair on the facts deducts, no consistency warning."""
    it = _repair("E3", 900, book_capitalized=True,
                 routine_maintenance_expected_more_than_once=False)
    out = compute_tangible_263a([it], _p())
    assert out["items"][0]["treatment"] == "repair_deduct"
    assert out["elective_capitalized_total"] == Decimal("0")
    assert not any("N-ELECTION-CONSISTENCY" in w for w in out["warnings"])


# --- step 1 + totals tie -------------------------------------------------------

def test_negative_amount_sme_review_excluded_from_totals():
    it = TangibleExpenditure(item_id="N1", amount=Decimal("-50"),
                             restoration=True)
    out = compute_tangible_263a([it], _p())
    assert out["items"][0]["treatment"] == "sme_review"
    assert "NEGATIVE-AMOUNT" in out["items"][0]["flags"]
    assert any("NEGATIVE-AMOUNT" in w for w in out["warnings"])
    assert out["deductible_total"] == Decimal("0")
    assert out["capitalized_total"] == Decimal("0")
    assert out["elective_capitalized_total"] == Decimal("0")


def test_totals_tie_across_every_branch():
    """One item per branch. Hand arithmetic:
      deductible = 1,200 (de minimis) + 500 (M&S) + 4,000 (STSH)
                 + 900 (routine) + 600 (repair)               =  7,200
      capitalized = 25,000 (improvement) + 7,500 (BAR pending) = 32,500
      elective    = 2,000 ((n) election)                       =  2,000
      sme_review  = -50 (excluded)
      tie: 7,200 + 32,500 + 2,000 = 41,700 = sum of non-review amounts."""
    items = [
        _repair("D1", 1200, invoice_or_item_cost=Decimal("900")),
        TangibleExpenditure(item_id="M1", amount=Decimal("500"),
                            is_material_or_supply=True,
                            ms_unit_cost_200_or_less=True),
        _repair("B1", 4000, is_building=True, unit_of_property="HQ",
                building_unadjusted_basis=Decimal("400000")),
        TangibleExpenditure(item_id="I1", amount=Decimal("25000"),
                            restoration=True,
                            invoice_or_item_cost=Decimal("25000")),
        TangibleExpenditure(item_id="Q1", amount=Decimal("7500"),
                            invoice_or_item_cost=Decimal("7500")),
        _repair("R1", 900, routine_maintenance_expected_more_than_once=True,
                invoice_or_item_cost=Decimal("5100")),
        _repair("R2", 600, routine_maintenance_expected_more_than_once=False,
                invoice_or_item_cost=Decimal("5100")),
        _repair("E1", 2000, book_capitalized=True,
                routine_maintenance_expected_more_than_once=False,
                invoice_or_item_cost=Decimal("5100")),
        TangibleExpenditure(item_id="N1", amount=Decimal("-50")),
    ]
    out = compute_tangible_263a(
        items, _p(), de_minimis_election=True,
        small_taxpayer_building_election=True,
        capitalize_repairs_following_books=True,
        total_building_repairs_maintenance_improvements={
            "HQ": Decimal("8000")})
    assert out["deductible_total"] == Decimal("7200")
    assert out["capitalized_total"] == Decimal("32500")
    assert out["elective_capitalized_total"] == Decimal("2000")
    non_review = sum((it.amount for it in items if it.amount >= 0),
                     Decimal("0"))
    assert (out["deductible_total"] + out["capitalized_total"]
            + out["elective_capitalized_total"]) == non_review == Decimal("41700")
    # BAR-pending item Q1 is in the OPEN QUESTIONS, never silently deducted
    assert any(q["item_id"] == "Q1" for q in out["open_questions"])
