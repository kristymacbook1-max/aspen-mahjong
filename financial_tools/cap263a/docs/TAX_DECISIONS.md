# Taxonomy Decisions & Changes — §263A / §263(a) / §266 Capitalization Classifier

**To:** Tax SME (reviewer / approver)
**From:** Tax Technical Review
**Re:** Rebuilt taxonomy (`categories.yaml`, 132 categories) vs. original `_CategoryRef` (122 codes) plus CC-engine maps (`cc_reclass.yaml`, `generic_map.yaml`, `cc_zones.yaml`)
**Date:** 2026-07-01

**Purpose.** Give the SME an item-by-item basis to *approve* or *overturn* every substantive change made in the rebuild. Sources: original workbook hidden sheets `_CategoryRef`, `_CCReclassMap`, `_GenericExpMap`; IRS Practice Units COR-P-020 (producers), COR-P-021 (resellers), COR-P-006 (interest), COR-C-023 (self-constructed). Net category count moved 122 → 132 (10 new codes); no codes were deleted.

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

1. **DM-\* raw/direct materials MSPM column left as "471-Pre" (not normalized to plain "471").** DM-RAW, DM-PKG, DM-COMP, DM-FRT, DM-DUTY carry `mspm: 471-Pre`, tagging direct materials as *pre-production* §471 content for the MSPM two-ratio split, while `resale/self_const/interest = 471`. **Question for SME:** Is treating raw/purchased material (and inbound freight/duty) as *pre-production* §471 content correct for the MSPM pre-production absorption ratio (COR-P-020, MSPM two-factor method), rather than plain production §471? Direct materials are unambiguously §471 direct costs; the only judgment is whether they belong in the *pre-production* factor. **Recommend: confirm** (consistent with MSPM), but flag because it materially shifts the pre-production ratio denominator.

2. **EX-BID conditional treatment (successful bids only).** The code now capitalizes bidding/proposal costs as Additional §263A, but §1.263A-1(e)(3)(ii)(T) capitalizes bidding costs **only for bids that are successful** (unsuccessful-bid costs are deductible). The taxonomy note flags "conditional," but the tool has no success/failure input. **Question:** Accept blanket "I" treatment (over-capitalizes failed bids) or require a success flag before capitalizing? **Recommend: revisit** — add a success indicator or route failed bids out.

3. **§266 land-context cost-center triggers + election dependency.** SEC266-TAX/-INT/-OTHER fire off `land` CC-zone keywords (`unimproved`, `vacant land`, `held for development`, `idle land`, `raw land`). §266 capitalization is **elective and annual** (Reg §1.266-1) — it is never automatic. **Question:** Should the tool auto-route land-context carrying charges to §266 (implying the election is/will be made), or hold them pending confirmation that a valid §266 election exists for that property/year? **Recommend: revisit** — treat as suspense/flag unless election is confirmed.

4. **SEC263A-REPAIR / -IMPROVE keyword scoping vs. departmental R&M.** Departmental "repairs & maintenance" cost centers route via the CC-engine to **FO-RM** (factory overhead, §471) or **GEN-RM** (MSC), **not** to the new §263(a) tangible-property codes; SEC263A-IMPROVE/REPAIR fire only on BAR-test / safe-harbor keywords (betterment, restoration, routine-maintenance safe harbor, de-minimis, UoP). **Question:** Is it correct that ordinary departmental R&M stays in the §263A overhead pool and only explicit improvement/safe-harbor language triggers the §263(a)-3 BAR analysis? This is defensible (avoids over-capitalizing routine plant R&M), but the boundary is keyword-fragile and a genuine improvement described in plain "repair" language will be missed. **Recommend: confirm scoping, revisit keyword coverage.**

---

## §4 — Known Limitations (SME should be aware)

1. **Only SPM is implemented; MSPM two-ratio and SRM combined-ratio are not yet computed.** The taxonomy *tags* costs as pre-production (`471-Pre`, `I-Pre`) and carries resale P/S/M codes, but the MSPM production/pre-production two-factor computation (COR-P-020) and the SRM purchasing + storage-&-handling dual absorption ratios (COR-P-021, incl. the beginning-inventory-in-S&H-denominator rule) are **not built**. Classifications will not yet produce MSPM/SRM adjustments.

2. **Per-asset / per-unit basis is deferred.** No unit-of-property or per-asset basis tracking. This limits §263A(f) interest (COR-P-006 requires unit-of-designated-property and APE per unit) and §263(a)-3 BAR (UoP-level) analysis; those codes classify but cannot yet compute at the asset level.

3. **DCN / authority citations are representative, not authoritative.** The reg/Practice-Unit citations embedded in `authority` fields are for reviewer orientation; they have **not** been validated as controlling for a specific taxpayer's facts, method, or year and should not be relied on as filing positions without confirmation.

4. **No negative-adjustment computation yet.** NEG-263A exists as a classification scaffold (`allows_negative_adj: true`), but the negative §263A cost computation (T.D. 9843; §1.263A-1(d)(3); the COR-P-020/-021 negative-cost audit issue) is **not implemented**. Negative adjustments must be computed manually for now.

5. **§263A(f) interest engine not built.** NO-INTCAP correctly routes to the §263A(f) layer, but the 7-step avoided-cost method (traced/nontraced debt, APE with compounding of prior capitalized interest, weighted-average rate) per COR-P-006 is not yet implemented.

---

### Reviewer summary
- **7 bug fixes (§1):** all recommended **approve**; items #3 (EX-BID) and the scope items carry a "revisit scope" caveat.
- **8 new-code groups / 10 codes (§2):** all recommended **approve** (SEC195-STARTUP and the SEC263A-IMPROVE/REPAIR keyword set carry minor-revisit notes).
- **4 SME judgment calls (§3):** require an explicit human decision before reliance.
- **5 known limitations (§4):** computation layers (MSPM/SRM, §263A(f), negative adj., per-asset basis) are not yet built; classification-only at this stage.
