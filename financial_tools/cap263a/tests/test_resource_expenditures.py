"""Resource-expenditure engines — compute_idc (§263(c)/§263(i)/§291(b)),
compute_mining (§616/§617/§291(b)), compute_circulation (§173): every
treatment branch, the conservative capitalize-on-missing-election paths,
the 30/70 penny split, open-question emission and dedup, and totals ties.
Golden figures hand-computed in each docstring."""

from decimal import Decimal

from financial_tools.cap263a.engines.resource_expenditures import (
    CirculationItem, IDCItem, MiningItem, compute_circulation, compute_idc,
    compute_mining)


def _idc(item_id="W1", amount="100000", **kw):
    """An IDC item with the working-interest gate satisfied by default."""
    kw.setdefault("operator_or_working_interest", True)
    return IDCItem(item_id=item_id, description=item_id,
                   amount=Decimal(amount), **kw)


def _mine(item_id="M1", amount="80000", kind="development", **kw):
    return MiningItem(item_id=item_id, description=item_id,
                      amount=Decimal(amount), kind=kind, **kw)


def _circ(item_id="C1", amount="25000"):
    return CirculationItem(item_id=item_id, description=item_id,
                           amount=Decimal(amount))


# =============================== IDC =========================================

# --- step 1: negative guard ---------------------------------------------------

def test_idc_negative_amount_sme_review():
    """Negative -> sme_review + NEGATIVE-AMOUNT, excluded from both totals."""
    out = compute_idc([_idc(amount="-500")], expense_election=True)
    row = out["items"][0]
    assert row["treatment"] == "sme_review"
    assert "NEGATIVE-AMOUNT" in row["flags"]
    assert any("NEGATIVE-AMOUNT [idc W1]" in w for w in out["warnings"])
    assert out["deductible_total"] == Decimal("0")
    assert out["capitalized_total"] == Decimal("0")
    assert out["amortizable_items"] == []


# --- step 2: working/operating interest (Reg. §1.612-4(a)) --------------------

def test_idc_working_interest_unknown_capitalizes_and_asks():
    """operator_or_working_interest None -> conservative capitalize with
    IDC-INTEREST-STATUS-UNKNOWN + an open question; nothing posted to the
    amortization schedule pending the answer. The gate PRECEDES the foreign
    branch: a foreign well with unknown interest lands here, not in §263(i)."""
    out = compute_idc([_idc(operator_or_working_interest=None, foreign=True)],
                      expense_election=True)
    row = out["items"][0]
    assert row["treatment"] == "open_question_capitalize_pending"
    assert "IDC-INTEREST-STATUS-UNKNOWN" in row["flags"]
    assert out["capitalized_total"] == Decimal("100000")
    assert out["deductible_total"] == Decimal("0")
    assert out["amortizable_items"] == []
    [q] = out["open_questions"]
    assert "operator_or_working_interest" in q["question"]
    assert "1.612-4(a)" in q["question"]


def test_idc_no_working_interest_capitalizes():
    """Explicitly False -> not IDC-eligible: capitalize_no_working_interest
    even when the §263(c) election is on; AmortizableItem with
    recovery_months=None (recovery follows the property)."""
    out = compute_idc([_idc(operator_or_working_interest=False)],
                      expense_election=True)
    row = out["items"][0]
    assert row["treatment"] == "capitalize_no_working_interest"
    assert out["capitalized_total"] == Decimal("100000")
    [item] = out["amortizable_items"]
    assert item.recovery_months is None
    assert "1.612-4(a)" in item.authority
    assert out["open_questions"] == []


# --- step 3: foreign wells (§263(i)) -------------------------------------------

def test_idc_foreign_10yr_election_month_known_full_month():
    """Foreign + ten_year_election_263i, month_incurred=4: 120-month
    AmortizableItem, full-month convention with the start month noted.
    Year-1 (full-month) = 120,000 × 12/120 = 12,000. No current expensing
    even though expense_election=True (§263(i))."""
    out = compute_idc([_idc(amount="120000", foreign=True,
                            ten_year_election_263i=True, month_incurred=4)],
                      expense_election=True)
    row = out["items"][0]
    assert row["treatment"] == "capitalize_263i_10yr"
    assert out["deductible_total"] == Decimal("0")
    assert out["capitalized_total"] == Decimal("120000")
    [item] = out["amortizable_items"]
    assert item.recovery_months == 120
    assert item.convention == "full-month"
    assert "month 4" in item.notes
    assert item.first_year_amortization() == Decimal("12000")
    assert "MONTH-UNKNOWN-MIDYEAR-PROXY" not in item.flags


