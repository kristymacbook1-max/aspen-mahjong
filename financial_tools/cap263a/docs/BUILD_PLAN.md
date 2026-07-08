# Build Plan — Complete §263A Computation Tool (MSPM · SRM · SCA · §263A(f))

**Goal:** extend `cap263a` from a classifier + SPM inventory calc into a complete tool that accurately computes §263A inventory under **MSPM** and **SRM**, §263A for **self-constructed assets (SCA)** using reasonable allocation factors, and a full **§263A(f)** interest capitalization for designated property (in CIP and placed in service mid-year), including automatic designated-property identification.

**Today the tool accepts exactly one input — a trial balance — and that is the ceiling on what it can compute.** MSPM/SRM/SCA/§263A(f) are mathematically impossible from a trial balance alone; they need four more schedules. The complete tool takes **five inputs**:

| # | Input | Feeds | Status |
|---|---|---|---|
| 1 | **Trial balance** (by cost center/department) | Classification, SPM absorption ratio | ✅ Built |
| 2 | **Book-tax difference schedule** | Negative-§263A adjustments, M-1 reconciliation | ❌ Phase A |
| 3 | **Fixed asset schedule** | Per-asset basis/class-life/PIS date → SCA allocation target + §263A(f) designated-property ID | ❌ Phase A |
| 4 | **CIP (construction-in-progress) detail** | Cumulative production expenditure over time → the core §263A(f) APE input | ❌ Phase A |
| 5 | **Debt/interest schedule** | Traced vs. non-traced debt, principal, rates → the other half of §263A(f) | ❌ Phase A |

Phase A below builds the ingestion for inputs 2-5. Phases B/C/D are the calculation engines those inputs feed. **Nothing in Phase B/C/D can run until Phase A exists** — that ordering is not optional.

Synthesized from four design specs (grounded in Reg §§1.263A-1..-15 and IRS Practice Units COR-P-020/-021/-006/COR-C-023). **Status as of 2026-07-08 (see `docs/TAX_DECISIONS.md` §7a-§7e for the full history): the core formulas for SSCM, MSPM, SRM, and §263A(f) designated-property/avoided-cost mechanics have since been verified directly against primary regulation text** (with real bugs found and fixed along the way — see the phase sections below, each individually marked VERIFIED/CONFIRMED/CORRECTED with a date). What remains genuinely unverified: pinpoint citations for `§1.263(a)-1/-3`, `§1.471-11`, `§1.266-1`; the current-year §448(c) small-business-taxpayer dollar threshold; and any Practice Unit document-ID/revision-date detail not independently cross-checked. Do not treat this plan as a finished filing position regardless of verification status — it is a build spec, not tax advice — but do not read the blanket "unverified" framing that appeared in earlier drafts of this paragraph as still accurate; it is not.

## Where we start (already built)
- Classifier + 133-code taxonomy whose `Classification.treatment` dict already carries the exact sub-bucket codes the engines aggregate (`mspm`: `471`/`471-Pre`/`I`/`I-Pre`/`C`/`M`/`E`/`N`; `resale`: `471`/`P`/`S`/`I`/…). **No new classification work — the engines are aggregation + arithmetic over `analyze()` output.** Current classification accuracy: ~78% raw / ~84% high-confidence precision on a 250-line messy labeled set (see README.md; re-check with `python -m financial_tools.cap263a.validation.validate` before relying on a stale number).
- `analyze()` → waterfall buckets + `compute_unicap` (SPM only) + SSCM labor ratio (reused by MSPM/SRM; **SCA reuse is GATED, not unconditional — see Phase C's `sscm_eligible` check below, added 2026-07-08 after this line was found stale relative to that fix**).
- Reader with debit/credit netting; 5-tab report; tests; validation harness.
- **Guardrail infrastructure already built and REUSE, don't duplicate:** `EntityProfile.LARGE_PRODUCER_THRESHOLD` (>$50M rule), the SSCM-ratio [0,1] clamp + warning pattern (`analysis.py` `compute_unicap`, ~line 220), the absorption-ratio->1 warning, and the `bucket_warnings`/`unicap["warnings"]` list pattern that surfaces computation caveats on the Summary tab. MSPM/SRM/SCA/§263A(f) must plug into this same warnings list, not invent a parallel mechanism — that's how a >100%-style bug gets caught instead of silently shipped again.
- **SME decisions affecting Phase B, both RESOLVED 2026-07-08** (`docs/TAX_DECISIONS.md` §3 items 1 and 5): (1) `DM-*` direct-materials lines are correctly tagged `471-Pre` for the MSPM pre-production ratio — confirmed, no change needed, use as-is. (5) Additional-§263A-tier labor (purchasing/warehouse/buying) belongs in the SSCM labor ratio's numerator AND denominator, alongside §471 production labor — **already implemented in the shipped `compute_unicap`** (`analysis.py`, `CAPITALIZABLE_LABOR_TIERS`/`UNICAP_LABOR_TIERS`), so Phase B's MSPM/SRM engines inherit this correctly for free by reusing the same SSCM computation; no separate Phase B decision needed. Three items remain open and unresolved (§3 items 2-4: EX-BID successful-bids-only gating, §266 land-context auto-routing vs. confirmed election, repair-vs-improvement keyword scoping) — none of them block Phase A-D, since they're classifier-level, not engine-level, but resolve before relying on the classifier output those engines consume.

## SSCM — mixed service cost allocation (§1.263A-1(h)), verified against primary source 2026-07-08

The shipped `compute_unicap` already computes an SSCM ratio, but it implements only
**one of the options the regulation actually provides** — this section is grounded in
the full text of 26 CFR §1.263A-1 (retrieved directly, not from search-engine summary
or model recall — the two prior verification passes in this project both turned out
to have real errors, so this is the first section of this plan built from an actual
primary-source read).

**General formula (§1.263A-1(h)(3)):** `capitalizable mixed service costs = allocation
ratio × total mixed service costs`. Two ratio options exist, and which one a taxpayer
may use depends on producer/reseller status — **this is a real election, not a single
fixed formula**:

- **Labor-based allocation ratio (h)(4)** — available to everyone, and the *only*
  option available to resellers: `§263A labor costs / total labor costs`, where both
  numerator and denominator explicitly EXCLUDE labor costs already counted inside
  mixed service costs, and the denominator includes labor from every activity in the
  trade or business (production AND resale, if the taxpayer does both) — not just
  production. **This is what `compute_unicap` implements today.**
- **Production cost allocation ratio (h)(5)) — producers only, not available to
  resellers**: `§263A production costs / total costs`, where the denominator is
  dramatically broader than the labor ratio's — "total costs" means literally every
  cost of the trade or business excluding only mixed service costs, interest, and
  income-based taxes: all direct/indirect production costs *and* R&E, *and*
  marketing/selling/distribution costs that every other part of this tool treats as
  `Excluded`-tier and walls off. **Not implemented; see below.**
- **(h)(3)(ii), verified election rule:** *"A producer may elect one of two allocation
  ratios, the labor-based allocation ratio or the production cost allocation ratio. A
  reseller that satisfies the requirements for using the simplified resale method of
  §1.263A-3(d) (whether or not that method is elected) may elect the simplified
  service cost method, but must use a labor-based allocation ratio."* The choice is a
  **method of accounting**, applied consistently at the trade-or-business level.

**Build implication — this is buildable now, not gated on Phase A.** Unlike
MSPM/SRM/SCA/§263A(f), the production cost ratio needs no new schedule: "total costs"
is just every classified TB dollar except mixed-service and interest lines, which
`analyze()` already buckets. Recommended task (can slot in ahead of or alongside Phase
B): add `EntityProfile.sscm_ratio_method: Literal["labor", "production_cost"] =
"labor"`; when `"production_cost"`, gate on `not profile.acquires_for_resale` (raise
or warn — a reseller electing this is a regulation violation, not just a judgment
call) and compute the ratio from `is_total` minus mixed-service and interest buckets
in both numerator/denominator per the verified formula above.

