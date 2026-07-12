"""Phase B inventory engines — MSPM (§1.263A-2(c)) and SRM (§1.263A-3(d)).

Both engines take the `analyze()` result dict plus an `EntityProfile` and
return a superset of the `compute_spm` shape (same
`additional_capitalized_to_inventory` key), dispatched from
`analysis.compute_unicap`. All arithmetic is Decimal; dollar outputs are
quantized to cents, absorption ratios to the precision the source formula's
own worked presentation shows (MSPM 0.0001 per §1.263A-2(c)(3)(vi) Example 1's
8.00%/10.22%; SRM 0.000001 per the 0.043750-style presentation) — and, per
the BUILD_PLAN Phase B rounding DECISION, ONLY the absorption ratios are
rounded before multiplying; every other intermediate (including the MSPM
mixed-service split proportion) carries full Decimal precision.

INPUT CONTRACTS (violating these is a material error even when no warning
fires — the engines can only clamp/flag the breaches that produce impossible
arithmetic):

MSPM (§1.263A-2(c)(3)(ii)):
  * `pre_production_471_on_hand` / `production_471_on_hand` are limited to
    §471 costs the taxpayer INCURS DURING THE CURRENT TAXABLE YEAR that
    remain on hand at year end ((c)(3)(ii)(C)/(E)) — NOT raw balance-sheet
    ending-inventory balances containing prior-year cost layers. Under that
    definition `pre_production_471_on_hand <= pre_production_471` and both
    on-hand figures are >= 0 structurally; a negative residual or negative
    on-hand balance can only mean the inputs violate (C)/(E).
  * `pre_production_additional_263A` / `production_additional_263A` must NOT
    already include any share of capitalizable mixed service costs — this
    engine computes the SSCM-capitalizable amount and ADDS the
    (c)(3)(iii)(B) pre-production/production split into the pools itself
    (the OPPOSITE input contract from SRM's, below).
  * Every input excludes costs described in §1.263A-1(e)(3)(ii) and
    §1.471-3(e) cost reductions properly allocable entirely to property
    SOLD during the year ((c)(3)(ii)(F)) — a global input filter this
    engine cannot verify from the figures alone.
  * The §471/additional-§263A boundary is financial-statement-based
    (§1.263A-1(d)(2)(i)); the classifier's tier split is a proxy that must
    be reviewed against the taxpayer's actual book capitalization.

SRM (§1.263A-3(d)(3)(i)):
  * `purchasing_costs` and `storage_handling_costs` must ALREADY include
    their allocable mixed-service share per the (d)(3)(i)(F) ONE-STEP
    sub-split (each activity's labor ratio x TOTAL mixed service costs) —
    this engine reports the SSCM split for visibility but does NOT add
    `mixed_capitalized` into either pool.
  * `current_year_471_costs` is the reg's "current year's purchases" —
    §471 costs incurred on purchases of property acquired for resale during
    the year ((d)(3)(i)(D)(2)/(E)) — not an undifferentiated all-§471 total.
  * `ending_inventory_471` (the multiplier) is the (d)(3)(i)(C)(2) "§471
    costs remaining on hand at year end" — current-year-incurred costs on
    hand, excluding prior-year layers and (per Practice Unit COR-P-021,
    interpreting (C)(2)) goods valued below cost. For LIFO it is the
    current-year INCREMENT stated in §471 costs, unless permissible
    variation (d)(3)(iii)(B) is elected (`srm_variation_b`), in which case
    the caller supplies total ending-inventory §471 costs instead.
  * `storage_handling_costs` excludes the §1.263A-3(c)(4) handling
    carve-outs (retail-facility handling, distribution/pick-and-pack, etc.)
    and reflects only off-site/dual-function-allocated storage per (c)(5).
  * For LIFO, `beginning_inventory_471` is stated at LIFO carrying value
    ((d)(3)(i)(D)(2) last sentence).

Negative additional-§263A amounts are PERMITTED under both methods with no
gross-receipts restriction (§1.263A-1(d)(3)(ii)(B)(2)/(B)(3) — the dollar cap
in (B)(1) is SPM-only), but are always surfaced with a warning because the
(d)(3)(ii)(C)-(E) restrictions (no negatives for cash/trade discounts or
§162(c)/(e)/(f)/(g)-type amounts; consistency) still apply to their contents.
"""

