# HANDOFF BUILD PLAN — cap263a capitalization tool (start here, no prior context needed)

**Repo:** `kristymacbook1-max/aspen-mahjong` · **Branch:** `claude/263a-cost-capitalization-plan-swcokh` (open PR #2)
**Working directory:** `financial_tools/cap263a/`
**This document is the single authoritative plan.** It supersedes `BUILD_PLAN.md`
and `FINAL_BUILD_PLAN.md` for scope. A fresh session should be able to finish the
tool from this file alone.

---

## 1. SCOPE (owner's decision, final)

The finished product computes, COMPLETELY, on both surfaces (Python tool AND
standalone HTML):

| Regime | Meaning |
| --- | --- |
| **§263A — complete** | inventory UNICAP (SPM/MSPM/SRM + SSCM + all elections), self-constructed assets, tax-basis TB, LIFO decrement, **§1.263A-4 farming** (§263A(d)/(e)), and **§263A(f) interest** incl. designated-property classification and §1.263A-11(c)/(f) |
| **§263(a) — complete** | §1.263(a)-2/-3 tangible (de minimis / M&S / small-taxpayer / BAR / routine maintenance / (n) election), §1.263(a)-4 intangibles, §1.263(a)-5 transaction costs, §195/§248/§709 start-up, §280B demolition |
| **§174 / §174A** | foreign mandatory, domestic default/elective, 2022-24 catch-up |
| **§59(e)** | all five categories (the categories reference §173/§616/§617/§263(c) — only the §59(e) overlay is in scope, see de-scope below) |
| **§460** | PCM cost-to-cost, §460(e) exemptions, 10% election (look-back stays out of scope, warned) |
| **§263(c)** | IDC: working-interest gate, expense election, §291(b) integrated-producer cutback, §263(i) foreign wells, dry holes |
| **§266** | elective carrying charges, all three categories with election granularity |

**DE-SCOPED (owner's instruction — do not build further):** §263(g)/§263(h)
financial positions; §616/§617 mining as standalone engines; §173 circulation as
a standalone engine; §175/§180/§194 farm elections; §181; §848; nonrecognition
basis; ALL post-capitalization cost recovery (MACRS/§167/§168/§179/bonus/
dispositions). §1060/§197 stay as already shipped (allocation/routing support).

The de-scoped engines `financial_positions.py`, the mining/circulation halves of
`resource_expenditures.py`, and their tests **already exist and pass — LEAVE THEM
in the repo** (they're tested and harmless) but do **NOT** port them to the HTML,
do not build UI for them, and mark them "library-only, out of product scope" in
docs.

## 2. ARCHITECTURE (already in place — do not redesign)

- **Python engines are the single source of truth**: `financial_tools/cap263a/`
  (`analysis.py` + `engines/*.py`). House pattern: exact `Decimal`, tri-state
  facts (`None` = not established → engine emits an `open_questions` entry and
  treats CONSERVATIVELY — never silently deducts), `CODE-PREFIX` warnings,
  honesty stubs for anything not computed.
- **Standalone HTML** (`standalone/cap263a_calculator.html`) is ONE self-contained
  offline file: JS ports of the engines (BigInt decimal class `D`, 28-digit
  half-even division), built by `standalone/build.py` from `template.html` +
  `engines.js` + `ingest.js` + `selftest.js` + `app.js` + `goldens.json` +
  `interview_spec.json`.
- **Parity is enforced, not asserted**: `standalone/goldens.py` runs pure-JSON
  scenario specs through the PYTHON engines → `goldens.json`;
  `standalone/test_parity.js` (Node) and the in-browser Self-Tests tab run the
  SAME specs through the JS ports and compare every number exactly (warnings by
  30-char-prefix multiset, flags exactly). `tests/test_standalone.py` fails CI on
  stale goldens, stale built HTML, or any divergence.
- Parity gotchas (learned the hard way): treat `undefined`, `null`, and `""` all
  as Python `None`; Python `!r` → `pyrepr()`; cents are HALF_EVEN except
  interest.py's HALF_UP (`q2up`); §460's completion factor is carried EXACT and
  only the displayed figure is quantized; §291(b)'s 30% side quantizes and the
  70% side is the arithmetic plug.

## 3. CURRENT STATE (commit `fa797ca`, all pushed)

**Python: DONE for the entire Section-1 scope.** 402 tests; the ONLY red test is
`test_standalone.py::test_goldens_json_is_current`, which is EXPECTED — it is the
freshness gate saying "the JS side hasn't caught up to the new Python engines."
Finishing §4 below turns it green.

Engines (all with their decision order documented in the module docstring —
**port from those docstrings verbatim**):

| File | Provides | Tests |
| --- | --- | --- |
| `analysis.py`, `engines/inventory.py`, `engines/sca.py`, `engines/tax_basis_tb.py` | §263A UNICAP core | shipped earlier, ported |
| `engines/interest.py` | §263A(f) **incl. NEW designated-property gate, 11(c) customer payments, 11(f) proxy, per-unit `designated_basis`** | `test_interest.py`, `test_interest_designated.py` (12 new) — **NOT yet ported** |
| `engines/tangible_263a.py` | §263(a) tangible | ported ✓ |
| `engines/intangibles.py`, `re_capitalization.py`, `qualified_expenditures.py`, `purchase_price_allocation.py` | §263(a)-4/-5, §174, §59(e), §1060 | ported ✓ |
| `engines/long_term_contracts.py` | **§460** (`compute_460`) | 24 tests — **NOT ported** |
| `engines/farming_unicap.py` | **§1.263A-4** (`compute_farming_unicap`) | 20 tests — **NOT ported** |
| `engines/resource_expenditures.py` | **§263(c) IDC** (`compute_idc`) — ALSO contains compute_mining/compute_circulation (de-scoped, do not port) | 30 tests — IDC half **NOT ported** |
| `engines/sec266.py` | **§266** (`compute_266`) | 15 tests — **NOT ported** |
| `engines/financial_positions.py` | §263(g)/(h) — **de-scoped, do not port** | 7 tests |

Desktop wiring DONE: tangible schedule in `readers.py` (tri-state facts, blank ≠
False), `pipeline.py` dispatch + interview-derived elections + double-count
warning, `report.py` "Tangible §263(a)" tab (`test_tangible_integration.py`).

Standalone HTML currently at the PREVIOUS scope: 91/91 self-tests, tabs for
profile/import/interview/TB-UNICAP/tangible/tax-basis/LIFO/interest/SCA/§174/
intangibles/§59(e)/§1060 — verified in headless Chromium. Defect fixes already
shipped: §448(c) thresholds 2018-2023 + PRE-TCJA-YEAR warnings, interview
election routing (`FLAG_ROUTES`/`ELECTION_KWARG_ROUTES` in app.js), completeness
checker schema, import amount/date cleanup + safe defaults.

## 4. REMAINING WORK (everything left; est. one focused session)

**Step 1 — JS ports into `standalone/engines.js`** (append before the exports
block; `computeTangible263a` is the stylistic template): `compute_460`,
`compute_farming_unicap`, `compute_idc` (ONLY — skip mining/circulation),
`compute_266`, and the interest.py CHANGES merged into the existing
`compute263af` (new project fields `is_real_property`/`class_life`/
`total_estimated_cost`/`production_start`/`production_complete`/`contract_role`/
`contract_payments_by_date`/`mid_production_purchase_price`; prong logic compares
day-spans >730/>365; five new warning codes; `designated_basis` per unit).
Export all under `CAP263A`.

**Step 2 — goldens**: in `standalone/goldens.py`, add runners (`run_460`,
`run_farming`, `run_idc`, `run_266`) constructing the dataclasses from JSON
specs (mirror `run_tangible`), plus 4-8 scenarios per engine covering EVERY
docstring decision branch — mine each engine's pytest file for hand-computed
fact patterns. Add 3-4 interest scenarios for the new behavior (not-designated
exclusion, unknown-conservative, customer payments, mid-production proxy). Add
matching `case` entries in `standalone/selftest.js` `runScenario`.

**Step 3 — UI tabs** in `standalone/app.js` (follow the existing `panel()` /
`ioTable` / `kvTable` / `warnList` / open-questions patterns exactly; add state
slots `state.s460`, `state.farming`, `state.idc`, `state.s266` with defaults):
"§460 Long-Term Contracts", "Farming UNICAP", "§263(c) IDC", "§266 Carrying
Charges" (items + per-category election inputs). Extend the §263A(f) tab's
projects table with the new designated-property/contract columns. Add the four
new schedules to `IMPORT_TARGETS` with alias tables; keep money fields in
`MONEY_FIELDS`, dates in `DATE_FIELDS`.

**Step 4 — verify chain (all must pass; run from repo root):**
```
python financial_tools/cap263a/standalone/goldens.py
node financial_tools/cap263a/standalone/test_parity.js      # N/N
node financial_tools/cap263a/standalone/test_ingest.js
python financial_tools/cap263a/standalone/build.py
timeout 60 /opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell \
  --headless --disable-gpu --no-sandbox --virtual-time-budget=8000 --dump-dom \
  "file://$PWD/financial_tools/cap263a/standalone/cap263a_calculator.html#buildall" \
  2>/dev/null | grep -o 'data-status="[^"]*"'                # every status PASS
python -m pytest financial_tools/cap263a/tests -q            # fully green incl. freshness gates
```

**Step 5 — docs**: update `standalone/README.md` coverage table (four new tabs +
"library-only, out of scope" note for financial_positions/mining/circulation) and
`docs/FINAL_BUILD_PLAN.md` §2/§5 to match Section 1 of THIS file. Commit, push
(`git push -u origin claude/263a-cost-capitalization-plan-swcokh`), deliver
`standalone/cap263a_calculator.html` to the owner.

**Step 6 — remaining known issues to fix if time allows** (from the shipped-code
review; none block Step 1-5): interview spec's `warning_if`/`derived_checks`/
`requires_schedule_if` are not rendered by the wizard; debt imports keep only the
first §1.263A-9(a)(4) screen per row; SSCM production-cost denominator keeps
non-income-tax Non-Operating dollars (inconsistent with the labor method's
exclusion — SME question, documented in TAX_DECISIONS.md style); small-taxpayer
safe harbor uses the §448(c) receipts figure as a proxy for §1.263(a)-3(h)(3) and
applies engagement-wide rather than per-building; de minimis doesn't model a
written policy specifying a ceiling below $5,000.

## 5. NON-NEGOTIABLE HOUSE RULES (for whoever continues)

1. Python engines are authoritative; the HTML never computes anything the Python
   engines don't; every JS number is pinned by a golden vector.
2. Never guess tax law into code: missing determinative facts → conservative
   treatment + an explicit `open_questions` entry; unimplemented mechanics → a
   loud `CODE-PREFIX` warning, never silence.
3. Regenerate goldens + rebuild the HTML in the SAME commit as any engine change
   (the freshness gates in `tests/test_standalone.py` enforce this).
4. All arithmetic in `Decimal`/`D` — never floats.
