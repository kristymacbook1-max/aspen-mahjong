"""§1060/Form 8594 residual-method purchase price allocation (BUILD_PLAN.md
Phase G addition).

Reg. §1.1060-1(c), borrowing the §338 regs' waterfall (§1.338-6(b)):
aggregate consideration allocates to Classes I→VI in order, each class
capped at its aggregate FMV; Class VII (goodwill/going-concern value) is the
residual — whatever remains after I-VI, ≥ 0 by construction. When remaining
consideration is insufficient for a class, §1.338-6(b) allocates WITHIN that
class in proportion to the assets' FMVs (this schedule carries one aggregate
FMV per class, so the whole remainder allocates to the short class — the
per-asset proportional split happens downstream on the class's asset detail)
and later classes take zero; that shortfall means consideration is below the
sum of Class I-VI FMVs — a data/valuation red flag, not a silent outcome
(CONSIDERATION-BELOW-CLASS-FMV).

Each class's allocation is the SEED basis for the downstream engines
(inventory pools for Class IV, FixedAsset/SCA for Class V, §197/intangibles
for Classes VI-VII) — this mechanic sets basis; it does not amortize.
Both buyer and seller must report the allocation consistently on Form 8594.
"""

from decimal import Decimal
from typing import Dict, List

from ..model import PurchasePriceAllocation

CLASS_ORDER = ["I", "II", "III", "IV", "V", "VI"]


def compute_1060_allocation(ppa: PurchasePriceAllocation) -> dict:
    """Returns {by_class, class_vii_residual, warnings}. by_class covers
    "I".."VII"; classes absent from ppa.class_fmv are treated as FMV 0."""
    warnings: List[str] = []
    by_class: Dict[str, Decimal] = {}
    consideration = ppa.aggregate_consideration

    if consideration < 0:
        warnings.append(
            f"NEGATIVE-CONSIDERATION [{ppa.transaction_id}]: aggregate "
            f"consideration ${consideration:,.2f} is negative — no "
            f"allocation computed; correct the input.")
        return {"by_class": {}, "class_vii_residual": Decimal("0"),
                "warnings": warnings}

    unknown = sorted(set(ppa.class_fmv) - set(CLASS_ORDER))
    if unknown:
        warnings.append(
            f"UNKNOWN-CLASS-KEYS [{ppa.transaction_id}]: {unknown} ignored — "
            f"class_fmv keys must be 'I'..'VI' (Class VII is the residual, "
            f"never an input).")

    remaining = consideration
    shortfall_hit = False
    for cls in CLASS_ORDER:
        fmv = ppa.class_fmv.get(cls, Decimal("0"))
        if shortfall_hit:
            by_class[cls] = Decimal("0")
            continue
        if remaining >= fmv:
            by_class[cls] = fmv
            remaining -= fmv
        else:
            # Consideration exhausted mid-waterfall: the short class takes
            # the whole remainder (proportional-to-FMV within the class per
            # §1.338-6(b) — trivial at this aggregate-per-class granularity),
            # every later class takes zero.
            by_class[cls] = remaining
            remaining = Decimal("0")
            shortfall_hit = True
            warnings.append(
                f"CONSIDERATION-BELOW-CLASS-FMV [{ppa.transaction_id}]: "
                f"consideration exhausted within Class {cls} (FMV "
                f"${fmv:,.2f}, only ${by_class[cls]:,.2f} available) — "
                f"allocated proportionally to FMV within the class per "
                f"§1.338-6(b), zero to later classes; consideration below "
                f"the sum of Class I-VI FMVs signals a data or valuation "
                f"error.")

    # Class VII (goodwill/going concern) = the residual, ≥ 0 by construction.
    by_class["VII"] = remaining
    return {"by_class": by_class, "class_vii_residual": remaining,
            "warnings": warnings}
