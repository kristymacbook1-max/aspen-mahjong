"""Cost Capitalization Analyzer — §266 / §263(a) / §263A.

Consumes a department / cost-center based trial balance and computes
capitalization under the required and elective provisions of IRC §266, §263(a),
and §263A (UNICAP), supporting BOTH account-level provision tagging AND
cost-center allocation overlays, reconciled against each other.

The analyzer computes the figures in Python (for the results dict and the
example output); the Excel report layers live in-cell formulas on top of the
same inputs so the workbook also functions as a reusable annual template.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional, Dict
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from revenue_recognition.utils.currency_helpers import (
    to_decimal, round_currency, format_currency,
)


# ---------------------------------------------------------------------------
# Provision constants
# ---------------------------------------------------------------------------

# Account-level provision tags
PROV_DEDUCTIBLE = "deductible"
PROV_266 = "266"
PROV_263A_ACQ = "263(a)"
PROV_263A = "263A"
PROV_MIXED = "mixed"
PROV_OTHER = "other_cap"

PROVISION_TAGS = [
    PROV_DEDUCTIBLE, PROV_266, PROV_263A_ACQ, PROV_263A, PROV_MIXED, PROV_OTHER,
]

# Capitalization buckets that allocation percentages map to
CAP_BUCKETS = [PROV_266, PROV_263A_ACQ, PROV_263A, PROV_DEDUCTIBLE]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CostCenter:
    """A department / cost center on the trial balance."""
    code: str
    name: str
    type: str = "mixed"          # production / service / resale / g&a / mixed
    is_263a_subject: bool = True  # production / resale activity subject to UNICAP


@dataclass
class TrialBalanceLine:
    """A single department-tagged trial balance line."""
    account_number: str
    account_name: str
    cost_center_code: str
    amount: Decimal = Decimal("0")
    book_category: str = ""           # cogs / labor / overhead / interest / taxes / sga ...
    provision: str = PROV_DEDUCTIBLE  # one of PROVISION_TAGS
    other_cap_section: str = ""       # for provision == other_cap: e.g. "174A", "197", "195"
    notes: str = ""

    def __post_init__(self):
        self.amount = to_decimal(self.amount)


@dataclass
class AllocationOverlay:
    """Per cost-center allocation of mixed spend across provisions (percent, 0-100)."""
    cost_center_code: str
    pct_266: Decimal = Decimal("0")
    pct_263a_acq: Decimal = Decimal("0")
    pct_263A: Decimal = Decimal("0")
    pct_deductible: Decimal = Decimal("0")

    def __post_init__(self):
        self.pct_266 = to_decimal(self.pct_266)
        self.pct_263a_acq = to_decimal(self.pct_263a_acq)
        self.pct_263A = to_decimal(self.pct_263A)
        self.pct_deductible = to_decimal(self.pct_deductible)

    @property
    def total_pct(self) -> Decimal:
        return self.pct_266 + self.pct_263a_acq + self.pct_263A + self.pct_deductible

    def fraction(self, bucket: str) -> Decimal:
        mapping = {
            PROV_266: self.pct_266,
            PROV_263A_ACQ: self.pct_263a_acq,
            PROV_263A: self.pct_263A,
            PROV_DEDUCTIBLE: self.pct_deductible,
        }
        return mapping.get(bucket, Decimal("0")) / Decimal("100")


@dataclass
class Section263AInputs:
    """UNICAP computation inputs (simplified methods + §263A(f) interest)."""
    method: str = "simplified_production"  # simplified_production / modified_simplified /
                                           # simplified_resale / simplified_service_cost /
                                           # facts_and_circumstances
    section_471_costs: Decimal = Decimal("0")          # current-year §471 costs incurred
    additional_263a_costs: Decimal = Decimal("0")      # current-year additional §263A costs
    ending_inventory_471: Decimal = Decimal("0")       # §471 costs in ending inventory
    beginning_inventory_471: Decimal = Decimal("0")
    # Reseller (SRM) split
    storage_handling_costs: Decimal = Decimal("0")
    purchasing_costs: Decimal = Decimal("0")
    # §263A(f) interest capitalization
    accumulated_production_expenditures: Decimal = Decimal("0")
    avoided_cost_rate: Decimal = Decimal("0")          # decimal, e.g. 0.06
    designated_property: bool = False

    def __post_init__(self):
        for f in ("section_471_costs", "additional_263a_costs", "ending_inventory_471",
                  "beginning_inventory_471", "storage_handling_costs", "purchasing_costs",
                  "accumulated_production_expenditures", "avoided_cost_rate"):
            setattr(self, f, to_decimal(getattr(self, f)))


@dataclass
class Section266Election:
    """Elective §266 carrying-charge capitalization flags (Reg §1.266-1)."""
    unimproved_real_property: bool = False   # (b)(1)(i) — annual election
    development_real_property: bool = False  # (b)(1)(ii) — project-period election
    personal_property: bool = False          # (b)(1)(iii) — to install / first use
    commissioner_catchall: bool = False      # (b)(1)(iv)/(b)(2)
    notes: str = ""


@dataclass
class Section263aElection:
    """§263(a) safe-harbor / election flags."""
    de_minimis_safe_harbor: bool = False     # §1.263(a)-1(f)
    has_afs: bool = False                    # drives $5,000 vs $2,500 ceiling
    small_taxpayer_safe_harbor: bool = False  # §1.263(a)-3(h)
    routine_maintenance: bool = False        # §1.263(a)-3(i)
    capitalize_repairs_election: bool = False  # §1.263(a)-3(n)
    success_fee_70_safe_harbor: bool = False  # Rev. Proc. 2011-29
    notes: str = ""

    @property
    def de_minimis_ceiling(self) -> Decimal:
        return Decimal("5000") if self.has_afs else Decimal("2500")


@dataclass
class SmallBusinessTest:
    """§448(c) gross-receipts test driving the §263A(i)/§471(c) exemption."""
    tax_year: int = 2026
    avg_annual_gross_receipts: Decimal = Decimal("0")  # 3-year average
    is_tax_shelter: bool = False

    # Verified inflation-adjusted thresholds (Rev. Procs. 2023-34/2024-40/2025-32)
    THRESHOLDS = {2024: Decimal("30000000"),
                  2025: Decimal("31000000"),
                  2026: Decimal("32000000")}

    def __post_init__(self):
        self.avg_annual_gross_receipts = to_decimal(self.avg_annual_gross_receipts)

    @property
    def threshold(self) -> Decimal:
        return self.THRESHOLDS.get(self.tax_year, Decimal("32000000"))

    @property
    def exempt(self) -> bool:
        """True if §263A/§471 small-business exception applies (UNICAP switched off)."""
        if self.is_tax_shelter:
            return False
        return self.avg_annual_gross_receipts <= self.threshold


@dataclass
class CostCapitalizationInput:
    """Full input bundle for a cost capitalization engagement."""
    company_name: str
    tax_year: int = 2026
    entity_type: str = "c_corp"
    cost_centers: List[CostCenter] = field(default_factory=list)
    trial_balance: List[TrialBalanceLine] = field(default_factory=list)
    allocations: List[AllocationOverlay] = field(default_factory=list)
    section_263a: Section263AInputs = field(default_factory=Section263AInputs)
    section_266: Section266Election = field(default_factory=Section266Election)
    section_263a_elections: Section263aElection = field(default_factory=Section263aElection)
    small_business: SmallBusinessTest = field(default_factory=SmallBusinessTest)


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class CostCapitalizationAnalyzer:
    """Computes capitalization by provision using both methods, then reconciles."""

    def analyze(self, inp: CostCapitalizationInput) -> dict:
        alloc_by_cc = {a.cost_center_code: a for a in inp.allocations}

        # ---- Account-level (tagging) method, with mixed split by allocation ----
        tagged = {b: Decimal("0") for b in CAP_BUCKETS}
        other_cap_total = Decimal("0")
        other_cap_by_section: Dict[str, Decimal] = {}
        per_line = []

        for line in inp.trial_balance:
            buckets = {b: Decimal("0") for b in CAP_BUCKETS}
            other = Decimal("0")
            if line.provision in (PROV_266, PROV_263A_ACQ, PROV_263A, PROV_DEDUCTIBLE):
                buckets[line.provision] = line.amount
            elif line.provision == PROV_MIXED:
                overlay = alloc_by_cc.get(line.cost_center_code)
                if overlay:
                    for b in CAP_BUCKETS:
                        buckets[b] = round_currency(line.amount * overlay.fraction(b))
                else:
                    buckets[PROV_DEDUCTIBLE] = line.amount
            elif line.provision == PROV_OTHER:
                other = line.amount
                sec = line.other_cap_section or "other"
                other_cap_by_section[sec] = other_cap_by_section.get(sec, Decimal("0")) + other

            for b in CAP_BUCKETS:
                tagged[b] += buckets[b]
            other_cap_total += other
            per_line.append({"line": line, "buckets": buckets, "other_cap": other})

        # ---- Allocation-overlay method (allocate each CC's total spend) ----
        cc_totals: Dict[str, Decimal] = {}
        for line in inp.trial_balance:
            cc_totals[line.cost_center_code] = (
                cc_totals.get(line.cost_center_code, Decimal("0")) + line.amount
            )
        overlay_totals = {b: Decimal("0") for b in CAP_BUCKETS}
        for cc_code, total in cc_totals.items():
            overlay = alloc_by_cc.get(cc_code)
            if overlay and overlay.total_pct > 0:
                for b in CAP_BUCKETS:
                    overlay_totals[b] += round_currency(total * overlay.fraction(b))
            else:
                overlay_totals[PROV_DEDUCTIBLE] += total

        # ---- Reconciliation between the two methods ----
        reconciliation = {
            b: {
                "account_tag": tagged[b],
                "allocation_overlay": overlay_totals[b],
                "variance": round_currency(tagged[b] - overlay_totals[b]),
            }
            for b in CAP_BUCKETS
        }

        # ---- §263A UNICAP absorption-ratio computation ----
        unicap = self._compute_263a(inp.section_263a, inp.small_business)

        # ---- Allocation checksums (flag cost centers whose % != 100) ----
        alloc_checks = [
            {
                "cost_center_code": a.cost_center_code,
                "total_pct": a.total_pct,
                "ok": a.total_pct == Decimal("100") or a.total_pct == Decimal("0"),
            }
            for a in inp.allocations
        ]

        total_tb = sum((l.amount for l in inp.trial_balance), Decimal("0"))
        total_capitalized = tagged[PROV_266] + tagged[PROV_263A_ACQ] + tagged[PROV_263A] + other_cap_total

        return {
            "company_name": inp.company_name,
            "tax_year": inp.tax_year,
            "entity_type": inp.entity_type,
            "tagged": tagged,
            "other_cap_total": other_cap_total,
            "other_cap_by_section": other_cap_by_section,
            "overlay_totals": overlay_totals,
            "reconciliation": reconciliation,
            "unicap": unicap,
            "allocation_checks": alloc_checks,
            "cc_totals": cc_totals,
            "per_line": per_line,
            "total_trial_balance": total_tb,
            "total_capitalized": total_capitalized,
            "total_deductible": tagged[PROV_DEDUCTIBLE],
            "small_business_exempt": inp.small_business.exempt,
            "_input": inp,
        }

    # ------------------------------------------------------------------
    def _compute_263a(self, s: Section263AInputs, sb: SmallBusinessTest) -> dict:
        """Absorption ratio + capitalizable add-on to ending inventory."""
        result = {
            "method": s.method,
            "exempt": sb.exempt,
            "section_471_costs": s.section_471_costs,
            "additional_263a_costs": s.additional_263a_costs,
            "ending_inventory_471": s.ending_inventory_471,
        }
        if sb.exempt:
            result.update({
                "absorption_ratio": Decimal("0"),
                "additional_263a_capitalized": Decimal("0"),
                "note": "§263A(i)/§471(c) small-business exception applies — UNICAP not required.",
            })
            return result

        if s.method == "simplified_resale":
            denom = s.section_471_costs
            ratio = (s.storage_handling_costs + s.purchasing_costs) / denom if denom else Decimal("0")
        else:  # simplified_production / modified_simplified / others use add'l / §471
            denom = s.section_471_costs
            ratio = s.additional_263a_costs / denom if denom else Decimal("0")

        capitalized = round_currency(s.ending_inventory_471 * ratio)
        result.update({
            "absorption_ratio": ratio,
            "additional_263a_capitalized": capitalized,
            "interest_capitalized": round_currency(
                s.accumulated_production_expenditures * s.avoided_cost_rate
            ) if s.designated_property else Decimal("0"),
        })
        return result
