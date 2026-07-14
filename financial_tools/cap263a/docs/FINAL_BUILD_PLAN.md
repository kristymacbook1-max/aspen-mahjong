# Final Build Plan — cap263a Python tool + standalone HTML calculator

Status: FINALIZED 2026-07-12. This document supersedes the phase roadmap in
BUILD_PLAN.md for scoping questions: it states what each surface computes,
what it deliberately refuses to compute (warned stubs), what uploads each
surface accepts, and how the interview/question layer guarantees the
calculations get every fact they need.

## 1. Surfaces

| Surface | Source of truth | Delivery |
| --- | --- | --- |
| Python tool | `financial_tools/cap263a/` engines | CLI / library / FTA 5-tab workbook (openpyxl) + `=PY()` workbook |
| Standalone HTML | `standalone/cap263a_calculator.html` | one self-contained file, offline, any browser |

The Python engines are authoritative. The HTML embeds JavaScript ports pinned
to them by golden-vector parity (`standalone/goldens.json`, regenerated from
the Python engines; `tests/test_standalone.py` fails CI on any drift — stale
vectors, stale build, or a numeric divergence).

## 2. Computation coverage (both surfaces unless noted)

### §263A — inventory UNICAP
- §448(c)/§263A(i) exemption gate (aggregated receipts, tax-shelter bar,
  indexed thresholds with estimate warnings).
- Classification waterfall → §471 vs additional-§263A pools (Python: keyword
  classifier + analyst review; HTML: analyst-assigned tiers).
- SSCM mixed-service allocation: labor-based, production-cost (producer-only
  gate), or override — with clamps and warnings.
- SPM (§1.263A-2(b)) including the $200K producer de minimis.
- MSPM (§1.263A-2(c)): two-ratio mechanics, residual rollover,
  direct-materials adjustment, (c)(3)(iii)(B) split (direct-material or
  labor), (c)(3)(iii)(C) 90% election, HAR election with the ±0.5pp
  recomputation test, LIFO combined ratio (Example 3), $200K de minimis
  (bars HAR).
- SRM (§1.263A-3(d)): purchasing + storage/handling ratios, variations (A)
  and (B), availability gates ((a)(4)(i)-(iii)), the (d)(3)(i)(F) input
  contract for mixed service.
- LIFO decrement release calculator (§1.263A-2(b)(3)(iii)(C)).
- Self-constructed assets (Phase C): pool → driver split → SSCM eligibility
  gate, penny-plug conservation, driver-reasonableness guardrails.
- Tax-basis TB: BTD application, M-1 tie, unmatched-BTD quarantine.

### §263A(f) — interest
- Avoided-cost method (§§1.263A-8/-9): point-in-time APE snapshots, traced
  debt (actual interest, never prorated), WAIR with the AFR fallback and the
  data-inconsistency refusal, all eight §1.263A-9(a)(4) eligible-debt
  screens, measurement-grid nesting rules (no zero-padding across mixed
  conventions), (c)(7) pro-rata cap on the excess pool with penny-plug,
  per-source consumption, ASC 835-20 book/tax reconciliation.

### §263(a) — mandatory and elective
- §1.263(a)-5 transaction costs: inherently-facilitative, bright-line date,
  covered-transaction conservatism, Rev. Proc. 2011-29 70/30 success-fee
  election (irrevocable, per transaction), abandoned-transaction losses.
- §1.263(a)-4 intangibles: 12-month rule (both prongs), $5,000 facilitative
  cliff, commissions always capitalized, §197 routing, benefit-term
  amortization, indefinite-life SME routing.
- §195/§248/§709 start-up & organizational pools ($5,000 first-year cap,
  $50,000 phase-out, 180-month amortization, §709(b) syndication permanent
  capitalization).
- §280B demolition (to land; casualty carve-out routed to SME).
- **NEW (this finalization): tangible repair-vs-improvement engine**
  (`engines/tangible_263a.py`): de minimis safe-harbor election
  (§1.263(a)-1(f), AFS/no-AFS ceilings), §1.162-3 materials & supplies,
  small-taxpayer building safe harbor (§1.263(a)-3(h), lesser of $10K/2%),
  BAR improvement tests (betterment (j) / adaptation (l) / restoration (k))
  with **conservative capitalize-on-missing-facts**, routine-maintenance
  safe harbor (§1.263(a)-3(i)), §1.263(a)-3(n) capitalize-following-books
  election — and an **open-questions channel**: every missing determinative
  fact becomes an explicit question for the user instead of a silent guess.

### Other regimes carried by the tool (unchanged)
§174/§174A (foreign mandatory / domestic default / §174A(c) election,
2022-24 catch-up, §174(d)), §59(e) (entity/AMT gate, per-item elections),
§1060 residual allocation, §266 carrying charges (elective bucket;
classification-level).

