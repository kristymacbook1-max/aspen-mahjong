"""Phase C — self-constructed-asset additional-§263A allocation (bucket B).

Three basis buckets per asset (BUILD_PLAN.md Phase C): A = book/CIP cost
(input, never recomputed here), B = additional §263A (this engine), C =
§263A(f) interest (Phase D — this engine only emits `ape_for_interest`).

Allocation model, per pool, across the pool's FULL declared target set
({assets..., NON_PRODUCTION}):

    share(t) = driver_value(t) / Σ driver_value
    allocated(t) = round2(pool.amount × share(t)); penny-plug largest

Mixed-service pools follow the ADOPTED Option-(B) ordering (DECISION
2026-07-08, docs/TAX_DECISIONS.md §8c): driver-split the FULL pool FIRST,
THEN gate each asset's resulting share through §1.263A-1(h)(2) SSCM
eligibility. An eligible share gets the SSCM capitalizable/deductible split;
an INELIGIBLE share is computed, kept visible in the audit trail, flagged
SSCM-INELIGIBLE-NO-FALLBACK, and NOT booked to bucket B (the general
§1.263A-1(g)(4) direct-reallocation/step-allocation fallback is documented
future work — the ratio is deliberately NOT applied to an ineligible share,
since applying it would presume the very SSCM eligibility that failed).
Non-mixed (plain indirect) pools have no SSCM step at all — the (h)(2) gate
governs the simplified service cost method only, so every asset share books
to indirect_263a regardless of `sscm_eligible`.

Driver reasonableness comes from taxonomy/sca_drivers.yaml: hard-blocked
pairings (HR by machine-hours) leave the pool UNALLOCATED with
HARD-BLOCKED-DRIVER; non-preferred-but-not-blocked pairings warn only.

The bucket A/B double-count question (book-capitalized indirect costs already
in CIP re-added through B) is explicitly UNRESOLVED — BUILD_PLAN.md Basis
Reconciliation §(2) and Gate 6 Q6.3 both route it to the review queue. A
nonzero `book_capitalized_indirect` entry therefore emits
CIP-DOUBLE-COUNT-REVIEW without adjusting any computed amount.
"""

import os
import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional

import yaml

from ..model import CostPool, SelfConstructedAsset

_DEFAULT_DRIVERS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                     "taxonomy", "sca_drivers.yaml")

NON_PRODUCTION = "NON_PRODUCTION"

_TWO = Decimal("0.01")


def _q(v: Decimal) -> Decimal:
    return v.quantize(_TWO, rounding=ROUND_HALF_UP)


def _canon(s: str) -> str:
    """Same canonical form taxonomy.py uses: lowercase, hyphens/slashes as
    spaces, collapsed whitespace — so 'Depreciation - Building' matches the
    'depreciation - building' keyword."""
    return re.sub(r"\s+", " ",
                  str(s).lower().replace("-", " ").replace("/", " ")).strip()


class DriverTaxonomyError(ValueError):
    pass


def load_drivers(path: Optional[str] = None) -> dict:
    """Load + shape-validate sca_drivers.yaml. Every driver name appearing in
    `categories` or `default` must be declared in the top-level `drivers`
    list — an unknown name is a dead entry (the taxonomy.py cross-reference
    principle) and errors at load, not silently at allocation time."""
    with open(path or _DEFAULT_DRIVERS_PATH, "r") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise DriverTaxonomyError("sca_drivers.yaml: top level must be a mapping")
    known = data.get("drivers")
    if not isinstance(known, list) or not all(isinstance(d, str) for d in known):
        raise DriverTaxonomyError("sca_drivers.yaml: `drivers` must be a list of names")
    known_set = set(known)

    def _check(names, where):
        if not isinstance(names, list):
            raise DriverTaxonomyError(f"sca_drivers.yaml: {where} must be a list")
        for n in names:
            if n not in known_set:
                raise DriverTaxonomyError(
                    f"sca_drivers.yaml: unknown driver {n!r} in {where} — "
                    f"declare it in `drivers` or fix the typo")

    cats = data.get("categories", [])
    if not isinstance(cats, list):
        raise DriverTaxonomyError("sca_drivers.yaml: `categories` must be a list")
    for i, cat in enumerate(cats):
        if not isinstance(cat, dict) or not isinstance(cat.get("match_keywords"), list):
            raise DriverTaxonomyError(
                f"sca_drivers.yaml: categories[{i}] needs a match_keywords list")
        _check(cat.get("preferred", []), f"categories[{i}].preferred")
        _check(cat.get("blocked", []), f"categories[{i}].blocked")
    default = data.get("default", {})
    if not isinstance(default, dict):
        raise DriverTaxonomyError("sca_drivers.yaml: `default` must be a mapping")
    _check(default.get("allowed", []), "default.allowed")
    return data


