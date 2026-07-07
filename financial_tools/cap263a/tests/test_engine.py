"""Golden classification set + cost-center-context regression tests."""

import pytest
from financial_tools.cap263a import classify

# (acct_desc, cc_desc, expected_code, expected_tier1)
GOLDEN = [
    ("Factory depreciation", "Plant 1", "FO-DEP", "§471 Cost"),
    ("Direct labor", "Production Dept", "DL-PROD", "§471 Cost"),
    ("Warehouse storage and handling", "Distribution Center", "RES-HANDLING", "Additional §263A"),
    ("Purchasing department salaries", "Procurement", "PP-PURCH", "Additional §263A"),
    ("Advertising expense", "Marketing", "EX-MKT", "Excluded"),
    ("Research and development", "R&D Lab", "EX-RD", "Excluded"),
    ("Sales revenue", "", "REV-OPER", "Revenue"),
    ("Accounts receivable", "", "BS-ASSET", "Balance Sheet"),
    # --- tax fixes ---
    ("Officer compensation", "Executive", "NO-OFFICER", "Mixed Service"),
    ("Construction period interest", "Plant Construction", "NO-INTCAP", "§263A(f) Interest"),
    ("Property taxes", "Land held for development", "SEC266-TAX", "§266 Carrying Charges"),
    # --- cost-center reclassification (same account, different department) ---
    ("Rent expense", "Corporate HQ", "MSC-CORPRENT", "Mixed Service"),
    ("Rent expense", "Manufacturing Plant", "FO-RENT", "§471 Cost"),
    ("Utilities", "Corporate HQ", "MSC-CORPUTIL", "Mixed Service"),
    ("Utilities", "Manufacturing Plant", "FO-UTIL", "§471 Cost"),
]


@pytest.mark.parametrize("acct,cc,code,tier1", GOLDEN)
def test_golden(acct, cc, code, tier1):
    r = classify(acct_desc=acct, cc_desc=cc)
    assert r.code == code, f"{acct}/{cc}: got {r.code} ({r.tier1})"
    assert r.tier1 == tier1


def test_repairs_depends_on_department():
    """The doc's central example: same account, three departments."""
    prod = classify(acct_desc="Repairs and maintenance", cc_desc="Manufacturing Plant")
    sales = classify(acct_desc="Repairs and maintenance", cc_desc="Sales Office")
    assert prod.tier1 == "§471 Cost"          # production overhead
    assert sales.tier1 in ("Excluded", "Mixed Service")


def test_variance_is_suspense_not_capitalized():
    # Must NOT become direct labor just because it sits in a production CC.
    r = classify(acct_desc="Cost allocation variance", cc_desc="Production")
    assert r.tier1 == "Mixed Service"
    assert "REVIEW" in r.flags


def test_deterministic():
    a = classify(acct_desc="Factory rent", cc_desc="Plant")
    b = classify(acct_desc="Factory rent", cc_desc="Plant")
    assert (a.code, a.confidence, a.flags) == (b.code, b.confidence, b.flags)


def test_treatment_columns_present():
    r = classify(acct_desc="Direct labor", cc_desc="Production")
    assert set(r.treatment) == {"mspm", "resale", "self_const", "interest"}


# --- regression: word-boundary keyword/clue/zone matching ---
# A raw substring `in` check let short keywords ("it", "hr") match inside
# unrelated words ("credit", "capital", "waiting"), silently mis-zoning or
# mis-classifying ordinary cost centers/accounts.

def test_cost_center_substring_false_positives_fixed():
    for cc in ("Capital Projects", "Credit Department", "Waiting Room"):
        r = classify(acct_desc="Rent expense", cc_desc=cc)
        assert r.code != "MSC-IT", f"{cc!r} falsely zoned as corporate IT"
        assert r.tier1 != "Mixed Service" or r.code != "MSC-CORPRENT" or "it" not in cc.lower()


def test_it_department_still_zones_as_corporate():
    """The word-boundary fix must not break the real "IT" cost-center case —
    the abbreviation expander turns "IT" into "information technology" before
    zone detection ever runs, so cc_zones.yaml needs that expanded phrase too."""
    r = classify(acct_desc="Software license", cc_desc="IT Department")
    assert r.code == "MSC-IT"
    assert r.tier1 == "Mixed Service"


