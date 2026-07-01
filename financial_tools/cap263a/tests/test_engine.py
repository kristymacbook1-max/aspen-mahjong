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
