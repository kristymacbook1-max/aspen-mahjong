"""Phase G — §1.263(a)-4/-5 intangibles + transaction costs, §195/§248/§709
start-up/organizational costs, and the §280B demolition router.

Mechanics (BUILD_PLAN.md Phase G):
- §1.263(a)-5 transaction costs: inherently facilitative amounts ALWAYS
  capitalize; non-inherently-facilitative amounts in a covered transaction
  incurred BEFORE the bright-line date are investigatory (deductible);
  on/after, capitalize. Success-based fees in a covered transaction with a
  Rev. Proc. 2011-29 election: 70% deductible / 30% capitalized
  (per-transaction, IRREVOCABLE). Abandoned transaction: capitalized-to-date
  amounts become a deductible loss (Rev. Rul. 73-580). Non-covered,
  non-facilitative: deductible under §162.
- §1.263(a)-4 intangibles: 12-month rule ((f)) — no capitalization when the
  benefit ends on/before the EARLIER of (a) 12 months after first
  realization and (b) the end of the taxable year following the payment
  year. CALENDAR-YEAR ASSUMPTION: prong (b)'s "end of the taxable year" is
  computed as December 31 of payment_year + 1 (fiscal-year taxpayers need a
  year-end input this schedule does not carry). $5,000 facilitative-cost
  de minimis ((e)(4)) is a CLIFF per transaction: aggregate ≤ $5,000 →
  deductible; one dollar over → the ENTIRE amount capitalizes (no partial).
  Acquired-with-a-business intangibles → §197, 180-month straight-line,
  full-month convention; other capitalized intangibles amortize over the
  benefit term when both dates are present, else recovery is per-item SME
  work (INDEFINITE-LIFE-SME-REVIEW), not a default.
- §195/§248/§709: $5,000 first-year deduction phased out dollar-for-dollar
  above $50,000 of total costs; remainder straight-line over 180 months
  beginning with the business-commencement month (first-year amortization =
  remainder × months-in-service/180, months-in-service = 12 − month + 1,
  calendar-year assumption). §709(b) SYNDICATION costs are PERMANENTLY
  capitalized — no $5,000, no amortization, no deduction short of complete
  liquidation.
- §280B (route_demolition): demolition cost AND remaining structure basis
  capitalize to LAND (no recovery period) — never a deductible loss; the
  Notice 90-21 casualty carve-out is flagged for SME confirmation, never
  auto-applied.

Basis reconciliation (Runtime Pipeline Step 3b): IntangibleItem.
prior_capitalized_basis feeds the shared reconcile() helper — only the
tax-required-minus-prior DELTA posts; the gross stays on the item row.
"""

import calendar
from datetime import date
from decimal import Decimal
from typing import FrozenSet, List, Optional

from ..model import (AmortizableItem, IntangibleItem, StartupOrgCostPool,
                     TransactionCostItem)
from .basis_reconciliation import reconcile

FACILITATIVE_DE_MINIMIS = Decimal("5000")    # §1.263(a)-4(e)(4) cliff
STARTUP_FIRST_YEAR_CAP = Decimal("5000")     # §195(b)(1)(A)/§248/§709
STARTUP_PHASEOUT_START = Decimal("50000")
STARTUP_RECOVERY_MONTHS = 180                # §195(b)(1)(B): 15 years
SEC197_RECOVERY_MONTHS = 180                 # §197(a): 15 years


def _add_months(d: date, months: int) -> date:
    """d + months, day clamped to the target month's length."""
    y, m = divmod(d.year * 12 + (d.month - 1) + months, 12)
    m += 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def _months_between(start: date, end: date) -> int:
    """Whole months start→end; a partial trailing month rounds UP (the
    benefit runs into that month, so the recovery period covers it)."""
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day > start.day:
        months += 1
    return months


def _twelve_month_rule_passes(it: IntangibleItem) -> Optional[bool]:
    """§1.263(a)-4(f): True = NOT capitalized. None = insufficient dates.
    EARLIER OF (a) benefit_start + 12 months and (b) December 31 of
    payment_year + 1 (calendar-year assumption — see module docstring)."""
    if not it.benefit_start or not it.benefit_end or not it.payment_year:
        return None
    prong_a = _add_months(it.benefit_start, 12)
    prong_b = date(it.payment_year + 1, 12, 31)
    return it.benefit_end <= min(prong_a, prong_b)