def _match_category(description: str, taxonomy: dict) -> Optional[dict]:
    """First category whose keyword appears (word-bounded) in the pool
    description; word boundaries keep 'hr'/'it' from firing inside words."""
    desc = _canon(description)
    for cat in taxonomy.get("categories", []):
        for kw in cat["match_keywords"]:
            if re.search(r"\b" + re.escape(_canon(kw)) + r"\b", desc):
                return cat
    return None


def _validate_driver(pool: CostPool, taxonomy: dict) -> List[str]:
    """Guardrail check -> warning list. A HARD-BLOCKED-DRIVER warning in the
    result means the pool must NOT be allocated."""
    warnings: List[str] = []
    known = set(taxonomy.get("drivers", []))
    label = f"pool {pool.pool_id} ({pool.description!r})"
    if pool.driver not in known:
        # An undeclared driver can't be reasonableness-checked at all; treat
        # like a hard block rather than allocating on an unvetted basis.
        warnings.append(
            f"HARD-BLOCKED-DRIVER [{label}]: driver {pool.driver!r} is not a "
            f"recognized allocation driver — pool not allocated")
        return warnings
    cat = _match_category(pool.description, taxonomy)
    if cat is not None:
        if pool.driver in cat.get("blocked", []):
            warnings.append(
                f"HARD-BLOCKED-DRIVER [{label}]: {pool.driver!r} is a "
                f"nonsensical driver for this pool category "
                f"(keywords {cat['match_keywords']}) — pool not allocated")
        elif cat.get("preferred") and pool.driver not in cat["preferred"]:
            warnings.append(
                f"SOFT-DRIVER-MISMATCH [{label}]: {pool.driver!r} is not a "
                f"preferred driver for this pool category "
                f"(preferred {cat['preferred']}) — allocated anyway; review")
    elif pool.driver not in taxonomy.get("default", {}).get("allowed", known):
        warnings.append(
            f"SOFT-DRIVER-MISMATCH [{label}]: {pool.driver!r} is outside the "
            f"default allowed driver set — allocated anyway; review")
    return warnings


def _split_pool(pool: CostPool) -> Dict[str, Decimal]:
    """share -> round2 -> penny-plug largest, so Σ allocated == pool.amount
    exactly (conservation). Caller guarantees Σ driver values > 0."""
    total = sum(pool.targets.values(), Decimal("0"))
    allocated: Dict[str, Decimal] = {
        t: _q(pool.amount * dv / total) for t, dv in pool.targets.items()}
    plug = pool.amount - sum(allocated.values(), Decimal("0"))
    if plug:
        largest = max(pool.targets, key=lambda t: pool.targets[t])
        allocated[largest] += plug
    return allocated


