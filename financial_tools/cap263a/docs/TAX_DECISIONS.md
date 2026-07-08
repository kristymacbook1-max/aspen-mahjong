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

**Corrected (moderate-to-high confidence; still not primary-source-verified):**
- `NO-OFFICER` (officer comp): §1.263A-1(e)(3)(ii)(**A**) → **(B)**. The indirect-cost list
  runs (A) indirect labor, (B) officers' comp, (C) pension/related costs, (D) benefits — the
  original cite was off by one letter.
- `DL-PENSION` (pension/benefits): §1.263A-1(e)(3)(ii)(**B)-(C**) → **(C)-(D)**. Same
  off-by-one-letter pattern, same direction — this looks systematic, not two independent typos.
- `SEC263A-REPAIR` de minimis safe harbor: cited to §1.263(a)-**3(f)** → corrected to
  **§1.263(a)-1(f)** (the de minimis election lives in the general capitalization reg, not the
  tangible-property BAR-test reg). The routine-maintenance (-3(i)) and small-taxpayer (-3(h))
  cites in the same entry were already in the right section.
- `EX-ABNORMAL` (abnormal spoilage): §1.263A-1(e)(3)(iii) → corrected to **§1.471-11(d)(2)(iii)**
  (the abnormal-costs exclusion is in the full-absorption costing regs, not the general
  non-capitalizable-costs list — a different provision from `BS-ASSET`'s §1.263A-1(e)(3)(iii)
  citation two rows up, which IS the right section for ITS purpose and was left alone).
- `NEG-263A` / the negative-pool warning (`analysis.py`, item #35/#48): **T.D. 9843 → T.D. 9942**.
  The TCJA small-business simplified-methods final regs (including the >$50M-producer
  negative-adjustment rule) were, to the auditing agent's recollection, finalized as T.D. 9942
  (Jan. 2021), not T.D. 9843.

**Flagged, deliberately NOT guess-corrected** (a wrong replacement citation is worse than an
honest "unverified" label — these need a primary source, not a second guess):
- **`docs/BUILD_PLAN.md` "T.D. 10034 (Oct 2025)"** — the auditing agent has *no recollection of
  this T.D. number existing at all* and suspects outright fabrication. This is the single most
  serious item in this section: it was driving a proposed `tax_year`-gated computation change
  (eliminating the associated-property rule, narrowing improvement interest) in the still-unbuilt
  §263A(f) engine. **Do not build tax-year cutover logic against this citation without first
  confirming, from a primary source, that the T.D. exists and says what's described.** Flagged
  prominently in BUILD_PLAN.md itself.
- `EX-BID` bidding-cost sub-letter (T) in §1.263A-1(e)(3)(ii)(T) — given the confirmed
  transposition pattern on two other sub-letters in this same list, this one should be
  re-verified, not trusted, before relying on the "(T)" pinpoint.
- `SEC266-INT`/`-OTHER` — §1.266-1(b)(1)(iii)-(iv): the carrying-charge list may only run
  three items (taxes/interest/other), which would make "(iv)" nonexistent. Unconfirmed either way.
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

**Bottom line for the SME/reviewer:** every citation in this tool should be treated as a
starting point for research, not a verified filing position, until confirmed against a primary
source — and the items above are the ones most likely to be wrong if spot-checked first.

---

### Reviewer summary
- **7 bug fixes (§1):** all recommended **approve**; items #3 (EX-BID) and the scope items carry a "revisit scope" caveat.
- **8 new-code groups / 10 codes (§2):** all recommended **approve** (SEC195-STARTUP and the SEC263A-IMPROVE/REPAIR keyword set carry minor-revisit notes).
- **5 SME judgment calls (§3), 2 resolved:** items 1 (DM-\* pre-production tagging, confirmed correct as-is) and 5 (SSCM ratio includes Additional-§263A labor in both numerator and denominator — code changed, dollar output affected) approved 2026-07-08. Items 2 (EX-BID successful-bids-only), 3 (§266 land-context auto-routing vs. election confirmation), and 4 (repair-vs-improvement keyword scoping) remain open.
- **5 known limitations (§4):** computation layers (MSPM/SRM, §263A(f), negative adj., per-asset basis) are not yet built; classification-only at this stage.
- **27 hardening-pass corrections (§5):** found across four independent multi-agent audit rounds (initial, adversarial re-verification, previously-unaudited files + deeper taxonomy data, and end-to-end/lexicon/practitioner review), all fixed and regression-tested; items #16, #28, #35, #36, and #37 change computed dollar output — re-run any workpaper generated before this pass.
- **8 red-team corrections (§6):** three adversarial agents (hostile input / tax-wrongness / single-source divergence). Two are security-class (formula injection #44, the =PY() NaN divergence #43); five change or bound computed dollar output (#45–#49). All fixed and regression-tested (93 tests). Highlights: an unbounded absorption ratio could show a **$50 billion** capitalized figure unflagged (#46); a NaN amount silently defeated the integrity tie-check (#45). Nothing further should be relied on for filing without SME sign-off on §3/§3a.
- **Citation accuracy audit (§7):** 5 citations corrected (moderate-high confidence, still unverified), 6 flagged unverified/possibly fabricated rather than guess-corrected — most notably a suspected-fabricated Treasury Decision ("T.D. 10034") in BUILD_PLAN.md. **No citation in this tool should be relied on for a filing position without independent primary-source verification.**