def compute_263a4_5(transaction_costs: List[TransactionCostItem],
                    intangibles: List[IntangibleItem],
                    startup_pools: List[StartupOrgCostPool], *,
                    success_fee_elections: FrozenSet[str] = frozenset(),
                    current_tax_year: int = 2026) -> dict:
    """Returns {transaction_items, intangible_items, startup_items,
    amortizable_items, capitalized_total, deductible_total, warnings}.
    deductible_total = current deductions (investigatory/§162/70%-elected/
    abandonment losses/12-month-rule amounts/first-year start-up deduction);
    scheduled amortization lives on the AmortizableItem rows, not here.
    capitalized_total = basis actually POSTED (post-reconciliation deltas)."""
    warnings: List[str] = []
    amortizable: List[AmortizableItem] = []
    capitalized_total = Decimal("0")
    deductible_total = Decimal("0")

    # --- §1.263(a)-5 transaction costs -------------------------------------
    transaction_items: List[dict] = []
    for tc in transaction_costs:
        row = {"item_id": tc.item_id, "transaction_id": tc.transaction_id,
               "description": tc.description, "amount": tc.amount,
               "treatment": "", "deductible": Decimal("0"),
               "capitalized": Decimal("0"), "flags": []}
        if tc.amount < 0:
            # a negative fee flowed silently into deductible_total
            # (round-4 symmetry sweep) — a cost cannot be negative
            row["treatment"] = "sme_review"
            row["flags"].append("NEGATIVE-AMOUNT")
            warnings.append(
                f"NEGATIVE-AMOUNT [txn cost {tc.item_id or tc.description}]: "
                f"${tc.amount:,.2f} — nothing computed; route "
                f"credits/refunds through the schedule, not a negative fee.")
            transaction_items.append(row)
            continue
        cap = Decimal("0")
        ded = Decimal("0")
        if (tc.success_based and tc.covered_transaction
                and tc.transaction_id in success_fee_elections):
            # Rev. Proc. 2011-29 safe harbor: 70/30, per-transaction,
            # IRREVOCABLE once elected.
            ded = (tc.amount * Decimal("0.70")).quantize(Decimal("0.01"))
            cap = tc.amount - ded
            row["treatment"] = "success_fee_70_30"
            row["flags"].append("REV-PROC-2011-29-IRREVOCABLE")
        elif tc.inherently_facilitative:
            # Inherently facilitative: capitalize regardless of timing.
            cap = tc.amount
            row["treatment"] = "inherently_facilitative_capitalize"
        elif (tc.covered_transaction and tc.bright_line_date
                and tc.incurred_date
                and tc.incurred_date < tc.bright_line_date):
            # Investigatory, pre-bright-line: deductible.
            ded = tc.amount
            row["treatment"] = "investigatory_pre_bright_line_deduct"
        elif tc.covered_transaction:
            # Covered, on/after the bright-line date (or dates missing —
            # conservative): capitalize.
            cap = tc.amount
            row["treatment"] = "facilitative_capitalize"
            if not (tc.bright_line_date and tc.incurred_date):
                row["flags"].append("BRIGHT-LINE-DATES-MISSING")
                warnings.append(
                    f"BRIGHT-LINE-DATES-MISSING [{tc.item_id}]: covered-"
                    f"transaction cost lacks incurred/bright-line dates — "
                    f"capitalized conservatively; supply dates to test the "
                    f"investigatory carve-out.")
        else:
            ded = tc.amount
            row["treatment"] = "deductible_162"

        if tc.transaction_abandoned and cap > 0:
            # Rev. Rul. 73-580: abandoned transaction — capitalized-to-date
            # amounts become a deductible loss.
            row["flags"].append("ABANDONED-TRANSACTION-LOSS-73-580")
            warnings.append(
                f"ABANDONED-TRANSACTION [{tc.item_id}]: transaction "
                f"{tc.transaction_id!r} abandoned — ${cap:,.2f} of "
                f"capitalized transaction costs becomes a deductible loss "
                f"(Rev. Rul. 73-580).")
            ded += cap
            cap = Decimal("0")
            row["treatment"] += "+abandoned_loss"

        if cap > 0:
            # Capitalized transaction costs attach to whatever they
            # facilitate (acquired-asset basis / §197 goodwill / issuance
            # costs) — posted with no recovery period pending that routing.
            amortizable.append(AmortizableItem(
                item_id=tc.item_id, description=tc.description,
                category="intangible", basis=cap, recovery_months=None,
                convention="none", start_year=current_tax_year,
                source="Phase G compute_263a4_5",
                authority="§1.263(a)-5 facilitative transaction cost",
                notes="Attach to the facilitated asset's basis (seed for "
                      "downstream routing — asset basis / §197 / §1.446-5)."))
        row["deductible"], row["capitalized"] = ded, cap
        deductible_total += ded
        capitalized_total += cap
        transaction_items.append(row)

    # --- §1.263(a)-4 intangibles -------------------------------------------
    intangible_items: List[dict] = []
    for it in intangibles:
        row = {"item_id": it.item_id, "description": it.description,
               "amount": it.amount, "facilitative_costs": it.facilitative_costs,
               "treatment": "", "deductible": Decimal("0"),
               "capitalized": Decimal("0"), "posted_basis": Decimal("0"),
               "flags": []}
        # Date-sanity guards (red-team: reversed dates produced a NEGATIVE
        # recovery period and negative amortization with zero warnings, or —
        # with a payment_year set — silently deducted the full amount via
        # the 12-month rule; a 4-digit-typo payment_year crashed date()).
        if it.benefit_start and it.benefit_end and it.benefit_end < it.benefit_start:
            row["flags"].append("BENEFIT-DATES-REVERSED")
            row["treatment"] = "sme_review"
            warnings.append(
                f"BENEFIT-DATES-REVERSED [{it.item_id}]: benefit_end "
                f"{it.benefit_end} precedes benefit_start {it.benefit_start} — "
                f"no treatment computed; fix the schedule dates.")
            intangible_items.append(row)
            continue
        if it.payment_year and not (1900 <= it.payment_year <= 9998):
            row["flags"].append("PAYMENT-YEAR-INVALID")
            row["treatment"] = "sme_review"
            warnings.append(
                f"PAYMENT-YEAR-INVALID [{it.item_id}]: payment_year="
                f"{it.payment_year} is not a plausible tax year — no "
                f"treatment computed.")
            intangible_items.append(row)
            continue
        passes_12mo = _twelve_month_rule_passes(it)
        if passes_12mo:
            # §1.263(a)-4(f): short-lived benefit — nothing capitalizes,
            # facilitative costs included.
            row["treatment"] = "twelve_month_rule_deduct"
            row["deductible"] = it.amount + it.facilitative_costs
            deductible_total += row["deductible"]
            # commissions are categorically outside the de minimis AND the
            # 12-month deduction path — round 2's fix covered only the
            # capitalize branch; a commission on a 12-month-rule item
            # vanished entirely (round-3 fuzz: neither deducted nor
            # capitalized nor flagged)
            if it.facilitative_commissions > 0:
                row["flags"].append("E4-COMMISSIONS-ALWAYS-CAPITALIZED")
                row["capitalized"] = it.facilitative_commissions
                delta, recon_w = reconcile(
                    Decimal("0"), it.facilitative_commissions,
                    f"12-month-rule item commissions {it.item_id or it.description}")
                warnings.extend(recon_w)
                amortizable.append(AmortizableItem(
                    item_id=it.item_id, description=f"{it.description} (commissions)",
                    category="intangible", basis=delta, recovery_months=None,
                    convention="none", start_year=current_tax_year,
                    source="Phase G compute_263a4_5",
                    authority="§1.263(a)-4(e)(4): commissions always facilitative",
                    flags=["E4-COMMISSIONS-ALWAYS-CAPITALIZED",
                           "INDEFINITE-LIFE-SME-REVIEW"]))
                row["posted_basis"] = delta
                capitalized_total += delta
            intangible_items.append(row)
            continue
        if passes_12mo is None and (it.benefit_start or it.benefit_end):
            row["flags"].append("TWELVE-MONTH-DATES-INCOMPLETE")

        # §1.263(a)-4(e)(4) $5,000 CLIFF on facilitative costs, per
        # transaction: ≤ $5,000 deductible; over → ALL capitalizable.
        # Commissions are categorically OUTSIDE the de minimis — always
        # capitalized, never counted toward (or sheltered by) the cliff.
        cap = it.amount + it.facilitative_commissions
        if it.facilitative_commissions > 0:
            row["flags"].append("E4-COMMISSIONS-ALWAYS-CAPITALIZED")
        ded = Decimal("0")
        if it.facilitative_costs > 0:
            if it.facilitative_costs <= FACILITATIVE_DE_MINIMIS:
                ded += it.facilitative_costs
                row["flags"].append("E4-DE-MINIMIS-DEDUCTED")
            else:
                cap += it.facilitative_costs
                row["flags"].append("E4-CLIFF-ALL-CAPITALIZED")
        row["treatment"] = "capitalize_263a4"

        # Recovery: §197 (acquired with a business) → 180 months full-month;
        # else benefit term when both dates exist; else SME review.
        if it.acquired_with_business:
            recovery: Optional[int] = SEC197_RECOVERY_MONTHS
            convention = "full-month"
            authority = "§197(a): acquired-with-business intangible, 15-year"
        elif it.benefit_start and it.benefit_end:
            recovery = _months_between(it.benefit_start, it.benefit_end)
            if recovery < 1:
                # a sub-one-month term parked basis forever at recovery 0,
                # indistinguishable from indefinite-life but UNFLAGGED
                recovery = 1
                row["flags"].append("RECOVERY-FLOORED-ONE-MONTH")
            convention = "full-month"
            authority = ("§1.263(a)-4: amortized over the benefit term "
                         f"({recovery} months, benefit_end − benefit_start)")
        else:
            recovery = None
            convention = "none"
            authority = "§1.263(a)-4: no ascertainable life in schedule"
            row["flags"].append("INDEFINITE-LIFE-SME-REVIEW")
            warnings.append(
                f"INDEFINITE-LIFE-SME-REVIEW [{it.item_id}]: capitalized "
                f"intangible with no §197 route and no benefit dates — "
                f"recovery period is a per-item SME determination, not "
                f"defaulted.")

        delta, recon_warnings = reconcile(
            it.prior_capitalized_basis, cap,
            f"§1.263(a)-4 intangible {it.item_id or it.description}")
        warnings.extend(recon_warnings)
        amortizable.append(AmortizableItem(
            item_id=it.item_id, description=it.description,
            category="intangible", basis=delta, recovery_months=recovery,
            convention=convention, start_year=current_tax_year,
            source="Phase G compute_263a4_5", authority=authority,
            flags=list(row["flags"])))
        row["deductible"], row["capitalized"] = ded, cap
        row["posted_basis"] = delta
        deductible_total += ded
        capitalized_total += delta
        intangible_items.append(row)

    # --- §195/§248/§709 start-up & organizational pools ---------------------
    startup_items: List[dict] = []
    for pool in startup_pools:
        row = {"pool_id": pool.pool_id, "kind": pool.kind,
               "total": pool.total, "first_year_deduction": Decimal("0"),
               "amortizable_remainder": Decimal("0"),
               "first_year_amortization": Decimal("0"), "flags": []}
        if pool.total < 0:
            # a negative pool total produced an unflagged NEGATIVE first-year
            # deduction (round-3 fuzz) — a cost pool cannot be negative
            row["flags"].append("NEGATIVE-POOL-TOTAL")
            warnings.append(
                f"NEGATIVE-POOL-TOTAL [startup {pool.pool_id}]: total "
                f"${pool.total:,.2f} — nothing computed; fix the schedule.")
            startup_items.append(row)
            continue
        if pool.kind == "syndication":
            # §709(b): syndication costs PERMANENTLY capitalized — no $5,000,
            # no 180-month amortization, no deduction short of liquidation.
            row["flags"].append("SYNDICATION-PERMANENTLY-CAPITALIZED")
            warnings.append(
                f"SYNDICATION-PERMANENTLY-CAPITALIZED [{pool.pool_id}]: "
                f"§709(b) syndication costs — no first-year deduction, no "
                f"amortization; deductible only on complete liquidation.")
            amortizable.append(AmortizableItem(
                item_id=pool.pool_id, description="Syndication costs",
                category="startup_org", basis=pool.total,
                recovery_months=None, convention="none",
                start_year=current_tax_year,
                source="Phase G compute_263a4_5",
                authority="§709(b): syndication costs, permanent "
                          "capitalization",
                flags=["SYNDICATION-PERMANENTLY-CAPITALIZED"]))
            capitalized_total += pool.total
            startup_items.append(row)
            continue

        # §195(b)/§248(a)/§709(b)(1): min(total, max(0, 5000 − excess over
        # 50,000)) deducted in year one; remainder over 180 months from the
        # business-commencement month.
        phaseout = max(Decimal("0"), pool.total - STARTUP_PHASEOUT_START)
        first_year = min(pool.total,
                         max(Decimal("0"), STARTUP_FIRST_YEAR_CAP - phaseout))
        remainder = pool.total - first_year
        # First-year amortization = remainder × months-in-service/180;
        # months-in-service = 12 − commencement month + 1 (calendar-year
        # assumption; a missing date is flagged and treated as January, the
        # full-year — i.e., most-amortization — placeholder).
        if pool.business_commencement:
            months_in_service = 12 - pool.business_commencement.month + 1
            start_year = pool.business_commencement.year
        else:
            months_in_service = 12
            start_year = current_tax_year
            row["flags"].append("BUSINESS-COMMENCEMENT-DATE-MISSING")
            warnings.append(
                f"BUSINESS-COMMENCEMENT-DATE-MISSING [{pool.pool_id}]: "
                f"amortization must begin with the month the active trade "
                f"or business begins — January assumed pending the date.")
        first_year_amort = Decimal("0")
        if remainder > 0:
            first_year_amort = (remainder * Decimal(months_in_service)
                                / Decimal(STARTUP_RECOVERY_MONTHS)
                                ).quantize(Decimal("0.01"))
            amortizable.append(AmortizableItem(
                item_id=pool.pool_id,
                description=f"{pool.kind} cost pool",
                category="startup_org", basis=remainder,
                recovery_months=STARTUP_RECOVERY_MONTHS,
                convention="full-month", start_year=start_year,
                source="Phase G compute_263a4_5",
                authority="§195(b)/§248(a)/§709(b)(1): 180-month "
                          "straight-line from business commencement",
                notes=f"Year-1 amortization {months_in_service}/180 "
                      f"(months in service, calendar-year assumption)."))
            capitalized_total += remainder
        row["first_year_deduction"] = first_year
        row["amortizable_remainder"] = remainder
        row["first_year_amortization"] = first_year_amort
        deductible_total += first_year
        startup_items.append(row)

    return {"transaction_items": transaction_items,
            "intangible_items": intangible_items,
            "startup_items": startup_items,
            "amortizable_items": amortizable,
            "capitalized_total": capitalized_total,
            "deductible_total": deductible_total,
            "warnings": warnings}