def test_idc_foreign_10yr_election_month_unknown_midyear_proxy():
    """month_incurred=0 -> mid-year proxy + MONTH-UNKNOWN-MIDYEAR-PROXY.
    Year-1 = 120,000 × 12/120 / 2 = 6,000."""
    out = compute_idc([_idc(amount="120000", foreign=True,
                            ten_year_election_263i=True)],
                      expense_election=True)
    [item] = out["amortizable_items"]
    assert item.convention == "mid-year"
    assert "MONTH-UNKNOWN-MIDYEAR-PROXY" in item.flags
    assert "MONTH-UNKNOWN-MIDYEAR-PROXY" in out["items"][0]["flags"]
    assert item.first_year_amortization() == Decimal("6000")


def test_idc_foreign_no_263i_election_capitalized_to_basis():
    """Foreign, ten_year_election_263i False: capitalized to depletable/
    depreciable basis (recovery_months=None) with both the
    RECOVERY-VIA-DEPLETION-OUT-OF-SCOPE and
    COST-DEPLETION-ALTERNATIVE-NOT-MODELED flags — §263(i) bars expensing
    regardless of expense_election=True."""
    out = compute_idc([_idc(foreign=True)], expense_election=True)
    row = out["items"][0]
    assert row["treatment"] == "capitalize_263i"
    assert "RECOVERY-VIA-DEPLETION-OUT-OF-SCOPE" in row["flags"]
    assert "COST-DEPLETION-ALTERNATIVE-NOT-MODELED" in row["flags"]
    assert out["capitalized_total"] == Decimal("100000")
    [item] = out["amortizable_items"]
    assert item.recovery_months is None
    assert "263(i)(2)(A)" in item.authority


# --- step 4: domestic — §263(c) election posture --------------------------------

def test_idc_domestic_election_unknown_asks_once_and_capitalizes():
    """expense_election None: conservative capitalize + IDC-ELECTION-UNKNOWN;
    the (run-level, binding) election question is emitted ONCE across items."""
    out = compute_idc([_idc("W1"), _idc("W2", amount="40000")])
    assert all(r["treatment"] == "open_question_capitalize_pending"
               for r in out["items"])
    assert all("IDC-ELECTION-UNKNOWN" in r["flags"] for r in out["items"])
    assert out["capitalized_total"] == Decimal("140000")
    assert out["amortizable_items"] == []
    assert len(out["open_questions"]) == 1
    q = out["open_questions"][0]
    assert "§263(c)" in q["question"] and "expense_election" in q["question"]
    assert "first return" in q["question"]


def test_idc_domestic_expensed_non_integrated():
    """expense_election True, not integrated: full deduction under §263(c)."""
    out = compute_idc([_idc()], expense_election=True)
    row = out["items"][0]
    assert row["treatment"] == "idc_expensed_263c"
    assert row["deductible"] == Decimal("100000")
    assert out["deductible_total"] == Decimal("100000")
    assert out["capitalized_total"] == Decimal("0")
    assert out["amortizable_items"] == []


def test_idc_integrated_cutback_penny_split_100_01():
    """§291(b)(1) 30/70 penny split on 100.01: 30% = 30.003 -> half-even to
    30.00 capitalized; 70% side is the plug: 100.01 - 30.00 = 70.01 —
    sides sum exactly to the amount. Month known (7) -> full-month 60-month
    AmortizableItem; year-1 = 30.00 × 12/60 = 6.00."""
    out = compute_idc([_idc(amount="100.01", month_incurred=7)],
                      is_integrated_producer=True, expense_election=True)
    row = out["items"][0]
    assert row["treatment"] == "idc_expensed_263c_291b_cutback"
    assert row["capitalized"] == Decimal("30.00")
    assert row["deductible"] == Decimal("70.01")
    assert row["capitalized"] + row["deductible"] == Decimal("100.01")
    [item] = out["amortizable_items"]
    assert item.basis == Decimal("30.00")
    assert item.recovery_months == 60
    assert item.convention == "full-month"
    assert "month 7" in item.notes
    assert item.first_year_amortization() == Decimal("6.00")


def test_idc_integrated_cutback_month_unknown_midyear_proxy():
    """Cutback with no month data: mid-year proxy + flag. 100,000 ->
    30,000 capitalized / 70,000 deducted; year-1 = 30,000 × 12/60 / 2 =
    3,000."""
    out = compute_idc([_idc()], is_integrated_producer=True,
                      expense_election=True)
    assert out["capitalized_total"] == Decimal("30000.00")
    assert out["deductible_total"] == Decimal("70000.00")
    [item] = out["amortizable_items"]
    assert item.convention == "mid-year"
    assert "MONTH-UNKNOWN-MIDYEAR-PROXY" in item.flags
    assert item.first_year_amortization() == Decimal("3000")