def compute_sca(pools: List[CostPool], assets: List[SelfConstructedAsset],
                sscm_ratio: Decimal, drivers_path: Optional[str] = None,
                book_capitalized_indirect: Optional[Dict[str, Decimal]] = None
                ) -> dict:
    """Bucket-B allocation for every pool/asset; returns per_asset totals,
    the full per-pool-per-target audit trail, warnings (the shared
    bucket_warnings pattern — callers append these to unicap['warnings']),
    and per-pool conservation checks."""
    taxonomy = load_drivers(drivers_path)
    warnings: List[str] = []
    audit_trail: List[dict] = []
    conservation_checks: List[dict] = []
    not_booked_total = Decimal("0")
    deductible_total = Decimal("0")

    sscm_ratio = Decimal(str(sscm_ratio))
    if not (Decimal("0") <= sscm_ratio <= Decimal("1")):
        # Same clamp+warn pattern as analysis.py's compute_sscm_ratio — a
        # service-cost allocation ratio is definitionally a fraction.
        warnings.append(
            f"SSCM RATIO = {sscm_ratio} is outside [0,1] — clamped. Review.")
        sscm_ratio = max(Decimal("0"), min(Decimal("1"), sscm_ratio))

    by_id = {a.asset_id: a for a in assets}
    per_asset: Dict[str, dict] = {
        a.asset_id: {"book_cost": a.book_cost,
                     "indirect_263a": Decimal("0"),
                     "mixed_263a": Decimal("0")}
        for a in assets}

    for pool in pools:
        pool_warnings = _validate_driver(pool, taxonomy)
        warnings.extend(pool_warnings)
        blocked = any(w.startswith("HARD-BLOCKED-DRIVER") for w in pool_warnings)
        driver_total = sum(pool.targets.values(), Decimal("0"))
        block_flag = "HARD-BLOCKED-DRIVER"
        if pool.amount < 0 and not blocked:
            # the round-2 block covered negative DRIVER VALUES only — a
            # negative pool AMOUNT still booked negative capitalized dollars
            # (and negative APE into Phase D) with zero warnings (round-3)
            blocked = True
            block_flag = "NEGATIVE-POOL-AMOUNT"
            warnings.append(
                f"NEGATIVE-POOL-AMOUNT [pool {pool.pool_id}]: pool amount is "
                f"${pool.amount:,.2f} — a cost pool cannot be negative; pool "
                f"NOT allocated. Route credits/reversals through the "
                f"classifier, not a negative pool.")
        negative_drivers = [t for t, dv in pool.targets.items() if dv < 0]
        if negative_drivers and not blocked:
            # A negative driver value produces a NEGATIVE share and a
            # negative "capitalized" allocation to a real asset while the
            # conservation check still ties (red-team, confirmed) — refuse.
            blocked = True
            block_flag = "NEGATIVE-DRIVER-VALUE"
            warnings.append(
                f"NEGATIVE-DRIVER-VALUE [pool {pool.pool_id}]: driver values "
                f"for {negative_drivers} are negative — a driver share is a "
                f"fraction of a physical quantity; pool NOT allocated. Fix "
                f"the driver data.")
        degenerate = driver_total == 0
        if degenerate and not blocked:
            warnings.append(
                f"POOL-DEGENERATE-DENOMINATOR [pool {pool.pool_id}]: Σ driver "
                f"values == 0 — nothing allocated; supply real driver data")

        if blocked or degenerate:
            # Pool stays visible in the audit trail at allocated 0.
            for target, dv in pool.targets.items():
                audit_trail.append({
                    "pool_id": pool.pool_id, "target": target,
                    "driver": pool.driver, "driver_value": dv,
                    "share": Decimal("0"), "allocated": Decimal("0"),
                    "capitalized": Decimal("0"), "deductible": Decimal("0"),
                    "not_booked": Decimal("0"),
                    "flags": [block_flag] if blocked
                             else ["POOL-DEGENERATE-DENOMINATOR"]})
            conservation_checks.append({
                "pool_id": pool.pool_id, "pool_amount": pool.amount,
                "allocated_sum": Decimal("0"), "expected": Decimal("0"),
                "ok": True,
                "note": "pool not allocated (blocked/degenerate driver)"})
            continue

        allocated = _split_pool(pool)
        for target, dv in pool.targets.items():
            amt = allocated[target]
            share = dv / driver_total          # full-precision Decimal
            flags: List[str] = []
            capitalized = Decimal("0")
            deductible = Decimal("0")
            not_booked = Decimal("0")
            asset = by_id.get(target)

            if target == NON_PRODUCTION:
                deductible = amt
            elif asset is None:
                # A target that is neither an asset nor NON_PRODUCTION can't
                # be booked anywhere — surface it, don't guess a disposition.
                flags.append("POOL-TARGET-UNKNOWN")
                not_booked = amt
                warnings.append(
                    f"POOL-TARGET-UNKNOWN [pool {pool.pool_id}]: target "
                    f"{target!r} matches no asset — share ${amt:,.2f} not booked")
            elif pool.is_mixed_service:
                if asset.sscm_eligible:
                    capitalized = _q(amt * sscm_ratio)
                    deductible = amt - capitalized
                    per_asset[target]["mixed_263a"] += capitalized
                else:
                    # Option (B) gate: the FULL share is unresolved pending
                    # the general (g)(4) method — no ratio applied.
                    flags.append("SSCM-INELIGIBLE-NO-FALLBACK")
                    not_booked = amt
                    warnings.append(
                        f"SSCM-INELIGIBLE-NO-FALLBACK [pool {pool.pool_id} → "
                        f"{target}]: asset fails §1.263A-1(h)(2) routes (C)/(D); "
                        f"driver share ${amt:,.2f} computed but NOT booked to "
                        f"bucket B — general §1.263A-1(g)(4) method required")
            else:
                # Plain indirect pool: no SSCM step, eligibility irrelevant.
                capitalized = amt
                per_asset[target]["indirect_263a"] += capitalized

            not_booked_total += not_booked
            deductible_total += deductible
            audit_trail.append({
                "pool_id": pool.pool_id, "target": target,
                "driver": pool.driver, "driver_value": dv, "share": share,
                "allocated": amt, "capitalized": capitalized,
                "deductible": deductible, "not_booked": not_booked,
                "flags": flags})

        allocated_sum = sum(allocated.values(), Decimal("0"))
        conservation_checks.append({
            "pool_id": pool.pool_id, "pool_amount": pool.amount,
            "allocated_sum": allocated_sum, "expected": pool.amount,
            "ok": allocated_sum == pool.amount, "note": ""})
        if allocated_sum != pool.amount:
            warnings.append(
                f"POOL-CONSERVATION-FAILED [pool {pool.pool_id}]: allocated "
                f"{allocated_sum} != pool amount {pool.amount}. Do not proceed.")

    for asset_id, amount in (book_capitalized_indirect or {}).items():
        amount = Decimal(str(amount or 0))
        if amount != 0:
            # UNRESOLVED double-count rule (BUILD_PLAN.md Basis Reconciliation
            # §(2), Gate 6 Q6.3): review-queue only, computation unchanged.
            warnings.append(
                f"CIP-DOUBLE-COUNT-REVIEW [{asset_id}]: ${amount:,.2f} of "
                f"indirect cost is already book-capitalized in CIP (bucket A); "
                f"bucket B may re-add some or all of it. No adjustment made — "
                f"routed to review queue pending the bucket A/B double-count rule")

    for asset_id, row in per_asset.items():
        row["additional_263a"] = row["indirect_263a"] + row["mixed_263a"]
        row["adjusted_basis_pre_interest"] = row["book_cost"] + row["additional_263a"]
        # Bucket C is Phase D's: emit APE, never compute interest here.
        row["ape_for_interest"] = row["adjusted_basis_pre_interest"]

    return {"per_asset": per_asset,
            "ape_by_asset": {aid: r["ape_for_interest"]
                             for aid, r in per_asset.items()},
            "audit_trail": audit_trail,
            "warnings": warnings,
            "not_booked_total": not_booked_total,
            "deductible_total": deductible_total,
            "conservation_checks": conservation_checks}
