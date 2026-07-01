# Build Plan — Complete §263A Computation Tool (MSPM · SRM · SCA · §263A(f))

**Goal:** extend `cap263a` from a classifier + SPM inventory calc into a complete tool that accurately computes §263A inventory under **MSPM** and **SRM**, §263A for **self-constructed assets (SCA)** using reasonable allocation factors, and a full **§263A(f)** interest capitalization for designated property (in CIP and placed in service mid-year), including automatic designated-property identification.

Synthesized from four design specs (grounded in Reg §§1.263A-1..-15 and IRS Practice Units COR-P-020/-021/-006/COR-C-023). Each engine has a worked numeric example destined to become a unit test.

## Where we start (already built)
- Classifier + 132-code taxonomy whose `Classification.treatment` dict already carries the exact sub-bucket codes the engines aggregate (`mspm`: `471`/`471-Pre`/`I`/`I-Pre`/`C`/`M`/`E`/`N`; `resale`: `471`/`P`/`S`/`I`/…). **No new classification work — the engines are aggregation + arithmetic over `analyze()` output.**
- `analyze()` → waterfall buckets + `compute_unicap` (SPM only) + SSCM labor ratio (reused by MSPM/SRM/SCA).
- Reader with debit/credit netting; 5-tab report; tests; validation harness.

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

**3. Avoided-cost method** (Reg §1.263A-9), per unit, per measurement date (≥ quarterly):
```
APE_avg_i = (APE_open + APE_close)/2            # APE includes prior §263(a)+§263A costs AND
                                                # prior capitalized interest (COMPOUNDING, mandatory)
traced_applied = min(APE_avg, traced_principal)
traced_interest = actual_traced_interest * (traced_applied/traced_principal) * proration
excess = max(0, APE_avg - traced_applied)
avoided_interest = excess * WAIR_nontraced * day_fraction * proration
WAIR = Σ interest(nontraced eligible) / Σ avg_principal(nontraced eligible)
unit_capitalized = Σ (traced_interest + avoided_interest)
total = min(Σ units, total_interest_incurred)   # cap; if binds, pro-rate + flag
```
- Data contract: FixedAsset (type, class_life, cost, PIS date), CIP detail (cumulative expenditure per measurement date, production start, total est. cost, `is_improvement`), Debt (principal, rate, interest_incurred, `traced_to`, `related_party`). Legacy scalar APE×rate stub retained as fallback when schedules are empty.
- Worked test: real-property CIP, 4 quarters, cumulative 2M→8M, traced loan 3M@6%, nontraced pool WAIR 7.142857% → traced 150,000 + avoided 111,023.69 = **261,023.69** (cap 680,000 doesn't bind); asserts per-quarter compounding and that uncovered Q1 traced interest stays deductible.
- **T.D. 10034 (Oct 2025) caveat, gated on `tax_year`:** associated-property rule eliminated (don't add land/existing structure to APE for TY≥2026); interest narrowed for improvements (`is_improvement` → only the improvement's own costs in APE). Flags `ASSOCIATED-PROPERTY-EXCLUDED`, `IMPROVEMENT-NARROWED-2025`; verify effective-date/mechanics against the published T.D. before locking.
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
- Unit tests from each worked example (MSPM 143,000; SRM 36,875; SCA 55k/asset + conservation + guardrail/degenerate; §263A(f) 261,023.69 + compounding + cap + mid-year proration).
- FK/validation tests (unresolved links flagged; debit/credit netting already covered).
- Method-conflict test (SRM chosen but production > de minimis).
- End-to-end: `read_engagement` on a multi-sheet sample → all engines → workbook with zero formula errors, every tab ties, and `formulas`-library evaluation of the live cells (LibreOffice is blocked in this sandbox).
- Extend `validation/validate.py` to report per-engine tie-outs alongside classification accuracy.

## Effort & risk
Four phases, each comparable to the classifier rebuild. Highest risk: §263A(f) (compounding, traced/nontraced, mid-year proration, T.D. 10034 currency) and data ingestion quality (real TBs/asset registers are messy — the Data Quality tab is the mitigation). Classification accuracy (~66–71% on messy data) means asset/CIP inputs should be reviewed, not blindly trusted — the review-queue + Data Quality tab surface this.

## Deferred / out of scope
Combined producer+reseller method; farming (§1.263A-4); interest on flow-through entities (§1.263A-15); live Form 3115 DCN mapping to the current Rev. Proc.; the EY-platform modules (§168(n), §163(j), §45X/§48D, cost seg).