def test_idc_domestic_no_election_capitalized_depletion_flag():
    """expense_election False: capitalize (recovery via depletion —
    out-of-scope flag), AmortizableItem recovery_months=None."""
    out = compute_idc([_idc()], expense_election=False)
    row = out["items"][0]
    assert row["treatment"] == "capitalize_no_election"
    assert "RECOVERY-VIA-DEPLETION-OUT-OF-SCOPE" in row["flags"]
    assert out["capitalized_total"] == Decimal("100000")
    [item] = out["amortizable_items"]
    assert item.recovery_months is None


# --- step 5: dry hole (Reg. §1.612-4(b)(4)) -------------------------------------

def test_idc_dry_hole_deductible_under_capitalize_posture():
    """nonproductive_well under expense_election=False: the dry-hole
    election still permits deduction — DRY-HOLE-DEDUCTIBLE flag per item;
    the confirm-the-posture warning fires ONCE for two dry holes."""
    out = compute_idc([_idc("W1", nonproductive_well=True),
                       _idc("W2", amount="55000", nonproductive_well=True)],
                      expense_election=False)
    assert all(r["treatment"] == "dry_hole_deduct" for r in out["items"])
    assert all("DRY-HOLE-DEDUCTIBLE" in r["flags"] for r in out["items"])
    assert out["deductible_total"] == Decimal("155000")
    assert out["capitalized_total"] == Decimal("0")
    assert sum(1 for w in out["warnings"]
               if "DRY-HOLE-ELECTION-CONFIRM" in w) == 1


def test_idc_dry_hole_moot_under_expensing():
    """Under expense_election=True the dry hole is moot — plain §263(c)
    deduction, no dry-hole flag or warning."""
    out = compute_idc([_idc(nonproductive_well=True)], expense_election=True)
    row = out["items"][0]
    assert row["treatment"] == "idc_expensed_263c"
    assert "DRY-HOLE-DEDUCTIBLE" not in row["flags"]
    assert not any("DRY-HOLE" in w for w in out["warnings"])


def test_idc_integrated_dry_hole_cutback_warns_exception_not_modeled():
    """Integrated + expensing + nonproductive well: the cutback is applied
    uniformly (spec) and 291B-NONPRODUCTIVE-EXCEPTION-NOT-MODELED warns
    that §291(b)(1)(A) excepts dry-hole IDC — SME review; once per run."""
    out = compute_idc([_idc("W1", nonproductive_well=True),
                       _idc("W2", nonproductive_well=True)],
                      is_integrated_producer=True, expense_election=True)
    assert all(r["treatment"] == "idc_expensed_263c_291b_cutback"
               for r in out["items"])
    assert sum(1 for w in out["warnings"]
               if "291B-NONPRODUCTIVE-EXCEPTION-NOT-MODELED" in w) == 1


def test_idc_totals_tie_mixed_batch():
    """Mixed batch tie: deductible_total + capitalized_total == sum of all
    non-sme_review amounts. Batch: 100.01 integrated-expensed (30.00 cap /
    70.01 ded), 50,000 foreign-no-election (cap), 20,000 no-working-interest
    (cap), -5 (excluded). Deductible 70.01; capitalized 30.00 + 50,000 +
    20,000 = 70,030.00; sum of computables 70,100.01."""
    items = [_idc("A", amount="100.01"),
             _idc("B", amount="50000", foreign=True),
             _idc("C", amount="20000", operator_or_working_interest=False),
             _idc("D", amount="-5")]
    out = compute_idc(items, is_integrated_producer=True,
                      expense_election=True)
    assert out["deductible_total"] == Decimal("70.01")
    assert out["capitalized_total"] == Decimal("70030.00")
    computable = sum(it.amount for it in items if it.amount >= 0)
    assert out["deductible_total"] + out["capitalized_total"] == computable


# =============================== MINING ======================================

def test_mining_negative_amount_sme_review():
    out = compute_mining([_mine(amount="-1")])
    assert out["items"][0]["treatment"] == "sme_review"
    assert "NEGATIVE-AMOUNT" in out["items"][0]["flags"]
    assert out["deductible_total"] == Decimal("0")
    assert out["capitalized_total"] == Decimal("0")


