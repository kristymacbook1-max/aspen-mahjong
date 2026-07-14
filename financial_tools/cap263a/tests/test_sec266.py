"""§266 elective capitalization of taxes and carrying charges
(Reg. §1.266-1) — every treatment branch, the otherwise-deductible gate
(True/False/None), election granularity (property_id set vs True), each
category gate in both directions, run-level warnings, open-question
emission/dedup, and the three-way totals tie. Golden figures hand-computed
in each docstring."""

from decimal import Decimal

from financial_tools.cap263a.engines.sec266 import (
    CarryingChargeItem, compute_266)

ALL = {"unimproved_real": True, "real_development": True,
       "personal_property": True}


def _cc(item_id="T1", amount="12000", category="unimproved_real", **kw):
    """A carrying charge that survives to capitalization by default:
    otherwise deductible, unproductive unimproved real property."""
    kw.setdefault("otherwise_deductible", True)
    kw.setdefault("charge_type", "tax")
    if category == "unimproved_real":
        kw.setdefault("property_unproductive", True)
    return CarryingChargeItem(item_id=item_id, description=item_id,
                              amount=Decimal(amount), category=category, **kw)


# --- step 1: negative guard ---------------------------------------------------

def test_negative_amount_sme_review_excluded_from_all_totals():
    out = compute_266([_cc(amount="-100")], elections=ALL)
    row = out["items"][0]
    assert row["treatment"] == "sme_review"
    assert "NEGATIVE-AMOUNT" in row["flags"]
    assert any("NEGATIVE-AMOUNT [§266 T1]" in w for w in out["warnings"])
    assert out["capitalized_total"] == Decimal("0")
    assert out["deductible_total"] == Decimal("0")
    assert out["not_booked_total"] == Decimal("0")


# --- step 2: category guard ---------------------------------------------------

def test_unknown_category_not_booked():
    out = compute_266([CarryingChargeItem(item_id="X1", amount=Decimal("500"),
                                          category="inventory",
                                          otherwise_deductible=True)],
                      elections=ALL)
    assert out["items"][0]["treatment"] == "sme_review"
    assert "266-CATEGORY-UNKNOWN" in out["items"][0]["flags"]
    assert any("266-CATEGORY-UNKNOWN" in w for w in out["warnings"])
    assert out["not_booked_total"] == Decimal("500")


# --- step 3: otherwise-deductible gate (Reg. §1.266-1(a)(1)) -------------------

def test_not_otherwise_deductible_nothing_to_capitalize():
    """otherwise_deductible False -> not_deductible_no_266: the item is
    simply nondeductible; nothing capitalized even though fully elected."""
    out = compute_266([_cc(otherwise_deductible=False)], elections=ALL)
    row = out["items"][0]
    assert row["treatment"] == "not_deductible_no_266"
    assert "266-NOT-OTHERWISE-DEDUCTIBLE" in row["flags"]
    assert out["capitalized_total"] == Decimal("0")
    assert out["deductible_total"] == Decimal("0")
    assert out["not_booked_total"] == Decimal("12000")
    assert out["amortizable_items"] == []


def test_deductibility_unknown_refuses_and_asks():
    """otherwise_deductible None -> sme_review + 266-DEDUCTIBILITY-UNKNOWN,
    nothing booked to either side; the open question names the §163(j)/SALT
    examples. Two items with the same id/description dedup to one question;
    a distinct item gets its own."""
    items = [_cc("I1", otherwise_deductible=None, charge_type="interest"),
             _cc("I1", otherwise_deductible=None, charge_type="interest"),
             _cc("I2", amount="800", otherwise_deductible=None)]
    out = compute_266(items, elections=ALL)
    assert all(r["treatment"] == "sme_review" for r in out["items"])
    assert all("266-DEDUCTIBILITY-UNKNOWN" in r["flags"]
               for r in out["items"])
    assert out["not_booked_total"] == Decimal("24800")
    assert len(out["open_questions"]) == 2
    q = out["open_questions"][0]["question"]
    assert "otherwise_deductible" in q
    assert "§163(j)" in q and "SALT" in q