## 3. Uploads — "any format necessary"

### Python tool
- `.xlsx`/`.xlsm` workbooks (multi-sheet engagements; alias-driven header
  detection, section-header skipping, amount cleanup incl. parens/`$`).
- `.csv` — per-schedule files and single-file TB.
- `.json` engagement files.
- Directories of mixed per-schedule files (name-matched, warned when not).

### Standalone HTML (`standalone/ingest.js`, zero dependencies, offline)
- `.xlsx`/`.xlsm` (native ZIP + OOXML parser — no third-party code; stored
  and deflate entries, shared strings, multi-sheet, dense-cell gap-filling),
  `.csv`/`.tsv`/`.txt` (RFC-4180 quoting, delimiter sniffing across comma/
  tab/semicolon/pipe), `.json` (parsed and shown for reference; full
  multi-schedule JSON-engagement import is not wired into the UI yet — the
  Python CLI is the fully-featured JSON path).
- Import flow (**Import Files** tab): pick a destination schedule → upload →
  the SAME alias tables as the Python reader/readers auto-detect the header
  row and column mapping → preview (with the detected `column → field`
  labels) → append into that schedule's table. Importable destinations:
  Trial Balance, Book-Tax Differences, §174 R&E, transaction costs,
  intangibles, start-up pools, §59(e) elections, the §263A(f) debt schedule,
  designated-property units, LIFO layers, SCA pools/assets, and §263(a)
  tangible-property items. **Not wired to a destination**: Fixed Assets
  (parses and previews, but the standalone app has no per-asset basis
  schedule for it to land in — that's desktop-tool territory) and full JSON
  engagements. Import is append-only (no replace/merge); re-importing the
  same file duplicates rows.

## 4. The question layer — "ask everything the calculation needs"

Three mechanisms, layered:
1. **Interview tab** (HTML; mirrors the Python Phase E interview graph via
   `standalone/interview_spec.json`, 78 questions / 12 gates — validated:
   every `show_if`/`derived` reference resolves, every `maps_to.profile_field`
   is a real `EntityProfile` field; see `INTERVIEW_NOTES.md`). Questions
   render as a single reactively-filtered form (conditional visibility per
   `show_if`, not a paginated step-by-step wizard) grouped by gate; "Apply
   answers to Profile" copies mapped answers onto the Entity Profile tab.
2. **Completeness checks** (pre-compute, same tab): the engine warning codes
   that mean "a required input is missing" (MSPM-LIFO-INCREMENT-MISSING,
   HAR-RATIOS-MISSING, SRM-VARIATION-B-INPUT-MISSING, WAIR-UNAVAILABLE,
   MSPM-SPLIT-INPUT-MISSING, SRM-PRODUCTION-LEVEL-UNKNOWN) are checked
   against the CURRENT profile on demand ("Check completeness"), so a gap
   surfaces as a question before computing, not discovered as a warning
   after.
3. **Engine open-questions** (post-compute): the tangible §263(a) engine
   returns `open_questions` (missing BAR facts, de minimis invoice costs,
   routine-maintenance expectations), rendered prominently above its results
   table; every other engine's honesty-gate warnings render in both
   surfaces and the workbook Cautions block.

## 5. Deliberately NOT computed (warned, never silent) — both surfaces
- MSC 90/10 all-departments election department mechanics
  (MSC-90-10-NOT-IMPLEMENTED).
- Automatic MSPM decrement-year integration (the LIFO release calculator is
  standalone; LIFO-DECREMENT-NOT-IMPLEMENTED flags the placeholder).
- §1.263A-10 unit-of-property / common-feature combination; §1.263A-11(c)
  contract-payment APE; §1.263A-11(f) mid-production purchases.
- SSCM-ineligible SCA shares (general §1.263A-1(g)(4) fallback) — computed,
  flagged, not booked.
- §1.162-3 incidental/non-incidental M&S timing.
- Keyword classification in the HTML (analyst assigns tiers; the Python
  classifier remains desktop-side).
- Out of scope per the original plan: §168(n), §163(j), §45X/§48D, cost
  segregation.

## 6. Verification gates (all must pass to ship either surface)
1. `pytest financial_tools/cap263a/tests` — engines, workbook, interview,
   readers, standalone freshness gates.
2. `node standalone/test_parity.js` — every golden scenario, JS vs Python.
3. `node standalone/test_ingest.js` — CSV/XLSX/amount/header parsing.
4. Headless Chromium on the built file: embedded self-tests all green, every
   panel builds (`#buildall`), UI smoke computes a known figure end-to-end.