def test_mining_foreign_honest_stub():
    """foreign True: §617(h)/§616(d) not implemented — sme_review +
    FOREIGN-MINING-NOT-IMPLEMENTED, nothing computed (both kinds)."""
    out = compute_mining([_mine("M1", kind="development", foreign=True),
                          _mine("M2", kind="exploration", foreign=True,
                                expense_election_617=True)])
    assert all(r["treatment"] == "sme_review" for r in out["items"])
    assert all("FOREIGN-MINING-NOT-IMPLEMENTED" in r["flags"]
               for r in out["items"])
    assert sum(1 for w in out["warnings"]
               if "FOREIGN-MINING-NOT-IMPLEMENTED" in w) == 2
    assert out["deductible_total"] == Decimal("0")
    assert out["capitalized_total"] == Decimal("0")
    assert out["amortizable_items"] == []


def test_mining_unknown_kind_guard():
    out = compute_mining([_mine(kind="reclamation")])
    assert out["items"][0]["treatment"] == "sme_review"
    assert "MINING-KIND-UNKNOWN" in out["items"][0]["flags"]
    assert any("MINING-KIND-UNKNOWN" in w for w in out["warnings"])


def test_mining_development_default_deduct_no_election_needed():
    """§616(a) development: DEFAULT current deduction — no election field
    consulted; non-corporate -> no cutback."""
    out = compute_mining([_mine(amount="80000")])
    row = out["items"][0]
    assert row["treatment"] == "development_deducted_616a"
    assert "§616(a)" in row["authority"]
    assert out["deductible_total"] == Decimal("80000")
    assert out["amortizable_items"] == []


def test_mining_616b_deferral_units_not_modeled():
    """§616(b) deferral: AmortizableItem with recovery_months=None, flag
    616B-UNITS-OF-PRODUCTION-NOT-MODELED, and an open question asking for
    the units schedule. No cutback (nothing deducted) even if corporate."""
    out = compute_mining([_mine(defer_election_616b=True)],
                         is_corporate=True)
    row = out["items"][0]
    assert row["treatment"] == "capitalize_616b_deferred"
    assert "616B-UNITS-OF-PRODUCTION-NOT-MODELED" in row["flags"]
    assert out["capitalized_total"] == Decimal("80000")
    assert out["deductible_total"] == Decimal("0")
    [item] = out["amortizable_items"]
    assert item.recovery_months is None
    assert "616B-UNITS-OF-PRODUCTION-NOT-MODELED" in item.flags
    [q] = out["open_questions"]
    assert "units" in q["question"]


def test_mining_exploration_617_elected_recapture_warned_once():
    """§617(a) elected: deduct; 617B-RECAPTURE-NOT-COMPUTED fires ONCE for
    the run across two elected items."""
    out = compute_mining([_mine("E1", kind="exploration", amount="30000",
                                expense_election_617=True),
                          _mine("E2", kind="exploration", amount="20000",
                                expense_election_617=True)])
    assert all(r["treatment"] == "exploration_deducted_617a"
               for r in out["items"])
    assert out["deductible_total"] == Decimal("50000")
    assert sum(1 for w in out["warnings"]
               if "617B-RECAPTURE-NOT-COMPUTED" in w) == 1


def test_mining_exploration_617_false_capitalizes():
    out = compute_mining([_mine(kind="exploration",
                                expense_election_617=False)])
    row = out["items"][0]
    assert row["treatment"] == "capitalize_no_election_617"
    assert "RECOVERY-VIA-DEPLETION-OUT-OF-SCOPE" in row["flags"]
    assert out["capitalized_total"] == Decimal("80000")
    [item] = out["amortizable_items"]
    assert item.recovery_months is None


def test_mining_exploration_617_none_asks_once_and_capitalizes():
    """expense_election_617 None: conservative capitalize +
    617-ELECTION-UNKNOWN; the election question is emitted ONCE across
    items (dedup)."""
    out = compute_mining([_mine("E1", kind="exploration"),
                          _mine("E2", kind="exploration", amount="10000")])
    assert all(r["treatment"] == "open_question_capitalize_pending"
               for r in out["items"])
    assert all("617-ELECTION-UNKNOWN" in r["flags"] for r in out["items"])
    assert out["capitalized_total"] == Decimal("90000")
    assert out["amortizable_items"] == []
    assert len(out["open_questions"]) == 1
    assert "expense_election_617" in out["open_questions"][0]["question"]


