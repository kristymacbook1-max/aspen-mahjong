"""§263(a) tangible property — capitalize-vs-deduct under the repair
regulations (Reg. §1.263(a)-1/-2/-3) and §1.162-3 materials & supplies.

DECISION ORDER per item (mirrors the regs' practical application order):
1. NEGATIVE amount -> flag NEGATIVE-AMOUNT, treatment "sme_review",
   nothing computed (house pattern: a cost cannot be negative).
2. De minimis safe harbor (only if de_minimis_election, Reg. §1.263(a)-1(f)
   — an ANNUAL, IRREVOCABLE election, all-or-nothing for qualifying items;
   with an AFS a WRITTEN accounting policy in place as of the start of the
   year is a condition): invoice_or_item_cost present and
   <= profile.de_minimis_ceiling ($5,000 AFS / $2,500 no-AFS per Notice
   2015-82 — the ceiling comes from the profile, never hardcoded) ->
   "de_minimis_deduct". Election on but invoice_or_item_cost is None ->
   flag DE-MINIMIS-COST-UNKNOWN + OPEN QUESTION, and continue down the
   tree (conservative).
3. Materials & supplies (is_material_or_supply, §1.162-3): deduct when
   EITHER prong is True — unit cost <= $200 (§1.162-3(c)(1)(iv)) or
   economic life <= 12 months (§1.162-3(c)(1)(iii)) ->
   "materials_supplies_deduct". Both prongs None -> OPEN QUESTION + fall
   through. Incidental vs non-incidental TIMING is OUT OF SCOPE — flag
   MS-TIMING-NOT-DETERMINED (one warning per run, not per item).
4. Small taxpayer building safe harbor (only if
   small_taxpayer_building_election and is_building, Reg. §1.263(a)-3(h)
   — annual, per-building): eligibility = avg_gross_receipts <=
   $10,000,000 AND building_unadjusted_basis <= $1,000,000; the
   per-building AGGREGATE of repairs + maintenance + improvements for the
   year must be <= the LESSER of $10,000 or 2% of unadjusted basis.
   Aggregate source: the explicit total_building_repairs_maintenance_
   improvements dict when given, else the sum of the supplied items
   sharing that unit_of_property (warned STSH-AGGREGATE-FROM-SCHEDULE-ONLY
   — amounts outside this schedule must be included by the caller).
   Pass -> "small_taxpayer_sh_deduct". Fail eligibility or ceiling ->
   flag and continue.
5. BAR improvement tests: betterment (§1.263(a)-3(j)) OR adaptation to a
   new/different use (§1.263(a)-3(l)) OR restoration (§1.263(a)-3(k),
   incl. major component / substantial structural part, basis-adjusted
   loss, return to ordinary efficient operating condition after
   deterioration to unusable) True -> "improvement_capitalize" citing the
   specific prong(s). ALL THREE explicitly False -> repair path (steps
   6/7). ANY prong None (and none True) ->
   "open_question_capitalize_pending" — capitalized CONSERVATIVELY with
   flag BAR-FACTS-INCOMPLETE and an OPEN QUESTION naming the missing
   prong(s). NEVER silently deducted on missing facts.
6. Routine maintenance safe harbor (§1.263(a)-3(i)): all BAR False and
   routine_maintenance_expected_more_than_once True ->
   "routine_maintenance_deduct" (expected more than once over the class
   life; buildings: more than once in 10 years). The (i)(3) exclusions
   (e.g. amounts for betterments/restorations under (k)(1)(i)-(vi)) are
   handled by the BAR gate PRECEDING this step. None -> OPEN QUESTION,
   fall to 7.
7. Repair: all BAR explicitly False -> "repair_deduct" (§162;
   §1.263(a)-3(d)). BUT if capitalize_repairs_following_books and
   book_capitalized -> "elective_capitalize_books" (§1.263(a)-3(n) — the
   election is a METHOD that applies to ALL repairs capitalized on books
   that year; items with book_capitalized True and others False while the
   election is on draw the N-ELECTION-CONSISTENCY warning).

The OPEN QUESTIONS list is the point of this engine: every place a
determination needs a fact the schedule does not carry, a precise question
a non-specialist can answer is emitted (never duplicated). Nothing is
silently deducted on missing facts — missing BAR facts capitalize
conservatively until answered.

Elective (n)-election dollars are reported in elective_capitalized_total
(the item row's `capitalized` carries the amount); mandatory improvement
and conservative-pending dollars are in capitalized_total. Totals are
exact Decimal sums — no division occurs, so nothing is quantized.
"""

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

