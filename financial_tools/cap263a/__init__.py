"""§263A / §263(a) / §266 capitalization tool (rebuilt).

Single authoritative Python engine over a data-driven taxonomy. Replaces the
original tool's four divergent engine implementations and seven taxonomy copies.

    from financial_tools.cap263a import classify, get_taxonomy, read_trial_balance
    c = classify(acct_desc="Factory depreciation", cc_desc="Plant 1")
    print(c.code, c.tier1, c.treatment, c.confidence)
"""

from .taxonomy import get_taxonomy, Taxonomy, TaxonomyError
from .engine import classify, detect_cc_zone, normalize
from .reader import read_trial_balance
from .model import TBLine, Classification

__all__ = [
    "get_taxonomy", "Taxonomy", "TaxonomyError",
    "classify", "detect_cc_zone", "normalize",
    "read_trial_balance", "TBLine", "Classification",
]
