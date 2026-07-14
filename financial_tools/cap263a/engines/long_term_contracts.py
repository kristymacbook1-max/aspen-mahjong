"""§460 long-term contracts — percentage-of-completion method (PCM,
§460(b)(1), cost-to-cost) with the §460(e) exemptions and the §460(b)(5)
10% election.

DECISION ORDER per contract:
1. Guards: a negative total_contract_price, estimated_total_allocable_costs,
   cumulative_allocable_costs, or prior_cumulative_allocable_costs ->
   treatment "sme_review", flag NEGATIVE-AMOUNT, nothing computed (house
   pattern: a price or cost cannot be negative). cumulative_allocable_costs
   < prior_cumulative_allocable_costs -> COSTS-DECREASED warning (a data
   error — cumulative costs cannot shrink), but the contract STILL computes
   on the cumulative figure as given.
2. Manufacturing PCM applicability (§460(f)(2)): a manufacturing contract
   is a long-term contract subject to PCM ONLY if it involves a unique item
   (§460(f)(2)(A)) OR an item normally requiring more than 12 months to
   complete (§460(f)(2)(B)). Both facts explicitly False -> treatment
   "not_long_term_exempt" (the taxpayer's normal accounting method applies;
   out of scope here) — nothing computed. Either fact None (and none True)
   -> OPEN QUESTION naming the missing fact(s), and PCM is computed
   CONSERVATIVELY with flag 460F2-FACTS-INCOMPLETE.
3. Home construction exemption (§460(e)(1)(A)/(e)(5): >= 80% of estimated
   total contract costs attributable to dwelling units in buildings of
   <= 4 units): is_home_construction -> treatment
   "home_construction_exempt", no PCM computed; warning
   HOME-CONSTRUCTION-EXEMPT — exempt from PCM, but §263A applies to the
   construction costs instead: route them through the UNICAP engines. This
   engine does NOT compute the exempt method.
4. Small construction contract exemption (§460(e)(1)(B), post-TCJA): a
   construction contract estimated (at commencement) to be completed within
   2 years AND profile.avg_gross_receipts <= profile.sec448_threshold (the
   §448(c) gross-receipts test — post-2017 the §460(e) receipts test uses
   §448(c) mechanics, TCJA §13102(d)) -> treatment
   "small_construction_exempt", no PCM; warning SMALL-CONSTRUCTION-EXEMPT
   (the completed-contract method or another permissible exempt method
   applies — NOT computed here). estimated_duration_years None on a
   construction contract -> OPEN QUESTION (the 2-year estimate at
   commencement decides the exemption) and PCM continues CONSERVATIVELY
   with flag 460E-DURATION-UNKNOWN.
5. PCM (§460(b)(1), cost-to-cost): completion_factor =
   cumulative_allocable_costs / estimated_total_allocable_costs, carried
   EXACT in Decimal. The REPORTED factor is quantized to 0.0001 HALF_EVEN
   for display, but all multiplication uses the EXACT factor — the house
   convention pre-rounds only ratios the regulation itself presents, and
   §460 prescribes no rounding, so only dollar outputs are quantized (to
   cents, HALF_EVEN). estimated_total_allocable_costs <= 0 -> ZERO-ESTIMATE
   warning, factor 0. factor > 1 -> clamp to 1 with COMPLETION-OVER-100PCT
   warning (a cost overrun means the estimate is stale — fix the estimate).
   cumulative_income = exact factor x total_contract_price;
   current_year_income = cumulative_income - prior_income_recognized. A
   NEGATIVE current-year figure is PERMITTED under PCM when estimates shift
   — it is NOT floored, but NEGATIVE-CURRENT-INCOME is warned once per run.
   current_year_costs_deducted = cumulative_allocable_costs -
   prior_cumulative_allocable_costs (PCM deducts allocable contract costs
   as incurred).
6. 10% method (§460(b)(5) — an ELECTION that applies to ALL long-term
   contracts of the electing year): if ten_percent_election and the exact
   completion factor < 10%, the contract is disregarded for the year —
   current_year_income = 0 and the current-year costs are NOT deducted
   (deferred with the income; reported in deferred_costs), flag
   TEN-PCT-DEFERRED. Once the contract is >= 10% complete in a later year,
   the catch-up happens automatically through the cumulative mechanics
   (prior_income_recognized carries 0 from the deferral year).
7. completed_this_year: cumulative income must equal total_contract_price.
   The factor is forced to 1 on completion; when
   estimated_total_allocable_costs > cumulative_allocable_costs (factor
   would be < 1) the full price is still recognized, with flag
   COMPLETION-TRUE-UP. LOOK-BACK interest (§460(b)(2), Form 8697) is NOT
   IMPLEMENTED — LOOKBACK-NOT-IMPLEMENTED is warned once per run whenever
   any contract is completed_this_year, or any COMPLETION-OVER-100PCT or
   NEGATIVE-CURRENT-INCOME fired (the estimate moved).
8. Cost-allocation input contract: the allocable-contract-cost inputs must
   already follow §1.460-5(b) (§263A-style direct + indirect cost
   allocation); with simplified_cost_to_cost=True, §1.460-5(c) permits the
   simplified cost-to-cost method (direct material, direct labor, and
   depreciation/amortization/cost recovery on equipment and facilities
   directly used) instead. COST-ALLOCATION-INPUT-CONTRACT is emitted once
   per run as an informational reminder of which regime the inputs must
   satisfy.

OUT OF SCOPE (documented, not computed): severing and aggregation of
contracts (§1.460-1(e)) is an SME determination — contracts are taken as
supplied, one row each; look-back interest (§460(b)(2), Form 8697); the
exempt-contract methods themselves (completed-contract, exempt-percentage-
of-completion, etc.) for contracts routed out at steps 2-4.

Dollar outputs are quantized to cents HALF_EVEN; totals are exact sums of
the quantized per-contract figures (so the totals tie to the rows by
construction).
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
from typing import List, Optional

from ..model import _dec

CENT = Decimal("0.01")
FACTOR_Q = Decimal("0.0001")            # reported completion factor, 4dp
TEN_PERCENT = Decimal("0.10")           # §460(b)(5)
SMALL_CONSTRUCTION_MAX_YEARS = Decimal("2")   # §460(e)(1)(B)(i)


@dataclass
class LongTermContract:
    """One long-term contract (§460 schedule row).

    The §460(f)(2) manufacturing facts are TRI-STATE: True/False when
    established, None when the schedule does not carry them — None is never
    treated as False."""
    contract_id: str = ""
    description: str = ""
    contract_type: str = "construction"     # construction / manufacturing
    total_contract_price: Decimal = Decimal("0")
    # §1.460-5 allocable contract costs, total estimated at year end:
    estimated_total_allocable_costs: Decimal = Decimal("0")
    # allocable costs incurred through THIS year end:
    cumulative_allocable_costs: Decimal = Decimal("0")
    # allocable costs incurred through the PRIOR year end:
    prior_cumulative_allocable_costs: Decimal = Decimal("0")
    prior_income_recognized: Decimal = Decimal("0")   # PCM income, prior years
    # estimated at contract commencement (drives §460(e)(1)(B)):
    estimated_duration_years: Optional[Decimal] = None
    # §460(e)(1)(A)/(e)(5): >= 80% of costs re dwelling units in buildings
    # of <= 4 units:
    is_home_construction: bool = False
    completed_this_year: bool = False
    ten_percent_election: bool = False      # §460(b)(5)
    # §460(f)(2) manufacturing PCM applicability facts (tri-state):
    unique_item: Optional[bool] = None                       # §460(f)(2)(A)
    normal_production_period_over_12mo: Optional[bool] = None  # §460(f)(2)(B)
    row_index: int = 0

    def __post_init__(self):
        self.total_contract_price = _dec(self.total_contract_price)
        self.estimated_total_allocable_costs = _dec(
            self.estimated_total_allocable_costs)
        self.cumulative_allocable_costs = _dec(self.cumulative_allocable_costs)
        self.prior_cumulative_allocable_costs = _dec(
            self.prior_cumulative_allocable_costs)
        self.prior_income_recognized = _dec(self.prior_income_recognized)
        if self.estimated_duration_years is not None:
            self.estimated_duration_years = _dec(self.estimated_duration_years)


def compute_460(contracts: List[LongTermContract], profile, *,
                simplified_cost_to_cost: bool = False) -> dict:
    """Apply the module-docstring decision order to every contract.

    Returns {contracts, open_questions, total_current_year_income,
    total_current_year_costs, warnings}. Dollar outputs are quantized to
    cents HALF_EVEN; the totals are exact sums of the quantized
    per-contract figures."""
    warnings: List[str] = []
    open_questions: List[dict] = []
    seen_questions: set = set()

    def ask(c: LongTermContract, question: str, why: str) -> None:
        if question in seen_questions:
            return
        seen_questions.add(question)
        open_questions.append({"contract_id": c.contract_id,
                               "question": question, "why": why})

    # --- 8. cost-allocation input contract (once per run) -------------------
    if contracts:
        if simplified_cost_to_cost:
            warnings.append(
                "COST-ALLOCATION-INPUT-CONTRACT: simplified_cost_to_cost is "
                "on — under Reg. §1.460-5(c) the simplified cost-to-cost "
                "method limits allocable contract costs to direct material, "
                "direct labor, and depreciation/amortization/cost recovery "
                "on equipment and facilities directly used to construct or "
                "produce the subject matter. The estimated_total and "
                "cumulative allocable-cost inputs must BOTH be built on that "
                "same simplified cost set.")
        else:
            warnings.append(
                "COST-ALLOCATION-INPUT-CONTRACT: allocable contract costs "
                "must follow Reg. §1.460-5(b) — §263A-style direct plus "
                "indirect cost allocation. The estimated_total and "
                "cumulative allocable-cost inputs are taken as ALREADY "
                "allocated under that regime; this engine does not allocate "
                "costs. (Set simplified_cost_to_cost=True if the "
                "§1.460-5(c) simplified cost-to-cost method is used.)")

    rows: List[dict] = []
    total_income = Decimal("0")
    total_costs = Decimal("0")
    negative_income_warned = False
    lookback_trigger = False

    for c in contracts:
        row = {"contract_id": c.contract_id, "treatment": "",
               "completion_factor": None,
               "cumulative_income": Decimal("0"),
               "current_year_income": Decimal("0"),
               "current_year_costs_deducted": Decimal("0"),
               "deferred_costs": Decimal("0"),
               "flags": []}
        label = c.contract_id or c.description

        # --- 1. guards -------------------------------------------------------
        negatives = [(name, getattr(c, name)) for name in (
            "total_contract_price", "estimated_total_allocable_costs",
            "cumulative_allocable_costs", "prior_cumulative_allocable_costs")
            if getattr(c, name) < 0]
        if negatives:
            row["treatment"] = "sme_review"
            row["flags"].append("NEGATIVE-AMOUNT")
            detail = "; ".join(f"{n} ${v:,.2f}" for n, v in negatives)
            warnings.append(
                f"NEGATIVE-AMOUNT [460 {label}]: {detail} — a contract "
                f"price or cost cannot be negative; nothing computed. Route "
                f"credits/adjustments through the schedule, not a negative "
                f"input.")
            rows.append(row)
            continue
        if c.cumulative_allocable_costs < c.prior_cumulative_allocable_costs:
            row["flags"].append("COSTS-DECREASED")
            warnings.append(
                f"COSTS-DECREASED [460 {label}]: cumulative allocable costs "
                f"(${c.cumulative_allocable_costs:,.2f}) are LESS than the "
                f"prior-year cumulative "
                f"(${c.prior_cumulative_allocable_costs:,.2f}) — cumulative "
                f"costs cannot shrink; this is a data error. The contract "
                f"was still computed on the cumulative figure as given — "
                f"verify both inputs.")
            # still compute on cumulative

        # --- 2. manufacturing PCM applicability (§460(f)(2)) ------------------
        if c.contract_type == "manufacturing":
            if c.unique_item is True \
                    or c.normal_production_period_over_12mo is True:
                pass    # long-term contract — PCM applies
            elif c.unique_item is False \
                    and c.normal_production_period_over_12mo is False:
                row["treatment"] = "not_long_term_exempt"
                warnings.append(
                    f"NOT-LONG-TERM [460 {label}]: manufacturing contract "
                    f"involves neither a unique item (§460(f)(2)(A)) nor an "
                    f"item normally requiring more than 12 months to "
                    f"complete (§460(f)(2)(B)) — it is not a long-term "
                    f"contract for §460. The taxpayer's normal accounting "
                    f"method applies; nothing computed here.")
                rows.append(row)
                continue
            else:
                missing = []
                if c.unique_item is None:
                    missing.append(
                        "unique_item (§460(f)(2)(A) — is the item unique, "
                        "i.e. not normally included in finished-goods "
                        "inventory?)")
                if c.normal_production_period_over_12mo is None:
                    missing.append(
                        "normal_production_period_over_12mo (§460(f)(2)(B) "
                        "— does the item normally require more than 12 "
                        "calendar months to complete regardless of the "
                        "contract's duration?)")
                row["flags"].append("460F2-FACTS-INCOMPLETE")
                ask(c,
                    f"Contract {label} '{c.description}': the §460(f)(2) "
                    f"manufacturing facts are not established: "
                    + " ".join(missing) + " Answer each True/False.",
                    "A manufacturing contract is a long-term contract "
                    "subject to PCM only if either §460(f)(2) prong is "
                    "True; both False takes it out of §460 entirely. PCM "
                    "was computed CONSERVATIVELY pending the answer.")
                # fall through — conservative PCM

        # --- 3. home construction exemption (§460(e)(1)(A)) --------------------
        if c.is_home_construction:
            row["treatment"] = "home_construction_exempt"
            warnings.append(
                f"HOME-CONSTRUCTION-EXEMPT [460 {label}]: home construction "
                f"contract (§460(e)(1)(A)/(e)(5)) — exempt from PCM, but "
                f"§263A applies to the construction costs instead: route "
                f"them through the UNICAP engines. This engine does not "
                f"compute the exempt method.")
            rows.append(row)
            continue

        # --- 4. small construction contract exemption (§460(e)(1)(B)) ----------
        if c.contract_type == "construction":
            if c.estimated_duration_years is None:
                row["flags"].append("460E-DURATION-UNKNOWN")
                ask(c,
                    f"Contract {label} '{c.description}': at contract "
                    f"commencement, was the contract estimated to be "
                    f"completed within 2 years of the commencement date "
                    f"(§460(e)(1)(B)(i))? Supply estimated_duration_years "
                    f"(the estimate made AT COMMENCEMENT, not the current "
                    f"outlook).",
                    "The 2-year estimate at commencement decides the small "
                    "construction contract exemption (with the §448(c) "
                    "gross-receipts test). PCM was computed CONSERVATIVELY "
                    "pending the answer.")
                # fall through — conservative PCM
            elif c.estimated_duration_years <= SMALL_CONSTRUCTION_MAX_YEARS \
                    and profile.avg_gross_receipts <= profile.sec448_threshold:
                row["treatment"] = "small_construction_exempt"
                warnings.append(
                    f"SMALL-CONSTRUCTION-EXEMPT [460 {label}]: construction "
                    f"contract estimated at commencement to complete within "
                    f"2 years, and average annual gross receipts "
                    f"(${profile.avg_gross_receipts:,.0f}) do not exceed "
                    f"the §448(c) threshold "
                    f"(${profile.sec448_threshold:,.0f}) — exempt from PCM "
                    f"under §460(e)(1)(B). NOTE: post-2017 (TCJA) the "
                    f"§460(e) receipts test uses §448(c) mechanics. The "
                    f"completed-contract method or another permissible "
                    f"exempt method applies — NOT computed here.")
                rows.append(row)
                continue

        # --- 5. PCM (§460(b)(1), cost-to-cost) ---------------------------------
        if c.estimated_total_allocable_costs <= 0:
            warnings.append(
                f"ZERO-ESTIMATE [460 {label}]: estimated total allocable "
                f"contract costs are "
                f"${c.estimated_total_allocable_costs:,.2f} — the "
                f"cost-to-cost completion factor is undefined; factor 0 was "
                f"used. Supply the year-end estimate of total allocable "
                f"contract costs.")
            factor = Decimal("0")
        else:
            factor = c.cumulative_allocable_costs \
                / c.estimated_total_allocable_costs      # EXACT — see docstring
            if factor > 1:
                factor = Decimal("1")
                row["flags"].append("COMPLETION-OVER-100PCT")
                lookback_trigger = True
                warnings.append(
                    f"COMPLETION-OVER-100PCT [460 {label}]: cumulative "
                    f"allocable costs "
                    f"(${c.cumulative_allocable_costs:,.2f}) exceed the "
                    f"estimated total "
                    f"(${c.estimated_total_allocable_costs:,.2f}) — a cost "
                    f"overrun means the estimate is stale. The factor was "
                    f"clamped to 1; fix the estimate.")

        # --- 7 (factor part). completion forces the factor to 1 ----------------
        if c.completed_this_year:
            lookback_trigger = True
            if factor < 1:
                factor = Decimal("1")
                row["flags"].append("COMPLETION-TRUE-UP")

        row["treatment"] = "pcm"
        row["completion_factor"] = factor.quantize(FACTOR_Q, ROUND_HALF_EVEN)
        cumulative_income = (factor * c.total_contract_price).quantize(
            CENT, ROUND_HALF_EVEN)
        current_year_income = (cumulative_income
                               - c.prior_income_recognized).quantize(
            CENT, ROUND_HALF_EVEN)
        current_year_costs = (c.cumulative_allocable_costs
                              - c.prior_cumulative_allocable_costs).quantize(
            CENT, ROUND_HALF_EVEN)
        deferred_costs = Decimal("0.00")

        # --- 6. 10% method (§460(b)(5) election) -------------------------------
        if c.ten_percent_election and factor < TEN_PERCENT:
            row["flags"].append("TEN-PCT-DEFERRED")
            deferred_costs = current_year_costs
            current_year_costs = Decimal("0.00")
            current_year_income = Decimal("0.00")
            # cumulative_income stays the PCM formula figure (informational);
            # the later-year catch-up flows through prior_income_recognized,
            # which carries 0 from a deferral year.

        if current_year_income < 0:
            row["flags"].append("NEGATIVE-CURRENT-INCOME")
            lookback_trigger = True
            if not negative_income_warned:
                negative_income_warned = True
                warnings.append(
                    "NEGATIVE-CURRENT-INCOME: at least one contract's "
                    "current-year PCM income is negative — permitted under "
                    "PCM when the completion estimate shifts (the "
                    "cumulative income fell below what prior years "
                    "recognized). The figure was NOT floored at zero; "
                    "verify the revised estimate.")

        row["cumulative_income"] = cumulative_income
        row["current_year_income"] = current_year_income
        row["current_year_costs_deducted"] = current_year_costs
        row["deferred_costs"] = deferred_costs
        total_income += current_year_income
        total_costs += current_year_costs
        rows.append(row)

    # --- 7 (look-back part). §460(b)(2) look-back NOT IMPLEMENTED --------------
    if lookback_trigger:
        warnings.append(
            "LOOKBACK-NOT-IMPLEMENTED: a contract completed this year or an "
            "estimate moved (COMPLETION-OVER-100PCT / "
            "NEGATIVE-CURRENT-INCOME) — the §460(b)(2) look-back interest "
            "computation (Form 8697) is NOT implemented by this engine and "
            "must be prepared separately.")

    return {"contracts": rows,
            "open_questions": open_questions,
            "total_current_year_income": total_income,
            "total_current_year_costs": total_costs,
            "warnings": warnings}
