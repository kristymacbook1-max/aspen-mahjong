"""Classifier accuracy harness — measurable, repeatable validation.

Runs the classifier over a bundled 250-line labeled trial balance spanning six
industries with deliberately messy GL abbreviations and many same-account-
different-department pairs, then reports tier1 agreement, high-confidence
precision, and the review-queue rate.

    python -m financial_tools.cap263a.validation.validate

`accuracy_report()` is also asserted by the test suite as a regression floor so
classification quality cannot silently degrade.
"""

import json
import os
from decimal import Decimal
from collections import Counter

from ..model import TBLine
from ..analysis import analyze, EntityProfile

_DATA = os.path.join(os.path.dirname(__file__), "validation_set.json")


def _defensible(line_data, got):
    """Documented judgment-call differences that are not classifier errors.

    Data-driven: each validation line that has a defensible alternative carries
    an explicit `acceptable_alt_tier1` + `alt_reason` in validation_set.json.
    (Previously this was a set of keyword heuristics in code — which meant new
    validation rows could silently pick up exemptions nobody decided on, and a
    new permissive branch could inflate the +defensible number with no data
    trail. Now every exemption is a reviewable, diffable label on a specific
    line.)"""
    return got == line_data.get("acceptable_alt_tier1")


def accuracy_report(data=None) -> dict:
    if data is None:
        with open(_DATA) as fh:
            data = json.load(fh)
    lines = [TBLine(acct_num=str(d.get("acct_num", "")), acct_desc=d.get("acct_desc", ""),
                    cc_desc=d.get("cc_desc", ""), amount=Decimal(str(d.get("amount", 0))))
             for d in data]
    # large gross receipts so UNICAP is on (matches the labeled expectations)
    rows = analyze(lines, EntityProfile(avg_gross_receipts=Decimal("500000000")))["rows"]
    n = len(data)
    conf = Counter(); correct = Counter(); wrong = Counter()
    raw_ok = defensible = 0
    for d, cr in zip(data, rows):
        et, gt, c = d["expected_tier1"], cr.cls.tier1, cr.cls.confidence
        band = "high" if c >= 70 else "med" if c >= 40 else "low"
        conf[band] += 1
        if gt == et:
            raw_ok += 1; correct[band] += 1
        elif _defensible(d, gt):
            defensible += 1; correct[band] += 1
        else:
            wrong[band] += 1
    hi = conf["high"] or 1
    return {
        "n": n,
        "raw_agreement": raw_ok / n,
        "agreement_incl_defensible": (raw_ok + defensible) / n,
        "defensible": defensible,
        "high_conf_precision": correct["high"] / hi,
        "high_conf_errors": wrong["high"],
        "review_rate": (conf["med"] + conf["low"]) / n,
        "confidence_bands": dict(conf),
    }


def main():
    r = accuracy_report()
    print(f"Validation set: {r['n']} labeled lines "
          f"(messy GL, same-account/different-department pairs)")
    print(f"Tier1 agreement (raw):          {r['raw_agreement']:.1%}")
    print(f"Tier1 agreement (+defensible):  {r['agreement_incl_defensible']:.1%}  "
          f"({r['defensible']} documented judgment diffs)")
    print(f"High-confidence precision:      {r['high_conf_precision']:.1%}  "
          f"({r['high_conf_errors']} high-conf errors)")
    print(f"Review queue (med+low conf):    {r['review_rate']:.0%}")
    print(f"Confidence bands:               {r['confidence_bands']}")


if __name__ == "__main__":
    main()
