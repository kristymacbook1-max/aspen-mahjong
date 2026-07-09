# Build Plan — Complete §263A/§263(a)/§266/§174/§59(e) Capitalization Tool (MSPM · SRM · SCA · §263A(f) · R&E · Intangibles · Qualified Expenditures)

**Goal:** extend `cap263a` from a classifier + SPM inventory calc into a complete tool that accurately computes §263A inventory under **MSPM** and **SRM**, §263A for **self-constructed assets (SCA)** using reasonable allocation factors, and a full **§263A(f)** interest capitalization for designated property (in CIP and placed in service mid-year), including automatic designated-property identification — **plus, ADDED 2026-07-09 per direct scope-expansion request, §174/§174A research & experimental expenditure capitalization (Phase F), §1.263(a)-4/-5 intangibles/transaction costs and §195/§248/§709 start-up/organizational costs (Phase G), and §59(e) elective qualified-expenditure amortization (Phase H)** — every mandatory AND elective capitalization provision under §263(a)/§174/§266/§59(e) this plan could identify, not §263A alone.

**Today the tool accepts exactly one input — a trial balance — and that is the ceiling on what it can compute.** SCA and §263A(f) are mathematically impossible from a trial balance alone — they need schedules 3-5 below. MSPM/SRM are gated only on inventory-balance/on-hand scalar inputs (`EntityProfile` fields, no new schedule) — **corrected 2026-07-09: an earlier draft of this paragraph said all four engines "need four more schedules" and that "nothing in Phase B/C/D can run until Phase A exists," which contradicted the sequencing section's own (accurate) statement that Phase B needs "no new schedules beyond inventory balances." Phase B is NOT gated on Phase A; Phases C/D are.** The complete tool takes **eight inputs** (inputs 6-8 ADDED 2026-07-09, see Phases F/G/H below — the plan's scope was §263A-only; it now also covers §174/§174A, §1.263(a)-4/-5 + §195/§248/§709, and §59(e), per direct user request):

| # | Input | Feeds | Status |
|---|---|---|---|
| 1 | **Trial balance** (by cost center/department) | Classification, SPM absorption ratio | ✅ Built |
| 2 | **Book-tax difference schedule** | Negative-§263A adjustments, M-1 reconciliation, §481(a) surface | ❌ Phase A |
| 3 | **Fixed asset schedule** | Per-asset basis/class-life/PIS date → SCA allocation target + §263A(f) designated-property ID | ❌ Phase A |
| 4 | **CIP (construction-in-progress) detail** | Cumulative production expenditure over time → the core §263A(f) APE input | ❌ Phase A |
| 5 | **Debt/interest schedule** | Traced vs. non-traced debt, principal, rates → the other half of §263A(f) | ❌ Phase A |
| 6 | **R&E (§174) expenditure schedule** — ADDED 2026-07-09 | Domestic/foreign split, project-level detail → Phase F's amortization schedule + catch-up computation | ❌ Phase F |
| 7 | **Intangibles & transaction-cost schedule** — ADDED 2026-07-09 | Per-transaction/per-intangible facts (covered-transaction status, facilitative-cost detail, start-up/organizational totals) → Phase G | ❌ Phase G |
| 8 | **§59(e) qualified-expenditure schedule** — ADDED 2026-07-09 | Per-item IDC/mining/circulation/domestic-R&E expenditures eligible for the elective 10-yr/60-month AMT-preference-avoidance amortization → Phase H | ❌ Phase H |

Phase A below builds the ingestion for inputs 2-5. Phases C/D are the calculation engines inputs 3-5 feed and cannot run until Phase A exists; Phase B needs only the new `EntityProfile` scalars. **Input 2 consumer, spec'd 2026-07-09 (a review pass found the BTD schedule was an orphan — ingested by Phase A but consumed by nothing in Phases B-D):** the BTD schedule feeds (a) the negative-§263A pipeline — book-tax differences embedded in §471 costs (book-over-tax depreciation in overhead, §174 timing, etc.) become negative additional-§263A costs when `include_negative_263a` is set, entering the MSPM/SRM numerators per §1.263A-1(d)(3); and (b) an M-1-style reconciliation block on the Summary tab tying book expense to the post-capitalization deductible total. If neither lands in the phase that ships BTD ingestion, defer input 2 explicitly rather than shipping a reader with no consumer. Inputs 6-8 are their own ingestion targets, built alongside Phases F/G/H respectively (not folded into Phase A, since none of Phases F/G/H depend on the §263A input 2-5 schedules or vice versa).

Synthesized from four design specs (grounded in Reg §§1.263A-1..-15 and IRS Practice Units COR-P-020/-021/-006/COR-C-023). **Status as of 2026-07-08 (see `docs/TAX_DECISIONS.md` §7a-§7f for the full history): the core formulas for SSCM, MSPM, SRM, and §263A(f) designated-property/avoided-cost mechanics have since been verified directly against primary regulation text** (with real bugs found and fixed along the way — see the phase sections below, each individually marked VERIFIED/CONFIRMED/CORRECTED with a date). What remains genuinely unverified: pinpoint citations for `§1.471-11`, and any Practice Unit document-ID/revision-date detail not independently cross-checked. (Previously on this list, all since verified: the §448(c) threshold — $32,000,000 for 2026 per Rev. Proc. 2025-32, matching `EntityProfile.THRESHOLDS`; and `§1.263(a)-1/-3` and `§1.266-1` — verified 2026-07-09 against complete authoritative eCFR text supplied directly into this project, see the full-text status update below.) Do not treat this plan as a finished filing position regardless of verification status — it is a build spec, not tax advice — but do not read the blanket "unverified" framing that appeared in earlier drafts of this paragraph as still accurate; it is not.