from decimal import Decimal

from ..analysis import compute_sscm

MSPM_RATIO_Q = Decimal("0.0001")    # Example 1 presents 8.00% / 10.22%
SRM_RATIO_Q = Decimal("0.000001")   # worked example presents 0.043750
_NINETY = Decimal("0.9")


def _q(x: Decimal) -> Decimal:
    # widened context: see analysis._q — a huge ratio×pool product crashed
    # quantize before the absurd-ratio warning could fire (round-3 fuzz)
    import decimal
    with decimal.localcontext() as ctx:
        ctx.prec = 50
        return x.quantize(Decimal("0.01"))


def _ratio_sanity(warnings_, label, ratio):
    """SPM has warned on a >100% absorption ratio since round 1; MSPM/SRM
    never got the analog — 50,000,000x ratios computed silently into
    trillion-dollar capitalizations (round-3 fuzz, confirmed)."""
    if ratio > 1:
        warnings_.append(
            f"ABSORPTION RATIO {label} = {ratio} (>100%): the numerator pool "
            f"exceeds its entire base — almost always a data error; verify "
            f"the inputs before relying on this figure.")
    elif ratio < 0:
        warnings_.append(
            f"ABSORPTION RATIO {label} = {ratio} (<0): a negative ratio means "
            f"a negative pool or denominator — review the negative inputs.")