# --- step 4: election coverage --------------------------------------------------

def test_no_election_deducts():
    out = compute_266([_cc()], elections={})
    assert out["items"][0]["treatment"] == "deduct_no_election"
    assert out["deductible_total"] == Decimal("12000")
    assert out["capitalized_total"] == Decimal("0")


def test_election_granularity_property_id_set_vs_true():
    """A property_id set covers only its members; True covers everything.
    P1 (in set) capitalizes, P2 (not in set) deducts; under True both
    would capitalize — shown by the P3 item under a True election."""
    items = [_cc("A", property_id="P1"), _cc("B", property_id="P2"),
             _cc("C", property_id="P3")]
    out = compute_266(items[:2],
                      elections={"unimproved_real": {"P1"}})
    assert out["items"][0]["treatment"] == "capitalize_266"
    assert out["items"][1]["treatment"] == "deduct_no_election"
    out_all = compute_266([items[2]],
                          elections={"unimproved_real": True})
    assert out_all["items"][0]["treatment"] == "capitalize_266"


def test_election_for_other_category_does_not_cover():
    """A real_development election does not reach an unimproved_real item."""
    out = compute_266([_cc()], elections={"real_development": True})
    assert out["items"][0]["treatment"] == "deduct_no_election"


# --- step 5: category gates ------------------------------------------------------

def test_unimproved_real_productive_property_deducts_with_warning():
    """(b)(1)(i) requires unimproved AND unproductive: productive property
    (False) deducts with the 266-PRODUCTIVE-PROPERTY warning."""
    out = compute_266([_cc(property_unproductive=False)], elections=ALL)
    row = out["items"][0]
    assert row["treatment"] == "deduct_productive_property"
    assert out["deductible_total"] == Decimal("12000")
    assert any("266-PRODUCTIVE-PROPERTY" in w for w in out["warnings"])


def test_unimproved_real_productive_status_unknown_asks_not_capitalized():
    """property_unproductive None: open question + NOT capitalized — the
    (already otherwise-deductible) charge stays on the deduct side with
    flag 266-PRODUCTIVE-STATUS-UNKNOWN."""
    out = compute_266([_cc(property_unproductive=None)], elections=ALL)
    row = out["items"][0]
    assert row["treatment"] == "deduct_productive_status_unknown"
    assert "266-PRODUCTIVE-STATUS-UNKNOWN" in row["flags"]
    assert out["deductible_total"] == Decimal("12000")
    assert out["capitalized_total"] == Decimal("0")
    [q] = out["open_questions"]
    assert "property_unproductive" in q["question"]
    assert "UNPRODUCTIVE" in q["question"]


def test_real_development_window_both_directions():
    """development_complete True -> deduct_post_completion (outside the
    (b)(1)(ii) window); False -> capitalize_266."""
    out = compute_266([_cc("R1", category="real_development",
                           development_complete=True),
                       _cc("R2", amount="9000", category="real_development")],
                      elections=ALL)
    assert out["items"][0]["treatment"] == "deduct_post_completion"
    assert out["items"][1]["treatment"] == "capitalize_266"
    assert out["deductible_total"] == Decimal("12000")
    assert out["capitalized_total"] == Decimal("9000")


def test_personal_property_installation_both_directions():
    """installed_or_first_used True -> deduct_post_installation ((b)(1)(iii)
    runs until installation/first use); False -> capitalize_266."""
    out = compute_266([_cc("P1", category="personal_property",
                           installed_or_first_used=True),
                       _cc("P2", amount="4000",
                           category="personal_property")],
                      elections=ALL)
    assert out["items"][0]["treatment"] == "deduct_post_installation"
    assert out["items"][1]["treatment"] == "capitalize_266"
    assert out["capitalized_total"] == Decimal("4000")


# --- step 6: capitalization + run-level warnings ----------------------------------

