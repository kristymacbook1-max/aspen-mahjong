"""Phase H — §59(e) elective qualified-expenditure amortization
(AMT-preference avoidance).

§59(e) lets a taxpayer ELECT straight-line amortization for qualified
expenditures (circulation §173 / domestic R&E §174A(a) / IDC §263(c) /
mining development §616(a) / mining exploration §617(a)) instead of the
otherwise-available faster write-off, pre-empting the individual-AMT
(§55/§56/§57) preference. Elections are ITEM-BY-ITEM (any portion of a
qualified expenditure), made by statement with the return for the year
amortization begins, and IRREVOCABLE except by IRS consent via letter
ruling in rare/unusual circumstances.

GATE (BUILD_PLAN.md Phase H / Gate 10 Q10.1, checked FIRST): a C corp with
no individual-AMT-exposed owners has NO current-law use for §59(e) — the
corporate AMT was repealed by TCJA, and the IRA 2022 CAMT (§55/§56A) starts
from adjusted financial statement income with its own closed adjustment
list; it does not use §57/§59(e) preference items.

Periods come from taxonomy/qualified_expenditure_periods.yaml (data, not
constants). CONVENTION NOTE (documented, not verified): the schedule carries
election_year only, no month data — amortization is computed straight-line
with a MID-YEAR start (half a full year in year 1) as the documented proxy
for the statute's ratable-from-when-benefits-are-realized start.

UNCERTAIN, flagged never silently resolved: (1) §57-MINING-CITE-UNVERIFIED —
the exact §57(a) subparagraph for the mining exploration/development
preference; (2) §59E-174A-ELECTION-CONFLICT — which period governs when
§59(e) (10-year) and §174A(c) (elected ≥60-month) are both elected on the
SAME domestic-R&E dollars; the item still computes here but the flag leads
and routes to SME.
"""

from decimal import Decimal
from pathlib import Path
from typing import FrozenSet, List

import yaml

from ..model import AmortizableItem, QualifiedExpenditureElection

_PERIODS_PATH = (Path(__file__).resolve().parent.parent
                 / "taxonomy" / "qualified_expenditure_periods.yaml")
_PERIODS_CACHE = None

C_CORP_GATE_WARNING = (
    "§59(e) has no current-law use for a C corp with no individual-AMT-"
    "exposed owners (corporate AMT repealed by TCJA; CAMT §55/§56A does not "
    "use §57/§59(e) preference items)")


def load_periods() -> dict:
    """category -> {months, authority} from the taxonomy YAML."""
    global _PERIODS_CACHE
    if _PERIODS_CACHE is None:
        with open(_PERIODS_PATH, "r", encoding="utf-8") as fh:
            _PERIODS_CACHE = yaml.safe_load(fh)["periods"]
    return _PERIODS_CACHE


def compute_59e(elections: List[QualifiedExpenditureElection], *,
                entity_type: str = "c_corp",
                individual_amt_exposure: bool = False,
                overlapping_174A_items: FrozenSet[str] = frozenset()) -> dict:
    """Returns {items, amortizable_items, warnings}. Gated FIRST on entity
    type / individual-AMT exposure (see module docstring); only records with
    elected=True are scheduled (the election is item-by-item and
    irrevocable except by IRS consent)."""
    warnings: List[str] = []
    items: List[dict] = []
    amortizable: List[AmortizableItem] = []

    # Gate 10 Q10.1 — checked before any per-item election logic. The plan's
    # question is "an individual, OR a pass-through whose owners may report
    # AMT preference items" — so an s_corp/partnership WITHOUT stated owner
    # exposure is gated out too, not served (red-team §16: the original
    # boolean only gated C corps, silently scheduling elections for
    # pass-throughs whose owners had no AMT exposure).
    if not individual_amt_exposure and entity_type != "sole_prop":
        if entity_type == "c_corp":
            return {"items": items, "amortizable_items": amortizable,
                    "warnings": [C_CORP_GATE_WARNING]}
        return {"items": items, "amortizable_items": amortizable,
                "warnings": [
                    f"§59E-NO-AMT-EXPOSURE: entity_type={entity_type!r} with "
                    f"individual_amt_exposure=False — §59(e) matters only when "
                    f"an individual owner could face §55/§56/§57 preference "
                    f"items (Gate 10 Q10.1). No election scheduled; re-run "
                    f"with individual_amt_exposure=True if owners are exposed."]}

    periods = load_periods()
    for el in elections:
        if not el.elected:
            continue
        if el.amount < 0:
            # scheduled silently with a negative amortization base
            # (round-4 symmetry sweep) — an expenditure cannot be negative
            warnings.append(
                f"NEGATIVE-AMOUNT [§59(e) {el.item_id}]: ${el.amount:,.2f} — "
                f"no schedule built; fix the expenditure figure.")
            continue
        row = {"item_id": el.item_id, "category": el.category,
               "amount": el.amount, "recovery_months": None,
               "first_year_amortization": Decimal("0"), "flags": []}
        spec = periods.get(el.category)
        if spec is None:
            warnings.append(
                f"§59E-CATEGORY-UNKNOWN [{el.item_id}]: {el.category!r} is "
                f"not a §59(e)(2) qualified-expenditure category — no "
                f"schedule built.")
            row["flags"].append("§59E-CATEGORY-UNKNOWN")
            items.append(row)
            continue
        if el.category.startswith("mining_"):
            row["flags"].append("§57-MINING-CITE-UNVERIFIED")
            warnings.append(
                f"§57-MINING-CITE-UNVERIFIED [{el.item_id}]: the exact "
                f"§57(a) subparagraph for the mining exploration/development "
                f"AMT preference is unconfirmed against primary text.")
        if el.item_id in overlapping_174A_items:
            # Both §59(e) and §174A(c) elected on the same dollars — the
            # governing period is unresolved; computed for visibility but
            # the flag leads: SME review before use.
            row["flags"].append("§59E-174A-ELECTION-CONFLICT")
            warnings.append(
                f"§59E-174A-ELECTION-CONFLICT [{el.item_id}]: §174A(c) "
                f"capitalization was also elected on these dollars — which "
                f"period governs (10-year §59(e) vs. the elected ≥60-month "
                f"§174A(c)) is unresolved; routed to SME review.")
        months = int(spec["months"])
        item = AmortizableItem(
            item_id=el.item_id,
            description=f"§59(e) election — {el.category}",
            category="qualified_expenditure", basis=el.amount,
            recovery_months=months, convention="mid-year",
            start_year=el.election_year,
            source="Phase H compute_59e", authority=spec["authority"],
            flags=list(row["flags"]),
            notes="Mid-year start is a documented proxy — the schedule "
                  "carries no month data (see module docstring). Election "
                  "is item-by-item and irrevocable except by IRS consent.")
        row["recovery_months"] = months
        row["first_year_amortization"] = item.first_year_amortization()
        amortizable.append(item)
        items.append(row)

    return {"items": items, "amortizable_items": amortizable,
            "warnings": warnings}
