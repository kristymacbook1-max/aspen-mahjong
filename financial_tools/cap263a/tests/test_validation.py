"""Accuracy regression floor — classification quality can't silently degrade."""

from financial_tools.cap263a.validation.validate import accuracy_report
from financial_tools.cap263a import classify


def test_accuracy_floor():
    r = accuracy_report()
    # current: raw ~66%, +defensible ~71%, high-conf precision ~72%, review ~28%
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