from ..model import _dec

STSH_GROSS_RECEIPTS_CEILING = Decimal("10000000")   # §1.263(a)-3(h)(1)
STSH_BASIS_CEILING = Decimal("1000000")             # §1.263(a)-3(h)(4)
STSH_DOLLAR_CEILING = Decimal("10000")              # §1.263(a)-3(h)(1)
STSH_BASIS_PCT = Decimal("0.02")                    # 2% of unadjusted basis
MS_UNIT_COST_CEILING = Decimal("200")               # §1.162-3(c)(1)(iv) —
# documented for reference; the schedule carries the $200 test as a
# yes/no fact (ms_unit_cost_200_or_less), not a dollar input.


@dataclass
class TangibleExpenditure:
    """One tangible-property expenditure line (repair-regs schedule row).

    BAR facts and the safe-harbor prongs are TRI-STATE: True/False when the
    fact is established, None when the schedule does not carry it — None is
    never treated as False."""
    item_id: str = ""
    description: str = ""
    amount: Decimal = Decimal("0")
    # per-invoice/per-item cost for de minimis testing; None = not provided
    invoice_or_item_cost: Optional[Decimal] = None
    unit_of_property: str = ""     # UOP label; building systems are separate UOPs
    is_building: bool = False
    building_unadjusted_basis: Decimal = Decimal("0")   # (h) safe harbor
    is_material_or_supply: bool = False                 # §1.162-3 candidate
    ms_unit_cost_200_or_less: Optional[bool] = None     # §1.162-3(c)(1)(iv)
    ms_economic_life_12mo_or_less: Optional[bool] = None  # §1.162-3(c)(1)(iii)
    # §1.263(a)-3(i): expected >1x over class life (buildings: >1x in 10 yrs)
    routine_maintenance_expected_more_than_once: Optional[bool] = None
    # BAR facts — True/False/None (None = fact not established):
    betterment: Optional[bool] = None      # §1.263(a)-3(j)
    adaptation: Optional[bool] = None      # §1.263(a)-3(l) new/different use
    restoration: Optional[bool] = None     # §1.263(a)-3(k)
    book_capitalized: bool = False         # follows books ((n) election)
    row_index: int = 0

    def __post_init__(self):
        self.amount = _dec(self.amount)
        self.building_unadjusted_basis = _dec(self.building_unadjusted_basis)
        if self.invoice_or_item_cost is not None:
            self.invoice_or_item_cost = _dec(self.invoice_or_item_cost)


