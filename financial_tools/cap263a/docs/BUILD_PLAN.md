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

Synthesized from four design specs (grounded in Reg §§1.263A-1..-15 and IRS Practice Units COR-P-020/-021/-006/COR-C-023 — **these citations, and every citation in this plan, are unverified against a primary source; see `docs/TAX_DECISIONS.md` §7 before treating any of them as a filing position**). Each engine has a worked numeric example destined to become a unit test.

## Where we start (already built)
- Classifier + 133-code taxonomy whose `Classification.treatment` dict already carries the exact sub-bucket codes the engines aggregate (`mspm`: `471`/`471-Pre`/`I`/`I-Pre`/`C`/`M`/`E`/`N`; `resale`: `471`/`P`/`S`/`I`/…). **No new classification work — the engines are aggregation + arithmetic over `analyze()` output.** Current classification accuracy: ~78% raw / ~84% high-confidence precision on a 250-line messy labeled set (see README.md; re-check with `python -m financial_tools.cap263a.validation.validate` before relying on a stale number).
- `analyze()` → waterfall buckets + `compute_unicap` (SPM only) + SSCM labor ratio (reused by MSPM/SRM/SCA).
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
  deductible, taxpayer may elect not to allocate any of it; if 90%+ are
  capitalizable, must allocate 100%. Under SSCM specifically, (h)(8) says an
  electing department drops out of the SSCM ratio pool entirely (its costs bypass the
  ratio, going straight to the qualifying activity). **Not implemented** — the
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

