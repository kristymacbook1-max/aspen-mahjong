"""Core data model for the §263A/§263(a)/§266/§174/§59(e) capitalization tool."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional, List, Dict


def _dec(v) -> Decimal:
    """Coerce any money-ish input to Decimal (None -> 0).

    bool is rejected by name (a JSON `true` in a money field crashed with a
    bare InvalidOperation) and non-finite values are rejected outright — a
    NaN silently poisons every total AND defeats the tie-check, so it must
    never enter a schedule (red-team findings, both confirmed)."""
    if isinstance(v, Decimal):
        d = v
    elif v is None:
        return Decimal("0")
    elif isinstance(v, bool):
        raise TypeError(f"expected a dollar amount, got bool {v!r}")
    else:
        try:
            d = Decimal(str(v))
        except Exception:
            raise ValueError(f"not a dollar amount: {v!r}")
    if not d.is_finite():
        raise ValueError(f"non-finite dollar amount rejected: {v!r}")
    # A finite-but-absurd magnitude (1e400) passes is_finite() yet becomes
    # float('inf') at the report layer, where openpyxl writes an EMPTY
    # numeric cell — silently blanking the figure AND every total it feeds;
    # with a recovery period it instead crashes quantize() and kills the
    # whole workbook (red-team round 3, both confirmed). No legitimate
    # engagement has a quadrillion-dollar line item.
    if abs(d) > Decimal("1e15"):
        raise ValueError(f"implausible dollar magnitude rejected: {v!r}")
    return d


@dataclass
class TBLine:
    """A department/cost-center trial-balance line (dollars carried through)."""
    acct_num: str = ""
    acct_desc: str = ""
    cc_num: str = ""
    cc_desc: str = ""
    amount: Decimal = Decimal("0")
    statement_type: str = ""     # "IS" / "BS" (set during classification)
    row_index: int = 0

    def __post_init__(self):
        # reader.py always hands a Decimal, but any other constructor (tests,
        # future readers, direct API use) could pass None/float/str/int and
        # fail confusingly deep inside analyze()'s Decimal arithmetic instead
        # of here, at the actual mistake.
        if not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount)) if self.amount is not None else Decimal("0")


@dataclass
class Classification:
    """Result of classifying one TB line."""
    code: str
    tier1: str
    tier2: str = ""
    tier3: str = ""
    treatment: Dict[str, str] = field(default_factory=dict)   # mspm/resale/self_const/interest
    cap_vs_deduct: Optional[str] = None
    allows_negative_adj: bool = False
    designated_property: bool = False
    election_required: bool = False
    is_labor: bool = False
    labor_type: str = ""
    authority: str = ""
    confidence: int = 0
    flags: List[str] = field(default_factory=list)
    method: str = ""             # provenance trail (which rules fired)
    notes: str = ""

    @property
    def review(self) -> bool:
        return "REVIEW" in self.flags or self.confidence < 40


# ---------------------------------------------------------------------------
# Phase A schedules (BUILD_PLAN.md Phase A + Runtime Pipeline).  All money is
# Decimal, all dates are datetime.date, every row keeps row_index/source_sheet
# provenance, mirroring TBLine's conventions.
# ---------------------------------------------------------------------------

@dataclass
class BookTaxDifference:
    """One book-tax difference. `adjustment` is signed TAX-minus-BOOK: applying
    it to the matching book TB line yields the tax-basis amount (Runtime
    Pipeline Step 2). `affects_471` marks BTDs embedded in §471 costs that
    become negative additional-§263A costs when include_negative_263a is set
    (§1.263A-1(d)(3))."""
    btd_id: str = ""
    acct_num: str = ""
    cc_num: str = ""
    description: str = ""
    adjustment: Decimal = Decimal("0")
    category: str = ""            # depreciation / §174 timing / reserves / other
    affects_471: bool = False
    row_index: int = 0
    source_sheet: str = ""

    def __post_init__(self):
        self.adjustment = _dec(self.adjustment)


@dataclass
class FixedAsset:
    """Fixed-asset register row — SCA allocation target, §263A(f) designated-
    property classification input, and Gate-4 BAR improvement target."""
    asset_id: str = ""
    description: str = ""
    asset_type: str = ""          # real / tangible_personal / land / intangible
    class_life: Optional[Decimal] = None
    cost: Decimal = Decimal("0")              # book basis already capitalized
    placed_in_service: Optional[date] = None
    cc_num: str = ""
    # Basis-reconciliation fields (Runtime Pipeline Step 3b):
    book_capitalized_interest: Decimal = Decimal("0")   # ASC 835-20 already on books
    is_improvement: bool = False
    demolition_event: bool = False            # §280B routing (to land basis)
    row_index: int = 0
    source_sheet: str = ""

    def __post_init__(self):
        self.cost = _dec(self.cost)
        self.book_capitalized_interest = _dec(self.book_capitalized_interest)
        if self.class_life is not None:
            self.class_life = _dec(self.class_life)


@dataclass
class CIPSnapshot:
    """Cumulative accumulated production expenditures at one measurement date."""
    measurement_date: Optional[date] = None
    cumulative_ape: Decimal = Decimal("0")

    def __post_init__(self):
        self.cumulative_ape = _dec(self.cumulative_ape)


@dataclass
class CIPProject:
    """CIP detail — one unit of designated property (or a common feature)."""
    project_id: str = ""
    description: str = ""
    linked_asset_id: str = ""
    is_real_property: bool = True
    class_life: Optional[Decimal] = None
    total_estimated_cost: Decimal = Decimal("0")
    production_start: Optional[date] = None
    production_complete: Optional[date] = None   # distinct from PIS date (Q7.10)
    is_improvement: bool = False
    mid_production_purchase_price: Decimal = Decimal("0")   # §1.263A-11(f)
    snapshots: List[CIPSnapshot] = field(default_factory=list)
    # §1.263A-10 unit-of-property structure:
    unit_id: str = ""
    is_common_feature: bool = False
    benefitted_unit_ids: List[str] = field(default_factory=list)
    # §1.263A-11(c) contract-payment APE rules (customer/contractor):
    contract_role: str = ""       # "" / customer / contractor
    contract_payments_by_date: Dict[str, Decimal] = field(default_factory=dict)
    book_capitalized_interest: Decimal = Decimal("0")
    row_index: int = 0
    source_sheet: str = ""

    def __post_init__(self):
        self.total_estimated_cost = _dec(self.total_estimated_cost)
        self.mid_production_purchase_price = _dec(self.mid_production_purchase_price)
        self.book_capitalized_interest = _dec(self.book_capitalized_interest)
        if self.class_life is not None:
            self.class_life = _dec(self.class_life)
        self.contract_payments_by_date = {k: _dec(v) for k, v in
                                          (self.contract_payments_by_date or {}).items()}


@dataclass
class DebtInstrument:
    """Debt schedule row. `traced_to` names the CIPProject the proceeds were
    allocated to under §1.163-8T tracing (empty = nontraced). The eligible-debt
    exclusion flags implement §1.263A-9(a)(4)(i)-(ix)."""
    debt_id: str = ""
    description: str = ""
    principal: Decimal = Decimal("0")            # average outstanding (fallback)
    rate: Decimal = Decimal("0")                 # annual, as a fraction
    interest_incurred: Decimal = Decimal("0")    # actual interest for the period
    traced_to: str = ""
    outstanding_by_date: Dict[str, Decimal] = field(default_factory=dict)
    # §1.263A-9(a)(4) eligible-debt exclusion screens:
    related_party_below_afr: bool = False
    non_interest_bearing: bool = False
    personal_or_qualified_residence: bool = False
    tax_exempt_org_nonbusiness: bool = False
    disallowed_163_8T: bool = False
    # the remaining three (a)(4) categories, previously documented-deferred:
    reserve_or_deferred_tax: bool = False       # reserves/DTLs not debt for tax
    tax_liability_453a_460b: bool = False       # income-tax/§453A/§460(b) items
    sale_leaseback_purchase_money: bool = False
    row_index: int = 0
    source_sheet: str = ""

    def __post_init__(self):
        self.principal = _dec(self.principal)
        self.rate = _dec(self.rate)
        self.interest_incurred = _dec(self.interest_incurred)
        # keys normalize to ISO strings — a date-object key silently missed
        # every lookup and fell back to principal (red-team, confirmed)
        self.outstanding_by_date = {
            (k.isoformat() if isinstance(k, date) else str(k)): _dec(v)
            for k, v in (self.outstanding_by_date or {}).items()}

    @property
    def is_eligible_debt(self) -> bool:
        """§1.263A-9(a)(4): excluded categories. Non-interest-bearing debt is
        eligible only when it is itself traced debt."""
        if self.disallowed_163_8T or self.related_party_below_afr:
            return False
        if self.personal_or_qualified_residence or self.tax_exempt_org_nonbusiness:
            return False
        if self.reserve_or_deferred_tax or self.tax_liability_453a_460b \
                or self.sale_leaseback_purchase_money:
            return False
        if self.non_interest_bearing and not self.traced_to:
            return False
        return True


@dataclass
class CostPool:
    """One indirect/mixed-service cost pool for SCA allocation.  `targets` maps
    target id (asset_id or the literal 'NON_PRODUCTION') -> driver value."""
    pool_id: str = ""
    description: str = ""
    amount: Decimal = Decimal("0")
    driver: str = ""              # headcount / square_footage / direct_labor / ...
    is_mixed_service: bool = False
    targets: Dict[str, Decimal] = field(default_factory=dict)

    def __post_init__(self):
        self.amount = _dec(self.amount)
        self.targets = {k: _dec(v) for k, v in (self.targets or {}).items()}


@dataclass
class SelfConstructedAsset:
    """A Phase C allocation target. `sscm_eligible` is the §1.263A-1(h)(2)
    route-(C)-or-(D) determination (Gate 6, Q6.2)."""
    asset_id: str = ""
    description: str = ""
    book_cost: Decimal = Decimal("0")          # bucket A (CIP book cost)
    sscm_eligible: bool = False

    def __post_init__(self):
        self.book_cost = _dec(self.book_cost)


# ---------------------------------------------------------------------------
# Phases F/G/H schedules (§174, §1.263(a)-4/-5 + §195/§248/§709, §59(e), §1060)
# ---------------------------------------------------------------------------

@dataclass
class REExpenditure:
    """§174/§174A research & experimental expenditure (per project/pool)."""
    re_id: str = ""
    description: str = ""
    amount: Decimal = Decimal("0")
    domestic: bool = True
    tax_year: int = 0             # year incurred (drives 2022-2024 catch-up)
    software_development: bool = False
    book_capitalized_amount: Decimal = Decimal("0")   # basis reconciliation
    row_index: int = 0
    source_sheet: str = ""

    def __post_init__(self):
        self.amount = _dec(self.amount)
        self.book_capitalized_amount = _dec(self.book_capitalized_amount)


@dataclass
class TransactionCostItem:
    """§1.263(a)-5 transaction cost line (per transaction)."""
    item_id: str = ""
    transaction_id: str = ""
    description: str = ""
    amount: Decimal = Decimal("0")
    cost_type: str = ""           # investment_banking/legal/due_diligence/...
    covered_transaction: bool = False
    inherently_facilitative: bool = False
    incurred_date: Optional[date] = None
    bright_line_date: Optional[date] = None
    success_based: bool = False
    transaction_abandoned: bool = False       # Rev. Rul. 73-580
    row_index: int = 0
    source_sheet: str = ""

    def __post_init__(self):
        self.amount = _dec(self.amount)


@dataclass
class IntangibleItem:
    """§1.263(a)-4 acquired/created intangible."""
    item_id: str = ""
    description: str = ""
    amount: Decimal = Decimal("0")
    category: str = ""            # financial_interest/contract_right/membership/
                                  # governmental_right/real_property_benefit/residual
    acquired_with_business: bool = False       # -> §197 15-year
    benefit_start: Optional[date] = None       # first realization (12-month rule)
    benefit_end: Optional[date] = None
    payment_year: int = 0
    facilitative_costs: Decimal = Decimal("0") # aggregate, for the (e)(4) $5k cliff
    # Commissions are CATEGORICALLY excluded from the (e)(4) de minimis —
    # always capitalized regardless of the $5,000 cliff. Keeping them inside
    # facilitative_costs let a $4,000 commission slip through as deductible
    # (red-team §16); supply them separately here.
    facilitative_commissions: Decimal = Decimal("0")
    prior_capitalized_basis: Decimal = Decimal("0")
    row_index: int = 0
    source_sheet: str = ""

    def __post_init__(self):
        self.amount = _dec(self.amount)
        self.facilitative_costs = _dec(self.facilitative_costs)
        self.facilitative_commissions = _dec(self.facilitative_commissions)
        self.prior_capitalized_basis = _dec(self.prior_capitalized_basis)


@dataclass
class StartupOrgCostPool:
    """§195/§248/§709 start-up or organizational cost pool."""
    pool_id: str = ""
    kind: str = "startup"         # startup / org_corp / org_partnership / syndication
    total: Decimal = Decimal("0")
    business_commencement: Optional[date] = None
    row_index: int = 0
    source_sheet: str = ""

    def __post_init__(self):
        self.total = _dec(self.total)


@dataclass
class QualifiedExpenditureElection:
    """§59(e) elective amortization of a qualified expenditure (per item)."""
    item_id: str = ""
    category: str = ""            # circulation / re_domestic / idc /
                                  # mining_exploration / mining_development
    amount: Decimal = Decimal("0")
    elected: bool = False
    election_year: int = 0
    row_index: int = 0
    source_sheet: str = ""

    def __post_init__(self):
        self.amount = _dec(self.amount)


@dataclass
class PurchasePriceAllocation:
    """§1060/Form 8594 residual-method input (per acquisition)."""
    transaction_id: str = ""
    aggregate_consideration: Decimal = Decimal("0")
    class_fmv: Dict[str, Decimal] = field(default_factory=dict)  # "I".."VI" -> FMV
    row_index: int = 0
    source_sheet: str = ""

    def __post_init__(self):
        self.aggregate_consideration = _dec(self.aggregate_consideration)
        self.class_fmv = {k: _dec(v) for k, v in (self.class_fmv or {}).items()}


# ---------------------------------------------------------------------------
# Shared basis/amortization record + engagement container
# ---------------------------------------------------------------------------

@dataclass
class AmortizableItem:
    """One row of the shared Basis & Amortization Schedule — the single record
    Phases C/D/F/G/H post capitalized amounts into (BUILD_PLAN.md Architecture).
    recovery_months None => capitalized with NO amortization (land, syndication
    costs, indefinite-life intangibles pending SME determination)."""
    item_id: str = ""
    description: str = ""
    category: str = ""            # real_property/tangible_personal/land/intangible/
                                  # re_pool/startup_org/qualified_expenditure/inventory
    basis: Decimal = Decimal("0")
    recovery_months: Optional[int] = None
    convention: str = "none"      # mid-year / full-month / none
    start_year: int = 0
    source: str = ""              # which phase/provision posted it
    authority: str = ""
    flags: List[str] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self):
        self.basis = _dec(self.basis)

    def first_year_amortization(self) -> Decimal:
        """Straight-line year-1 amortization under this item's convention."""
        if not self.recovery_months or self.basis == 0:
            return Decimal("0")
        annual = self.basis * Decimal("12") / Decimal(self.recovery_months)
        if self.convention == "mid-year":
            annual = annual / Decimal("2")
        return annual.quantize(Decimal("0.01"))