def test_401k_contribution_is_not_charitable():
    """NO-CHARITY's bare "contribution"/"donation"/"gift" keywords used to
    swallow ordinary payroll benefit lines. Must resolve to a benefits code,
    never Non-Operating charitable."""
    r = classify(acct_desc="401k employer contribution", cc_desc="Manufacturing Plant")
    assert r.code != "NO-CHARITY"
    assert r.tier1 != "Non-Operating"


def test_401k_parens_shorthand_still_matches_the_keyword():
    """"401(k)" (the standard way payroll GLs spell it) was silently mangled
    to "401 " by the generic parenthetical-content stripper, losing the
    "401k" keyword entirely and falling through to NO-CHARITY via a
    zero-score tie-break on the bare "contribution" word."""
    r = classify(acct_desc="401(k) employer match contribution", cc_desc="Manufacturing Plant")
    assert r.code != "NO-CHARITY"
    assert r.tier1 != "Non-Operating"

    r2 = classify(acct_desc="403(b) plan contribution", cc_desc="Corporate HQ")
    assert r2.code != "NO-CHARITY"
    assert r2.tier1 != "Non-Operating"

    r2 = classify(acct_desc="Pension plan contribution expense", cc_desc="Corporate HQ")
    assert r2.code != "NO-CHARITY"
    assert r2.tier1 != "Non-Operating"


def test_generic_freight_and_commission_reclass_by_zone():
    """GEN-FRT/GEN-COMM used to never reclass by cost-center zone — a bare
    "freight"/"commission" line landed as flat Mixed Service everywhere,
    regardless of whether it was a sales, production, or R&D cost center."""
    r = classify(acct_desc="Commission expense", cc_desc="Sales")
    assert r.code == "EX-SALES"
    r = classify(acct_desc="Freight", cc_desc="Manufacturing Plant")
    assert r.code == "DM-FRT"
    r = classify(acct_desc="Freight", cc_desc="R&D Lab")
    assert r.code == "EX-RD"


def test_zone_only_reclass_is_calibrated_not_overconfident():
    """A cc-reclass driven purely by zone/clue context (no direct account
    keyword hit) must be capped and flagged, not reported as a confident,
    unflagged 70+ match — otherwise the review queue is meaningless."""
    r = classify(acct_desc="Depreciation expense", cc_desc="Manufacturing Plant")
    assert "CC-RECLASSED" in r.flags
    assert r.confidence < 70
    assert "LOW-CONF" in r.flags or "REVIEW" in r.flags


def test_phrase_level_lexicon_no_longer_corrupts_text():
    """Word-by-word substitution let 2-letter abbreviation keys that are also
    real words ("or"->operating room, "oh"->overhead, "pr"->payroll) corrupt
    ordinary descriptions and state abbreviations, and made every multi-word
    lexicon key silently dead. Phrase-level replacement + pruning fixes both."""
    # Ohio is not the corporate zone
    r = classify(acct_desc="Depreciation expense", cc_desc="Machine Shop - Toledo OH")
    assert r.code != "MSC-CORPDEP"
    # PR firm retainer is not payroll
    r = classify(acct_desc="PR agency retainer", cc_desc="Marketing")
    assert r.code != "GEN-COMP"
    # a communications/PR department is not production labor
    r = classify(acct_desc="Salaries", cc_desc="Press Office")
    assert r.tier1 != "§471 Cost"
    # revived multi-word cc synonym: inventory management is a warehouse function
    r = classify(acct_desc="Rent", cc_desc="Inventory Management")
    assert r.tier1 == "Additional §263A"


def test_hyphenated_abbreviations_expand():
    """"Deprec-Mfg equip" tokenized as one word, so deprec/mfg never expanded
    and the line missed FO-DEP entirely."""
    r = classify(acct_desc="Deprec-Mfg equip", cc_desc="Production - Plant 1")
    assert r.code == "FO-DEP"
    assert r.tier1 == "§471 Cost"