**Other verified SSCM mechanics not yet reflected in the shipped code:**
- **Eligible property (h)(2):** SSCM applies to inventory, non-inventory held for
  sale, and certain self-constructed assets *produced on a routine and repetitive
  basis* (mass-produced, standardized/assembly-line, ≤3-year MACRS recovery period)
  — with an explicit taxpayer election to EXCLUDE self-constructed assets from SSCM
  entirely, in which case they fall back to the general (g)(4) method instead.
  Relevant to Phase C (SCA): most self-constructed *capital* assets (the kind Phase C
  targets — longer-lived, not mass-produced) likely do NOT qualify for SSCM's
  routine/repetitive carve-in, meaning SCA's mixed-cost allocation should default to
  the general method (below), not silently assume SSCM eligibility.
- **90% de minimis department election (g)(4)(ii), NOT SSCM-specific — a general
  mixed-service-cost rule):** if 90%+ of a mixed-service *department's* costs are
  deductible, taxpayer may elect not to allocate any of it. **CORRECTED 2026-07-08 — the "if 90%+
  are capitalizable, must allocate 100%" companion clause in a prior draft of this bullet is
  UNCONFIRMED and should NOT be relied on:** COR-C-023 (the IRS Concept Unit on self-constructed-asset
  costs) states only the one-sided version of this rule — "if 90% or more of a mixed service
  department's costs are deductible service costs, a taxpayer may elect not to allocate any
  portion... to property produced" — with no stated companion rule for the ≥90%-capitalizable case
  anywhere in the retrieved text. This exact overstated symmetric framing was flagged as a repeated
  error in the Phase C section too (now fixed there) and was missed here on the first pass; do not
  implement a symmetric ≥90%→100%/≤10%→0% shortcut under this citation without further primary-source
  verification. (Note: §1.263A-2(c)(3)(iii)(C)'s MSPM pre-production/production SSCM-split de minimis
  rule IS genuinely two-sided, but that is a different provision entirely — see the MSPM section
  below — and doesn't transfer to this general (g)(4)(ii) department-level election.) Under SSCM
  specifically, (h)(8) says an electing department drops out of the SSCM ratio pool entirely (its
  costs bypass the ratio, going straight to the qualifying activity). **Not implemented** — the
  current SSCM ratio treats all mixed-service costs uniformly with no per-department
  90% carve-out. Low priority (most cost-center-level mixed pools in a real TB won't
  cleanly split into single "departments" the way the regulation's factory-org-chart
  model assumes), but worth a TODO.
- **General (non-SSCM) alternative — (g)(4)(iii), if SSCM is not elected:** a
  **direct reallocation method** (mixed-service costs pushed straight to
  production/resale departments only, ignoring cross-mixed-service-department
  benefit) or a **step-allocation method** (cascading allocation, broadest-benefiting
  mixed-service department first, recognizing cross-mixed-service benefit). Full
  worked numerical examples exist in the regulation text. **Out of scope** — this
  tool implements SSCM only, consistent with its existing "combined
  producer+reseller method... deferred" scope note below; document, don't build,
  unless a future engagement specifically needs facts-and-circumstances allocation.
- **Independent election (h)(9):** SSCM is elected separately from SPM/MSPM/SRM —
  a taxpayer could pair SSCM with a facts-and-circumstances §471-cost method, or pair
  the general (g)(4) mixed-service method with MSPM. `EntityProfile.method` (SPM/
  MSPM/SRM) and the new `sscm_ratio_method` field above are correctly independent
  axes — don't couple them.
- **Multi-business apportionment (h)(7):** if mixed service costs span more than one
  trade or business, apportion by "any reasonable method" before applying SSCM. Out
  of scope for a single-entity-scoped tool; note only.

**RESOLVED 2026-07-08 (was "still unverified" in this section):** how MSPM splits the
SSCM-capitalized total between its pre-production and production absorption ratios
is now confirmed against the actual §1.263A-2(c)(3)(iii)(B) text — see the MSPM
section of Phase B below for the verified formula and the regulation's own worked
examples. The earlier WebSearch-only lead (direct-material proportion or
pre-production-labor proportion) turned out to be exactly right, word for word.

## Architecture of the extension

```
readers.py (new)      multi-sheet: TB + BTD + FixedAsset + CIP + Debt -> EngagementData
model.py (extend)     BookTaxDifference, FixedAsset, CIPProject(+CIPExpenditure),
                      DebtInstrument, SelfConstructedAsset, CostPool, DriverRow, Driver,
                      EngagementData, ValidationReport
analysis.py (extend)  EntityProfile fields; compute_unicap -> dispatcher:
                        compute_spm (existing) | compute_mspm | compute_srm
engines/ (new)        sca.py (compute_sca), interest.py (compute_263Af)
taxonomy/ (new data)  sca_drivers.yaml  (pool-category -> allowed/preferred driver matrix)
report.py (extend)    per-asset Asset Basis; real §263A(f) tab; MSPM/SRM ratio tables;
                      Data Quality tab; waterfall wiring
```

Contract that keeps the waterfall stable: **every inventory method returns `additional_capitalized_to_inventory` and `adjusted_deductible_post`** (the keys the Summary already consumes), so MSPM/SRM need no waterfall change.

---

## Phase A — Input data model & ingestion (everything else depends on this)

**None of `BookTaxDifference`, `FixedAsset`, `CIPProject`, `DebtInstrument`, or `EngagementData` exist yet** — `model.py` today has only `TBLine`/`Classification` (42 lines). This phase is net-new schema, not an "extension" in the sense of touching existing fields; there's nothing to conflict with, but there's also nothing to validate the design against except this plan. Build it before Phase B/C/D, since none of them can run without it.

New dataclasses (mirror `TBLine`: `Decimal` money, `Optional[date]`, `row_index`, `source_sheet`, coercion in `__post_init__`). Keys link the schedules:

```
TBLine.cc_num ─ cost-center ─ FixedAsset/CIP driver values (headcount, sq ft, labor$, machine hrs)
CIPProject.linked_asset_id ─FK→ FixedAsset.asset_id      (CIP rolls to asset on placed-in-service)
DebtInstrument.traced_project_id ─FK→ CIPProject.project_id   (traced debt → that project's APE)
```

- `read_engagement(path, *, btd_path=…, assets_path=…, cip_path=…, debt_path=…) -> EngagementData` — one multi-sheet workbook (sheet-title hints) or per-schedule files; reuse `reader.py`'s alias-header detection + `_to_decimal`; missing schedules degrade gracefully.
- Per-schedule alias tables + `_to_date`/`_to_bool` helpers; CIP accepts a dated ledger OR month-end balance columns.
- `ValidationReport`: required keys, numeric/date parsing, negative costs, enum sanity, **duplicate PKs**, and **cross-schedule FK resolution** (unresolved `linked_asset_id`/`traced_project_id` = ERROR; unknown cost-center = WARN). Non-structural issues accumulate (don't raise); `--force` overrides.
- **Data Quality tab** in the report listing issues with drill-down keys + a "Blocking issues: N" cell the Summary cross-references.

Backward compatible: existing `read_trial_balance`/`analyze`/`generate` keep working; `EngagementData` is additive.

---

## Phase B — Inventory: MSPM & SRM

Refactor `compute_unicap` into a dispatcher on `profile.method` (`"SPM"` keeps the existing body renamed `compute_spm`).

### MSPM (Reg §1.263A-2(c)) — two absorption ratios, VERIFIED 2026-07-08 against primary-source text

Full text of §1.263A-2 was directly retrieved and read (see `docs/TAX_DECISIONS.md` §7a/§7b).
The formula below is materially more precise than this plan's earlier version — it has two
mechanics that were previously missing entirely (residual pre-production costs, the direct
materials adjustment), both of which move real dollars and are not optional simplifications:

```
add'l_to_inv = (pre_production_ratio * pre_production_471_on_hand)
             + (production_ratio     * production_471_on_hand)

pre_production_ratio = pre_production_additional_263A / pre_production_471
  # pre_production_additional_263A = additional §263A costs that are pre-production costs
  #   (incurred before production begins, on property held/reasonably-likely-to-be-produced)
  #   + the pre-production SHARE of capitalizable mixed service costs (see SSCM split below)
  #   + additional §263A costs for property acquired for resale
  #   + additional §263A costs for contract-produced property treated as taxpayer's own
  # pre_production_471 = §471 direct material costs + §471 costs for property acquired for resale

pre_production_471_on_hand = pre_production_471 remaining in ending inventory,
  # EXCLUDING direct material costs that have already entered/completed production
  # (i.e. WIP/finished-goods direct materials are NOT pre-production for this ratio —
  # only unprocessed/raw materials still on hand count)

residual_pre_production_263A = pre_production_additional_263A
                              - (pre_production_ratio * pre_production_471_on_hand)
  # the pre-production additional cost NOT absorbed into pre-production ending inventory
  # rolls INTO the production ratio's numerator — do not drop it

direct_materials_adjustment = beginning_DM_not_yet_in_production
                             + DM_purchased_during_year
                             - ending_DM_not_yet_in_production
  # net direct materials that DID enter production during the year

production_ratio = (production_additional_263A + residual_pre_production_263A)
                  / (production_471 + direct_materials_adjustment)
  # production_471 = total §471 costs incurred during the year MINUS pre_production_471 incurred
production_471_on_hand = total §471 remaining on hand at year end MINUS pre_production_471_on_hand
```

**SSCM split between pre-production and production (§1.263A-2(c)(3)(iii)(B)) — the item
this plan previously flagged as unverified is now CONFIRMED, verbatim:** *"...the amount of
capitalizable mixed service costs... allocated to and included in pre-production additional
section 263A costs... is determined based on either of the following: The proportion of
direct material costs to total section 471 costs that a taxpayer incurs during its current
taxable year or the proportion of pre-production labor costs to total labor costs that a
taxpayer incurs during its current taxable year."* Both options are real, it's a taxpayer
choice (method of accounting), and — critically — the labor-based option requires excluding
mixed-service labor from BOTH the pre-production-labor numerator and the total-labor
denominator (mirrors the SSCM ratio's own exclusion rule). A **90% de minimis election**
also applies here specifically ((c)(3)(iii)(C)): if 90%+ of capitalizable mixed service costs
allocate to one bucket under either method, taxpayer may elect 100% to that bucket.
Implement as `EntityProfile.mspm_mixed_split_method: Literal["direct_material", "labor"]`.

- **Negatives + $50M rule (VERIFIED, §1.263A-1(d)(3)(ii)(B), see "Where we start"):** SPM excludes negative §263A when gross receipts exceed $50M (already implemented as `LARGE_PRODUCER_THRESHOLD` compared against the EXISTING `EntityProfile.avg_gross_receipts` field — reuse both, don't recreate or duplicate); **MSPM and SRM allow negatives with NO size restriction** (verified: (B)(2)/(B)(3) list MSPM/SRM with no dollar threshold, unlike (B)(1)'s SPM $50M cap). **Corrected 2026-07-08:** an earlier draft of this bullet both said the $50M comparison was "already implemented" AND instructed "add `avg_gross_receipts_prior3`" as a new field in the same sentence — self-contradictory. Resolution: `EntityProfile.avg_gross_receipts` already exists and already feeds the SPM $50M comparison; do NOT add a second, differently-named gross-receipts field for that comparison. Only add `include_negative_263a: bool` as new. If a true 3-year-rolling-average (as opposed to whatever single-year/period figure `avg_gross_receipts` currently represents) turns out to be needed for precision, that's a migration of the EXISTING field's computation, not an additional field living alongside it.
- **HAR election (VERIFIED, §1.263A-2(c)(4)):** requires 3+ consecutive prior years on MSPM with actual (not historic) ratios; frozen pre-production AND production historic ratios (or a combined ratio for LIFO) used for a 5-year qualifying period; recompute in year 6 (the "recomputation year") — if within ±0.5 percentage points of the historic ratio(s), extend 5 more years; if not, revert to actual ratios and rebuild a new 3-year test period. Fields: `har_election`, `har_preprod_ratio`, `har_production_ratio`, `har_qualifying_year_index`.
- **De minimis for producers with ≤$200,000 total indirect costs (VERIFIED, §1.263A-2(b)(3)(iv), applies to MSPM via (c)(3)(v)):** additional §263A costs deemed zero — a real, cheap early-out worth implementing regardless of Phase B's other complexity.
- **Canonical worked test — the regulation's OWN Example 1 (§1.263A-2(c)(3)(vi)(A), Taxpayer P), not a hand-built illustration: use this verbatim as the `test_mspm_srm.py` golden fixture, since every intermediate number is IRS-sourced, not derived.**
  Inputs: pre-production §471 incurred $2,500,000 ($1,900,000 direct material + $600,000 resale); production §471 incurred $7,500,000; pre-production additional §263A incurred $200,000; production additional §263A incurred $800,000; pre-production §471 on hand at year end $1,000,000 ($800,000 direct material + $200,000 resale); production §471 on hand at year end $2,000,000; beginning direct materials not yet in production $400,000, ending $800,000.
  - `pre_production_ratio = 200,000 / 2,500,000 = 8.00%`
  - `residual_pre_production_263A = 200,000 - (8.00% × 1,000,000) = 120,000`
  - `direct_materials_adjustment = 400,000 + 1,900,000 - 800,000 = 1,500,000`
  - `production_ratio = (800,000 + 120,000) / (7,500,000 + 1,500,000) = 920,000 / 9,000,000 = 10.22%`
  - `add'l_to_inv = (8.00% × 1,000,000) + (10.22% × 2,000,000) = 80,000 + 204,400 = **284,400**`
  - Total ending inventory = $3,000,000 §471 + $284,400 = **$3,284,400**.
- **SSCM-split worked tests, also verbatim from the regulation** ((c)(3)(vi) Examples 4-6): $200,000 capitalizable mixed service costs; direct-material method with $2,000,000 direct materials / $8,000,000 total §471 = 25% → **$50,000 pre-production / $150,000 production**; labor method with $1,000,000 pre-production labor / $10,000,000 total labor = 10% → **$20,000 pre-production / $180,000 production**; the labor-method case with a 90%+/production split → **100% to production** under the de minimis election.

### SRM (Reg §1.263A-3(d)) — combined ratio (two denominators), VERIFIED 2026-07-08 against primary-source text + cross-checked against IRS LB&I Practice Unit COR-P-021 "Examining a Reseller's IRC 263A Computation" (11/07/2024)

Full text of §1.263A-3 was directly retrieved and read (see `docs/TAX_DECISIONS.md` §7c). The formula below was
already substantially correct in this plan before verification — unlike MSPM, no missing mechanics were found —
but the **method-availability gate** below was missing entirely and is a real, build-blocking constraint:

```
# variable names match the EntityProfile fields declared below exactly (fixed 2026-07-08 — a prior
# draft used shorthand names here that didn't match the declared field names)
purchasing_ratio       = purchasing_costs / current_year_471_costs                            # beginning inv EXCLUDED
storage_handling_ratio = storage_handling_costs / (beginning_inventory_471 + current_year_471_costs) # beginning inv INCLUDED
combined = purchasing_ratio + storage_handling_ratio
add'l_to_inv = combined * ending_inventory_471
```
Both denominators re-checked term-for-term against Practice Unit COR-P-021 Step 6 (`docs/TAX_DECISIONS.md` §7e):
CONFIRMED exactly as written — the purchasing-ratio denominator omits beginning inventory, the storage-and-handling
denominator includes it. This is the single most safety-critical formula in this section — **the claim that it is
"the #1"/"most common" reseller audit error is this plan's own characterization, RE-FLAGGED 2026-07-08 as still
UNCONFIRMED: no sentence in the retrieved Practice Unit text ranks or names audit-error frequency.** The underlying
mechanic (beginning inventory belongs in the S&H denominator only) is confirmed; the superlative framing around it
is not, and should not be repeated as if it were a sourced fact. Treat any future change to the formula itself with
the same re-verification rigor regardless of how the error is ranked.
- Assert beginning inventory is in the S&H denominator only, never the purchasing denominator.
- **Goods valued below cost excluded from the base (§1.263A-3(d)(3)(i)(C)(2), missing entirely until now):**
  `ending_inventory_471` for purposes of this formula does NOT include inventory the taxpayer has written down or
  written off as obsolete/below cost. Without this exclusion, a taxpayer with write-downs would get an inflated
  base and an overstated capitalized amount.
- **1/3–2/3 purchasing-labor** rule (§1.263A-3(c)(3)(ii)(A)) — election; if not elected, reasonably allocate.
- **90/10 dual-function storage** rule — CORRECTED citation mapping 2026-07-08: the 90/10 deeming itself ("if 90%+
  of a facility's costs are on-site, the whole facility is deemed on-site" and its off-site mirror) is §1.263A-3(c)(5)(iii)(C).
  The **allocation ratio formula** (gross on-site sales of the facility ÷ total gross sales of the facility) used
  when the 90/10 deeming does NOT apply is a separate, more general rule at §1.263A-3(c)(5)(iii) (with the
  dual-function facility itself defined at (c)(5)(ii)(G)) — a prior draft attributed both under a single (iii)(C)
  citation, which overstates what that specific subpart governs. Also missing: "total gross sales" for this ratio
  **includes the value of items the taxpayer ships to its OTHER facilities**, not just external retail sales — a
  builder computing the denominator from external sales alone would understate it.
- **Method-availability gate (RE-VERIFIED 2026-07-08 against Practice Unit COR-P-021 Step 2 text directly, one
  framing corrected):**
  - de minimis production activity → **not required** to capitalize additional §263A costs at all (§1.263A-3(a)(5)).
  - **de minimis production activity, capitalization of resale+production costs is REQUIRED** (§1.263A-3(a)(4)(ii))
    → **may use SPM or SRM**. **Corrected 2026-07-08: a prior draft mischaracterized this as the taxpayer
    "choosing to capitalize... anyway" — the Practice Unit states this scenario as mandatory ("is required to
    capitalize resale and production costs"), not elective.** The Practice Unit lists this as a distinct scenario
    from the plain de-minimis/not-required bullet above without stating what distinguishes when each applies;
    `EntityProfile.production_activity_level` needs a fourth state (or an added field) to capture this distinction
    rather than collapsing it into "de_minimis," since the two de-minimis scenarios have different capitalization
    consequences even though production-activity level alone doesn't resolve which one applies — flag as an open
    modeling question, not yet resolved by any source retrieved so far.
  - **more than de minimis** production activity → **required** to capitalize resale+production costs, and **may
    use SPM but NOT SRM** ((a)(2)(i)) — this is the real trigger for `method_conflict`, not a soft "recommend"
    warning; SRM is simply unavailable to this taxpayer.
  - **private-label goods** exception: reseller with private-label production is required to capitalize resale+
    production costs but **may use SPM or SRM** ((a)(4)(iii)). **Note added 2026-07-08:** the framing that this
    "carves back out of the more-than-de-minimis bar" is this plan's own structural inference, not something the
    Practice Unit states outright (it lists private-label as a parallel, independent bullet) — treat as plausible
    but unconfirmed pending the primary §1.263A-3(a)(4)(iii) text itself.
  - Implement as `EntityProfile.production_activity_level: Literal["none", "de_minimis", "more_than_de_minimis"]`
    + `EntityProfile.private_label_goods: bool`; `compute_srm` raises `method_conflict=True` (hard, not a
    recommendation) when `production_activity_level == "more_than_de_minimis" and not private_label_goods`.
  - De minimis production activities test itself (sourced to the primary reg text per §7c, not to the Practice
    Unit — the Practice Unit text alone does not state this numeric test): <10% of gross receipts from produced
    property AND <10% of labor costs on production activities.
- **Allocable mixed service costs per activity (purchasing / storage-and-handling) — DOWNGRADED from "confirmed" to
  unconfirmed 2026-07-08:** a prior draft claimed Practice Unit COR-P-021 Step 5 confirms this uses the same
  SSCM labor-ratio structure as the resale-vs-other-activities split. On re-reading, Step 5 only describes the
  overall SSCM resale/non-resale split (`§263A labor costs / total labor costs`) — it does not describe any further
  sub-allocation of the resale-allocable MSC pool between purchasing and storage-and-handling specifically, which is
  what SRM's two separate numerators actually need. Treat this as **NOT addressed in the source text retrieved so
  far** — a plausible engineering assumption, not a confirmed rule — and re-verify against the primary §1.263A-3(c)
  text before relying on it for a filing position.
- Worked test: 60k/2.0M=0.03 + 105k/2.4M=0.043750 = 0.073750 × 500k = **36,875** (arithmetic independently
  re-verified 2026-07-08; this remains a hand-built illustration, not a regulation- or Practice-Unit-sourced
  example — no such worked SRM example was found in the source material retrieved so far).

### LIFO
Apply current-year ratio to the new layer on increments; on a **decrement**, release the liquidated layers' prior §263A to COGS (don't apply current ratio to liquidated qty). `inventory_method`, `lifo_layers` fields; fallback = single-layer approximation + REVIEW flag.

New `EntityProfile` fields (**consolidated 2026-07-08 — a prior version of this list omitted three fields proposed
earlier in this same phase, which is fixed here**): `beginning_inventory_471`, `ending_inventory_471_preprod/_prod`,
`ending_inventory_471` (undivided, for SRM — needed since SRM applies its combined ratio to the whole ending
§471 balance, unlike MSPM's pre-production/production split; not previously declared anywhere despite the SRM
formula referencing it), `current_year_471_costs`, `purchasing_costs`, `storage_handling_costs` (the latter three
also referenced by the SRM formula but previously undeclared), `production_gross_receipts`, `include_negative_263a`,
`inventory_method`, `lifo_layers`, HAR fields (`har_election`, `har_preprod_ratio`, `har_production_ratio`,
`har_qualifying_year_index`), `mspm_mixed_split_method`, `production_activity_level`, `private_label_goods` (these
last three were each proposed in the MSPM/SRM subsections above but missing from this consolidated list before).
**Scope note added 2026-07-08 (a red-team pass found this list was still incomplete as "the" EntityProfile field
reference, since it only ever claimed to consolidate Phase B's own fields): this list does NOT include
`EntityProfile.sscm_ratio_method` (proposed in the SSCM section, before Phase B) or
`EntityProfile.interest_afr_plus_3_election` / the `avg_gross_receipts_3yr_10m_test` helper (both proposed in Phase D)
— those remain correctly scoped to their own sections above and below, respectively; do not treat this Phase-B list
as a complete global `EntityProfile` field inventory.**
`compute_mspm`/`compute_srm` return supersets of the SPM shape (same `additional_capitalized_to_inventory` key). UNICAP tab renders the method-specific ratio tables in IRS Practice-Unit format (numerator/denominator/ratio/applied $).

---

## Phase C — Self-constructed assets (SCA)

Same classifier output, different allocation target: an **asset register**, not ending inventory. Three basis
buckets per asset: **A** §471 (CIP book cost) + **B** additional §263A (allocated indirect + capitalizable mixed) +
**C** §263A(f) interest (from Phase D). **Direct material/labor/contractor always in A — CONFIRMED 2026-07-08
against IRS Concept Unit COR-C-023, which states a taxpayer's §471 costs "MUST INCLUDE ALL direct material costs...
whether or not a taxpayer capitalizes these costs in its financial statements," with the identical mandatory
language for direct labor, explicitly extending to "contract employees and independent contractors."** The 11
non-capitalizable categories never enter B.
- **GAP found 2026-07-08, not yet addressed:** COR-C-023 also confirms OTHER indirect costs (engineering, design,
  utilities, insurance incurred to build the asset) can ALSO be §471/bucket-A costs, "provided some portion of the
  costs incurred is properly allocable to the property produced" AND the taxpayer's own financial statements
  capitalize them that way — the general §471 test is financial-statement-based, and material/labor/contractor are
  the ONLY costs pulled into bucket A unconditionally regardless of book treatment. Phase C's current bucket
  A/B split doesn't describe a mechanism for routing book-capitalized indirect costs (already sitting in CIP book
  cost, i.e. already in bucket A per this plan's own definition of A) versus re-adding them via bucket B's
  "allocated indirect" pool — a live double-count risk on real capital projects, where engineering/design costs are
  commonly booked directly to the CIP account. Needs a rule: if a cost is already reflected in the asset's own
  CIP/book-cost ledger, it must NOT also be re-allocated through bucket B's pool-based mechanism.

Allocation model: **pool → driver → per-asset share** across `{assets…, NON_PRODUCTION}`:
```
share(t) = driver_value(t) / Σ driver_value ; allocated(t) = round2(pool * share); penny-plug largest
```
- Drivers: headcount, square_footage, direct_labor_$/hrs, machine_hours, book_cost, direct_material_$; a pool declares one driver (or a weighted composite for facts-&-circumstances).
- **GAP found 2026-07-08: this driver-share formula implements only ONE of the three cost-allocation methods
  COR-C-023 describes as valid, independently-electable methods of accounting — Specific Identification (which is
  exactly this `share(t)=driver_value(t)/Σdriver_value` mechanic). Burden Rate (a PREDETERMINED rate set in advance,
  approximating actual indirect costs) and Standard Cost (PREESTABLISHED standard allowances, computed WITHOUT
  reference to actual costs incurred, with a required variance reconciliation) are both real elections common in
  actual manufacturing/construction books and are not addressed anywhere in this plan.** `docs/TAX_DECISIONS.md`
  §7c previously claimed this was checked and "matched" COR-C-023's three methods — **that claim was false and has
  been corrected, see `docs/TAX_DECISIONS.md` §7e.** Treat burden-rate/standard-cost support as an explicit,
  documented gap (a taxpayer using either method cannot be modeled by this tool as specified) rather than an
  implicit simplification — flag it in the tool's output when a taxpayer's book method doesn't match specific
  identification, rather than silently forcing specific identification on their data.
- **Mixed pools — SSCM eligibility gate added 2026-07-08, this was the most serious gap found in this section:**
  a prior draft said "SSCM split first (reuse `compute_unicap`'s ratio for consistency)" **unconditionally** — this
  directly contradicted the SSCM section's own eligible-property discussion above (§1.263A-1(h)(2)), which warns
  that most self-constructed CAPITAL assets (longer-lived, not mass-produced — exactly what Phase C targets) likely
  do NOT qualify for SSCM's "routine and repetitive" carve-in, and that SCA's mixed-cost allocation "should default
  to the general method, not silently assume SSCM eligibility." COR-C-023 independently confirms this scoping: it
  states its own general facts-and-circumstances guidance (direct reallocation / step-allocation for mixed service
  costs, per §1.263A-1(g)(4)(iii)) applies specifically to assets that do NOT qualify for the simplified methods.
  **Corrected mechanic: before reusing the SSCM ratio for a given asset's mixed-service pool, `compute_sca` must
  check the asset against the §1.263A-1(h)(2) eligibility test (produced on a routine and repetitive basis, ≤3-yr
  MACRS recovery period, substantially identical to inventory the taxpayer produces) via a new
  `SelfConstructedAsset.sscm_eligible: bool` (or equivalent derived check). If NOT eligible — the expected case for
  most Phase C targets per the SSCM section's own analysis — the tool must NOT silently apply the SSCM ratio.**
  Since the correct fallback (the general §1.263A-1(g)(4) direct-reallocation/step-allocation method) is itself
  declared out of scope in the SSCM section, the honest interim behavior is: apply the SSCM ratio ONLY when
  `sscm_eligible` is true; otherwise, warn/flag the asset (`SSCM-INELIGIBLE-NO-FALLBACK` or similar) and require a
  human override rather than silently computing a number using a method the regulation doesn't actually permit for
  that asset. This is a real scope decision, not a cosmetic fix — building the general method is future work; NOT
  silently mis-applying SSCM in the meantime is required now.
- **90% de minimis rule — CORRECTED 2026-07-08, the symmetric framing was unsupported.** A prior draft stated
  "90% de minimis (≥90%→100%, ≤10%→0%)" as if it were one symmetric two-sided rule applicable to per-asset driver
  shares. COR-C-023's actual text describes only a ONE-SIDED rule: "if 90% or more of a mixed service department's
  costs are DEDUCTIBLE service costs, a taxpayer MAY ELECT NOT TO ALLOCATE ANY PORTION... to property produced" —
  there is no stated companion "≥90% capitalizable → must/may allocate 100%" rule anywhere in the retrieved text.
  (Separately, MSPM's SSCM-split de minimis rule at §1.263A-2(c)(3)(iii)(C) IS genuinely two-sided, but that's a
  different provision governing a two-bucket pre-production/production split of an already-capitalized total — not
  a per-asset, N-way driver allocation, and doesn't transfer to this context.) Until the correct citation and scope
  for a symmetric per-asset version of this rule is confirmed against primary text, treat this bullet as: **only
  the one-sided ≥90%-deductible→elect-zero-allocation rule is confirmed; do not implement a symmetric ≤10%→0%/
  ≥90%→100% shortcut for per-asset driver shares without further primary-source verification.**
- **Officer compensation — reconciliation gap noted 2026-07-08, not yet resolved.** `docs/TAX_DECISIONS.md` §1
  item 1 (NO-OFFICER) re-tiers officer compensation to a blanket Mixed-Service/SSCM-ratio treatment. COR-C-023 lists
  "Officer's compensation" as a typical additional-§263A (bucket B) cost, consistent with that blanket M-tier
  routing as a DEFAULT — but COR-C-023 separately allows a purely management-related officer's salary to be
  ELECTED OUT entirely as a deductible service cost (a binary election, not a blended ratio), while COR-P-020's own
  audit guidance goes the other direction for a production-engaged owner/officer: "the taxpayer MUST capitalize the
  salary and benefits of this officer... because the officer's activities benefit the production" (full
  capitalization / specific identification, not dilution through a company-wide blended ratio). Phase C's SCA
  engine inherits the blanket M-tier/SSCM treatment without any asset-specific override for either fact pattern —
  on a project with a working owner/officer materially involved in construction, this can both under-capitalize
  (relative to COR-P-020's mandate) and over-capitalize (relative to COR-C-023's available elect-out) versus a
  facts-based treatment. Not resolved here; flagged as a known limitation for the SME to weigh in on before this
  is built, similar to the still-open §3 items already tracked in `docs/TAX_DECISIONS.md`.
- **Reasonableness guardrails** in `taxonomy/sca_drivers.yaml`: hard-block nonsensical pairings (HR by machine-hours; property tax by headcount), soft-warn plausible-but-not-preferred, degenerate-denominator guard (Σ=0 → allocate 0, flag), year-over-year driver-change flag (method change).
- `compute_sca(result, profile)` returns per-asset {book_cost, indirect_263a, mixed_263a, additional_263a, adjusted_basis_pre_interest, `ape_for_interest`, allocation audit trail} + conservation tie-checks. Emits `ape_by_asset` to Phase D (does not compute interest).
- Worked test: two assets, mixed HR pool 100k @ SSCM 0.60 split by production headcount (45k/15k) + building-dep 50k by sq ft (10k/40k) → each asset +55k additional §263A (arithmetic independently re-verified 2026-07-08 — conservation: 45k+10k=55k, 15k+40k=55k, total 110k = 60k HR + 50k building, correct); conservation = 0; guardrail test (HR-by-machine-hours blocks); degenerate test (Σ driver=0). **Note: this worked test assumes the asset is SSCM-eligible for illustration purposes — per the eligibility-gate fix above, a real asset must pass that check before this SSCM-then-driver-allocate sequence applies at all.**
- Rebuild the Asset Basis Schedule tab to **per-asset**: `original book basis + §263A indirect + §263A mixed + §263A(f) interest = adjusted basis` (live formula), regime rollup + tie-check retained.

---

## Phase D — §263A(f) interest capitalization (the hardest engine)

New `engines/interest.py`, `compute_263Af(result, profile)`, called after `compute_unicap`.

**1. Designated-property identification** (Reg §1.263A-8(b)), first match wins — CONFIRMED 2026-07-08 against
the primary text of 26 CFR §1.263A-8 itself (retrieved directly; see `docs/TAX_DECISIONS.md` §7e), superseding
the earlier Practice-Unit-only confirmation:
- real property → designated (Category 1);
- TPP with class life ≥ 20 yrs (Cat 2), **but ONLY IF the property is not §1221(l) property in the hands of the
  taxpayer or a related person** (§1.263A-8(b)(1)(ii)(A) — this carve-out was missing from the plan entirely; §1221(l)
  is the patent/invention-sale capital-gain provision, so this mostly matters for a taxpayer holding self-created
  patents/inventions as long-lived TPP) OR est. production period > 2 yrs (Cat 3) OR (> 1 yr AND cost > $1M) (Cat 4).
- de minimis screen: TPP with cost ≤ $1M **and** period ≤ 2 yrs → not designated. `NEEDS-CLASSLIFE` flag when only MACRS recovery period (not class life) is available.
- **Excluded property (§1.263A-8(b)(3), missing from the plan entirely until now):** designated property does NOT
  include (i) timber and evergreen trees more than 6 years old when severed from the roots, or (ii) property the
  taxpayer produces for use OTHER than in a trade or business or an activity conducted for profit (e.g., personal-use
  property). Implement as an early-out check alongside the de minimis screen, before the Category 1-4 tests.
- **Separate de minimis rule for ALL designated property, not just TPP** (§1.263A-8(b)(4), newly found in the
  Practice Unit — not previously in this plan): a production period of **90 days or fewer** AND total production
  expenditures **≤ $1,000,000 ÷ number of days in the production period** → excluded from designated property
  entirely (e.g., a 10-day production period caps out at $100,000 of expenditures). Excludes the adjusted basis of
  producing assets, land cost, and interest itself from the expenditure test. Implement as an early-out check
  before the Category 1-4 tests, not after — a property can fail this even if it would otherwise be Category 1.
- Scope: applies to designated property **still in CIP at year end** AND **placed in service during the year** — both computed; the only difference is where the production period ends.
- **Eligible-taxpayer AFR-plus-3 election** (§1.263A-9(e), CORRECTED 2026-07-08): a taxpayer with avg. annual gross
  receipts ≤ $10,000,000 for the prior 3 years (and every year since 1994 — the "$10,000,000 gross receipts test")
  may elect to use the highest Applicable Federal Rate + 3 percentage points as a substitute for the weighted
  average interest rate. **A prior draft of this bullet understated the election's scope: a taxpayer making this
  election may NOT trace debt at all** (§1.263A-9(e)(1) — "A taxpayer that makes this election may not trace
  debt") — electing AFR-plus-3 converts the ENTIRE unit's computation to a no-tracing approach; it is not a
  substitute rate plugged into the excess-expenditure step while a separate traced-debt calculation continues in
  parallel. It is also a **method of accounting**: the first-time election requires no Commissioner consent, but
  any later change to or from it (other than by ceasing to be an eligible taxpayer) does, and all such changes are
  made on a cut-off basis (no §481(a) adjustment). Implement as `EntityProfile.interest_afr_plus_3_election: bool`
  that, when set, ALSO forces `include_negative_263a`-style debt-tracing off for §263A(f) purposes — gated on a
  `avg_gross_receipts_3yr_10m_test` helper (renamed from an earlier draft's `avg_gross_receipts_10yr_test`, which
  mis-described a 3-year-average/$10M test as a "10-year" test; distinct from the $25M/$26M §448(c) small-business
  test already in `EntityProfile`).
- **Cessation-period election** (§1.263A-12(g), CORRECTED 2026-07-08): if production activities cease for ≥120
  consecutive days, taxpayer may elect to suspend interest capitalization starting with the first measurement
  period that BEGINS AFTER the cessation began, resuming (mandatorily) once activities resume. **A prior draft
  omitted the regulation's carve-out that materially narrows when this even applies**: production activities are
  NOT considered to have "ceased" — and the election is therefore unavailable — if the cessation is due to
  circumstances INHERENT in the production process: normal adverse weather, scheduled plant shutdowns, delays due
  to design/construction flaws, obtaining a permit or license, or settlement of groundfill. Also: interest on debt
  otherwise "traced" to the paused unit during the suspension must be capitalized as nontraced interest available
  to *other* units instead — it doesn't just disappear; and post-suspension APE for the resuming unit = the
  balance at suspension-start PLUS any non-interest costs incurred DURING the suspension (non-interest
  capitalization keeps running even while interest capitalization is paused). Lower priority than the AFR-plus-3
  election and de minimis rule above — flag as a Phase D stretch goal, not required for MVP, but implement the
  "inherent in the production process" gate FIRST if this is ever built, since without it the tool would let a
  taxpayer improperly suspend capitalization for an ordinary weather delay.
- **Related-person aggregation (§1.263A-8(b)(2)(ii), §1.263A-12(b), newly found — GAP, not yet spec'd):** activities
  and costs of a person RELATED to the taxpayer (§267(b)/§707(b)) must be taken into account both in applying the
  designated-property classification thresholds (Category 2/3/4 above) and in determining the taxpayer's own
  production period — regardless of whether the related person is performing a mere service or producing a
  component the related person must itself separately treat as designated property. `DebtInstrument.related_party`
  (already in the Phase D data contract below) covers related-party DEBT exclusions only; it does not yet cover
  this separate related-person COST/ACTIVITY aggregation requirement for classification and production-period
  purposes. Needs a `related_person_activities`/`related_person_costs` input on the CIP-detail schedule before this
  can be built correctly for any taxpayer using related-party contractors or affiliates.

**2. Production period** (Reg §1.263A-12): start = first physical activity (real) / 5%-of-total-cost (TPP, including
planning/design expenditures in the 5% test, determined without regard to whether physical activity has started).
**End — CORRECTED 2026-07-08, was understated as simply "ready for intended use (PIS)":** per §1.263A-12(d)(1), the
production period ends only when the unit is placed in service (or ready to be held for sale) **AND** all production
activities reasonably expected to be undertaken by/for the taxpayer or a related person are actually completed —
the regulation's own example (a homebuilder who paints/finishes interiors only once a buyer is found) explicitly
holds that the production period does NOT end at PIS/marketing-ready if further production activity is still
expected. Implement as: PIS date alone is NOT sufficient to stop interest capitalization; the CIP-detail schedule
needs an explicit `production_complete` flag/date distinct from `placed_in_service_date`, and capitalization runs
until the LATER of the two (mirroring `§1.263A-12(d)(3)`'s point that a single unit undergoing sequential internal
stages doesn't end its production period until ALL stages finish, even though *separate* units — e.g. two wings of
a building, each their own unit of property — end independently as each is completed). Mid-year PIS/completion →
prorate the sub-period by active days.

**3. Avoided-cost method (Reg §1.263A-9) — CORRECTED 2026-07-08, primary text re-derived; the plan's earlier
formula and worked example were materially wrong, not just imprecise.** A multi-agent audit against the actual
regulation text (`docs/TAX_DECISIONS.md` §7e) found that averaging each period's opening/closing APE **before**
comparing it against the traced-debt principal does not match how §1.263A-9(b)/(c) and its own worked Example 3
actually compute the amounts: the regulation evaluates traced debt and excess expenditures **at each measurement
DATE** (a point-in-time snapshot — the measurement dates themselves, e.g. quarter-ends, not a period average), and
only afterward averages those snapshot-level results across the computation period. The two approaches diverge
whenever a traced loan's principal sits between a period's opening and closing APE, which is exactly the shape of
this plan's own worked example (see below) — the old formula understated the correct answer by about 16%.

Corrected mechanics, per unit, evaluated at each measurement date *d* within a computation period (commonly the
full taxable year with quarterly measurement dates — a taxpayer may instead elect shorter computation periods per
§1.263A-9(f)(1), in which case this same snapshot-then-average logic is redone independently per period):
```
APE_d          = accumulated production expenditures AS OF measurement date d (a snapshot, NOT an average of two
                 dates) — includes prior §263(a)+§263A costs AND prior capitalized interest (COMPOUNDING, mandatory,
                 per §1.263A-11(b)(1): interest capitalized in a prior computation period is deemed capitalized on
                 the day immediately following that period's end, so it's part of APE for every later snapshot)
traced_debt_d  = eligible debt actually allocated (under the §1.163-8T tracing rules) to this unit's APE as of date d
                 — this is a TRACING determination, not `min(APE_d, principal)`; in the common case where a loan's
                 full proceeds funded this unit and APE_d exceeds the loan's principal at every date, traced_debt_d
                 equals the full principal at every date, but tracing can also produce a SMALLER traced amount at an
                 EARLIER date than a later one (see the regulation's own Property D/E example, §1.263A-9(c)(5)(i)(B))
excess_d       = max(0, APE_d - traced_debt_d)

# Traced debt amount for the computation period = actual $ interest incurred on the traced debt during each
# measurement PERIOD (the interval ending on measurement date d) — NOT an annualized-rate × day-fraction estimate:
traced_interest_period = Σ over each measurement period (interval ending on date d) of
                            (actual interest incurred, during that period, on the debt identified as traced_debt_d
                             for the measurement date ending that period)

# Excess expenditure amount for the computation period — ONE figure for the whole period, from averaging the
# point-in-time snapshots, not a per-sub-period sum of separately-scaled amounts:
average_excess_expenditures = (Σ over all measurement dates d in the period of excess_d) / (number of measurement dates)
WAIR_nontraced = (Σ interest incurred on nontraced debt during the period)
                 / [(Σ over all measurement dates d of nontraced debt outstanding at d) / (number of measurement dates)]
excess_expenditure_amount = average_excess_expenditures * WAIR_nontraced

unit_capitalized = traced_interest_period + excess_expenditure_amount

# Cap — CORRECTED: §1.263A-9(c)(1) applies the pro-rata cap ONLY to the excess-expenditure (avoided-cost) pool
# across all of a taxpayer's units, NOT to the combined traced+avoided total. Traced-debt interest is always fully
# capitalized based on actual interest incurred on the traced debt; it is never part of this proration.
if Σ (excess_expenditure_amount across all units) > total_interest_available_for_capitalization:
    # total_interest_available = nontraced-debt interest + certain below-AFR related-party borrowings (§1.263A-9(a)(4)(iii))
    #   + partnership guaranteed payments for use of capital (§1.263A-9(c)(2)(iii), §707(c)) — see sourcing order below
    each unit's excess_expenditure_amount *= total_interest_available_for_capitalization
                                              / Σ (excess_expenditure_amount across all units)
    flag PRORATED
total = Σ units (traced_interest_period + each unit's possibly-prorated excess_expenditure_amount)
```
- **Excess-expenditure interest sourcing order (§1.263A-9(c)(2)), missing entirely from the prior draft:** interest
  available to satisfy the excess expenditure amount is drawn, in this order, and only up to the total excess
  expenditure amount for all units: (1) interest incurred on nontraced debt; (2) interest incurred on certain
  below-AFR related-party borrowings (§1.263A-9(a)(4)(iii)); (3) in the case of a partnership, guaranteed payments
  for the use of capital under §707(c) that would otherwise be deductible. **Item (3) was previously mis-cited in
  this plan's "Deferred/out of scope" list as "§1.263A-15" (that section is just effective dates/anti-abuse) — the
  correct citation is §1.263A-9(c)(2)(iii), inside the very avoided-cost-method section this plan claims to have
  fully verified.** This is not truly out of scope for any partnership-structured project; move it into Phase D's
  build list (lower priority than the core snapshot mechanics above) rather than the deferred list.
- **Eligible-debt exclusions (§1.263A-9(a)(4)), missing entirely from the prior draft:** not all outstanding debt
  qualifies for tracing/WAIR purposes. Excluded from "eligible debt": debt with interest disallowed under
  §1.163-8T(m)(7)(ii); non-interest-bearing debt (accounts payable etc.) unless it is itself traced debt; debt from
  a related person at a below-AFR rate (at issuance); personal interest (§163(h)(2)); qualified residence interest
  (§163(h)(3)); debt of a tax-exempt organization outside an unrelated trade or business; reserves/deferred-tax
  liabilities not treated as debt for tax purposes; income tax liabilities/§453A deferred tax/§460(b) look-back
  hypothetical liabilities; and certain sale-leaseback purchase-money obligations. `DebtInstrument` needs an
  `is_eligible_debt` derivation (or the individual flags to derive it) — not just `related_party`, `traced_to`.
- **Ordering against other Code sections (§1.263A-9(g)(1)), missing entirely from the prior draft:** §263A(f)
  capitalization must be applied BEFORE §163(d) (investment interest), §163(j) (business interest limitation), §266
  (carrying-charge election), §469 (passive loss limitation), and §861 (interest sourcing) — capitalized interest is
  removed from consideration under those sections entirely. Within the excess-expenditure step specifically, interest
  that is NEITHER investment/business/passive interest must be capitalized BEFORE interest that IS one of those
  types. Conversely, certain "deferral provisions" (§163(e)(3), §267, §446, §461) are applied BEFORE §263A(f) — the
  opposite ordering — meaning interest deferred under one of those sections is capitalized only in the year it would
  otherwise become deductible. This interacts materially with §163(j) in particular for any leveraged real-estate or
  production project; not addressed anywhere in this plan's data model today. Flag as a required build item before
  Phase D can be relied on for a taxpayer subject to the §163(j) limitation, not a stretch goal.
- Data contract: FixedAsset (type, class_life, cost, PIS date), CIP detail (cumulative expenditure PER MEASUREMENT
  DATE — snapshots, not just open/close pairs — production start, `production_complete` flag/date per the corrected
  production-period-end rule above, total est. cost, `is_improvement`, mid-production-purchase price per §1.263A-11(f)
  — this field was previously described only in prose below and never actually added to this data contract list,
  which is the fix), Debt (principal, rate, interest_incurred, `traced_to`, `related_party`, plus enough detail to
  derive `is_eligible_debt` per the exclusions above). Legacy scalar APE×rate stub retained as fallback when
  schedules are empty.
- **Worked test — CORRECTED, was materially wrong** (real-property CIP, 4 equal quarters, traced loan $3,000,000 @
  6% annual outstanding the full year, nontraced-pool WAIR 7.142857% (1/14) annual, APE at each quarter-end
  measurement date ramping from $3,500,000 to $8,000,000 — quarterly measurement dates within a single annual
  computation period, so the average/WAIR below are computed ONCE for the year, not per quarter):

  | Measurement date | APE (snapshot) | traced_debt (fully allocated every date, since APE > $3M throughout) | excess |
  |---|---|---|---|
  | Q1 end | 3,500,000 | 3,000,000 | 500,000 |
  | Q2 end | 5,000,000 | 3,000,000 | 2,000,000 |
  | Q3 end | 6,500,000 | 3,000,000 | 3,500,000 |
  | Q4 end | 8,000,000 | 3,000,000 | 5,000,000 |

  Traced debt amount = actual interest incurred on the fully-traced $3,000,000 loan for the full year = $3,000,000 ×
  6% = **$180,000.00**. Average excess expenditures = (500,000+2,000,000+3,500,000+5,000,000)/4 = **$2,750,000**.
  Excess expenditure amount = $2,750,000 × (1/14) = **$196,428.57**. **Total capitalized = $180,000.00 +
  $196,428.57 = $376,428.57** (verified with exact `Decimal` arithmetic — recomputed independently and confirmed;
  see `docs/TAX_DECISIONS.md` §7e). This replaces the prior draft's $323,571.43 figure (traced $176,250.00 + avoided
  $147,321.43), which used the wrong open/close-averaging methodology and must NOT be used as the `test_interest.py`
  golden fixture. This table is the corrected literal fixture for `test_interest.py`.
- **"T.D. 10034" is REAL — RESOLVED 2026-07-08, primary text retrieved and read (26 CFR 1.263A-8/-11/-12/-15
  as currently in force).** The earlier "suspected fabrication" flag from the citation-accuracy audit was itself
  wrong — a case of an under-verified guess turning out to be model recall of a genuine, recently-added citation.
  T.D. 10034, 90 FR 47582/47583, Oct. 2, 2025, amended §1.263A-8(d)(3), §1.263A-11(e)-(f), and consequentially
  §1.263A-15(a)(6), **effective for tax years beginning after October 2, 2025** (a change in method of accounting
  under §§446/481 — not a self-executing cutover). Confirmed content, replacing the earlier speculative
  description:
  - §1.263A-8(d)(3): any improvement to real or tangible personal property (under §1.263(a)-3 / §1.263A-2(a)(2)(ii))
    constitutes production of designated property, UNLESS the de minimis exception (§1.263A-8(b)(4)) applies or
    the activity is a repair/maintenance item under §1.162-4(a) — this confirms `is_improvement` needs its own
    de-minimis and repair-carve-out checks, not just a flag.
  - §1.263A-11(e) (new): APE for an improvement is limited to costs required to be capitalized **with respect to
    the improvement itself** — the regulation's own words are "consists of all direct and indirect costs required
    to be capitalized with respect to the improvement." **Hedge restored 2026-07-08 (this bullet had overstated its
    own certainty): the text is an affirmative SCOPING statement, not an explicit exclusion clause — it does not
    itself say "excludes the pre-existing property's basis." The likely practical effect is the same (the
    pre-existing basis is simply never counted as an improvement cost, so it's excluded by omission), but calling
    this "CONFIRMED, not speculative" overstated what the cited text literally supports; it is a reasonable
    inference from the text, not a directly confirmed exclusion rule.** Implement as: when `is_improvement`, APE is
    scoped to costs capitalized with respect to the improvement itself (which in practice excludes the pre-existing
    property's basis/APE, but treat that practical effect as inferred, not textually guaranteed, until a primary-text
    example squarely on point is found).
  - §1.263A-11(f) (new, NOT previously in this plan at all): a **mid-production purchase** rule — if a taxpayer
    buys a unit of property for further production before placing it in service, APE includes the **full purchase
    price** of the purchased unit PLUS all additional direct/indirect production costs the taxpayer incurs
    afterward. Real new mechanic: add an `EntityProfile`/CIP-detail field for "acquired mid-production, purchase
    price" so the APE calc doesn't understate basis for assets bought partway through construction by someone
    else.
  - The "associated property rule eliminated" half of the old guess is **not confirmed by this text** — no
    "associated property" rule appears anywhere in §§1.263A-8 through -15 as retrieved. Drop that claim; it may
    have been a hallucinated elaboration on the real T.D. number, or it may live in text not yet retrieved (e.g.
    a different subsection). Flags `IMPROVEMENT-NARROWED-2025` (confirmed), `MID-PRODUCTION-PURCHASE` (new).
  - Lower-priority, noted but not yet spec'd: §1.263A-9(g)(7) 15-day repayment election (treat debt repaid within
    15 days before a quarterly measurement date as still outstanding on that date — prevents WAIR "mismatch"
    inflation) and §1.263A-9(g)(3) simplified inventory method (an alternative to per-unit avoided-cost tracking
    for inventory-only designated property, using inventory-age segmentation and a compounded interest factor per
    segment — a materially different algorithm from the per-unit method already spec'd above; treat as a
    stretch-goal alternative path, not a required build item).
- Outputs: a real **§263A(f) Interest tab** (per-unit 7-step APE worksheet in Practice-Unit format), the interest column of the Asset Basis Schedule, and the Summary `§263A(f) Interest` bucket (route *capitalized* interest to the bucket; incurred − capitalized stays deductible — document in the tie-check to avoid double count).

---

## Sequencing & why

1. **Phase A first** — the three schedules are the inputs every engine consumes; nothing numeric is possible without them.
2. **Phase B (MSPM/SRM)** — pure arithmetic over existing classifier output; lowest risk, immediate value, no new schedules beyond inventory balances.
3. **Phase C (SCA)** — needs FixedAsset/CIP + driver tables (Phase A) and **conditionally** reuses SSCM (gated on
   the per-asset `sscm_eligible` check — most Phase C targets are expected to fail it, per the SSCM section's own
   analysis; this line previously said "reuses SSCM" unconditionally, which was stale relative to that fix);
   produces `ape_by_asset`.
4. **Phase D (§263A(f))** — needs FixedAsset/CIP/Debt (Phase A) and SCA's APE hand-off (Phase C); hardest, so last.

Each phase ships standalone value and keeps the waterfall tie-out.

## Files
- **New:** `readers.py`, `engines/sca.py`, `engines/interest.py`, `taxonomy/sca_drivers.yaml`, tests `test_readers.py`/`test_mspm_srm.py`/`test_sca.py`/`test_interest.py`.
- **Extend:** `model.py` (schedule + SCA dataclasses, `EngagementData`, `ValidationReport`), `analysis.py` (EntityProfile fields, dispatcher, `compute_mspm/srm/sca`, call `compute_263Af`), `report.py` (per-asset Asset Basis, §263A(f) tab, MSPM/SRM tables, Data Quality tab, waterfall wiring).

## Verification
- Unit tests from each worked example — **figures CORRECTED 2026-07-08 to match the actual worked-example sections above** (a prior draft of this checklist had gone stale relative to formula corrections made earlier in the same document): MSPM **284,400** additional §263A / **$3,284,400** total ending inventory (the regulation's own Example 1 — NOT the superseded 143,000 hand-built figure); SRM 36,875; SCA 55k/asset + conservation + guardrail/degenerate; §263A(f) **376,428.57** = traced **180,000.00** + avoided/excess-expenditure **196,428.57** (NOT the superseded 323,571.43 figure, which used an incorrect open/close-averaging methodology — see the Phase D section above and `docs/TAX_DECISIONS.md` §7e). Also confirm MSPM's rounding convention explicitly before coding the test: the regulation's own Example 1 arrives at exactly $284,400 only if the 10.22% production ratio is rounded to two decimal places BEFORE multiplying by ending inventory (unrounded, 920,000/9,000,000 × $2,000,000 = $204,444.44, giving $284,444.44 total) — MSPM should round the ratio to match the IRS's own presentation, which is a DIFFERENT convention from Phase D's "exact Decimal arithmetic, not rounded intermediates" rule; document this per-engine rather than assuming one global rounding rule applies everywhere.
- FK/validation tests (unresolved links flagged; debit/credit netting already covered).
- Method-conflict test (SRM chosen but production > de minimis).
- End-to-end: `read_engagement` on a multi-sheet sample → all engines → workbook with zero formula errors, every tab ties, and `formulas`-library evaluation of the live cells (LibreOffice is blocked in this sandbox).
- Extend `validation/validate.py` to report per-engine tie-outs alongside classification accuracy.

## Effort & risk
Four phases, each comparable to the classifier rebuild. Highest risk: §263A(f) — **not because T.D. 10034 is unverified (it's confirmed real, see Phase D above and `docs/TAX_DECISIONS.md` §7d/§7e) but because the avoided-cost method's core snapshot-vs-average mechanics, the eligible-debt exclusions, the excess-expenditure interest-sourcing order, and the ordering rules against §163(j)/§266/§469/etc. are all newly corrected/added as of 2026-07-08 and have NOT yet been implemented or tested against real data** — treat the corrected Phase D formula as unvalidated-by-implementation even though it is now validated-by-primary-text. Also high-risk: data ingestion quality (real TBs/asset registers are messy — the Data Quality tab is the mitigation). Classification accuracy (~78% raw / ~84% high-confidence precision, ~35% review queue on messy data — re-verify against a live `validate.py` run, this number moves as the taxonomy is hardened) means asset/CIP inputs should be reviewed, not blindly trusted — the review-queue + Data Quality tab surface this. Remaining unverified-citation risk (narrower than before, see the opening disclaimer above): `§1.263(a)-1/-3`, `§1.471-11`, `§1.266-1`, and the current §448(c) dollar threshold.

## Deferred / out of scope
Combined producer+reseller method; farming (§1.263A-4, see `docs/TAX_DECISIONS.md` §7d); change in accounting method for §263A costs / §481(a) beginning-inventory revaluation (§1.263A-7, see `docs/TAX_DECISIONS.md` §7d — this is a distinct, later-phase deliverable, not touched by Phase A-D above); the general (g)(4)(iii) non-SSCM mixed-service-cost alternative (direct reallocation / step-allocation methods — see the SSCM section above); multi-business mixed-service-cost apportionment (§1.263A-1(h)(7) — see the SSCM section above); live Form 3115 DCN mapping to the current Rev. Proc.; the EY-platform modules (§168(n), §163(j) as a standalone module — though §163(j)'s INTERACTION with §263A(f) ordering is now in-scope for Phase D, see above — §45X/§48D, cost seg).
**Corrected 2026-07-08:** partnership guaranteed-payment interest sourcing (§1.263A-9(c)(2)(iii)) was previously
listed here as "interest on flow-through entities (§1.263A-15)" — that citation was wrong (§1.263A-15 is effective
dates/anti-abuse, not flow-through interest) and the underlying mechanic is not actually out of scope; it has been
moved into Phase D's build list above as part of the excess-expenditure interest-sourcing order.