def compute_tangible_263a(
        items: List[TangibleExpenditure], profile, *,
        de_minimis_election: bool = False,
        small_taxpayer_building_election: bool = False,
        capitalize_repairs_following_books: bool = False,
        total_building_repairs_maintenance_improvements:
            Optional[Dict[str, Decimal]] = None) -> dict:
    """Apply the module-docstring decision order to every item.

    Returns {items, open_questions, deductible_total, capitalized_total,
    elective_capitalized_total, warnings}. Tie: deductible_total +
    capitalized_total + elective_capitalized_total == sum of all
    non-sme_review amounts (exact Decimal sums, nothing quantized)."""
    warnings: List[str] = []
    open_questions: List[dict] = []
    seen_questions: set = set()

    def ask(item: TangibleExpenditure, question: str, why: str) -> None:
        if question in seen_questions:
            return
        seen_questions.add(question)
        open_questions.append({"item_id": item.item_id,
                               "question": question, "why": why})

    # --- run-level election-condition warnings (once per run) --------------
    if de_minimis_election and profile.has_afs:
        warnings.append(
            "DE-MINIMIS-POLICY-CONDITION: the §1.263(a)-1(f) de minimis safe "
            "harbor is elected and the taxpayer has an AFS — a WRITTEN "
            "accounting policy expensing amounts under the ceiling, in place "
            "as of the START of the taxable year, is a condition of the "
            "election ((f)(1)(i)(B)). Confirm it exists; the election is "
            "annual, irrevocable, and all-or-nothing for qualifying items.")
    if small_taxpayer_building_election \
            and profile.avg_gross_receipts > STSH_GROSS_RECEIPTS_CEILING:
        warnings.append(
            f"STSH-INELIGIBLE-RECEIPTS: the §1.263(a)-3(h) small-taxpayer "
            f"building safe harbor is elected but average annual gross "
            f"receipts (${profile.avg_gross_receipts:,.0f}) exceed the "
            f"$10,000,000 ceiling — the safe harbor is unavailable; no item "
            f"was deducted under it.")

    # Per-UOP schedule sums — the (h) aggregate FALLBACK when the caller
    # does not supply the explicit per-building totals dict.
    uop_sums: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for it in items:
        if it.unit_of_property and it.amount >= 0:
            uop_sums[it.unit_of_property] += it.amount

    ms_timing_warned = False
    stsh_schedule_agg_warned = False
    repairs_book_capitalized = 0
    repairs_book_expensed = 0

    rows: List[dict] = []
    deductible_total = Decimal("0")
    capitalized_total = Decimal("0")
    elective_capitalized_total = Decimal("0")

    for it in items:
        row = {"item_id": it.item_id, "description": it.description,
               "amount": it.amount, "treatment": "", "authority": "",
               "flags": [], "deductible": Decimal("0"),
               "capitalized": Decimal("0")}
        label = it.item_id or it.description

        # --- 1. negative amount --------------------------------------------
        if it.amount < 0:
            row["treatment"] = "sme_review"
            row["flags"].append("NEGATIVE-AMOUNT")
            warnings.append(
                f"NEGATIVE-AMOUNT [tangible {label}]: ${it.amount:,.2f} — "
                f"nothing computed; route credits/refunds through the "
                f"schedule, not a negative expenditure.")
            rows.append(row)
            continue

        # --- 2. de minimis safe harbor (§1.263(a)-1(f)) ----------------------
        if de_minimis_election:
            if it.invoice_or_item_cost is not None:
                if it.invoice_or_item_cost <= profile.de_minimis_ceiling:
                    row["treatment"] = "de_minimis_deduct"
                    row["authority"] = "Reg. §1.263(a)-1(f); Notice 2015-82"
                    row["deductible"] = it.amount
                    deductible_total += it.amount
                    rows.append(row)
                    continue
            else:
                row["flags"].append("DE-MINIMIS-COST-UNKNOWN")
                ask(it,
                    f"Item {label} '{it.description}': what is the "
                    f"per-invoice (or per-item as substantiated on the "
                    f"invoice) cost (Reg. §1.263(a)-1(f))? Supply "
                    f"invoice_or_item_cost to test it against the "
                    f"${profile.de_minimis_ceiling:,.0f} de minimis ceiling.",
                    "The de minimis election is on but the schedule does "
                    "not carry the per-invoice/per-item cost — the item "
                    "continued down the decision tree conservatively.")
                # fall through — conservative

        # --- 3. materials & supplies (§1.162-3) ------------------------------
        if it.is_material_or_supply:
            if it.ms_unit_cost_200_or_less or it.ms_economic_life_12mo_or_less:
                prongs = []
                if it.ms_unit_cost_200_or_less:
                    prongs.append("§1.162-3(c)(1)(iv) unit cost ≤ $200")
                if it.ms_economic_life_12mo_or_less:
                    prongs.append("§1.162-3(c)(1)(iii) economic life ≤ 12 months")
                row["treatment"] = "materials_supplies_deduct"
                row["authority"] = "; ".join(prongs)
                row["flags"].append("MS-TIMING-NOT-DETERMINED")
                if not ms_timing_warned:
                    ms_timing_warned = True
                    warnings.append(
                        "MS-TIMING-NOT-DETERMINED: materials & supplies were "
                        "deducted under §1.162-3, but the incidental "
                        "(deduct when paid/incurred, (a)(2)) vs "
                        "non-incidental (deduct when used or consumed, "
                        "(a)(1)) TIMING distinction is out of scope for "
                        "this engine — confirm the deduction year per item.")
                row["deductible"] = it.amount
                deductible_total += it.amount
                rows.append(row)
                continue
            if it.ms_unit_cost_200_or_less is None \
                    and it.ms_economic_life_12mo_or_less is None:
                ask(it,
                    f"Item {label} '{it.description}': is the unit "
                    f"acquisition/production cost $200 or less "
                    f"(§1.162-3(c)(1)(iv)), or is the economic useful life "
                    f"12 months or less (§1.162-3(c)(1)(iii))? Answer "
                    f"ms_unit_cost_200_or_less and "
                    f"ms_economic_life_12mo_or_less True/False.",
                    "The item is marked as a materials & supplies "
                    "candidate but neither §1.162-3 prong is established — "
                    "it continued down the decision tree.")
                # fall through

        # --- 4. small taxpayer building safe harbor (§1.263(a)-3(h)) ---------
        if small_taxpayer_building_election and it.is_building:
            eligible = (profile.avg_gross_receipts <= STSH_GROSS_RECEIPTS_CEILING
                        and it.building_unadjusted_basis <= STSH_BASIS_CEILING)
            if not eligible:
                row["flags"].append("STSH-NOT-ELIGIBLE")
            else:
                uop = it.unit_of_property
                explicit = total_building_repairs_maintenance_improvements
                if explicit is not None and uop in explicit:
                    aggregate = _dec(explicit[uop])
                else:
                    aggregate = uop_sums[uop] if uop else it.amount
                    if not stsh_schedule_agg_warned:
                        stsh_schedule_agg_warned = True
                        warnings.append(
                            "STSH-AGGREGATE-FROM-SCHEDULE-ONLY: the "
                            "§1.263(a)-3(h) per-building aggregate was "
                            "summed from the items ON THIS SCHEDULE only — "
                            "the test requires ALL amounts paid during the "
                            "year for repairs, maintenance, and "
                            "improvements on the building, including "
                            "amounts outside this schedule. Supply "
                            "total_building_repairs_maintenance_"
                            "improvements to test the true aggregate.")
                ceiling = min(STSH_DOLLAR_CEILING,
                              STSH_BASIS_PCT * it.building_unadjusted_basis)
                if aggregate <= ceiling:
                    row["treatment"] = "small_taxpayer_sh_deduct"
                    row["authority"] = ("Reg. §1.263(a)-3(h) small taxpayer "
                                        "building safe harbor")
                    row["deductible"] = it.amount
                    deductible_total += it.amount
                    rows.append(row)
                    continue
                row["flags"].append("STSH-CEILING-EXCEEDED")
            # fail eligibility or ceiling -> continue down the tree

        # --- 5. BAR improvement tests (§1.263(a)-3(j)/(l)/(k)) ---------------
        bar_true = []
        if it.betterment:
            bar_true.append("Reg. §1.263(a)-3(j) betterment")
        if it.adaptation:
            bar_true.append("Reg. §1.263(a)-3(l) adaptation to a "
                            "new/different use")
        if it.restoration:
            bar_true.append("Reg. §1.263(a)-3(k) restoration")
        if bar_true:
            row["treatment"] = "improvement_capitalize"
            row["authority"] = "; ".join(bar_true)
            row["capitalized"] = it.amount
            capitalized_total += it.amount
            rows.append(row)
            continue
        missing = []
        prompts = {
            "betterment": ("betterment (§1.263(a)-3(j)) — does the work "
                           "ameliorate a pre-existing material condition or "
                           "defect, or materially add to or increase the "
                           "capacity, productivity, efficiency, strength, or "
                           "quality of the unit of property?"),
            "adaptation": ("adaptation (§1.263(a)-3(l)) — does the work "
                           "adapt the unit of property to a new or different "
                           "use?"),
            "restoration": ("restoration (§1.263(a)-3(k)) — does the work "
                            "replace a major component or substantial "
                            "structural part, restore after a basis-adjusted "
                            "loss, or return the property to ordinary "
                            "efficient operating condition after "
                            "deterioration to a state of disrepair where it "
                            "was no longer functional?"),
        }
        for prong in ("betterment", "adaptation", "restoration"):
            if getattr(it, prong) is None:
                missing.append(prong)
        if missing:
            row["treatment"] = "open_question_capitalize_pending"
            row["authority"] = ("Reg. §1.263(a)-3(d)/(j)/(k)/(l) — "
                                "improvement facts pending; capitalized "
                                "conservatively")
            row["flags"].append("BAR-FACTS-INCOMPLETE")
            row["capitalized"] = it.amount
            capitalized_total += it.amount
            ask(it,
                f"Item {label} '{it.description}': the following "
                f"improvement facts are not established: "
                f"{', '.join(missing)}. Answer each True/False: "
                + " ".join(prompts[p] for p in missing),
                "Any single True prong requires capitalization as an "
                "improvement (§1.263(a)-3(d)(2)); all-False opens the "
                "repair / routine-maintenance path. The amount is "
                "capitalized CONSERVATIVELY pending the answer — never "
                "silently deducted on missing facts.")
            rows.append(row)
            continue

        # --- 6. routine maintenance safe harbor (§1.263(a)-3(i)) -------------
        # (all BAR explicitly False from here down; the (i)(3) exclusions
        # are handled by the BAR gate above.)
        if it.routine_maintenance_expected_more_than_once:
            row["treatment"] = "routine_maintenance_deduct"
            row["authority"] = ("Reg. §1.263(a)-3(i) routine maintenance "
                                "safe harbor")
            row["deductible"] = it.amount
            deductible_total += it.amount
            rows.append(row)
            continue
        if it.routine_maintenance_expected_more_than_once is None:
            ask(it,
                f"Item {label} '{it.description}': at the time the unit of "
                f"property was placed in service, was this maintenance "
                f"expected to be performed more than once over the "
                f"property's class life (for a building: more than once in "
                f"10 years) (§1.263(a)-3(i))? Answer "
                f"routine_maintenance_expected_more_than_once True/False.",
                "All BAR prongs are False, so the amount is deductible "
                "either way — the answer only settles whether the routine "
                "maintenance safe harbor or the general repair rule is the "
                "cited authority.")
            # fall to 7

        # --- 7. repair (§162; §1.263(a)-3(d)) / (n) election ------------------
        if capitalize_repairs_following_books and it.book_capitalized:
            repairs_book_capitalized += 1
            row["treatment"] = "elective_capitalize_books"
            row["authority"] = ("Reg. §1.263(a)-3(n) election to capitalize "
                                "repairs capitalized on books")
            row["capitalized"] = it.amount
            elective_capitalized_total += it.amount
            rows.append(row)
            continue
        if capitalize_repairs_following_books:
            repairs_book_expensed += 1
        row["treatment"] = "repair_deduct"
        row["authority"] = "§162; Reg. §1.263(a)-3(d)"
        row["deductible"] = it.amount
        deductible_total += it.amount
        rows.append(row)

    if capitalize_repairs_following_books \
            and repairs_book_capitalized and repairs_book_expensed:
        warnings.append(
            "N-ELECTION-CONSISTENCY: the §1.263(a)-3(n) election is on, but "
            "some repair items are capitalized on books and others are not "
            "— the election applies to ALL amounts paid for repair and "
            "maintenance capitalized on the books and records for the year. "
            "Verify the book treatment of every repair line is consistent "
            "with the election.")

    return {"items": rows,
            "open_questions": open_questions,
            "deductible_total": deductible_total,
            "capitalized_total": capitalized_total,
            "elective_capitalized_total": elective_capitalized_total,
            "warnings": warnings}