def compute_mspm(result: dict, profile) -> dict:
    """Modified simplified production method (§1.263A-2(c)): two absorption
    ratios (pre-production / production), residual pre-production rollover,
    and the direct-materials adjustment, per the verified Phase B formula."""
    warnings_ = []
    if profile.producer_de_minimis_200k:
        # §1.263A-2(c)(3)(v) via (b)(3)(iv): additional §263A deemed ZERO.
        if profile.har_election:
            warnings_.append(
                "HAR-BARRED-200K: the HAR election is not available to a "
                "taxpayer deemed to have zero additional §263A costs under "
                "the $200K de minimis (§1.263A-2(c)(4) refinement (4)) — "
                "election ignored.")
        return {
            "exempt": False, "method": "MSPM",
            "note": "§1.263A-2(c)(3)(v) $200K producer de minimis — "
                    "additional §263A costs deemed zero.",
            "warnings": warnings_,
            "mixed_alloc_ratio": Decimal("0"),
            "production_labor": Decimal("0"), "total_labor": Decimal("0"),
            "mixed_capitalized": Decimal("0"),
            "mixed_deductible": result["mixed_total"],
            "pre_production_ratio": Decimal("0"),
            "production_ratio": Decimal("0"),
            "pre_production_pool": Decimal("0"), "production_pool": Decimal("0"),
            "residual_pre_production_263A": Decimal("0"),
            "direct_materials_adjustment": Decimal("0"),
            "pre_production_471": profile.pre_production_471,
            "production_471": profile.production_471,
            "pre_production_471_on_hand": profile.pre_production_471_on_hand,
            "production_471_on_hand": profile.production_471_on_hand,
            "additional_capitalized_to_inventory": Decimal("0"),
            "adjusted_deductible_post": result["deductible_total"] + result["mixed_total"],
        }

    sscm = compute_sscm(result, profile)
    if sscm["ratio_warning"]:
        warnings_.append(sscm["ratio_warning"])
    mixed_cap = sscm["mixed_capitalized"]
    mixed_ded = sscm["mixed_deductible"]

    # (h)(5) production-cost ratio is implemented in compute_sscm as of
    # round 5 (producers only; resellers fall back with a warning).

    # --- SSCM split between pre-production and production pools,
    # §1.263A-2(c)(3)(iii)(B): taxpayer's choice of the direct-material
    # proportion or the pre-production-labor proportion. The proportion is
    # carried at full precision (rounding DECISION 2026-07-08).
    split_denom = profile.pre_production_471 + profile.production_471
    dm_prop = (profile.DM_purchased_during_year / split_denom) if split_denom \
        else Decimal("0")
    split_method_used = "direct_material"
    pre_prop = dm_prop
    if profile.mspm_mixed_split_method == "labor":
        raw = getattr(profile, "mspm_labor_split_proportion", None)
        if raw is None:
            if mixed_cap:
                warnings_.append(
                    "MSPM-SPLIT-INPUT-MISSING: mspm_mixed_split_method='labor' but no "
                    "mspm_labor_split_proportion (pre-production labor / total labor, both "
                    "excluding mixed-service labor, §1.263A-2(c)(3)(iii)(B)) was supplied — "
                    "fell back to the direct-material proportion. Supply the labor "
                    "proportion or change the split method.")
        else:
            pre_prop = Decimal(str(raw))
            split_method_used = "labor"
            if not (Decimal("0") <= pre_prop <= Decimal("1")):
                warnings_.append(
                    f"MSPM-SPLIT-PROPORTION-INVALID: mspm_labor_split_proportion={pre_prop} "
                    f"is outside [0,1] — a split proportion is a fraction; clamped. "
                    f"Check the input.")
                pre_prop = min(max(pre_prop, Decimal("0")), Decimal("1"))
    if mixed_cap and split_method_used == "direct_material" and split_denom == 0:
        warnings_.append(
            "MSPM-SPLIT-ZERO-DENOMINATOR: total §471 costs incurred "
            "(pre_production_471 + production_471) is zero — the direct-material split "
            "proportion defaulted to 0 (all mixed service costs to production). Review.")

    # (c)(3)(iii)(C) 90% de minimis election: if >=90% of capitalizable mixed
    # service costs allocate to one bucket, taxpayer may elect 100% there.
    ninety_pct_applied = False
    if profile.mspm_90pct_split_election:
        if pre_prop >= _NINETY:
            pre_prop, ninety_pct_applied = Decimal("1"), True
        elif (Decimal("1") - pre_prop) >= _NINETY:
            pre_prop, ninety_pct_applied = Decimal("0"), True
    mixed_pre = mixed_cap * pre_prop
    mixed_prod = mixed_cap - mixed_pre

    # Shares enter the pools BEFORE either absorption ratio is computed
    # ((c)(3)(iii)(B): the split amounts are "included in" the additional
    # §263A cost pools the ratios are built from).
    pre_pool = profile.pre_production_additional_263A + mixed_pre
    prod_pool = profile.production_additional_263A + mixed_prod
    for name, pool, cite in (("pre-production", pre_pool, "(B)(2)"),
                             ("production", prod_pool, "(B)(2)")):
        if pool < 0:
            warnings_.append(
                f"MSPM-NEGATIVE-POOL: the {name} additional §263A pool is negative "
                f"(${pool:,.2f}). Negative adjustments are permitted under the MSPM with "
                f"no gross-receipts restriction (§1.263A-1(d)(3)(ii)(B)(2), unlike the "
                f"SPM), but verify none derive from cash/trade discounts or "
                f"§162(c)/(e)/(f)/(g)-type amounts (§1.263A-1(d)(3)(ii)(C)-(E)).")

    # On-hand multiplicands: current-year-incurred costs remaining on hand
    # ((c)(3)(ii)(C)/(E)) — structurally >= 0; a negative can only be an
    # input-contract breach (see module docstring). Floor + flag.
    pre_on_hand = profile.pre_production_471_on_hand
    prod_on_hand = profile.production_471_on_hand
    if pre_on_hand < 0:
        warnings_.append(
            f"MSPM-NEGATIVE-ON-HAND-BALANCE: pre_production_471_on_hand "
            f"(${pre_on_hand:,.2f}) is negative — input inconsistent with "
            f"§1.263A-2(c)(3)(ii)(C)/(E): on-hand figures must be current-year-incurred "
            f"costs remaining on hand, not raw inventory balances. Floored at 0.")
        pre_on_hand = Decimal("0")
    if prod_on_hand < 0:
        warnings_.append(
            f"MSPM-NEGATIVE-ON-HAND-BALANCE: production_471_on_hand "
            f"(${prod_on_hand:,.2f}) is negative — input inconsistent with "
            f"§1.263A-2(c)(3)(ii)(C)/(E): on-hand figures must be current-year-incurred "
            f"costs remaining on hand, not raw inventory balances. Floored at 0.")
        prod_on_hand = Decimal("0")

    # Pre-production absorption ratio, quantized BEFORE any multiplication
    # (the regulation's own Example 1 presentation — 8.00%).
    if profile.pre_production_471:
        pre_ratio = (pre_pool / profile.pre_production_471).quantize(MSPM_RATIO_Q)
    else:
        pre_ratio = Decimal("0")
        warnings_.append(
            "MSPM-ZERO-DENOMINATOR: pre_production_471 is zero — the pre-production "
            "absorption ratio was set to 0. Verify the §471 direct-material/resale "
            "cost inputs.")

    # Residual pre-production §263A not absorbed into pre-production ending
    # inventory rolls into the production ratio's numerator ((c)(3)(ii)).
    residual = pre_pool - pre_ratio * pre_on_hand
    if residual < 0:
        warnings_.append(
            f"MSPM-NEGATIVE-RESIDUAL-FLOORED: residual pre-production §263A computed "
            f"negative (${residual:,.2f}) — input inconsistent with "
            f"§1.263A-2(c)(3)(ii)(C)/(E): on-hand figures must be current-year-incurred "
            f"costs remaining on hand, not raw inventory balances (a compliant "
            f"pre_production_471_on_hand cannot exceed pre_production_471). Floored at 0.")
        residual = Decimal("0")

    dm_adjustment = (profile.beginning_DM_not_yet_in_production
                     + profile.DM_purchased_during_year
                     - profile.ending_DM_not_yet_in_production)

    prod_denom = profile.production_471 + dm_adjustment
    if prod_denom < 0:
        # ending DM-not-in-production exceeding beginning + purchased makes
        # the DM adjustment more negative than production_471 — a negative
        # denominator produced a negative ratio and NEGATIVE capitalization
        # with zero warnings (round-3 fuzz, confirmed)
        production_ratio = Decimal("0")
        warnings_.append(
            f"MSPM-NEGATIVE-DENOMINATOR: production_471 + "
            f"direct_materials_adjustment is negative (${prod_denom:,.2f}) — "
            f"ending DM-not-yet-in-production exceeds beginning + purchases, "
            f"an impossible materials flow. Ratio set to 0; fix the DM "
            f"inputs.")
    elif prod_denom:
        production_ratio = ((prod_pool + residual) / prod_denom).quantize(MSPM_RATIO_Q)
    else:
        production_ratio = Decimal("0")
        warnings_.append(
            "MSPM-ZERO-DENOMINATOR: production_471 + direct_materials_adjustment is "
            "zero — the production absorption ratio was set to 0. Verify the "
            "production §471 and direct-material flow inputs.")

    _ratio_sanity(warnings_, "(MSPM pre-production)", pre_ratio)
    _ratio_sanity(warnings_, "(MSPM production)", production_ratio)
    actual_pre, actual_prod = pre_ratio, production_ratio

    is_lifo = profile.inventory_method in ("lifo_specific", "lifo_dollar_value")
    har_applied = False
    if profile.har_election and not is_lifo:
        # §1.263A-2(c)(4): frozen historic ratios for the qualifying period.
        if profile.har_preprod_ratio is None or profile.har_production_ratio is None:
            warnings_.append(
                "HAR-RATIOS-MISSING: har_election set but the frozen "
                "pre-production/production historic ratios were not supplied "
                "— ACTUAL ratios used; supply har_preprod_ratio and "
                "har_production_ratio.")
        elif profile.har_qualifying_year_index == 6:
            # recomputation year: BOTH ratios within ±0.5 percentage points
            # of actuals (conjunctive) → extension (recomputation year + 5
            # following); either outside → actuals apply, HAR resumes on the
            # updated test period in the 3rd year following.
            band = Decimal("0.005")
            passes = (abs(profile.har_preprod_ratio - actual_pre) <= band
                      and abs(profile.har_production_ratio - actual_prod) <= band)
            if passes:
                pre_ratio = profile.har_preprod_ratio.quantize(MSPM_RATIO_Q)
                production_ratio = profile.har_production_ratio.quantize(MSPM_RATIO_Q)
                har_applied = True
                warnings_.append(
                    "HAR-RECOMPUTATION-PASSED: both historic ratios within "
                    "±0.5pp of actuals — HAR extends through the "
                    "recomputation year and the five following taxable years "
                    "(§1.263A-2(c)(4)).")
            else:
                warnings_.append(
                    "HAR-RECOMPUTATION-FAILED: a historic ratio fell outside "
                    "±0.5pp of the actual ratio (conjunctive test) — ACTUAL "
                    "ratios applied this year; HAR must RESUME on the "
                    "updated test period in the third taxable year following "
                    "the recomputation year (§1.263A-2(c)(4)).")
        else:
            pre_ratio = profile.har_preprod_ratio.quantize(MSPM_RATIO_Q)
            production_ratio = profile.har_production_ratio.quantize(MSPM_RATIO_Q)
            har_applied = True

    nonlifo_add = _q(pre_ratio * pre_on_hand + production_ratio * prod_on_hand)

    combined_ratio = None
    if is_lifo:
        # §1.263A-2(c)(3)(iv): MSPM under LIFO collapses to ONE combined
        # absorption ratio — total additional §263A allocable to property on
        # hand ÷ total §471 on hand, both on a NON-LIFO basis — applied to
        # the current-year increment stated in §471 costs (the regulation's
        # own Example 3: 284,400 ÷ 3,000,000 = 9.48% × 1,500,000 = 142,200).
        total_on_hand = pre_on_hand + prod_on_hand
        if profile.har_election:
            if profile.har_combined_ratio is not None:
                combined_ratio = profile.har_combined_ratio.quantize(MSPM_RATIO_Q)
                har_applied = True
            else:
                warnings_.append(
                    "HAR-RATIOS-MISSING: har_election under LIFO needs the "
                    "COMBINED historic absorption ratio ((c)(4)(iii)) — "
                    "har_combined_ratio not supplied; the actual combined "
                    "ratio was used.")
        if combined_ratio is None:
            combined_ratio = (nonlifo_add / total_on_hand).quantize(MSPM_RATIO_Q) \
                if total_on_hand else Decimal("0")
            if not total_on_hand:
                warnings_.append(
                    "MSPM-LIFO-ZERO-ON-HAND: no §471 costs on hand — the "
                    "combined absorption ratio was set to 0.")
        increment = profile.lifo_current_year_increment_471
        if increment > 0:
            add_to_inv = _q(combined_ratio * increment)
        elif increment < 0:
            add_to_inv = nonlifo_add
            warnings_.append(
                "LIFO-DECREMENT-NOT-IMPLEMENTED: a negative increment is a "
                "LIFO decrement year — the released-§263A computation "
                "(§1.263A-2(b)(3)(iii)(C)) needs per-layer data this engine "
                "does not carry; the NON-LIFO figure below is a placeholder, "
                "NOT the LIFO-correct answer.")
        else:
            add_to_inv = nonlifo_add
            warnings_.append(
                "MSPM-LIFO-INCREMENT-MISSING: inventory_method is LIFO but "
                "lifo_current_year_increment_471 was not supplied — the "
                "figure below is the NON-LIFO computation, not the combined-"
                "ratio × increment answer (§1.263A-2(c)(3)(iv)). Supply the "
                "increment.")
    else:
        add_to_inv = nonlifo_add

    return {
        "exempt": False,
        "method": "MSPM",
        "warnings": warnings_,
        # SSCM reporting + split
        "mixed_alloc_ratio": sscm["mixed_alloc_ratio"],
        "production_labor": sscm["production_labor"],
        "total_labor": sscm["total_labor"],
        "mixed_capitalized": mixed_cap,
        "mixed_deductible": mixed_ded,
        "mixed_split_method": split_method_used,
        "mixed_split_proportion_pre": pre_prop,
        "mixed_pre_production_share": _q(mixed_pre),
        "mixed_production_share": _q(mixed_prod),
        "mspm_90pct_applied": ninety_pct_applied,
        # pools / ratios / intermediates (Practice-Unit ratio-table shape)
        "pre_production_pool": _q(pre_pool),
        "production_pool": _q(prod_pool),
        "pre_production_471": profile.pre_production_471,
        "pre_production_ratio": pre_ratio,
        "pre_production_471_on_hand": pre_on_hand,
        "residual_pre_production_263A": _q(residual),
        "direct_materials_adjustment": _q(dm_adjustment),
        "production_471": profile.production_471,
        "production_ratio": production_ratio,
        "production_471_on_hand": prod_on_hand,
        "actual_pre_production_ratio": actual_pre,
        "actual_production_ratio": actual_prod,
        "har_applied": har_applied,
        "lifo_combined_ratio": combined_ratio,
        "additional_capitalized_to_inventory": add_to_inv,
        "adjusted_deductible_post": result["deductible_total"] + mixed_ded,
    }


