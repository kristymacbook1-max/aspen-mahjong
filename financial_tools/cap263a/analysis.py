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
    # §263A UNICAP inputs (Phase 3)
    method: str = "SPM"                    # SPM / MSPM / SRM
    ending_inventory_471: Decimal = Decimal("0")   # §471 costs in ending inventory
    mixed_alloc_ratio: Optional[Decimal] = None    # SSCM ratio; None -> labor-based
    # §263A(f) interest inputs (Phase 4)
    accumulated_production_expenditures: Decimal = Decimal("0")
    avoided_cost_rate: Decimal = Decimal("0")
    has_designated_property: bool = False

    THRESHOLDS = {2024: Decimal("30000000"), 2025: Decimal("31000000"),
                  2026: Decimal("32000000")}
    # Reg §1.263A-1(d)(3)(ii)(C) (T.D. 9843): a producer with 3-yr average
    # gross receipts over $50M may not include negative adjustments in
    # additional §263A costs under the SPM (MSPM required).
    LARGE_PRODUCER_THRESHOLD = Decimal("50000000")

    def __post_init__(self):
        self.avg_gross_receipts = Decimal(str(self.avg_gross_receipts or 0))
        self.ending_inventory_471 = Decimal(str(self.ending_inventory_471 or 0))
        self.accumulated_production_expenditures = Decimal(str(self.accumulated_production_expenditures or 0))
        self.avoided_cost_rate = Decimal(str(self.avoided_cost_rate or 0))
        if self.mixed_alloc_ratio is not None:
            self.mixed_alloc_ratio = Decimal(str(self.mixed_alloc_ratio))

    @property
    def sec448_threshold(self) -> Decimal:
        return self.THRESHOLDS.get(self.tax_year, Decimal("32000000"))

    @property
    def sec448_threshold_is_estimate(self) -> bool:
        """True when tax_year has no published figure in THRESHOLDS — the 2026
        amount is used as a stand-in and must be verified (the threshold is
        inflation-indexed; a stale figure can flip the small-business
        exemption, which turns UNICAP entirely on or off)."""
        return self.tax_year not in self.THRESHOLDS

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
        # §263A(i)/§448(c) exempts from ALL of §263A, including (f) interest.
        # (§263(a) mandatory and §266 are NOT §263A provisions — no gate there.)
        return "Deductible" if profile.small_business_exempt else "§263A(f) Interest"
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
    """Classify + bucket every line, compute totals and UNICAP.

    Note: sets `statement_type` on the INPUT TBLine objects (idempotent, but a
    visible side effect on caller data — pass copies if that matters)."""
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

    # Capitalization is an addition to basis; a NEGATIVE capitalized bucket
    # (contra/reversal lines net below zero) is economically invalid and must
    # be surfaced. The compute_unicap guard only saw the §263A pools; catch the
    # §263(a) / §266 / §263A(f) buckets and the aggregate here too.
    bucket_warnings = []
    for b in CAPITALIZED_BUCKETS:
        if totals[b] < 0:
            bucket_warnings.append(
                f"NEGATIVE '{b}' BUCKET (${totals[b]:,.0f}): capitalization cannot be "
                f"negative — contra/reversal lines classified here need review.")
    if capitalized < 0:
        bucket_warnings.append(
            f"TOTAL CAPITALIZED IS NEGATIVE (${capitalized:,.0f}) — the workbook would "
            f"show a negative addition to basis. Review the contributing lines.")

    result = {
        "profile": profile,
        "rows": rows,
        "bucket_totals": totals,
        "is_total": is_total,
        "capitalized_total": capitalized,
        "mixed_total": mixed,
        "deductible_total": deductible,
        "review_count": sum(1 for r in rows if r.cls.review),
        "flagged_count": sum(1 for r in rows if r.cls.flags),
        "bucket_warnings": bucket_warnings,
        # NOTE: partition invariant, NOT a reconciliation. Every IS line is
        # assigned to exactly one bucket, so this is 0 by construction — it
        # catches a bucketing/refactor bug, it does NOT validate that any line
        # is classified correctly. (The Summary's live tie row, which reacts to
        # analyst Cap% overrides, is the meaningful check.)
        "tie_check": is_total - (capitalized + mixed + deductible),
    }
    result["unicap"] = compute_unicap(result, profile)
    return result


def _q(x):
    return x.quantize(Decimal("0.01"))


