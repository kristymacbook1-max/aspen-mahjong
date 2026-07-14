"""§266 — elective capitalization of taxes and carrying charges
(Reg. §1.266-1).

The election mirrors the reg's granularity, so `elections` is
{"unimproved_real": set of property_ids OR True (all),
 "real_development": ..., "personal_property": ...}:
(b)(1)(i) unimproved/unproductive real property is an ANNUAL election made
property-by-property; (b)(1)(ii) real-property development binds through
completion for the project; (b)(1)(iii) personal property runs until
installation or first use. A missing/falsy key means not elected.

DECISION ORDER per item:
1. NEGATIVE amount -> flag NEGATIVE-AMOUNT, treatment "sme_review",
   nothing computed (house pattern: a charge cannot be negative;
   excluded from every total).
2. category not "unimproved_real"/"real_development"/"personal_property"
   -> "sme_review" + warning 266-CATEGORY-UNKNOWN; the dollars land in
   not_booked_total.
3. Otherwise-deductible gate (Reg. §1.266-1(a)(1) — §266 capitalizes only
   items OTHERWISE DEDUCTIBLE): otherwise_deductible False ->
   "not_deductible_no_266" (nothing to capitalize — the item is simply
   nondeductible; flag 266-NOT-OTHERWISE-DEDUCTIBLE; not_booked_total).
   None -> OPEN QUESTION (e.g. §163(j)-limited interest, SALT-capped
   individual taxes — whether the amount is otherwise deductible must be
   established) + conservative DEDUCT-side refusal: treatment
   "sme_review", flag 266-DEDUCTIBILITY-UNKNOWN, nothing booked
   (not_booked_total).
4. Election coverage: is the item's category elected for its property_id
   (set membership, or True = all properties)? Not elected ->
   "deduct_no_election".
5. Category gates:
   - unimproved_real requires property_unproductive True for the year
     ((b)(1)(i) — unimproved AND unproductive). False ->
     "deduct_productive_property" + warning 266-PRODUCTIVE-PROPERTY.
     None -> OPEN QUESTION + NOT capitalized (flag
     266-PRODUCTIVE-STATUS-UNKNOWN, treatment
     "deduct_productive_status_unknown" — the amount is otherwise
     deductible, so it stays on the deduct side pending the answer).
   - real_development with development_complete True ->
     "deduct_post_completion" (charges after completion are outside the
     (b)(1)(ii) election's window).
   - personal_property with installed_or_first_used True ->
     "deduct_post_installation" ((b)(1)(iii) runs until installation or
     first use).
6. Capitalize the survivors: treatment "capitalize_266", AmortizableItem
   basis=amount, recovery_months=None (the charge attaches to the
   property's basis; recovery follows the property), authority
   Reg. §1.266-1(b).

Run-level warnings (once each, when relevant):
- 266-STATEMENT-REQUIRED (any election active): the election statement
  must be filed with the ORIGINAL return (Reg. §1.266-1(c)(3)).
- 266-263AF-ORDERING (interest capitalized under §266): interest on
  DESIGNATED PROPERTY production expenditures is governed by §263A(f),
  which this election cannot override — confirm no dollars appear in
  both this schedule and the §263A(f) computation (same
  DOUBLE-COUNT-RECONCILE posture as pipeline.py's other overlap
  warnings).
- 266-ANNUAL-ELECTION (unimproved_real elected): the (b)(1)(i) election
  is year-by-year.

Totals are exact Decimal sums (no division, nothing quantized). Tie:
capitalized_total + deductible_total + not_booked_total == sum of all
non-negative item amounts (NEGATIVE-AMOUNT rows carry no computable
dollars and sit outside every total).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from ..model import AmortizableItem, _dec

CATEGORIES = ("unimproved_real", "real_development", "personal_property")

# AmortizableItem.category by §266 property class (model.py vocabulary):
_AMORT_CATEGORY = {"unimproved_real": "land",
                   "real_development": "real_property",
                   "personal_property": "tangible_personal"}


@dataclass
class CarryingChargeItem:
    """One tax/interest/other carrying charge line (per property)."""
    item_id: str = ""
    description: str = ""
    amount: Decimal = Decimal("0")
    charge_type: str = "other"    # "tax" | "interest" | "other"
    category: str = ""            # unimproved_real | real_development |
                                  # personal_property
    property_id: str = ""
    # Reg. §1.266-1(a)(1) gate — tri-state; None = not established:
    otherwise_deductible: Optional[bool] = None
    # (b)(1)(i) gate, unimproved_real only — tri-state:
    property_unproductive: Optional[bool] = None
    development_complete: bool = False        # real_development only
    installed_or_first_used: bool = False     # personal_property only

    def __post_init__(self):
        self.amount = _dec(self.amount)


def _elected(elections: dict, category: str, property_id: str) -> bool:
    """True when the category is elected for this property: the elections
    value is True (all properties) or a container of property_ids."""
    sel = elections.get(category)
    if sel is True:
        return True
    if not sel:
        return False
    return property_id in sel


def compute_266(items: List[CarryingChargeItem], *, elections: dict) -> dict:
    """Apply the module-docstring decision order to every item.

    Returns {items, amortizable_items, open_questions, capitalized_total,
    deductible_total, not_booked_total, warnings}."""
    elections = elections or {}
    warnings: List[str] = []
    open_questions: List[dict] = []
    seen_questions: set = set()

    def ask(item_id: str, question: str, why: str) -> None:
        if question in seen_questions:
            return
        seen_questions.add(question)
        open_questions.append({"item_id": item_id, "question": question,
                               "why": why})

    rows: List[dict] = []
    amortizable: List[AmortizableItem] = []
    capitalized_total = Decimal("0")
    deductible_total = Decimal("0")
    not_booked_total = Decimal("0")
    interest_capitalized = False

    # --- run-level election warnings (once each, when relevant) ------------
    if any(elections.get(c) for c in CATEGORIES):
        warnings.append(
            "266-STATEMENT-REQUIRED: a §266 election is in effect — the "
            "election statement must be filed with the ORIGINAL return for "
            "the year (Reg. §1.266-1(c)(3)); confirm it is attached.")
    if elections.get("unimproved_real"):
        warnings.append(
            "266-ANNUAL-ELECTION: the Reg. §1.266-1(b)(1)(i) unimproved/"
            "unproductive real property election is YEAR-BY-YEAR (annual, "
            "made per property) — it does not carry forward; re-make it "
            "each year it is wanted.")

    for it in items:
        row = {"item_id": it.item_id, "description": it.description,
               "amount": it.amount, "charge_type": it.charge_type,
               "category": it.category, "property_id": it.property_id,
               "treatment": "", "authority": "", "flags": [],
               "deductible": Decimal("0"), "capitalized": Decimal("0")}
        label = it.item_id or it.description

        # --- 1. negative amount ------------------------------------------
        if it.amount < 0:
            row["treatment"] = "sme_review"
            row["flags"].append("NEGATIVE-AMOUNT")
            warnings.append(
                f"NEGATIVE-AMOUNT [§266 {label}]: ${it.amount:,.2f} — "
                f"nothing computed; route credits/refunds through the "
                f"schedule, not a negative carrying charge.")
            rows.append(row)
            continue

        # --- 2. category guard ----------------------------------------------
        if it.category not in CATEGORIES:
            row["treatment"] = "sme_review"
            row["flags"].append("266-CATEGORY-UNKNOWN")
            warnings.append(
                f"266-CATEGORY-UNKNOWN [§266 {label}]: "
                f"category={it.category!r} is not one of "
                f"{'/'.join(CATEGORIES)} — nothing booked.")
            not_booked_total += it.amount
            rows.append(row)
            continue

        # --- 3. otherwise-deductible gate (Reg. §1.266-1(a)(1)) --------------
        if it.otherwise_deductible is False:
            row["treatment"] = "not_deductible_no_266"
            row["authority"] = ("Reg. §1.266-1(a)(1) — not otherwise "
                                "deductible; nothing to capitalize")
            row["flags"].append("266-NOT-OTHERWISE-DEDUCTIBLE")
            not_booked_total += it.amount
            rows.append(row)
            continue
        if it.otherwise_deductible is None:
            row["treatment"] = "sme_review"
            row["authority"] = ("Reg. §1.266-1(a)(1) — deductibility not "
                                "established; nothing booked")
            row["flags"].append("266-DEDUCTIBILITY-UNKNOWN")
            not_booked_total += it.amount
            ask(it.item_id,
                f"Item {label} '{it.description}': is this "
                f"{it.charge_type or 'carrying'} charge otherwise "
                f"DEDUCTIBLE for the year (Reg. §1.266-1(a)(1)) — e.g. "
                f"§163(j)-limited interest or SALT-capped individual taxes "
                f"may not be? Answer otherwise_deductible True/False.",
                "§266 capitalizes only items otherwise deductible — "
                "nothing was booked to either side (treatment sme_review) "
                "pending the answer.")
            rows.append(row)
            continue

        # --- 4. election coverage ---------------------------------------------
        if not _elected(elections, it.category, it.property_id):
            row["treatment"] = "deduct_no_election"
            row["authority"] = ("Reg. §1.266-1(b) — no §266 election covers "
                                "this category/property")
            row["deductible"] = it.amount
            deductible_total += it.amount
            rows.append(row)
            continue

        # --- 5. category gates -------------------------------------------------
        if it.category == "unimproved_real":
            if it.property_unproductive is False:
                row["treatment"] = "deduct_productive_property"
                row["authority"] = ("Reg. §1.266-1(b)(1)(i) — property was "
                                    "productive; election unavailable")
                row["deductible"] = it.amount
                deductible_total += it.amount
                warnings.append(
                    f"266-PRODUCTIVE-PROPERTY [§266 {label}]: the property "
                    f"produced income for the year — the (b)(1)(i) election "
                    f"reaches UNIMPROVED AND UNPRODUCTIVE real property "
                    f"only; the charge was deducted, not capitalized.")
                rows.append(row)
                continue
            if it.property_unproductive is None:
                row["treatment"] = "deduct_productive_status_unknown"
                row["authority"] = ("Reg. §1.266-1(b)(1)(i) — unproductive "
                                    "status pending; not capitalized")
                row["flags"].append("266-PRODUCTIVE-STATUS-UNKNOWN")
                row["deductible"] = it.amount
                deductible_total += it.amount
                ask(it.item_id,
                    f"Item {label} '{it.description}': was the real "
                    f"property UNPRODUCTIVE for the year (no income "
                    f"produced) as well as unimproved "
                    f"(Reg. §1.266-1(b)(1)(i))? Answer "
                    f"property_unproductive True/False.",
                    "The (b)(1)(i) election reaches unimproved AND "
                    "unproductive real property only — the charge (already "
                    "established as otherwise deductible) stays on the "
                    "deduct side, NOT capitalized, pending the answer.")
                rows.append(row)
                continue
        elif it.category == "real_development":
            if it.development_complete:
                row["treatment"] = "deduct_post_completion"
                row["authority"] = ("Reg. §1.266-1(b)(1)(ii) — charges "
                                    "after development/construction "
                                    "completion are outside the election's "
                                    "window")
                row["deductible"] = it.amount
                deductible_total += it.amount
                rows.append(row)
                continue
        else:  # personal_property
            if it.installed_or_first_used:
                row["treatment"] = "deduct_post_installation"
                row["authority"] = ("Reg. §1.266-1(b)(1)(iii) — the "
                                    "election runs until installation or "
                                    "first use")
                row["deductible"] = it.amount
                deductible_total += it.amount
                rows.append(row)
                continue

        # --- 6. capitalize the survivors ----------------------------------------
        row["treatment"] = "capitalize_266"
        row["authority"] = "Reg. §1.266-1(b)"
        row["capitalized"] = it.amount
        capitalized_total += it.amount
        if it.charge_type == "interest":
            interest_capitalized = True
        amortizable.append(AmortizableItem(
            item_id=it.item_id,
            description=f"§266 capitalized {it.charge_type or 'carrying'} "
                        f"charge — {it.description}",
            category=_AMORT_CATEGORY[it.category], basis=it.amount,
            recovery_months=None, convention="none",
            source="sec266 compute_266", authority="Reg. §1.266-1(b)",
            notes=f"Capitalized carrying charge attaches to the basis of "
                  f"property {it.property_id or '(unidentified)'} — "
                  f"recovery follows the property (no separate "
                  f"amortization)."))
        rows.append(row)

    if interest_capitalized:
        warnings.append(
            "266-263AF-ORDERING: interest was capitalized under §266, but "
            "interest on DESIGNATED PROPERTY production expenditures is "
            "governed by §263A(f), which the §266 election cannot override "
            "— confirm no dollars appear in BOTH this schedule and the "
            "§263A(f) computation (same DOUBLE-COUNT-RECONCILE posture as "
            "the pipeline's other overlap warnings).")

    return {"items": rows, "amortizable_items": amortizable,
            "open_questions": open_questions,
            "capitalized_total": capitalized_total,
            "deductible_total": deductible_total,
            "not_booked_total": not_booked_total,
            "warnings": warnings}
