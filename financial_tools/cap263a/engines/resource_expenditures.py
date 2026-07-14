"""Resource expenditures — IDC (§263(c)/§263(i)/§291(b)), mining
exploration and development (§617/§616/§291(b)), and circulation
expenditures (§173).

Three compute functions share this module; each returns
{items, amortizable_items, open_questions, deductible_total,
capitalized_total, warnings}. Dollar totals are exact Decimal sums; the
only division in the module is the §291(b) 30%/70% cutback split, which
quantizes the 30% (capitalized) side to cents ROUND_HALF_EVEN and makes
the 70% (deducted) side the plug, so the two sides always sum exactly to
the item amount. Items capitalized CONSERVATIVELY pending an open
question are counted in capitalized_total but post NOTHING to the
amortization schedule until the fact is established.

DECISION ORDER — compute_idc (per item):
1. NEGATIVE amount -> flag NEGATIVE-AMOUNT, treatment "sme_review",
   nothing computed (house pattern: a cost cannot be negative).
2. operator_or_working_interest None -> OPEN QUESTION (Reg. §1.612-4(a):
   the IDC option is available only to an OPERATOR holding a working or
   operating interest) + conservative capitalize
   ("open_question_capitalize_pending", flag IDC-INTEREST-STATUS-UNKNOWN).
   Explicitly False -> not IDC-eligible: "capitalize_no_working_interest"
   (AmortizableItem, recovery_months=None — recovery follows the
   underlying property).
3. FOREIGN well (§263(i)): NO current expensing regardless of the §263(c)
   election. ten_year_election_263i True -> "capitalize_263i_10yr": an
   AmortizableItem amortized straight-line over 120 months
   (§263(i)(2)(B)); month_incurred 1-12 -> convention "full-month" with
   the start month noted, unknown -> "mid-year" proxy + flag
   MONTH-UNKNOWN-MIDYEAR-PROXY (same documented-proxy pattern as
   qualified_expenditures.py). ten_year_election_263i False ->
   "capitalize_263i": capitalized to the property's depletable/
   depreciable basis (AmortizableItem, recovery_months=None), flags
   RECOVERY-VIA-DEPLETION-OUT-OF-SCOPE and
   COST-DEPLETION-ALTERNATIVE-NOT-MODELED — the §263(i)(2)(A)
   alternative election to recover the costs through cost depletion is
   NOT modeled here. (Foreign dry holes stay under §263(i); the
   §1.612-4(b)(4) dry-hole interaction with §263(i) is not modeled.)
4. DOMESTIC: expense_election None -> OPEN QUESTION (the §263(c) option
   is a BINDING election made with the first return containing IDC —
   answer True/False) + conservative capitalize
   ("open_question_capitalize_pending", flag IDC-ELECTION-UNKNOWN).
   True -> deduct ("idc_expensed_263c"), EXCEPT the §291(b)(1)
   integrated-producer cutback: if is_integrated_producer, 30% of the
   otherwise-deductible IDC is capitalized and amortized ratably over 60
   MONTHS beginning with the month paid/incurred (§291(b)(2)) —
   treatment "idc_expensed_263c_291b_cutback", 70% deducted
   (month_incurred known -> "full-month", else mid-year proxy + flag).
   §291(b)(1)(A)'s exception for nonproductive-well IDC is NOT modeled:
   the cutback is applied uniformly (conservative), with warning
   291B-NONPRODUCTIVE-EXCEPTION-NOT-MODELED when it bites.
   False -> "capitalize_no_election" (recovery via depletion —
   AmortizableItem, recovery_months=None, flag
   RECOVERY-VIA-DEPLETION-OUT-OF-SCOPE), EXCEPT step 5:
5. nonproductive_well under the expense_election=False posture: the
   DRY-HOLE election (Reg. §1.612-4(b)(4)) still permits deduction when
   the well is plugged/abandoned -> "dry_hole_deduct", flag
   DRY-HOLE-DEDUCTIBLE, + warning DRY-HOLE-ELECTION-CONFIRM (once per
   run) to confirm the dry-hole election posture. Under expensing, moot.

DECISION ORDER — compute_mining (per item):
1. NEGATIVE amount -> NEGATIVE-AMOUNT, "sme_review", nothing computed.
2. foreign True -> §617(h)/§616(d) foreign rules (10-year amortization /
   basis adjustments) are NOT implemented: treatment "sme_review" +
   warning FOREIGN-MINING-NOT-IMPLEMENTED, nothing computed (honest
   stub).
3. kind not "exploration"/"development" -> "sme_review" + warning
   MINING-KIND-UNKNOWN, nothing computed.
4. Development (§616): DEFAULT is current deduction under §616(a) — no
   election needed -> "development_deducted_616a" (subject to step 6).
   defer_election_616b True -> §616(b) deferred expenses are deducted
   ratably as the benefited ore/mineral is sold; units-of-production is
   NOT modeled: "capitalize_616b_deferred", AmortizableItem with
   recovery_months=None, flag 616B-UNITS-OF-PRODUCTION-NOT-MODELED +
   OPEN QUESTION asking for the units schedule.
5. Exploration (§617): expense_election_617 True ->
   "exploration_deducted_617a" (subject to step 6), with warning
   617B-RECAPTURE-NOT-COMPUTED (once per run — §617(b) recapture when
   the mine reaches the producing stage is not computed). False ->
   "capitalize_no_election_617" (depletion recovery — AmortizableItem,
   recovery_months=None, flag RECOVERY-VIA-DEPLETION-OUT-OF-SCOPE).
   None -> OPEN QUESTION + conservative capitalize
   ("open_question_capitalize_pending", flag 617-ELECTION-UNKNOWN).
6. §291(b)(1) corporate cutback: if is_corporate, 30% of amounts
   otherwise DEDUCTED under §616(a)/§617(a) is capitalized and amortized
   over 60 months (same mechanics/flags as compute_idc's cutback; the
   mining schedule carries no month data, so always the mid-year proxy +
   MONTH-UNKNOWN-MIDYEAR-PROXY); 70% deducted. Treatments
   "development_deducted_616a_291b_cutback" /
   "exploration_deducted_617a_291b_cutback".

DECISION ORDER — compute_circulation (per item):
1. NEGATIVE amount -> NEGATIVE-AMOUNT, "sme_review", nothing computed.
2. DEFAULT (§173): deduct -> "circulation_deducted_173".
3. capitalize_election (Reg. §1.173-1(c) election to capitalize) ->
   "capitalize_173_election", AmortizableItem with recovery_months=None,
   flag CIRCULATION-RECOVERY-SME.
4. In BOTH branches (once per run, when any item computed): the §59(e)
   3-year (36-month) ratable alternative exists — the tool's §59(e)
   engine (qualified_expenditures.compute_59e) handles it; informational
   warning CIRCULATION-59E-ALTERNATIVE points there.

Every place a determination needs a fact the schedule does not carry, a
precise question a non-specialist can answer is emitted (never
duplicated). Nothing is silently deducted on missing facts — missing
election/status facts capitalize conservatively until answered.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
from typing import List, Optional

from ..model import AmortizableItem, _dec

CENTS = Decimal("0.01")
CUTBACK_RATE = Decimal("0.30")        # §291(b)(1) — 30% capitalized
CUTBACK_MONTHS = 60                   # §291(b)(2) — 60-month ratable
FOREIGN_IDC_MONTHS = 120              # §263(i)(2)(B) — 10 taxable years


@dataclass
class IDCItem:
    """One intangible drilling & development cost line (per well)."""
    item_id: str = ""
    description: str = ""
    amount: Decimal = Decimal("0")
    foreign: bool = False                       # §263(i) well outside the U.S.
    nonproductive_well: bool = False            # dry hole
    # Reg. §1.612-4(a) gate — tri-state; None = fact not established:
    operator_or_working_interest: Optional[bool] = None
    ten_year_election_263i: bool = False        # §263(i)(2)(B) 120-month
    month_incurred: int = 0                     # 1-12; 0 = unknown

    def __post_init__(self):
        self.amount = _dec(self.amount)


@dataclass
class MiningItem:
    """One mining exploration (§617) or development (§616) cost line."""
    item_id: str = ""
    description: str = ""
    amount: Decimal = Decimal("0")
    kind: str = ""                              # "exploration" | "development"
    foreign: bool = False
    # §617(a) election — exploration only; tri-state (None = not established):
    expense_election_617: Optional[bool] = None
    defer_election_616b: bool = False           # development only

    def __post_init__(self):
        self.amount = _dec(self.amount)


@dataclass
class CirculationItem:
    """One §173 circulation expenditure line."""
    item_id: str = ""
    description: str = ""
    amount: Decimal = Decimal("0")

    def __post_init__(self):
        self.amount = _dec(self.amount)


def _split_291b(amount: Decimal):
    """§291(b)(1) 30/70 split. The 30% (capitalized) side quantizes to
    cents ROUND_HALF_EVEN; the 70% (deducted) side is the plug, so
    thirty + seventy == amount exactly (e.g. 100.01 -> 30.00 / 70.01)."""
    thirty = (amount * CUTBACK_RATE).quantize(CENTS, rounding=ROUND_HALF_EVEN)
    return thirty, amount - thirty


def _monthly_amortizable(*, item_id, description, basis, months,
                         month_incurred, start_year, source, authority,
                         note=""):
    """AmortizableItem with the module's month convention: month known
    (1-12) -> full-month with the start month noted; unknown -> mid-year
    proxy + MONTH-UNKNOWN-MIDYEAR-PROXY (documented-proxy pattern shared
    with qualified_expenditures.py)."""
    flags: List[str] = []
    if 1 <= month_incurred <= 12:
        convention = "full-month"
        month_note = (f"Amortization begins with month {month_incurred} of "
                      f"{start_year} (start month noted; full-month "
                      f"convention).")
    else:
        convention = "mid-year"
        flags.append("MONTH-UNKNOWN-MIDYEAR-PROXY")
        month_note = ("Mid-year start is a documented proxy — the schedule "
                      "does not carry the month paid/incurred.")
    return AmortizableItem(
        item_id=item_id, description=description,
        category="resource_expenditure", basis=basis,
        recovery_months=months, convention=convention, start_year=start_year,
        source=source, authority=authority, flags=flags,
        notes=(note + " " + month_note).strip())


def _basis_amortizable(*, item_id, description, basis, start_year, source,
                       authority, flags=(), note=""):
    """Capitalized-to-basis record: recovery_months=None (recovery follows
    the underlying property — depletion/depreciation, out of scope)."""
    return AmortizableItem(
        item_id=item_id, description=description,
        category="resource_expenditure", basis=basis, recovery_months=None,
        convention="none", start_year=start_year, source=source,
        authority=authority, flags=list(flags), notes=note)


def _new_row(it) -> dict:
    return {"item_id": it.item_id, "description": it.description,
            "amount": it.amount, "treatment": "", "authority": "",
            "flags": [], "deductible": Decimal("0"),
            "capitalized": Decimal("0")}


# ---------------------------------------------------------------------------
# A) IDC — §263(c) / §263(i) / §291(b)
# ---------------------------------------------------------------------------

def compute_idc(items: List[IDCItem], *,
                is_integrated_producer: bool = False,
                expense_election: Optional[bool] = None,
                current_tax_year: int = 2026) -> dict:
    """Apply the module-docstring compute_idc decision order to every item.

    Returns {items, amortizable_items, open_questions, deductible_total,
    capitalized_total, warnings}. Tie: deductible_total +
    capitalized_total == sum of all non-sme_review amounts."""
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
    deductible_total = Decimal("0")
    capitalized_total = Decimal("0")
    dry_hole_warned = False
    nonproductive_cutback_warned = False

    for it in items:
        row = _new_row(it)
        label = it.item_id or it.description

        # --- 1. negative amount ------------------------------------------
        if it.amount < 0:
            row["treatment"] = "sme_review"
            row["flags"].append("NEGATIVE-AMOUNT")
            warnings.append(
                f"NEGATIVE-AMOUNT [idc {label}]: ${it.amount:,.2f} — nothing "
                f"computed; route credits/refunds through the schedule, not "
                f"a negative expenditure.")
            rows.append(row)
            continue

        # --- 2. working/operating interest (Reg. §1.612-4(a)) -------------
        if it.operator_or_working_interest is None:
            row["treatment"] = "open_question_capitalize_pending"
            row["authority"] = ("Reg. §1.612-4(a) — working-interest status "
                                "pending; capitalized conservatively")
            row["flags"].append("IDC-INTEREST-STATUS-UNKNOWN")
            row["capitalized"] = it.amount
            capitalized_total += it.amount
            ask(it.item_id,
                f"Item {label} '{it.description}': does the taxpayer hold a "
                f"working or operating interest in the well and act as "
                f"operator (Reg. §1.612-4(a))? The IDC option is available "
                f"only to an operator holding a working/operating interest — "
                f"answer operator_or_working_interest True/False.",
                "The IDC option's threshold condition is not established — "
                "the amount is capitalized CONSERVATIVELY pending the "
                "answer; never silently deducted on missing facts.")
            rows.append(row)
            continue
        if it.operator_or_working_interest is False:
            row["treatment"] = "capitalize_no_working_interest"
            row["authority"] = ("Reg. §1.612-4(a) — no working/operating "
                                "interest; not IDC-eligible")
            row["capitalized"] = it.amount
            capitalized_total += it.amount
            amortizable.append(_basis_amortizable(
                item_id=it.item_id,
                description=f"IDC (no working interest) — {it.description}",
                basis=it.amount, start_year=current_tax_year,
                source="resource_expenditures compute_idc",
                authority="Reg. §1.612-4(a)",
                note="Not IDC-eligible (no working/operating interest) — "
                     "capitalized to the property's basis; recovery follows "
                     "the underlying property."))
            rows.append(row)
            continue

        # --- 3. foreign wells (§263(i)) -----------------------------------
        if it.foreign:
            if it.ten_year_election_263i:
                row["treatment"] = "capitalize_263i_10yr"
                row["authority"] = ("§263(i)(2)(B) — 120-month ratable "
                                    "amortization (foreign IDC)")
                item = _monthly_amortizable(
                    item_id=it.item_id,
                    description=f"Foreign IDC §263(i) 10-year — "
                                f"{it.description}",
                    basis=it.amount, months=FOREIGN_IDC_MONTHS,
                    month_incurred=it.month_incurred,
                    start_year=current_tax_year,
                    source="resource_expenditures compute_idc",
                    authority="§263(i)(2)(B)",
                    note="§263(c) expensing is unavailable for a well "
                         "outside the U.S. (§263(i)).")
                row["flags"].extend(item.flags)
                amortizable.append(item)
            else:
                row["treatment"] = "capitalize_263i"
                row["authority"] = ("§263(i)(2)(A) — capitalized to "
                                    "depletable/depreciable basis "
                                    "(foreign IDC)")
                row["flags"].extend(["RECOVERY-VIA-DEPLETION-OUT-OF-SCOPE",
                                     "COST-DEPLETION-ALTERNATIVE-NOT-MODELED"])
                amortizable.append(_basis_amortizable(
                    item_id=it.item_id,
                    description=f"Foreign IDC §263(i) basis — "
                                f"{it.description}",
                    basis=it.amount, start_year=current_tax_year,
                    source="resource_expenditures compute_idc",
                    authority="§263(i)(2)(A)",
                    flags=["RECOVERY-VIA-DEPLETION-OUT-OF-SCOPE",
                           "COST-DEPLETION-ALTERNATIVE-NOT-MODELED"],
                    note="The §263(i)(2)(A) alternative election to recover "
                         "the costs through cost depletion is NOT modeled — "
                         "recovery via depletion is out of scope."))
            row["capitalized"] = it.amount
            capitalized_total += it.amount
            rows.append(row)
            continue

        # --- 4. domestic — §263(c) election posture -----------------------
        if expense_election is None:
            row["treatment"] = "open_question_capitalize_pending"
            row["authority"] = ("§263(c); Reg. §1.612-4 — election posture "
                                "pending; capitalized conservatively")
            row["flags"].append("IDC-ELECTION-UNKNOWN")
            row["capitalized"] = it.amount
            capitalized_total += it.amount
            ask(it.item_id,
                "Has the taxpayer made (or will it make with this return) "
                "the §263(c) option to expense intangible drilling and "
                "development costs? The option is a BINDING election made "
                "with the first return containing IDC — answer "
                "expense_election True/False.",
                "expense_election is not established; every domestic IDC "
                "item is capitalized CONSERVATIVELY pending the answer — "
                "never silently deducted on missing facts.")
            rows.append(row)
            continue

        if expense_election:
            if is_integrated_producer:
                thirty, seventy = _split_291b(it.amount)
                row["treatment"] = "idc_expensed_263c_291b_cutback"
                row["authority"] = ("§263(c); §291(b)(1)-(2) integrated-"
                                    "producer 30% cutback")
                row["deductible"] = seventy
                row["capitalized"] = thirty
                deductible_total += seventy
                capitalized_total += thirty
                item = _monthly_amortizable(
                    item_id=it.item_id,
                    description=f"§291(b) IDC cutback (30%) — "
                                f"{it.description}",
                    basis=thirty, months=CUTBACK_MONTHS,
                    month_incurred=it.month_incurred,
                    start_year=current_tax_year,
                    source="resource_expenditures compute_idc",
                    authority="§291(b)(2)",
                    note="30% of otherwise-deductible IDC capitalized, "
                         "amortized ratably over 60 months beginning with "
                         "the month paid/incurred.")
                row["flags"].extend(item.flags)
                amortizable.append(item)
                if it.nonproductive_well and not nonproductive_cutback_warned:
                    nonproductive_cutback_warned = True
                    warnings.append(
                        "291B-NONPRODUCTIVE-EXCEPTION-NOT-MODELED: "
                        "§291(b)(1)(A) excepts nonproductive-well IDC from "
                        "the integrated-producer cutback, but this engine "
                        "applies the 30% cutback uniformly (conservative) — "
                        "SME review to restore the exception where it "
                        "applies.")
            else:
                row["treatment"] = "idc_expensed_263c"
                row["authority"] = "§263(c); Reg. §1.612-4(a)"
                row["deductible"] = it.amount
                deductible_total += it.amount
            rows.append(row)
            continue

        # expense_election is False — capitalize posture.
        # --- 5. dry hole (Reg. §1.612-4(b)(4)) -----------------------------
        if it.nonproductive_well:
            row["treatment"] = "dry_hole_deduct"
            row["authority"] = "Reg. §1.612-4(b)(4) dry-hole election"
            row["flags"].append("DRY-HOLE-DEDUCTIBLE")
            row["deductible"] = it.amount
            deductible_total += it.amount
            if not dry_hole_warned:
                dry_hole_warned = True
                warnings.append(
                    "DRY-HOLE-ELECTION-CONFIRM: nonproductive-well IDC was "
                    "deducted under the Reg. §1.612-4(b)(4) dry-hole "
                    "election notwithstanding the capitalize posture "
                    "(expense_election=False) — confirm the dry-hole "
                    "election posture and that each well was plugged and "
                    "abandoned in the year deducted.")
            rows.append(row)
            continue

        row["treatment"] = "capitalize_no_election"
        row["authority"] = ("§263(c) not elected — capitalized to "
                            "depletable/depreciable basis")
        row["flags"].append("RECOVERY-VIA-DEPLETION-OUT-OF-SCOPE")
        row["capitalized"] = it.amount
        capitalized_total += it.amount
        amortizable.append(_basis_amortizable(
            item_id=it.item_id,
            description=f"IDC capitalized (no §263(c) election) — "
                        f"{it.description}",
            basis=it.amount, start_year=current_tax_year,
            source="resource_expenditures compute_idc",
            authority="§263(c); Reg. §1.612-4",
            flags=["RECOVERY-VIA-DEPLETION-OUT-OF-SCOPE"],
            note="Recovery via depletion is out of scope — the basis "
                 "attaches to the depletable property."))
        rows.append(row)

    return {"items": rows, "amortizable_items": amortizable,
            "open_questions": open_questions,
            "deductible_total": deductible_total,
            "capitalized_total": capitalized_total,
            "warnings": warnings}


# ---------------------------------------------------------------------------
# B) Mining — §616 / §617 / §291(b)
# ---------------------------------------------------------------------------

def compute_mining(items: List[MiningItem], *,
                   is_corporate: bool = False,
                   current_tax_year: int = 2026) -> dict:
    """Apply the module-docstring compute_mining decision order to every
    item. Returns {items, amortizable_items, open_questions,
    deductible_total, capitalized_total, warnings}. Tie: deductible_total
    + capitalized_total == sum of all non-sme_review amounts."""
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
    deductible_total = Decimal("0")
    capitalized_total = Decimal("0")
    recapture_warned = False

    def cutback(it, row, base_treatment: str, authority: str) -> None:
        """Deduct the item, applying the §291(b)(1) corporate 30% cutback
        when is_corporate (60-month AmortizableItem; the mining schedule
        carries no month data, so always the mid-year proxy)."""
        nonlocal deductible_total, capitalized_total
        if is_corporate:
            thirty, seventy = _split_291b(it.amount)
            row["treatment"] = base_treatment + "_291b_cutback"
            row["authority"] = authority + "; §291(b)(1)-(2) corporate 30% cutback"
            row["deductible"] = seventy
            row["capitalized"] = thirty
            deductible_total += seventy
            capitalized_total += thirty
            item = _monthly_amortizable(
                item_id=it.item_id,
                description=f"§291(b) mining cutback (30%) — "
                            f"{it.description}",
                basis=thirty, months=CUTBACK_MONTHS, month_incurred=0,
                start_year=current_tax_year,
                source="resource_expenditures compute_mining",
                authority="§291(b)(2)",
                note="30% of the amount otherwise deducted under "
                     "§616(a)/§617(a) capitalized, amortized ratably over "
                     "60 months.")
            row["flags"].extend(item.flags)
            amortizable.append(item)
        else:
            row["treatment"] = base_treatment
            row["authority"] = authority
            row["deductible"] = it.amount
            deductible_total += it.amount

    for it in items:
        row = _new_row(it)
        label = it.item_id or it.description

        # --- 1. negative amount ------------------------------------------
        if it.amount < 0:
            row["treatment"] = "sme_review"
            row["flags"].append("NEGATIVE-AMOUNT")
            warnings.append(
                f"NEGATIVE-AMOUNT [mining {label}]: ${it.amount:,.2f} — "
                f"nothing computed; route credits/refunds through the "
                f"schedule, not a negative expenditure.")
            rows.append(row)
            continue

        # --- 2. foreign — honest stub (§617(h)/§616(d)) --------------------
        if it.foreign:
            row["treatment"] = "sme_review"
            row["flags"].append("FOREIGN-MINING-NOT-IMPLEMENTED")
            warnings.append(
                f"FOREIGN-MINING-NOT-IMPLEMENTED [mining {label}]: the "
                f"§617(h)/§616(d) foreign exploration/development rules "
                f"(10-year amortization / basis adjustments) are NOT "
                f"implemented — nothing computed; SME review.")
            rows.append(row)
            continue

        # --- 3. kind guard --------------------------------------------------
        if it.kind not in ("exploration", "development"):
            row["treatment"] = "sme_review"
            row["flags"].append("MINING-KIND-UNKNOWN")
            warnings.append(
                f"MINING-KIND-UNKNOWN [mining {label}]: kind={it.kind!r} is "
                f"not 'exploration' or 'development' — nothing computed.")
            rows.append(row)
            continue

        # --- 4. development (§616) ------------------------------------------
        if it.kind == "development":
            if it.defer_election_616b:
                row["treatment"] = "capitalize_616b_deferred"
                row["authority"] = ("§616(b) — deferred; deducted ratably "
                                    "as benefited ore/mineral is sold")
                row["flags"].append("616B-UNITS-OF-PRODUCTION-NOT-MODELED")
                row["capitalized"] = it.amount
                capitalized_total += it.amount
                amortizable.append(_basis_amortizable(
                    item_id=it.item_id,
                    description=f"§616(b) deferred development — "
                                f"{it.description}",
                    basis=it.amount, start_year=current_tax_year,
                    source="resource_expenditures compute_mining",
                    authority="§616(b)",
                    flags=["616B-UNITS-OF-PRODUCTION-NOT-MODELED"],
                    note="§616(b) deferred expenses are deducted ratably as "
                         "the benefited ore or mineral is sold — "
                         "units-of-production is NOT modeled; supply the "
                         "units schedule."))
                ask(it.item_id,
                    f"Item {label} '{it.description}': §616(b) deferral is "
                    f"elected — supply the units-of-production schedule "
                    f"(benefited ore/mineral units sold this year vs. total "
                    f"recoverable units) so the ratable §616(b) deduction "
                    f"can be computed.",
                    "Units-of-production recovery is not modeled — the "
                    "deferred amount is carried with no recovery period "
                    "until the schedule is supplied.")
                rows.append(row)
                continue
            cutback(it, row, "development_deducted_616a",
                    "§616(a) — current deduction (default, no election "
                    "needed)")
            rows.append(row)
            continue

        # --- 5. exploration (§617) ------------------------------------------
        if it.expense_election_617 is None:
            row["treatment"] = "open_question_capitalize_pending"
            row["authority"] = ("§617(a) — election posture pending; "
                                "capitalized conservatively")
            row["flags"].append("617-ELECTION-UNKNOWN")
            row["capitalized"] = it.amount
            capitalized_total += it.amount
            ask(it.item_id,
                "Has the taxpayer elected under §617(a) to deduct mining "
                "exploration expenditures? Answer expense_election_617 "
                "True/False.",
                "expense_election_617 is not established; exploration items "
                "are capitalized CONSERVATIVELY pending the answer — never "
                "silently deducted on missing facts.")
            rows.append(row)
            continue
        if it.expense_election_617:
            if not recapture_warned:
                recapture_warned = True
                warnings.append(
                    "617B-RECAPTURE-NOT-COMPUTED: exploration expenditures "
                    "were deducted under §617(a) — the §617(b) recapture "
                    "when the mine reaches the producing stage is NOT "
                    "computed by this engine; track deducted exploration by "
                    "mine for recapture.")
            cutback(it, row, "exploration_deducted_617a", "§617(a)")
            rows.append(row)
            continue
        row["treatment"] = "capitalize_no_election_617"
        row["authority"] = ("§617(a) not elected — capitalized (depletion "
                            "recovery)")
        row["flags"].append("RECOVERY-VIA-DEPLETION-OUT-OF-SCOPE")
        row["capitalized"] = it.amount
        capitalized_total += it.amount
        amortizable.append(_basis_amortizable(
            item_id=it.item_id,
            description=f"Exploration capitalized (no §617(a) election) — "
                        f"{it.description}",
            basis=it.amount, start_year=current_tax_year,
            source="resource_expenditures compute_mining",
            authority="§617(a)",
            flags=["RECOVERY-VIA-DEPLETION-OUT-OF-SCOPE"],
            note="Recovery via depletion is out of scope — the basis "
                 "attaches to the mineral property."))
        rows.append(row)

    return {"items": rows, "amortizable_items": amortizable,
            "open_questions": open_questions,
            "deductible_total": deductible_total,
            "capitalized_total": capitalized_total,
            "warnings": warnings}


# ---------------------------------------------------------------------------
# C) Circulation — §173
# ---------------------------------------------------------------------------

def compute_circulation(items: List[CirculationItem], *,
                        capitalize_election: bool = False,
                        current_tax_year: int = 2026) -> dict:
    """Apply the module-docstring compute_circulation decision order.
    Returns {items, amortizable_items, open_questions, deductible_total,
    capitalized_total, warnings}. Tie: deductible_total +
    capitalized_total == sum of all non-sme_review amounts."""
    warnings: List[str] = []
    rows: List[dict] = []
    amortizable: List[AmortizableItem] = []
    deductible_total = Decimal("0")
    capitalized_total = Decimal("0")
    fiftynine_e_noted = False

    for it in items:
        row = _new_row(it)
        label = it.item_id or it.description

        # --- 1. negative amount ------------------------------------------
        if it.amount < 0:
            row["treatment"] = "sme_review"
            row["flags"].append("NEGATIVE-AMOUNT")
            warnings.append(
                f"NEGATIVE-AMOUNT [circulation {label}]: ${it.amount:,.2f} "
                f"— nothing computed; route credits/refunds through the "
                f"schedule, not a negative expenditure.")
            rows.append(row)
            continue

        # --- 4. §59(e) alternative note (once per run, BOTH branches) ------
        if not fiftynine_e_noted:
            fiftynine_e_noted = True
            warnings.append(
                "CIRCULATION-59E-ALTERNATIVE: §59(e) offers an elective "
                "3-year (36-month) ratable amortization alternative for "
                "circulation expenditures — the tool's §59(e) engine "
                "(qualified_expenditures.compute_59e) handles it; route "
                "any elected items there (informational).")

        if capitalize_election:
            # --- 3. Reg. §1.173-1(c) election to capitalize ----------------
            row["treatment"] = "capitalize_173_election"
            row["authority"] = "Reg. §1.173-1(c) election to capitalize"
            row["flags"].append("CIRCULATION-RECOVERY-SME")
            row["capitalized"] = it.amount
            capitalized_total += it.amount
            amortizable.append(_basis_amortizable(
                item_id=it.item_id,
                description=f"Circulation capitalized (§1.173-1(c)) — "
                            f"{it.description}",
                basis=it.amount, start_year=current_tax_year,
                source="resource_expenditures compute_circulation",
                authority="Reg. §1.173-1(c)",
                flags=["CIRCULATION-RECOVERY-SME"],
                note="Recovery period/method for capitalized circulation "
                     "expenditures requires SME determination."))
        else:
            # --- 2. §173 default: deduct -----------------------------------
            row["treatment"] = "circulation_deducted_173"
            row["authority"] = "§173"
            row["deductible"] = it.amount
            deductible_total += it.amount
        rows.append(row)

    return {"items": rows, "amortizable_items": amortizable,
            "open_questions": [],
            "deductible_total": deductible_total,
            "capitalized_total": capitalized_total,
            "warnings": warnings}