def compute_lifo_decrement_release(layers: list, decrement: Decimal) -> dict:
    """§1.263A-2(b)(3)(iii)(C): on a LIFO decrement, the liquidated layers'
    prior §263A releases to COGS — released = layer's additional §263A ×
    (liquidated §471 ÷ layer's §471). Layers are consumed LIFO order (the
    LAST list entry first); each layer dict: {"layer_471": Decimal,
    "layer_additional_263a": Decimal} (+ any identifying keys, echoed back).

    Pure calculator (round 5c): the caller supplies per-layer data — no
    schedule carries it yet, which is why the MSPM/SRM engines still flag
    decrement years rather than calling this automatically."""
    decrement = Decimal(str(decrement))
    if decrement <= 0:
        raise ValueError(f"decrement must be positive, got {decrement}")
    warnings_: list = []
    released = Decimal("0")
    remaining = decrement
    detail = []
    for layer in reversed(layers):
        if remaining <= 0:
            break
        layer_471 = Decimal(str(layer["layer_471"]))
        layer_add = Decimal(str(layer["layer_additional_263a"]))
        if layer_471 <= 0:
            warnings_.append(
                f"LIFO-LAYER-INVALID: layer {layer!r} has non-positive §471 "
                f"costs — skipped; fix the layer schedule.")
            continue
        liquidated = min(remaining, layer_471)
        share = layer_add * liquidated / layer_471
        released += share
        remaining -= liquidated
        detail.append({**layer, "liquidated_471": liquidated,
                       "released_263a": _q(share)})
    if remaining > 0:
        warnings_.append(
            f"LIFO-DECREMENT-EXCEEDS-LAYERS: ${remaining:,.2f} of the "
            f"decrement exceeds the supplied layers' total §471 costs — "
            f"the layer schedule is incomplete; released §263A is "
            f"understated until it is.")
    return {"released_263a_to_cogs": _q(released), "layers": detail,
            "unabsorbed_decrement": _q(remaining), "warnings": warnings_}


