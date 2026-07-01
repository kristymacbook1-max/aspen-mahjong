"""Capitalization analysis — carries dollars through the layered hierarchy.

Each IS trial-balance line is classified, then assigned to exactly one waterfall
bucket, so the Summary Dashboard ties by construction:
    starting IS total = Σ(capitalized buckets) + mixed + deductible.

Layers (legal order): §263(a) mandatory/elective → §263A (§471 + additional) →
§263A(f) interest → §266. Mixed-service costs are held separately pending the
§263A allocation (Phase 3). The entity profile gates safe harbors.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

from .engine import classify
from .taxonomy import get_taxonomy
from .model import TBLine, Classification


@dataclass
class EntityProfile:
    entity_name: str = ""
    entity_type: str = "c_corp"            # c_corp/s_corp/partnership/sole_prop
    tax_year: int = 2026
    avg_gross_receipts: Decimal = Decimal("0")   # 3-yr avg (§448(c))
    has_afs: bool = True                   # de minimis $5,000 vs $2,500
    industry: str = ""
    produces: bool = True                  # §263A producer
    acquires_for_resale: bool = False

    THRESHOLDS = {2024: Decimal("30000000"), 2025: Decimal("31000000"),
                  2026: Decimal("32000000")}

    def __post_init__(self):
        self.avg_gross_receipts = Decimal(str(self.avg_gross_receipts or 0))

    @property
    def sec448_threshold(self) -> Decimal:
        return self.THRESHOLDS.get(self.tax_year, Decimal("32000000"))

    @property
    def small_business_exempt(self) -> bool:
        return self.avg_gross_receipts <= self.sec448_threshold

    @property
    def de_minimis_ceiling(self) -> Decimal:
        return Decimal("5000") if self.has_afs else Decimal("2500")


# Waterfall buckets (order = presentation order)
BUCKETS = ["Inventory §471", "§263A Additional", "§263(a) Mandatory",
           "§263(a) Elective", "§263A(f) Interest", "§266 Carrying",
           "Mixed (allocable)", "Deductible", "Non-Operating"]
CAPITALIZED_BUCKETS = ["Inventory §471", "§263A Additional", "§263(a) Mandatory",
                       "§263(a) Elective", "§263A(f) Interest", "§266 Carrying"]
_NON_IS_TIERS = {"Balance Sheet", "Revenue"}


def bucket_of(cl: Classification, profile: EntityProfile) -> str:
    t = cl.tier1
    if t == "§471 Cost":
        # small-business exception turns off UNICAP -> these stay COGS/deductible
        return "Deductible" if profile.small_business_exempt else "Inventory §471"
    if t in ("Additional §263A", "Capitalizable (MSPM)"):
        return "Deductible" if profile.small_business_exempt else "§263A Additional"
    if t == "§263(a) Tangible":
        if cl.cap_vs_deduct == "capitalize":
            return "§263(a) Mandatory"
        if cl.cap_vs_deduct == "elective":
            return "§263(a) Elective"
        return "Deductible"
    if t == "§263(a) Transaction/Intangible":
        return "§263(a) Mandatory"
    if t == "§263A(f) Interest":
        return "§263A(f) Interest"
    if t == "§266 Carrying Charges":
        return "§266 Carrying"
    if t == "Mixed Service":
        return "Deductible" if profile.small_business_exempt else "Mixed (allocable)"
    if t == "Non-Operating":
        return "Non-Operating"
    return "Deductible"           # Excluded


@dataclass
class ClassifiedLine:
    line: TBLine
    cls: Classification
    bucket: str
    is_income_statement: bool


def analyze(lines: List[TBLine], profile: Optional[EntityProfile] = None) -> dict:
    profile = profile or EntityProfile()
    tax = get_taxonomy()
    rows: List[ClassifiedLine] = []
    totals = {b: Decimal("0") for b in BUCKETS}
    is_total = Decimal("0")

    for ln in lines:
        cl = classify(acct_num=ln.acct_num, acct_desc=ln.acct_desc,
                      cc_num=ln.cc_num, cc_desc=ln.cc_desc, tax=tax)
        is_is = cl.tier1 not in _NON_IS_TIERS
        ln.statement_type = "IS" if is_is else "BS"
        bucket = bucket_of(cl, profile) if is_is else ""
        if is_is:
            totals[bucket] += ln.amount
            is_total += ln.amount
        rows.append(ClassifiedLine(ln, cl, bucket, is_is))

    capitalized = sum((totals[b] for b in CAPITALIZED_BUCKETS), Decimal("0"))
    mixed = totals["Mixed (allocable)"]
    deductible = totals["Deductible"] + totals["Non-Operating"]

    return {
        "profile": profile,
        "rows": rows,
        "bucket_totals": totals,
        "is_total": is_total,
        "capitalized_total": capitalized,
        "mixed_total": mixed,
        "deductible_total": deductible,
        "review_count": sum(1 for r in rows if r.cls.review),
        "tie_check": is_total - (capitalized + mixed + deductible),
    }
