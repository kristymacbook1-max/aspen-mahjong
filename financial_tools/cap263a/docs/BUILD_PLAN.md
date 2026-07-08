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
- **Open SME decisions that materially affect this build** (`docs/TAX_DECISIONS.md` §3, items 1 and 5 — resolve or make configurable before locking Phase B math): (1) whether `DM-*` direct-materials lines are correctly tagged `471-Pre` for the MSPM pre-production ratio; (5) whether Additional-§263A-tier labor (purchasing/warehouse/buying) belongs in the SSCM labor-ratio denominator — three defensible readings exist with a material dollar swing. Build Phase B's ratio logic to expose both as named constants/flags rather than hardcoding one answer, so the SME's eventual decision is a one-line change, not a re-derivation.

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

### MSPM (Reg §1.263A-2(c)) — two absorption ratios
```
pre_production_ratio = preprod_additional_263A / preprod_471          # I-Pre / 471-Pre (+ mixed preprod share)
production_ratio     = prod_additional_263A    / prod_471             # I    / 471     (+ mixed prod share)
add'l_to_inv = pre_production_ratio*ending_inv_471_preprod + production_ratio*ending_inv_471_prod
```
- Split additional & §471 pools pre-production vs production from the `mspm` codes; split SSCM `mixed_cap` by §471-labor (fallback: §471 base) proportion.
- **Negatives + $50M rule:** SPM excludes negative §263A when `avg_gross_receipts_prior3 > $50M` (flag REVIEW → suggest MSPM); **MSPM allows negatives regardless**. Add `avg_gross_receipts_prior3`, `include_negative_263a`, `LARGE_PRODUCER_THRESHOLD=50_000_000`.
- **HAR election:** 3-yr test period → frozen ratio(s) for a 6-yr qualifying period; recompute in yr 3; ±0.5% corridor. Fields: `har_election`, `har_ratios`, `har_prior_year_ratios`, `har_qualifying_year_index`.
- Worked test: preprod 140k/1.0M=0.14, prod 360k/3.0M=0.12 → 0.14×250k + 0.12×900k = **143,000**.

### SRM (Reg §1.263A-3(d)) — combined ratio (two denominators)
```
purchasing_ratio       = purchasing_costs / current_year_471_costs               # beginning inv EXCLUDED
storage_handling_ratio = storage_handling / (beginning_inv_471 + current_year_471)# beginning inv INCLUDED
combined = purchasing_ratio + storage_handling_ratio
add'l_to_inv = combined * ending_inventory_471
```
- The #1 reseller audit error is the S&H denominator — assert beginning inventory is in S&H denom only.
- **1/3–2/3 purchasing-labor** rule; **90/10 dual-function storage** rule; **de minimis production 10%/10%** test (if it fails while method=SRM → return `method_conflict:True`, recommend SPM/MSPM).
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

**1. Designated-property identification** (Reg §1.263A-8(b)), first match wins:
- real property → designated (Category 1);
- TPP with class life ≥ 20 yrs (Cat 2) OR est. production period > 2 yrs (Cat 3) OR (> 1 yr AND cost > $1M) (Cat 4).
- de minimis screen: TPP with cost ≤ $1M **and** period ≤ 2 yrs → not designated. `NEEDS-CLASSLIFE` flag when only MACRS recovery period (not class life) is available.
- Scope: applies to designated property **still in CIP at year end** AND **placed in service during the year** — both computed; the only difference is where the production period ends.

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
- **⚠ "T.D. 10034 (Oct 2025)" citation is UNVERIFIED and under active suspicion of fabrication** (flagged by a citation-accuracy audit — see `docs/TAX_DECISIONS.md` §7 — no Treasury Decision by this number is recognized). Do NOT gate any tax-year cutover logic on this T.D. number without first confirming, from a primary source (IRS.gov, a tax research service, or direct reg-text lookup), that it exists and says what's described below. If it does not check out, treat the associated-property-rule/improvement-interest change described here as unconfirmed and drop the `tax_year`-gated behavior entirely rather than shipping a citation-shaped guess. As specified (pending that verification): associated-property rule eliminated (don't add land/existing structure to APE for TY≥2026); interest narrowed for improvements (`is_improvement` → only the improvement's own costs in APE). Flags `ASSOCIATED-PROPERTY-EXCLUDED`, `IMPROVEMENT-NARROWED-2025`.
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
