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
