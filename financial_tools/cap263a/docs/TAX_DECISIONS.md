# Taxonomy Decisions & Changes — §263A / §263(a) / §266 Capitalization Classifier

**To:** Tax SME (reviewer / approver)
**From:** Tax Technical Review
**Re:** Rebuilt taxonomy (`categories.yaml`, 133 categories) vs. original `_CategoryRef` (122 codes) plus CC-engine maps (`cc_reclass.yaml`, `generic_map.yaml`, `cc_zones.yaml`)
**Date:** 2026-07-01

**Purpose.** Give the SME an item-by-item basis to *approve* or *overturn* every substantive change made in the rebuild. Sources: original workbook hidden sheets `_CategoryRef`, `_CCReclassMap`, `_GenericExpMap`; IRS Practice Units COR-P-020 (producers), COR-P-021 (resellers), COR-P-006 (interest), COR-C-023 (self-constructed) — **these Practice Unit IDs are themselves unverified, see §7**. Net category count moved 122 → 132 (10 new codes; §5 item #49 `EX-ABNORMAL` later brought the total to 133); no codes were deleted.

---

## §1 — Tax-Bug Fixes

Each of these is a correction of a defect in the original taxonomy that would have produced a wrong tax answer.

| # | Change | Before | After | Citation | Severity | Recommendation |
|---|--------|--------|-------|----------|----------|----------------|
| 1 | **NO-OFFICER** (Officer Compensation) re-tiered | Tier1 = *Non-Operating*; MSPM/Resale/SelfConst/Interest = **N/N/N/N** (never capitalized) | Tier1 = *Mixed Service*; **M/M/M/M** (allocable via SSCM) | §1.263A-1(e)(3)(ii)(A); COR-P-020 (officers' comp allocable to production is a listed capitalizable indirect category; "overlooking officer compensation" named a **top audit issue**) | **High** — original permanently excluded a mandatory §263A cost pool item | **Approve** |
| 2 | **NO-INTCAP** (Capitalizable Interest) re-tiered + flagged | Tier1 = *Non-Operating*; interest code = **471**; `designated_property` absent/false | Tier1 = *§263A(f) Interest*; SelfConst/Interest = **F**; `designated_property: true` | §263A(f); Reg §1.263A-8 through -15; COR-P-006 (avoided-cost method) | **High** — interest was flowing into the §471/§263A cost layer instead of the separate §263A(f) avoided-cost computation, double-counting risk | **Approve** |
| 3 | **EX-BID** (Bidding / Proposal) reclassified | Tier1 = *Excluded*; **E/E/E/E** | Tier1 = *Additional §263A*; **I/I/I/I** (conditional — successful bids only) | §1.263A-1(e)(3)(ii)(T) — bidding expenses are a listed capitalizable indirect category | **Medium** — correct direction, but scope is conditional (see SME item #2) | **Approve direction / revisit scope** |
| 4 | **FO-PTAX** (Factory Property Tax) labor flags corrected | `is_labor: TRUE`, `labor_type: benefits` | `is_labor: FALSE`, `labor_type: ''` | §1.263A-1(e)(3)(ii)(L)–(M) (taxes/insurance are indirect **costs**, not labor); data-integrity fix | **Medium** — property tax mis-tagged as labor would corrupt any labor-based allocation / 1/3–2/3 split | **Approve** |
| 5 | **CC-reclass dead targets** (corporate zone) repointed | `MSC-RENT`, `MSC-DEP`, `MSC-UTIL`, `MSC-INS`, `MSC-PROF` (none exist in `_CategoryRef`) | `MSC-CORPRENT`, `MSC-CORPDEP`, `MSC-CORPUTIL`, `MSC-CORPINS`, `MSC-AUDIT` (all valid MSC codes → M/M/M/M) | Reg §1.263A-1(e)(4) (mixed service costs); mechanical fix (5 broken map rows) | **High** — every corporate-zone rent/dep/util/ins/prof-fee cost center hit a non-existent code and fell through to fallback, silently misclassifying MSC costs | **Approve** |
| 6 | **VAGUE-\*** generic-map routing changed | `_GenericExpMap`: VAGUE-ALLOC/ACCR/VAR/OTHER → **`compensation`** (→ in a production zone resolves to **DL-PROD**, a §471 direct cost) | VAGUE-\* → **`suspense`** (held for review; codes themselves are MSC, priority −15/−20) | §1.263A-1(e) (unidentified pooled/allocation costs are not per se direct labor); COR-P-020 audit issue "incorrect classification of mixed service costs" | **High** — unlabeled allocation/accrual/variance lines were being swept into direct production labor and fully capitalized | **Approve** |
| 7 | **GEN-COMM / GEN-FRT** added to generic map | `generic_map.yaml` had no `commission` or `freight` expense-type entries | `GEN-COMM: commission`, `GEN-FRT: freight` added (both MSC, priority −10) | Mechanical completeness fix; §1.263A-1(e)(4) fallback | **Low/Medium** — commission & freight cost centers previously had no generic fallback and could go unclassified | **Approve** |

---

## §2 — New Regimes / Codes Added (10)

New codes extend the tool beyond §263A inventory into §266, §263(a) transaction/intangible, and §263(a) tangible repair-vs-improvement. Each is scoped so it does **not** disturb existing §471/§263A routing (high `priority`, land/context-gated `cc_clues`, mostly N/A treatment columns).

| # | Code(s) | Regime / Scope | Citation | Severity | Recommendation |
|---|---------|----------------|----------|----------|----------------|
| 8 | **SEC266-TAX / -INT / -OTHER** | §266 carrying charges on unimproved/idle/held-for-development land (taxes, interest, other). Treatment N/A across all four §263A columns; `cap_vs_deduct: elective`, `election_required: true`; gated to `land` CC-zone | §266 / Reg §1.266-1(b)(1)(i)–(iv) | Correctly scoped as **elective** — good | **Approve** (note election dependency; see SME #3) |
| 9 | **SEC263A-TXN** | Facilitative transaction costs (M&A, debt issuance, due diligence, success fees) | Reg §1.263(a)-5 | Correctly scoped; `cap_vs_deduct: capitalize`, priority 5 | **Approve** |
| 10 | **SEC263A-INTANG** | Created/acquired intangibles (customer lists, covenants, trademarks, franchise, goodwill) | Reg §1.263(a)-4 / §197 | Correctly scoped | **Approve** |
| 11 | **SEC195-STARTUP** | Start-up / organizational / syndication costs | §195 / §248 / §709 | Correctly scoped; note these are amortizable, not purely "capitalize" | **Approve / minor revisit** (label nuance: §195/§248 elect-to-amortize, not permanent capitalization) |
| 12 | **SEC263A-IMPROVE** | Tangible-property **improvement** under BAR test (betterment/adaptation/restoration, UoP) → self-const/interest = 471 | Reg §1.263(a)-3 (BAR test) | Correctly scoped as capitalize | **Approve direction / revisit keywords** (see SME #4) |
| 13 | **SEC263A-REPAIR** | Tangible-property **deductible** repair / routine-maintenance & de-minimis safe harbor / materials & supplies → MSPM/Resale = M | Reg §1.263(a)-3(i)/(h)/(f); §1.162-3 | `cap_vs_deduct: deduct`; priority 4 (below IMPROVE's 5) | **Approve direction / revisit keywords** (see SME #4) |
| 14 | **NEG-263A** | Negative §263A adjustments (excess book depreciation, 471 add-backs, unfavorable M-1 reversals); MSPM/Resale = C; `allows_negative_adj: true` | §1.263A-1(d)(3); T.D. 9843 (negative adjustments); COR-P-020/-021 (negative §263A cost audit issue) | Placeholder code correct; **computation not yet built** (see Limitations #4) | **Approve as scaffold** |
| 15 | **DL-PENSION** | Production pension / 401(k) / profit-sharing / retirement as a **direct-labor benefit** (§471 producer cost); priority 1; `labor_type: benefits` | §1.263A-1(e)(3)(ii)(B)–(C) (pension/profit-sharing + employee benefits allocable to production) | Correctly scoped as capitalizable producer benefit | **Approve** |

---

## §3 — SME Decisions Required (human judgment)

These are defensible-but-debatable calls the tool cannot make on the facts alone. Each needs an explicit human decision.

1. ~~**DM-\* raw/direct materials MSPM column left as "471-Pre".**~~ **RESOLVED — SME approved 2026-07-08.** DM-RAW/-PKG/-COMP/-FRT/-DUTY's `mspm: 471-Pre` tagging (direct/purchased material, incl. inbound freight/duty, as pre-production §471 content) is **confirmed correct** for the MSPM pre-production absorption ratio. No code change was needed — the taxonomy was already tagged this way; this closes out the open question. Phase B (MSPM, not yet built) should implement the pre-production ratio using this existing tag without further debate.

2. **EX-BID conditional treatment (successful bids only).** The code now capitalizes bidding/proposal costs as Additional §263A, but §1.263A-1(e)(3)(ii)(T) capitalizes bidding costs **only for bids that are successful** (unsuccessful-bid costs are deductible). The taxonomy note flags "conditional," but the tool has no success/failure input. **Question:** Accept blanket "I" treatment (over-capitalizes failed bids) or require a success flag before capitalizing? **Recommend: revisit** — add a success indicator or route failed bids out.

3. **§266 land-context cost-center triggers + election dependency.** SEC266-TAX/-INT/-OTHER fire off `land` CC-zone keywords (`unimproved`, `vacant land`, `held for development`, `idle land`, `raw land`). §266 capitalization is **elective and annual** (Reg §1.266-1) — it is never automatic. **Question:** Should the tool auto-route land-context carrying charges to §266 (implying the election is/will be made), or hold them pending confirmation that a valid §266 election exists for that property/year? **Recommend: revisit** — treat as suspense/flag unless election is confirmed.

4. **SEC263A-REPAIR / -IMPROVE keyword scoping vs. departmental R&M.** Departmental "repairs & maintenance" cost centers route via the CC-engine to **FO-RM** (factory overhead, §471) or **GEN-RM** (MSC), **not** to the new §263(a) tangible-property codes; SEC263A-IMPROVE/REPAIR fire only on BAR-test / safe-harbor keywords (betterment, restoration, routine-maintenance safe harbor, de-minimis, UoP). **Question:** Is it correct that ordinary departmental R&M stays in the §263A overhead pool and only explicit improvement/safe-harbor language triggers the §263(a)-3 BAR analysis? This is defensible (avoids over-capitalizing routine plant R&M), but the boundary is keyword-fragile and a genuine improvement described in plain "repair" language will be missed. **Recommend: confirm scoping, revisit keyword coverage.**

5. ~~**SSCM labor ratio: should Additional-§263A-tier labor be in the ratio?**~~ **RESOLVED — SME approved 2026-07-08: reading (a), include in both numerator and denominator.** Purchasing/warehouse/buying-office labor (`PP-PURCH`/`ADD-WHLBR`/`RES-BUYING`, Additional §263A tier) is now summed into BOTH `production_labor` (numerator) and `total_labor` (denominator) in `analysis.py` `compute_unicap`, alongside §471 Cost labor — treated as already-established capitalizable labor, analogous to production labor, not excluded. **This changes computed dollar output** on any TB with material purchasing/warehouse/buying labor (§471 $200k/Mixed $50k/Additional §263A $80k/Excluded $300k example: ratio moved from 0.800 (old, exclude-entirely) to 0.848485 (new, reading (a))). Fixed and regression-tested (`test_sscm_labor_ratio_includes_additional_263a_tier_labor`); re-run any workpaper generated before this decision if purchasing/warehouse/buying labor was material.

---

## §3a — Residual High-Confidence Error Patterns (post error-mining, for SME awareness)

After the error-mining round (raw agreement 68.8% → 77.6%), the ~28 remaining high-confidence
disagreements on the validation set cluster into patterns that are deliberately NOT being
"fixed" by data tweaks, because they are tier-boundary judgment calls or need new categories:

1. **§471 vs Additional §263A boundary** (production planning, materials handling, warehouse
   staging labor): both sides capitalize — the disagreement rarely changes the tax answer,
   only which pool the cost sits in. Candidates for `acceptable_alt_tier1` labels if the SME
   agrees; not relabeled unilaterally.
2. **Banking codes' tier1** (BANK-ORIGINATE/-SERVICING/-APPRAISAL as Mixed Service vs the
   set's expected §263(a) Transaction/Intangible or Excluded): whether direct loan origination
   costs capitalize under §1.263(a)-4/-5 for tax (they generally do NOT follow book SFAS 91
   deferral) is a genuine SME call; changing these tiers changes real answers.
3. **Abnormal spoilage / dry-hole IDC** (expected Excluded, classified §471/§263(a)):
   correctly excluding these needs dedicated deductible categories (abnormal rework/spoilage;
   §263(c) IDC election) — new tax content, queued rather than guessed.
4. **§263(a) Elective bucket is unreachable from the taxonomy** (no category carries tier1
   `§263(a) Tangible` + `cap_vs_deduct: elective`): the Summary row and Asset Basis line are
   $0 unless an analyst overrides a Bucket cell. Adding an elective capitalize-repairs
   (§1.263(a)-3(n)) category is an SME decision.
5. **Expense lines containing "inventory"** ("Insurance - warehouse inventory", floor-plan
   interest): the bare "inventory" balance keyword occasionally grabs these at conf 85;
   narrowing it breaks the (far more common) bare "Inventory" balance line. Left for review.

## §4 — Known Limitations (SME should be aware)

1. **Only SPM is implemented; MSPM two-ratio and SRM combined-ratio are not yet computed.** The taxonomy *tags* costs as pre-production (`471-Pre`, `I-Pre`) and carries resale P/S/M codes, but the MSPM production/pre-production two-factor computation (COR-P-020) and the SRM purchasing + storage-&-handling dual absorption ratios (COR-P-021, incl. the beginning-inventory-in-S&H-denominator rule) are **not built**. Classifications will not yet produce MSPM/SRM adjustments.

2. **Per-asset / per-unit basis is deferred.** No unit-of-property or per-asset basis tracking. This limits §263A(f) interest (COR-P-006 requires unit-of-designated-property and APE per unit) and §263(a)-3 BAR (UoP-level) analysis; those codes classify but cannot yet compute at the asset level.

3. **DCN / authority citations are representative, not authoritative.** The reg/Practice-Unit citations embedded in `authority` fields are for reviewer orientation; they have **not** been validated as controlling for a specific taxpayer's facts, method, or year and should not be relied on as filing positions without confirmation.

4. **No negative-adjustment computation yet.** NEG-263A exists as a classification scaffold (`allows_negative_adj: true`), but the negative §263A cost computation (T.D. 9843; §1.263A-1(d)(3); the COR-P-020/-021 negative-cost audit issue) is **not implemented**. Negative adjustments must be computed manually for now.

5. **§263A(f) interest engine not built.** NO-INTCAP correctly routes to the §263A(f) layer, but the 7-step avoided-cost method (traced/nontraced debt, APE with compounding of prior capitalized interest, weighted-average rate) per COR-P-006 is not yet implemented.

---

## §5 — Hardening-Pass Corrections (post-review, 2026-07-01)

An independent multi-agent audit of the implemented layers (taxonomy, classification engine,
reader, SPM/SSCM math, workbook output) found and fixed the following. None of these change the
taxonomy's category count or scope (§1/§2 above) — they fix defects in the code that consumes it.

| # | Change | Severity | Citation / rationale |
|---|--------|----------|----------------------|
| 16 | **SSCM labor ratio denominator** (`analysis.py`) restricted to §471 Cost + Mixed Service labor. Previously summed *all* `is_labor` rows including Excluded-tier compensation (sales commissions, R&D labor), which could understate the capitalizable mixed-service share by up to ~85% whenever sales/R&D payroll was large relative to production payroll. | **High — wrong dollar answer** | Reg §1.263A-1(h)(4): the SSCM ratio is capitalizable mixed-service labor over total production + mixed-service labor, not total enterprise labor. |
| 17 | **Word-boundary keyword/clue/zone matching** (`engine.py`). All matching previously used raw substring containment, so short keywords/clues ("it", generic 2-3 letter abbreviations) matched inside unrelated words — e.g. a cost center named "Capital Projects" or "Credit Department" was silently zoned as corporate IT because both contain the letters "it". Fixed to word-boundary regex matching everywhere (desc keywords, combined keywords, cc_clues, zone detection). | **High — silent misclassification** | Mechanical/data-integrity fix; no reg citation, just correct string matching. |
| 18 | **"IT" cost-center zone restored.** The abbreviation expander turns "IT" into "information technology" *before* zone detection runs, so the zone rule needed the expanded phrase too (added to `cc_zones.yaml`) — otherwise fixing #17 would have broken the one legitimate "IT department" case it was trying to protect. | High (paired with #17) | Same. |
| 19 | **`NO-CHARITY` keyword set narrowed.** Bare `contribution`/`donation`/`gift` matched ordinary payroll benefit lines (e.g. "401k employer contribution") and mis-tagged them Non-Operating/charitable instead of a benefits/labor code. Replaced with specific phrases (`charitable contribution`, `charitable donation`, `charitable gift`, `donation to charity`). | **High — wrong tier, high confidence, no review flag** | §1.263A-1(e)(3)(ii)(B)–(C) (pension/benefits are capitalizable indirect costs, not charitable contributions). |
| 20 | **Confidence calibration applied to cost-center-reclassified lines.** A line reclassified purely by zone/cc-clue context (no direct account-description keyword) was previously exempted from the confidence cap, so it could report 70 confidence with no `LOW-CONF`/`REVIEW` flag — exactly the "zone-only match" case the calibration comment says must be flagged. | Medium — review-queue integrity | Consistency with the tool's own stated design intent. |
| 21 | **`GEN-FRT`/`GEN-COMM` now reclassify by cost-center zone** for the zones where the direction is unambiguous: `sales` → `EX-SALES`/`ADD-FRTOUT` (commission and freight in a sales cost center), `production` → `DM-FRT` (freight in a plant/production cost center defaults to inbound material freight), `r&d` → `EX-RD`. Previously these always fell to a flat Mixed-Service default regardless of department. **Warehouse and corporate-zone freight/commission remain unmapped** (genuinely ambiguous — could be inbound or outbound — left for SME review rather than guessed). | Medium | §1.263A-1(e)(4) fallback correctness. |
| 22 | **Reader hardening** (`reader.py`): a TB with no amount/debit/credit column now raises instead of silently producing $0 for every line; Excel formula-error literals (`#REF!`, `#N/A`, etc.) are filtered instead of becoming phantom line items; an accounting-negative amount with a dollar sign *and* a space before the parenthesis (`"$ (1,234.00)"`) now parses correctly instead of silently zeroing; picking among multiple candidate sheets with no name-hint match now raises requesting an explicit `sheet=` instead of arbitrarily taking the first one in workbook order; the header-row scan window was widened from 20 to 100 rows (real ERP exports commonly have 20–40 preamble rows). | High (several silent-corruption paths) | Data-integrity, not tax-law. |
| 23 | **Report generation crash on an empty trial balance** (`report.py`) — a zero-row TB inverted the conditional-formatting range (`O4:O3`), which openpyxl rejects, aborting workbook generation entirely. Guarded. | High (hard crash) | — |
| 24 | **Tab ordering bug** (`report.py`) — the "move Summary Dashboard to the front" offset was computed assuming it was always the *last* sheet; since it's actually created 2nd (right after Classified TB), the reorder silently did nothing and "Classified TB" stayed first, contradicting the documented "Tab 1 = Summary Dashboard" contract. Fixed to compute the offset from Summary's actual current index. | Medium (contract violation, not wrong numbers) | — |
| 25 | **`get_taxonomy()` dead-code landmine in the `=PY()` blob** (`build_pyexcel.py`) — the assembled Python-in-Excel source contained two definitions of `get_taxonomy()`: the shim's (returns the live taxonomy) and the *real* `taxonomy.py`'s (calls `Taxonomy()`, which needs the file-loading `_load()` the assembly strips out). The real one executed last and silently shadowed the shim's, so any code path that fell back to the no-argument `get_taxonomy()` (the same fallback `engine.classify()` uses in the CLI) would raise `NameError`. It didn't fire in practice only because the bootstrap always passes `tax=` explicitly — a landmine, not a guarantee. Fixed by re-binding `get_taxonomy()` after all modules are inlined, so the shim's version always wins. | High (latent crash, single-source-of-truth risk) | — |

An independent adversarial re-verification of the 9 items above (fresh agent, no access to the fix
rationale) confirmed all fixed and found two further items, both from the same underlying report:

| # | Change | Severity | Citation / rationale |
|---|--------|----------|----------------------|
| 26 | **"401(k)"/"403(b)" IRC-shorthand mangled by the parenthetical stripper** (`engine.py` `normalize()`). The blanket "strip anything in parens" regex treated "(k)" the same as a narrative aside, turning "401(k) employer match contribution" into "401 employer match contribution" — destroying the "401k" keyword and, combined with #19 above being only a keyword-list fix (not a matching-pipeline fix), letting the line fall through to `NO-CHARITY` again via item #27's mechanism. Added a targeted pre-step that converts `\d(letter{1,3})` → `\dletter` (`401(k)`→`401k`, `403(b)`→`403b`) before the generic parens-stripper runs, so real narrative asides are still stripped normally. | High (real payroll GLs write it exactly this way) | Data-integrity, not tax-law. |
| 27 | **A code with zero real signal could still "win" purely on a nonnegative `priority` default.** `taxonomy.py`'s keyword index is built word-by-word (so a single word from a multi-word keyword phrase, e.g. "contribution" from `NO-CHARITY`'s "charitable contribution", pulls that code into the candidate pool even when the full phrase never matches). If that code's *only* score contribution ends up being its `priority` (0 for `NO-CHARITY`) while every other real candidate has a negative-priority generic fallback, `NO-CHARITY` won outright — not on a coin-flip tie-break, but because 0 > any negative number. `engine.py` now detects a winning candidate with an empty match-method list (i.e. zero keyword/clue/zone/fuzzy signal) and reroutes it to `VAGUE-OTHER`/REVIEW instead of accepting a no-evidence tier1. Verified this does not change the 250-line validation accuracy numbers (identical before/after), i.e. it only affects genuinely no-evidence cases. | Medium-High (systemic; not limited to the 401(k) case — confirmed ~40 other keyword words share the word-index over-inclusion pattern) | Consistency: a classification with literally no supporting evidence must never present as a specific, confident-looking tier. |

All fixes are covered by new regression tests (`test_engine.py`, `test_analysis.py`, `test_reader.py`,
`test_report.py`, `test_pyexcel.py`, `test_taxonomy.py`) and the §263A(f) worked example in
`docs/BUILD_PLAN.md` was independently re-derived with exact `Decimal` arithmetic after the prior
version was found not to reconcile with its own stated formula (see that document's Phase D
section for the corrected, fully-shown quarterly table).

A third audit round (four fresh agents covering `model.py`/`pipeline.py`/`cli.py`/`export_reference.py`,
the validation harness itself, a deeper substantive pass on `categories.yaml`, and one more adversarial
re-check of every prior fix) found the following. The validation harness itself was confirmed
computationally clean (all 250 lines genuinely scored, no silent skips, confidence bands match
`engine.py`'s real output space, the regression test calls the same function as the printed report) —
two low-severity governance gaps noted below (items 33-34), not measurement bugs.

| # | Change | Severity | Citation / rationale |
|---|--------|----------|----------------------|
| 28 | **Bare single-word keywords on `BS-ASSET`/`REV-OPER` silently dropped real income-statement costs out of the analysis entirely** (`taxonomy/categories.yaml`) — worse than mis-bucketing, since `Balance Sheet`/`Revenue` tiers are excluded from every waterfall bucket (`analysis.py` `_NON_IS_TIERS`), not just deducted. `"revenue"` matched `"Cost of Revenue - Materials"`; `"land"`/`"investment"`/`"goodwill"` matched `"Land Development Costs"`, `"Marketing Investment Expense"`, `"Goodwill Amortization"` — all at confidence 85 with no review flag. `"goodwill"` was also duplicated verbatim on `SEC263A-INTANG` (capitalize) with the balance-sheet code winning the tie, silently un-capitalizing what should have been a §1.263(a)-4 intangible position. Narrowed `BS-ASSET`'s keywords to `land account`/`land at cost`/`land held for use`, `investment account`/`marketable securities`/`short-term investment`/`long-term investment`, removed `goodwill` (now solely owned by `SEC263A-INTANG`); removed bare `revenue` from `REV-OPER`, added `total revenue`. | **High — costs silently vanish from the entire analysis, not just mis-tagged** | Same generic-keyword-overreach pattern as the already-fixed items #19/#27, but on the two tiers where the consequence is worst. |
| 29 | **`export_reference.py` round-trip corrupted every originally-empty `keywords`/`cc_clues` list into `['None']`.** A blank Excel cell reads back as Python `None`; `str(None)` = `"None"`, which survived the `"|"`-split and truthy-filter. Verified 35 categories with legitimately empty `cc_clues` picked up a spurious `"none"` clue after an export/reload round-trip, polluting cost-center-zone matching for the Python-in-Excel rebuild path specifically. Fixed to `str(v or "").split("|")`. | **High — silently pollutes the `=PY()` workbook's matching, not the CLI** | Single-source-of-truth risk: the whole point of `export_reference.py` is that the Excel and CLI paths classify identically. |
| 30 | **`export_reference.py`: `tier3`/`tier2` lost empty-string identity (became `None`) on round-trip, and the category `note` audit-trail field (present on `EX-BID`/`NO-INTCAP`/`NO-OFFICER`, documenting prior fixes) was silently dropped entirely** — not read into `_CAT_COLS` at all. Fixed both. | Medium (data-quality / audit-trail loss, no classification impact) | — |
| 31 | **`model.py`: `TBLine` had no `__post_init__` coercion**, unlike `EntityProfile`. `TBLine(amount=None)` or `TBLine(amount=1234.56)` (a plain float) constructed without error, then crashed deep inside `analyze()`'s `Decimal` arithmetic with a confusing `TypeError` far from the actual mistake — reader.py itself always hands a `Decimal` so this never fired via the CLI, but any other constructor (tests, future readers, direct API use) hit it. Added the same coercion pattern `EntityProfile` already uses. | High (confusing failure mode for any non-reader.py caller) | — |
| 32 | **`cli.py` had no error handling** — a missing input file dumped a raw multi-frame traceback (`zipfile`/openpyxl internals) instead of a clean message, and negative `--gross-receipts`/`--ending-inventory`/`--ape`/`--avoided-rate` were accepted silently (a negative gross-receipts trivially satisfies the small-business exemption test, silently routing every line to Deductible regardless of actual entity size). Wrapped the pipeline call in try/except → clean `error:` message + exit 1; added a `>= 0` check on all four numeric flags before use. | High (raw traceback to the user; silent wrong-mode entity sizing) | — |
| 33 | **`pipeline.py`: the output-filename tag built from `--entity` wasn't path-sanitized.** `--entity "Acme/Sub LLC"` silently created an unintended subdirectory via `os.path.join`; a crafted `--entity "../../etc"` could write outside `output_dir`. Sanitized to `[^\w\-]` → `_`. | Medium (path-injection risk if entity name is ever attacker-influenced) | — |
| 34 | **`reader.py`'s ambiguous-sheet guard (item #22) didn't check whether candidate sheets structurally look like a trial balance before raising** — a workbook with one title/cover sheet and one real TB sheet (whose name doesn't match `_TB_SHEET_HINTS`) now falsely demanded an explicit `sheet=` even though only one sheet had TB-shaped columns at all. Added a `_looks_like_tb()` check (has an account-description column plus an amount/debit/credit column) that filters candidates before the ambiguity check fires — only raises when 2+ candidates are genuinely TB-shaped. | Medium (regression against a common real workflow, introduced by fix #22 itself) | — |

Two items were deliberately **not** silently fixed and instead added to §3 as SME decisions: whether Additional-§263A-tier labor (purchasing/warehouse/buying) belongs in the SSCM ratio (§3 item 5 — three defensible reg readings, material dollar swing), and the hardcoded (not data-driven) "defensible difference" carve-out in the validation harness (`validate.py`) — low severity, but flagged so future additions to the carve-out require an explicit reviewer decision rather than a code-only change with no data trail. *(The carve-out was subsequently made data-driven: each exempt line now carries `acceptable_alt_tier1` + `alt_reason` in `validation_set.json`.)*

A fourth round (true end-to-end run with live-formula evaluation, a deep lexicon audit, and a practitioner-workflow review) produced the following. Items marked ⚠ change computed dollar output.

| # | Change | Severity | Citation / rationale |
|---|--------|----------|----------------------|
| 35 | ⚠ **Negative additional-§263A pool guard** (`analysis.py`). A pool that netted negative silently produced a negative absorption ratio and a negative "capitalized to inventory" figure rendered green in the workbook. Now emits explicit warnings — including the **T.D. 9843 / Reg §1.263A-1(d)(3)(ii)(C)** rule that a >$50M producer may not include negative adjustments under the SPM (MSPM required) — surfaced on the Summary tab and CLI stderr. Zero/negative §471-pool anomaly likewise warned. | **High — wrong-sign tax number presented as final** | T.D. 9843 |
| 36 | ⚠ **Phrase-level lexicon replacement** (`taxonomy.py`/`engine.py`). Word-by-word substitution made **76 of 425 lexicon entries silently dead** (every multi-word key) and let 2-letter abbreviation keys that are real words corrupt text: "Toledo **OH**" → corporate zone, "**PR** agency retainer" → payroll, "Continuing **ed**" → emergency department, "Repairs **or** maintenance" → operating room. Replaced with longest-first word-boundary phrase substitution; pruned 9 dangerous keys (`or/oh/ed/pr/wi/co/er/sub/cap`) and 3 dangerous cc synonyms (`press/batch/management: …`); repaired dead-end synonym values; hyphenated abbreviations ("Deprec-Mfg") now expand. Revived entries were checked for regressions (e.g. `401k expense`'s dead value would have destroyed a live keyword — repaired). | **High — silent misclassification + 18% of the lexicon dead** | Data-integrity |
| 37 | ⚠ **INV-BOOK re-tiered to Balance Sheet.** A book-inventory *balance* was tier1 §471 Cost, so a routine balance-sheet inventory line ($2M in the e2e test) inflated the §471 pool and distorted the absorption ratio; "Machinery & equipment" balances similarly leaked in via cost-center clues (BS-ASSET now carries the `&`-spelled keyword). Reserve/obsolescence keywords moved to NEG-263A (IS-side negative-adj scaffold). | **High — §471 pool overstated by balance-sheet amounts** | §471; ending inventory is an `EntityProfile` input, not a TB expense line |
| 38 | **Construction-loan interest now reaches the §263A(f) layer.** "Interest expense - construction loan" hit plain NO-INT (Non-Operating) at conf 85 because the immune-tier bonus outvoted the §263A(f) keyword. The immune bonus is now suppressed when a §263A(f)/§266 code has a direct description-keyword hit (it exists to stop *department* pull, not to bury explicit regime keywords); NO-INTCAP gained the `land` cc-clue. Plain "Interest expense" is unchanged. | **High — interest-cap candidates invisible to the regime layer** | §263A(f); COR-P-006 |
| 39 | **Contra lines routed correctly**: "Sales returns and allowances" (contra-revenue) was Excluded/deductible expense (inflating both IS and deductible totals); "Purchase discounts"/vendor rebates (§471 contra credits) landed in production-labor codes via cc-clues. Now REV-OPER and DM-RAW respectively. Bare "land"/"land holdings" cost-center keywords added to the §266 land zone. | Medium | §471 / §1.263A-1(e) |
| 40 | **Calibration gap closed** (`engine.py`): the clue/zone-only confidence cap (40) sat exactly at the review threshold (<40), so garbage matches were LOW-CONF but never REVIEW-queued. Cap is now 35 — such lines land in the review queue. | Medium — review-queue integrity | — |
| 41 | **Workpaper usability** (`report.py`/`cli.py`/`pipeline.py`): Summary label "= Adjusted currently-deductible" was stored as a *formula* and rendered #NAME? in Excel (fixed); Classified TB gained autofilter + frozen header, red/orange conditional formatting (review/low-conf), **Method (why)** and **Zone** provenance columns (the audit trail for defending a coding on exam), and a Bucket data-validation list (a typo'd bucket silently dropped the line from every SUMIFS); Summary now shows both review and any-flag counts, a **Cautions** block (computation warnings + reader data-quality notes), a stale-§448(c)-threshold caveat for years not on file (2027+ silently used the 2026 figure), an unimplemented-method warning (`--method MSPM/SRM` silently computed SPM), and a note that only the waterfall is live (tabs 3-5 need a re-run). CLI gained `--sheet` and prints all warnings; reader warnings are captured into the result and rendered in the workbook. | Medium-High (trust/professional-standards) | — |
| 42 | **Performance** (`engine.py`): per-call `re.compile` thrashed the regex cache (~90% of runtime on a large TB). Cached patterns: **145 → ~1,900 lines/sec** (10k-line GL: 69s → ~5s). | Medium | — |

Validation after this round: raw agreement 65.6% → **68.8%**, +defensible 71.2% → **72.8%**, high-conf precision 75.0% → **77.4%**, review queue 38%. The e2e harness also confirmed the full workbook evaluates with **zero formula errors** (via the `formulas` library) and the `=PY()` bootstrap executes end-to-end with classifications identical to the CLI.

### §6 — Red-Team Round (three adversarial agents: hostile input, tax-wrongness, single-source divergence)

| # | Change | Severity | Citation / rationale |
|---|--------|----------|----------------------|
| 43 | ⚠ **`=PY()` workbook diverged from the CLI on the ONE path that runs in Excel** (`export_reference.py`). Blank cells come back as `None` via `iter_rows` (tested) but as `float('nan')` via the real `xl(...).values.tolist()` pandas path (untested). NaN is truthy AND `nan != nan`, so the None-scrubber missed it — 36 categories got a phantom `nan` keyword/clue, and every classified row in the Excel deliverable diverged from the CLI on `cap_vs_deduct`/`authority`/`labor_type`; a cost center containing the token "nan" even flipped confidence 40→70 and dropped its review flag. Added a NaN-aware scrubber (`v != v`); added a regression test that drives the actual pandas path. | **High — the "identical by construction" guarantee was false on the production surface** | Single-source-of-truth |
| 44 | **Spreadsheet formula injection** (`report.py`, `build_pyexcel.py`). A trial balance is untrusted; openpyxl stores any string beginning with `= + - @` as an ACTIVE formula, so a client account description `=HYPERLINK("http://evil","click")` would execute (phishing/exfiltration/DDE) when a reviewer opens the output workbook. All user-text cells now pass through a `_defuse()` that prefixes a formula-guard apostrophe and forces text type. | **High — code/URL execution in the deliverable from hostile input** | Security (CWE-1236) |
| 45 | ⚠ **NaN/±Infinity amounts poisoned every total and defeated the tie-check** (`reader.py`). `Decimal("NaN")`/`Decimal("Infinity")` parse fine, flow through `analyze`, blank out in the workbook, and make the printed "tie check" `$NaN` — the integrity self-check silently defeated; `"Infinity"` additionally crashed the CLI. `_to_decimal` now rejects non-finite values (→ 0). | **High — silent wrong totals + integrity-check bypass** | Data-integrity |
| 46 | **Absorption ratio >100% and inconsistent ending inventory unchecked** (`analysis.py`). `additional_capitalized_to_inventory = ending_inventory_471 × (additional/§471)` with no bound: a $100 §471 pool + $500k additional pool + a user-typed $10M ending inventory produced **$50 billion** capitalized, rendered green, unflagged. Now warns when the absorption ratio exceeds 100% and when ending inventory exceeds the §471 pool. | **Critical — headline number can be absurd and unflagged** | §1.263A-2(b) |
| 47 | ⚠ **SSCM ratio not bounded to [0,1]** (`analysis.py`). A `mixed_alloc_ratio` override of 3.5 capitalized 350% of the mixed pool (mixed_deductible went negative); a negative production-labor line produced a negative ratio. A service-cost allocation ratio is definitionally a fraction — now clamped to [0,1] with a warning on either side. | **High — over/under-capitalization of the mixed pool** | Reg §1.263A-1(h) |
| 48 | ⚠ **Negative-capitalization guard only covered the §263A pools** (`analysis.py`). A contra/reversal line driving §263(a) Mandatory, §266, or §263A(f), or the aggregate `capitalized_total`, negative (an economically impossible negative addition to basis) was unflagged. The guard now covers every capitalized bucket and the total. | **High — wrong-sign capitalization presented as valid** | — |
| 49 | ⚠ **Abnormal spoilage capitalized into §471 at conf 70, no review flag** (`categories.yaml`, `engine.py`). Abnormal spoilage/rework/casualty is DEDUCTIBLE (excluded from §471 per Reg §1.263A-1(e)(3)(iii)); the production-department zone bonus buried it in the FO-SCRAP §471 pool. Added an `EX-ABNORMAL` Excluded category and generalized the zone-bonus suppression (already used for §263A(f)/§266/negative-adj codes) so an explicit exclusion keyword in the description isn't overridden by department context. NORMAL scrap correctly stays §471. This *raised* validation accuracy (77.6%→78.4% raw, 82.8%→84.0% precision). | **High dollar** | Reg §1.263A-1(e)(3)(iii) |
| 50 | **Misc hardening**: the misleading "tie check" is relabeled a structural *partition invariant* (0 by construction — it does not validate classifications) in both the CLI and workbook, while the workbook's live *override* check (which does react to analyst edits) is kept; the CLI now catches XML `ParseError`/`OSError`/any unexpected error with a clean message instead of a traceback; the reader stops after a long blank run rather than iterating to an inflated `ws.max_row` (~1M rows from one stray cell); the entity-name output tag is length-capped (a ~300-char client name overflowed the 255-char filename limit). | Medium (assurance/robustness) | — |

Red-team items verified NOT exploitable: no user text is concatenated into the executable `=PY()` code blob (only into data cells, covered by #44); openpyxl blocks the control-char write path (invalid XML fails on read first); the small-business exemption boundary is correct (`≤` threshold per §448(c), verified at exactly $32,000,000 / $32,000,001 for TY2026); no dollar double-counting between the mixed-capitalized figure and the additional pool; assembly of the `=PY()` blob does not drop or mangle any of the round-4/5 constructs (`_pattern`, `_phrase_replacer`, `_IRC_PAREN`, `specialized_codes`) — 0 mismatches over a 42-description battery.

Validation after the red-team round: raw **78.4%**, +defensible **82.4%**, high-conf precision **84.0%**, review queue 35%. 93 tests (up from 82).

---

## §7 — Citation Accuracy Audit (read before relying on ANY authority/citation string in this tool)

Every `authority` field in `categories.yaml`, and every reg/T.D./Rev. Proc./Practice-Unit
citation elsewhere in these docs, was **written from model training knowledge, not looked up
against a primary source** (IRS.gov, a reg-text database, Westlaw/CCH). The tool has always
disclaimed this generally ("representative, not authoritative" — §4 item 3). A dedicated
fact-checking pass fact-checked a sample against the auditing agent's own knowledge and found
**multiple citations that were substantively wrong**, including a suspected fabricated
Treasury Decision number. This is a materially more serious finding than a generic
disclaimer conveys, so it gets its own section.

**Corrected (moderate-to-high confidence; not primary-source-verified when originally logged
2026-07-08 — see §7a for the subset since upgraded to VERIFIED against actual regulation text):**
- `NO-OFFICER` (officer comp): §1.263A-1(e)(3)(ii)(**A**) → **(B)**. The indirect-cost list
  runs (A) indirect labor, (B) officers' comp, (C) pension/related costs, (D) benefits — the
  original cite was off by one letter. **Since VERIFIED correct, §7a.**
- `DL-PENSION` (pension/benefits): §1.263A-1(e)(3)(ii)(**B)-(C**) → **(C)-(D)**. Same
  off-by-one-letter pattern, same direction — this looks systematic, not two independent typos.
  **Since VERIFIED correct, §7a.**
- `SEC263A-REPAIR` de minimis safe harbor: cited to §1.263(a)-**3(f)** → corrected to
  **§1.263(a)-1(f)** (the de minimis election lives in the general capitalization reg, not the
  tangible-property BAR-test reg). The routine-maintenance (-3(i)) and small-taxpayer (-3(h))
  cites in the same entry were already in the right section. Still not independently
  re-verified (§1.263A-1(e) text was retrieved and read for §7a but not §1.263(a)-1/-3).
- `EX-ABNORMAL` (abnormal spoilage): §1.263A-1(e)(3)(iii) → corrected to **§1.471-11(d)(2)(iii)**
  (a different regulation, §1.471-11, not retrieved in the §7a pass — still not
  independently re-verified).
- `NEG-263A` / the negative-pool warning (`analysis.py`, item #35/#48): the T.D. number guess
  (T.D. 9843 → T.D. 9942) was itself never verified and is now dropped rather than repeated —
  **the actual regulation pinpoint was wrong too and has since been corrected with real primary
  text, see §7a.**

**Flagged, deliberately NOT guess-corrected** (a wrong replacement citation is worse than an
honest "unverified" label — these need a primary source, not a second guess):
- **`docs/BUILD_PLAN.md` "T.D. 10034 (Oct 2025)"** — the auditing agent has *no recollection of
  this T.D. number existing at all* and suspects outright fabrication. This is the single most
  serious item in this section: it was driving a proposed `tax_year`-gated computation change
  (eliminating the associated-property rule, narrowing improvement interest) in the still-unbuilt
  §263A(f) engine. **Do not build tax-year cutover logic against this citation without first
  confirming, from a primary source, that the T.D. exists and says what's described.** Flagged
  prominently in BUILD_PLAN.md itself. Still unresolved — §1.263A-8/-9/-12 (the §263A(f) regs)
  were not part of the §7a retrieval.
- `SEC266-INT`/`-OTHER` — §1.266-1(b)(1)(iii)-(iv): the carrying-charge list may only run
  three items (taxes/interest/other), which would make "(iv)" nonexistent. Still unconfirmed
  (§1.266-1 was not part of the §7a retrieval).
- `SEC263A-INTANG` geological/geophysical keywords — likely mis-grouped under §1.263(a)-4/§197
  (general intangibles); G&G costs may instead be governed by the dedicated **§167(h)** 24-month
  amortization provision. Flagged for the SME to either split into a dedicated code or confirm
  the current grouping applies on the relevant facts.
- **IRS LB&I Practice Unit IDs** (COR-P-020, COR-P-021, COR-P-006, COR-C-023, cited throughout
  `BUILD_PLAN.md` and this memo's §1 sources): the auditing agent does not recognize this ID
  format/prefix as matching real Practice Unit numbering and cannot confirm these exist as
  named. Treat as unverified placeholders — consistent with, but stronger than, the tool's
  existing "representative, not authoritative" disclaimer.
- **§448(c) $32,000,000 threshold for TY2026** — the $30M(2024)/$31M(2025) figures match the
  auditing agent's recollection of the published inflation-adjusted amounts; the $32M/2026
  figure is an unverified extrapolation of the pattern, not confirmed against the actual TY2026
  Rev. Proc.

**Also stale (doc-only, not a citation error):** `BUILD_PLAN.md`'s Phase D verification checklist
cited the §263A(f) worked-example total as $261,023.69 — a number from a version of that example
that was later found not to reconcile with its own formula and was corrected to $323,571.43
elsewhere in the same document (Phase D worked table, item #43-area). The checklist line was
never updated to match; corrected in this pass.

### §7a — Primary-source-verified corrections (2026-07-08, actual regulation text retrieved)

Everything above this subsection was written from model recall or search-engine snippet
summaries. The items below are different in kind: the **full text of 26 CFR §1.263A-1**
was directly retrieved and read (not summarized by a search engine, not recalled from
training) after `WebFetch` to Cornell LII/eCFR/Federal Register/govinfo.gov was found to be
blocked at this environment's network-policy layer (confirmed via the proxy status endpoint —
a gateway-level `403` on `CONNECT`, not those sites refusing the request). This is the first
citation work in this project done against an actual primary source rather than a proxy for one.

- **`EX-BID` bidding-cost citation CONFIRMED CORRECT, no longer flagged.** §1.263A-1(e)(3)(ii)(T)
  is exactly right: *"Bidding costs are costs incurred in the solicitation of contracts...
  ultimately awarded to the taxpayer... If the contract is not awarded to the taxpayer, bidding
  costs are deductible..."* Unsuccessful-bid costs are separately confirmed at
  §1.263A-1(e)(3)(iii)(J) ("Unsuccessful bidding expenses... are NOT required to capitalize").
  This directly grounds the still-open §3 item 2 SME decision (successful-bids-only gating) — the
  regulation text is now confirmed, only the implementation (a success/failure input) remains open.
- **`NO-OFFICER` (e)(3)(ii)(**B**) and `DL-PENSION` (e)(3)(ii)(**C**)-(**D**) CONFIRMED CORRECT**
  — the earlier moderate-confidence guesses were exactly right: *"(B) Officers' compensation...
  (C) Pension and other related costs... (D) Employee benefit expenses..."*
- **The $50M SPM negative-adjustment citation was WRONG in a way neither prior audit caught, now
  fixed.** The rule lives at **§1.263A-1(d)(3)(ii)(B)(1)**, not `(d)(3)(ii)(C)` as shipped in
  `analysis.py`/`categories.yaml` since the original build — `(C)` is a completely different rule
  (bars negative adjustments for cash/trade discounts under §1.471-3(b)). Verified full text:
  *"(B) Exception for certain taxpayers removing costs from section 471 costs... the following
  taxpayers may... include negative adjustments... (1) A taxpayer using the simplified production
  method... if... average annual gross receipts for the three previous taxable years... do not
  exceed $50,000,000... (2) A taxpayer using the modified simplified production method... and
  (3) A taxpayer using the simplified resale method..."* — this also **confirms MSPM and SRM have
  NO size restriction on negative adjustments** (only SPM is capped at $50M), which BUILD_PLAN.md
  had asserted but this project had never actually verified. Fixed in `analysis.py`, the
  `NEG-263A` taxonomy entry, and the regression test that asserts the warning text. The exact T.D.
  number for the underlying November 2018 amendment remains unconfirmed (the regulation's own
  applicability note dates paragraphs (d)(2)-(3) to "taxable years beginning after November 20,
  2018," matching Federal Register document 2018-24545 "Allocation of Costs Under the Simplified
  Methods" — but that document's T.D. number was not independently retrieved, so no T.D. number
  is cited in the fixed warning text).
- **SSCM (§1.263A-1(h)) has two allocation-ratio options, not one — the shipped `compute_unicap`
  implements only the labor-based ratio.** Full verified detail moved into `docs/BUILD_PLAN.md`'s
  new dedicated SSCM section (placed before Phase B, since SSCM is shared infrastructure every
  engine reuses). Headline: producers may elect either the labor-based ratio (`compute_unicap`'s
  current implementation) or a much-broader production-cost ratio (denominator = essentially every
  cost in the trade or business, including marketing/selling/distribution costs this tool
  otherwise treats as walled-off `Excluded`); resellers are restricted to labor-based only. This
  is genuinely new information this project did not have — not a citation fix, a scope gap.
- **Still NOT covered by this retrieval** (different regulation sections, not fetched this pass):
  §1.263(a)-1/-3 (de minimis/BAR-test citations), §1.471-11 (abnormal spoilage), §1.266-1 (§266
  carrying charges), §1.263A-3 (SRM mechanics), §1.263A-8/-9/-12 (§263A(f) interest, including
  the "T.D. 10034" fabrication concern). **§1.263A-2 (MSPM) was subsequently retrieved and
  verified — see §7b below**, closing out what was the single largest open item in §7a.

### §7b — §1.263A-2 (MSPM) primary-source verification (2026-07-08, same-day follow-up)

The user supplied the full text of 26 CFR §1.263A-2 directly (same retrieval method as §7a —
this tool's `WebFetch` remains blocked to the primary-source sites). This closed the one
open item §7a explicitly flagged as unresolved: **how MSPM splits SSCM-capitalized mixed
service costs between its pre-production and production absorption ratios.**

- **CONFIRMED, verbatim, exactly matching the earlier lower-confidence WebSearch lead:**
  §1.263A-2(c)(3)(iii)(B) allows either "the proportion of direct material costs to total
  section 471 costs" or "the proportion of pre-production labor costs to total labor costs"
  — a taxpayer election, both real. A 90% de minimis election applies to this split too
  ((c)(3)(iii)(C)). Full detail and the regulation's own three worked examples (Examples 4-6)
  moved into `docs/BUILD_PLAN.md`'s MSPM section.
- **Found two mechanics this plan had never had at all, not just wrong**, both of which move
  real dollars in the MSPM formula: the **residual pre-production additional §263A costs**
  (the portion of pre-production additional costs not absorbed into pre-production ending
  inventory rolls INTO the production ratio's numerator — omitting this understates the
  production ratio) and the **direct materials adjustment** (net direct materials that
  entered production during the year, added to the production ratio's denominator). The
  plan's prior MSPM formula (`pre_production_ratio*ending_inv_471_preprod +
  production_ratio*ending_inv_471_prod` with no residual/adjustment terms) was a
  simplification that would have produced a wrong number even with correct inputs.
  Confirmed by reproducing the regulation's own Example 1 by hand: $284,400 additional §263A
  allocable to ending inventory, matching the text's stated result exactly (worked in
  BUILD_PLAN.md's MSPM section, replacing the plan's prior hand-built 143,000 illustration
  as the canonical test fixture — the regulation's own numbers are more defensible than a
  constructed example).
- **Also confirmed:** the HAR (historic absorption ratio) election mechanics — a 5-year
  qualifying period (not 6 as the plan previously guessed) with a year-6 recomputation check
  against a ±0.5 percentage point corridor; and a $200,000 total-indirect-costs de minimis
  rule (§1.263A-2(b)(3)(iv), applies to MSPM via (c)(3)(v)) that zeroes additional §263A costs
  entirely for small producers — not previously in this plan at all.

**Bottom line for the SME/reviewer:** every citation in this tool should be treated as a
starting point for research, not a verified filing position, until confirmed against a primary
source. §7a shows the gap between "search-engine-plausible" and "actually reads the regulation"
is not hypothetical — it found a real, previously-uncaught wrong citation in shipped code
(the $50M rule's pinpoint cite) sitting right next to two guesses that turned out to be exactly
right. Both outcomes are reasons to keep verifying, not stop.

---

### §7c — IRS LB&I Practice Unit cross-checks (2026-07-08, same-day follow-up)

The user supplied four IRS LB&I units (Practice Units and a Concept Unit) directly as PDFs:
COR-P-021 "Examining a Reseller's IRC 263A Computation" (rev. 11/07/2024), COR-P-006 "Interest
Capitalization for Self-Constructed Assets" (rev. 02/01/21), COR-C-023 "Section 263A Costs for
Self-Constructed Assets" (07/15/21), and COR-P-020 "Producer's 263A Computation" (rev.
11/07/2024). **These are LB&I audit-technique guides, not binding law** — each explicitly states
"this document is not an official pronouncement of law, and cannot be used, cited or relied upon
as such" — but they are IRS-authored secondary interpretation and a strong independent
cross-check against §7a/§7b's primary-source regulation reads.

- **SRM/SPM method-availability gate — a real gap, not just a citation issue.** COR-P-021 Step 2
  (citing §1.263A-3(a)(2)(i)/(a)(4)(ii)/(a)(4)(iii)/(a)(5)) states a reseller with **more than de
  minimis** production activity may use **SPM but NOT SRM** — this plan's SRM section previously
  only had a soft `method_conflict:True`/"recommend SPM/MSPM" framing for a generic de minimis
  test, not a hard method-availability bar. Also newly found: a **private-label goods carve-out**
  that restores SRM eligibility even above the de minimis threshold. Both added to
  `BUILD_PLAN.md`'s SRM section as a build-blocking gate, not a soft warning.
- **§263A(f) de minimis designated-property exclusion — previously entirely missing.** COR-P-006
  (citing §1.263A-8(b)(4)) confirmed a 90-day-or-fewer production period with total production
  expenditures ≤ $1,000,000/days-in-period is excluded from designated property altogether — a
  cheap, real early-out this plan had never included. Also newly found: the **eligible-taxpayer
  AFR-plus-3 election** (§1.263A-9(e), $10M gross receipts test, distinct from the $25M/$26M
  §448(c) small-business threshold already tracked) letting small producers skip the weighted-
  average-interest-rate computation, and the **120-day cessation-period election** (lower
  priority, flagged as a stretch goal). Both added to `BUILD_PLAN.md`'s Phase D.
- **Confirmed, not changed:** COR-P-020 independently reproduces the exact SSCM labor-ratio and
  production-cost-ratio formulas already verified from the primary §1.263A-1(h) text in an
  earlier round of this session — no discrepancy found, a good sign the earlier primary-source
  read was accurate.
- **CORRECTED 2026-07-08 (§7e): the claim in this bullet was FALSE and has been retracted.** This
  entry originally asserted that "COR-C-023's three cost-allocation methods (specific
  identification, burden rate, standard cost) and the 90% mixed-service-department de minimis
  election match what's already in Phase C/the SSCM section; no changes made there beyond noting
  the match." A subsequent multi-agent audit (§7e) found this was not actually checked carefully:
  Phase C's driver-share formula implements ONLY specific identification — burden rate and
  standard cost are not addressed anywhere in Phase C, despite both being real, independently
  electable methods under COR-C-023. The 90% rule comparison was also wrong: COR-C-023 states a
  one-sided rule (≥90% deductible → may elect zero allocation), not the two-sided (≥90%→100%,
  ≤10%→0%) rule Phase C's text claimed. See §7e for the full correction and the fixes made to
  `BUILD_PLAN.md`. This stands as a caution about this document's own audit trail: a "no changes
  made... beyond noting the match" entry can itself be wrong if the underlying comparison wasn't
  done rigorously — treat past verification entries as claims to spot-check, not settled fact,
  same as any citation in the plan itself.
- **Still not independently verified from these four units:** the §263A(f) compounding mechanic
  and the traced/nontraced excess-expenditure math in `BUILD_PLAN.md`'s Phase D worked example
  were cross-checked structurally against COR-P-006's own worked example (Corporation X, Units
  A/B, avoided-cost sub-steps A-E) and match in structure and formula, but COR-P-006's numbers
  were not re-derived by hand this pass — do that before treating Phase D's 323,571.43 fixture as
  doubly-confirmed.

---

### §7d — §1.263A-4 (farming) and §§1.263A-7 through -15 (change in method + interest capitalization) primary-source verification (2026-07-08, same-day follow-up)

The user supplied the full primary text of 26 CFR §1.263A-4 (farming businesses), §1.263A-7
(change in method of accounting for §263A costs), and §§1.263A-8 through -15 (the complete
interest-capitalization regulatory scheme underlying Phase D — designated property, the avoided
cost method, unit of property, accumulated production expenditures, production period, oil/gas
special rules, related persons, and effective dates/anti-abuse).

- **"T.D. 10034" resolved — it is REAL, not fabricated.** A prior citation-accuracy audit round
  (§7, before any primary text had been retrieved) flagged "T.D. 10034 (Oct 2025)" in
  `BUILD_PLAN.md` as **under active suspicion of fabrication**, and `BUILD_PLAN.md` carried a
  hard warning not to build tax-year-gated logic around it without verification. The now-retrieved
  primary text confirms T.D. 10034, 90 FR 47582/47583 (Oct. 2, 2025), is a real amendment to
  §1.263A-8(d)(3) and §1.263A-11(e)-(f), effective for tax years beginning after October 2, 2025.
  **This is the second time in this session a flagged-unverified citation turned out to be exactly
  right** (the first being the SSCM-split formula in §7b) — a reminder that "unverified" is a
  statement about confidence, not a prediction of wrongness, and that guesses need confirming in
  both directions before being trusted OR discarded.
- **What T.D. 10034 actually changed (previously only guessed at) — confirmed:** APE for an
  improvement to existing property is limited to the improvement's own capitalized costs
  (§1.263A-11(e)) — the plan's prior guess ("interest narrowed for improvements") was correct.
  **What was newly found, not previously guessed at all:** a mid-production-purchase rule
  (§1.263A-11(f)) — APE for property purchased for further production before being placed in
  service includes the full purchase price plus subsequent production costs. **What was NOT
  confirmed and has been dropped from the plan:** the "associated property rule eliminated" half
  of the prior guess — no "associated property" rule appears anywhere in the retrieved text of
  §§1.263A-8 through -15; that detail may have been a hallucinated elaboration riding along with
  an otherwise-correct T.D. number, or may live in text not yet retrieved. Treat it as unconfirmed,
  not as false — the distinction matters for how confidently the plan's silence on it should be read.
- **Phase D's avoided-cost-method pseudocode (`APE_avg`, `traced_applied`, `excess`,
  `avoided_interest`, WAIR) was checked against §1.263A-9(b)/(c) primary text at the time —
  ⚠ RETRACTED 2026-07-08, see §7e: this "no discrepancy found" claim was WRONG.** A subsequent
  red-team pass (part of §7e) found the check here was not actually rigorous: the pseudocode's
  open/close-APE-averaging approach does not match §1.263A-9(b)/(c)'s measurement-date-snapshot
  mechanic, and understated the golden worked example by ~16% ($323,571.43 vs. the corrected
  $376,428.57). See §7e for the full correction. Leave this entry as a visible example of how a
  confident "cross-checked... no discrepancy found" claim can itself be wrong — the fix is to
  re-verify by independently re-deriving the answer, not to trust a prior verification pass's own
  self-report, however confident it reads. The de minimis designated-property exclusion (§1.263A-8(b)(4), 90-day/$1,000,000-per-day)
  and the eligible-taxpayer AFR-plus-3 election (§1.263A-9(e), $10M gross receipts) added to
  `BUILD_PLAN.md` in §7c were both confirmed to match the primary text exactly, including the
  $10,000,000 figure and the "3 percentage points" language. The cessation-period mechanic
  (§1.263A-12(g)) and its caution about traced-debt interest becoming nontraced for *other* units
  during a suspension were also confirmed verbatim.
- **Two lower-priority items newly found, not yet in the plan:** the 15-day repayment election
  (§1.263A-9(g)(7), prevents a weighted-average-interest-rate "mismatch" when nontraced debt is
  repaid just before a measurement date) and the simplified inventory method (§1.263A-9(g)(3), a
  materially different algorithm for inventory-only designated property using inventory-age
  segmentation and a compounded interest factor instead of per-unit avoided-cost tracking). Both
  noted in `BUILD_PLAN.md` as stretch goals, not required for the Phase D MVP.
- **§1.263A-4 (farming) and §1.263A-7 (change in method of accounting) are OUT OF SCOPE for this
  tool, not silently ignored.** §1.263A-4 is a specialized vertical (preproductive-period rules
  for plants/animals in a farming business — a wholly different fact pattern from the
  reseller/producer/SCA/interest scope this tool targets) with its own election mechanics
  (§263A(d)(3)), casualty-loss exceptions, and unit-livestock-price inventory method — nothing in
  the current `BUILD_PLAN.md` scope touches farming, and this decision explicitly does not add it.
  §1.263A-7 governs the §481(a) beginning-inventory revaluation mechanics when a taxpayer changes
  its §263A accounting method (facts-and-circumstances / weighted-average / 3-year-average
  revaluation methods) — relevant only to a "Method Changes" deliverable, which the original
  scoping doc placed in a later, not-yet-reached phase (Phase 4/Tab 5, Form 3115/§481(a)), not
  Phase A-D. If the SME later wants either regime built, it needs its own phase and this same
  primary-source verification treatment — do not retrofit either into the existing Phase B/C/D
  specs described above.

---

### §7e — Full multi-agent audit of BUILD_PLAN.md against all primary/secondary text supplied this session (2026-07-08)

At the user's request, four parallel subagents independently re-derived every specific claim in
`BUILD_PLAN.md` against the actual regulation/Practice-Unit text already supplied in this session
(not summaries of it, and not trusting the plan's own "VERIFIED"/"CONFIRMED" labels) — one each
for Phase D (§263A(f)) against the full primary text of §§1.263A-8 through -15, the SRM section
against Practice Unit COR-P-021, Phase C (SCA) against Concept Unit COR-C-023 and Practice Unit
COR-P-020, and a fourth agent checking the document's internal consistency (stale cross-references,
self-contradictions, Phase A schema sufficiency). Findings were consolidated, and `BUILD_PLAN.md`
was then corrected section by section. This is the most consequential verification pass of the
session — it found a real methodological error in the plan's hardest engine, a false verification
claim in this very document (§7c, now corrected above), and a genuine self-contradiction between
two sections of the plan that would have caused the tool to misapply SSCM.

**Highest-severity finding — Phase D's avoided-cost-method formula did not match the regulation.**
The plan averaged each period's opening/closing APE before comparing it to traced-debt principal.
The regulation (§1.263A-9(b)/(c), confirmed by its own worked Example 3) instead evaluates traced
debt and excess expenditures **at each measurement-date snapshot**, and only afterward averages
those snapshot results. Independently re-deriving the plan's own golden worked example under the
regulation's actual mechanic (confirmed by hand calculation, not just the auditing subagent's
claim) gives **$376,428.57** (traced $180,000.00 + excess-expenditure $196,428.57) — not the
plan's original **$323,571.43** (traced $176,250.00 + avoided $147,321.43), an understatement of
about 16%. `BUILD_PLAN.md`'s Phase D section has been rewritten with the corrected formula, the
corrected worked example, and several previously-missing mechanics found in the same pass:
eligible-debt exclusions (§1.263A-9(a)(4)), the excess-expenditure interest-sourcing order
(nontraced debt → below-AFR related-party debt → partnership guaranteed payments, the last of
which was previously mis-cited to §1.263A-15 in the Deferred/out-of-scope list when it actually
lives in §1.263A-9(c)(2)(iii)), the ordering rules against §163(d)/(j)/266/469/861, a corrected
cap rule (the pro-rata cap applies only to the excess-expenditure pool, not the combined
traced+avoided total), a corrected AFR-plus-3 election description (it forecloses debt tracing
entirely, not just substitutes a rate), a corrected cessation-period description (excludes
weather/permit/design-flaw delays "inherent in the production process"), a corrected
production-period-end test (PIS alone is not enough; production activities must also be complete,
per the regulation's own homebuilder-finishing example), a missing §1221(l) carve-out and missing
§1.263A-8(b)(3) exclusions in the designated-property test, and a missing related-person cost/
activity aggregation requirement for classification and production-period purposes.

**SRM section corrections:** the core combined-ratio formula itself was re-verified and confirmed
correct term-for-term against Practice Unit COR-P-021 (this is genuinely solid). Fixed: a missing
"goods valued below cost" exclusion from the ending-§471-costs base; a missing "total gross sales
includes inter-facility shipments" nuance in the dual-function storage ratio; a citation-mapping
error that attributed the general dual-function ratio formula to the 90/10-specific subpart
((c)(5)(iii)(C)) rather than the broader (c)(5)(iii); a mischaracterization of the
§1.263A-3(a)(4)(ii) scenario as elective when the Practice Unit states it as mandatory; and a
downgrade of the "purchasing/storage-handling MSC sub-split reuses the SSCM labor-ratio structure"
claim from "confirmed" to "not addressed in the source text retrieved so far" (Practice Unit Step
5 only describes the overall resale/non-resale split, not a further sub-split). Also flagged: the
private-label "carves back out of the more-than-de-minimis bar" framing is this plan's own
inference, not something the Practice Unit states.

**Phase C (SCA) corrections — the most consequential non-Phase-D finding:** Phase C's own text
said to "reuse SSCM's ratio" for mixed-cost pools **unconditionally**, directly contradicting the
SSCM section's own warning (added earlier this session) that most capital SCA assets likely do
NOT qualify for SSCM's routine-and-repetitive eligibility test and that Phase C "should default to
the general method... not silently assume SSCM eligibility." `BUILD_PLAN.md` now requires an
explicit `sscm_eligible` gate before applying the SSCM ratio to any asset, with a hard warning/flag
(not a silent misapplication) when an asset fails that gate, since the correct general-method
fallback remains out of scope. Also fixed: the false "three allocation methods match" claim from
§7c (Phase C only implements specific identification, not burden rate or standard cost); the
unsupported symmetric 90% de-minimis rule (the source only supports a one-sided version); a gap
around book-capitalized indirect costs' bucket-A-vs-B routing; and an unresolved (flagged, not yet
fixed, pending SME input) tension between the blanket officer-compensation M-tier treatment and
the fact-specific rules in COR-C-023/COR-P-020.

**Internal-consistency corrections:** a stale MSPM worked-example figure in the Verification
checklist (143,000, superseded by the corrected 284,400/3,284,400 figure elsewhere in the same
document); a stale "T.D. 10034 is unverified" warning in Effort & risk and the opening disclaimer,
contradicted by the plan's own later confirmation that it's real; an incomplete `EntityProfile`
field consolidation list missing three fields proposed earlier in the same phase; a
self-contradictory instruction to both "reuse the already-implemented $50M comparison" and "add a
new field" for the same gross-receipts figure in the same sentence; a misnamed
`avg_gross_receipts_10yr_test` helper for what is actually a 3-year-average-plus-since-1994 test;
an incomplete Deferred/out-of-scope list missing two items the SSCM section separately calls out
of scope; and an unresolved rounding-convention ambiguity between MSPM's example (which only
reproduces the IRS's own $284,400 figure with a rounded ratio) and Phase D's stated "no rounded
intermediates" preference — now documented explicitly as a per-engine convention rather than one
assumed global rule.

**What this pass does NOT cover:** none of these fixes have been implemented or tested against
real data yet — Phase A/B/C/D remain unbuilt. The corrected Phase D formula is now validated
against primary text but not validated by an actual implementation; treat that as the next
verification gate, not a substitute for this one.

---

### §7f — Red-team of §7e's own fixes (2026-07-08, same-day follow-up)

At the user's request, the §7e fixes were themselves red-teamed rather than accepted at face
value. Three parallel checks: (1) an agent given ONLY the raw regulation text and the numeric
facts of Phase D's worked example — with NO knowledge of either the original or "corrected"
answer, specifically to avoid anchoring bias — was asked to derive the answer completely from
scratch; (2) an agent re-read both files front to back hunting for new contradictions the §7e
edit itself might have introduced; (3) an agent checked every one of the ~35 individual findings
from the four original audit agents against the final edited text, to catch anything dropped,
watered down, or overstated in translation.

**Result on the highest-stakes item: independently confirmed.** Working from raw facts alone,
agent (1) derived $180,000.00 traced + $196,428.57 excess-expenditure = **$376,428.57**, matching
§7e's correction exactly, and gave an unambiguous "no" verdict — with quoted textual support from
both worked examples in §1.263A-9(c)(5)(ii)(B) and (f)(3) — that the original per-quarter
opening/closing-APE-averaging methodology is supported by the text. This is real independent
corroboration, not just a repeat of the same reasoning.

**But the red-team also found real bugs in the §7e fix itself — the meta-lesson here matters as
much as the tax-law lesson:**
- **A false "no discrepancy found" claim survived in this very document.** §7d's original Phase D
  entry asserted the avoided-cost-method pseudocode was "independently cross-checked... no
  discrepancy found" — directly contradicted by §7e's own "highest-severity finding" 45 lines
  later in the same file, about the identical formula. §7e corrected `BUILD_PLAN.md` but never
  went back to fix or flag the false claim still sitting in §7d — exactly the kind of staleness
  bug this whole audit chain was originally set up to catch, reproduced one level up, in the audit
  trail itself. Now retracted with an explicit note (see the §7d entry above).
- **Two more stale "reuses SSCM unconditionally" references survived the SSCM-eligibility-gate
  fix** — one in "Where we start" (near the top of `BUILD_PLAN.md`), one in "Sequencing & why"
  (near the bottom) — both describing Phase C as unconditionally reusing SSCM even though the
  Phase C section itself was rewritten to require an `sscm_eligible` gate first. Both now fixed.
- **A flagged-as-unconfirmed claim got upgraded to MORE confident, not corrected** — the SRM
  section's "#1 reseller audit error" superlative, which the original audit explicitly said was
  unsupported by the retrieved Practice Unit text, was rewritten in the §7e fix to read as if "the
  reg's own audit guidance" confirms it — the opposite of the requested downgrade. Now re-hedged.
- **The exact same unsupported symmetric 90% rule the audit flagged as a "repeated error in two
  places" was only fixed in one of them.** Phase C's copy was corrected; the SSCM section's
  identical claim ("if 90%+ are capitalizable, must allocate 100%") was missed entirely, sitting
  directly under a section header that claims primary-source verification. Now fixed.
- **A deliberately-hedged "low materiality, overstated inference" finding (§1.263A-11(e)'s
  improvement-APE scoping) got flattened into unqualified "CONFIRMED, not speculative" language**
  in both the fix and the write-up — the opposite of what the original finding asked to preserve.
  Now re-hedged.
- **Two more `EntityProfile` fields introduced elsewhere in the §7e edit (`sscm_ratio_method`,
  `interest_afr_plus_3_election`) were absent from the "consolidated" field list that exists
  specifically to fix this class of bug** — a second-order instance of the exact completeness gap
  the list was created to close. Now scoped explicitly rather than left to look complete.
- Minor: a pseudocode/declared-field-name mismatch in the SRM formula (shorthand names not
  matching the newly-declared `EntityProfile` fields) — fixed.
- Confirmed clean: no stray references to the four superseded dollar figures (323,571.43 /
  176,250.00 / 147,321.43 / 143,000) were found anywhere outside explicit "superseded by" framing;
  no leftover old-methodology (`day_fraction`/`APE_avg_i`) fragments were found in Phase D's Files,
  Verification, or Effort & risk subsections; all ~30 of the other ~35 original findings were
  incorporated faithfully with their original hedging level intact.

**A candid, unfixed observation from the red-team, not itself acted on:** the cumulative effect of
several audit rounds' worth of inline "CORRECTED 2026-07-08"/"GAP found"/"was stale" annotations
directly inside the operative spec text (rather than in a separate changelog) is now a real
readability cost — an implementer extracting "what do I actually build" for, e.g., Phase D, has to
read through several sentences of revision-history narrative per bullet to reach the current rule.
Not fixed in this pass; flagged as a candidate follow-up (move historical narrative to a changelog,
leave the spec text as a clean current-state-only statement) if the document keeps accumulating
audit rounds.

**Standing lesson:** this is the second time in one day a confident "verified"/"no discrepancy
found" claim in this document's own audit trail was itself wrong (the first being §7c's Phase-C
claim, retracted earlier). Treat every verification entry in this file — including this one — as
a claim to spot-check, not settled fact.

---

### Reviewer summary
- **7 bug fixes (§1):** all recommended **approve**; items #3 (EX-BID) and the scope items carry a "revisit scope" caveat.
- **8 new-code groups / 10 codes (§2):** all recommended **approve** (SEC195-STARTUP and the SEC263A-IMPROVE/REPAIR keyword set carry minor-revisit notes).
- **5 SME judgment calls (§3), 2 resolved:** items 1 (DM-\* pre-production tagging, confirmed correct as-is) and 5 (SSCM ratio includes Additional-§263A labor in both numerator and denominator — code changed, dollar output affected) approved 2026-07-08. Items 2 (EX-BID successful-bids-only), 3 (§266 land-context auto-routing vs. election confirmation), and 4 (repair-vs-improvement keyword scoping) remain open.
- **5 known limitations (§4):** computation layers (MSPM/SRM, §263A(f), negative adj., per-asset basis) are not yet built; classification-only at this stage.
- **27 hardening-pass corrections (§5):** found across four independent multi-agent audit rounds (initial, adversarial re-verification, previously-unaudited files + deeper taxonomy data, and end-to-end/lexicon/practitioner review), all fixed and regression-tested; items #16, #28, #35, #36, and #37 change computed dollar output — re-run any workpaper generated before this pass.
- **8 red-team corrections (§6):** three adversarial agents (hostile input / tax-wrongness / single-source divergence). Two are security-class (formula injection #44, the =PY() NaN divergence #43); five change or bound computed dollar output (#45–#49). All fixed and regression-tested (93 tests). Highlights: an unbounded absorption ratio could show a **$50 billion** capitalized figure unflagged (#46); a NaN amount silently defeated the integrity tie-check (#45). Nothing further should be relied on for filing without SME sign-off on §3/§3a.
- **Citation accuracy audit (§7):** 5 citations corrected (moderate-high confidence, still unverified), 6 flagged unverified/possibly fabricated rather than guess-corrected — most notably a suspected-fabricated Treasury Decision ("T.D. 10034") in BUILD_PLAN.md. **No citation in this tool should be relied on for a filing position without independent primary-source verification.**
- **Primary-source verification passes (§7a-§7f):** §1.263A-1 (SSCM/UNICAP general), §1.263A-2 (MSPM), §1.263A-3 (SRM), §1.263A-4 (farming), and §§1.263A-7 through -15 (change in method + full interest-capitalization scheme) regulation text retrieved and cross-checked directly; four IRS LB&I Practice/Concept Units (resellers, interest capitalization, self-constructed-asset costs, producers) cross-checked as independent secondary confirmation, then re-audited a second time by four parallel subagents (§7e) specifically checking whether the plan's own "VERIFIED" claims actually held up, then **red-teamed a third time (§7f)** — including an agent given only raw facts, with no knowledge of any prior answer, to independently re-derive the hardest number from scratch. Found and fixed: one real citation bug ($50M rule); two real missing MSPM mechanics (residual pre-production, direct materials adjustment); one real missing SRM method-availability gate (SPM-only above de minimis production) plus several smaller SRM gaps; one real missing §263A(f) de minimis designated-property exclusion and mid-production-purchase APE rule; a **materially wrong core avoided-cost-method formula** in Phase D that understated the golden worked example by ~16% (corrected from $323,571.43 to $376,428.57, then independently re-confirmed from scratch in §7f); **two separate false verification claims in this very document's own audit trail** (§7c's Phase-C-cost-methods claim, and §7d's Phase-D-formula claim — both retracted); and a genuine **self-contradiction** where Phase C silently misapplied SSCM to assets the plan's own SSCM section says likely don't qualify for it (plus two more instances of that same "reuses SSCM" staleness found and fixed in §7f, elsewhere in the document). Also resolved the "T.D. 10034" suspected-fabrication flag: the citation is real (§7d). **Standing lesson from this whole sequence: confident "verified"/"no discrepancy found" language in this document's own audit trail has twice turned out to be wrong — every entry, including this one, is a claim to spot-check, not settled fact.**
- **Synthetic-data full-calculation stress test + final decisions (§8):** every formula (SPM/MSPM/SRM/SCA/§263A(f)) run end-to-end against non-trivial synthetic datasets by five parallel subagents; a real shipped-code taxonomy bug found and fixed (§8, intro); four genuine specification gaps found and closed with explicit adopted decisions (§8a-§8d). `BUILD_PLAN.md` updated throughout and declared final/buildable as of 2026-07-08.
- **Full-text reconciliation, §§1.261-1..1.266-1 + §§1.263A-0..-15 (§10, 2026-07-09 second pass):** complete authoritative eCFR text supplied in-session — §9's provenance caveat lifted for everything it covers, and every §9 correction it covers confirmed verbatim. One §9 hedge reversed (the (h)(5) income-tax exclusion IS in the reg — partial retrieval of a correct paragraph had produced a false hedge); one adopted SME decision reversed (SRM 90/10 threshold = the (c)(5)(iii)(B) sales ratio, not an independent cost study); §1.263A-3(a)(4)(iv) resolved (production costs flow through the SRM formula itself); §1.263(a)-1/-3 and §1.266-1 verified (closing two of the three remaining unverified citations — only §1.471-11 remains); and ~10 genuinely new mechanics entered the plan (financial-statement-based §471 definition, MSPM+LIFO combined ratio, SRM handling exclusions incl. pick-and-pack, §1.263A-10 unit/common-feature rules, §1.263A-11(c) contract-payment APE rules, §1.263A-9(d) no-tracing election, aged-property production periods, de minimis safe harbor $2,500-authority note). Suite: 96 passing.
- **Pre-build completeness validation of the interview layer (§12, 2026-07-09):** three parallel agents (field-reachability audit, golden-example dry run, adversarial fresh-eyes gap hunt) pressure-tested Phase E as a spec, before any interview code exists. Two of the four golden worked examples FAILED as originally written — SRM's own `ending_inventory_471` multiplier (confirmed independently by two agents) and MSPM's `DM_purchased_during_year` were both silently un-asked — plus a load-bearing Gate 0/1 contradiction (an undefined `none-noncompliant` prior-method path) and 8 further Gate-7 per-unit/per-debt gaps (aged-property periods, producing-asset APE inputs, T.D. 10034 mid-production purchase price, pre-2025 associated-property inputs, `production_complete` vs. placed-in-service, AFR-plus-3's since-1994 look-back, the A/P fold-in sub-election, related-person activities-vs-costs). All fixed inline in Phase E, including a same-day follow-up that numbered Gates 3/5/6/7 into individual `Q#.#` nodes (Q3.1-Q3.22, Q5.1-Q5.3, Q6.1-Q6.5, Q7.1-Q7.23), closing the one item initially left as documentation debt.
- **Interview layer / question decision tree (§11, 2026-07-09):** review found the plan had no user-facing question inventory or conditional-ask logic (engine-first, fields scattered as implementation notes; three required questions absent entirely). Added BUILD_PLAN.md Phase E: declarative question graph (`taxonomy/interview.yaml` + `interview.py`), seven gates with exemption short-circuiting, FACT/ELECTION/METHOD-OF-ACCOUNTING tagging feeding the Form 3115 warning, per-facility/per-asset/per-unit/per-line sub-trees, and graph-validation + path tests.
- **Full regulation-by-regulation review, §§1.263A-1..-15 (§9, 2026-07-09):** five parallel agents, clause-by-clause against retrieved regulation text (mirrored/search channels — canonical hosts blocked; provenance in §9). Five MATERIAL findings, all fixed: the shipped SSCM labor-ratio denominator was backwards on two counts vs (h)(4) (code + tests fixed — prior workpapers used a wrong ratio); the "one-sided 90% rule" correction from §7e was itself wrong (both sides exist at (g)(4)(ii), asymmetrically); Phase D's §1221 carve-out misread an eCFR rendering artifact as a nonexistent "§1221(l) patent provision" (it's the §1221(a)(1) inventory carve-out); the dropped "associated property rule eliminated" claim was actually TRUE (restored, with a pre/post-Oct-2025 dual-regime implication); a day-proration sentence contradicted the (f)(2)(iii) measurement-date convention. Plus: the SRM (a)(4)(ii)-vs-(a)(5) open question RESOLVED (taxpayer size), the MSC sub-split found prescribed at (d)(3)(i)(F), the §1.263A-7 method-change gap partially in-scoped, the §448(c) 2026 threshold verified ($32M), a tax-shelter bar added to the exemption, and ~30 smaller citation/scope corrections. Suite: 96 passing. Four standing lessons recorded (§9.8).

---

## §8 — Synthetic-data full-calculation stress test and final decisions (2026-07-08)

Five parallel subagents each built a non-trivial synthetic dataset (larger and messier than the
regulation's own tiny textbook examples) and ran the full calculation for one of SPM (against the
real shipped code), MSPM, SRM, SCA, and §263A(f) (against this document's/`BUILD_PLAN.md`'s
formulas, via standalone throwaway scripts using exact `Decimal`/`Fraction` arithmetic, not
committed to the repo). Every documented formula computed correctly on every scenario tested — no
arithmetic error survived this pass, across SSCM-election variants, 90% de minimis shifts,
dual-function facilities, multi-loan tracing, and cross-unit pro-rata proration. Two categories of
finding resulted.

### A real bug in already-shipped code (not a build-plan gap)
The SPM subagent built a 33-line synthetic trial balance and ran it through the actual `analyze()`/
`compute_unicap()` code. All UNICAP arithmetic matched independent hand-verification exactly, but
the classifier itself mis-tagged one line: **"Finished goods warehouse storage costs"** (a
production-cost-center P&L line) classified as `INV-BOOK` (Balance Sheet) instead of `ADD-FGWH`
(Additional §263A) — $78,450.25 of real capitalizable cost would have silently vanished from the
income statement entirely. Root cause: `INV-BOOK`'s bare `"finished goods"` keyword is a substring
of `ADD-FGWH`'s own `"finished goods warehouse"` keyword; `INV-BOOK`'s Balance-Sheet immune-tier
scoring bonus (+25, `engine.py`'s `IMMUNE_TIERS` mechanic) plus its cost-center clue hit on
"warehouse" (+20) outscored `ADD-FGWH`'s kw+cc+zone total (95 vs 90). **Fixed 2026-07-08:**
`taxonomy/categories.yaml`'s `INV-BOOK` keyword narrowed from `"finished goods"` to `"finished
goods inventory"` — still catches genuine balance-sheet descriptions ("Finished goods inventory",
and via the still-present bare `"inventory"` keyword, "Inventory - finished goods"), no longer
bare-matches a cost-line description that merely mentions finished goods in passing. Verified via
(1) a new regression test, `test_fg_warehouse_costs_dont_collide_with_fg_inventory_balance` in
`tests/test_engine.py`, asserting the fix AND that the two existing balance-sheet test cases still
pass; (2) the full test suite (95 passing, up from 94); (3) the classification accuracy validation
harness (`python -m financial_tools.cap263a.validation.validate`) — 78.4% raw / 84.0%
high-confidence precision, byte-identical to the previously documented baseline, confirming no
regression across the 250-line labeled set.

### Four specification gaps, each closed with an explicit adopted decision

**§8a — MSPM: rounding order, and negative-residual/negative-on-hand floors.** The synthetic
dataset (a manufacturer with resale property, non-trivial mixed-service costs, and a
residual-pre-production absorbing 85% of its bucket — far harder-worked than the regulation's own
example, where the residual is a comparatively mild 60%) surfaced two gaps:
- *Rounding order.* The regulation's own Example 1 rounds the two absorption ratios to 2 decimal
  places before multiplying; it says nothing about whether the SSCM pre-production/production
  split proportion (an intermediate feeding one of those ratios' numerators) should also be
  pre-rounded. **Decision: round only the two absorption ratios; carry the SSCM split proportion at
  full `Decimal` precision.** This is an adopted convention (not textually mandated — the
  regulation's SSCM-split examples land on clean 25%/10% splits that don't test the question either
  way), chosen to avoid compounding rounding error into an intermediate with no textual basis for
  rounding it.
- *Negative residual / negative on-hand.* Both are structurally possible (a carried-forward
  beginning-inventory stockpile can make `pre_production_ratio * pre_production_471_on_hand`
  exceed `pre_production_additional_263A`; a WIP/finished-goods drawdown can make total on-hand
  smaller than the pre-production on-hand subcomponent) — demonstrated with concrete numbers in the
  subagent's script (residual −$37,695.00; on-hand −$119,630.00 in modified sensitivity runs). The
  formula text gives no floor. **Decision: floor both at zero, with `MSPM-NEGATIVE-RESIDUAL-FLOORED`
  / `MSPM-NEGATIVE-ON-HAND-BALANCE` flags for review** — mirrors the existing codebase's
  clamp-and-warn pattern (the SSCM ratio's own [0,1] clamp), and is required because a negative
  residual/on-hand balance flowing through unclamped would improperly reduce capitalized cost with
  no basis in the formula's own "not yet absorbed" logic.
- Also confirmed by the same test: the labor-proportion vs. direct-material-proportion SSCM-split
  election is not cosmetic — it moved the result by ~$9,860 on identical underlying facts. No
  action needed (the plan already documents this as a real election); noted here as confirmation
  the election matters enough to warrant clear UI/input handling when built.

**§8b — SRM: four gaps closed by a multi-facility synthetic dataset.**
- *On-site/off-site definition* — never actually stated anywhere in `BUILD_PLAN.md` before this
  pass, despite the plan's dual-function-storage rule depending on it. **Decision (adopted, not yet
  independently re-verified word-for-word against primary text in this session — flag before
  relying on it for a filing position): on-site = attached to/part of a retail sales facility
  (non-capitalizable); off-site = separate warehouse/distribution function (capitalizable).**
- *Multi-facility combination* — the formula's `storage_handling_costs` is one scalar; the plan
  never said how a reseller with more than one storage facility combines them. **Decision: sum each
  facility's own already-determined capitalizable share** (each facility independently run through
  its own 90/10 test or gross-sales-ratio fallback, then summed) — the only mechanic that is
  dimensionally coherent given the formula shape.
- *Write-down exclusion scope* — does the §1.263A-3(d)(3)(i)(C)(2) write-down exclusion reach
  `current_year_471_costs` (either ratio's denominator), or only the final `ending_inventory_471`
  multiplier? **Decision: only the final multiplier** — the textually narrower, more conservative
  reading (the cited rule speaks to "ending inventory," not costs incurred during the year). Tested
  impact of the rejected alternative: ~$4,800 swing on a ~$293K base — flagged as a candidate SME
  override, not a closed question beyond this plan's own working assumption.
- *90/10 threshold basis* — is the 90%+ threshold test itself measured by the same gross-sales
  ratio used as the fallback allocation formula, or an independent cost-attribution measure?
  **Decision: an independent cost-attribution measure** (e.g. a functional/time study or
  square-footage determination) — the regulation's threshold language speaks to "costs," the
  fallback ratio explicitly speaks to "sales"; treated as two different measures by the plain text.
- All four decisions are reflected in the SRM section of `BUILD_PLAN.md`, each marked `DECISION
  2026-07-08`.

**§8c — SCA: mixed-SSCM-eligibility-within-one-pool (the single most consequential gap this pass
found).** A synthetic scenario with four self-constructed assets sharing mixed-service pools — two
SSCM-ineligible, one eligible, sharing the SAME pool — exposed a question the existing 2-asset
worked example (which assumed uniform eligibility) never had to answer: what happens to a mixed
pool's allocation once eligibility isn't uniform across its target assets? Two orderings are each
individually consistent with the eligibility-gate rule (don't silently apply SSCM to an ineligible
asset) but diverge by tens of thousands of dollars on identical facts (confirmed: $59,778.74 vs.
$48,155.10 on one pool; $33,623.28 vs. $4,174.95 on another):
- *(A) Ratio-first:* apply the SSCM ratio to the whole pool, then driver-split only the resulting
  capitalizable dollars across the eligible assets alone. Matches the existing worked example's
  arithmetic under uniform eligibility, but under split eligibility it silently reroutes an
  ineligible asset's implied share of the pool onto a DIFFERENT eligible asset sharing that pool —
  overstating the eligible asset's basis and dropping the ineligible asset's share entirely.
- *(B) Split-first:* driver-split the FULL pool across every declared target — every asset assigned
  to the pool plus `NON_PRODUCTION` — first, preserving the general allocation formula's own
  literal target set (`{assets…, NON_PRODUCTION}`) and the pool's total-dollar conservation
  invariant, THEN gate each asset's own resulting dollar share through the SSCM eligibility test.

  **Decision: adopt (B).** Rationale: (A) has no basis in either the general allocation formula
  (which names every asset sharing the pool — not just the eligible ones — as a target-set member)
  or in COR-C-023; reallocating one asset's cost onto a different asset purely because the first is
  SSCM-ineligible is not a "reasonable allocation method," it is a basis-shifting error with no
  textual support. Under (B), an ineligible asset's own computed share stays visible in the
  allocation audit trail but is not booked to bucket B — flagged `SSCM-INELIGIBLE-NO-FALLBACK`,
  consistent with the existing interim-behavior rule (apply SSCM only when eligible; otherwise flag
  for human override, since the correct general-method fallback remains out of scope). This is an
  explicit SME-level policy call made where the primary text was genuinely silent on the combined
  scenario — not a re-derivation of settled law — and is flagged as open to override in
  `BUILD_PLAN.md`.

**§8d — Phase D: reconciling the sourcing-order prose with the proration pseudocode.** The
multi-unit/multi-loan synthetic test (two designated-property units, one with two traced loans
drawn at different dates, one with zero traced debt, a shared nontraced pool, an excluded
below-AFR related-party loan, and a scenario engineered so the pro-rata cap actually fires) found
an apparent conflict: the cap pseudocode sums all three interest sources (nontraced, below-AFR
related-party, §707(c) guaranteed payments) into one scalar and prorates the combined total as a
single pool, while the sourcing-order prose describes drawing on the three sources sequentially, in
priority order, "only up to" what's needed. **Resolved, not a real conflict — the two govern
different outputs.** The units-level total capitalized $ and the per-unit pro-rata split depend
only on the SCALAR total of all three sources combined, and are correct as written regardless of
source order — confirmed independently: whenever proration actually fires (the pool is fully
exhausted, by definition of the `if` branch), every dollar of all three sources gets consumed
regardless of order, so order cannot change either the total or the per-unit split in that case
(verified in testing: the two units' prorated amounts summed to the cap exactly, both as exact
`Fraction`s and at rounded-cents precision). What the sourcing-order rule actually governs is a
separate, additional output the pseudocode was missing entirely: how much of EACH source gets
"consumed" by capitalization (as opposed to remaining ordinary deductible interest, which matters
for the already-flagged §163(j)/§266/§469/§861 ordering elsewhere in Phase D). **Decision: add a
strict sequential draw-down computation, additive to (not a replacement for) the existing total/
per-unit math** — consume nontraced interest first up to the full excess-expenditure total, then
below-AFR related-party interest for any remainder, then guaranteed payments for any remainder
still outstanding; each source's unconsumed remainder stays ordinary deductible interest. This only
produces a different-looking number from a flat-consumption assumption when the pool is NOT fully
exhausted — a case this plan's own worked test doesn't exercise (it deliberately hits the proration
branch) and that the next `test_interest.py` build should add as a separate fixture. Also confirmed
in this test: the below-AFR related-party loan was correctly excluded from both the traced-debt
pool and the WAIR-nontraced pool (folding it in wrongly would have moved WAIR from 7.12% to 6.29%,
a material, non-hypothetical error the eligible-debt exclusion list exists to prevent).

### What this section does not cover
No engine code was written for MSPM/SRM/SCA/§263A(f) in this pass — the synthetic-data tests ran
against standalone throwaway scripts implementing the documented formulas, not against
`financial_tools/cap263a/engines/` (which does not yet exist). "Validated by synthetic-data stress
test" is a stronger claim than "validated by primary text alone," but it is still not "validated by
implementation" — a future engine-coding pass can still introduce translation bugs even from a
now-fully-specified formula. See `BUILD_PLAN.md`'s "Effort & risk" section (updated 2026-07-08) for
this exact caveat.

**Staleness note added 2026-07-09:** this section's SPM run figures (mixed_alloc_ratio 0.578915,
total_labor 2,475,356.45, etc.) were computed under the pre-§9 SSCM denominator rule and are a
point-in-time record of that run, not current expected outputs — the §1.263A-1(h)(4) correction in
§9 below changes SPM's computed ratios on the same inputs.

---

## §9 — Full regulation-by-regulation review, §§1.263A-1 through -15 (2026-07-09)

Five parallel review agents compared `BUILD_PLAN.md` (and the shipped `analysis.py`) clause-by-clause
against retrieved text of 26 CFR §§1.263A-1 through -15: one agent each for -1 (SSCM/general), -2
(MSPM), -3 (SRM), -8 through -15 (interest capitalization), and -4/-7 plus a whole-document
internal-consistency sweep.

**Retrieval provenance (applies to everything below):** the canonical hosts (ecfr.gov,
law.cornell.edu, govinfo.gov, irs.gov, federalregister.gov) are BLOCKED by this environment's egress
policy (403 CONNECT denials at the proxy). No agent fell back on model recall. Text was retrieved
via (a) GitHub-hosted eCFR mirrors — two independent mirrors diff-checked against each other with
verbatim agreement on every clause used (§1.263A-2 and §§-8..-15 were retrieved this way IN FULL,
including a pre-T.D.-10034 snapshot that proved decisive, see below), plus Cornell LII's own MathML
equation files for the MSPM ratio formulas; and (b) server-side WebSearch snippets of the canonical
pages, cross-checked across multiple independently-phrased queries (§§1.263A-1, -3, -4, -7 — snippet-
level, one fidelity notch below a full-page read). Items neither channel could pin down are flagged
"could not verify" in place, both here and in `BUILD_PLAN.md`. **Re-pull load-bearing quotes from
live eCFR before any filing position.**

### §9.1 — MATERIAL: the shipped SSCM labor ratio implemented the wrong denominator (FIXED in code)

§1.263A-1(h)(4) defines the labor-based allocation ratio as §263A labor costs / total labor costs,
where BOTH sides exclude labor included in mixed service costs, and the denominator includes the
labor of EVERY activity of the trade or business (production, resale, selling, R&D, G&A). The
shipped `compute_unicap` did the opposite on both counts: Mixed-Service-tier labor was IN the
denominator and Excluded-tier labor was OUT (`UNICAP_LABOR_TIERS = ("§471 Cost", "Mixed Service",
"Additional §263A")`), with a code comment asserting the incorrect rule and a BUILD_PLAN sentence
("This is what `compute_unicap` implements today") falsely claiming conformity — sitting directly
under the plan's own CORRECT prose description of (h)(4). The two errors bias in opposite
directions, so prior outputs were wrong in a fact-dependent direction. **Fixed 2026-07-09:**
`SSCM_DENOM_EXCLUDED_TIERS = ("Mixed Service", "Non-Operating", "Balance Sheet", "Revenue")` —
denominator now = all trade-or-business labor except MSC labor. Non-Operating labor is excluded as
outside the trade or business (a documented judgment call: officer comp was already re-tiered out of
Non-Operating, so this exclusion touches genuinely non-operating labor only). Both encoded-wrong
tests rewritten (`test_analysis.py`; e.g. the 3-line fixture's correct ratio is 100k/950k = 0.105263,
not 100k/150k = 0.666667). SME decision §3 item 5 (Additional-§263A labor in both numerator and
denominator) is unaffected — that labor is trade-or-business, non-MSC labor on both sides either way.
**Any workpaper generated before this fix used a wrong SSCM ratio.**

### §9.2 — MATERIAL: yesterday's "one-sided 90% rule" correction was itself wrong (REVERSED)

§1.263A-1(g)(4)(ii) contains BOTH sides of the department-level 90% rule, asymmetrically:
≥90%-deductible → may ELECT zero allocation; ≥90%-capitalizable → MUST allocate 100% to the
benefitted activity. The 2026-07-08 pass (§7e/§7f) declared the capitalizable side "unconfirmed —
do not rely," reasoning from IRS Concept Unit COR-C-023's silence — a false negative produced by
verifying against a secondary source instead of the primary text. Both BUILD_PLAN locations (SSCM
section, Phase C) re-corrected; the mandatory capitalizable side is an under-capitalization risk and
needs at least a warning flag when built. What survives from the earlier correction: (g)(4)(ii) is
department-level and still does not transfer to per-asset N-way driver shares. **Meta-lesson
(third instance in this file): a "correction" is only as good as the source it was checked against —
COR-C-023's silence was treated as the regulation's silence.**

### §9.3 — MATERIAL: Phase D's §1221 carve-out misread (FIXED)

§1.263A-8(b)(1)(ii)(A)'s Category-2 carve-out reads "not property described in section 1221(l)" in
the eCFR rendering — a digit-1→letter-l artifact (provable: §1221(l) does not exist; the same
retrieved section renders "(b)(l)(ii)(A)" where (b)(1)(ii) is meant; the rule dates to T.D. 8584
(1994) when §1221 ran (1)-(5)). The intended cite is §1221(1), today §1221(a)(1): INVENTORY /
held-for-sale property. The 2026-07-08 pass glossed it as "the patent/invention-sale capital-gain
provision" and told implementers to model a patents flag — wrong target entirely; the real effect is
that a producer's long-lived held-for-sale product (aircraft, vessels) escapes Category 2. Fixed;
implement `held_for_sale_by_taxpayer_or_related_person`, and the rendering artifact is documented in
the plan so nobody re-chases "§1221(l)".

### §9.4 — MATERIAL: the "associated property rule eliminated" claim was TRUE (RESTORED)

The 2026-07-08 T.D. 10034 verification concluded the claim "T.D. 10034 eliminated the associated
property rule" was unconfirmed/possibly hallucinated and directed it be dropped. Wrong: the
pre-amendment §1.263A-11(e)(1)(ii)(B) (retrieved this pass from a Feb-2025 snapshot) expressly
defined "associated property," and T.D. 10034's rewrite of (e) removed it — corroborated by the
Federal Register's description. The 2026-07-08 pass searched only the CURRENT text for a rule whose
whole point is that it no longer exists there — a structurally guaranteed false negative.
Restored, with a build implication: pre-Oct-2025 tax years still need the OLD (e) mechanics
(dual-regime improvement path keyed on tax year). **Meta-lesson: verifying a claim about a REPEALED
provision requires the before-text, not the after-text.**

### §9.5 — MATERIAL: Phase D's mid-year proration sentence contradicted the regulation (FIXED)

"Mid-year PIS/completion → prorate the sub-period by active days" contradicted §1.263A-9(f)(1)(iii)
(full computation period regardless of production-period start/end) and (f)(2)(iii) (APE counted
from the first measurement date after the period starts through the first after it ends). The
regulation's own examples zero out out-of-period measurement dates and always divide by the full
number of dates — no day-fraction proration anywhere. Fixed to the measurement-date convention (the
worked table already implicitly followed it; only the prose was wrong).

### §9.6 — Resolved SRM items (one WRONG-CITATION, one open question closed, one downgrade reversed)

- **Write-down exclusion re-cited:** the "goods valued below cost" exclusion is NOT in
  §1.263A-3(d)(3)(i)(C)(2)'s text — it is Practice Unit COR-P-021's gloss ON (C)(2). Rule kept,
  authority level corrected. What (C)(2) actually says: the multiplier is current-year-incurred §471
  costs remaining on hand (LIFO: the increment) — which itself was a missed constraint, now added
  (the multiplier is NOT the undivided ending balance).
- **The (a)(4)(ii)-vs-(a)(5) open question is RESOLVED: taxpayer size.** (a)(5) is just the de
  minimis DEFINITION (10%/10% presumption); its small-reseller example is where "not required to
  capitalize" comes from. Small reseller (now the §263A(i)/§448(c) exemption axis) → not required;
  larger reseller with the same de-minimis, incident-to-resale production → required, may elect SPM
  or SRM under (a)(4)(ii). No fourth `production_activity_level` state — gate on existing
  small-business machinery + new `production_incident_to_resale` flag.
- **The MSC purchasing/storage/handling sub-split is prescribed by the reg itself** at
  §1.263A-3(d)(3)(i)(F) — a one-step allocation (per-activity labor ratio × TOTAL mixed service
  costs, MSC labor excluded from both ratio sides), NOT the two-step capitalize-then-sub-split
  approximation previously assumed, and NOT "unaddressed in sources" as the 2026-07-08 downgrade
  concluded from the Practice Unit alone.
- Also: SRM bar cite corrected (a)(2)(i)→(a)(4)(i); private-label inference upgraded to confirmed
  ((a)(4)(i) opens "Except as provided in (a)(4)(ii) and (iii)") with the unrelated-party/
  incident-to-resale/sold-to-customers conditions attached; permissible variations (d)(3)(iii)(A)/(B)
  added (the beginning-inventory assert must be conditional); 1/3-2/3 rule nuances (all-or-nothing
  election, middle band still requires reasonable allocation); on-site/off-site definitions confirmed
  with (c)(5)(i)/(ii)(A)/(ii)(C) cites plus the retail-sales-facility exclusivity and
  physically-present-customer sub-definitions; the 90/10 threshold-basis DECISION's rationale
  rewritten (the reg supplies no attribution mechanism for the cost-worded threshold — the
  independent-cost-attribution reading stays as an SME call, explicitly open to the
  sales-ratio-collapse alternative).

### §9.7 — Other gaps closed (per-section)

- **§1.263A-1:** (h)(2) eligible property is four categories with (C)/(D) as alternative routes
  (Phase C's gate reshaped; materials/supplies-consumed-within-3-years arm added); (h)(5) "income-
  based taxes" exclusion hedged (Practice Unit formula says it, retrieved reg text says only
  MSC+interest); (h)(7) "any reasonable method" downgraded to paraphrase; §448(a)(3) tax-shelter bar
  added to `small_business_exempt` (code + test) with the §448(c)(2) aggregation documentation; 2026
  §448(c) threshold VERIFIED at $32M (Rev. Proc. 2025-32) — `THRESHOLDS` correct as shipped.
- **§1.263A-2:** (c)(3)(ii)(F) property-sold cost exclusion added as a global MSPM input filter;
  HAR refinements (extension = recomputation year + 5 following; both-ratios AND-test; mandatory
  resumption in the 3rd year after a failed recomputation; HAR unavailable to (c)(3)(v)-zero
  taxpayers); $200K de minimis sub-rules (excludable categories, related-party aggregation); the §8a
  negative-residual/on-hand DECISION's rationale rewritten — the reg's current-year-incurred on-hand
  definitions make negatives structurally impossible on compliant inputs, so the floors are DATA-
  ERROR guardrails, not tax-scenario handling (and the engine must document the input contract, not
  just clamp).
- **§§1.263A-8..-15:** the fabricated "TPP de minimis screen" deleted (non-designation follows from
  failing (b)(1)(ii)(A)-(C); the conjunctive shorthand missed a case and mis-ordered vs Cat 2);
  (b)(2)(iii) contemporaneous-records + estimate-exclusion requirements added; timber-exclusion
  phrasing re-confirmed verbatim; traced-debt definition pinpointed to (b)(2) with the
  unpaid-capitalized-interest component added; WAIR division-by-zero fallback added ((c)(5)(iii)(D):
  highest AFR when no nontraced debt); APE composition expanded per §1.263A-11(d)/(b)(1)/(b)(2)/(h)
  (producing-asset bases — the bulldozer rule — pre-production costs entering day one, dedication,
  installation) and -11(g) (related-person activities count, only taxpayer costs enter APE);
  AFR-plus-3 second eligibility route ((e)(2) last sentence: §1.263A-1(j) small business taxpayers);
  proration-share note ((c)(7)(i)(B) prorates by average-excess share — identical result, right
  cite); (d)(3)(iii) independent-thresholds gate for TPP improvements; cessation (g)(2)/(g)(3)
  sub-rules; (g)(1)(ii) residual deferral clause + no-retroactive-capitalization note; the deferral
  machinery ((c)(4)/(g)(2)) declared out of scope EXPLICITLY; worked-fixture completed with
  nontraced-pool inputs ($2.8M avg nontraced debt / $200K nontraced interest).
- **§§1.263A-4/-5/-6/-7/-13/-14/-15:** -4 (farming) and -7 (method change) characterizations
  confirmed; -5/-6 confirmed reserved (nothing ignored); -15 description completed ("transitional
  rules" added); -13/-14 noted as out of scope. **The real -7 finding: switching an EXISTING taxpayer
  onto MSPM/SRM through `profile.method` is a Form 3115/§481(a) method change with beginning-
  inventory revaluation — the plan treated smaller elections as method-of-accounting events while
  leaving the biggest switch unflagged.** Partially in-scoped: `prior_year_method` field +
  `METHOD-CHANGE-3115-481A-REQUIRED` warning + revalued-inputs contract note; the revaluation/§481(a)
  computation itself stays deferred.
- **Internal consistency:** the intro's "nothing in Phase B/C/D can run until Phase A exists" fixed
  (Phase B was never schedule-gated — it contradicted the sequencing section); "the three schedules"
  → four; the orphaned BTD input (#2) given a spec'd consumer (negative-§263A pipeline + M-1 block);
  the Phase C worked test restated in the ADOPTED Option-(B) ordering (as written it demonstrated
  the rejected ratio-first ordering — same numbers under uniform eligibility, wrong shape to copy);
  the AFR-plus-3 "forces `include_negative_263a`-style debt-tracing off" wording fixed; the §7a-§7e
  history pointer → §7a-§7f; the "(h)(5))" unbalanced paren fixed.

### §9.8 — Standing lessons (now four instances deep)

1. Verifying against a SECONDARY source's silence (COR-C-023, twice now) produces false "one-sided
   rule" / "unaddressed in sources" conclusions the primary text contradicts.
2. Verifying a claim about a REPEALED provision against only the current text guarantees a false
   negative (§9.4).
3. A correct prose description and a false "the code implements this" claim can sit adjacent for
   multiple audit rounds without the contradiction being noticed (§9.1) — conformity claims about
   code need to be checked against the code, not against the prose next to them.
4. eCFR rendering artifacts (digit-1 as letter-l) can send a verifier chasing a nonexistent Code
   subsection (§9.3); when a citation looks wrong, check the promulgation-era numbering before
   inventing a gloss.

Every §9 fix is marked in place in `BUILD_PLAN.md` with `CORRECTED/ADDED/RESTORED 2026-07-09`. Code
changes: `analysis.py` (SSCM denominator, `is_tax_shelter` + exemption bar, aggregation doc),
`tests/test_analysis.py` (two ratio tests rewritten to the correct rule, one new tax-shelter test).
Suite: 96 passing. Accuracy harness re-run: 78.4%/84.0%, unchanged (the SSCM fix changes UNICAP
ratios, not classification).

---

## §10 — Full authoritative eCFR text supplied in-session; plan reconciled against it (2026-07-09, second pass)

The complete current text of the "Items Not Deductible" regulations from §1.261-1 through §1.266-1
(including all of §1.263(a)-1 through -6, the tangible property regulations) and the complete
§1.263A-0 outline plus §§1.263A-1 through -15 was pasted directly into this project. Unlike every
prior verification round, this pass worked from full authoritative text in-context — no mirrors, no
search snippets, no agents. **The §9 provenance caveat is lifted for everything the supplied text
covers** (it survives only for the pre-T.D.-10034 old §1.263A-11(e) text, which is not part of the
current text by definition).

### §10.1 — §9's corrections all held against the full text

Every §9-pass correction covered by the supplied text was confirmed verbatim, including: the
§1.263A-1(h)(4) SSCM denominator rule (the code fix); both sides of the (g)(4)(ii) 90% rule; the
(h)(2) four-category eligible-property structure with (C)/(D) as alternative routes and the
materials/supplies arm of (D); the (h)(3)(ii) election quote; (h)(8)/(h)(9); the (d)(3)(ii)(B)
negatives/$50M structure; the full MSPM mechanics including (c)(3)(ii)(C)/(E)
current-year-incurred on-hand definitions, (c)(3)(ii)(F), the (c)(3)(iii)(B) SSCM split with its
labor-exclusion sentence, the genuinely-two-sided (c)(3)(iii)(C) election, Example 1's every figure
(8.00%/$120,000/$1,500,000/10.22%/$284,400/$3,284,400), Examples 4-6, and all four §9 HAR
refinements (recomputation-year+5 extension; both-ratios AND-test; mandatory third-year
resumption; HAR barred for (c)(3)(v)-zero taxpayers); the SRM two-ratio structure, (d)(3)(i)(F)
one-step MSC sub-split, (a)(4)(i) SRM bar, (a)(4)(iii) private-label conditions, the 1/3-2/3
mechanics; and Phase D's traced-debt definition at (b)(2) including the capitalized-interest
component, the (c)(2) sourcing order, (c)(5)(iii)(D) WAIR/AFR fallback, (c)(7)(i) proration by
average-excess shares, all nine (a)(4) eligible-debt exclusions, the (f)(2)(iii) measurement-date
convention (no day proration), (g)(1) ordering both directions plus the
no-later-recapture-of-deferred-interest rule, the -12(g) suspension rules including (g)(2)/(g)(3),
the -8(b)(3)/(b)(4) exclusions, (b)(2)(iii) estimate rules, and the T.D. 10034 provisions
(-8(d)(3) with the (d)(3)(iii) TPP gate, -11(e)/(f), -15(a)(6)).

### §10.2 — A hedge from the §9 pass was itself wrong (the (h)(5) income-tax exclusion)

§1.263A-1(h)(5)(ii)'s LAST sentence — "Such costs do not include, however, taxes described in
paragraph (e)(3)(iii)(F) of this section" — confirms that the production-cost-ratio denominator
excludes income-based taxes, exactly as this plan originally said before the §9 pass hedged it as
Practice-Unit-only. The snippet-level retrieval had captured the body of (h)(5)(ii) but not its
last sentence. **Standing-lesson addendum: incomplete retrieval of a correct paragraph produced an
over-cautious false hedge — the inverse of §9's false-confidence failures. Partial-text
verification can err in BOTH directions.** Fixed in the SSCM section (exclusion list restored to
MSC + interest + income-based taxes) and the build-implication line.

### §10.3 — One adopted SME decision REVERSED: the SRM 90/10 threshold basis

§8b adopted (and §9 kept, with a weakened rationale) an "independent cost-attribution measure"
(time study/square footage) for the dual-function 90/10 threshold test. The full (c)(5)(iii) text
settles it the other way: (iii)(B) makes the on-site-sales/total-gross-sales ratio the MANDATORY
mechanism for attributing a dual-function facility's costs between the two functions ("must be
allocated... using the ratio"), so (iii)(C)'s "costs... attributable to the on-site storage
function" can only be measured by that ratio — the 90/10 deeming is a rounding rule applied to the
(B) result. The independent-cost-study reading is abandoned; the §8 synthetic fixture's Facility A
scenario must be restated before SRM tests are built. Decision reversal documented in place in
`BUILD_PLAN.md`.

### §10.4 — Previously-unretrievable/flagged items now resolved

- **§1.263A-3(a)(4)(iv)** (the paragraph no channel could retrieve): a de-minimis/private-label
  reseller on SRM "must capitalize all costs allocable to eligible property produced using the
  simplified resale method" — production costs flow through the SAME SRM formula; flag closed.
- **(a)(4)(i) permitted methods**: the full text names SPM *or MSPM* as the permitted elections for
  a producer-reseller barred from SRM — the plan's "SPM but not SRM" phrasing was incomplete.
- **The (a)(5)-vs-(a)(4)(ii) size-axis mapping**: current (a)(2)(ii) is the §448(c) exemption; the
  current (a)(5)(iii) example (Taxpayer N, over the threshold, 5%-receipts/3%-labor bakery) confirms
  the §9 resolution in current-law terms; pre-TCJA caveat closed. Also: the 10%/10% test is a
  presumption within facts-and-circumstances, and its gross receipts are measured per §1.448-2(c)
  at the TRADE-OR-BUSINESS level ((a)(5)(ii)) — a different scope than the exemption test.
- **(h)(7) wording** ("any reasonable allocation method consistent with the principles of
  paragraph (f)(4)") and the **(d)(3)(i)(C)(3)/(D)(3)/(E)(3)** property-sold-exclusion pinpoints —
  both hedges closed.
- **§§1.263A-5/-6 reserved titles** confirmed from the §1.263A-0 outline.
- **§1221 rendering**: the authoritative text still prints "1221(l)" in -8(b)(1)(ii)(A) while
  -3(a) repeatedly uses "1221(1)" in the inventory sense — cross-evidence strengthening §9.3's
  inventory reading; noted in place.

### §10.5 — Genuinely new items entering the plan (each marked "2026-07-09 full-text pass")

- **§1.263A-1(d)(2) §471-cost definition is financial-statement-based** (with (d)(2)(ii)'s
  mandatory direct-cost override): the classifier's §471/Additional tiers are a proxy needing a
  book-capitalization review step; the TD 9843 elective methods ((d)(2)(iii) alternative book
  method, (d)(2)(iv) 5% direct-cost de minimis rules, (d)(2)(v) 5% variance safe harbor) and the
  (d)(3)(ii)(C)-(E) negative-adjustment restrictions documented as flag-don't-model items.
- **(g)(4)(ii) refinement**: the mandatory ≥90%-capitalizable→100% side binds only "under this
  election"; one election covers all mixed service departments and is a method of accounting.
- **MSPM+LIFO combined absorption ratio** ((c)(3)(iv)(B)(2)), with the regulation's own Example 3
  (9.48% on the Taxpayer P facts) — the LIFO section previously described only the SPM shape.
- **SRM handling-cost exclusions** ((c)(4)): retail-facility handling, dual-function on-site-sales
  share (same (B) ratio), distribution costs (loading-dock rule; related-person exception),
  custom-order delivery, pick-and-pack (with the inbound-activities and occupancy-costs
  non-exclusions) — plus the LIFO carrying-value rule for the S&H denominator's beginning
  inventory, and the retail-customer/(E)(2) non-retail-treated-as-retail four-part test.
- **§1.263A-10 unit-of-property/common-feature rules** — new Phase D gap with data-contract
  fields (`is_common_feature`, benefitted-unit allocation, per-property activity dates) and the
  five (b)(5) timing rules.
- **§1.263A-11(c) contract-payment APE rules** (customer payments IN customer's APE; customer
  payments REDUCE contractor's APE), the (b)(1) phase-completion no-reallocation rule, and the
  (b)(2) materials dedication rule — new Phase D data-contract items.
- **§1.263A-9(d) election not to trace debt** (with the payables-inclusion option) — a
  simplification path distinct from AFR-plus-3; and the (g)(7) 15-day rule is NOT a method of
  accounting (per-period toggle).
- **Aged property** (tobacco/wine/whiskey): production period includes the aging period
  (§1.263A-12(d)(1)) — industry-specific mechanic previously absent.
- **Contract production-period start variants** (§1.263A-12(c)(2)/(3), §1.263A-8(d)(2)(iv)) for
  customer vs. contractor.
- **§1.263(a)-1(f) de minimis safe harbor authority**: the reg text sets $5,000 (AFS) and **$500**
  (non-AFS); the $2,500 in `EntityProfile.de_minimis_ceiling` rests on Notice 2015-82 via the
  "published guidance" clause — documented in a code comment in `analysis.py`. The §1.263(a)-3
  BAR/safe-harbor citations underlying the classifier's `cap_vs_deduct` tiers ((h) small-taxpayer
  building safe harbor: lesser of 2%-of-unadjusted-basis or $10,000, ≤$1M building, ≤$10M
  receipts; (i) routine maintenance: 10-year/class-life twice-expectation tests; (j)/(k)/(l)
  betterment/restoration/adaptation standards) are now verified — closing the `§1.263(a)-1/-3`
  unverified-citation item.
- **§1.266-1 verified** (the last of the three unverified citations other than §1.471-11): the
  (b)(1) item categories match the classifier's §266 tier; election mechanics ((c)(3): statement
  with original return; category-(i) elections are annual) support the `election_required` flag
  and §3 item 3's pending confirmation-workflow decision; §1.266-1(a)(2) confirms the
  §263A(f)-before-§266 ordering from the §266 side.

### §10.6 — Remaining unverified

`§1.471-11` pinpoints, Practice Unit document-ID/revision-date details, and the pre-T.D.-10034 old
§1.263A-11(e) text (mirror-sourced only). Everything else in the plan's citation base is now
verified against primary text either supplied in-session or independently retrieved.

Code changes this pass: `analysis.py` (documentation comment on the de minimis ceiling authority
only — no computational change). Suite: 96 passing.

---

## §11 — Interview layer added: the user-question inventory and decision tree (2026-07-09)

A direct review question ("does the plan include all the questions users must answer, and a
platform that asks them via decision trees?") surfaced an honest NO: the plan was engine-first —
its fields, elections, and gates existed but were scattered across sections as implementation
notes, with no consolidated user-facing question set, no ask-ordering, no conditional logic, and
no fact/election/method-of-accounting distinction. Three required questions existed NOWHERE in any
form: the de minimis safe harbor's written-accounting-procedures-at-year-start prerequisite and
its annual-statement election mechanics (§1.263(a)-1(f)); the per-building small-taxpayer safe
harbor election (§1.263(a)-3(h)); and the established-prior-year-method question that drives the
Form 3115 trigger as an interview input rather than an after-the-fact warning.

**Resolution: BUILD_PLAN.md Phase E** — `interview.py` + a declarative `taxonomy/interview.yaml`
question graph (id / question / answer type / maps-to field / authority / ask-when predicate /
kind / consequence), validated at load with the same discipline as the taxonomy (every
engine-consumed field reachable, no orphan questions). Seven gates encode the decision tree:
Gate 0 (identity/exemption/adoption-vs-change — the §448(c) exemption SHORT-CIRCUITS gates 1-3,
6-7 while §263(a)/§266 gates still run, and the prior-year-method answer arms the 3115 warning),
Gate 1 (activity profile → method availability matrix), Gate 2 (method + elections, each tagged
FACT / ELECTION / METHOD-OF-ACCOUNTING), Gate 3 (method-conditioned balance inputs + the
per-facility SRM sub-tree), Gate 4 (§263(a) safe harbors and BAR follow-ups, per flagged line),
Gate 5 (§266 election confirmation — wiring the still-open §3 item 3 into the interview), Gate 6
(per-asset SCA sub-tree incl. the SSCM (C)/(D) route facts and the officer-involvement surfacing),
Gate 7 (per-unit and per-debt §263A(f) sub-trees incl. tracing posture as a three-way choice:
trace / §1.263A-9(d) no-tracing / AFR-plus-3). Sequencing updated: Gate 0-2 core builds early
(it populates `EntityProfile` for everything and tells Phase A which schedules to request);
Gates 3/6/7 land with Phases B/C/D respectively.

Scope note: the deliverable is the question graph + runner (CLI prompts or JSON answers file) —
a graphical front end is out of scope; any UI consumes the same YAML.

## §12 — Pre-build completeness validation of the interview layer (2026-07-09)

**Trigger:** a direct question — "how can you test this and make sure it has everything needed
before you do an actual build?" — asked after Phase E (§11) closed the "no user-facing question
inventory" gap but before any Phase E code exists. Since `interview.yaml` isn't written yet,
"testing" here means validating the PROSE SPECIFICATION in `BUILD_PLAN.md`'s Phase E section
against (a) what the engines actually require and (b) taxpayer scenarios more complex than the
plan's own worked examples — the same discipline Phase E's own build notes call for
("graph-validation tests... every engine field reachable"), applied by hand before the graph is
code.

**Methodology — three independent agents, run in parallel, each with no visibility into the
others' work:**
1. **Field-reachability audit** — enumerated every `EntityProfile` field / schedule column /
   election flag named anywhere in the engine sections (SSCM, MSPM, SRM, LIFO, SCA, §263A(f)),
   including ones introduced only in inline "DEFINITIONAL CONSTRAINTS" code-comment blocks, and
   checked each against Phase E's Gates 0-7 for a question that would populate it.
2. **Golden-example dry run** — reconstructed the full taxpayer fact pattern behind each of the
   plan's four verified worked examples (MSPM's $284,400/$3,284,400 Taxpayer-P example; SRM's
   $36,875 example; SCA's $55,000/asset example; §263A(f)'s $376,428.57 example) and hand-traced
   that taxpayer through Gates 0-7 as literally written, checking whether the interview would
   actually arrive at the exact inputs those formulas need.
3. **Adversarial fresh-eyes gap hunt** — invented a composite taxpayer deliberately outside all
   five existing worked examples (a partnership, producing AND reselling above the 10%/10% de
   minimis threshold, LIFO, a dual-function retail/warehouse facility, mid-construction on a
   self-constructed asset with both traced and nontraced debt, in its second year on SRM after
   switching off SPM) and walked it through the gates looking for points where the described
   interview breaks down, contradicts itself, or has no defined next step.

**Findings — two of the four golden traces FAILED as originally written, both on load-bearing
inputs the SRM/MSPM formulas cannot compute without:**
- **SRM ($36,875 example) — FAIL, confirmed independently by BOTH the field-reachability audit
  AND the golden-example dry run:** Gate 3's SRM branch never asked for `ending_inventory_471` —
  the §471-costs-remaining-on-hand-at-year-end figure that is the direct multiplier in
  `add'l_to_inv = combined * ending_inventory_471`. It jumped from beginning inventory straight to
  the write-down carve-out (an adjustment to a number that was never established). The
  field-reachability audit separately found the SRM numerator (`purchasing_costs`, the
  purchasing-department cost pool) was also never asked, and that Gate 3's bare word "purchases"
  was ambiguous between that field and `current_year_471_costs` (the reg's "current year's
  purchases," a different, already-named field).
- **MSPM ($284,400 example) — FAIL:** the golden-example dry run found Gate 3's MSPM branch never
  separately asked for `DM_purchased_during_year` — a fact distinct from both the aggregate
  pre-production-incurred figure and the DM-not-in-production begin/end stock figures, and one
  the `direct_materials_adjustment` formula in the MSPM section directly requires.
- **HAR `ask_when` not scoped to MSPM:** the golden-example dry run separately noticed Gate 2's
  Q2.6 (HAR election) had no method restriction at all, so as written it would incorrectly fire
  for SPM/SRM taxpayers too, even though HAR is an MSPM-only mechanic.
- **Gate 0/Gate 1 contradiction (adversarial run):** Q0.6 offers `none-noncompliant` as a
  prior-year-method answer, but nothing defines what happens when a taxpayer's stated prior
  method (e.g. SRM) turns out to have been legally unavailable under Gate 1's own
  method-availability matrix — a discovered-impermissible-method scenario the interview had no
  path for.
- **SCA ($55,000/asset) and §263A(f) ($376,428.57) golden traces both PASSED** — no missing fact
  found; Gate 6/7's topic coverage was adequate for those two examples, with only soft
  (non-blocking) observations noted.
- **Adversarial run found 11 total snags**, the Gate 0/1 contradiction above being the only
  hard, load-bearing one; the rest were unscoped `ask_when` conditions, a Gate-5/Gate-7 ordering
  conflict for a self-constructed real-property asset that is simultaneously a §266 development-
  project candidate (per §1.266-1(a)(2), §263A(f) must be determined first), a Gate 6 question
  with no defined cost-allocation-method screen (Specific ID vs. burden rate vs. standard cost —
  this tool implements Specific ID only, per Phase C's own scope), and "officer" terminology not
  adapted for a partnership entity type.
- **Field-reachability audit found 11 gaps total** (see above for the two shared with the
  dry-run) plus, in Gate 7's per-unit/per-debt tree specifically: the aged-property
  (tobacco/wine/whiskey) production-period extension; producing-asset basis + usage-apportionment
  for equipment used TO PRODUCE a unit (moves real dollars into APE); the T.D. 10034
  mid-production-acquisition purchase price; the pre-Oct-2025 associated-property inputs for the
  dual regime; a `production_complete` date distinct from `placed_in_service_date`; the
  since-1994 (not just 3-year) look-back for AFR-plus-3 eligibility; the §1.263A-9(d)(1)
  accounts-payable fold-in sub-election; and related-person ACTIVITIES vs. related-person COSTS
  as two distinct data needs, not one question. Plus 7 lower-severity ambiguous items (an
  unnamed field for MSPM's 90%-one-bucket election; an orphaned `production_gross_receipts`
  field; the already-shipped `mixed_alloc_ratio` override and legacy Phase-4 fallback scalars
  never addressed by Phase E).

**All findings fixed in `BUILD_PLAN.md`'s Phase E section directly** (dated `ADDED`/`CORRECTED`/
`CLARIFIED` 2026-07-09 inline, following this document's established annotation convention):
the two SRM inputs and the MSPM input added to Gate 3 with explicit disambiguation from their
same-formula neighbors; HAR's `ask_when` scoped to MSPM; the Q0.6/Gate-1 reconciliation node
(Q0.6a) added with a distinct `PRIOR-METHOD-IMPERMISSIBLE` flag for the discovered-impermissible-
method case; the Gate 5/Gate 7 cross-dependency documented; a cost-allocation-method question
added to Gate 6 along with entity-neutral "officer" wording; the 8 Gate-7 per-unit/per-debt gaps
added as a consolidated bullet; the MSPM 90%-election field named; and a scope note added
clarifying `mixed_alloc_ratio` and the legacy Phase-4 fallback scalars are intentionally outside
Phase E's question set.

**Deliberately NOT fixed this pass:** the §446(e) discovered-impermissible-method CORRECTION
computation itself remains out of scope (same boundary as the existing §1.263A-7 revaluation/
§481(a) computation deferral) — Gate 0's Q0.6a only routes to a distinct warning flag, it does not
compute the correction.

**Follow-up, same day (2026-07-09):** the `Q#.#` numbering of Gates 3, 5, 6, and 7 — flagged above
as documentation debt — has now been closed. All four gates are individually numbered (Q3.1-Q3.22,
Q5.1-Q5.3, Q6.1-Q6.5, Q7.1-Q7.23) matching the style already used in Gates 0/1/2/4, so every node
referenced anywhere in Phase E, including every gap this pass added, has a stable ID the
`taxonomy/interview.yaml` loader's reachability validation can target once the YAML is authored.

**Standing-lesson note:** this is the first validation pass in this document's history performed
entirely against a PROSE SPECIFICATION with no code and no regulation text to re-verify — it
tested internal consistency and completeness of the plan itself, not tax accuracy. It caught two
independently-confirmed load-bearing gaps in worked examples this same document had already
"verified" as buildable (§8/§10/§11) — a reminder that "the formula is correct" and "the
interview that's supposed to gather the formula's inputs actually gathers them" are separate
claims, and this document's prior passes had only ever tested the former.

Suite: 96 passing (docs-only change; no code touched this pass).
