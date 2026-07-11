"""Phase D — §263A(f) avoided-cost interest capitalization (§§1.263A-8/-9/-11/-12).

Implements BUILD_PLAN.md Phase D step 3's corrected snapshot-then-average
mechanics: APE and traced debt are evaluated at each measurement DATE (a
point-in-time snapshot, per §1.263A-9's own Example 3 — never an open/close
average), excess_d = max(0, APE_d − traced_debt_d) is averaged across the
computation period's measurement dates, and the excess expenditure amount =
average excess expenditures × the nontraced-debt weighted average interest
rate (WAIR, §1.263A-9(c)(5)(iii)).

Traced interest is the ACTUAL interest incurred on traced debt for the period
(§1.263A-9(b)(2)) and is ALWAYS fully capitalized — the §1.263A-9(c)(7)
pro-rata cap applies ONLY to the excess-expenditure pool across units,
prorated by each unit's average-excess share ((c)(7)(i)(B); numerically
identical to excess-amount share because WAIR is one taxpayer-level rate).

Per-source sequential consumption (nontraced → below-AFR related-party
(§1.263A-9(a)(4)(iii)) → §707(c) guaranteed payments (§1.263A-9(c)(2)(iii)),
each min()-capped, unconsumed remainder stays ordinary deductible interest)
is computed additively per the DECISION 2026-07-08 (docs/TAX_DECISIONS.md
§8d) — it never changes the total or the per-unit split.

Eligible-debt screens are §1.263A-9(a)(4), implemented on
DebtInstrument.is_eligible_debt (the model owns the rule; this engine only
reports WHICH screen excluded each ineligible instrument).

Unit-of-property / common-feature mechanics (§1.263A-10) are OUT of this
engine's scope — every project handed in is treated as one active designated-
property unit; is_common_feature is flag-only (warning, no allocation).

Basis reconciliation (Runtime Pipeline Step 3b, item (3)): where the books
already capitalize interest under ASC 835-20, only the tax-over-book DELTA
posts, via the shared engines/basis_reconciliation.reconcile() helper.

All arithmetic is exact Decimal; only final dollar outputs are quantized to
cents (WAIR and average-excess intermediates are carried exact — for the
golden fixture 200,000/2,800,000 must behave as exactly 1/14).
"""

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional

from ..model import CIPProject, DebtInstrument
from .basis_reconciliation import reconcile

_CENT = Decimal("0.01")
_ZERO = Decimal("0")


def _dec(v) -> Decimal:
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v)) if v is not None else _ZERO


def _q(v: Decimal) -> Decimal:
    """Quantize a FINAL dollar output to cents (never an intermediate)."""
    return v.quantize(_CENT, rounding=ROUND_HALF_UP)


def _exclusion_screen(debt: DebtInstrument) -> str:
    """Name the §1.263A-9(a)(4) screen that excluded an ineligible debt.
    Mirrors DebtInstrument.is_eligible_debt's order; first match reported."""
    if debt.disallowed_163_8T:
        return "§1.263A-9(a)(4) — interest disallowed under §1.163-8T(m)(7)(ii)"
    if debt.related_party_below_afr:
        return ("§1.263A-9(a)(4)(iii) — related-person debt at a below-AFR "
                "rate at issuance")
    if debt.personal_or_qualified_residence:
        return ("§1.263A-9(a)(4) — personal interest (§163(h)(2)) / qualified "
                "residence interest (§163(h)(3))")
    if debt.tax_exempt_org_nonbusiness:
        return ("§1.263A-9(a)(4) — tax-exempt organization debt outside an "
                "unrelated trade or business")
    if debt.non_interest_bearing and not debt.traced_to:
        return ("§1.263A-9(a)(4) — non-interest-bearing debt (accounts "
                "payable etc.) that is not itself traced debt")
    return "§1.263A-9(a)(4) — excluded (unspecified screen)"


def _normalize_date_key(k: str) -> str:
    """'2026-3-31' / '03/31/2026' style keys normalize to ISO so a format
    mismatch can't silently fall back to principal (red-team finding)."""
    s = str(k).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return s