def compute_unicap(result: dict, profile: EntityProfile) -> dict:
    """§263A UNICAP: SSCM mixed-service allocation + SPM absorption ratio.

    Mixed-service costs are split into a capitalizable share (labor-based SSCM
    ratio, unless overridden) that joins the additional §263A pool, and a
    deductible remainder. The simplified production method then computes the
    absorption ratio (additional §263A ÷ §471) and the additional §263A cost
    capitalized to ending inventory.
    """
    if profile.small_business_exempt:
        w = []
        if profile.sec448_threshold_is_estimate:
            w.append(f"§448(c) threshold for TY {profile.tax_year} is not on file — the "
                     f"2026 figure (${profile.sec448_threshold:,.0f}) was used to determine "
                     f"the exemption. VERIFY: a higher indexed threshold cannot change this "
                     f"result, but relying on it should be documented.")
        return {"exempt": True, "note": "§263A(i)/§448(c) small-business exception — UNICAP off.",
                "warnings": w,
                "mixed_capitalized": Decimal("0"), "mixed_deductible": result["mixed_total"],
                "absorption_ratio": Decimal("0"), "additional_capitalized_to_inventory": Decimal("0")}

    rows = result["rows"]
    # Reg §1.263A-1(h): the SSCM labor ratio is capitalizable production labor
    # over total UNICAP-relevant labor (production + mixed-service), NOT total
    # enterprise labor. Sales/R&D/other Excluded-tier compensation is never part
    # of that base and must not dilute the denominator.
    UNICAP_LABOR_TIERS = ("§471 Cost", "Mixed Service")
    prod_labor = sum((r.line.amount for r in rows
                      if r.cls.is_labor and r.cls.tier1 == "§471 Cost"), Decimal("0"))
    total_labor = sum((r.line.amount for r in rows
                       if r.cls.is_labor and r.cls.tier1 in UNICAP_LABOR_TIERS), Decimal("0"))
    ratio_warn = None
    if profile.mixed_alloc_ratio is not None:
        ratio = profile.mixed_alloc_ratio
        if not (Decimal("0") <= ratio <= Decimal("1")):
            ratio_warn = (f"SSCM ALLOCATION RATIO OVERRIDE = {ratio} is outside [0,1] — a "
                          f"service-cost allocation ratio is a fraction; clamped to "
                          f"[0,1] for the computation. Check the input.")
    else:
        ratio = (prod_labor / total_labor) if total_labor else Decimal("0")
        if not (Decimal("0") <= ratio <= Decimal("1")):
            ratio_warn = (f"SSCM LABOR RATIO = {ratio.quantize(Decimal('0.0001'))} is outside "
                          f"[0,1] (production labor {prod_labor:,} / UNICAP labor {total_labor:,}) "
                          f"— likely a negative/contra labor line; clamped to [0,1]. Review.")
    # A service-cost allocation ratio is definitionally a fraction; clamp so a
    # bad input can't over- or negatively-capitalize the mixed pool.
    if ratio < 0:
        ratio = Decimal("0")
    elif ratio > 1:
        ratio = Decimal("1")
    ratio = ratio.quantize(Decimal("0.000001"))
    mixed = result["mixed_total"]
    mixed_cap = _q(mixed * ratio)
    mixed_ded = mixed - mixed_cap

    sec471_pool = result["bucket_totals"]["Inventory §471"]
    additional_pool = result["bucket_totals"]["§263A Additional"] + mixed_cap
    absorption = _q(additional_pool / sec471_pool) if sec471_pool else Decimal("0")
    add_to_inv = _q(profile.ending_inventory_471 * absorption)

    warnings_ = []
    if ratio_warn:
        warnings_.append(ratio_warn)
    if profile.method != "SPM":
        warnings_.append(
            f"METHOD: profile.method={profile.method!r} is not implemented — this "
            f"computation is SPM. Do not sign an {profile.method} workpaper off these "
            f"numbers (MSPM/SRM are Phase B of the build plan).")
    # SPM absorption ratio > 1 means the additional §263A pool exceeds the ENTIRE
    # §471 base — almost always a data error (e.g. a tiny §471 pool). Not clamped
    # (rare edge cases exist) but always surfaced.
    if absorption > 1:
        warnings_.append(
            f"ABSORPTION RATIO = {absorption} (>100%): the additional §263A pool "
            f"(${additional_pool:,.0f}) exceeds the entire §471 base (${sec471_pool:,.0f}). "
            f"Verify the §471 classifications — this is almost always a data error.")
    # ending_inventory_471 is a free-typed input; if it dwarfs the §471 pool the
    # capitalized-to-inventory figure is meaningless (the pool is the ceiling on
    # the year's §471 cost).
    if profile.ending_inventory_471 > sec471_pool and sec471_pool > 0:
        warnings_.append(
            f"ENDING §471 INVENTORY (${profile.ending_inventory_471:,.0f}) EXCEEDS THE "
            f"§471 COST POOL (${sec471_pool:,.0f}): the amount capitalized to inventory "
            f"scales off an input inconsistent with the trial balance — verify the "
            f"ending-inventory figure.")
    if additional_pool < 0:
        warnings_.append(
            "NEGATIVE ADDITIONAL §263A POOL: the absorption ratio and the amount "
            "capitalized to ending inventory are negative. Verify the negative "
            "adjustments driving this are permissible in the pool.")
        if profile.method == "SPM" and \
                profile.avg_gross_receipts > profile.LARGE_PRODUCER_THRESHOLD:
            warnings_.append(
                "T.D. 9843 / Reg §1.263A-1(d)(3)(ii)(C): a producer with >$50M "
                "average gross receipts may NOT include negative adjustments in "
                "additional §263A costs under the SPM — use the MSPM.")
    if sec471_pool <= 0 and additional_pool:
        warnings_.append(
            f"§471 POOL IS {'ZERO' if sec471_pool == 0 else 'NEGATIVE'} while the "
            f"additional §263A pool is nonzero — the absorption ratio is not "
            f"meaningful; check classification of §471 lines.")
    if profile.sec448_threshold_is_estimate:
        warnings_.append(
            f"§448(c) threshold for TY {profile.tax_year} is not on file — the 2026 "
            f"figure (${profile.sec448_threshold:,.0f}) was used. The threshold is "
            f"inflation-indexed; VERIFY before relying on the small-business "
            f"exemption determination.")

    return {
        "exempt": False,
        "warnings": warnings_,
        "mixed_alloc_ratio": ratio,
        "production_labor": prod_labor, "total_labor": total_labor,
        "mixed_capitalized": mixed_cap, "mixed_deductible": mixed_ded,
        "sec471_pool": sec471_pool, "additional_263a_pool": additional_pool,
        "absorption_ratio": absorption,
        "ending_inventory_471": profile.ending_inventory_471,
        "additional_capitalized_to_inventory": add_to_inv,
        "adjusted_deductible_post": result["deductible_total"] + mixed_ded,
    }
