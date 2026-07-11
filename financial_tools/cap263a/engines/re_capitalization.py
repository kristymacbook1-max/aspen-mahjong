"""Phase F — §174/§174A research & experimental expenditure capitalization.

Regime (BUILD_PLAN.md Phase F; post-OBBBA/P.L. 119-21 §70302, tax years
beginning after 12/31/2024):
- FOREIGN research (§174(a)): MANDATORY capitalization, 180-month (15-year)
  straight-line, mid-year convention (half a full year's amortization in
  year 1 regardless of when incurred). No election out.
- DOMESTIC research (§174A(a)): DEFAULT is current expensing. Elective
  alternative (§174A(c)): capitalize and amortize ratably over a
  taxpayer-chosen period of NOT LESS THAN 60 months — a METHOD OF ACCOUNTING,
  distinct from the §59(e) 10-year election (see engines/
  qualified_expenditures.py; the interaction is flagged there, not resolved).
- 2022-2024 transition (OBBBA relief for domestic amounts still amortizing at
  the 2025 changeover): deduct the remaining basis in one year, or spread it
  over two years. The exact two-year ratable split is flagged
  CATCHUP-SPLIT-UNVERIFIED pending a Rev. Proc. 2025-28 primary read; 50/50
  is used as the working assumption. Alternatively the §448(c) small-business
  retroactive election amends 2022-2024 returns (amended-return deadline
  July 6, 2026 per Rev. Proc. 2025-28) — mutually exclusive with a catch-up.
- §174(d): NO loss deduction on disposal/retirement/abandonment of property
  with capitalized R&E basis — amortization continues as if the disposition
  never happened. Whether post-OBBBA §174(d) reaches DOMESTIC research
  capitalized under the §174A(c) elective is UNVERIFIED
  (§174D-DOMESTIC-ELECTIVE-UNVERIFIED) — the conservative reading (rule
  applies) is used, flagged, never silently resolved.

Basis reconciliation (Runtime Pipeline Step 3b): for each capitalized item
with book_capitalized_amount > 0, only the tax-required-minus-book DELTA
posts to the Basis & Amortization Schedule (shared reconcile() helper); the
gross tax-required amount stays visible on the per-item row.
"""

from decimal import Decimal
from typing import List, Optional

from ..model import AmortizableItem, REExpenditure
from .basis_reconciliation import reconcile

FOREIGN_RECOVERY_MONTHS = 180          # §174(a)(2)(B): 15 years, foreign research
MIN_ELECTED_MONTHS = 60                # §174A(c): "not less than 60 months"

_174A_START_MONTH_NOTE = (
    "§174A(c) amortization runs ratably from the month the taxpayer first "
    "realizes benefits; that month is not in the input schedule (DATA GAP) — "
    "mid-year convention applied as a documented proxy.")