def test_capitalize_266_amortizable_record():
    """Survivor: capitalize_266 with an AmortizableItem — basis=amount,
    recovery_months=None (attaches to the property's basis), authority
    Reg. §1.266-1(b); unimproved_real maps to the model's 'land' category."""
    out = compute_266([_cc(property_id="LOT-9")], elections=ALL)
    row = out["items"][0]
    assert row["treatment"] == "capitalize_266"
    assert row["authority"] == "Reg. §1.266-1(b)"
    assert out["capitalized_total"] == Decimal("12000")
    [item] = out["amortizable_items"]
    assert item.basis == Decimal("12000")
    assert item.recovery_months is None
    assert item.authority == "Reg. §1.266-1(b)"
    assert item.category == "land"
    assert "LOT-9" in item.notes


def test_statement_and_annual_warnings_once_each():
    """Any active election -> 266-STATEMENT-REQUIRED (original return,
    §1.266-1(c)(3)); an unimproved_real election additionally draws
    266-ANNUAL-ELECTION — each once per run across multiple items."""
    out = compute_266([_cc("A"), _cc("B", amount="700")], elections=ALL)
    assert sum(1 for w in out["warnings"]
               if "266-STATEMENT-REQUIRED" in w) == 1
    assert "ORIGINAL return" in next(w for w in out["warnings"]
                                     if "266-STATEMENT-REQUIRED" in w)
    assert sum(1 for w in out["warnings"]
               if "266-ANNUAL-ELECTION" in w) == 1


def test_annual_warning_only_for_unimproved_real_election():
    """A real_development-only election: statement warning yes, annual
    ((b)(1)(i)) warning no. No election at all: neither."""
    out = compute_266([_cc("R1", category="real_development")],
                      elections={"real_development": True})
    assert any("266-STATEMENT-REQUIRED" in w for w in out["warnings"])
    assert not any("266-ANNUAL-ELECTION" in w for w in out["warnings"])
    out_none = compute_266([_cc()], elections={})
    assert not any("266-STATEMENT-REQUIRED" in w
                   for w in out_none["warnings"])


def test_263af_ordering_warning_only_when_interest_capitalized():
    """Capitalized INTEREST draws 266-263AF-ORDERING (§263A(f) designated-
    property interest cannot be overridden; DOUBLE-COUNT-RECONCILE
    posture); a tax-only capitalization does not, nor does interest that
    was merely deducted (no election)."""
    interest = CarryingChargeItem(
        item_id="I1", description="construction loan interest",
        amount=Decimal("30000"), charge_type="interest",
        category="real_development", otherwise_deductible=True)
    out = compute_266([interest], elections={"real_development": True})
    [w] = [w for w in out["warnings"] if "266-263AF-ORDERING" in w]
    assert "§263A(f)" in w and "DOUBLE-COUNT-RECONCILE" in w
    out_tax = compute_266([_cc()], elections=ALL)
    assert not any("266-263AF-ORDERING" in w for w in out_tax["warnings"])
    out_ded = compute_266([interest], elections={})
    assert not any("266-263AF-ORDERING" in w for w in out_ded["warnings"])


# --- totals tie --------------------------------------------------------------------

def test_totals_tie_three_way():
    """capitalized + deductible + not_booked == sum of non-negative amounts.
    Batch: 12,000 capitalized; 5,000 deduct_no_election (P2 outside the
    set); 3,000 not otherwise deductible (not booked); 2,000 deductibility
    unknown (not booked); -50 excluded. 12,000 + 5,000 + 5,000 = 22,000."""
    items = [_cc("A", property_id="P1"),
             _cc("B", amount="5000", property_id="P2"),
             _cc("C", amount="3000", property_id="P1",
                 otherwise_deductible=False),
             _cc("D", amount="2000", property_id="P1",
                 otherwise_deductible=None),
             _cc("E", amount="-50", property_id="P1")]
    out = compute_266(items, elections={"unimproved_real": {"P1"}})
    assert out["capitalized_total"] == Decimal("12000")
    assert out["deductible_total"] == Decimal("5000")
    assert out["not_booked_total"] == Decimal("5000")
    computable = sum(it.amount for it in items if it.amount >= 0)
    assert (out["capitalized_total"] + out["deductible_total"]
            + out["not_booked_total"]) == computable