def test_construction_loan_interest_reaches_263af_layer():
    """"Interest expense - construction loan" classified as plain Non-Operating
    interest at conf 85 — the immune-tier bonus outvoted the §263A(f) keyword,
    so the interest-capitalization layer never saw the line."""
    r = classify(acct_desc="Interest expense - construction loan", cc_desc="Land Holdings")
    assert r.code == "NO-INTCAP"
    assert r.tier1 == "§263A(f) Interest"
    # plain interest expense is untouched
    r2 = classify(acct_desc="Interest expense", cc_desc="Corporate")
    assert r2.tier1 == "Non-Operating"


def test_inventory_charges_stay_in_waterfall_but_balances_do_not():
    """Re-tiering INV-BOOK to Balance Sheet initially swallowed IS-side
    inventory CHARGES (adjustment/variance/write-off/shrinkage) — costs
    silently vanished from the waterfall at conf 85. Charge-event language
    routes to NEG-263A (Additional §263A, negative-adjustment scaffold),
    whose explicit keywords suppress the balance-sheet immune bonus; pure
    balances stay Balance Sheet."""
    charges = [("Inventory adjustment", "Warehouse"), ("WIP variance", "Production"),
               ("Finished goods write-off", "Warehouse"), ("Inventory shrinkage", "Warehouse"),
               ("Inventory obsolescence charge", "Corporate")]
    for desc, cc in charges:
        r = classify(acct_desc=desc, cc_desc=cc)
        assert r.tier1 not in ("Balance Sheet", "Revenue"), f"{desc} dropped from waterfall"
    balances = [("Inventory - finished goods", "Warehouse"),
                ("Raw materials inventory", "Plant"), ("Inventory", "")]
    for desc, cc in balances:
        r = classify(acct_desc=desc, cc_desc=cc)
        assert r.tier1 == "Balance Sheet", f"{desc} should be a balance-sheet line"


def test_balance_sheet_asset_and_contra_lines():
    """From the end-to-end audit: M&E balances were pulled into §471 labor by
    cost-center clues; book-inventory balances were treated as current-period
    §471 cost; contra-revenue landed as deductible expense; purchase discounts
    became production labor."""
    r = classify(acct_desc="Machinery & equipment", cc_desc="Production - Plant 1")
    assert r.tier1 == "Balance Sheet"
    r = classify(acct_desc="Inventory - finished goods", cc_desc="Warehouse")
    assert r.tier1 == "Balance Sheet"
    r = classify(acct_desc="Sales returns and allowances", cc_desc="Sales")
    assert r.tier1 == "Revenue"
    r = classify(acct_desc="Purchase discounts", cc_desc="Purchasing")
    assert r.code == "DM-RAW"       # §471 contra (credit) line stays in the pool


def test_bare_generic_keywords_no_longer_drop_costs_from_the_analysis():
    """BS-ASSET/REV-OPER bare single-word keywords ("land", "investment",
    "goodwill", "revenue") used to match plain expense lines and route them
    to Balance-Sheet/Revenue tiers, which are excluded from every waterfall
    bucket entirely — silently vanishing the cost, not just mis-bucketing it."""
    r = classify(acct_desc="Cost of Revenue - Materials")
    assert r.tier1 not in ("Revenue",)
    r = classify(acct_desc="Marketing Investment Expense")
    assert r.tier1 not in ("Balance Sheet",)
    r = classify(acct_desc="Goodwill Amortization")
    assert r.code == "SEC263A-INTANG"   # capitalizable, not a dropped BS line
    assert r.tier1 != "Balance Sheet"


def test_zero_signal_code_cannot_win_on_priority_alone():
    """A code with zero real signal (no keyword/clue/zone/fuzzy hit) could
    still "win" purely because a nonnegative `priority` default outscored
    every other candidate's negative-priority generic fallback — reachable
    whenever a single word from a multi-word keyword phrase (e.g.
    "contribution" from NO-CHARITY's "charitable contribution") pulls a code
    into the candidate pool without it ever actually phrase-matching. Such a
    zero-evidence pick must fall back to VAGUE-OTHER, not a specific
    (and here, wrong) tier1 like Non-Operating."""
    r = classify(acct_desc="401(k) employer match contribution", cc_desc="")
    assert r.code != "NO-CHARITY"
    assert r.tier1 != "Non-Operating"