def compute_174(re_expenditures: List[REExpenditure], *,
                current_tax_year: int = 2026,
                domestic_capitalization_election: bool = False,
                elected_period_months: int = 60,
                catchup_method: Optional[str] = None,
                remaining_2022_2024_basis: Decimal = Decimal("0"),
                small_business_retroactive: bool = False,
                disposal_events: Optional[List[str]] = None) -> dict:
    """Route each R&E item (foreign mandatory / domestic default-expense /
    domestic elected-capitalize), compute the 2022-2024 catch-up, and post
    capitalized items to the shared Basis & Amortization Schedule.

    Returns {items, amortizable_items, current_year_deduction,
    capitalized_total, warnings}. current_year_deduction = domestic default
    expensing + catch-up; scheduled amortization lives on the
    AmortizableItem rows, not in this total. capitalized_total = basis
    actually POSTED (post-reconciliation deltas); each item row keeps the
    gross tax-required figure.
    """
    remaining_2022_2024_basis = Decimal(str(remaining_2022_2024_basis or 0))
    disposal_ids = set(disposal_events or [])
    warnings: List[str] = []
    items: List[dict] = []
    amortizable: List[AmortizableItem] = []
    current_year_deduction = Decimal("0")
    capitalized_total = Decimal("0")

    if domestic_capitalization_election:
        if elected_period_months < MIN_ELECTED_MONTHS:
            warnings.append(
                f"ELECTED-PERIOD-BELOW-60: §174A(c) requires a period of not "
                f"less than 60 months; {elected_period_months} requested — "
                f"floored to 60.")
            elected_period_months = MIN_ELECTED_MONTHS
        warnings.append(
            "§174A(c) domestic-capitalization election is a METHOD OF "
            "ACCOUNTING — consistency/3115 discipline applies.")

    seen_ids = set()
    for exp in re_expenditures:
        seen_ids.add(exp.re_id)
        disposed = exp.re_id in disposal_ids
        row = {"re_id": exp.re_id, "description": exp.description,
               "amount": exp.amount, "domestic": exp.domestic,
               "treatment": "", "tax_required_capitalized": Decimal("0"),
               "posted_basis": Decimal("0"),
               "current_year_deduction": Decimal("0"), "flags": []}

        if not exp.domestic:
            # §174(a): mandatory foreign capitalization, 180 months, mid-year.
            row["treatment"] = "foreign_mandatory_capitalize"
            row["tax_required_capitalized"] = exp.amount
            delta, recon_warnings = reconcile(
                exp.book_capitalized_amount, exp.amount,
                f"§174 foreign R&E {exp.re_id or exp.description}")
            warnings.extend(recon_warnings)
            row["posted_basis"] = delta
            item = AmortizableItem(
                item_id=exp.re_id, description=exp.description,
                category="re_pool", basis=delta,
                recovery_months=FOREIGN_RECOVERY_MONTHS,
                convention="mid-year",
                start_year=exp.tax_year or current_tax_year,
                source="Phase F compute_174",
                authority="§174(a)(2): foreign research, 15-year "
                          "straight-line, midpoint (mid-year) convention")
            if disposed:
                row["flags"].append("DISPOSAL-NO-LOSS-174D")
                item.flags.append("DISPOSAL-NO-LOSS-174D")
                warnings.append(
                    f"§174(d) [{exp.re_id}]: disposal/retirement/abandonment "
                    f"of property with capitalized foreign R&E basis — NO "
                    f"loss deduction; amortization continues as if the "
                    f"disposition never occurred.")
            amortizable.append(item)
            capitalized_total += delta

        elif domestic_capitalization_election:
            # §174A(c): elected domestic capitalization, ≥60 months.
            row["treatment"] = "domestic_elected_capitalize"
            row["tax_required_capitalized"] = exp.amount
            delta, recon_warnings = reconcile(
                exp.book_capitalized_amount, exp.amount,
                f"§174A(c) elected domestic R&E {exp.re_id or exp.description}")
            warnings.extend(recon_warnings)
            row["posted_basis"] = delta
            item = AmortizableItem(
                item_id=exp.re_id, description=exp.description,
                category="re_pool", basis=delta,
                recovery_months=elected_period_months,
                convention="mid-year",
                start_year=exp.tax_year or current_tax_year,
                source="Phase F compute_174",
                authority="§174A(c): elective domestic capitalization, "
                          f"{elected_period_months}-month straight-line",
                notes=_174A_START_MONTH_NOTE)
            if disposed:
                # Conservative reading: §174(d) applies; flagged UNVERIFIED.
                row["flags"] += ["DISPOSAL-NO-LOSS-174D",
                                 "§174D-DOMESTIC-ELECTIVE-UNVERIFIED"]
                item.flags += ["DISPOSAL-NO-LOSS-174D",
                               "§174D-DOMESTIC-ELECTIVE-UNVERIFIED"]
                warnings.append(
                    f"§174(d) [{exp.re_id}]: disposal touching ELECTED-"
                    f"capitalization domestic R&E basis — no loss taken and "
                    f"amortization continued (conservative reading); whether "
                    f"post-OBBBA §174(d) reaches §174A(c)-elected domestic "
                    f"basis is UNVERIFIED — "
                    f"§174D-DOMESTIC-ELECTIVE-UNVERIFIED, SME review.")
            amortizable.append(item)
            capitalized_total += delta

        else:
            # §174A(a) default: domestic current expensing — no AmortizableItem.
            row["treatment"] = "domestic_default_expense"
            row["current_year_deduction"] = exp.amount
            current_year_deduction += exp.amount
            if exp.book_capitalized_amount > 0:
                warnings.append(
                    f"BOOK-TAX-DIVERGENCE [{exp.re_id}]: books capitalize "
                    f"${exp.book_capitalized_amount:,.2f} of domestic R&E the "
                    f"§174A(a) default currently expenses — book/tax "
                    f"difference, review (no tax capitalization posted).")
            if disposed:
                # §174(d) has nothing to bite on — no capitalized tax basis.
                row["flags"].append("DISPOSAL-MOOT-EXPENSED")

        items.append(row)

    for unknown in sorted(disposal_ids - seen_ids):
        warnings.append(f"DISPOSAL-UNKNOWN-RE-ID: {unknown!r} matches no "
                        f"R&E expenditure in the schedule.")

    # --- 2022-2024 domestic catch-up (OBBBA transition relief) -------------
    catchup = {"method": catchup_method,
               "current_year_deduction": Decimal("0"),
               "following_year_deduction": Decimal("0")}
    if small_business_retroactive and catchup_method:
        warnings.append(
            "CATCHUP-RETROACTIVE-MUTUALLY-EXCLUSIVE: the §448(c) small-"
            "business retroactive election and a catch-up method were BOTH "
            "selected — they are mutually exclusive; catch-up computed below "
            "for visibility, SME must resolve which applies.")
    if small_business_retroactive:
        warnings.append(
            "SMALL-BUSINESS-RETROACTIVE-DEADLINE: the Rev. Proc. 2025-28 "
            "retroactive election requires AMENDED 2022-2024 returns by "
            "July 6, 2026 — a lapsing hard deadline; the amended-return "
            "computation itself is out of scope for this engine.")
    if catchup_method == "one_year":
        catchup["current_year_deduction"] = remaining_2022_2024_basis
        current_year_deduction += remaining_2022_2024_basis
    elif catchup_method == "two_year":
        half = remaining_2022_2024_basis / Decimal("2")
        catchup["current_year_deduction"] = half
        catchup["following_year_deduction"] = remaining_2022_2024_basis - half
        current_year_deduction += half
        warnings.append(
            "CATCHUP-SPLIT-UNVERIFIED: two-year catch-up assumed 50/50 across "
            "the two years — the exact ratable split needs a Rev. Proc. "
            "2025-28 primary read before filing use.")
    elif catchup_method not in (None, "one_year", "two_year"):
        warnings.append(f"CATCHUP-METHOD-UNKNOWN: {catchup_method!r} — no "
                        f"catch-up computed (expected one_year/two_year).")

    return {"items": items, "amortizable_items": amortizable,
            "current_year_deduction": current_year_deduction,
            "capitalized_total": capitalized_total,
            "catchup": catchup, "warnings": warnings}