@dataclass
class ValidationReport:
    """Accumulates ingestion issues; ERRORs block, WARNs don't."""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def blocking(self) -> int:
        return len(self.errors)


@dataclass
class EngagementData:
    """Everything read for one engagement — the eight Runtime Pipeline inputs."""
    tb_lines: List[TBLine] = field(default_factory=list)
    btds: List[BookTaxDifference] = field(default_factory=list)
    fixed_assets: List[FixedAsset] = field(default_factory=list)
    cip_projects: List[CIPProject] = field(default_factory=list)
    debts: List[DebtInstrument] = field(default_factory=list)
    re_expenditures: List[REExpenditure] = field(default_factory=list)
    transaction_costs: List[TransactionCostItem] = field(default_factory=list)
    intangibles: List[IntangibleItem] = field(default_factory=list)
    startup_pools: List[StartupOrgCostPool] = field(default_factory=list)
    qualified_expenditures: List[QualifiedExpenditureElection] = field(default_factory=list)
    purchase_price_allocations: List[PurchasePriceAllocation] = field(default_factory=list)
    # Holds engines.tangible_263a.TangibleExpenditure rows (§263(a) repair-regs
    # schedule). Deliberately untyped here: the dataclass lives with its engine
    # and model.py stays import-free of engine modules.
    tangible_items: List = field(default_factory=list)  # List[TangibleExpenditure]
    validation: ValidationReport = field(default_factory=ValidationReport)