def _outstanding_at(debt: DebtInstrument, d: date,
                    misses: Optional[List[str]] = None) -> Decimal:
    """Point-in-time outstanding balance on measurement date d: the dated
    schedule when supplied, else the principal (= average outstanding
    fallback). A debt WITH a dated schedule that lacks this specific date
    records a miss — silently substituting principal distorted WAIR by 3x
    in the round-3 counterexample. Keys must already be normalized (done
    once per debt in compute_263af — re-normalizing the whole dict per call
    was O(dates² × debts): 128s on a 365-date/200-debt engagement)."""
    if not debt.outstanding_by_date:
        return debt.principal
    iso = d.isoformat()
    if iso not in debt.outstanding_by_date:
        if misses is not None:
            misses.append(f"{debt.debt_id or debt.description}@{iso}")
        return debt.principal
    return debt.outstanding_by_date[iso]


def compute_263af(cip_projects: List[CIPProject],
                  debts: List[DebtInstrument], *,
                  afr_highest: Optional[Decimal] = None,
                  below_afr_interest: Decimal = Decimal("0"),
                  guaranteed_payments: Decimal = Decimal("0")) -> dict:
    """§263A(f) avoided-cost computation for one computation period.

    Every project in `cip_projects` is treated as an active designated-
    property unit (designated-property classification and unit-of-property
    determination happen upstream). Returns per-unit worksheets plus the
    taxpayer-level WAIR, proration, and per-source consumption results.
    """
    below_afr_interest = _dec(below_afr_interest)
    guaranteed_payments = _dec(guaranteed_payments)
    if afr_highest is not None:
        afr_highest = _dec(afr_highest)

    warnings: List[str] = []

    # ---- eligible-debt screens (§1.263A-9(a)(4)) -------------------------
    # Ineligible debt is excluded from BOTH tracing and the WAIR pool; the
    # model's is_eligible_debt property owns the rule — do not reimplement.
    eligible: List[DebtInstrument] = []
    for debt in debts:
        if debt.outstanding_by_date:
            # normalize dated-balance keys ONCE per instrument (in place —
            # this engine already mutates the floored interest field below)
            debt.outstanding_by_date = {
                _normalize_date_key(k): v
                for k, v in debt.outstanding_by_date.items()}
        if debt.interest_incurred < 0:
            # a negative incurred figure produced a NEGATIVE WAIR, negative
            # capitalization, and a fabricated deductible remainder through
            # the min() consumption chain (round-3 fuzz, confirmed) —
            # floor + warn, mirroring the SCA negative-driver block
            warnings.append(
                f"NEGATIVE-INTEREST-INCURRED [{debt.debt_id or debt.description}]: "
                f"${debt.interest_incurred:,.2f} floored to 0 — interest "
                f"incurred cannot be negative; route rebates/adjustments "
                f"through the schedule, not a negative figure.")
            debt.interest_incurred = _ZERO
        if debt.is_eligible_debt:
            eligible.append(debt)
        else:
            warnings.append(
                f"INELIGIBLE-DEBT [{debt.debt_id or debt.description}]: "
                f"excluded from tracing and the WAIR pool — "
                f"{_exclusion_screen(debt)}.")

    project_ids = {p.project_id for p in cip_projects}
    traced_by_unit: Dict[str, List[DebtInstrument]] = {}
    nontraced: List[DebtInstrument] = []
    for debt in eligible:
        if debt.traced_to:
            if debt.traced_to not in project_ids:
                warnings.append(
                    f"TRACED-TO-UNKNOWN-UNIT [{debt.debt_id or debt.description}]: "
                    f"traced_to={debt.traced_to!r} matches no unit given to "
                    f"this computation — interest neither traced nor in the "
                    f"WAIR pool; review the tracing schedule.")
                continue
            traced_by_unit.setdefault(debt.traced_to, []).append(debt)
        else:
            nontraced.append(debt)

    # The computation period's measurement-date grid (§1.263A-9(f)):
    # measurement dates are ONE taxpayer-level convention, not per-unit data
    # grids. Use the union ONLY when every unit's dates nest inside the
    # largest unit's set (a partial-period unit on the same convention).
    # A naive union of mixed frequencies (one monthly unit + one quarterly
    # unit) zero-padded every unit against 16 dates — a 4x understatement of
    # a full-year quarterly unit's average excess (round-3 red team, found
    # in round 2's own fix). Mixed grids get a HARD warning and per-unit
    # denominators (no zero-padding), never silent cross-contamination.
    per_unit_dates = [
        {s.measurement_date for s in p.snapshots if s.measurement_date is not None}
        for p in cip_projects if p.snapshots]
    union_dates = set().union(*per_unit_dates) if per_unit_dates else set()
    largest = max(per_unit_dates, key=len) if per_unit_dates else set()
    grids_nested = bool(per_unit_dates) and largest == union_dates and all(
        ds <= largest for ds in per_unit_dates)
    if per_unit_dates and not grids_nested:
        warnings.append(
            "MIXED-MEASUREMENT-GRID: units carry snapshot dates on different "
            "conventions (their date sets do not nest) — §1.263A-9(f) uses "
            "ONE taxpayer-level measurement-date convention. Each unit was "
            "averaged over ITS OWN dates (no zero-padding); align the CIP "
            "snapshot schedules to one grid before relying on this "
            "computation.")
    all_dates = sorted(union_dates) if grids_nested else []

    # ---- WAIR (§1.263A-9(c)(5)(iii)) — one taxpayer-level rate -----------
    nontraced_interest = sum((d.interest_incurred for d in nontraced), _ZERO)
    avg_nontraced_outstanding = _ZERO
    balance_misses: List[str] = []
    if nontraced:
        if all_dates and any(d.outstanding_by_date for d in nontraced):
            total = sum((_outstanding_at(debt, d, balance_misses)
                         for d in all_dates for debt in nontraced), _ZERO)
            avg_nontraced_outstanding = total / Decimal(len(all_dates))
        else:
            # principal = average outstanding fallback, summed as given
            avg_nontraced_outstanding = sum((d.principal for d in nontraced),
                                            _ZERO)

    if avg_nontraced_outstanding > 0:
        # exact Decimal division — never rounded before it multiplies
        wair = nontraced_interest / avg_nontraced_outstanding
        wair_source = "nontraced"
    elif nontraced_interest > 0:
        # Inconsistent data: nontraced interest incurred but zero average
        # outstanding on every measurement date. Falling back to the AFR
        # while also treating that interest as consumable would be
        # internally inconsistent (red-team finding) — refuse, don't guess.
        wair = _ZERO
        wair_source = "unavailable"
        warnings.append(
            f"WAIR-DATA-INCONSISTENT: ${nontraced_interest:,.2f} nontraced "
            f"interest incurred but zero nontraced principal outstanding on "
            f"every measurement date — WAIR cannot be computed and the AFR "
            f"fallback does not apply (debt existed). Excess amounts "
            f"computed as ZERO; fix the debt schedule's dated balances.")
    elif afr_highest is not None:
        # §1.263A-9(c)(5)(iii)(D): no nontraced debt outstanding during the
        # computation period → the highest §1274(d) AFR in effect stands in.
        wair = afr_highest
        wair_source = "afr_fallback"
        warnings.append(
            "WAIR-AFR-FALLBACK: no eligible nontraced debt outstanding "
            "during the computation period — WAIR set to the highest "
            "applicable Federal rate per §1.263A-9(c)(5)(iii)(D).")
    else:
        wair = _ZERO
        wair_source = "unavailable"
        warnings.append(
            "WAIR-UNAVAILABLE: no eligible nontraced debt outstanding AND no "
            "highest AFR supplied — §1.263A-9(c)(5)(iii)(D) fallback cannot "
            "run; excess expenditure amounts computed as ZERO. Supply "
            "afr_highest before relying on this computation.")

    # ---- per-unit snapshot mechanics (§1.263A-9(b)/(c)) ------------------
    per_unit: Dict[str, dict] = {}
    raw_excess: Dict[str, Decimal] = {}   # exact, pre-proration
    for project in cip_projects:
        pid = project.project_id
        if project.is_common_feature:
            warnings.append(
                f"COMMON-FEATURE-OUT-OF-SCOPE [{pid}]: §1.263A-10(b) "
                f"common-feature/unit-of-property mechanics are not "
                f"implemented — treated as a standalone designated-property "
                f"unit.")

        unit_debts = traced_by_unit.get(pid, [])
        # Traced debt amount = ACTUAL interest incurred on the traced debt
        # for the period (§1.263A-9(b)(2)) — never a rate × day estimate,
        # never prorated, never capped.
        traced_interest = sum((d.interest_incurred for d in unit_debts), _ZERO)

        snaps = sorted((s for s in project.snapshots
                        if s.measurement_date is not None),
                       key=lambda s: s.measurement_date)
        ape: Dict[str, Decimal] = {}
        traced_by_date: Dict[str, Decimal] = {}
        excess_by_date: Dict[str, Decimal] = {}
        for s in snaps:
            iso = s.measurement_date.isoformat()
            if iso in ape:
                warnings.append(
                    f"DUPLICATE-MEASUREMENT-DATE [{pid}] {iso}: two APE "
                    f"snapshots on the same date — the later row overwrote "
                    f"the earlier (${ape[iso]:,.2f}). Fix the CIP schedule.")
            ape[iso] = s.cumulative_ape
            # traced_debt_d is a point-in-time tracing snapshot, NOT
            # min(APE_d, principal) — see §1.263A-9(c)(5)(i)(B)'s
            # Property D/E example.
            traced_d = sum((_outstanding_at(d, s.measurement_date, balance_misses)
                            for d in unit_debts), _ZERO)
            traced_by_date[iso] = traced_d
            excess_by_date[iso] = max(_ZERO, s.cumulative_ape - traced_d)

        if excess_by_date:
            # §1.263A-9(f)(2)(iii) measurement-date convention: dates in the
            # computation period OUTSIDE the unit's own production period
            # count as ZERO in the numerator and the denominator is the FULL
            # period's measurement-date count. Dividing by the unit's own
            # snapshot count overstated a partial-period unit's average by
            # the missing-dates ratio (2x in the red-team counterexample).
            denominator = Decimal(len(all_dates)) if all_dates else \
                Decimal(len(excess_by_date))
            average_excess = sum(excess_by_date.values(), _ZERO) / denominator
            if all_dates and len(excess_by_date) < len(all_dates):
                warnings.append(
                    f"PARTIAL-PERIOD-UNIT [{pid}]: {len(excess_by_date)} APE "
                    f"snapshots over a {len(all_dates)}-date computation "
                    f"period — missing dates treated as zero excess per the "
                    f"§1.263A-9(f)(2)(iii) snapshot convention. Confirm the "
                    f"unit's production period actually excludes those dates "
                    f"(a missing data row would UNDERSTATE capitalization).")
        else:
            average_excess = _ZERO
            warnings.append(
                f"NO-MEASUREMENT-DATES [{pid}]: unit has no dated APE "
                f"snapshots — average excess expenditures computed as ZERO; "
                f"only traced interest capitalized. Supply the CIP snapshot "
                f"schedule.")

        raw_excess[pid] = average_excess * wair
        per_unit[pid] = {
            "measurement_dates": sorted(ape.keys()),
            "ape_snapshots": ape,
            "traced_debt_by_date": traced_by_date,
            "excess_by_date": excess_by_date,
            "average_excess": average_excess,
            "traced_interest": _q(traced_interest),
        }

    if balance_misses:
        shown = ", ".join(balance_misses[:6])
        more = f" (+{len(balance_misses) - 6} more)" if len(balance_misses) > 6 else ""
        warnings.append(
            f"DATED-BALANCE-MISSING: debts with dated balance schedules lack "
            f"a balance on these measurement dates — principal was "
            f"substituted, which can distort WAIR and traced-debt snapshots: "
            f"{shown}{more}. Complete the debt balance schedule.")

    # ---- pro-rata cap on the excess pool ONLY (§1.263A-9(c)(1)/(c)(7)) ---
    total_available = nontraced_interest + below_afr_interest + guaranteed_payments
    sum_raw = sum(raw_excess.values(), _ZERO)
    prorated = False
    if sum_raw > total_available:
        # (c)(7)(i)(B) prorates by average-excess share; scaling every
        # unit's amount by total_available/sum_raw is mathematically
        # identical because WAIR is a single taxpayer-level rate.
        factor = total_available / sum_raw       # exact Decimal
        raw_excess = {pid: amt * factor for pid, amt in raw_excess.items()}
        prorated = True
        warnings.append(
            f"PRORATED: aggregate excess expenditure amounts "
            f"(${_q(sum_raw):,}) exceed total interest available for "
            f"capitalization (${_q(total_available):,}) — each unit's excess "
            f"amount scaled pro rata per §1.263A-9(c)(7); traced interest is "
            f"never prorated.")

    # ---- finalize per-unit dollars + basis reconciliation (Step 3b) ------
    # Penny-plug after proration: quantizing each unit independently drifted
    # Σ excess a cent past total_available (capitalized interest with no
    # interest source — round-3 fuzz). Plug the largest unit so the
    # prorated sum lands exactly on the cap, same pattern as SCA's splits.
    quantized = {pid: _q(amt) for pid, amt in raw_excess.items()}
    if prorated and quantized:
        drift = sum(quantized.values(), _ZERO) - _q(total_available)
        if drift != 0:
            largest = max(quantized, key=lambda p: quantized[p])
            quantized[largest] -= drift

    total_traced = _ZERO
    total_excess = _ZERO
    projects_by_id = {p.project_id: p for p in cip_projects}
    for pid, unit in per_unit.items():
        excess_amount = quantized[pid]
        unit["excess_expenditure_amount"] = excess_amount
        unit["total_capitalized"] = unit["traced_interest"] + excess_amount
        total_traced += unit["traced_interest"]
        total_excess += excess_amount

        # Runtime Pipeline Step 3b item (3): post only the tax-over-book
        # delta when ASC 835-20 interest is already in the book basis;
        # book > tax flags rather than posting a negative.
        project = projects_by_id[pid]
        book = project.book_capitalized_interest
        unit["book_capitalized_interest"] = book
        delta, rec_warnings = reconcile(book, unit["total_capitalized"],
                                        f"§263A(f) interest — {pid}")
        unit["tax_delta_to_post"] = delta
        warnings.extend(rec_warnings)

    # ---- per-source sequential consumption (DECISION 2026-07-08) ---------
    # Nontraced → below-AFR related-party → §707(c) guaranteed payments
    # (§1.263A-9(c)(2)), each min()-capped; every source's unconsumed
    # remainder stays ordinary deductible interest. Additive output only —
    # never changes total_excess or the per-unit split.
    remaining = total_excess
    consumed_nontraced = min(nontraced_interest, remaining)
    remaining -= consumed_nontraced
    consumed_below_afr = min(below_afr_interest, remaining)
    remaining -= consumed_below_afr
    consumed_guaranteed = min(guaranteed_payments, remaining)
    remaining -= consumed_guaranteed
    consumption = {
        "nontraced_consumed": _q(consumed_nontraced),
        "below_afr_consumed": _q(consumed_below_afr),
        "guaranteed_payments_consumed": _q(consumed_guaranteed),
        "nontraced_remaining_deductible": _q(nontraced_interest
                                             - consumed_nontraced),
        "below_afr_remaining_deductible": _q(below_afr_interest
                                             - consumed_below_afr),
        "guaranteed_payments_remaining_deductible": _q(guaranteed_payments
                                                       - consumed_guaranteed),
        # zero by construction whenever the (c)(7) cap ran; kept visible as
        # a tie-check rather than assumed
        "unsourced_excess": _q(remaining),
    }

    return {
        "per_unit": per_unit,
        "wair": wair,
        "wair_source": wair_source,
        "total_traced": total_traced,
        "total_excess": total_excess,
        "total_capitalized": total_traced + total_excess,
        "prorated": prorated,
        "consumption": consumption,
        "warnings": warnings,
    }
