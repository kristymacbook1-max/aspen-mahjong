"""Core data model for the §263A/§263(a)/§266 capitalization tool."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, List, Dict


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