def route_demolition(demolition_cost: Decimal,
                     remaining_structure_basis: Decimal, *,
                     casualty: bool = False) -> dict:
    """§280B/Reg. §1.280B-1: on demolition, NO deduction for the demolition
    cost or the structure's remaining basis — BOTH capitalize to the LAND
    (no recovery period). casualty=True: Notice 90-21 carve-out is a SME
    call — nothing auto-routed, flag only."""
    demolition_cost = Decimal(str(demolition_cost or 0))
    remaining_structure_basis = Decimal(str(remaining_structure_basis or 0))
    warnings: List[str] = []
    items: List[AmortizableItem] = []
    if casualty:
        warnings.append(
            "CASUALTY-EXCEPTION-SME-REVIEW: casualty-triggered demolition — "
            "Notice 90-21 carve-out may apply; §280B land capitalization NOT "
            "auto-applied, route to SME.")
        return {"amortizable_items": items, "warnings": warnings}
    total = demolition_cost + remaining_structure_basis
    warnings.append(
        f"§280B-CAPITALIZED-TO-LAND: demolition cost "
        f"${demolition_cost:,.2f} + remaining structure basis "
        f"${remaining_structure_basis:,.2f} capitalized to land — no loss, "
        f"no depreciation (Reg. §1.280B-1).")
    items.append(AmortizableItem(
        description="§280B demolition — capitalized to land",
        category="land", basis=total, recovery_months=None,
        convention="none", source="Phase G route_demolition",
        authority="§280B / Reg. §1.280B-1",
        flags=["§280B-CAPITALIZED-TO-LAND"]))
    return {"amortizable_items": items, "warnings": warnings}
