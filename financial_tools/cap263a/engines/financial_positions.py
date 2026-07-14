"""§263(g)/§263(h) — mandatory capitalization for financial positions.

Two independent calculators, one per subsection:

§263(g) STRADDLE CARRYING CHARGES (personal property that is part of a
§1092(c) straddle): interest on debt incurred/continued to purchase or carry
the position, PLUS amounts paid to insure, store, or transport it, REDUCED
(never below zero) by the §263(g)(2)(B) income offsets — interest (including
OID) includible on the property, §954(c)(1)(G)-type payments with respect to
securities loans includible, and dividends includible reduced by the §243/
§245 deductions allowable. The net charge is NOT deductible; it capitalizes
into the position's basis. Identified §1256(e) hedging transactions are
outside §1092/§263(g) — a position flagged as a hedge is routed out with a
warning, never netted.

§263(h) SHORT-SALE PAYMENTS IN LIEU (payments in lieu of dividends on stock
used to close a short sale): NOT deductible when the short sale is closed
within 45 days after the date of the short sale (1 year for EXTRAORDINARY
dividends, §263(h)(3)); the disallowed payment ADDS TO THE BASIS of the
stock used to close the short sale (§263(h)(1) flush). Held longer than the
applicable window -> ordinarily deductible (as investment interest under
§163(d)(3)(C) — the §163(d) limitation itself is out of scope, warned).
The §263(h)(5)(A) exception (short sale held open ≥ 1 year? no — the
exception for amounts treated as ordinary income where the taxpayer includes
compensation from the lender) and day-counting suspensions under §263(h)(4)
(diminished-risk periods pause the count) are NOT computed — the day count
is an INPUT; the suspension rule is surfaced as a per-item reminder flag.

Both calculators follow the house pattern: tri-state facts (None = not
established -> OPEN QUESTION + conservative treatment), CODE-PREFIX
warnings, exact-Decimal totals, nothing silent.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from ..model import _dec


@dataclass
class StraddlePosition:
    """One personal-property position for the §263(g) computation."""
    position_id: str = ""
    description: str = ""
    interest_to_carry: Decimal = Decimal("0")     # §263(g)(2)(A)(i)
    insurance_storage_transport: Decimal = Decimal("0")   # (2)(A)(ii)
    interest_income: Decimal = Decimal("0")       # (2)(B)(i) incl. OID
    securities_loan_payments: Decimal = Decimal("0")      # (2)(B)(iii)-type
    dividends_net_of_drd: Decimal = Decimal("0")  # (2)(B)(ii): dividends − §243/§245 DRD
    is_straddle_position: Optional[bool] = None   # part of a §1092(c) straddle?
    is_identified_hedge: bool = False             # §1256(e) hedging transaction
    row_index: int = 0

    def __post_init__(self):
        for f in ("interest_to_carry", "insurance_storage_transport",
                  "interest_income", "securities_loan_payments",
                  "dividends_net_of_drd"):
            setattr(self, f, _dec(getattr(self, f)))


@dataclass
class ShortSalePayment:
    """One payment in lieu of dividends for the §263(h) computation."""
    payment_id: str = ""
    description: str = ""
    payment_in_lieu: Decimal = Decimal("0")
    days_short_sale_open: Optional[int] = None    # closing-date count, §263(h)(2)
    extraordinary_dividend: bool = False          # §263(h)(3) -> 1-year window
    row_index: int = 0

    def __post_init__(self):
        self.payment_in_lieu = _dec(self.payment_in_lieu)


def compute_263g(positions: List[StraddlePosition]) -> dict:
    """Per-position net carrying charge -> capitalized into basis.

    Returns {items, open_questions, capitalized_total, deductible_total,
    warnings}. deductible_total carries charges on positions established as
    NOT straddle positions (ordinary deductibility rules apply — §163(d)
    etc. are out of scope, warned once)."""
    warnings: List[str] = []
    open_questions: List[dict] = []
    seen: set = set()
    items: List[dict] = []
    capitalized_total = Decimal("0")
    deductible_total = Decimal("0")
    nonstraddle_warned = False

    def ask(pos, question, why):
        if question in seen:
            return
        seen.add(question)
        open_questions.append({"item_id": pos.position_id,
                               "question": question, "why": why})

    for pos in positions:
        label = pos.position_id or pos.description
        charges = pos.interest_to_carry + pos.insurance_storage_transport
        offsets = (pos.interest_income + pos.securities_loan_payments
                   + pos.dividends_net_of_drd)
        row = {"item_id": pos.position_id, "description": pos.description,
               "charges": charges, "offsets": offsets, "treatment": "",
               "capitalized": Decimal("0"), "deductible": Decimal("0"),
               "flags": []}
        if charges < 0 or offsets < 0:
            row["treatment"] = "sme_review"
            row["flags"].append("NEGATIVE-AMOUNT")
            warnings.append(
                f"NEGATIVE-AMOUNT [§263(g) {label}]: carrying charges "
                f"(${charges:,.2f}) and offsets (${offsets:,.2f}) must each "
                f"be non-negative — nothing computed; fix the schedule.")
            items.append(row)
            continue
        if pos.is_identified_hedge:
            row["treatment"] = "hedging_excluded"
            row["flags"].append("1256E-HEDGE-OUTSIDE-1092")
            row["deductible"] = charges
            deductible_total += charges
            warnings.append(
                f"1256E-HEDGE-OUTSIDE-1092 [{label}]: an identified §1256(e) "
                f"hedging transaction is not a straddle position — §263(g) "
                f"does not apply; charges left deductible (ordinary rules).")
            items.append(row)
            continue
        if pos.is_straddle_position is None:
            row["treatment"] = "open_question_capitalize_pending"
            row["flags"].append("STRADDLE-STATUS-UNKNOWN")
            net = max(Decimal("0"), charges - offsets)
            row["capitalized"] = net
            row["deductible"] = charges - net
            capitalized_total += net
            deductible_total += charges - net
            ask(pos,
                f"Position {label} '{pos.description}': is the personal "
                f"property part of a straddle under §1092(c) (offsetting "
                f"positions with substantially diminished risk of loss)? "
                f"Answer is_straddle_position True/False.",
                "§263(g) capitalization is mandatory for straddle positions "
                "only — the net charge is capitalized CONSERVATIVELY pending "
                "the answer; never silently deducted.")
            items.append(row)
            continue
        if not pos.is_straddle_position:
            row["treatment"] = "not_straddle_deduct"
            row["deductible"] = charges
            deductible_total += charges
            if not nonstraddle_warned:
                nonstraddle_warned = True
                warnings.append(
                    "NON-STRADDLE-DEDUCTIBILITY: charges on non-straddle "
                    "positions were left deductible — the §163(d) investment-"
                    "interest limitation and other deduction limits are out "
                    "of scope for this engine.")
            items.append(row)
            continue
        net = charges - offsets
        if net < 0:
            net = Decimal("0")
            row["flags"].append("OFFSETS-EXCEED-CHARGES")
        row["treatment"] = "straddle_capitalize_263g"
        row["capitalized"] = net
        row["deductible"] = charges - net
        capitalized_total += net
        deductible_total += charges - net
        items.append(row)

    return {"items": items, "open_questions": open_questions,
            "capitalized_total": capitalized_total,
            "deductible_total": deductible_total, "warnings": warnings}


def compute_263h(payments: List[ShortSalePayment]) -> dict:
    """Payments in lieu of dividends: ≤45 days (1 year if extraordinary) ->
    capitalized to the basis of the stock used to close (§263(h)(1));
    longer -> deductible (investment-interest treatment, limits out of
    scope). Day counts are inputs; the §263(h)(4) diminished-risk
    suspension is a per-item reminder, not computed."""
    warnings: List[str] = []
    open_questions: List[dict] = []
    seen: set = set()
    items: List[dict] = []
    capitalized_total = Decimal("0")
    deductible_total = Decimal("0")
    suspension_reminded = False

    def ask(p, question, why):
        if question in seen:
            return
        seen.add(question)
        open_questions.append({"item_id": p.payment_id,
                               "question": question, "why": why})

    for p in payments:
        label = p.payment_id or p.description
        row = {"item_id": p.payment_id, "description": p.description,
               "payment_in_lieu": p.payment_in_lieu, "treatment": "",
               "capitalized": Decimal("0"), "deductible": Decimal("0"),
               "flags": []}
        if p.payment_in_lieu < 0:
            row["treatment"] = "sme_review"
            row["flags"].append("NEGATIVE-AMOUNT")
            warnings.append(
                f"NEGATIVE-AMOUNT [§263(h) {label}]: payment in lieu "
                f"${p.payment_in_lieu:,.2f} — nothing computed; fix the "
                f"schedule.")
            items.append(row)
            continue
        window = 365 if p.extraordinary_dividend else 45
        if not suspension_reminded:
            suspension_reminded = True
            warnings.append(
                "263H-SUSPENSION-NOT-COMPUTED: the §263(h)(4) rule SUSPENDS "
                "the day count for periods of diminished risk (offsetting "
                "positions, options) — the day counts supplied here must "
                "already reflect any suspension; this engine does not "
                "compute it.")
        if p.days_short_sale_open is None:
            row["treatment"] = "open_question_capitalize_pending"
            row["flags"].append("DAYS-OPEN-UNKNOWN")
            row["capitalized"] = p.payment_in_lieu
            capitalized_total += p.payment_in_lieu
            ask(p,
                f"Payment {label} '{p.description}': how many days was the "
                f"short sale open on the date it closed (after any "
                f"§263(h)(4) suspension)? The disallowance window is "
                f"{window} days"
                + (" (extraordinary dividend)" if p.extraordinary_dividend
                   else "") + ".",
                "§263(h) capitalization turns entirely on the holding "
                "window — the payment is capitalized CONSERVATIVELY pending "
                "the day count; never silently deducted.")
            items.append(row)
            continue
        if p.days_short_sale_open <= window:
            row["treatment"] = "capitalize_263h_to_closing_stock_basis"
            row["capitalized"] = p.payment_in_lieu
            capitalized_total += p.payment_in_lieu
        else:
            row["treatment"] = "deductible_held_past_window"
            row["deductible"] = p.payment_in_lieu
            deductible_total += p.payment_in_lieu
            row["flags"].append("163D-LIMIT-OUT-OF-SCOPE")
        items.append(row)

    return {"items": items, "open_questions": open_questions,
            "capitalized_total": capitalized_total,
            "deductible_total": deductible_total, "warnings": warnings}