def compute_srm(result: dict, profile) -> dict:
    """Simplified resale method (§1.263A-3(d)): purchasing ratio + storage &
    handling ratio (combined), applied to §471 costs remaining on hand."""
    warnings_ = []

    # Method-availability gate (§1.263A-3(a)(4)): SRM is available only to a
    # pure reseller, an (a)(4)(ii) de-minimis producer whose production is
    # INCIDENT TO RESALE, or an (a)(4)(iii) private-label producer. HARD
    # conflict — numbers still computed for visibility, warning leads.
    # (Red-team §16: the original gate ignored production_incident_to_resale
    # entirely and silently passed on an unknown activity level.)
    method_conflict = False
    if profile.produces and profile.private_label_goods:
        warnings_.append(
            "PRIVATE-LABEL-CONDITIONS: SRM availability rests on the "
            "(a)(4)(iii) private-label carve-out — confirm its three "
            "conditions hold (production under contract with an UNRELATED "
            "person; incident to resale; property sold to customers). "
            "Neither this engine nor the interview verifies them.")
    if profile.produces and not profile.private_label_goods:
        if profile.production_activity_level == "more_than_de_minimis":
            method_conflict = True
            warnings_.append(
                "SRM-METHOD-CONFLICT: §1.263A-3(a)(4)(i) bars the simplified resale "
                "method for a producer above the de minimis threshold (SPM/MSPM "
                "required) — these SRM figures are NOT a permissible filing position.")
        elif profile.production_activity_level == "de_minimis" \
                and not profile.production_incident_to_resale:
            method_conflict = True
            warnings_.append(
                "SRM-METHOD-CONFLICT: §1.263A-3(a)(4)(ii) permits SRM for a de-minimis "
                "producer only when production is INCIDENT TO RESALE of §1221(1) "
                "property — production_incident_to_resale is False, so SRM is not "
                "available. These figures are NOT a permissible filing position.")
        elif not profile.production_activity_level:
            warnings_.append(
                "SRM-PRODUCTION-LEVEL-UNKNOWN: the taxpayer produces but "
                "production_activity_level was never established (Gate 1 Q1.2) — the "
                "§1.263A-3(a)(4) availability gate CANNOT be evaluated. Resolve the "
                "de minimis determination before relying on these SRM figures.")
    elif not profile.produces \
            and profile.production_activity_level == "more_than_de_minimis":
        warnings_.append(
            "SRM-INPUTS-INCONSISTENT: produces=False but production_activity_level="
            "'more_than_de_minimis' — the availability gate cannot be evaluated on "
            "contradictory inputs. Fix the activity profile.")

    # SSCM is reported for visibility only — per the (d)(3)(i)(F) one-step
    # sub-split, the purchasing/storage-handling pools supplied on the
    # profile ALREADY include their allocable mixed-service share (see the
    # module docstring's input contract); do not add mixed_capitalized here.
    sscm = compute_sscm(result, profile)
    if sscm["ratio_warning"]:
        warnings_.append(sscm["ratio_warning"])
    # (production-cost election by a reseller now warns inside compute_sscm
    # itself — SSCM-PRODUCTION-COST-RESELLER — and falls back to labor.)

    for name, pool in (("purchasing_costs", profile.purchasing_costs),
                       ("storage_handling_costs", profile.storage_handling_costs)):
        if pool < 0:
            warnings_.append(
                f"SRM-NEGATIVE-POOL: {name} is negative (${pool:,.2f}). Negative "
                f"adjustments are permitted under the SRM with no gross-receipts "
                f"restriction (§1.263A-1(d)(3)(ii)(B)(3), unlike the SPM), but verify "
                f"none derive from cash/trade discounts or §162(c)/(e)/(f)/(g)-type "
                f"amounts (§1.263A-1(d)(3)(ii)(C)-(E)).")

    # Purchasing ratio: beginning inventory EXCLUDED from the denominator
    # ((d)(3)(i)(E)) — the denominator is the current year's purchases only.
    if profile.current_year_471_costs:
        purchasing_ratio = (profile.purchasing_costs
                            / profile.current_year_471_costs).quantize(SRM_RATIO_Q)
    else:
        purchasing_ratio = Decimal("0")
        warnings_.append(
            "SRM-ZERO-DENOMINATOR: current_year_471_costs (the current year's "
            "purchases, §1.263A-3(d)(3)(i)(D)(2)/(E)) is zero — the purchasing ratio "
            "was set to 0. Verify the purchases input.")

    # Storage & handling ratio: beginning inventory INCLUDED in the
    # denominator ((d)(3)(i)(D)(2)) — unless permissible variation
    # (d)(3)(iii)(A) is elected, which excludes it.
    sh_denom = profile.current_year_471_costs
    if not profile.srm_variation_a:
        sh_denom += profile.beginning_inventory_471
    if sh_denom:
        storage_handling_ratio = (profile.storage_handling_costs
                                  / sh_denom).quantize(SRM_RATIO_Q)
    else:
        storage_handling_ratio = Decimal("0")
        warnings_.append(
            "SRM-ZERO-DENOMINATOR: the storage & handling denominator "
            "(beginning_inventory_471 + current_year_471_costs"
            + (", beginning inventory excluded per the (d)(3)(iii)(A) variation"
               if profile.srm_variation_a else "")
            + ") is zero — the storage & handling ratio was set to 0. Verify the "
              "inventory and purchases inputs.")

    combined_ratio = purchasing_ratio + storage_handling_ratio
    # Variation (d)(3)(iii)(B): a LIFO taxpayer may multiply THE STORAGE &
    # HANDLING RATIO ONLY by total ending-inventory §471 costs — the
    # purchasing ratio still applies to the current-year increment. A single
    # combined × total shortcut overstated by purchasing-ratio × prior-year
    # layers (red-team §16, confirmed by counterexample).
    _ratio_sanity(warnings_, "(SRM purchasing)", purchasing_ratio)
    _ratio_sanity(warnings_, "(SRM storage & handling)", storage_handling_ratio)
    if profile.ending_inventory_471 < 0:
        warnings_.append(
            f"SRM-NEGATIVE-ENDING-INVENTORY: ending_inventory_471 is negative "
            f"(${profile.ending_inventory_471:,.2f}) — a §471-costs-on-hand "
            f"figure cannot be negative; the capitalized amount below is "
            f"meaningless until the input is fixed.")
    if profile.srm_variation_a and profile.srm_variation_b:
        warnings_.append(
            "SRM-VARIATION-A-PLUS-B: both (d)(3)(iii) variations elected — "
            "A's current-year-only S&H denominator is being applied to B's "
            "all-layer total multiplicand, an internally inconsistent "
            "combination the regulation text presents as independent options "
            "without addressing. SME must confirm before filing.")
    if profile.srm_variation_b:
        total_lifo = profile.ending_inventory_471_total_lifo
        if total_lifo <= 0:
            warnings_.append(
                "SRM-VARIATION-B-INPUT-MISSING: srm_variation_b elected but "
                "ending_inventory_471_total_lifo (TOTAL ending-inventory §471 at LIFO "
                "carrying value — the S&H ratio's multiplicand under (d)(3)(iii)(B)) "
                "was not supplied; computed WITHOUT the variation.")
            add_to_inv = _q(combined_ratio * profile.ending_inventory_471)
        else:
            add_to_inv = _q(purchasing_ratio * profile.ending_inventory_471
                            + storage_handling_ratio * total_lifo)
    else:
        add_to_inv = _q(combined_ratio * profile.ending_inventory_471)

    # (d)(3)(i)(F) input contract: the profile's purchasing/S&H pools must
    # ALREADY include their allocable mixed-service share (the one-step
    # sub-split is not computed here — no per-activity labor inputs exist).
    # The aggregate SSCM split therefore must NOT flow into this method's
    # capitalized/deductible outputs: publishing mixed_capitalized from the
    # aggregate ratio double-reported dollars the pools already carry and
    # zeroed real deductions out of adjusted_deductible_post (red-team §16).
    if result["mixed_total"]:
        warnings_.append(
            f"SRM-MSC-INPUT-CONTRACT: ${result['mixed_total']:,.0f} of mixed-service "
            f"costs are on the classified TB. Under the SRM their capitalizable share "
            f"belongs INSIDE the purchasing/storage-handling pool inputs per the "
            f"§1.263A-3(d)(3)(i)(F) one-step sub-split — confirm the pool figures "
            f"already include it; the full TB mixed total is otherwise reported as "
            f"currently deductible here (informational SSCM ratio: "
            f"{sscm['mixed_alloc_ratio']}).")

    return {
        "exempt": False,
        "method": "SRM",
        "method_conflict": method_conflict,
        "warnings": warnings_,
        # SSCM reported informationally; NOT applied to the TB mixed bucket —
        # the (F) shares live inside the pool inputs per the contract above.
        "mixed_alloc_ratio": sscm["mixed_alloc_ratio"],
        "production_labor": sscm["production_labor"],
        "total_labor": sscm["total_labor"],
        "mixed_capitalized": Decimal("0"),
        "mixed_deductible": result["mixed_total"],
        # ratios / intermediates (Practice-Unit ratio-table shape)
        "purchasing_costs": profile.purchasing_costs,
        "current_year_471_costs": profile.current_year_471_costs,
        "purchasing_ratio": purchasing_ratio,
        "storage_handling_costs": profile.storage_handling_costs,
        "storage_handling_denominator": sh_denom,
        "storage_handling_ratio": storage_handling_ratio,
        "combined_ratio": combined_ratio,
        "srm_variation_a": profile.srm_variation_a,
        "srm_variation_b": profile.srm_variation_b,
        "ending_inventory_471": profile.ending_inventory_471,
        "additional_capitalized_to_inventory": add_to_inv,
        "adjusted_deductible_post": result["deductible_total"] + result["mixed_total"],
    }