def test_mining_corporate_cutback_both_kinds_penny_split():
    """§291(b)(1) corporate cutback hits BOTH §616(a) development and
    §617(a)-elected exploration. 100.01 each: 30.00 capitalized / 70.01
    deducted per item; the 60-month schedule uses the mid-year proxy
    (mining carries no month data). Totals: deductible 140.02, capitalized
    60.00."""
    out = compute_mining([_mine("D1", amount="100.01"),
                          _mine("E1", kind="exploration", amount="100.01",
                                expense_election_617=True)],
                         is_corporate=True)
    assert out["items"][0]["treatment"] == "development_deducted_616a_291b_cutback"
    assert out["items"][1]["treatment"] == "exploration_deducted_617a_291b_cutback"
    for row in out["items"]:
        assert row["capitalized"] == Decimal("30.00")
        assert row["deductible"] == Decimal("70.01")
    assert out["deductible_total"] == Decimal("140.02")
    assert out["capitalized_total"] == Decimal("60.00")
    assert len(out["amortizable_items"]) == 2
    for item in out["amortizable_items"]:
        assert item.recovery_months == 60
        assert item.convention == "mid-year"
        assert "MONTH-UNKNOWN-MIDYEAR-PROXY" in item.flags
        # 30.00 × 12/60 / 2 = 3.00 year-1 under the mid-year proxy
        assert item.first_year_amortization() == Decimal("3.00")


def test_mining_noncorporate_no_cutback():
    out = compute_mining([_mine(amount="100.01")], is_corporate=False)
    assert out["items"][0]["treatment"] == "development_deducted_616a"
    assert out["deductible_total"] == Decimal("100.01")
    assert out["capitalized_total"] == Decimal("0")


def test_mining_totals_tie_mixed_batch():
    """Corporate batch tie: development 50,000 (15,000 cap / 35,000 ded),
    617-None exploration 10,000 (cap), 616(b) 20,000 (cap), foreign 9,999
    (sme_review, excluded), negative (excluded). deductible 35,000;
    capitalized 15,000 + 10,000 + 20,000 = 45,000; computable sum 80,000."""
    items = [_mine("D1", amount="50000"),
             _mine("E1", kind="exploration", amount="10000"),
             _mine("D2", amount="20000", defer_election_616b=True),
             _mine("F1", amount="9999", foreign=True),
             _mine("N1", amount="-3")]
    out = compute_mining(items, is_corporate=True)
    assert out["deductible_total"] == Decimal("35000.00")
    assert out["capitalized_total"] == Decimal("45000.00")
    computable = sum(r["amount"] for r in out["items"]
                     if r["treatment"] != "sme_review")
    assert out["deductible_total"] + out["capitalized_total"] == computable


# =============================== CIRCULATION =================================

def test_circulation_default_deduct_with_59e_note_once():
    """§173 default deduct; the CIRCULATION-59E-ALTERNATIVE informational
    warning (pointing to the §59(e) engine) fires ONCE across two items."""
    out = compute_circulation([_circ("C1"), _circ("C2", amount="5000")])
    assert all(r["treatment"] == "circulation_deducted_173"
               for r in out["items"])
    assert out["deductible_total"] == Decimal("30000")
    assert out["capitalized_total"] == Decimal("0")
    assert out["amortizable_items"] == []
    fiftynine = [w for w in out["warnings"]
                 if "CIRCULATION-59E-ALTERNATIVE" in w]
    assert len(fiftynine) == 1
    assert "compute_59e" in fiftynine[0]


def test_circulation_capitalize_election():
    """Reg. §1.173-1(c) election: capitalize with recovery_months=None +
    CIRCULATION-RECOVERY-SME; the §59(e) note still fires (BOTH branches)."""
    out = compute_circulation([_circ()], capitalize_election=True)
    row = out["items"][0]
    assert row["treatment"] == "capitalize_173_election"
    assert "CIRCULATION-RECOVERY-SME" in row["flags"]
    assert out["capitalized_total"] == Decimal("25000")
    assert out["deductible_total"] == Decimal("0")
    [item] = out["amortizable_items"]
    assert item.recovery_months is None
    assert "CIRCULATION-RECOVERY-SME" in item.flags
    assert sum(1 for w in out["warnings"]
               if "CIRCULATION-59E-ALTERNATIVE" in w) == 1


def test_circulation_negative_and_empty_run():
    """Negative -> sme_review, nothing computed; an empty run emits no
    warnings at all (the §59(e) note fires only when an item computes)."""
    out = compute_circulation([CirculationItem(item_id="N1",
                                               amount=Decimal("-10"))])
    assert out["items"][0]["treatment"] == "sme_review"
    assert not any("CIRCULATION-59E-ALTERNATIVE" in w
                   for w in out["warnings"])
    assert compute_circulation([])["warnings"] == []
