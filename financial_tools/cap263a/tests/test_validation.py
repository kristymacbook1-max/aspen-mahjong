"""Accuracy regression floor — classification quality can't silently degrade."""

from financial_tools.cap263a.validation.validate import accuracy_report
from financial_tools.cap263a import classify


def test_accuracy_floor():
    r = accuracy_report()
    # current: raw ~68.8%, +defensible ~72.8%, high-conf precision ~77.4%, review ~38%
    assert r["raw_agreement"] >= 0.63, f"raw agreement regressed to {r['raw_agreement']:.1%}"
    assert r["high_conf_precision"] >= 0.68, \
        f"high-conf precision regressed to {r['high_conf_precision']:.1%}"
    # a meaningful review queue must exist (calibration): not everything is 'high'
    assert 0.15 <= r["review_rate"] <= 0.45, f"review rate off: {r['review_rate']:.0%}"


def test_validation_fixes_locked():
    # cases the validation pass fixed — lock them as regressions
    cases = [
        ("Frt out", "Shipping", "Excluded"),                       # outbound freight
        ("Deprec-Mfg equipment", "Manufacturing", "§471 Cost"),    # messy abbreviation
        ("Accounts receivable - trade", "Finance & Accounting", "Balance Sheet"),
        ("Accounts payable - trade", "Finance & Accounting", "Balance Sheet"),
        ("Accumulated depreciation", "Finance", "Balance Sheet"),  # immune-tier recognition
    ]
    for acct, cc, tier1 in cases:
        assert classify(acct_desc=acct, cc_desc=cc).tier1 == tier1, f"{acct}/{cc}"


def test_defensible_exemptions_are_data_driven():
    """The +defensible carve-out must come from explicit per-line labels in
    validation_set.json (acceptable_alt_tier1 + alt_reason), not from keyword
    heuristics in code — so every exemption is a reviewable, diffable decision
    on a specific line and new rows can't silently pick up exemptions."""
    import json, os
    from financial_tools.cap263a.validation import validate as v
    with open(v._DATA) as fh:
        data = json.load(fh)
    stamped = [d for d in data if "acceptable_alt_tier1" in d]
    assert stamped, "expected explicit defensible labels in validation_set.json"
    for d in stamped:
        assert d.get("alt_reason"), f"{d['acct_desc']}: labeled defensible without a reason"
        assert d["acceptable_alt_tier1"] != d["expected_tier1"], \
            f"{d['acct_desc']}: alt tier1 must differ from expected"