**STATUS UPDATE 2026-07-09 — FULL REGULATION-BY-REGULATION REVIEW (§§1.263A-1 through -15), see `docs/TAX_DECISIONS.md` §9.** Five parallel review agents compared this plan clause-by-clause against retrieved regulation text (via mirrored/search-retrieved eCFR text — the canonical hosts are blocked from this environment; provenance documented in §9). This pass found and fixed: **a material bug in the shipped SSCM labor-ratio code** (denominator rule backwards on two counts vs §1.263A-1(h)(4) — see the SSCM section), **a reversal of a prior "correction"** (the two-sided 90% department rule at (g)(4)(ii) is real; yesterday's "one-sided only" edit was itself wrong), **a §1221 citation misreading in Phase D** (inventory carve-out, not patents), **a wrongly-dropped T.D. 10034 claim restored** (the associated-property rule really was eliminated), a day-proration sentence contradicting the measurement-date convention, a missing WAIR fallback, a resolved SRM open question, a §1.263A-7 method-change gap, and a set of smaller citation/scope fixes — each marked in place below with `CORRECTED/ADDED 2026-07-09`.

**STATUS UPDATE 2026-07-09 (second pass) — COMPLETE AUTHORITATIVE eCFR TEXT SUPPLIED IN-SESSION, see `docs/TAX_DECISIONS.md` §10.** The full current text of §§1.261-1 through 1.266-1 (including §1.263(a)-1 through -6, the tangible property regulations) and the complete §1.263A-0 outline plus §§1.263A-1 through -15 was provided directly into this project, eliminating the mirror/search-snippet provenance caveat for everything it covers. Every mechanic this plan marked CONFIRMED in the §9 review that is covered by the supplied text checked out against it verbatim (the (h)(4) denominator fix, both sides of the (g)(4)(ii) 90% rule, (h)(2)'s four eligible-property categories, the MSPM formula and all its examples, the SRM ratios and (d)(3)(i)(F) sub-split, the §1.263A-8/-9/-11/-12 mechanics including the traced-debt capitalized-interest component, WAIR AFR fallback, (c)(7) proration shares, sourcing order, eligible-debt exclusions, suspension rules, and the T.D. 10034 provisions at -8(d)(3)/-11(e)/(f)/-15(a)(6)). This pass ALSO found: one of yesterday's hedges was itself wrong ((h)(5) DOES exclude income-based taxes — see the SSCM section), one adopted SME decision must be reversed (the SRM 90/10 threshold basis — see the SRM section), the previously-unretrievable §1.263A-3(a)(4)(iv) is resolved, and several genuinely new items entered the plan (unit-of-property/common-feature rules, contract-payment APE mechanics, pick-and-pack and related handling exclusions, the §1.263A-9(d) no-tracing election, the §1.263A-1(d)(2) financial-statement-based §471-cost definition, aged-property production periods) — each marked `2026-07-09 full-text pass` below.

**STATUS UPDATE 2026-07-08 — PLAN DECLARED FINAL/BUILDABLE, see `docs/TAX_DECISIONS.md` §8 for the full record.** Every formula above (SPM/MSPM/SRM/SCA/§263A(f)) was run end-to-end against non-trivial synthetic datasets (larger and messier than the regulation's own tiny textbook examples) by independent sub-agents, using exact `Decimal`/`Fraction` arithmetic. Every documented formula computed correctly on every scenario tested (SSCM-election variants, 90% de minimis shifts, dual-function facilities, multi-loan tracing, cross-unit pro-rata proration) — no arithmetic errors survived this pass. Two categories of finding came out of it, both now closed:
1. **A real bug in already-shipped code** (not this plan): `taxonomy/categories.yaml`'s `INV-BOOK` code had a bare `"finished goods"` keyword that silently swallowed genuine Additional-§263A cost lines (e.g. "Finished goods warehouse storage costs") into the Balance Sheet tier — the immune-tier scoring bonus outweighed `ADD-FGWH`'s own kw+cc+zone score. **Fixed 2026-07-08**: narrowed to `"finished goods inventory"` (still catches genuine balance lines, no longer bare-matches a cost-line description), with a regression test added (`test_fg_warehouse_costs_dont_collide_with_fg_inventory_balance`, `tests/test_engine.py`). Full suite re-run (95 passing) and the accuracy validation harness re-run — no regression (78.4%/84.0%, unchanged from the documented baseline).
2. **Four genuine gaps in this document**, each surfaced only because the stress test used datasets with more moving parts than the tiny worked examples ever needed to resolve — MSPM's rounding order and negative-residual/negative-on-hand edge cases, SRM's multi-facility combination mechanic and on-site/off-site definitions, SCA's split-SSCM-eligibility-within-one-pool question, and Phase D's sourcing-order-vs-proration-pseudocode relationship. **Each is now resolved with an explicit, documented decision** — see the phase sections below (each marked `DECISION 2026-07-08`) and `docs/TAX_DECISIONS.md` §8 for the full rationale and rejected alternatives. These are SME-level policy calls made where the primary text was genuinely silent, not re-derivations of settled law — flagged as such and open to override.

## Where we start (already built)
- Classifier + 133-code taxonomy whose `Classification.treatment` dict already carries the exact sub-bucket codes the engines aggregate (`mspm`: `471`/`471-Pre`/`I`/`I-Pre`/`C`/`M`/`E`/`N`; `resale`: `471`/`P`/`S`/`I`/…). **No new classification work — the engines are aggregation + arithmetic over `analyze()` output.** Current classification accuracy: ~78% raw / ~84% high-confidence precision on a 250-line messy labeled set (see README.md; re-check with `python -m financial_tools.cap263a.validation.validate` before relying on a stale number).
- `analyze()` → waterfall buckets + `compute_unicap` (SPM only) + SSCM labor ratio (reused by MSPM/SRM; **SCA reuse is GATED, not unconditional — see Phase C's `sscm_eligible` check below, added 2026-07-08 after this line was found stale relative to that fix**).
- Reader with debit/credit netting; 5-tab report; tests; validation harness.
- **Guardrail infrastructure already built and REUSE, don't duplicate:** `EntityProfile.LARGE_PRODUCER_THRESHOLD` (>$50M rule), the SSCM-ratio [0,1] clamp + warning pattern (`analysis.py` `compute_unicap`, ~line 220), the absorption-ratio->1 warning, and the `bucket_warnings`/`unicap["warnings"]` list pattern that surfaces computation caveats on the Summary tab. MSPM/SRM/SCA/§263A(f) must plug into this same warnings list, not invent a parallel mechanism — that's how a >100%-style bug gets caught instead of silently shipped again.
- **SME decisions affecting Phase B, both RESOLVED 2026-07-08** (`docs/TAX_DECISIONS.md` §3 items 1 and 5): (1) `DM-*` direct-materials lines are correctly tagged `471-Pre` for the MSPM pre-production ratio — confirmed, no change needed, use as-is. (5) Additional-§263A-tier labor (purchasing/warehouse/buying) belongs in the SSCM labor ratio's numerator AND denominator, alongside §471 production labor — implemented in the shipped `compute_unicap` (`analysis.py`, `CAPITALIZABLE_LABOR_TIERS`/`SSCM_DENOM_EXCLUDED_TIERS`; the denominator rule itself was CORRECTED 2026-07-09 per §1.263A-1(h)(4) — see the SSCM section below and `docs/TAX_DECISIONS.md` §9 — but item 5's inclusion decision is unaffected), so Phase B's MSPM/SRM engines inherit this correctly for free by reusing the same SSCM computation; no separate Phase B decision needed. Three items remain open and unresolved (§3 items 2-4: EX-BID successful-bids-only gating, §266 land-context auto-routing vs. confirmed election, repair-vs-improvement keyword scoping) — none of them block Phase A-D, since they're classifier-level, not engine-level, but resolve before relying on the classifier output those engines consume.
- **Taxonomy already has partial coverage for Phases F/G/H, found 2026-07-09 while scoping those phases — reuse, don't re-tag:** `taxonomy/categories.yaml` (3,958 lines) already contains `EX-RD` (R&D/R&E costs, tier1 `Excluded`), `EX-174AMORT` (the §174 amortization deduction line item, also tier1 `Excluded`), `SEC263A-TXN` (§1.263(a)-5 transaction/facilitative costs), `SEC263A-INTANG` (§1.263(a)-4/§197 intangibles), and `SEC195-STARTUP` (§195/§248/§709 start-up/organizational costs) — both under a `§263(a) Transaction/Intangible` tier1. **The gap Phases F/G/H close is downstream of classification, not classification itself:** `analysis.py`'s `bucket_of()` (~line 126) routes every `§263(a) Transaction/Intangible`-tier line to a single flat `"§263(a) Mandatory"` bucket total, and `EX-RD`/`EX-174AMORT` both route to `"Deductible"` unconditionally — neither distinguishes the sub-treatments each actually requires (domestic R&E expensed vs. elected-capitalized vs. mandatorily-capitalized foreign R&E; §197-eligible acquired intangibles vs. other capitalized intangibles; the 12-month-rule/bright-line-date/success-fee mechanics; the $5,000/$50,000 start-up phase-out; syndication's permanent non-amortization). No per-item amortization schedule exists for any of it. Also found: `SEC263A-INTANG`'s own `authority` field already flags a likely mis-citation (geological/geophysical costs keyworded alongside §1.263(a)-4/§197 items when they're probably §167(h) instead) — carry that flag into Phase G's build, don't silently re-tag it.

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
  trade or business (production AND resale AND selling/R&D/G&A, if the taxpayer has
  them) — not just production. **CORRECTED 2026-07-09 (`docs/TAX_DECISIONS.md` §9):
  a prior draft of this bullet ended "This is what `compute_unicap` implements today"
  — that claim was FALSE. The shipped code implemented the opposite rule on both
  counts (Mixed-Service-tier labor IN the denominator, Excluded-tier labor OUT),
  and this section's own correct prose sat directly above the false claim without
  anyone noticing the contradiction. The code and its two tests are now fixed to
  match this bullet (`SSCM_DENOM_EXCLUDED_TIERS` in `analysis.py`; Non-Operating
  labor also stays out of the denominator as outside the trade or business — a
  documented judgment call). Any workpaper generated before this fix used a wrong
  ratio.**
- **Production cost allocation ratio (h)(5) — producers only, not available to
  resellers**: `§263A production costs / total costs`, where the denominator is
  dramatically broader than the labor ratio's — "total costs" means every cost of
  the trade or business excluding mixed service costs and interest: all
  direct/indirect production costs *and* R&E, *and* marketing/selling/distribution
  costs that every other part of this tool treats as `Excluded`-tier and walls off.
  **HEDGE CLOSED — 2026-07-09 full-text pass: the income-based-taxes exclusion IS in
  the regulation.** §1.263A-1(h)(5)(ii)'s LAST sentence (which the earlier snippet-level
  retrieval missed): *"Such costs do not include, however, taxes described in paragraph
  (e)(3)(iii)(F) of this section"* — i.e., taxes assessed on the basis of income. The
  confirmed exclusion list for "total costs" is therefore mixed service costs, interest,
  AND income-based taxes — exactly the original three-item list a hedge was added
  against yesterday. Meta-note for the audit trail: this is the inverse failure mode of
  the ones §9 recorded — an over-cautious hedge produced by an incomplete retrieval of
  an otherwise-correct paragraph; the hedge itself was the error. **Not implemented; see
  below.**
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
call) and compute the ratio from `is_total` minus mixed-service, interest, AND
income-based-tax buckets in both numerator/denominator per the verified formula above
(the income-tax exclusion confirmed at (h)(5)(ii) last sentence, 2026-07-09 full-text
pass — see the corrected bullet above).

**Other verified SSCM mechanics not yet reflected in the shipped code:**
- **Eligible property (h)(2) — CORRECTED 2026-07-09 (the prior draft collapsed two
  independent qualifying routes into one conjunctive test):** eligible property has
  FOUR categories — (A) inventory; (B) non-inventory property held primarily for
  sale; (C) self-constructed assets *substantially identical in nature to, and
  produced in the same manner as*, inventory the taxpayer produces (or other
  held-for-sale property); (D) self-constructed TPP produced on a *routine and
  repetitive basis* — numerous substantially identical assets, standardized designs
  and assembly-line techniques, AND (≤3-year §168(c) recovery period OR a material/
  supply that will be used and consumed within 3 years of production). (C) and (D)
  are ALTERNATIVE routes, not one merged test — a prior draft (and Phase C's gate,
  now fixed) required "substantially identical to inventory" AND "routine and
  repetitive" AND "≤3-yr MACRS" together, which fails-safe but would wrongly flag
  (C)-qualifying assets as ineligible, and omitted the materials/supplies arm of
  (D) entirely. There is also an explicit taxpayer election ((h)(2)(ii)) to EXCLUDE
  self-constructed assets from SSCM entirely, in which case they fall back to the
  general (g)(4) method (the fallback is stated in the regulation itself).
  Relevant to Phase C (SCA): most self-constructed *capital* assets (the kind Phase C
  targets — longer-lived, not mass-produced, not identical to the taxpayer's
  inventory) likely qualify under NEITHER (C) nor (D), meaning SCA's mixed-cost
  allocation should default to the general method (below), not silently assume SSCM
  eligibility — that conclusion survives the correction; only the test's shape
  changed.
- **90% de minimis department rule (g)(4)(ii), NOT SSCM-specific — a general
  mixed-service-cost rule). RE-CORRECTED 2026-07-09 — yesterday's "one-sided only"
  correction was ITSELF wrong; the primary (g)(4)(ii) text contains BOTH sides:**
  (a) if 90%+ of a mixed-service *department's* costs are DEDUCTIBLE service costs,
  the taxpayer **may elect** not to allocate any portion to production/resale
  (elective); AND (b) if 90%+ of the department's costs are CAPITALIZABLE service
  costs, the taxpayer **must allocate 100%** of the department's costs to the
  production or resale activity benefitted (mandatory). The rule is two-sided but
  ASYMMETRIC — elective on the deductible side, mandatory on the capitalizable side.
  **Refined 2026-07-09 full-text pass — the exact conditionality:** the regulation's
  mandatory side opens *"Under this election, however..."* — the ≥90%-capitalizable→100%
  allocation is a CONDITION OF MAKING the election, not a free-standing rule; a taxpayer
  that never makes the (g)(4)(ii) election is bound by neither side. And per the
  paragraph's last sentences, one election covers ALL of the taxpayer's mixed service
  departments (no cherry-picking departments) and is the adoption of/change in a method
  of accounting. Implementation shape: `EntityProfile.msc_90_10_election: bool`; when
  set, each department ≥90% deductible → zero allocation, each department ≥90%
  capitalizable → 100% allocation, everything else → normal ratio; when unset, no
  department-level 90% shortcut in either direction.
  The 2026-07-08 draft declared the capitalizable side "UNCONFIRMED... do not rely"
  because it verified against IRS Concept Unit COR-C-023, which states only the
  deductible side — verifying against a secondary source's silence instead of the
  primary text produced a false negative (see `docs/TAX_DECISIONS.md` §9; the same
  false correction was applied to Phase C's bullet, also now fixed). Implementation
  consequence: the MANDATORY ≥90%-capitalizable→100% side is an under-capitalization
  risk if unimplemented — it needs at least a warning flag when a department's ratio
  crosses it, even before the per-department mechanics are built. What still does
  NOT transfer: this is a department-level rule; it is not a symmetric shortcut for
  per-asset N-way driver shares (Phase C's caution on that narrower point stands).
  (§1.263A-2(c)(3)(iii)(C)'s MSPM SSCM-split de minimis rule is a separate,
  genuinely-elective two-sided provision — see the MSPM section.) Under SSCM
  specifically, (h)(8) says an electing department drops out of the SSCM ratio pool
  entirely (its costs bypass the ratio, going straight to the qualifying activity).
  **Not implemented** — the current SSCM ratio treats all mixed-service costs
  uniformly with no per-department 90% carve-out. Low priority for the elective
  side; add the mandatory-side warning when Phase B lands.
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
  trade or business, apportion "by using any reasonable allocation method consistent
  with the principles of paragraph (f)(4)" (exact wording confirmed 2026-07-09
  full-text pass — the earlier could-not-verify hedge on this phrase is closed). Out
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
                       + R&E schedule + Intangible/Txn schedule + §59(e) schedule (Phases F/G/H)
model.py (extend)     BookTaxDifference, FixedAsset, CIPProject(+CIPExpenditure),
                      DebtInstrument, SelfConstructedAsset, CostPool, DriverRow, Driver,
                      EngagementData, ValidationReport
                      + AmortizableItem (ADDED 2026-07-09 — generalizes the "Asset Basis
                        Schedule" concept below into the one shared basis/amortization
                        record Phases C/F/G/H all post into: basis, recovery period,
                        convention, amortization-start date, disposal handling)
                      + REExpenditure, IntangibleItem, TransactionCostItem,
                        StartupOrgCostPool, QualifiedExpenditureElection (Phases F/G/H)
analysis.py (extend)  EntityProfile fields; compute_unicap -> dispatcher:
                        compute_spm (existing) | compute_mspm | compute_srm
engines/ (new)        sca.py (compute_sca), interest.py (compute_263Af)
                      + re_capitalization.py (compute_174, Phase F)
                      + intangibles.py (compute_263a4_5, Phase G)
                      + qualified_expenditures.py (compute_59e, Phase H)
taxonomy/ (new data)  sca_drivers.yaml  (pool-category -> allowed/preferred driver matrix)
                      + qualified_expenditure_periods.yaml (§59(e) category -> period
                        table: circulation 3yr / R&E 10yr / IDC 60mo / mining exp+dev
                        10yr each — see Phase H)
report.py (extend)    per-asset Asset Basis; real §263A(f) tab; MSPM/SRM ratio tables;
                      Data Quality tab; waterfall wiring
                      + generalized into a Basis & Amortization Schedule tab covering
                        tangible assets, R&E pools, intangibles, and §59(e) elections
                        (Phases F/G/H); §59(e) Election Tracker tab
```

Contract that keeps the waterfall stable: **every inventory method returns `additional_capitalized_to_inventory` and `adjusted_deductible_post`** (the keys the Summary already consumes), so MSPM/SRM need no waterfall change. Phases F/G/H follow the same discipline: each returns amounts into the existing `CAPITALIZED_BUCKETS`/`BUCKETS` waterfall (a new `"§174 Capitalized"` bucket for Phase F; existing `"§263(a) Mandatory"` refined, not replaced, for Phase G — see below) plus a per-item row on the shared Basis & Amortization Schedule, so the Summary tie-check keeps working by construction rather than by a parallel total.

---

## Runtime Pipeline — the five steps the finished tool actually runs, in order (ADDED 2026-07-09)

**Why this section exists:** a completeness audit (three parallel agents, 2026-07-09) confirmed the plan, as written, is organized entirely by Code section/Phase letter (A=ingestion, B=inventory, C=SCA, D=interest, F=R&E, G=intangibles, H=§59(e)) with **no single section stating the runtime order the finished tool processes a client's data in.** "Sequencing & why" (below) answers a *different* question — what order to BUILD the phases in — and risked being mistaken for this. This section is the authoritative runtime pipeline, stated once, per the project owner's own five-step description of what the finished tool must do:

**Step 1 — Ingest a department/cost-center-based trial balance.** Phase A, input 1. ✅ Already built (`reader.py`/`read_trial_balance`).

**Step 2 — Adjust the P&L for book-tax differences to produce an actual tax-basis, department/cost-center-level trial balance.** **GENUINE GAP, closed here 2026-07-09** (confirmed by audit: Phase A's BTD schedule, as previously spec'd, only fed the negative-§263A pipeline and an M-1 *reconciliation note* on the Summary tab — it never materialized an adjusted TB as its own deliverable). New requirement: `compute_tax_basis_tb(tb_lines, btd_schedule) -> List[TBLine]` (or a dedicated `TaxBasisTBLine`) that applies every book-tax difference to its source TB line and re-rolls up by cost center/department, producing a **second, tax-basis trial balance** structurally identical to the input TB (so it can be re-classified by the same engine) — not merely a reconciling adjustment buried in a footnote. New tab: **Tax-Basis TB** (book TB → BTD adjustments applied, column by column → tax-basis TB, with a department/cost-center subtotal row for each). The existing M-1 reconciliation block (Phase A's original spec) stays too — it explains the *difference*; this new tab delivers the *result*. Every downstream step (3-5) operates on this tax-basis TB, not the raw book TB.

**Step 3 — Mandatory capitalization, by asset category, starting from what's already capitalized.** Two mechanics, and the audit found they must be kept conceptually SEPARATE (conflating them was the risk):
- **(3a) Detection — already solved, just needs naming.** The classifier's `Classification.cap_vs_deduct`/`tier1` fields, applied to the tax-basis TB from Step 2, already identify every line that is a required-capitalize cost still sitting on the P&L (`bucket_of()` in `analysis.py`) — this is the "identify anything left on the trial balance that is a required cost" mechanic, and it already exists. Nothing new to build here except re-running it against the Step-2 tax-basis TB instead of the raw book TB.
- **(3b) Basis reconciliation — a genuine, mostly-unbuilt gap, see the new section immediately below.** For asset categories that ALREADY have a pre-existing book/tax basis (placed-in-service real/tangible property, existing CIP, existing intangibles, interest already capitalized on the books under ASC 835-20), the tool must read that existing basis BEFORE adding newly-detected mandatory amounts, so it adds the DELTA, not a duplicate of the whole required amount. For inventory (§263A), this reconciliation step is **not applicable by design** — additional §263A costs are, by definition, costs the taxpayer's own books never capitalized (see the new "Basis Reconciliation" section for why this is correct, not an oversight).

**Step 4 — Allocation: post the mandatory-capitalization amounts to specific assets.** The generalized `AmortizableItem`/Basis & Amortization Schedule (Phases C/F/G/H already post to it). **Confirmed by audit, now stated explicitly rather than left implicit:** allocation granularity differs correctly by asset category, not uniformly — Phase C/F/G/H post to *specific, named assets* (an item-by-item schedule); Phase B (inventory) posts one *pool total* to ending inventory as a whole, because that is how the regulations themselves define SPM/MSPM/SRM absorption ratios (applied to an inventory pool, never to individual SKUs/lots) — **this is not a gap to fix, it is the correct reflection of how UNICAP actually works**, and this plan should stop being read as though per-item inventory allocation were an implicit unmet goal. The one place allocation was found genuinely MISSING, not just pool-scoped: **Gate 4's §263(a)-mandatory tangible-property improvements (BAR-flagged lines) currently route to a review queue with no posting to any specific `FixedAsset` at all** — fixed in the new Basis Reconciliation section below.

**Step 5 — Elective capitalization, run AFTER and ON TOP OF the mandatory pass.** **GENUINE GAP, closed here 2026-07-09**: no consolidated list of the ~15+ elections scattered across this document existed anywhere, and the document conflated two (really three) different kinds of "election" that behave differently in this pipeline. See the new "Elective Capitalization Menu" section below (placed near Phase E, since it maps directly onto the interview gates). **Explicit sequencing principle, stated for the first time here:** elective capitalization NEVER reduces or replaces a mandatory amount from Step 3/4 — it either (a) chooses HOW a mandatory amount is computed (a method-of-accounting election — doesn't change the plan's Step-3/4 output shape at all, just which formula produces it), (b) ADDS capitalization on top of an amount that would otherwise be currently deductible (a true incremental Step-5 action), or (c) uses a safe harbor to DEDUCT currently an amount that Step 3's BAR/mandatory rules would otherwise have required to be capitalized (the one category that legitimately reduces a Step-3 amount, and only because Congress/Treasury built a specific safe-harbor override into the mandatory rule itself — not a generic "election beats mandatory" principle). The Elective Capitalization Menu tags every election with which of these three it is.

---

## Basis Reconciliation — book-capitalized vs. tax-required, per asset category (ADDED 2026-07-09)

**What this section is:** the mechanic Step 3b above depends on, generalized from the one place it already exists in this plan (Phase C's self-constructed-asset bucket structure) to every asset category where a pre-existing basis can exist. Two audits independently converged on the same finding: this mechanic is (a) NOT applicable to inventory (correctly, by the nature of §263A additional costs), (b) PARTIALLY built, with an explicitly unresolved gap, for self-constructed assets in CIP, and (c) MISSING ENTIRELY for every other category — interest, intangibles, R&E, and (most consequentially) tangible-property improvements under Gate 4.

**(1) Inventory (§263A) — NOT APPLICABLE, and this is correct, not a gap.** Every dollar the classifier tags `Additional §263A`/`Capitalizable (MSPM)` is, by definition, a cost the taxpayer's OWN books never capitalized — it is still sitting on the P&L as a period expense (that is precisely what makes it "additional," as opposed to the `§471 Cost` tier, which the books already capitalize). There is no pre-existing "already capitalized" baseline to reconcile against for this pool; `compute_unicap`'s absorption-ratio math (SPM/MSPM/SRM) IS the complete mechanic. The one real book-conformity question here — confirmed already spec'd, Phase B's §1.263A-1(d)(2) GAP note above — is whether the classifier's `§471 Cost`/`Additional §263A` SPLIT matches the taxpayer's actual financial-statement capitalization (a classification-accuracy question), not a basis-reconciliation question.

**(2) Self-constructed assets / CIP (Phase C) — PARTIALLY BUILT, gap named but not yet resolved (carried forward, not re-solved here).** The three-bucket structure (A = existing book/§471 CIP cost; B = additional §263A allocated on top; C = §263A(f) interest on top of that) IS the book-vs-required mechanic the owner described, already spec'd. Its one open hole, unchanged by this pass: whether a specific cost (e.g., engineering/design labor) is already reflected in bucket A (the book CIP ledger) before bucket B's pool-allocation mechanism re-adds it — Phase C's own text and Gate 6's Q6.3 both already flag this as "needs a rule," routed to the review queue rather than silently double-counted. This remains the template for the new build items below, not a solved problem to copy verbatim.

**(3) §263A(f) interest (Phase D) — GAP, closed here.** Interest capitalization under ASC 835-20 is a common financial-statement practice — a taxpayer may already have SOME interest capitalized on its books before the tool computes the full tax-required traced/avoided-cost amount. **New requirement:** before posting Phase D's computed capitalized-interest figure to the Basis & Amortization Schedule, read any interest ALREADY reflected in the asset's book basis (a new `FixedAsset.book_capitalized_interest`/`CIPProject.book_capitalized_interest` field) and post only the DELTA (tax-required minus book-already-capitalized) as the incremental tax adjustment — analogous to Phase C's bucket A/B split, applied to interest specifically. If book-capitalized interest EXCEEDS the tax-required amount (possible under differing book/tax debt-tracing conventions), flag rather than silently create a negative posting.

**(4) Intangibles, transaction costs, start-up costs (Phase G) — GAP, closed here.** Before posting a newly-identified capitalizable intangible/transaction cost to `AmortizableItem`, check whether an existing intangible-basis record for the SAME asset/transaction already reflects some or all of it (most relevant for a taxpayer with its own book-level intangible-asset tracking, or a multi-year transaction where prior-year facilitative costs were already capitalized). New requirement: `IntangibleItem`/`TransactionCostItem` gain a `prior_capitalized_basis` field, checked before posting; only the delta posts as new.

**(5) R&E (Phase F) — GAP, closed here.** Some taxpayers capitalize R&E on their financial statements (GAAP capitalized software development costs, for example) even in years the tax rule would otherwise permit current expensing. New requirement: `REExpenditure` gains a `book_capitalized_amount` field; Phase F's engine compares the tax-required treatment (mandatory foreign-capitalize / elected domestic-capitalize / default domestic-expense) against this book figure and posts only the delta needed to reach the tax-required position, flagging any book/tax divergence rather than silently double- or under-posting.

**(6) §263(a)-mandatory tangible-property improvements (Gate 4/BAR) — the MOST CONSEQUENTIAL gap found, closed here.** Confirmed by audit: BAR-flagged (`§263(a) Mandatory`) lines currently have **no posting mechanism to any specific asset at all** — they land in a flat waterfall bucket total and stop, unlike every other phase's output. **New requirement:** every BAR-flagged TB line must resolve to a target `FixedAsset` (via the same cost-center/description-linking pattern Phase A already uses for `CIPProject.linked_asset_id` — extend it to a new `improvement_target_asset_id` resolvable from cost-center + a per-line override when the automatic match is ambiguous, per the existing review-queue/override pattern) and post to that asset's `AmortizableItem` record, adding to its basis (a betterment/restoration/adaptation increases the asset's basis and, typically, starts a new depreciation period for the improved component — flag this consequence for the interview/SME rather than silently assuming a single blended basis). Without this fix, a real building improvement capitalized under BAR has no asset-level basis record anywhere in the tool's output — a genuine, previously-undetected hole in the "allocate those costs to the assets" mandate.

**Build:** `compute_basis_reconciliation(profile, engagement) -> ...` as a shared helper Phases C/D/F/G and Gate 4's BAR routing all call before their final `AmortizableItem` posting — not five separately-reimplemented delta calculations. Tests: for each of (3)-(6), a fixture with a non-zero pre-existing book-capitalized amount, confirming only the delta posts (not the gross tax-required amount), plus a fixture with book-capitalized exceeding tax-required, confirming the flag fires rather than a silent negative posting.

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
- **`compute_tax_basis_tb(tb_lines, btd_schedule) -> List[TaxBasisTBLine]` — ADDED 2026-07-09, Runtime Pipeline Step 2.** Applies every `BookTaxDifference` to its source `TBLine`, re-rolls up by cost center/department, and returns a second, tax-basis trial balance structurally identical to the input TB (re-classifiable by the same `engine.py` classifier). Feeds a new **Tax-Basis TB tab**: book TB → BTD adjustments → tax-basis TB, department/cost-center subtotal rows. This is a MATERIALIZED deliverable, not the M-1 reconciliation note alone (that note stays too, as the explanation; this is the result). Every phase from Phase B onward classifies THIS output, not the raw input TB — a scope clarification, not a new classification pass (the classifier itself doesn't change).

Backward compatible: existing `read_trial_balance`/`analyze`/`generate` keep working; `EngagementData` is additive.

---

## Phase B — Inventory: MSPM & SRM

Refactor `compute_unicap` into a dispatcher on `profile.method` (`"SPM"` keeps the existing body renamed `compute_spm`).

**GAP added 2026-07-09 full-text pass — the regulation's §471-cost definition is financial-statement-based, and the
classifier's tier assignment is only a proxy for it.** §1.263A-1(d)(2)(i): a taxpayer's §471 costs are "the types of
costs, other than interest, that a taxpayer capitalizes to property produced or property acquired for resale IN ITS
FINANCIAL STATEMENT" (at tax amounts), with one mandatory override — (d)(2)(ii): ALL direct costs (direct material,
direct labor, acquisition costs) must be in §471 costs "whether or not" book-capitalized. This is the same
book-conformity principle COR-C-023 stated for Phase C's bucket A, now confirmed as the GENERAL §471/additional-263A
boundary for the inventory engines too: which indirect costs sit in the §471 pool (ratio denominators) versus the
additional-§263A pool (ratio numerators) legally depends on the taxpayer's book capitalization, not on a
keyword-assigned tier. The classifier's `§471 Cost` / `Additional §263A` tiers encode a TYPICAL book treatment;
Phase B needs (a) a documented input-contract statement that the tier split must be reviewed against the taxpayer's
actual financial-statement capitalization, and (b) a per-line override mechanism (the existing review-queue/override
pattern suffices) rather than a silent assumption. Also documented, not built (each is an elective method of
accounting a real taxpayer may already be on, and the tool should FLAG rather than silently mis-model them):
(d)(2)(iii) the alternative method (book amounts as §471 costs, with book-to-tax differences pushed into additional
§263A costs); (d)(2)(iv) the 5% de minimis rules for uncapitalized direct labor/direct material costs (moved into
additional §263A costs); (d)(2)(v) the 5% variance/under-over-applied-burden safe harbor; (d)(3)(ii)(C)-(E) the
negative-adjustment restrictions (no negatives for cash/trade discounts; none for §162(c)/(e)/(f)/(g)-type amounts;
consistency requirement) — the (C) restriction interacts with the classifier's discount/rebate codes and belongs in
`compute_mspm`/`compute_srm`'s warning set when `include_negative_263a` is on.

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

# TWO DEFINITIONAL CONSTRAINTS ADDED 2026-07-09 (verified against §1.263A-2(c)(3)(ii)):
# 1. BOTH on-hand figures are limited to costs the taxpayer INCURS DURING THE CURRENT
#    TAXABLE YEAR that remain on hand at year end ((c)(3)(ii)(C)/(E)) — prior-year cost
#    layers in ending inventory are NOT part of either multiplicand. This is why the
#    negative-residual/on-hand cases below are data errors, not tax scenarios.
# 2. Per (c)(3)(ii)(F), every term above EXCLUDES costs described in §1.263A-1(e)(3)(ii)
#    and §1.471-3(e) cost reductions properly allocated entirely to property SOLD during
#    the year — a global input filter previously missing from this block.
```

**DECISION 2026-07-08 — rounding order, and negative-residual/negative-on-hand floors (found via synthetic-data stress test, `docs/TAX_DECISIONS.md` §8a):** a larger synthetic dataset than the regulation's own example surfaced two gaps the tiny example never had to resolve.
- **Rounding order:** round ONLY the two absorption ratios (`pre_production_ratio`, `production_ratio`) to 2 decimal places before multiplying — exactly what the regulation's own Example 1 demonstrates (see "Verification" below). Do NOT separately pre-round the SSCM pre-production/production split proportion that feeds into `pre_production_additional_263A` — carry it at full `Decimal` precision. This is an ADOPTED CONVENTION, not textually mandated (the regulation's own SSCM-split examples land on clean 25%/10% splits that don't actually test a rounding rule either way) — chosen because rounding an intermediate that only ever feeds another ratio's numerator would compound imprecision with no textual basis requiring it, and because it matches the "round only what the regulation's own worked example shows rounded" principle already used elsewhere in this plan.
- **Negative `residual_pre_production_263A` / negative `production_471_on_hand` — RATIONALE REWRITTEN 2026-07-09 (the floors stand; the reasoning behind them was wrong).** The 2026-07-08 rationale framed these as real tax scenarios the regulation is silent on ("a stock/balance figure, which can include prior-year carryforward"). That premise contradicts the regulation's own definitions: per §1.263A-2(c)(3)(ii)(C)/(E), BOTH on-hand figures are limited to current-year-incurred costs remaining on hand — prior-year carryforward is definitionally excluded, so `pre_production_471_on_hand ≤ pre_production_471` and `production_471_on_hand ≥ 0` hold structurally whenever the inputs comply with the reg's definitions. **Corrected framing: a negative residual or negative on-hand balance can only mean the INPUTS violate (c)(3)(ii)(C)/(E)** (e.g. a raw balance-sheet ending-inventory figure containing prior-year layers was supplied where a current-year-costs-on-hand figure was required). Keep the zero floors as guardrails (`MSPM-NEGATIVE-RESIDUAL-FLOORED` / `MSPM-NEGATIVE-ON-HAND-BALANCE`), but the warning text must say the actual thing: "input inconsistent with §1.263A-2(c)(3)(ii)(C)/(E) — on-hand figures must be current-year-incurred costs remaining on hand, not raw inventory balances." And the engine's input contract must DOCUMENT that requirement, not just clamp when it's breached — feeding raw balance-sheet stock into these fields would be a material error even when no negative fires.

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
Implement as `EntityProfile.mspm_mixed_split_method: Literal["direct_material", "labor"]` and
`EntityProfile.mspm_90pct_split_election: bool` (field name ADDED 2026-07-09 — a Phase-E
completeness pass found this election described in prose but never assigned a field, so Gate
2's Q2.7 had nothing concrete to `maps_to`).

- **Negatives + $50M rule (VERIFIED, §1.263A-1(d)(3)(ii)(B), see "Where we start"):** SPM excludes negative §263A when gross receipts exceed $50M (already implemented as `LARGE_PRODUCER_THRESHOLD` compared against the EXISTING `EntityProfile.avg_gross_receipts` field — reuse both, don't recreate or duplicate); **MSPM and SRM allow negatives with NO size restriction** (verified: (B)(2)/(B)(3) list MSPM/SRM with no dollar threshold, unlike (B)(1)'s SPM $50M cap). **Corrected 2026-07-08:** an earlier draft of this bullet both said the $50M comparison was "already implemented" AND instructed "add `avg_gross_receipts_prior3`" as a new field in the same sentence — self-contradictory. Resolution: `EntityProfile.avg_gross_receipts` already exists and already feeds the SPM $50M comparison; do NOT add a second, differently-named gross-receipts field for that comparison. Only add `include_negative_263a: bool` as new. If a true 3-year-rolling-average (as opposed to whatever single-year/period figure `avg_gross_receipts` currently represents) turns out to be needed for precision, that's a migration of the EXISTING field's computation, not an additional field living alongside it.
- **HAR election (VERIFIED, §1.263A-2(c)(4); four refinements ADDED 2026-07-09):** requires 3+ consecutive prior years on MSPM with actual (not historic) ratios; frozen pre-production AND production historic ratios (or a combined ratio for LIFO) used for a 5-year qualifying period; recompute in the "recomputation year" (the first year after the qualifying period). Refinements from the primary text a prior draft got wrong or omitted: (1) on a PASSING recomputation, the extension covers **the recomputation year AND the following five taxable years** (six more HAR years, not "extend 5 more"); (2) for non-LIFO taxpayers the ±0.5-percentage-point test is conjunctive — **BOTH** ratios must be within the band; either one outside fails the test; (3) after a failed test, using actual ratios is not open-ended — the taxpayer **must resume** HAR based on the updated test period **in the third taxable year following the recomputation year**; (4) HAR is **not available** to a taxpayer deemed to have zero additional §263A costs under the (c)(3)(v)/$200K de minimis rule — gate `har_election` on that check, since this plan implements both. Fields: `har_election`, `har_preprod_ratio`, `har_production_ratio`, `har_qualifying_year_index`.
- **De minimis for producers with ≤$200,000 total indirect costs (VERIFIED, §1.263A-2(b)(3)(iv), applies to MSPM via (c)(3)(v)):** additional §263A costs deemed zero — a real, cheap early-out worth implementing regardless of Phase B's other complexity. Two sub-rules ADDED 2026-07-09: taxpayers may exclude indirect-cost categories they are not required to capitalize when measuring the $200,000 ((b)(3)(iv)(A) second sentence), and related-party/aggregation rules apply to the test ((b)(3)(iv)(B)) — the $200K is not tested entity-by-entity for related groups.
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

# THREE DEFINITIONAL CONSTRAINTS ADDED 2026-07-09 (verified against §1.263A-3(d)(3)(i)):
# 1. `current_year_471_costs` is the reg's "current year's PURCHASES" — §471 costs incurred on
#    purchases of property acquired for resale during the year ((d)(3)(i)(D)(2)/(E)) — not an
#    undifferentiated all-§471 total. For a pure reseller they coincide; when SRM is used by an
#    (a)(4)(ii)/(iii) reseller with permitted production, (a)(4)(iv) governs how production
#    costs fold in — RESOLVED 2026-07-09 full-text pass (paragraph now retrieved): such a
#    taxpayer "must capitalize all costs allocable to eligible property produced USING THE
#    SIMPLIFIED RESALE METHOD" — i.e., the de-minimis/private-label production costs flow
#    through the SAME SRM formula (eligible property per (d)(2) includes the §1.263A-2(b)(2)
#    produced property in that case), not through a parallel SPM computation.
#    Two more 2026-07-09 full-text additions to this constraint set:
#    - LIFO: the S&H ratio DENOMINATOR's beginning-inventory term is stated at LIFO CARRYING
#      VALUE, not current-year dollars ((d)(3)(i)(D)(2) last sentence).
#    - The property-sold cost exclusion's exact pinpoints are (d)(3)(i)(C)(3), (D)(3), and
#      (E)(3) (a §9-era location flag, now closed).
# 2. `ending_inventory_471` (the multiplier) is the reg's "§471 costs remaining on hand at year
#    end" ((d)(3)(i)(C)(2)): §471 costs the taxpayer incurs DURING THE CURRENT YEAR that remain
#    on hand — NOT the undivided ending-inventory balance. Prior-year cost layers (FIFO with
#    declining volumes, etc.) are excluded; for LIFO, (C)(2) itself says the multiplier is the
#    current-year INCREMENT stated in §471 costs (consistent with the LIFO section below).
# 3. Permissible variations ((d)(3)(iii)) exist and the engine must not hard-reject them:
#    (A) a taxpayer MAY exclude beginning inventory from the S&H denominator; (B) a LIFO
#    taxpayer MAY multiply the S&H ratio by TOTAL ending-inventory §471 costs instead of the
#    increment. The "assert beginning inventory is in the S&H denominator" check below must be
#    conditional on variation (A) not being elected (add `srm_variation_a`/`srm_variation_b`
#    flags), not an unconditional invariant as a prior draft implied.
# NAMING DISAMBIGUATION ADDED 2026-07-09 (Phase-E completeness pass found Gate 3's bare word
# "purchases" ambiguous between two distinct declared fields): `current_year_471_costs` is the
# formula's PURCHASING-RATIO DENOMINATOR — the reg's "current year's purchases" ((d)(3)(i)(D)(2));
# `purchasing_costs` is a SEPARATE field — the purchasing-DEPARTMENT COST POOL that is the
# purchasing-ratio NUMERATOR. Both are real, distinct dollar figures the interview must ask for
# separately; do not let one question answer both.
```
Both denominators re-checked term-for-term against Practice Unit COR-P-021 Step 6 (`docs/TAX_DECISIONS.md` §7e):
CONFIRMED exactly as written — the purchasing-ratio denominator omits beginning inventory, the storage-and-handling
denominator includes it. This is the single most safety-critical formula in this section — **the claim that it is
"the #1"/"most common" reseller audit error is this plan's own characterization, RE-FLAGGED 2026-07-08 as still
UNCONFIRMED: no sentence in the retrieved Practice Unit text ranks or names audit-error frequency.** The underlying
mechanic (beginning inventory belongs in the S&H denominator only) is confirmed; the superlative framing around it
is not, and should not be repeated as if it were a sourced fact. Treat any future change to the formula itself with
the same re-verification rigor regardless of how the error is ranked.
**DECISION 2026-07-08 — four SRM gaps closed via synthetic-data stress test (`docs/TAX_DECISIONS.md` §8b), each RE-VERIFIED against retrieved §1.263A-3 text 2026-07-09 (`docs/TAX_DECISIONS.md` §9) — two confirmed, two revised:**
- **On-site vs. off-site definition — CONFIRMED 2026-07-09, flag closed, with the load-bearing sub-definitions added:** per (c)(5)(i), storage costs are capitalizable to the extent attributable to an OFF-SITE storage/warehousing facility; costs of an ON-SITE facility are not required to be capitalized. On-site facility ((c)(5)(ii)(A)) = "physically attached to, and an integral part of, a retail sales facility"; "integral part" ((c)(5)(ii)(C)) = essential and indispensable to the retail facility (e.g. used exclusively for filling orders/completing sales there). Two sub-definitions the tool's facility classifier needs, previously missing: a "retail sales facility" is one where the taxpayer sells merchandise EXCLUSIVELY to retail customers in on-site sales (exclusivity matters), and "on-site sales" are sales to customers PHYSICALLY PRESENT at the facility — mail-order/catalog sales are expressly not on-site. **Full-text pass additions 2026-07-09:** the off-site definition ((c)(5)(ii)(F)) is confirmed and is purely RESIDUAL — "a storage facility that is not an on-site storage facility" (so the classifier needs only the on-site test; everything else is off-site/capitalizable). "Retail customer" ((c)(5)(ii)(E)) = the FINAL purchaser (not a reseller/contractor/manufacturer-incorporator), and a non-retail customer is TREATED as retail only if all four (E)(2) conditions hold: same terms as retail (no special discounts), same manner (no advance orders; must come to the facility), retail customers shop routinely with no reserved non-retail days/hours, and >50% of the facility's gross sales are retail. A wholesale warehouse where customers buy in person but resell fails this ((c)(5)(v) Example 3 — all storage costs capitalizable).
- **Multi-facility combination — stands as adopted (reg confirmed SILENT):** targeted retrieval found no aggregation provision anywhere in (c)(5)/(d); every operative sentence is per-facility. Per-facility determination of each facility's capitalizable share, then dollar-sum into the single numerator. Keep the SME-override flag.
- **Write-down exclusion — RE-CITED 2026-07-09 (WRONG-CITATION found): the "goods valued below cost" exclusion is NOT in the regulation's (d)(3)(i)(C)(2) text.** The actual (C)(2) defines the multiplier as current-year-incurred §471 costs remaining on hand (see the formula-block constraints above) and contains no below-cost sentence. The below-cost exclusion is **Practice Unit COR-P-021's gloss interpreting (C)(2)** ("do not include goods that the taxpayer valued below cost"). Keep the rule (an IRS audit-position source is worth following) but cite it as "COR-P-021, interpreting §1.263A-3(d)(3)(i)(C)(2)" — not as regulation text. The adopted scope (multiplier only, not the ratio denominators) is SUPPORTED: both the PU sentence and (C)(2) speak solely to the on-hand multiplier, and the denominators are defined by separate terms ((D)/(E)). The candidate-SME-override flag can narrow to just the below-cost gloss's authority level.
- **90/10 threshold basis — DECISION REVERSED 2026-07-09 full-text pass (supersedes both the §8b adoption and the §9 rationale revision):** with the complete (c)(5)(iii) text now in hand, the sales-ratio-collapse reading is correct and the "independent cost-attribution measure" reading is abandoned. (c)(5)(iii)(B) states that a dual-function facility's storage costs "MUST be allocated between the off-site storage function and the on-site storage function USING THE RATIO of gross on-site sales of the facility to total gross sales of the facility" — the sales ratio is the regulation's exclusive, mandatory mechanism for attributing costs to the two functions. (C)'s threshold ("if 90 percent or more of the costs of a facility are attributable to the on-site storage function...") therefore can only be measured by the (B) allocation itself; the 90/10 deeming operates as a rounding rule ON the (B) result (≥90% on-site by sales ratio → treat 100% on-site; ≤10% → treat 100% off-site). Implement as: compute the (B) sales ratio for every dual-function facility first (after the (c)(5)(iii)(B)(3)/(c)(5)(iv) carve-out of costs not attributable to the storage function at all — e.g., an attached sales office); apply the (C) deeming to that ratio; no time-study/square-footage input is needed or permitted for this test. The §8 synthetic test's Facility A scenario (an "independent cost study showing 91.5% on-site") is superseded — its fixture must be restated with a sales-ratio-based threshold before `test_mspm_srm.py`/SRM tests are built.
- Assert beginning inventory is in the S&H denominator only, never the purchasing denominator — **conditional on permissible variation (d)(3)(iii)(A) not being elected** (see the formula-block constraints above; an unconditional assert would hard-fail a taxpayer validly electing the variation).
- **1/3–2/3 purchasing-labor** rule (§1.263A-3(c)(3)(ii)(A), pinpoint CONFIRMED 2026-07-09) — election; two nuances added from the primary text: the election is **all-or-nothing across all dual-role personnel** (if elected, it must be applied to every person performing both purchasing and non-purchasing activities), and the middle band still requires judgment even under the election: <1/3 purchasing → 0% allocated, >2/3 → 100%, but **between 1/3 and 2/3 the taxpayer must reasonably allocate** — the election eliminates the endpoints, not the middle. If not elected at all, reasonably allocate throughout.
- **Handling-cost exclusions — ADDED 2026-07-09 full-text pass (§1.263A-3(c)(4), previously absent from this plan entirely):** handling costs (processing/assembling/repackaging/transporting) are generally capitalizable, but the regulation carves out, and the `storage_handling_costs` input must therefore EXCLUDE: (1) handling at a RETAIL SALES FACILITY for property sold to retail customers there ((c)(4)(i) — unloading/unpacking/marking/tagging at the store is deductible); (2) handling at a DUAL-FUNCTION facility to the extent attributable to on-site sales, determined by the SAME (c)(5)(iii)(B) sales ratio used for storage costs ((c)(4)(i) last sentences); (3) DISTRIBUTION costs — transportation outside a storage facility delivering goods to a customer, with anything on a loading dock deemed outside the facility ((c)(4)(vi)(A); EXCEPTION: delivery to a §267(b)/§707(b) related person is not excluded — those costs go into the sold goods' basis); (4) delivery of CUSTOM-ORDERED items from storage to a retail facility against a pre-existing identifiable customer order ((c)(4)(vi)(B), four-factor test); and (5) PICK-AND-PACK activities inside a storage facility — moving, packing, and staging specific goods for imminent shipment against a placed order ((c)(4)(vi)(C)) — but NOT the inbound activities (unloading, quantity/quality checking, receiving documents, moving to storage location, storing), and NOT occupancy costs (rent/depreciation/utilities of the facility), which stay capitalizable. Capitalizable transportation ((c)(4)(v)): vendor→taxpayer, storage→storage, storage→retail, retail→storage, retail→retail. Classifier impact: the `resale` treatment codes for freight/handling lines need enough cost-center/keyword signal to route store-level handling and outbound-delivery lines OUT of the S&H pool — flag as a taxonomy review item, not just an engine note.
- **90/10 dual-function storage** rule — citation mapping RE-TIGHTENED 2026-07-09: the 90/10 deeming is
  §1.263A-3(c)(5)(iii)(C) (confirmed verbatim, both directions). The **allocation ratio formula** sits specifically at
  **(c)(5)(iii)(B)** (a prior fix cited it one level up, at "(c)(5)(iii)" — imprecise, not wrong): *"the ratio of gross
  on-site sales of the facility (i.e., gross sales of the facility made to retail customers visiting the premises in
  person and purchasing merchandise stored therein) to total gross sales of the facility"*, with the dual-function
  facility defined at (c)(5)(ii)(G) (confirmed). "Total gross sales" for this ratio **includes the value of items the
  taxpayer ships to its OTHER facilities** (confirmed verbatim 2026-07-09) — a builder computing the denominator from
  external sales alone would understate it.
- **Method-availability gate (RE-VERIFIED against retrieved primary §1.263A-3(a) text 2026-07-09 — one citation
  corrected, the open modeling question RESOLVED, the private-label inference CONFIRMED):**
  - de minimis production activity, incident to resale, by a SMALL reseller → **not required** to capitalize
    additional §263A costs at all. **Corrected 2026-07-09: the prior "(§1.263A-3(a)(5))" cite was wrong — (a)(5) is
    the DEFINITION of de minimis production activities (facts-and-circumstances plus the 10%/10% presumption), not
    itself a not-required-to-capitalize rule.** The not-required outcome appears in (a)(5)'s own small-reseller
    example, and the distinguishing axis is TAXPAYER SIZE (see the resolution bullet below).
  - **de minimis production activity, capitalization of resale+production costs is REQUIRED** (§1.263A-3(a)(4)(ii))
    → **may use SPM or SRM** — with a previously-missing conjunctive condition from the primary text: the production
    activities must be de minimis **and incident to the taxpayer's resale of personal property described in
    §1221(1)** (inventory/held-for-sale property). Add `production_incident_to_resale: bool`.
  - **OPEN QUESTION RESOLVED 2026-07-09 (was: "what distinguishes the (a)(5) not-required scenario from the
    (a)(4)(ii) required scenario?"):** the primary text resolves it — **taxpayer size**. The current-text
    not-required route is the §263A(i)/§448(c) small-business-taxpayer exemption at (a)(2)(ii) (cross-referencing
    §1.263A-1(j)), already modeled in `EntityProfile`. A reseller too large for that exemption, with a
    de-minimis/incident-to-resale production profile, must capitalize but may use SRM (or SPM/MSPM) under
    (a)(4)(ii). **Do NOT add a fourth `production_activity_level` state — gate on the existing
    `small_business_exempt` machinery plus the new `production_incident_to_resale` flag.** **Caveat CLOSED
    2026-07-09 full-text pass:** the current (a)(2)/(a)(5) text confirms the mapping exactly — (a)(2)(ii) is the
    small-business exemption, and the current (a)(5)(iii) example (Taxpayer N, a grocery chain OVER the §448(c)
    threshold with a 5%-receipts/3%-labor bakery operation) holds N's production de minimis and permits SRM under
    (a)(4)(ii); the pre-TCJA $10M small-reseller machinery is gone from the current text. Two definitional details
    added: the 10%/10% de minimis test is a PRESUMPTION inside a facts-and-circumstances test that also weighs
    production volume ((a)(5)(i)), and its gross-receipts measure is the §1.448-2(c) definition applied at the
    TRADE-OR-BUSINESS level, not the aggregated single-employer level ((a)(5)(ii)) — a different scope than the
    §448(c) exemption test itself.
  - **more than de minimis** production activity → **required** to capitalize resale+production costs, and **may
    use SPM or MSPM but NOT SRM** — **citation CORRECTED 2026-07-09: the SRM bar lives at (a)(4)(i)**; per the full
    text (2026-07-09 pass) the paragraph reads: *"Except as provided in paragraphs (a)(4)(ii) and (iii) of this
    section, a taxpayer may elect the simplified production method, as described in § 1.263A-2(b), or the modified
    simplified production method, as described in § 1.263A-2(c), but may not elect the simplified resale method...
    if the taxpayer is engaged in both production and resale activities"* — a prior draft omitted the MSPM option
    from the permitted side. The substance stands: hard `method_conflict` on SRM, not a soft warning; SPM and MSPM
    both remain available.
  - **private-label goods** exception ((a)(4)(iii)) — **UPGRADED from "plausible but unconfirmed" to CONFIRMED
    2026-07-09:** (a)(4)(i) literally opens "Except as provided in paragraphs (a)(4)(ii) and (iii)," so the
    "carves back out of the bar" framing is the regulation's own structure, not just this plan's inference. Three
    conditions from the primary text to attach to the `private_label_goods` gate (the reg never says "private
    label" — that's the Practice Unit's label): property produced under contract with an UNRELATED person
    (§267(b)/§707(b)), the contract entered into INCIDENT TO the reseller's resale activities, and the property
    SOLD TO ITS CUSTOMERS.
  - Implement as `EntityProfile.production_activity_level: Literal["none", "de_minimis", "more_than_de_minimis"]`
    + `EntityProfile.private_label_goods: bool` + `EntityProfile.production_incident_to_resale: bool`;
    `compute_srm` raises `method_conflict=True` (hard, not a recommendation) when
    `production_activity_level == "more_than_de_minimis" and not private_label_goods`.
  - De minimis production activities test itself (§1.263A-3(a)(5)(i), pinpoint confirmed 2026-07-09): gross
    receipts from produced property <10% of total gross receipts AND production-allocable labor <10% of total
    labor. **Framing note added: this is a PRESUMPTION inside a facts-and-circumstances determination, not a
    bright-line test** — a pass should be labeled "presumed de minimis," and a fail does not automatically mean
    not-de-minimis.
- **Allocable mixed service costs per activity (purchasing / storage / handling) — RESOLVED 2026-07-09: the
  regulation itself prescribes the mechanism, at §1.263A-3(d)(3)(i)(F).** A 2026-07-08 note downgraded this to
  "NOT addressed in the source text retrieved so far"; the primary (d)(3)(i)(F) text (retrieved this pass) settles
  it: if MSC are allocated using a §1.263A-1(g)(4) method, no further determination is needed; **if the taxpayer
  uses SSCM, the MSC included in each ratio's numerator = (labor costs allocable to that particular activity —
  purchasing, storage, handling — excluding MSC labor) / (total trade-or-business labor costs, excluding MSC labor)
  × TOTAL mixed service costs.** Note the shape: (F) multiplies **total** MSC by each activity's labor ratio
  directly — it is a ONE-STEP allocation, NOT the two-step "SSCM-capitalize the pool first, then sub-split the
  capitalized amount" approximation the plan previously assumed. Implement (F) verbatim; the ratio numerators
  "must include the amount of allocable mixed service costs as described in paragraph (d)(3)(i)(F)."
- Worked test: 60k/2.0M=0.03 + 105k/2.4M=0.043750 = 0.073750 × 500k = **36,875** (arithmetic independently
  re-verified 2026-07-08; this remains a hand-built illustration, not a regulation- or Practice-Unit-sourced
  example — no such worked SRM example was found in the source material retrieved so far).

### LIFO
Apply current-year ratio to the new layer on increments; on a **decrement**, release the liquidated layers' prior §263A to COGS (don't apply current ratio to liquidated qty — per §1.263A-2(b)(3)(iii)(C), decrement's released §263A = layer's additional §263A × (decrement ÷ layer's §471 costs), confirmed 2026-07-09 full-text pass). `inventory_method`, `lifo_layers` fields; fallback = single-layer approximation + REVIEW flag. **MSPM+LIFO mechanics ADDED 2026-07-09 full-text pass (§1.263A-2(c)(3)(iv)):** MSPM under LIFO does NOT apply the two ratios separately to an increment — the increment (stated in §471 costs, current-year dollars) is multiplied by a single **combined absorption ratio** = total additional §263A costs allocable to eligible property on hand at year end, determined on a NON-LIFO basis, ÷ total (pre-production + production) §471 costs on hand at year end, determined on a non-LIFO basis (the regulation's own Example 3: 9.48% = $284,400 ÷ $3,000,000 on the Taxpayer P facts, applied to a $1,500,000 increment → $142,200). The MSPM engine therefore always runs its full non-LIFO computation first, then collapses to the combined ratio for the LIFO layer. (The MSPM HAR under LIFO likewise uses a combined historic absorption ratio, (c)(4)(iii).) **Added 2026-07-09:** for SRM+LIFO, §1.263A-3(d)(3)(i)(C)(2) itself states the multiplier is the current-year increment stated in §471 costs (consistent with the above), and permissible variation (d)(3)(iii)(B) lets a LIFO taxpayer instead multiply the S&H ratio by total ending-inventory §471 costs — support via the `srm_variation_b` flag rather than rejecting. Also note §1.263A-7's ordering rule for an engagement changing LIFO and §263A methods in the same year (a §263A method change is generally deemed to occur first, with a LIFO-discontinuation exception) — see the method-change bullet in "Deferred / out of scope."

New `EntityProfile` fields (**consolidated 2026-07-08 — a prior version of this list omitted three fields proposed
earlier in this same phase, which is fixed here; extended 2026-07-09 with the regulation-review additions**):
`beginning_inventory_471`, `ending_inventory_471_preprod/_prod`,
`ending_inventory_471` (for SRM — **definition corrected 2026-07-09: NOT the undivided ending-§471 balance** but the
(d)(3)(i)(C)(2) "§471 costs remaining on hand at year end" = current-year-incurred costs remaining on hand (LIFO:
the current-year increment) — see the SRM formula-block constraints; the MSPM on-hand fields carry the analogous
§1.263A-2(c)(3)(ii)(C)/(E) current-year-incurred definition), `current_year_471_costs` (= the reg's "current year's
purchases" for SRM — see the same constraints), `purchasing_costs`, `storage_handling_costs`,
`production_gross_receipts`, `include_negative_263a`,
`inventory_method`, `lifo_layers`, HAR fields (`har_election`, `har_preprod_ratio`, `har_production_ratio`,
`har_qualifying_year_index`), `mspm_mixed_split_method`, `production_activity_level`, `private_label_goods` (these
last three were each proposed in the MSPM/SRM subsections above but missing from this consolidated list before).
**Added 2026-07-09** (each introduced in the sections above/below this list): `production_incident_to_resale`
(the (a)(4)(ii) conjunctive condition), `srm_variation_a`/`srm_variation_b` ((d)(3)(iii) permissible variations),
`is_tax_shelter` (§448(a)(3) bar on the small-business exemption — ALREADY IMPLEMENTED in `analysis.py` 2026-07-09,
not Phase B work), and `prior_year_method`/`is_first_263a_year` (the §1.263A-7 method-change trigger — see
"Deferred / out of scope").
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
  check the asset against the §1.263A-1(h)(2) eligibility test via a new `SelfConstructedAsset.sscm_eligible: bool`
  (or equivalent derived check). TEST SHAPE CORRECTED 2026-07-09: eligibility is (C) OR (D) — two ALTERNATIVE
  routes, not one conjunctive test as a prior draft had it. Route (C): substantially identical in nature to, and
  produced in the same manner as, inventory the taxpayer produces (or other held-for-sale property). Route (D):
  produced on a routine and repetitive basis — numerous substantially identical assets, standardized
  designs/assembly-line techniques, AND (≤3-yr §168(c) recovery period OR a material/supply consumed within 3
  years). See the SSCM section's corrected (h)(2) bullet. If eligible under NEITHER — the expected case for
  most Phase C targets per the SSCM section's own analysis — the tool must NOT silently apply the SSCM ratio.**
  Since the correct fallback (the general §1.263A-1(g)(4) direct-reallocation/step-allocation method) is itself
  declared out of scope in the SSCM section, the honest interim behavior is: apply the SSCM ratio ONLY when
  `sscm_eligible` is true; otherwise, warn/flag the asset (`SSCM-INELIGIBLE-NO-FALLBACK` or similar) and require a
  human override rather than silently computing a number using a method the regulation doesn't actually permit for
  that asset. This is a real scope decision, not a cosmetic fix — building the general method is future work; NOT
  silently mis-applying SSCM in the meantime is required now.
  **DECISION 2026-07-08 — mixed-eligibility pools (found via synthetic-data stress test, `docs/TAX_DECISIONS.md`
  §8c, the single most consequential gap this pass found): what happens when ONE mixed-service pool's target set
  contains BOTH SSCM-eligible and SSCM-ineligible assets?** The existing worked test below assumed uniform
  eligibility and never had to answer this. Two orderings are each internally consistent with the eligibility-gate
  rule above but diverge by tens of thousands of dollars on identical facts (confirmed in testing): (A) apply the
  SSCM ratio to the WHOLE pool first, then driver-split only the resulting capitalizable dollars across the
  eligible assets alone — this silently reroutes an ineligible asset's implied share of the pool onto a DIFFERENT,
  eligible asset sharing the same pool, overstating the eligible asset's basis and dropping the ineligible asset's
  entirely; vs. (B) driver-split the FULL pool across every declared target first — every asset assigned to the
  pool, plus `NON_PRODUCTION` — preserving the general allocation formula's own literal target set (`{assets…,
  NON_PRODUCTION}`) and the pool's total-dollar conservation invariant, THEN gate each asset's own resulting dollar
  share through the SSCM eligibility test. **ADOPTED: Option (B).** Rationale: Option (A) has no basis in either
  the general allocation formula (which names every asset sharing the pool, not just the eligible ones, as a
  member of the target set) or in COR-C-023 — reallocating one asset's cost onto another asset entirely because the
  first is SSCM-ineligible is not a "reasonable allocation method," it's a basis-shifting error. Under (B): an
  eligible asset's own driver-share gets the normal SSCM capitalizable/deductible split; an ineligible asset's own
  driver-share is computed and stays visible in the allocation audit trail, but is NOT booked to bucket B — flagged
  `SSCM-INELIGIBLE-NO-FALLBACK`, pending the general method being built (per the interim-behavior rule above).
  Restated: `share(t) = driver_value(t) / Σ driver_value` is computed once, across the pool's FULL target set,
  before the eligibility gate is ever applied — the gate operates on each target's resulting SHARE, not on the
  pool's total dollars or its target set. This is an explicit SME-level policy call, not a re-derivation of settled
  law where the text was silent — flagged as such and open to override.
- **90% de minimis rule — RE-CORRECTED 2026-07-09 (the 2026-07-08 "one-sided only" correction was itself wrong;
  see the SSCM section's re-corrected (g)(4)(ii) bullet and `docs/TAX_DECISIONS.md` §9).** The primary (g)(4)(ii)
  text contains BOTH sides, asymmetrically: ≥90%-deductible → the taxpayer MAY ELECT zero allocation (elective);
  ≥90%-capitalizable → the taxpayer MUST allocate 100% to the benefitted production/resale activity (mandatory).
  The 2026-07-08 draft declared the capitalizable side unconfirmed because COR-C-023 states only the deductible
  side — a false negative from verifying against a secondary source's silence. (Refined 2026-07-09 full-text pass:
  the mandatory side operates "under this election" — it binds only a taxpayer that has MADE the all-departments
  (g)(4)(ii) election; see the SSCM section's refined bullet for the implementation shape.) What REMAINS correct
  from the earlier correction, and still matters for this section: **(g)(4)(ii) is a DEPARTMENT-level rule — it is
  not a shortcut applicable to per-asset, N-way driver shares.** Do not apply either side of it per-asset; apply it (when
  built) at the mixed-service-department level, before pool allocation. (MSPM's SSCM-split de minimis at
  §1.263A-2(c)(3)(iii)(C) remains a separate, genuinely-elective two-bucket provision — unchanged.)
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
- Worked test — **RESTATED 2026-07-09 in the ADOPTED Option-(B) ordering (a review pass found the prior statement
  "100k @ SSCM 0.60 split by headcount (45k/15k)" demonstrated the REJECTED ratio-first ordering — the numbers
  coincide under uniform eligibility, but an implementer copying the fixture as written would code Option (A)):**
  two assets, both SSCM-eligible, plus a NON_PRODUCTION target with driver value 0 for simplicity. Mixed HR pool
  $100k, driver = headcount → driver-split FIRST across the full target set: asset1 75k / asset2 25k; THEN gate each
  share (both eligible) and apply SSCM 0.60 per share: asset1 45k / asset2 15k. Building-dep pool $50k (indirect,
  not mixed-service — no SSCM step) by sq ft: 10k/40k. Result: asset1 +55k, asset2 +55k additional §263A
  (conservation on the capitalizable amounts: 45k+15k=60k = 100k×0.60; 10k+40k=50k; totals unchanged from the prior
  statement of this fixture — only the ORDER of operations is restated). Guardrail test (HR-by-machine-hours
  blocks); degenerate test (Σ driver=0). A real fixture should also include one SSCM-INELIGIBLE asset sharing the
  HR pool to exercise the gate (its driver-share computed, flagged, NOT booked to B — per the DECISION above).
- Rebuild the Asset Basis Schedule tab to **per-asset**: `original book basis + §263A indirect + §263A mixed + §263A(f) interest = adjusted basis` (live formula), regime rollup + tie-check retained.

---

## Phase D — §263A(f) interest capitalization (the hardest engine)

New `engines/interest.py`, `compute_263Af(result, profile)`, called after `compute_unicap`.

**1. Designated-property identification** (Reg §1.263A-8(b)), first match wins — CONFIRMED 2026-07-08 against
the primary text of 26 CFR §1.263A-8 itself (retrieved directly; see `docs/TAX_DECISIONS.md` §7e), superseding
the earlier Practice-Unit-only confirmation:
- real property → designated (Category 1);
- TPP with class life ≥ 20 yrs (Cat 2), **but ONLY IF the property is not property described in §1221(1) — old
  numbering, today §1221(a)(1): INVENTORY / stock in trade / property held primarily for sale to customers — in the
  hands of the taxpayer or a related person** (§1.263A-8(b)(1)(ii)(A)). **CORRECTED 2026-07-09 — the 2026-07-08
  version of this carve-out misread the eCFR's "1221(l)" rendering as a Code subsection "§1221(l)" (which does not
  exist; §1221 has only (a)/(b)) and glossed it as "the patent/invention-sale capital-gain provision." It is a
  digit-1→letter-l rendering artifact (the same retrieved section renders "(b)(l)(ii)(A)" where (b)(1)(ii) is
  unambiguously meant, and the rule dates to T.D. 8584 (1994), when §1221 ran (1)-(5) with no letters). The
  practical target is NOT patent holders — it is the common case of a producer whose 20+-year-class-life product IS
  its inventory (aircraft, vessels built for sale): such property escapes Cat 2 and is tested only under Cat 3/4.
  Implement as a per-unit `held_for_sale_by_taxpayer_or_related_person` input, not a patents flag. Note the
  rendering artifact here so a future verifier doesn't re-chase "§1221(l)". Cross-evidence added 2026-07-09
  full-text pass: the authoritative eCFR text supplied in-session still renders "section 1221(l)" at
  §1.263A-8(b)(1)(ii)(A) — while §1.263A-3(a)(1) and (a)(4)(ii), in the same document, repeatedly use "section
  1221(1)" unambiguously in the inventory/held-for-resale sense; the inventory reading stands.** OR est.
  production period > 2 yrs (Cat 3) OR (> 1 yr AND cost > $1M) (Cat 4).
- ~~de minimis screen: TPP with cost ≤ $1M **and** period ≤ 2 yrs → not designated~~ — **DELETED as a rule
  2026-07-09: no such "screen" exists in the regulation; TPP non-designation follows solely from failing all of
  (b)(1)(ii)(A)-(C), whose exact complement is "period ≤ 2 yrs AND (period ≤ 1 yr OR cost ≤ $1M)" — the prior
  conjunctive shorthand missed the period-≤1yr-but-cost->$1M case (also not designated), and if run BEFORE the
  Cat-2 test it would wrongly de-designate long-lived TPP with small cost/short period. No-match → not designated
  is the correct default; don't call anything here "de minimis" (in the reg that term is exclusively (b)(4)).**
  `NEEDS-CLASSLIFE` flag when only MACRS recovery period (not class life) is available. **ADDED 2026-07-09
  (§1.263A-8(b)(2)(iii)):** the Cat-3/4 production-period and total-cost ESTIMATES must be made at the start of
  production, kept in contemporaneous written records, and are respected if reasonable — and the estimated total
  cost of production for these tests EXCLUDES producing-asset bases and hypothetical interest (the same exclusions
  the plan previously applied only to the (b)(4) test). Add `estimate_date`/`estimate_documented` inputs.
- **Excluded property (§1.263A-8(b)(3), missing from the plan entirely until now; phrasing RE-CONFIRMED verbatim
  2026-07-09 — a review pass suspected the timber wording was garbled; it is not, the reg really says "more than 6
  years old when severed from the roots"):** designated property does NOT include (i) timber and evergreen trees
  that are more than 6 years old when severed from the roots, or (ii) property the taxpayer produces for use OTHER
  than in a trade or business or an activity conducted for profit (e.g., personal-use property). Implement as an
  early-out check alongside the (b)(4) de minimis rule, before the Category 1-4 tests.
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
  that, when set, forces debt tracing off for §263A(f) purposes — a derived gate, e.g. `tracing_allowed = not
  interest_afr_plus_3_election` (**wording fixed 2026-07-09: a prior draft said the election "forces
  `include_negative_263a`-style debt-tracing off," reading as if it toggled that unrelated Phase B negatives flag;
  the intended meaning was only "a hard off-switch, in the same spirit as other profile-driven gates"**) — gated on
  a `avg_gross_receipts_3yr_10m_test` helper (renamed from an earlier draft's `avg_gross_receipts_10yr_test`, which
  mis-described a 3-year-average/$10M test as a "10-year" test; distinct from the §448(c) small-business
  test already in `EntityProfile`). **Second eligibility route ADDED 2026-07-09 (§1.263A-9(e)(2), last sentence,
  added by T.D. 9942):** a taxpayer is ALSO an eligible taxpayer if it is a small business taxpayer under
  §1.263A-1(j) — an independent OR-route the `avg_gross_receipts_3yr_10m_test` helper alone doesn't capture.
  Edge-relevant only (a §448(c)-meeting taxpayer is generally exempt from §263A entirely), but model it as
  `eligible = avg_gross_receipts_3yr_10m_test OR small_business_exempt` rather than the $10M test alone.
- **Election not to trace debt (§1.263A-9(d)) — ADDED 2026-07-09 full-text pass, previously absent from this plan:**
  separate from (and available to taxpayers ineligible for) AFR-plus-3, ANY taxpayer may elect not to trace debt at
  all: every item of eligible debt is treated as nontraced, so each unit's entire computation runs through the
  average-excess-expenditures × WAIR mechanic (the engine's Unit-2/zero-traced-debt path, already spec'd and
  stress-tested in §8d). Two details: the taxpayer MAY fold otherwise-excluded non-interest-bearing debt (accounts
  payable) into eligible debt under this election if it would have been traced debt but for the election ((d)(1)
  second-to-last sentence — this LOWERS the WAIR by adding zero-interest principal to the denominator); and the
  election is a method of accounting (change requires consent). Implement as
  `EntityProfile.interest_no_tracing_election: bool` — a genuine simplification path that skips the §1.163-8T
  tracing input entirely; distinct from AFR-plus-3, which additionally replaces the WAIR with an external rate.
- **15-day repayment rule detail (§1.263A-9(g)(7)), refined 2026-07-09:** confirmed verbatim, with one correction to
  the prior description — the election "may be made or discontinued for any computation period and is NOT a method
  of accounting" (no consent needed; a per-period toggle).
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
  taxpayer improperly suspend capitalization for an ordinary weather delay. **Two sub-rules ADDED 2026-07-09 if this
  is ever built:** (g)(2) — for a cessation spanning taxable years, suspension starts from the first measurement
  period of the year in which the 120-day threshold is satisfied; (g)(3) — the suspension election is a METHOD OF
  ACCOUNTING that must be applied consistently to all qualifying units, not a per-project choice.
- **Related-person aggregation (§1.263A-8(b)(2)(ii), §1.263A-12(b), both pinpoints RE-CONFIRMED 2026-07-09 — GAP,
  not yet spec'd):** activities
  and costs of a person RELATED to the taxpayer (§267(b)/§707(b), per §1.263A-8(a)(4)(i)) must be taken into account
  both in applying the designated-property classification thresholds (per -12(b), specifically the (b)(1)(ii)(B)/(C)
  production-period tests — Category 2 is touched by related persons via the §1221(1) carve-out's "hands of... a
  related person" language and the general (b)(2)(ii) rule) and in determining the taxpayer's own
  production period — regardless of whether the related person is performing a mere service or producing a
  component the related person must itself separately treat as designated property. **Flip side ADDED 2026-07-09
  (§1.263A-11(g)):** related-person ACTIVITIES count for classification/production-period purposes, but only costs
  incurred by THE TAXPAYER enter the taxpayer's own APE. `DebtInstrument.related_party`
  (already in the Phase D data contract below) covers related-party DEBT exclusions only; it does not yet cover
  this separate related-person COST/ACTIVITY aggregation requirement for classification and production-period
  purposes. Needs a `related_person_activities`/`related_person_costs` input on the CIP-detail schedule before this
  can be built correctly for any taxpayer using related-party contractors or affiliates.

**2. Production period** (Reg §1.263A-12): start = first physical activity (real) / 5%-of-total-cost (TPP, including
planning/design expenditures in the 5% test, determined without regard to whether physical activity has started).
**Added 2026-07-09 full-text pass:** for property produced UNDER CONTRACT the start rules have customer/contractor
variants — real property: contractor starts when the CONTRACTOR begins physical activity, customer starts when
EITHER party begins physical activity (§1.263A-12(c)(2)); TPP: contractor's 5% test uses the contractor's own
expenditures WITHOUT reduction for customer payments, customer's 5% test uses the customer's expenditures, with a
further election at §1.263A-8(d)(2)(iv)(A) to start when contractor+customer expenditures combined hit 5%. Also
added: for property customarily AGED before sale (tobacco, wine, whiskey), the production period INCLUDES the aging
period (§1.263A-12(d)(1) last sentence) — inventory designated property for such taxpayers keeps accruing
capitalizable interest through aging, a real industry-specific mechanic previously absent from this plan.
**End — CORRECTED 2026-07-08, was understated as simply "ready for intended use (PIS)":** per §1.263A-12(d)(1), the
production period ends only when the unit is placed in service (or ready to be held for sale) **AND** all production
activities reasonably expected to be undertaken by/for the taxpayer or a related person are actually completed —
the regulation's own example (a homebuilder who paints/finishes interiors only once a buyer is found) explicitly
holds that the production period does NOT end at PIS/marketing-ready if further production activity is still
expected. Implement as: PIS date alone is NOT sufficient to stop interest capitalization; the CIP-detail schedule
needs an explicit `production_complete` flag/date distinct from `placed_in_service_date`, and capitalization runs
until the LATER of the two (mirroring §1.263A-12(d)(3)'s point that a single unit undergoing sequential internal
stages doesn't end its production period until ALL stages finish, even though *separate* units — e.g. two wings of
a building, each their own unit of property — end independently as each is completed). **Mid-year start/completion
handling — CORRECTED 2026-07-09: a prior draft said "prorate the sub-period by active days," which CONTRADICTS the
regulation's convention.** §1.263A-9(f)(1)(iii): the avoided cost method applies on the basis of a FULL computation
period regardless of whether the production period begins or ends inside it; §1.263A-9(f)(2)(iii): a unit's APE is
taken into account from the first measurement date following the production period's start through the first
measurement date following its end — and the regulation's own examples handle partial-year units with ZERO ENTRIES
on out-of-period measurement dates (e.g. a unit ending June 16 averages [400k+600k+0+0]÷4), never by day-fraction
proration. Implement exactly that: zero snapshots outside the production period, always divide by the total number
of measurement dates in the computation period. (The corrected worked table below already implicitly follows this
convention — the prose sentence was the error.)

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
                 the day immediately following that period's end, so it's part of APE for every later snapshot).
                 # APE COMPOSITION EXPANDED 2026-07-09 (§1.263A-11, previously under-spec'd): APE also includes
                 # (d) the adjusted bases (or apportioned portion, e.g. by machine-hours/mileage) of equipment/
                 #     facilities USED in a reasonably proximate manner to produce the unit during any measurement
                 #     period in which so used — the reg's own bulldozer example; moves real dollars; previously
                 #     appearing in this plan ONLY as an exclusion from the -8(b)(4) test, never as an APE input;
                 # (b)(1) costs capitalized BEFORE the production period begins (e.g. raw land) — they enter APE
                 #     on day one of the production period, not when incurred;
                 # (b)(2) the dedication rule for materials, and (h) installation costs.
                 # The CIP-detail data contract below needs producing-asset basis + usage-apportionment inputs.
traced_debt_d  = eligible debt actually allocated (under the §1.163-8T tracing rules) to this unit's APE as of date d
                 — this is a TRACING determination, not `min(APE_d, principal)`; in the common case where a loan's
                 full proceeds funded this unit and APE_d exceeds the loan's principal at every date, traced_debt_d
                 equals the full principal at every date, but tracing can also produce a SMALLER traced amount at an
                 EARLIER date than a later one (see the regulation's own Property D/E example, §1.263A-9(c)(5)(i)(B)).
                 # DEFINITION PINPOINT + COMPONENT ADDED 2026-07-09: traced debt is defined at §1.263A-9(b)(2) (the
                 # (c)(5) cites govern NONtraced debt), and per (b)(2)'s last sentence traced debt ALSO includes
                 # unpaid interest previously capitalized w.r.t. the unit that is included in APE on the measurement
                 # date — a component the prior draft omitted.
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
# WAIR FALLBACK ADDED 2026-07-09 (§1.263A-9(c)(5)(iii)(D), previously missing — the formula above divides by zero
# for a taxpayer with NO nontraced debt outstanding during the computation period): in that case, WAIR = the
# highest applicable Federal rate under §1274(d) in effect during the computation period (plus a contingent-rate
# rule for debt with contingent interest). Implement the guard, don't let the division fault or silently zero.
excess_expenditure_amount = average_excess_expenditures * WAIR_nontraced

unit_capitalized = traced_interest_period + excess_expenditure_amount

# Cap — CORRECTED: §1.263A-9(c)(1) applies the pro-rata cap ONLY to the excess-expenditure (avoided-cost) pool
# across all of a taxpayer's units, NOT to the combined traced+avoided total. Traced-debt interest is always fully
# capitalized based on actual interest incurred on the traced debt; it is never part of this proration.
# PRORATION-SHARE NOTE ADDED 2026-07-09: (c)(7)(i)(B) prorates by each unit's AVERAGE EXCESS EXPENDITURES share,
# while the line below prorates by excess-AMOUNT share — mathematically identical because WAIR is one
# taxpayer-level rate (it cancels), but cite/implement per (c)(7) if per-unit rates ever diverge. (c)(7)(i)(A)
# also computes the prorable total "including deferred interest" — the (c)(4)/(g)(2) deferral machinery is wholly
# out of scope in this plan (see the ordering-rules bullet below), which is a scoping choice, stated explicitly.
if Σ (excess_expenditure_amount across all units) > total_interest_available_for_capitalization:
    # total_interest_available = nontraced-debt interest + certain below-AFR related-party borrowings (§1.263A-9(a)(4)(iii))
    #   + partnership guaranteed payments for use of capital (§1.263A-9(c)(2)(iii), §707(c)) — see sourcing order below
    each unit's excess_expenditure_amount *= total_interest_available_for_capitalization
                                              / Σ (excess_expenditure_amount across all units)
    flag PRORATED
total = Σ units (traced_interest_period + each unit's possibly-prorated excess_expenditure_amount)

# DECISION 2026-07-08 (docs/TAX_DECISIONS.md §8d): per-SOURCE consumption tracking, additive to the above, not a
# replacement. A synthetic-data stress test found an apparent conflict between this pseudocode (a flat sum of all
# 3 sources into one `total_interest_available_for_capitalization` scalar, prorated as one pool) and the sourcing-
# order prose below (nontraced -> below-AFR related-party -> guaranteed payments, "in this order, and only up to"
# what's needed). RESOLVED: these are not actually in conflict — they answer two different questions. The units-
# level total capitalized $ and the per-unit proration (both computed above) depend ONLY on the scalar total of all
# 3 sources combined, and are correct as written regardless of source order (confirmed independently in testing:
# when the pool is fully exhausted, as it is whenever proration fires at all, every dollar of all 3 sources gets
# consumed regardless of order, so order cannot change the total or the per-unit split in that case). What the
# sourcing-order rule actually governs is a SEPARATE, additional output this pseudocode was missing: how much of
# EACH of the 3 sources gets treated as "consumed" by capitalization (as opposed to remaining ordinary deductible
# interest, relevant to the §163(j)/§266/§469/§861 ordering already flagged below). Compute this as a strict
# sequential draw-down AFTER the total/per-unit math above: consumed_nontraced = min(nontraced_interest,
# Σ excess_expenditure_amount); remaining = Σ excess_expenditure_amount - consumed_nontraced; consumed_below_afr =
# min(below_afr_interest, remaining); remaining -= consumed_below_afr; consumed_guaranteed_payments =
# min(guaranteed_payments, remaining). Each source's UNCONSUMED remainder (nontraced_interest - consumed_nontraced,
# etc.) stays ordinary deductible interest, available to other Code sections in the ordering below. This only
# produces a different-looking number from a flat consumption assumption when the pool is NOT fully exhausted
# (Σ excess_expenditure_amount < total_interest_available_for_capitalization) — the case this plan's own worked
# test doesn't exercise, since it deliberately tests the proration branch.
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
  types — **note added 2026-07-09: this intra-step ordering layers a second sequencing dimension onto the per-source
  consumption DECISION in the pseudocode above; the sequential draw-down there must respect it within each source.**
  Conversely, certain "deferral provisions" (§163(e)(3), §267, §446, §461 — **plus, per (g)(1)(ii)'s residual
  clause, ALL other deferral/limitation provisions not listed in (g)(1)(i)**) are applied BEFORE §263A(f) — the
  opposite ordering — meaning interest deferred under one of those sections is capitalized only in the year it would
  otherwise become deductible (and interest NOT capitalized after §263A(f) runs is never retroactively capitalized
  later). This interacts materially with §163(j) in particular for any leveraged real-estate or
  production project; not addressed anywhere in this plan's data model today. Flag as a required build item before
  Phase D can be relied on for a taxpayer subject to the §163(j) limitation, not a stretch goal. **Scoping statement
  added 2026-07-09: the (c)(4)/(g)(2) deferral-amount/shortfall/substitute-capitalization machinery is wholly OUT OF
  SCOPE for this plan — an explicit scoping choice, stated here so its absence reads as deliberate, not overlooked.**
- Data contract: FixedAsset (type, class_life, cost, PIS date), CIP detail (cumulative expenditure PER MEASUREMENT
  DATE — snapshots, not just open/close pairs — production start, `production_complete` flag/date per the corrected
  production-period-end rule above, total est. cost, `is_improvement`, mid-production-purchase price per §1.263A-11(f)
  — this field was previously described only in prose below and never actually added to this data contract list,
  which is the fix), Debt (principal, rate, interest_incurred, `traced_to`, `related_party`, plus enough detail to
  derive `is_eligible_debt` per the exclusions above). Legacy scalar APE×rate stub retained as fallback when
  schedules are empty.
- **Unit of property / common features (§1.263A-10) — GAP added 2026-07-09 full-text pass; this plan previously
  treated the unit determination as a bare input assumption (each CIP project = one unit).** The regulation's own
  rules materially move dollars for any real-estate developer: a unit of REAL property = all functionally
  interdependent components PLUS an allocable share of any COMMON FEATURE (streets, sidewalks, pools, clubhouses —
  real property benefitting the units and not separately income-producing), and starting production on a common
  feature STARTS the production period for every benefitted unit ((b)(1)). Offsetting timing relief in (b)(5) that a
  naive per-project model would miss in BOTH directions: land attributable to a benefitted property stays OUT of APE
  until direct production activity starts on that property ((b)(5)(ii)(A)); a benefitted property whose only work
  was clearing/grading can drop back out after 120 days of direct-activity cessation even while common-feature work
  continues ((b)(5)(ii)(B)); a COMPLETED, placed-in-service common feature drops out of the units' APE
  ((b)(5)(iii)); a unit SOLD before the common feature completes ends its production period at sale, and
  common-feature costs incurred after the sale never enter it ((b)(5)(iv)); a benefitted property placed in service
  before the common feature completes drops its own costs out while the unfinished common-feature share stays in
  ((b)(5)(v)). Separately-income-producing property (e.g. a convenience store serving a condo project) is NOT a
  common feature — it is its own unit ((b)(6) Ex. 4). TPP units use functional interdependence / customarily-sold-
  as-single-unit ((c)); self-installed property aggregates production+installation ((d)). Data-contract impact: the
  CIP schedule needs `unit_id`, `is_common_feature`, `benefitted_unit_ids`/allocation weights, and per-property
  direct-activity start/cessation dates — without them the engine cannot implement (b)(5) and must conservatively
  treat every project as a standalone unit with a warning.
- **Property produced under contract — APE payment rules (§1.263A-11(c)) — GAP added 2026-07-09 full-text pass:**
  for designated property produced under contract, the CUSTOMER's APE includes cumulative contract PAYMENTS (plus
  incurred-but-unpaid amounts where §461 is satisfied ahead of payment, plus the customer's own capitalizable
  costs); the CONTRACTOR's APE is REDUCED by cumulative customer payments. Neither mechanic is in the data contract
  above — a developer using a general contractor (the common case) needs a contract-payments-by-measurement-date
  input, and a taxpayer that IS a contractor needs customer-receipts-by-date. Related: §1.263A-11(b)(1) also adds a
  phase-completion rule (land/common-feature costs allocated to COMPLETED units are never REALLOCATED to incomplete
  units) and (b)(2) the materials dedication rule (raw materials enter APE when dedicated — first specifically
  associated with a unit by record, job-site assignment, or incorporation; components/subassemblies enter during
  their own production).
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
  golden fixture. This table is the corrected literal fixture for `test_interest.py`. **Fixture completion note
  added 2026-07-09: as stated, the fixture gives WAIR = 1/14 without the underlying nontraced principal/interest,
  so the (c)(2) cap ("not in excess of...") and the per-source consumption DECISION can't be exercised from it.
  Add explicit nontraced-pool inputs — e.g. average nontraced debt $2,800,000 with $200,000 nontraced interest
  incurred (= 1/14 exactly), which also satisfies the cap ($200,000 ≥ $196,428.57) so the excess amount is fully
  sourced from nontraced interest with $3,571.43 left deductible.**
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
    de-minimis and repair-carve-out checks, not just a flag. **THIRD GATE ADDED 2026-07-09 — the compression above
    skipped (d)(3)(iii): an improvement to TANGIBLE PERSONAL PROPERTY the taxpayer has NOT treated as designated
    property is designated-property production only if the improvement INDEPENDENTLY meets the (b)(1)(ii)
    classification thresholds** (class-life/production-period/cost tests applied to the improvement itself).
    Without this gate, `is_improvement` over-captures routine improvements to ordinary machinery. Real-property
    improvements are unaffected ((d)(3)(ii) — no independent-threshold requirement).
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
  - **The "associated property rule eliminated" claim is TRUE — RESTORED 2026-07-09 (the 2026-07-08 instruction
    to "drop that claim" was itself the error).** The PRE-T.D.-10034 §1.263A-11(e)(1)(ii)(B) — retrieved this pass
    from a pre-amendment (Feb 2025) snapshot — expressly defined "associated property": the adjusted basis of any
    existing structure, common feature, or other property NOT placed in service or temporarily withdrawn from
    service to complete the improvement, with a 5% de minimis at old (e)(2). T.D. 10034's rewrite of (e) removed
    it entirely (corroborated by the Federal Register's own description of the final rules). The 2026-07-08 pass
    searched only the CURRENT text — where the rule no longer exists precisely BECAUSE it was eliminated — and
    concluded the claim was a hallucination; searching the current text for a repealed rule can only ever produce
    that false negative. Implication for the tool: for tax years beginning ON OR BEFORE Oct 2, 2025, the OLD (e)
    (associated-property + allocable-land-cost mechanics) still governs improvements — a dual-regime `is_improvement`
    path keyed on tax year, previously thought unnecessary. Flags `IMPROVEMENT-NARROWED-2025` (confirmed),
    `MID-PRODUCTION-PURCHASE` (new), `ASSOCIATED-PROPERTY-PRE-2025` (restored).
  - Lower-priority, noted but not yet spec'd: §1.263A-9(g)(7) 15-day repayment election (treat debt repaid within
    15 days before a quarterly measurement date as still outstanding on that date — prevents WAIR "mismatch"
    inflation) and §1.263A-9(g)(3) simplified inventory method (an alternative to per-unit avoided-cost tracking
    for inventory-only designated property, using inventory-age segmentation and a compounded interest factor per
    segment — a materially different algorithm from the per-unit method already spec'd above; treat as a
    stretch-goal alternative path, not a required build item).
- Outputs: a real **§263A(f) Interest tab** (per-unit 7-step APE worksheet in Practice-Unit format), the interest column of the Asset Basis Schedule, and the Summary `§263A(f) Interest` bucket (route *capitalized* interest to the bucket; incurred − capitalized stays deductible — document in the tie-check to avoid double count).

---

## Phase F — §174/§174A research & experimental expenditure capitalization (ADDED 2026-07-09)

**Scope addition, direct user request 2026-07-09:** the plan's title and scope were §263A-only; the user asked whether §263(a)/§266 were covered (yes, Gate 4/Gate 5) and whether §174 and §59(e) were (no — added here and in Phases G/H). This phase is fully SEPARATE from §263A: R&E costs are categorically EXCLUDED from the §263A additional-cost pool (§1.263A-1(e)(3)(ii), already reflected in `EX-RD`'s `Excluded` tier1) — §174/§174A is its own mandatory-and-elective capitalization regime running in parallel, not a UNICAP sub-rule.

**Mandatory vs. elective split (VERIFIED against concordant secondary sources — see `docs/TAX_DECISIONS.md` §13 for full sourcing; primary-text pull recommended before filing use, per that section's methodology note):**
- **Foreign research** (§174(a), as it stands after OBBBA carved domestic research out into new §174A): MANDATORY capitalization, amortized straight-line over **15 years**, mid-year convention (half a year's amortization in the first year regardless of when in the year the cost was incurred). No election out.
- **Domestic research** (new §174A(a), added by OBBBA/P.L. 119-21 §70302, effective for tax years beginning after 12/31/2024): DEFAULT is current-year expensing (full deduction, no amortization). **Elective alternative** (§174A(c)): the taxpayer may instead elect to capitalize and amortize domestic research ratably over **not less than 60 months**, taxpayer's choice of period ≥60 months — METHOD-OF-ACCOUNTING. This is the mechanic that also matters for Phase H: electing 60-month-plus capitalization here is a DIFFERENT thing from the §59(e) election (Phase H) to amortize over exactly 10 years to avoid an individual-AMT preference — a taxpayer could theoretically face both decisions on the same domestic-research dollar, and the tool must not conflate them (see Phase H's build note on this interaction).
- **Software development costs**: current guidance treats software development as "specified research or experimental expenditures" subject to the same §174/§174A domestic/foreign, mandatory/elective framework as other R&E — no separate regime. Flag rather than hard-code, since the exact scope line (e.g., routine debugging/maintenance vs. capitalizable development) is a facts-and-circumstances call per Notice 2023-63/Rev. Proc. 2024-9-era guidance that this plan has not independently verified against primary text.

**2022-2024 transition (VERIFIED at the structural level):** for the period between TCJA's original mandatory-capitalization effective date (tax years beginning after 12/31/2021) and OBBBA's 2025 restoration of domestic expensing, DOMESTIC research was mandatorily capitalized and amortized over 5 years (foreign stayed at 15 years, unaffected by OBBBA). OBBBA provides transition relief for those 2022-2024 domestic amounts still being amortized as of the 2025 changeover:
- **Catch-up election**: a taxpayer may deduct the entire remaining unamortized 2022-2024 domestic-R&E basis in ONE YEAR (2025) or SPREAD IT OVER TWO YEARS (2025-2026) — a real, material election affecting the current-year deductible total, not just a bookkeeping mechanic.
- **Small-business retroactive election**: taxpayers meeting the §448(c) gross-receipts test (Rev. Proc. 2025-28 sets the threshold at the historical $31M/2025 figure — cross-check against `EntityProfile.THRESHOLDS` for the applicable year, don't hard-code a second copy of the same number) may instead amend 2022-2024 returns entirely, retroactively applying current-expensing treatment as if OBBBA had always been in effect. Amended-return deadline: **July 6, 2026** (Rev. Proc. 2025-28) — a hard filing-window fact the interview must surface, not bury in a footnote, since it lapses.

**§174(d) disposal/retirement/abandonment (VERIFIED on the core rule and the foreign/domestic-expensed split; UNCERTAIN on one sub-case — flag, don't guess):** no loss deduction is allowed for unamortized capitalized R&E costs remaining in a disposed/retired/abandoned property's basis — the taxpayer must continue the amortization schedule as if the disposition never happened, rather than recognizing a §165 loss for the unamortized remainder.
- Currently-expensed domestic research under §174A's default: the rule has nothing to bite on — no capitalized basis remains once the cost was expensed, so it's moot for that category.
- Foreign research (still mandatorily capitalized under §174(a)): the rule squarely applies — confirmed.
- **UNCERTAIN, flag for SME/primary-text review before building**: whether the post-OBBBA §174(d) (amended by P.L. 119-21 §70302(b)(1)(C), effective for dispositions after May 12, 2025) still reaches domestic research the taxpayer elected to capitalize under §174A(c)'s ≥60-month alternative — secondary-source commentary frames the amended rule around "foreign research expenditures" specifically, which raises a real question the tool should not silently resolve either way. Build the disposal-loss-disallowance check for foreign R&E and elected-domestic-capitalization R&E identically for now (the conservative reading), with a `§174D-DOMESTIC-ELECTIVE-UNVERIFIED` warning flag on any disposal event touching elected-capitalization domestic R&E basis, rather than asserting the rule applies (or doesn't) with false confidence.
- **This tool tracks the amortization-continuation mechanic and flags disposal events touching R&E basis — it does NOT build a general §165 loss-computation engine.** Same scoping discipline as the rest of this plan: flag facts that feed a computation out of scope, don't silently absorb them into scope.

**Build:**
- `REExpenditure` schedule (input 6): per-project/cost-pool amount, domestic/foreign flag, tax year, and (for 2022-2024 layers still amortizing) original 5-year schedule start date.
- `compute_174(profile, re_expenditures) -> ...`: routes each item by domestic/foreign and the elected treatment; builds a 15-year (foreign) or ≥60-month (domestic-elected) amortization schedule with mid-year convention; computes the 2022-2024 catch-up deduction under whichever method was elected; emits `§174D-DOMESTIC-ELECTIVE-UNVERIFIED` and small-business-deadline warnings as applicable.
- New waterfall bucket `"§174 Capitalized"` (added to `CAPITALIZED_BUCKETS`/`BUCKETS` in `analysis.py`) for foreign-mandatory and domestic-elected-capitalization amounts; currently-expensed domestic research stays `"Deductible"` (as `EX-RD`/`EX-174AMORT` already route it — correct as-is for that one sub-case, per the "Taxonomy already has partial coverage" note above).
- Posts each capitalized R&E item to the shared `AmortizableItem`/Basis & Amortization Schedule (see Architecture above), not a bespoke R&E-only ledger — this is the "allocate to assets" mechanic the user asked for, generalized rather than duplicated across Phases C/F/G/H.
- Outputs: an **R&E Amortization tab** (domestic/foreign split, 2022-2024 catch-up detail, 15-yr/≥60-mo schedules) feeding the shared Basis & Amortization Schedule and the new `§174 Capitalized` waterfall bucket.

---

## Phase G — §1.263(a)-4/-5 intangibles, transaction costs, and start-up/organizational costs (ADDED 2026-07-09)

**Scope addition, same trigger as Phase F.** The existing Gate 4/§1.263(a)-1/-3 coverage in this plan is the TANGIBLE-property repair regs only. §1.263(a)-4 (intangibles) and §1.263(a)-5 (transaction costs facilitating an acquisition/reorganization/capital transaction) are a separate, equally-mandatory §263(a) regime this plan never covered — closing that gap is the point of this phase. §195/§248/§709 (start-up and organizational costs) are doctrinally adjacent (the same INDOPCO future-benefit lineage) though technically their own Code sections, not §263(a) itself; grouped here because the existing taxonomy already groups them under one `§263(a) Transaction/Intangible` tier1 and they share the "capitalize, then amortize over a fixed statutory period" shape.

**§1.263(a)-4 — created/acquired intangibles (VERIFIED at the mechanics level — see `docs/TAX_DECISIONS.md` §13):**
- **12-month rule ((f))**: no capitalization required for a right/benefit that does not extend beyond the **EARLIER OF** (a) 12 months after the taxpayer first realizes the right/benefit, or (b) the end of the taxable year following the year of payment. Both prongs must independently hold — it is the more restrictive of the two dates that governs, not the more permissive ("later of" is a documented common drafting error this plan is explicitly avoiding).
- **$5,000 facilitative-cost de minimis ((e)(4)) — a CLIFF, not a per-dollar exclusion, and NOT the same $5,000 already in this plan's Gate 4.1**: amounts (other than employee compensation, overhead, and commissions — commissions are categorically excluded from this de minimis regardless of amount) paid to investigate/pursue a transaction that facilitates acquiring/creating an intangible are treated as non-facilitative (currently deductible) IF their aggregate does not exceed $5,000 per transaction. If the aggregate EXCEEDS $5,000, the ENTIRE amount becomes capitalizable — there is no "$5,000 exempt, excess capitalized" partial relief. Separately, a taxpayer may ELECT to treat employee compensation/overhead/de-minimis-eligible costs AS facilitative (voluntarily capitalize) per transaction — the inverse of the usual safe-harbor shape. **This is legally and mechanically distinct from `EntityProfile.de_minimis_ceiling`/Gate 4.1's $5,000-AFS/$2,500-non-AFS tangible-property safe harbor** — same dollar figure, unrelated provisions, do not let one `EntityProfile` field or one interview answer serve both.
- **Categories requiring capitalization (confirmed at the policy level; exact subparagraph citations flagged UNCERTAIN — see `docs/TAX_DECISIONS.md` §13, verify against full eCFR text before citing a specific letter in a workpaper)**: financial interests (equity/debt instruments, forward contracts, options); contract rights (leases, licenses, service contracts, and payments to induce another party to enter/renew/renegotiate an agreement); memberships and privileges (trade/business league, professional-organization dues to obtain the membership itself, not ongoing dues); certain governmental rights (trademarks, trade names, copyrights, licenses, permits, franchises from a government agency); certain benefits from real property transfers (easements, life estates, mineral interests, timber rights, zoning variances, rights of first refusal); and a residual catch-all — broader for ACQUIRED intangibles ("any other intangible acquired from another person") than for CREATED intangibles (only future benefits the IRS/Treasury identify in SUBSEQUENT PUBLISHED GUIDANCE — a narrower, guidance-dependent residual, not a general catch-all; the tool should not silently capitalize a "some other future benefit" created-intangible cost absent an identified authority).
- **Routing**: an intangible acquired as part of acquiring a trade or business generally becomes a §197 intangible (15-year straight-line amortization, anti-churning rules apply — already in this plan's "Related regimes" authority list, `authority_databases/cost_capitalization.py` lines 377-390). An intangible NOT acquired with a business, or a created (not acquired) intangible, is capitalized under §1.263(a)-4 but is NOT automatically a §197 intangible — its amortization period (if any) depends on the specific asset (a fixed contract term, an indefinite life with no amortization until disposal, etc.) — flag for SME determination per item rather than defaulting to a period.

**§1.263(a)-5 — transaction/facilitative costs (already has a working Phase-1 classifier + authority base to build on — `financial_tools/transaction_costs/`, confirmed reusable 2026-07-09; NEEDS ADAPTATION, not built from scratch):**
- Reuse `transaction_costs/technical_authority/authorities/transaction_cost_authorities.py` (covered-transactions list, inherently-facilitative-costs list, the bright-line-date rule, the §1.263(a)-5(g) employee-compensation carve-out, Rev. Proc. 2011-29's success-based-fee safe harbor, Rev. Rul. 73-580 abandoned-transaction treatment) as the authority source — it is already solid and should not be re-derived.
- Reuse `transaction_costs/phase1/ten_k_analyzer.py`'s `TransactionCostAnalyzer._classify_costs()` rule shape (inherently-facilitative cost TYPES — investment banking/regulatory/financing/due-diligence → capitalize; legal → allocate; integration → deduct; non-facilitative → deduct under §162) as the starting classification logic for cap263a's own engine, adapted from that tool's 10-K/public-data Phase-1 scope to cap263a's engagement-level per-transaction scope.
- **Build what that tool flagged as its own unbuilt Phase 2 roadmap items** (confirmed still unbuilt 2026-07-09): the bright-line-date field/logic (investigatory costs before the bright-line date are generally deductible unless inherently facilitative; costs after are capitalized) and the Rev. Proc. 2011-29 success-based-fee 70/30 election (in lieu of documenting the non-facilitative portion of a success-based fee in a covered transaction, elect to treat 70% as deductible and capitalize 30% — irrevocable, per-transaction).
- Routing: capitalized transaction costs attach to whatever they facilitate — an asset acquisition's facilitative costs add to the acquired asset's basis (post to the shared `AmortizableItem`); a stock/debt issuance's costs amortize under their own rules (debt issuance costs: Treas. Reg. §1.446-5, already in the reused authority file); a taxable trade-or-business acquisition's capitalized costs generally become part of acquired goodwill/going-concern value (§197, 15-year). An ABANDONED transaction's capitalized-to-date costs become a deductible loss (Rev. Rul. 73-580) — flag, don't silently leave stranded in a capitalized bucket.

**§195/§248/§709 — start-up and organizational costs (authority text already correct and reusable; the $5,000/180-month computation itself is unbuilt anywhere in the repo — confirmed 2026-07-09):**
- Mechanic: **$5,000 immediate deduction** in the year the trade or business begins, **phased out dollar-for-dollar** for total start-up/organizational costs above **$50,000** (fully phased out at $55,000) — a real cliff-adjacent computation the tool must actually run, not just describe. The remainder (after the $5,000/phase-out) amortizes **straight-line over 180 months**, beginning with the month the active trade or business begins.
- **Partnership SYNDICATION costs (§709(b) fees to promote/sell partnership interests) are PERMANENTLY CAPITALIZED — no $5,000 deduction, no 180-month amortization, no deduction ever except on complete liquidation of the partnership.** This is a real trap (the existing `SEC195-STARTUP` code's keyword list includes `"syndication"` alongside `"start-up"`/`"organizational cost"` with NO distinction in treatment) — the engine must route syndication costs to a separate no-amortization bucket, not the same $5,000/180-month schedule as genuine start-up/organizational costs.
- Corporate organizational costs (§248) and partnership organizational costs (§709(a), non-syndication) follow the same $5,000/$50,000/180-month mechanic as §195 start-up costs; distinguish only for the syndication carve-out and for entity-type-appropriate election language (Gate 0's `entity_type` already available).

**Build:**
- `IntangibleItem` and `TransactionCostItem` schedules (input 7): per-item facts (covered-transaction flag, inherently-facilitative flag, bright-line date, facilitative-cost aggregate for the $5,000 (e)(4) test, 12-month-rule dates, intangible category, §197-eligibility flag) plus a `StartupOrgCostPool` (aggregate start-up/organizational total, business-commencement date, syndication flag).
- `compute_263a4_5(profile, intangibles, transaction_costs, startup_pools) -> ...`: applies the 12-month rule; the (e)(4) cliff test; the bright-line-date/inherently-facilitative classification (adapted from `transaction_costs/`); the success-fee 70/30 election when made; the $5,000/$50,000-phase-out/180-month start-up computation; routes syndication costs to permanent non-amortization; routes §197-eligible intangibles to 15-year amortization and other capitalized intangibles to per-item SME-flagged treatment.
- **Refines, not replaces, the existing `"§263(a) Mandatory"` bucket**: `bucket_of()`'s flat `if t == "§263(a) Transaction/Intangible": return "§263(a) Mandatory"` (analysis.py ~line 126) stays the top-level waterfall bucket (no waterfall/tie-check change needed), but each line additionally posts a typed row (intangible / transaction cost / start-up-org / syndication) to the shared Basis & Amortization Schedule with its own amortization treatment, rather than landing as an undifferentiated lump sum with no further computation, which is the actual gap being closed.
- Outputs: an **Intangibles & Transaction Costs tab** (per-item facilitative determination, 12-month-rule/de-minimis test results, success-fee election detail) and a **Start-up/Organizational Costs block** (the $5,000/phase-out computation, 180-month schedule, syndication flag) — both feeding the shared Basis & Amortization Schedule.

**Scope clarification, ADDED 2026-07-09 (a completeness sweep found this framing risk):** "§263(a)" in this plan's scope has meant, in practice, BAR/improvement rules (§1.263(a)-3, Gate 4) plus this phase's intangibles/transaction costs (§1.263(a)-4/-5). **Reg. §1.263(a)-2 — the general rule requiring capitalization of amounts paid to ACQUIRE OR PRODUCE a unit of real or personal property in the first place (invoice price, transaction costs, work performed before the property is placed in service)** — is a THIRD §1.263(a) regulation this plan has never separately named, even though its substance (inherently facilitative acquisition costs) is already touched on in this section and the SSCM section above. Day-one acquisition/construction cost capitalization for a NEW building or NEW equipment purchase is squarely §1.263(a)-2's job, not just BAR's (which governs improvements to property the taxpayer ALREADY owns). No new engine is needed — Gate 4/Phase G's existing mandatory-capitalize routing already reaches these costs functionally — but the plan's scope language and Gate 4's own framing should name §1.263(a)-2 explicitly so a reader doesn't read "§263(a) coverage" as BAR-only.

**§1060/Form 8594 — residual-method purchase price allocation for a taxable trade-or-business acquisition (ADDED 2026-07-09, new mechanic, distinct from this phase's facilitative-cost coverage above):** when a taxpayer ACQUIRES a trade or business (an asset acquisition, or a deemed asset acquisition under §338), the PURCHASE PRICE ITSELF — not just the acquirer's facilitative/transaction costs, which §1.263(a)-5 above already covers — must be allocated across seven statutory asset classes under the residual method (Reg. §1.1060-1(c), borrowing the §338 regs' waterfall): Class I cash; II actively-traded personal property; III accounts receivable/debt instruments; IV inventory; V all other tangible property (real AND personal); VI §197 intangibles other than goodwill/going concern; VII goodwill/going concern (the residual, last-in-line class). Both buyer and seller must report consistently on Form 8594. This is the primary basis-SETTING mechanic for an acquired business's assets across every asset category this tool targets (real property, tangible personal property, intangible property, inventory) and was entirely absent from this plan before this pass — confirmed by research: no existing repo code or authority file models the 7-class residual allocation itself (only the pre/post-acquisition facilitative-cost treatment, already in scope above).
- Build: `PurchasePriceAllocation` schedule (aggregate consideration + FMV estimates per class, entered per acquisition) feeding a `compute_1060_allocation(consideration, class_fmvs) -> per-class allocated basis`, applying the residual method (fill Classes I-VI up to FMV in order, Class VII absorbs whatever remains — including a negative-Class-VII-implied scenario, which must be flagged, not silently permitted, since aggregate consideration below the sum of Classes I-VI FMVs signals a data or valuation error). Each class's allocated basis posts to the corresponding `AmortizableItem`/inventory pool/§197 schedule — i.e., this mechanic is the entry point that SEEDS the basis Phases B/C/F/G/H then build on for a business acquired mid-stream, not a competing computation.
- Interview: a new question in Gate 9 (or a dedicated sub-tree) — was this an asset acquisition (or deemed asset acquisition) of a trade or business this year? If yes: aggregate consideration, per-class FMV estimates, Form 8594 consistency confirmation with the counterparty.
- Output: a **Purchase Price Allocation tab** (the 7-class table, each class's allocated basis, Form 8594 cross-reference).

**§280B — demolition of structures (ADDED 2026-07-09, small, well-defined mandatory rule):** when a taxpayer demolishes a structure, NO deduction is allowed for either the demolition cost or any loss on the structure's remaining basis — BOTH must be capitalized to the basis of the LAND on which the structure stood (Reg. §1.280B-1), with a casualty-triggered-demolition carve-out (Notice 90-21). This is not subsumed by BAR (which governs improvements to a structure that continues to exist) or by §263A production costs — it is its own narrow rule, routine in real-property redevelopment/CIP fact patterns squarely inside this tool's real-property/CIP scope. Build: a `demolition_event` flag on the relevant `FixedAsset`/CIP item, routing demolition cost + remaining undepreciated basis to the LAND `AmortizableItem` record (non-depreciable, since land has no recovery period) rather than to a deductible loss or to the (now-nonexistent) structure's own basis; flag the casualty exception for SME confirmation rather than auto-applying it.

---

## Phase H — §59(e) elective qualified-expenditure amortization (AMT-preference avoidance) (ADDED 2026-07-09)

**Scope addition, same trigger.** §59(e) lets a taxpayer ELECT straight-line amortization for certain "qualified expenditures" instead of the otherwise-available (faster) treatment, specifically to avoid having the difference treated as an AMT preference/adjustment item. This is a cross-cutting ELECTION layered on top of five distinct underlying Code provisions, not its own cost-classification tier — model it as an election overlay, not a sixth flat bucket.

**Qualified expenditures and periods (VERIFIED against Cornell LII text — see `docs/TAX_DECISIONS.md` §13):**

| Category | Underlying provision | §59(e) elective period | Taxonomy status |
|---|---|---|---|
| Circulation expenditures | §173 | 3 years | **No taxonomy code exists — build from scratch** |
| Domestic research & experimental | §174A(a) (NOT old §174(a) — see below) | 10 years | `EX-RD`/`EX-174AMORT` exist but don't model this election |
| Intangible drilling costs (IDC) | §263(c) | 60 months | **No taxonomy code exists — build from scratch** |
| Mining exploration expenditures | §617(a) | 10 years | **No taxonomy code exists — build from scratch** |
| Mining development expenditures | §616(a) | 10 years | **No taxonomy code exists — build from scratch** |

**Election mechanics:** item-by-item (any PORTION of a qualified expenditure may be elected, not an all-or-nothing entity-wide election), made by a statement attached to the original or amended return for the year amortization begins, IRREVOCABLE except by IRS consent in rare/unusual circumstances via letter ruling. `EntityProfile`/schedule shape: a list of `QualifiedExpenditureElection` records (category, amount, election year), not a single flag — same per-item pattern as the other new schedules in this phase set.

**CRITICAL gating fact this plan would have gotten wrong without verification (VERIFIED 2026-07-09, materially changes who should even be offered this election):**
- §59(e)(2)(B) was ITSELF amended by OBBBA to point at new **§174A(a)** (domestic R&E), not old §174(a) — table above reflects the current cite.
- The R&E prong of §59(e) is **NOT a dead/vestigial provision** for current-law purposes, though it genuinely was moot for 2022-2024 (when §174 already mandated capitalization at a pace equal to or slower than any AMT-required rate, leaving no "faster" write-off to create a preference). OBBBA's 2025 restoration of domestic-R&E current expensing under §174A REVIVED the preference: §56(b)(2) (as amended) now requires INDIVIDUAL (non-corporate) AMT taxpayers to capitalize/amortize over 10 years both foreign R&E and any domestic R&E expensed under §174A's default — reactivating exactly the situation §59(e)'s R&E election exists to pre-empt.
- **The CORPORATE alternative minimum tax was repealed by TCJA (2018) and NOT replaced by anything using §59(e)/§57 preference items.** The 2022 Inflation Reduction Act's Corporate Alternative Minimum Tax (CAMT, §55/§56A) is a structurally different regime — it starts from Adjusted Financial Statement Income (book income from the taxpayer's AFS) with its own closed adjustment list under §56A, not from regular taxable income plus §57 preferences. §59(e) has no bearing on CAMT liability. (Confidence: verified at the structural/mechanical level; not a direct primary-source quote stating this in so many words — see `docs/TAX_DECISIONS.md` §13 for the "verified-by-inference" flag.)
- **Build consequence: Gate 10 (below) must ask the taxpayer's entity type / AMT exposure FIRST and gate the whole election on it, not offer §59(e) uniformly.** A C-corp with no individual owners reporting K-1 preference items has no live use case for this election at all under current law; an individual, or a pass-through entity whose owners could face §55/§56/§57 individual AMT, does.
- **UNCERTAIN, flagged not guessed:** the exact §57(a) subparagraph for the mining exploration/development AMT preference (IDC's is confirmed at §57(a)(2); mining's numbered citation could not be confirmed against primary text this pass) — flag `§57-MINING-CITE-UNVERIFIED` rather than asserting a specific subparagraph.
- **Also uncertain:** whether the §59(e) election interacts with a §174A(c) domestic-research capitalization election on the SAME dollars (both are real, both produce multi-year amortization, but over different periods — 10 years under §59(e) vs. the taxpayer's chosen ≥60-month period under §174A(c)). This plan does not resolve which one governs if a taxpayer tries to make both; flag `§59E-174A-ELECTION-CONFLICT` and route to SME review rather than silently picking one.

**Build:**
- `QualifiedExpenditureElection` schedule (input 8) + `taxonomy/qualified_expenditure_periods.yaml` (the table above, as data, not hard-coded constants — mirrors the `sca_drivers.yaml` pattern).
- New taxonomy codes needed (none exist today, confirmed 2026-07-09): circulation expenditures, IDC (a distinct code from the existing generic §263(a)/§263A cost pools — IDC is oil & gas operator-specific and this plan has no oil & gas coverage at all today), mining exploration, mining development.
- `compute_59e(profile, elections) -> ...`: gates on the entity-type/AMT-exposure screen above; for each elected item, builds the category-appropriate straight-line schedule from `qualified_expenditure_periods.yaml`; posts to the shared Basis & Amortization Schedule; emits `§57-MINING-CITE-UNVERIFIED` and `§59E-174A-ELECTION-CONFLICT` warnings where applicable.
- **Explicitly out of scope: computing the taxpayer's overall AMT or CAMT liability.** This phase tracks the preference-avoidance AMORTIZATION ELECTION and its schedule — a real, dollar-moving computation — not the full AMT/CAMT return. Same scoping boundary this plan already applies elsewhere (e.g., §1.263A-7's revaluation/§481(a) computation is flagged, not built).
- Outputs: a **§59(e) Election Tracker tab** (per-category, per-item elections and their amortization schedules) feeding the shared Basis & Amortization Schedule.

---

## Elective Capitalization Menu — every election in this plan, in one place (ADDED 2026-07-09)

**Why this section exists:** the Runtime Pipeline's Step 5 needs a single, scannable list of every elective provision this plan covers — an audit confirmed none existed; the ~15+ elections were scattered across Phase B/C/D/F/G/H/Gate text with no consolidated view, and the document conflated conceptually different KINDS of election. This section is that list, and the taxonomy that keeps them distinct.

**Three kinds of election, not one — this distinction did not exist anywhere in the plan before this pass:**
- **(a) METHOD elections** — choose HOW a mandatory amount is computed; do not change what's ultimately required to be capitalized, just which formula produces the number. Getting this election "wrong" doesn't under- or over-capitalize, it just picks a different (still fully mandatory-compliant) computation path.
- **(b) ADD-ON elections** — voluntarily capitalize an amount that would otherwise be currently deductible, purely at the taxpayer's option. These are genuinely incremental Step-5 actions layered on top of the Step-3/4 mandatory floor.
- **(c) SAFE-HARBOR-OUT elections** — a specific, Congress/Treasury-authorized override that lets the taxpayer DEDUCT currently an amount Step 3's mandatory rules would otherwise require to be capitalized. The only category that legitimately reduces a Step-3/4 amount, and only because the safe harbor is itself part of the mandatory regime's own design (not a generic "taxpayer election beats mandatory law" principle).

| Election | Code cite | Kind | Mechanic |
|---|---|---|---|
| SPM / MSPM / SRM method choice | §1.263A-2/-3 | (a) | Which UNICAP absorption-ratio formula applies |
| SSCM ratio method (labor vs. production-cost) | §1.263A-1(h)(3)(ii) | (a) | Which SSCM allocation-ratio formula applies |
| MSPM SSCM-split method + 90% one-bucket election | §1.263A-2(c)(3)(iii)(B)/(C) | (a) | How the SSCM total splits between pre-production/production |
| (g)(4)(ii) 90% mixed-service-department election | §1.263A-1(g)(4)(ii) | (a) | Department-level shortcut inside the mandatory SSCM computation |
| Historic Absorption Ratio (HAR) | §1.263A-2(c)(4) | (a) | Uses a frozen historic ratio instead of recomputing annually — still fully mandatory-compliant |
| SRM permissible variations A/B; 1/3-2/3 purchasing-labor | §1.263A-3(d)(3)(iii) | (a) | Alternate SRM computation inputs |
| Negative §263A adjustments (MSPM/SRM/SPM≤$50M) | §1.263A-1(d)(3)(ii) | (a) | Whether negative adjustments are included in the mandatory computation |
| SSCM self-constructed-asset exclusion | §1.263A-1(h)(2)(ii) | (a) | Routes SCA mixed costs to the general (g)(4) method instead of SSCM |
| Tracing posture: trace / no-tracing (§1.263A-9(d)) / AFR-plus-3 | §1.263A-8/-9 | (a) | Which §263A(f) avoided-cost computation path applies |
| Computation period & measurement-date frequency | §1.263A-9(f) | (a) | Timing convention for the mandatory §263A(f) computation |
| Suspension election (120-day) | §1.263A-9(g) | (a) | Whether a temporary-cessation period pauses the mandatory computation |
| 15-day repayment election | §1.263A-9(g)(7) | (a) | A mandatory-computation timing convention, not incremental capitalization |
| §266 — unimproved/unproductive land | §1.266-1(b)(1)(i) | (b) | ADDS capitalization of otherwise-deductible taxes/carrying charges |
| §266 — development/construction real property | §1.266-1(b)(1)(ii) | (b) | ADDS capitalization of otherwise-deductible interest/taxes |
| §266 — personal property | §1.266-1(b)(1)(iii) | (b) | ADDS capitalization of otherwise-deductible carrying charges |
| §1.263(a)-3(n) — capitalize book-capitalized repairs | §1.263(a)-3(n) | (b) | ADDS capitalization of amounts otherwise deductible as repairs |
| §174A(c) — elect ≥60-month domestic R&E capitalization | §174A(c) | (b) | ADDS capitalization instead of the §174A(a) current-expense default |
| §59(e) — qualified-expenditure amortization | §59(e) | (b) | Re-times (spreads) an otherwise currently-deductible/faster-written-off amount — AMT-preference-avoidance flavor of an add-on election |
| Rev. Proc. 2011-29 — 70/30 success-fee safe harbor | Rev. Proc. 2011-29 | (b)/(c) hybrid | Simplifies documentation; can move the capitalized amount UP or DOWN from the fact-specific result depending on the actual facilitative/non-facilitative split — flag as fact-dependent, don't assume a direction |
| De minimis safe harbor (tangible property) | §1.263(a)-1(f) | (c) | DEDUCTS currently amounts BAR would otherwise require to be capitalized, below the $5,000/$2,500 ceiling |
| Small-taxpayer building safe harbor | §1.263(a)-3(h) | (c) | DEDUCTS currently repairs/improvements below the 2%/$10,000 per-building ceiling |
| Routine maintenance safe harbor | §1.263(a)-3(i) | (c) | Not technically an election (a safe harbor applied when facts are met) — DEDUCTS currently what BAR might otherwise treat as a restoration |
| $200,000 producer de minimis (deemed-zero additional §263A) | §1.263A-2(b)(3)(iv) | (c) | DEDUCTS currently additional §263A costs below the threshold |
| $5,000 facilitative-cost de minimis (intangibles) | §1.263(a)-4(e)(4) | (c) | DEDUCTS currently facilitative costs below the $5,000-per-transaction cliff — distinct provision from the tangible-property de minimis above despite the same figure |
| $5,000/$50,000 start-up cost first-year deduction | §195/§248/§709 | (c) | DEDUCTS currently the first $5,000 (phased out above $50,000) of otherwise-capitalized start-up costs |

**Sequencing consequence, stated explicitly for Phase E's build:** kind-(a) elections are answered in Gate 2 (§263A methods) and parts of Gate 7/8/10 (tracing posture, computation timing) — they configure HOW the Step-3/4 mandatory engines run, so they must be answered BEFORE those engines execute. Kind-(b) and kind-(c) elections (Gates 4, 5, 8's Q8.2, 9's Q9.3, 10) are answered and applied AFTER the mandatory Step-3/4 output exists, since they either add to it (b) or carve a safe-harbor exception out of a specific mandatory determination (c) — they cannot be evaluated first. Phase E's existing FACT/ELECTION/METHOD-OF-ACCOUNTING tagging (Gates 0-10) should be read alongside this table's (a)/(b)/(c) tagging — they answer different questions (legal character vs. pipeline-sequencing role) and neither substitutes for the other.

---

## Phase E — Interview layer: the question inventory and decision tree (ADDED 2026-07-09)

**Ordering note:** Phase E appears here, after F/G/H, not because it's built last — its Gate 0-2 core builds
EARLY, per "Sequencing & why" below — but because it's a cross-cutting layer that populates `EntityProfile` for
EVERY engine phase (A-D and F-H alike), and reading it after all the engines it serves is easier to follow than
reading it between D and F, which would visually suggest it only serves the §263A engines. The letter "E" reflects
when it was first added to this plan (right after Phase D existed), not its position in this document.

**Gap this phase closes:** every engine above consumes `EntityProfile` fields and schedules but nothing specified how
they get populated. A user cannot be handed a 40-field dataclass; the tool needs an interview that asks only the
questions the taxpayer's prior answers make relevant, distinguishes facts from elections from methods of accounting,
and emits a fully-populated `EntityProfile` + schedule requirements list + warnings. This section is the
authoritative question inventory; the engines' sections above remain the authority for each rule's mechanics.
Gates 8-10 (ADDED 2026-07-09, alongside Phases F/G/H above) extend this to §174/§174A, §1.263(a)-4/-5 +
§195/§248/§709, and §59(e) — **these three gates have NOT been through the field-reachability/golden-example/
adversarial validation pass described immediately below, since that pass predates them; treat Gates 8-10 as
first-draft, not validated, until a follow-up pass covers them the same way Gates 0-7 were covered.**

**VALIDATION PASS 2026-07-09 (before any code exists):** three independent agents pressure-tested this section as
written — (1) a field-reachability audit cross-checking every engine-declared input against a Gate 0-7 question,
(2) a hand-trace of all four golden worked examples (MSPM/SRM/SCA/§263A(f)) through the gates to confirm the
interview would actually reconstruct their assumed inputs, (3) an adversarial run of a composite taxpayer (producer
+ reseller above de minimis, LIFO, dual-function facility, mid-construction SCA with traced+nontraced debt, second
year on a just-switched method) not covered by any existing example. Two of the four golden traces FAILED as
originally written (MSPM and SRM — both silently missing a required input), and the adversarial run surfaced a
load-bearing contradiction at Gate 0/1. All findings below are fixed inline; see `docs/TAX_DECISIONS.md` §12 for
the full report. **Documentation debt closed 2026-07-09 (same pass):** Gates 3, 5, 6, and 7 were unnumbered
prose/topic lists at first; all four are now individually numbered `Q#.#` questions matching the style already
used in Gates 0, 1, 2, and 4, so every node referenced anywhere in this section (including the newly-added ones
above) now has a stable ID the `taxonomy/interview.yaml` loader's reachability validation can target.

**Architecture:** `interview.py` + `taxonomy/interview.yaml`. The YAML is a declarative question graph — each node:
`id`, `question`, `answer_type` (bool/enum/decimal/date/per-item), `maps_to` (EntityProfile field / schedule
column / per-line override), `authority`, `ask_when` (predicate over prior answers — this IS the decision tree),
`kind` (**FACT** / **ELECTION** / **METHOD-OF-ACCOUNTING**), and `consequence` (gates skipped or unlocked; warnings
emitted). Loader validates: every engine-consumed field is populated by exactly one reachable node or an explicit
default; every `ask_when` references defined nodes (same validate-at-load discipline as the taxonomy). Every
`kind: METHOD-OF-ACCOUNTING` answer that differs from the established-method answer (Q0.6) emits the
`METHOD-CHANGE-3115-481A-REQUIRED` warning; first-§263A-year adoption does not. Sub-trees repeat per facility
(Gate 3), per asset (Gate 6), per unit/per debt instrument (Gate 7), and per flagged line (Gate 4).

**Gate 0 — Identity, exemption, and adoption-vs-change (asked always; can END most of the interview):**
- Q0.1 Entity type (c_corp/s_corp/partnership/sole_prop) → `entity_type`. FACT. Unlocks §707(c) guaranteed-payment
  questions (Gate 7) for partnerships; determines who signs elections (entity-level for S corps/partnerships).
- Q0.2 Tax year → `tax_year`. FACT. Drives §448(c) threshold lookup and the T.D. 10034 pre/post-Oct-2025 regime.
- Q0.3 Is the taxpayer a tax shelter under §448(a)(3) (syndicate/loss-allocation tests)? → `is_tax_shelter`. FACT.
  If yes: exemption barred regardless of receipts (skip Q0.4's exemption consequence).
- Q0.4 Aggregated 3-yr average gross receipts under §448(c)(2)/§1.448-2 (single-employer aggregation — ask the
  related-entities sub-questions needed to aggregate) → `avg_gross_receipts`. FACT. If ≤ threshold and not Q0.3 →
  `small_business_exempt`: **skip Gates 1-3, 6, 7 entirely** (all §263A off, including (f)); Gates 4-5 (§263(a),
  §266 — not §263A provisions) still run.
- Q0.5 First taxable year with production/resale activities? → `is_first_263a_year`. FACT. If yes → methods below
  are ADOPTED (no 3115); if no → Q0.6.
- Q0.6 Established §263A method last year (SPM/MSPM/SRM/facts-and-circumstances/none-noncompliant) + established
  sub-elections → `prior_year_method`. FACT. Any divergence from answers below → 3115 warning + the
  revalued-beginning-inventory input-contract notice (§1.263A-7).
- Q0.6a **RECONCILIATION, ADDED 2026-07-09** (closes a contradiction an adversarial trace found: `none-noncompliant`
  was an enum value with no defined consequence, and a taxpayer whose true Q0.6 answer — e.g. SRM — turns out to
  have been legally unavailable under Gate 1's consequence matrix below had nowhere to go): once Gate 1's
  method-availability matrix is known, VALIDATE it against Q0.6. If `prior_year_method` was never legally available
  for this taxpayer's activity profile, that is a DISCOVERED IMPERMISSIBLE METHOD, not a voluntary election —
  route to a distinct `PRIOR-METHOD-IMPERMISSIBLE` flag (an error-correction event under §446(e)/the applicable
  Rev. Proc. for changing FROM an impermissible method — still needs a 3115 but with a different DCN/§481(a)
  posture than an ordinary elective switch; the correction computation itself is out of scope, see "Deferred").
  If `prior_year_method` was legally available and simply differs from this year's chosen method, the ordinary
  `METHOD-CHANGE-3115-481A-REQUIRED` path already described applies.

**Gate 1 — Activity profile and method availability (ask unless exempt):**
- Q1.1 Produces real/tangible property? Acquires for resale? Both? → `produces`/`acquires_for_resale`. FACT.
- Q1.2 (if both) Production gross receipts and production labor as shares of the trade or business (measured at
  trade-or-business level per (a)(5)(ii)) → `production_activity_level` via the 10%/10% presumption; below both →
  presumed de minimis, above → facts-and-circumstances follow-up (volume). FACT. **CLARIFIED 2026-07-09** (a
  completeness pass found the follow-up an undefined black box): the follow-up is not a single yes/no — it walks
  the same frequency / dollar-volume-trend / business-purpose factors as the de-minimis discussion, resolves to
  `production_activity_level ∈ {de_minimis, more_than_de_minimis}`, and is a review-queue SME judgment call, not
  an automated formula.
- Q1.3 (if production de minimis) Incident to resale of §1221(a)(1) property? → `production_incident_to_resale`. FACT.
- Q1.4 Private-label production (contract, UNRELATED party, incident to resale, sold to customers — three
  sub-questions)? → `private_label_goods`. FACT. `ask_when`: **always** (NOT gated on Q1.3's de-minimis answer —
  CLARIFIED 2026-07-09: (a)(4)(iii) private-label is specifically the carve-out that can qualify a MORE-than-de-
  minimis producer for SRM, unlike Q1.3 which only matters for the de-minimis-incident route).
- Consequence matrix (no question — computed): SRM available only if pure reseller, or de-minimis-incident
  ((a)(4)(ii)), or private-label ((a)(4)(iii)); otherwise SPM/MSPM only (`method_conflict` if SRM chosen).

**Gate 2 — Inventory & UNICAP method elections (ask unless exempt):**
- Q2.1 Inventory method (FIFO / specific-goods LIFO / dollar-value LIFO; if LIFO → layer detail) → `inventory_method`,
  `lifo_layers`. FACT (established method).
- Q2.2 §263A method this year (menu constrained by Gate 1) → `method`. METHOD-OF-ACCOUNTING.
- Q2.3 (SPM only) >$50M 3-yr receipts? → negatives barred; else Q2.4.
- Q2.4 Include negative §263A adjustments? → `include_negative_263a`. METHOD-OF-ACCOUNTING; warn on the
  (d)(3)(ii)(C)-(E) restrictions (no negatives for discounts / §162(c)(e)(f)(g) items; consistency).
- Q2.5 (producers) Total indirect costs ≤ $200,000 (after excluding not-required-to-capitalize categories;
  related-party aggregated)? → de-minimis zero additional §263A; **skip Gates 2.6-2.8 and 3's ratio inputs**. FACT.
- Q2.6 HAR election? `ask_when`: **Q2.2 = MSPM** AND 3+ consecutive prior years on MSPM with actual ratios AND not
  Q2.5-zero → `har_election` + ratio/qualifying-year inputs. METHOD-OF-ACCOUNTING (cut-off). **CORRECTED 2026-07-09**
  — HAR is an MSPM-only mechanic (§1.263A-2(c)(4)); the prior wording had no method restriction at all, so as
  written it would have wrongly asked SPM/SRM taxpayers this question too.
- Q2.7 (MSPM) SSCM-split method (direct-material vs. labor) → `mspm_mixed_split_method`; and the (c)(3)(iii)(C) 90%
  one-bucket election → `mspm_90pct_split_election`. Both METHOD-OF-ACCOUNTING.
- Q2.8 SSCM: elected? ratio method (labor; production-cost offered ONLY if producer per (h)(3)(ii)) →
  `sscm_ratio_method`; exclude-self-constructed-assets election ((h)(2)(ii)); (g)(4)(ii) all-departments 90%
  election → `msc_90_10_election`. Each METHOD-OF-ACCOUNTING.
- Q2.9 Book-conformity check (§1.263A-1(d)(2)): does financial-statement capitalization match the classifier's
  §471/Additional tier split? On TD 9843 elective methods ((d)(2)(iii)/(iv)/(v))? → review-queue flags, not fields
  (flag-don't-model per Phase B). FACT.

**Gate 3 — Balance and cost-pool inputs (menu strictly follows Q2.2; per-facility sub-tree repeats per facility) —
NUMBERED 2026-07-09 (was an unnumbered prose list; see the documentation-debt note above):**

*SPM (ask_when: Q2.2 = SPM):*
- Q3.1 §471 costs remaining in ending inventory → `ending_inventory_471`. FACT.

*MSPM (ask_when: Q2.2 = MSPM):*
- Q3.2 Pre-production §471 costs incurred during the year (direct material + resale) → `pre_production_471`. FACT.
- Q3.3 Production §471 costs incurred during the year → `production_471`. FACT.
- Q3.4 Pre-production additional §263A costs incurred → `pre_production_additional_263A`. FACT.
- Q3.5 Production additional §263A costs incurred → `production_additional_263A`. FACT.
- Q3.6 Pre-production §471 costs on hand at year end (current-year-incurred only, per (c)(3)(ii)(C)/(E) — see the
  input-contract note in the MSPM DECISION block above) → `pre_production_471_on_hand`. FACT.
- Q3.7 Production §471 costs on hand at year end (same current-year-incurred limitation) → `production_471_on_hand`. FACT.
- Q3.8 Beginning direct materials not yet in production → `beginning_DM_not_yet_in_production`. FACT.
- Q3.9 Ending direct materials not yet in production → `ending_DM_not_yet_in_production`. FACT.
- Q3.10 Direct materials purchased during the year → `DM_purchased_during_year`. FACT. **ADDED 2026-07-09** — a
  golden-example dry run found this fact, distinct from both Q3.2's aggregate and Q3.8/Q3.9's stock figures, was
  silently un-asked despite feeding `direct_materials_adjustment` directly.

*SRM (ask_when: Q2.2 = SRM):*
- Q3.11 Current year's purchases — §471 costs incurred on property acquired for resale during the year (the
  purchasing-ratio DENOMINATOR) → `current_year_471_costs`. FACT. **DISAMBIGUATED 2026-07-09** from Q3.12 —
  see the naming-disambiguation note in the SRM formula block above.
- Q3.12 Purchasing-department cost pool (the purchasing-ratio NUMERATOR) → `purchasing_costs`. FACT. **ADDED
  2026-07-09** — previously conflated with Q3.11 under Gate 3's old bare "purchases" wording.
- Q3.13 Storage & handling costs → `storage_handling_costs`. FACT.
- Q3.14 Beginning inventory §471 costs (LIFO carrying value if Q2.1 = LIFO) → `beginning_inventory_471`. FACT.
- Q3.15 §471 costs remaining on hand at year end (LIFO: current-year increment, unless Q3.18's Variation B is
  elected) → `ending_inventory_471`. FACT. **ADDED 2026-07-09** — both the field-reachability audit and the
  golden-example dry run independently found this, the direct multiplicand of `add'l_to_inv`, was never asked.
- Q3.16 1/3–2/3 purchasing-labor election → ELECTION (all-or-nothing).
- Q3.17 Write-down carve-out scope (which write-downs are excluded from the S&H cost pool) → FACT.
- Q3.18 Permissible-variation elections: (A) exclude beginning inventory from the S&H denominator; (B) LIFO
  taxpayer multiplies by total ending-inventory §471 costs instead of the increment → `srm_variation_a`/
  `srm_variation_b`. METHOD-OF-ACCOUNTING.

*Per-facility sub-tree (SRM only; repeats per facility):*
- Q3.19 Attached to a retail facility? Integral part of it? → FACT.
- Q3.20 Exclusively retail on-site sales? (the (E)(2) four-part test if non-retail customers exist) → FACT.
- Q3.21 (if dual-function) On-site sales $ and total gross sales $, INCLUDING inter-facility shipments (the (B)
  ratio; 90/10 deeming applies per the reversed decision above) → FACT.
- Q3.22 Handling-cost exclusion facts: store-level handling, distribution, custom-order, pick-and-pack (per the
  (c)(4) bullet above) → FACT.

**Gate 4 — §263(a) tangible-property questions (always asked; per flagged line where noted):**
- Q4.1 De minimis safe harbor: AFS? (→ ceiling authority) — **written accounting procedures in place at the
  BEGINNING of the year** ((f)(1)(i)(B)/(ii)(B) — a prerequisite fact no prior draft of this plan captured
  anywhere)? elect this year? → ANNUAL ELECTION (statement on timely filed return, irrevocable for the year, NOT a
  method change — (f)(5)).
- Q4.2 Small-taxpayer building safe harbor ((h)): ≤$10M receipts under (h)(3)'s OWN definition (not §448(c))?
  per-building: unadjusted basis ≤$1M? repairs+improvements ≤ lesser of 2% basis or $10,000? → ANNUAL PER-BUILDING
  ELECTION — also not previously in this plan.
- Q4.3 Routine-maintenance safe harbor facts (twice-in-10-years / twice-in-class-life expectation) — per flagged
  line from the review queue. FACT.
- Q4.4 Election to capitalize repairs per books ((n)) → ANNUAL ELECTION. BAR follow-ups (betterment/restoration/
  adaptation sub-questions) per flagged improvement line.

**Gate 5 — §266 (always asked where classifier flags candidates) — NUMBERED 2026-07-09:**
- Q5.1 Property unimproved AND unproductive this year? → ELECTION (annual, year-by-year).
- Q5.2 Development/construction project? → ELECTION (sticks until the work completes).
- Q5.3 Election statement confirmed filed with the original return? → FACT. Resolves the still-open §3 item 3
  confirmation workflow.

**ORDERING NOTE ADDED 2026-07-09** (an adversarial
trace found a real conflict for a self-constructed real-property asset that is simultaneously a §266(b)(1)(ii)
development-project candidate and a Gate-7 designated-property/common-feature candidate): per §1.266-1(a)(2),
§§1.263A-8..-15 apply FIRST, and a §266 election for designated property is valid only if it does not thereby
"materially distort" the computation (see "Deferred/out of scope" above). For any asset flagged in BOTH Gate 5 and
Gate 7, Gate 5's election question must be asked AFTER Gate 7's per-unit/per-debt determination for that asset is
known, not on Gate 5's own fixed position in the sequence — implementers should treat this as a cross-gate
`ask_when` dependency, not a strict linear Gate-0-through-7 walk.

**Gate 6 — SCA (ask if self-constructed assets exist; per asset) — NUMBERED 2026-07-09:**
- Q6.1 Cost-allocation method of accounting: specific identification / burden rate / standard cost → FACT.
  **ADDED 2026-07-09** — a field-reachability audit found Gate 6 asked for pool/driver assignments without first
  establishing which method the taxpayer uses; this tool implements Specific Identification only (Phase C above) —
  burden-rate/standard-cost answers must be FLAGGED, not silently forced into a Specific-ID pool/driver structure.
- Q6.2 SSCM eligibility route: (C) or (D) (three sub-facts each) → FACT.
- Q6.3 Book-capitalized indirect costs already in CIP (double-count guard) → FACT. **Note:** Phase C's own text
  flags the double-count RULE itself as unresolved — this answer routes to the review queue, not a computed
  adjustment, until that gap closes.
- Q6.4 Pool/driver assignments (validated against `sca_drivers.yaml`) → FACT.
- Q6.5 Individual materially involved in construction — officer, or for a partnership/sole proprietorship the
  general/managing partner or proprietor (per Q0.1's entity type) → FACT. **ADDED 2026-07-09** — an adversarial
  trace found the original "officer" wording doesn't fit a partnership; surfaces the open §8c-adjacent
  officer/partner-comp limitation rather than silently proceeding.

**Gate 7 — §263A(f) (ask if designated-property candidates exist) — NUMBERED 2026-07-09:**

*Per-unit sub-tree (repeats per unit):*
- Q7.1 Real property? → FACT. (Category 1, automatic designation.)
- Q7.2 Improvement to existing property + the (d)(3)(iii) gate? → FACT.
- Q7.3 Tangible personal property with class life ≥20 years + held-for-sale carve-out? → FACT. (Category 2/3.)
- Q7.4 Estimated production period and cost, with the contemporaneous-records question ((b)(2)(iii))? → FACT.
- Q7.5 90-day production period / $1M-per-day cost de minimis exclusion? → FACT.
- Q7.6 Otherwise-excluded property (per the exclusion list above)? → FACT.
- Q7.7 Related-person ACTIVITIES (classification/production-period purposes)? → FACT.
- Q7.8 Related-person COSTS incurred by the taxpayer (excluded from the taxpayer's own APE)? → FACT. **ADDED
  2026-07-09** — a distinct data need from Q7.7, previously asked (if at all) as one undifferentiated question.
- Q7.9 Unit-of-property structure: common features, benefitted-unit map, per-property activity dates (§1.263A-10) → FACT.
- Q7.10 `production_complete` date, distinct from the FixedAsset schedule's `placed_in_service_date` → FACT.
  **ADDED 2026-07-09** — capitalization runs until the LATER of the two; conflating them silently undercounts the
  computation period.
- Q7.11 (`ask_when`: `industry` indicates customary aging, e.g. tobacco/wine/whiskey) Aged-property production-period
  extension → FACT. **ADDED 2026-07-09.**
- Q7.12 Were producing assets/equipment (e.g. owned construction equipment) used to produce this unit? If so, their
  basis and usage-apportionment method → FACT. **ADDED 2026-07-09** — moves real dollars into APE per the
  bulldozer example in Phase D above; previously un-asked entirely.
- Q7.13 Acquired mid-production? If so, purchase price → FACT. **ADDED 2026-07-09** (T.D. 10034, §1.263A-11(f)).
- Q7.14 (`ask_when`: Q0.2's tax year begins on/before Oct 2, 2025) Pre-amendment associated-property inputs:
  adjusted basis of the existing structure/common feature; the 5% de minimis test → FACT. **ADDED 2026-07-09.**
- Q7.15 Produced under contract? Customer or contractor role, and payments-by-date → FACT.

*Taxpayer/computation-level (not per-unit):*
- Q7.16 Computation period & measurement-date frequency → METHOD-OF-ACCOUNTING.
- Q7.17 Tracing posture: trace / §1.263A-9(d) no-tracing election / AFR-plus-3 (`ask_when`: $10M test OR
  small-business route; forecloses tracing) → METHOD-OF-ACCOUNTING.
- Q7.18 (`ask_when`: Q7.17's AFR-plus-3 $10M route is being evaluated) Since-1994 average-receipts look-back for
  that eligibility test → FACT. **ADDED 2026-07-09** — a longer window than Q0.4's ordinary 3-year §448(c) test;
  do not silently reuse Q0.4's answer.
- Q7.19 (`ask_when`: Q7.17 = no-tracing) Accounts-payable fold-in sub-election (§1.263A-9(d)(1)), which lowers the
  WAIR denominator → METHOD-OF-ACCOUNTING. **ADDED 2026-07-09** — a distinct choice, not implied by electing
  no-tracing itself.

*Per-debt-instrument sub-tree (repeats per debt instrument):*
- Q7.20 Eligible-debt exclusion screens ((a)(4)(i)-(ix)) → FACT.
- Q7.21 Suspension election (120-day facts + inherent-cause carve-out) → METHOD-OF-ACCOUNTING, all-units consistency.
- Q7.22 15-day repayment toggle (per-period, NOT a method) → FACT.
- Q7.23 (`ask_when`: Q0.1 = partnership) Guaranteed payments for use of capital ((c)(2)(iii)) → FACT.

**Gate 8 — §174/§174A research & experimental expenditures (ask if R&E-tagged costs exist; per project/pool):**
- Q8.1 Domestic or foreign research (or both, per project)? → `re_domestic_or_foreign`. FACT.
- Q8.2 (domestic) Elect ≥60-month capitalization instead of current expensing, per §174A(c)? If yes, elected period
  (≥60 months) → `re_capitalization_election`, `re_capitalization_period_months`. METHOD-OF-ACCOUNTING.
- Q8.3 (if the taxpayer has 2022-2024 domestic R&E still being amortized under the old 5-year schedule) Catch-up
  method: 1-year (all in 2025) or 2-year (split 2025-2026)? → `re_catchup_method`. METHOD-OF-ACCOUNTING.
- Q8.4 (if `avg_gross_receipts` ≤ the applicable §448(c) small-business threshold — reuse Q0.4's answer, do not
  re-ask) Elect the small-business RETROACTIVE amendment instead of the catch-up (Q8.3)? Amended-return deadline
  July 6, 2026 — surface this date directly, not as a footnote → `re_small_business_retroactive_election`.
  METHOD-OF-ACCOUNTING; mutually exclusive with Q8.3.
- Q8.5 Software development costs among these expenditures? (routes to the same domestic/foreign, mandatory/
  elective framework — flag for SME scope confirmation per the Phase F note, not an automated determination) →
  FACT, review-queue flag.
- Q8.6 (per disposal/retirement/abandonment event touching R&E-basis-bearing property) Was any capitalized R&E
  basis remaining? → FACT; triggers the `§174D-DOMESTIC-ELECTIVE-UNVERIFIED` flag from Phase F for elected-
  capitalization domestic R&E, or the confirmed-applicable rule for foreign R&E.

**Gate 9 — §1.263(a)-4/-5 intangibles, transaction costs, and start-up/organizational costs (ask if flagged
transaction/intangible-tagged costs exist; per transaction / per intangible / per start-up-cost pool):**
- Q9.1 Is this a covered transaction (acquisition of a trade/business, reorganization, or capital-structure/
  capital transaction per §1.263(a)-5(e)(1))? → FACT.
- Q9.2 (if covered transaction) Bright-line date established? Cost incurred before or after it? Inherently
  facilitative (investment banking, appraisal, title/transfer, regulatory, financing — always capitalized
  regardless of timing)? → FACT, feeds the classification adapted from `transaction_costs/`.
- Q9.3 (if a success-based fee in a covered transaction) Elect the Rev. Proc. 2011-29 70/30 safe harbor (70%
  deductible / 30% capitalized) instead of documenting the actual facilitative portion? → ELECTION, irrevocable,
  per-transaction.
- Q9.4 (per intangible) 12-month rule: does the right/benefit extend beyond the EARLIER OF 12 months from first
  realizing it or the end of the following tax year? → FACT. If no (within the window) → not required to capitalize.
- Q9.5 (per intangible, if not exempted by Q9.4) Facilitative-cost aggregate for this transaction ≤ $5,000 ((e)(4)
  — separate from Gate 4.1's tangible-property de minimis, do NOT reuse that answer)? → FACT (cliff test, not a
  partial exclusion). Elect to treat compensation/overhead/de-minimis-eligible costs as facilitative anyway? →
  ELECTION.
- Q9.6 (per intangible requiring capitalization) Category (financial interest / contract right / membership or
  privilege / governmental right / real-property-transfer benefit / residual) and acquired-with-a-trade-or-
  business flag (routes to §197 15-year amortization if yes) → FACT.
- Q9.7 Start-up or organizational cost pool present? Total costs (for the $5,000/$50,000 phase-out test) and the
  date the active trade or business began (amortization start) → `startup_org_total`, `business_commencement_date`.
  FACT.
- Q9.8 (partnerships only, from Q0.1) Any portion representing SYNDICATION costs under §709(b) (fees to promote/
  sell partnership interests)? → FACT. If yes, routes to PERMANENT non-amortization, not the $5,000/180-month
  schedule — a real trap the interview must not silently miss (see Phase G's build note on the existing taxonomy
  code's undifferentiated keyword list).
- Q9.9 **ADDED 2026-07-09**: Did the taxpayer acquire a trade or business this year (an asset acquisition, or a
  deemed asset acquisition under §338)? → FACT. If yes → routes to the §1060 Purchase Price Allocation sub-tree:
  aggregate consideration; per-class (I-VII) fair-market-value estimates; Form 8594 consistency confirmation with
  the counterparty (has the counterparty agreed to the same class allocation?) → `PurchasePriceAllocation` record.
  This SEEDS basis for Phases B/C/F/G/H on the acquired assets — ask this before the per-asset Gates (3/6/7) for
  any asset acquired in this transaction, since their basis inputs depend on this allocation's output.
- Q9.10 **ADDED 2026-07-09** (per structure demolished this year): was the demolition triggered by casualty (Notice
  90-21 carve-out) or a voluntary redevelopment decision? → FACT. If voluntary, demolition cost + remaining
  undepreciated basis routes to the LAND `AmortizableItem` (non-depreciable), never to a deductible loss or to the
  demolished structure's own (now-nonexistent) basis — see the §280B bullet in Phase G above.

**Gate 10 — §59(e) elective qualified-expenditure amortization (ask if IDC/mining/circulation/domestic-R&E-
tagged costs exist AND the entity-type/AMT-exposure screen below indicates the election could matter):**
- Q10.1 **GATING QUESTION, asked first:** is the taxpayer an individual, or a pass-through entity whose owners may
  report AMT preference items (§55/§56/§57 individual AMT)? → FACT. If the taxpayer is a C-corp with no
  individual-AMT-exposed owners, SKIP the rest of this gate — under current law the corporate AMT was repealed by
  TCJA and the CAMT (§55/§56A, Inflation Reduction Act 2022) does not use §59(e)/§57 preference items at all (see
  Phase H's build note); offering this election to a pure C-corp with no flow-through owners has no live use case.
- Q10.2 (if Q10.1 = yes) Per qualified expenditure: category (circulation §173 / domestic R&E §174A(a) / IDC
  §263(c) / mining exploration §617(a) / mining development §616(a)), amount, and elect §59(e) amortization
  (item-by-item, any portion, irrevocable except by IRS consent)? → `QualifiedExpenditureElection` record.
  METHOD-OF-ACCOUNTING.
- Q10.3 (if the elected category is domestic R&E AND Gate 8's Q8.2 §174A(c) capitalization election was ALSO made
  on the same dollars) Flag `§59E-174A-ELECTION-CONFLICT` and route to SME review — this plan does not resolve
  which period (10 years under §59(e) vs. the Q8.2-elected ≥60-month period) governs when both elections are made
  on the same expenditure.
- Q10.4 (if the elected category is mining exploration or development) Surface the `§57-MINING-CITE-UNVERIFIED`
  flag noted in Phase H — the exact AMT-preference subparagraph citation was not confirmed against primary text.

**Build/test notes:** the interview emits (a) a populated `EntityProfile`, (b) the list of schedules Phase A must
ingest for this taxpayer (only what the answers require), (c) the election/3115 summary for the workpaper, and (d)
warnings. Tests: graph-validation tests (every engine field reachable; no orphan questions), path tests (exempt
taxpayer answers 6 questions and is done; pure reseller never sees MSPM questions; SRM blocked when Gate 1 says
`method_conflict`), and a golden full-path fixture per method. UI is out of scope — the deliverable is the question
graph + `interview.py` runner (CLI prompts or a JSON answers file); any front end consumes the same YAML.

**Scope note on already-shipped analyst fields ADDED 2026-07-09** (flagged by the field-reachability audit, not a
gap in Phase E — a scope clarification): `EntityProfile.mixed_alloc_ratio` (the SSCM ratio override already live
in `analysis.py`) is deliberately NOT an interview question — it is a workpaper-preparer override for a value the
interview otherwise derives, entered directly on the `EntityProfile` object by whoever runs the tool, not asked of
the taxpayer. The legacy Phase-4 fallback scalars (`accumulated_production_expenditures`, `avoided_cost_rate`,
`has_designated_property`) stay as the documented fallback path for when Phase A's Debt/FixedAsset/CIP schedules
are empty (see `analysis.py`'s existing comment); Gate 7's schedule-driven path is the primary path and does not
retire them.

---

## Sequencing & why

1. **Phase A first** — the four new schedules (BTD, FixedAsset, CIP, Debt) are the inputs Phases C/D consume ("three" was a stale count, fixed 2026-07-09; and per the corrected intro, Phase B is NOT actually gated on Phase A — only C/D are).
2. **Phase B (MSPM/SRM)** — pure arithmetic over existing classifier output; lowest risk, immediate value, no new schedules beyond inventory balances.
3. **Phase C (SCA)** — needs FixedAsset/CIP + driver tables (Phase A) and **conditionally** reuses SSCM (gated on
   the per-asset `sscm_eligible` check — most Phase C targets are expected to fail it, per the SSCM section's own
   analysis; this line previously said "reuses SSCM" unconditionally, which was stale relative to that fix);
   produces `ape_by_asset`.
4. **Phase D (§263A(f))** — needs FixedAsset/CIP/Debt (Phase A) and SCA's APE hand-off (Phase C); hardest, so last.
5. **Phase E (interview layer)** — build its Gate 0-2 core EARLY (alongside or before Phase B), since it is what
   populates `EntityProfile` for every engine and what tells Phase A which schedules a given taxpayer even needs;
   Gates 3-7 land with their corresponding engine phases (Gate 3 with B, Gate 6 with C, Gate 7 with D). Gates 4-5
   can ship any time — they gate classifier-level decisions, not engines.
6. **Phases F/G/H (§174/§174A, §1.263(a)-4/-5 + §195/§248/§709, §59(e)) — ADDED 2026-07-09, fully INDEPENDENT of
   Phases A-D and each other:** none of the three touch §263A at all (R&E is categorically excluded from the
   UNICAP pools; intangibles/transaction costs and start-up costs are their own §263(a)/§195/§248/§709 regime;
   §59(e) is an election layered on five separate underlying provisions), and none of the three depend on Phase
   A's BTD/FixedAsset/CIP/Debt schedules or on each other's schedules — they can build in any order, or in
   parallel, whenever prioritized. Phase G's §1.263(a)-5 piece has a head start (reusable Phase-1 classifier +
   authorities already exist in `transaction_costs/`, confirmed 2026-07-09 — see Phase G above), making it the
   lowest-effort of the three to start; Phase H (§59(e)) is gated first on the entity-type/AMT-exposure screen
   (Gate 10, Q10.1) before any per-item election logic matters, so build that gate first within Phase H regardless
   of build order relative to F/G. Their corresponding interview gates (8/9/10) land with them, same pattern as
   Gates 3/6/7 landing with B/C/D.
7. **The Tax-Basis TB (Runtime Pipeline Step 2) and Basis Reconciliation (Step 3b) — ADDED 2026-07-09, build
   BEFORE the phases that depend on them, not after:** the Tax-Basis TB deliverable belongs in Phase A itself (it's
   an ingestion-adjacent output, not a new phase) and should ship with Phase A so every downstream phase classifies
   the correct (adjusted) TB from day one, rather than being retrofitted later. `compute_basis_reconciliation` is a
   shared helper Phases C/D/F/G and Gate 4's BAR routing all call — build it once, alongside whichever of
   C/D/F/G ships FIRST (not duplicated per-phase), and have the later phases call the existing helper rather than
   each re-deriving their own delta logic.
8. **§1060 Purchase Price Allocation and §280B demolition (Phase G additions) — ADDED 2026-07-09:** §1060 SEEDS
   basis for an acquired business's assets, so if a taxpayer engagement includes a mid-year acquisition, build the
   §1060 mechanic before or alongside whichever of Phases B/C/F/G/H will consume the acquired assets' basis — it's
   an input dependency for them in that scenario, not an independent add-on. §280B is small and has no dependents;
   build whenever convenient within Phase G.

Each phase ships standalone value and keeps the waterfall tie-out.

## Files
- **New:** `readers.py`, `engines/sca.py`, `engines/interest.py`, `taxonomy/sca_drivers.yaml`, `interview.py` + `taxonomy/interview.yaml` (Phase E), tests `test_readers.py`/`test_mspm_srm.py`/`test_sca.py`/`test_interest.py`/`test_interview.py`.
- **New, ADDED 2026-07-09 (Phases F/G/H):** `engines/re_capitalization.py`, `engines/intangibles.py`, `engines/qualified_expenditures.py`, `taxonomy/qualified_expenditure_periods.yaml`, tests `test_re_capitalization.py`/`test_intangibles.py`/`test_qualified_expenditures.py`.
- **New, ADDED 2026-07-09 (Runtime Pipeline finalization):** `engines/tax_basis_tb.py` (`compute_tax_basis_tb`, Step 2), `engines/basis_reconciliation.py` (`compute_basis_reconciliation`, the shared Step-3b helper), `engines/purchase_price_allocation.py` (`compute_1060_allocation`), tests `test_tax_basis_tb.py`/`test_basis_reconciliation.py`/`test_purchase_price_allocation.py`.
- **Extend:** `model.py` (schedule + SCA dataclasses, `EngagementData`, `ValidationReport`, plus `AmortizableItem`/`REExpenditure`/`IntangibleItem`/`TransactionCostItem`/`StartupOrgCostPool`/`QualifiedExpenditureElection` — Phases F/G/H; plus `TaxBasisTBLine`, `PurchasePriceAllocation`, and the new `book_capitalized_*`/`prior_capitalized_basis`/`improvement_target_asset_id`/`demolition_event` fields for Basis Reconciliation), `analysis.py` (EntityProfile fields, dispatcher, `compute_mspm/srm/sca`, call `compute_263Af`; plus the `"§174 Capitalized"` bucket and Phase F/G/H field additions), `report.py` (per-asset Asset Basis generalized into the shared Basis & Amortization Schedule, §263A(f) tab, MSPM/SRM tables, Data Quality tab, waterfall wiring; plus R&E Amortization tab, Intangibles & Transaction Costs tab, §59(e) Election Tracker tab, **Tax-Basis TB tab, Purchase Price Allocation tab**), `taxonomy/categories.yaml` (new circulation/IDC/mining-exploration/mining-development codes for Phase H — none exist today; the R&E/intangible/start-up codes Phases F/G consume already exist, per the "Taxonomy already has partial coverage" note above).

## Verification
- Unit tests from each worked example — **figures CORRECTED 2026-07-08 to match the actual worked-example sections above** (a prior draft of this checklist had gone stale relative to formula corrections made earlier in the same document): MSPM **284,400** additional §263A / **$3,284,400** total ending inventory (the regulation's own Example 1 — NOT the superseded 143,000 hand-built figure); SRM 36,875; SCA 55k/asset + conservation + guardrail/degenerate; §263A(f) **376,428.57** = traced **180,000.00** + avoided/excess-expenditure **196,428.57** (NOT the superseded 323,571.43 figure, which used an incorrect open/close-averaging methodology — see the Phase D section above and `docs/TAX_DECISIONS.md` §7e). Also confirm MSPM's rounding convention explicitly before coding the test: the regulation's own Example 1 arrives at exactly $284,400 only if the 10.22% production ratio is rounded to two decimal places BEFORE multiplying by ending inventory (unrounded, 920,000/9,000,000 × $2,000,000 = $204,444.44, giving $284,444.44 total) — MSPM should round the ratio to match the IRS's own presentation, which is a DIFFERENT convention from Phase D's "exact Decimal arithmetic, not rounded intermediates" rule; document this per-engine rather than assuming one global rounding rule applies everywhere.
- FK/validation tests (unresolved links flagged; debit/credit netting already covered).
- Method-conflict test (SRM chosen but production > de minimis).
- End-to-end: `read_engagement` on a multi-sheet sample → all engines → workbook with zero formula errors, every tab ties, and `formulas`-library evaluation of the live cells (LibreOffice is blocked in this sandbox).
- Extend `validation/validate.py` to report per-engine tie-outs alongside classification accuracy.
- **Synthetic-data stress test, done 2026-07-08 (`docs/TAX_DECISIONS.md` §8; scripts were throwaway, not committed — see that section for the full inputs/outputs of each run):** every formula (SPM against the real code; MSPM/SRM/SCA/§263A(f) against this document's formulas, via standalone scripts) was run against non-trivial synthetic datasets exceeding the size/complexity of the worked examples above, with exact `Decimal`/`Fraction` arithmetic — all passed. (**Staleness note 2026-07-09:** the §8 SPM run's recorded ratio figures (0.578915 etc.) reflect the PRE-correction SSCM denominator rule and are a point-in-time record, not current expected outputs — the §1.263A-1(h)(4) denominator fix in `docs/TAX_DECISIONS.md` §9 changes SPM's computed ratios.) This is validation-by-larger-example, not implementation testing (MSPM/SRM/SCA/§263A(f) still have no engine code); when `test_mspm_srm.py`/`test_sca.py`/`test_interest.py` are actually built in Phase B/C/D, they should include, IN ADDITION TO the regulation's own tiny example, an analogous larger/multi-entity fixture exercising: MSPM's negative-residual and negative-on-hand floors; SRM's multi-facility combination and write-down-scope decisions; SCA's mixed-SSCM-eligibility-within-one-pool gate; and Phase D's per-source sequential consumption tracking under a NOT-fully-exhausted interest pool (the one branch this pass didn't exercise, since the worked test deliberately hits the proration branch instead) — these are exactly the cases the tiny golden examples are too small to catch a regression in.
- **Phases F/G/H — HONESTY NOTE, ADDED 2026-07-09: unlike Phases B/C/D, these three phases have NO hand-derived or IRS-sourced golden worked example yet.** Before coding `compute_174`/`compute_263a4_5`/`compute_59e`, build at least one worked numeric example per phase the same way MSPM's Example 1 and SRM's fixture were built — Phase F: a domestic + foreign R&E fact pattern exercising the mid-year-convention 15-year and elected-≥60-month schedules plus a 2022-2024 catch-up computation; Phase G: a covered-transaction fact pattern exercising the bright-line date, the 70/30 success-fee election, and a separate start-up-cost fact pattern exercising the $5,000/$50,000 phase-out and 180-month schedule (with a syndication sub-case to confirm the permanent-non-amortization routing doesn't leak into the amortized bucket); Phase H: a qualified-expenditure fact pattern exercising at least the IDC 60-month and one 10-year category, gated correctly by the entity-type/AMT-exposure screen. Do not treat Phases F/G/H as build-ready until each has a fixture with independently-verifiable arithmetic, matching the discipline every other phase in this plan was held to.
- **Runtime Pipeline mechanics (Tax-Basis TB, Basis Reconciliation, §1060 allocation) — ADDED 2026-07-09, same honesty discipline applies:** no worked example exists yet for any of these three either. Minimum fixtures before build-ready: Tax-Basis TB — a TB with at least one BTD (book depreciation ≠ tax depreciation) that ties book total = tax-basis total + Σ(BTDs), by cost center; Basis Reconciliation — a fixture per asset category (3)-(6) in the new section above with a NON-ZERO pre-existing book-capitalized amount, confirming only the delta posts, PLUS the "book exceeds tax-required" flag-not-negative-post case; §1060 — the regulation's own residual-method example structure (7 classes, an aggregate consideration that exactly exhausts Classes I-VI leaving a small Class VII residual, AND a stress case where consideration is LESS than the sum of Class I-VI FMVs, confirming the error flag fires rather than a silent negative Class VII).

## Effort & risk
Four phases, each comparable to the classifier rebuild. Highest risk: §263A(f) — **not because T.D. 10034 is unverified (it's confirmed real, see Phase D above and `docs/TAX_DECISIONS.md` §7d/§7e), and not because the core mechanics are unvalidated math (the snapshot-vs-average formula, the eligible-debt exclusions, the sourcing order, and the multi-unit proration all now check out against a larger synthetic multi-loan/multi-unit scenario, per §8/§8d above) — but because NONE of it has been implemented as actual code yet.** Every MSPM/SRM/SCA/§263A(f) formula in this plan, however many times re-verified against primary text and stress-tested against synthetic data, is still a specification, not a running engine — `engines/interest.py`, `engines/sca.py`, and the MSPM/SRM branches of `compute_unicap`'s dispatcher do not exist in the codebase today. Treat "validated by primary text" and "validated by synthetic-data stress test" as necessary, not sufficient — implementation risk (a coding mistake in translating a now-correct formula into Python) remains fully open until Phase A-D actually ship, and each phase needs its own implementation-level test suite built from these worked examples (see "Verification" above for which additional larger-scale fixtures each engine's golden tests should include beyond the regulation's own tiny examples). Also high-risk: data ingestion quality (real TBs/asset registers are messy — the Data Quality tab is the mitigation). Classification accuracy (~78% raw / ~84% high-confidence precision, ~35% review queue on messy data — re-verify against a live `validate.py` run, this number moves as the taxonomy is hardened) means asset/CIP inputs should be reviewed, not blindly trusted — the review-queue + Data Quality tab surface this. Remaining unverified-citation risk (see the opening disclaimer above): `§1.471-11` only — `§1.263(a)-1/-3` and `§1.266-1` were verified 2026-07-09 against complete authoritative eCFR text supplied in-session, and the §448(c) threshold against Rev. Proc. 2025-32. The §9 mirrored/search-channel provenance caveat is LIFTED for everything covered by the in-session text (§§1.261-1..1.266-1 and §§1.263A-0..-15); it survives only for material sourced exclusively from the earlier mirror/snippet retrievals (principally the PRE-T.D.-10034 old §1.263A-11(e) associated-property text underlying the pre/post-2025 dual-regime note, which by definition is not in the current text).

**Phases F/G/H risk profile, ADDED 2026-07-09 — different shape from A-D's, not comparable severity:** these three
were researched via WebSearch (the canonical primary-source hosts — Cornell LII, eCFR, IRS.gov — returned 403s at
the network/proxy level even via WebFetch this pass, an org egress-policy restriction, not a site-specific block;
see `docs/TAX_DECISIONS.md` §13 for the full methodology note), not a direct primary-text pull the way §§1.263A-1
through -15 eventually were (`docs/TAX_DECISIONS.md` §10). Confidence is markedly lower as a result. Specific open
items, do not resolve silently when building: (1) `§174D-DOMESTIC-ELECTIVE-UNVERIFIED` — whether post-OBBBA
§174(d)'s disposal-loss-disallowance rule reaches domestic R&E capitalized under the §174A(c) elective (as opposed
to mandatorily-capitalized foreign R&E, where it clearly applies); (2) `§57-MINING-CITE-UNVERIFIED` — the exact
§57(a) subparagraph for the mining exploration/development AMT preference; (3) `§59E-174A-ELECTION-CONFLICT` —
which period governs when a taxpayer elects both §59(e) (10-year) and §174A(c) (≥60-month) capitalization on the
same domestic-R&E dollars; (4) exact subparagraph lettering within Reg. §1.263(a)-4(c)/(d) for each intangible
category (the category list itself is confirmed at the policy level; the citations are not). **Recommend one
direct pull of 26 U.S.C. §§59, 174, 56, 57 and Reg. §1.263(a)-4 from a licensed research tool (Checkpoint/CCH/
Bloomberg Tax) before Phases F/G/H are built from this spec**, the same way the §263A regulations were eventually
pulled in full for Phases A-D. Separately, and independent of citation confidence: **no golden worked example
exists yet for any of the three** (see the "Verification" section's honesty note above) — that gap is a build
blocker in its own right, regardless of citation confidence, since every other phase in this plan was required to
clear that bar before being declared build-ready.

## Deferred / out of scope
Combined producer+reseller method; farming (§1.263A-4, see `docs/TAX_DECISIONS.md` §7d); the §1.263A-7 revaluation/§481(a) COMPUTATION (see the corrected method-change bullet below); the general (g)(4)(iii) non-SSCM mixed-service-cost alternative (direct reallocation / step-allocation methods — see the SSCM section above); multi-business mixed-service-cost apportionment (§1.263A-1(h)(7) — see the SSCM section above); live Form 3115 DCN mapping to the current Rev. Proc.; the EY-platform modules (§168(n), §163(j) as a standalone module — though §163(j)'s INTERACTION with §263A(f) ordering is now in-scope for Phase D, see above — §45X/§48D, cost seg). (§§1.263A-5/-6 are reserved sections with no content — confirmed 2026-07-09 against the §1.263A-0 outline and their published reserved titles ("qualified creative expenses" and "rules for foreign persons"), nothing there to scope in or out. §1.263A-13 (oil & gas) and §1.263A-14 (related-person average-excess-expenditure allocation) are also out of scope, noted 2026-07-09 for completeness; the §1.263A-9(g)(5) consolidated-group intercompany-lending rules are likewise out of scope for a single-entity tool, added 2026-07-09 full-text pass.)
**ADDED 2026-07-09, alongside Phases F/G/H:** computing the taxpayer's overall AMT (individual, §55/§56/§57) or CAMT (corporate, §55/§56A) LIABILITY — Phase H tracks the §59(e) preference-avoidance amortization ELECTION and its schedule, a real dollar-moving computation, but not the full AMT/CAMT return; the general oil & gas regime beyond the bare IDC §59(e)-election tracking (percentage depletion, other O&G-specific provisions — this tool has no oil & gas coverage otherwise, per §1.263A-13's existing out-of-scope note above, and Phase H does not change that); the §174(d) disposal-LOSS computation itself beyond flagging that a disposal event touches R&E-basis-bearing property (same boundary discipline as the §1.263A-7 revaluation computation above); indefinite-life/no-fixed-period intangible amortization determinations under §1.263(a)-4 (per-item SME call, not automated); and the exact scope line between capitalizable software development costs and routine debugging/maintenance under §174/§174A (flagged for SME review per Phase F, not automated).
**ADDED 2026-07-09, "anything else" completeness sweep (a dedicated research pass, not exhaustive of the entire Code — see `docs/TAX_DECISIONS.md` §14 for the full methodology and what else was considered and rejected):** §263(g) (interest/carrying charges on straddles — a real mandatory capitalize-to-basis rule, but scoped to commodity/securities straddle positions under §1092(c), a specialized trading/hedging fact pattern this tool doesn't otherwise address; DEFERRED); §461(g) (prepaid interest/points for cash-method taxpayers — on closer look this is a DEDUCTION-TIMING rule, not a basis-capitalization provision: prepaid interest is a deferred expense item, not a component added to any asset's basis; note only, so the tool doesn't mistakenly let a user route points into a building's basis — Reg. §1.263(a)-2(e) actually EXCLUDES financing costs from property basis); §616/§617's MANDATORY baseline beyond the §59(e) elective-amortization angle already in Phase H (exploration/development costs are capital expenditures BY DEFAULT, with an election to currently deduct instead, and RECAPTURE on a mine reaching the producing stage that re-converts previously-deducted amounts back into basis — a real "default-capitalize / elect-to-deduct / recapture-reconverts" cycle §59(e) alone doesn't capture, but mining-industry-specific and low priority, same tier as the already-deferred oil & gas/depletion regime; DEFERRED); §194 (reforestation cost amortization election — a genuine parallel to the §59(e)/§195/§248 family of elective capitalize-and-amortize provisions, timber-industry-niche; DEFERRED, mention only for parity awareness).
**§266/§1.266-1 VERIFIED 2026-07-09 full-text pass** (this was one of the plan's three remaining unverified citations): §1.266-1(b)(1) confirms the classifier's §266 tier structure — electively capitalizable carrying charges are (i) annual taxes/mortgage interest/other carrying charges on UNIMPROVED AND UNPRODUCTIVE real property (an ANNUAL election, year-by-year); (ii) interest, employment taxes, materials taxes, and other necessary expenditures for real-property development/construction (election sticks until the work completes); (iii) transport/installation-related taxes and interest for personal property (until later of installation or first use); (iv) other, with Commissioner approval. Election mechanics ((c)(3)): statement filed with the ORIGINAL return — consistent with the classifier's `election_required` flag and the still-open §3 item 3 (auto-routing vs. confirmed election). Also confirmed from the §266 side: §1.266-1(a)(2) applies §§1.263A-8..-15 FIRST, then permits a §266 election for designated property "provided a computation... is not thereby materially distorted" — the mirror image of Phase D's (g)(1)(i) ordering rule, now confirmed from both directions.
**Corrected 2026-07-08:** partnership guaranteed-payment interest sourcing (§1.263A-9(c)(2)(iii)) was previously
listed here as "interest on flow-through entities (§1.263A-15)" — that citation was wrong (§1.263A-15 is effective
dates/transitional rules/anti-abuse ("transitional rules" added to this description 2026-07-09 — the prior
two-item summary omitted it), not flow-through interest) and the underlying mechanic is not actually out of scope;
it has been moved into Phase D's build list above as part of the excess-expenditure interest-sourcing order.
**Method-change bullet CORRECTED + PARTIALLY IN-SCOPED 2026-07-09 (`docs/TAX_DECISIONS.md` §9):** a prior draft
deferred §1.263A-7 entirely as "not touched by Phase A-D." That was overstated — per §1.263A-7(a), a taxpayer may
ADOPT a §263A method only in its FIRST year of resale/production activity; every other taxpayer switching methods
(including an existing SPM taxpayer moving to MSPM/SRM via this tool's `profile.method` input, or first-time flips
of `sscm_ratio_method`/`mspm_mixed_split_method`/HAR) is making a CHANGE in method of accounting — Form 3115,
beginning-inventory REVALUATION (as if the new method had applied in all prior years, via the facts-and-
circumstances / weighted-average / 3-year-average revaluation methods), and a §481(a) adjustment. The plan already
treats SMALLER elections as method-of-accounting events while leaving the top-level SPM/MSPM/SRM switch — the
biggest method change of all — unflagged. What stays deferred: the revaluation/§481(a) COMPUTATION engine. What
moves into Phase B now: (1) `EntityProfile.prior_year_method` (or `is_first_263a_year: bool`); (2) a hard warning
into the existing `unicap["warnings"]` channel (`METHOD-CHANGE-3115-481A-REQUIRED`) whenever computed method ≠
established method (same pattern for first-time election flips); (3) an input-contract note that in a year of
change, `beginning_inventory_471`/on-hand inputs must already BE §1.263A-7-revalued figures — the tool consumes
them, it does not produce them. The BTD schedule (input 2) is where a §481(a) adjustment naturally surfaces.