- **Negatives + $50M rule (VERIFIED, §1.263A-1(d)(3)(ii)(B), see "Where we start"):** SPM excludes negative §263A when `avg_gross_receipts_prior3 > $50M` (already implemented as `LARGE_PRODUCER_THRESHOLD` + a warning — reuse it, don't recreate); **MSPM and SRM allow negatives with NO size restriction** (verified: (B)(2)/(B)(3) list MSPM/SRM with no dollar threshold, unlike (B)(1)'s SPM $50M cap). Add `avg_gross_receipts_prior3`, `include_negative_263a` fields to `EntityProfile`.
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
purchasing_ratio       = purchasing_costs / current_year_471_costs               # beginning inv EXCLUDED
storage_handling_ratio = storage_handling / (beginning_inv_471 + current_year_471)# beginning inv INCLUDED
combined = purchasing_ratio + storage_handling_ratio
add'l_to_inv = combined * ending_inventory_471
```
- The #1 reseller audit error is the S&H denominator — assert beginning inventory is in S&H denom only.
- **1/3–2/3 purchasing-labor** rule (§1.263A-3(c)(3)(ii)(A)) — election; if not elected, reasonably allocate.
- **90/10 dual-function storage** rule (§1.263A-3(c)(5)(iii)(C)) — on-site/off-site facility deeming, ratio =
  gross on-site sales / total gross sales of the facility.
- **Method-availability gate (VERIFIED via Practice Unit COR-P-021, citing §1.263A-3(a)(2)(i)/(a)(4)(ii)/(a)(4)(iii)):
  this is NOT just a "de minimis production" flag — it determines which method is even legal to use:**
  - de minimis production activity → **not required** to capitalize additional §263A costs at all (§1.263A-3(a)(5)).
  - de minimis production activity, but taxpayer chooses to capitalize resale+production costs anyway → **may use
    SPM or SRM** ((a)(4)(ii)).
  - **more than de minimis** production activity → **required** to capitalize resale+production costs, and **may
    use SPM but NOT SRM** ((a)(2)(i)) — this is the real trigger for `method_conflict`, not a soft "recommend"
    warning; SRM is simply unavailable to this taxpayer.
  - **private-label goods** exception: reseller with private-label production is required to capitalize resale+
    production costs but **may use SPM or SRM** ((a)(4)(iii)) — carves back out of the "more than de minimis" bar.
  - Implement as `EntityProfile.production_activity_level: Literal["none", "de_minimis", "more_than_de_minimis"]`
    + `EntityProfile.private_label_goods: bool`; `compute_srm` raises `method_conflict=True` (hard, not a
    recommendation) when `production_activity_level == "more_than_de_minimis" and not private_label_goods`.
  - De minimis production activities test itself (confirmed same-day in §7c from the primary reg text): <10% of
    gross receipts from produced property AND <10% of labor costs on production activities.
- Allocable mixed service costs per activity (purchasing / storage-and-handling), confirmed via Practice Unit
  COR-P-021 Step 5 to use the **same SSCM labor-ratio structure** already implemented for the resale-vs-other-activities
  split — `labor costs allocable to the activity / total labor costs`, both nets of MSC labor — reuse, don't
  reimplement.
- Worked test: 60k/2.0M=0.03 + 105k/2.4M=0.043750 = 0.073750 × 500k = **36,875**.

### LIFO
Apply current-year ratio to the new layer on increments; on a **decrement**, release the liquidated layers' prior §263A to COGS (don't apply current ratio to liquidated qty). `inventory_method`, `lifo_layers` fields; fallback = single-layer approximation + REVIEW flag.

New `EntityProfile` fields: `beginning_inventory_471`, `ending_inventory_471_preprod/_prod`, `avg_gross_receipts_prior3`, `production_gross_receipts`, `include_negative_263a`, `inventory_method`, `lifo_layers`, HAR fields. `compute_mspm`/`compute_srm` return supersets of the SPM shape (same `additional_capitalized_to_inventory` key). UNICAP tab renders the method-specific ratio tables in IRS Practice-Unit format (numerator/denominator/ratio/applied $).

---

## Phase C — Self-constructed assets (SCA)

Same classifier output, different allocation target: an **asset register**, not ending inventory. Three basis buckets per asset: **A** §471 (CIP book cost) + **B** additional §263A (allocated indirect + SSCM-capitalized mixed) + **C** §263A(f) interest (from Phase D). Direct material/labor/contractor always in A; the 11 non-capitalizable categories never enter B.

Allocation model: **pool → driver → per-asset share** across `{assets…, NON_PRODUCTION}`:
```
share(t) = driver_value(t) / Σ driver_value ; allocated(t) = round2(pool * share); penny-plug largest
```
- Drivers: headcount, square_footage, direct_labor_$/hrs, machine_hours, book_cost, direct_material_$; a pool declares one driver (or a weighted composite for facts-&-circumstances).
- Mixed pools: SSCM split first (reuse `compute_unicap`'s ratio for consistency), then driver-allocate the capitalizable share; **90% de minimis** (≥90%→100%, ≤10%→0%).
- **Reasonableness guardrails** in `taxonomy/sca_drivers.yaml`: hard-block nonsensical pairings (HR by machine-hours; property tax by headcount), soft-warn plausible-but-not-preferred, degenerate-denominator guard (Σ=0 → allocate 0, flag), year-over-year driver-change flag (method change).
- `compute_sca(result, profile)` returns per-asset {book_cost, indirect_263a, mixed_263a, additional_263a, adjusted_basis_pre_interest, `ape_for_interest`, allocation audit trail} + conservation tie-checks. Emits `ape_by_asset` to Phase D (does not compute interest).
- Worked test: two assets, mixed HR pool 100k @ SSCM 0.60 split by production headcount (45k/15k) + building-dep 50k by sq ft (10k/40k) → each asset +55k additional §263A; conservation = 0; guardrail test (HR-by-machine-hours blocks); degenerate test (Σ driver=0).
- Rebuild the Asset Basis Schedule tab to **per-asset**: `original book basis + §263A indirect + §263A mixed + §263A(f) interest = adjusted basis` (live formula), regime rollup + tie-check retained.

---

## Phase D — §263A(f) interest capitalization (the hardest engine)

New `engines/interest.py`, `compute_263Af(result, profile)`, called after `compute_unicap`.

**1. Designated-property identification** (Reg §1.263A-8(b)), first match wins — CONFIRMED 2026-07-08 against
IRS LB&I Practice Unit COR-P-006 "Interest Capitalization for Self-Constructed Assets" (rev. 02/01/21), a
secondary-authority audit-technique doc, not binding law, but a reliable cross-check on the reg mechanics:
- real property → designated (Category 1);
- TPP with class life ≥ 20 yrs (Cat 2) OR est. production period > 2 yrs (Cat 3) OR (> 1 yr AND cost > $1M) (Cat 4).
- de minimis screen: TPP with cost ≤ $1M **and** period ≤ 2 yrs → not designated. `NEEDS-CLASSLIFE` flag when only MACRS recovery period (not class life) is available.
- **Separate de minimis rule for ALL designated property, not just TPP** (§1.263A-8(b)(4), newly found in the
  Practice Unit — not previously in this plan): a production period of **90 days or fewer** AND total production
  expenditures **≤ $1,000,000 ÷ number of days in the production period** → excluded from designated property
  entirely (e.g., a 10-day production period caps out at $100,000 of expenditures). Excludes the adjusted basis of
  producing assets, land cost, and interest itself from the expenditure test. Implement as an early-out check
  before the Category 1-4 tests, not after — a property can fail this even if it would otherwise be Category 1.
- Scope: applies to designated property **still in CIP at year end** AND **placed in service during the year** — both computed; the only difference is where the production period ends.
- **Eligible-taxpayer AFR-plus-3 election** (§1.263A-9(e), newly found): a taxpayer with avg. annual gross receipts
  ≤ $10,000,000 for the prior 3 years (and every year since 1994) may elect to skip the weighted-average-interest-
  rate computation entirely and use the highest Applicable Federal Rate + 3 percentage points for the year instead.
  Cheap real simplification for small producers — implement as `EntityProfile.interest_afr_plus_3_election: bool`
  gated on a `avg_gross_receipts_10yr_test` helper (distinct from the $25M/$26M §448(c) small-business test already
  in `EntityProfile` — this is a separate, lower threshold specific to §263A(f)).
- **Cessation-period election** (§1.263A-9/-12(g), newly found): if production activities cease for ≥120
  consecutive days, taxpayer may elect to suspend interest capitalization for that period (with a caution: during
  a cessation period, interest on debt otherwise "traced" to the paused unit may have to be capitalized as
  nontraced interest for *other* units instead — it doesn't just disappear). Lower priority than the AFR-plus-3
  election and de minimis rule above — flag as a Phase D stretch goal, not required for MVP.

**2. Production period** (Reg §1.263A-12): start = first physical activity (real) / 5%-of-total-cost (TPP); end = ready for intended use (PIS). Mid-year PIS → prorate the sub-period by active days.

**3. Avoided-cost method** (Reg §1.263A-9), per unit, per measurement period *i* (≥ quarterly). Every rate below is **annual**; `day_fraction_i` converts it to the period's share of the year (0.25 for an ordinary full quarter; smaller for a partial/mid-year period — this is the *same* fraction that prorates a mid-year PIS sub-period in step 2, not a separate variable):
```
APE_avg_i        = (APE_open_i + APE_close_i) / 2   # APE includes prior §263(a)+§263A costs AND
                                                     # prior capitalized interest (COMPOUNDING, mandatory)
traced_applied_i = min(APE_avg_i, traced_principal)
traced_interest_i  = (traced_principal * traced_annual_rate * day_fraction_i)
                     * (traced_applied_i / traced_principal)
excess_i         = max(0, APE_avg_i - traced_applied_i)
avoided_interest_i = excess_i * WAIR_nontraced_annual * day_fraction_i
WAIR_nontraced_annual = Σ interest(nontraced eligible) / Σ avg_principal(nontraced eligible)
unit_capitalized = Σ_i (traced_interest_i + avoided_interest_i)
total = min(Σ units, total_interest_incurred)       # cap; if binds, pro-rate + flag
```
- Data contract: FixedAsset (type, class_life, cost, PIS date), CIP detail (cumulative expenditure per measurement date, production start, total est. cost, `is_improvement`), Debt (principal, rate, interest_incurred, `traced_to`, `related_party`). Legacy scalar APE×rate stub retained as fallback when schedules are empty.
- **Worked test** (real-property CIP, 4 equal quarters, traced loan $3,000,000 @ 6% annual, nontraced-pool WAIR 7.142857% (1/14) annual, APE ramping linearly from $2,000,000 to $8,000,000 over the year — `day_fraction_i = 0.25` for every quarter, no mid-year proration in this example):

  | Q | APE open | APE close | APE avg | traced_applied | traced_interest | excess | avoided_interest |
  |---|---|---|---|---|---|---|---|
  | 1 | 2,000,000 | 3,500,000 | 2,750,000 | 2,750,000 | 41,250.00 | 0 | 0.00 |
  | 2 | 3,500,000 | 5,000,000 | 4,250,000 | 3,000,000 | 45,000.00 | 1,250,000 | 22,321.43 |
  | 3 | 5,000,000 | 6,500,000 | 5,750,000 | 3,000,000 | 45,000.00 | 2,750,000 | 49,107.14 |
  | 4 | 6,500,000 | 8,000,000 | 7,250,000 | 3,000,000 | 45,000.00 | 4,250,000 | 75,892.86 |

  Totals: traced **176,250.00** + avoided **147,321.43** = **323,571.43** capitalized (verified with exact `Decimal` arithmetic, not rounded intermediates). Cap (`total_interest_incurred`, assumed ≥ $500,000 across traced + nontraced debt in this example) doesn't bind. Q1's traced-applied equals its full APE (excess = 0) because the loan principal exceeds the APE that quarter — illustrates the "uncovered" case only starting Q2, once cumulative APE outgrows the $3M traced loan and the excess spills into the avoided-cost/nontraced-WAIR calculation. This table is the literal fixture for `test_interest.py` — encode the per-quarter APE_open/close pairs directly rather than re-deriving them.
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
    the improvement itself** — this is exactly the plan's prior `is_improvement` guess (narrow the APE to the
    improvement's own costs) and is now CONFIRMED, not speculative. Implement as: when `is_improvement`, APE
    excludes the pre-existing property's basis/APE entirely.
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
3. **Phase C (SCA)** — needs FixedAsset/CIP + driver tables (Phase A) and reuses SSCM; produces `ape_by_asset`.
4. **Phase D (§263A(f))** — needs FixedAsset/CIP/Debt (Phase A) and SCA's APE hand-off (Phase C); hardest, so last.

Each phase ships standalone value and keeps the waterfall tie-out.

## Files
- **New:** `readers.py`, `engines/sca.py`, `engines/interest.py`, `taxonomy/sca_drivers.yaml`, tests `test_readers.py`/`test_mspm_srm.py`/`test_sca.py`/`test_interest.py`.
- **Extend:** `model.py` (schedule + SCA dataclasses, `EngagementData`, `ValidationReport`), `analysis.py` (EntityProfile fields, dispatcher, `compute_mspm/srm/sca`, call `compute_263Af`), `report.py` (per-asset Asset Basis, §263A(f) tab, MSPM/SRM tables, Data Quality tab, waterfall wiring).

## Verification
- Unit tests from each worked example (MSPM 143,000; SRM 36,875; SCA 55k/asset + conservation + guardrail/degenerate; §263A(f) 323,571.43 = traced 176,250.00 + avoided 147,321.43 + compounding + cap + mid-year proration).
- FK/validation tests (unresolved links flagged; debit/credit netting already covered).
- Method-conflict test (SRM chosen but production > de minimis).
- End-to-end: `read_engagement` on a multi-sheet sample → all engines → workbook with zero formula errors, every tab ties, and `formulas`-library evaluation of the live cells (LibreOffice is blocked in this sandbox).
- Extend `validation/validate.py` to report per-engine tie-outs alongside classification accuracy.

## Effort & risk
Four phases, each comparable to the classifier rebuild. Highest risk: §263A(f) (compounding, traced/nontraced, mid-year proration, and the unverified "T.D. 10034" currency — confirm it's a real citation before building tax-year-gated logic around it) and data ingestion quality (real TBs/asset registers are messy — the Data Quality tab is the mitigation). Classification accuracy (~78% raw / ~84% high-confidence precision, ~35% review queue on messy data — re-verify against a live `validate.py` run, this number moves as the taxonomy is hardened) means asset/CIP inputs should be reviewed, not blindly trusted — the review-queue + Data Quality tab surface this. Additionally: every regulatory citation embedded in this plan and the taxonomy is unverified against a primary source (`docs/TAX_DECISIONS.md` §7) — treat citation confirmation as a build-blocking task for any provision Phase B/C/D newly relies on (the MSPM/SRM/SCA/§263A(f) reg sections themselves have not yet been through the same fact-check pass that found errors in the already-built classifier's citations).

## Deferred / out of scope
Combined producer+reseller method; farming (§1.263A-4); interest on flow-through entities (§1.263A-15); live Form 3115 DCN mapping to the current Rev. Proc.; the EY-platform modules (§168(n), §163(j), §45X/§48D, cost seg).
