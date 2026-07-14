# Standalone HTML calculator

`cap263a_calculator.html` is a **single self-contained file** that runs every
cap263a numeric engine in the browser — double-click it on any computer
(no server, no install, works offline from `file://`).

## What it computes

| Tab | Engine (Python source of truth) |
| --- | --- |
| Entity Profile | §448(c)/§263A(i) exemption gate, thresholds (`analysis.EntityProfile`) |
| Trial Balance & UNICAP | waterfall buckets → SSCM → SPM / MSPM (HAR, LIFO combined ratio, 90% split, $200K de minimis) / SRM (variations A/B, availability gates) (`analysis.py`, `engines/inventory.py`) |
| Tax-Basis TB | book-tax differences → materialized tax-basis TB + M-1 (`engines/tax_basis_tb.py`) |
| LIFO Decrement Release | §1.263A-2(b)(3)(iii)(C) layer liquidation (`engines/inventory.py`) |
| §263A(f) Interest | avoided-cost: snapshots, WAIR, debt screens, (c)(7) proration, consumption (`engines/interest.py`) |
| Self-Constructed Assets | Phase C bucket-B pool allocation + SSCM gating (`engines/sca.py`) |
| §174/§174A R&E | foreign mandatory / domestic default / §174A(c) election, 2022-24 catch-up (`engines/re_capitalization.py`) |
| §263(a)-4/-5 & Start-up | transaction costs, 12-month rule, $5K cliff, §195/§248/§709, §280B (`engines/intangibles.py`) |
| §59(e) Elections | qualified-expenditure amortization + entity gate (`engines/qualified_expenditures.py`) |
| §1060 Allocation | Form 8594 residual method (`engines/purchase_price_allocation.py`) |
| §263(a) Tangible Property | de minimis / M&S / small-taxpayer building safe harbors, BAR improvement tests, routine maintenance, (n) election — with an **open-questions** channel for missing facts (`engines/tangible_263a.py`) |
| Import Files | offline CSV/XLSX/JSON ingestion into any schedule, alias-mapped the same way the Python readers do (`standalone/ingest.js`) |
| Interview | guided question graph mirroring the desktop tool's Phase E interview, plus pre-compute completeness checks (`standalone/interview_spec.json`) |

The keyword **classifier is not embedded** — the Trial Balance tab takes
analyst-assigned tiers (the same review step the desktop tool routes
low-confidence lines to). Everything numeric downstream is a faithful port.
See `docs/FINAL_BUILD_PLAN.md` (repo root, `financial_tools/cap263a/docs/`)
for the full coverage matrix and the honest list of what's deliberately not
computed (warned, never silent).

## How parity is enforced

- Arithmetic is exact decimal (BigInt), mirroring Python `Decimal` — 28-digit
  half-even division, half-even/half-up quantization per engine.
- `goldens.py` runs 87 scenario specs through the **Python** engines →
  `goldens.json`. `test_parity.js` (Node) and the in-file **Self-Tests tab**
  run the identical specs through the **JS** engines and compare every number.
- `test_ingest.js` covers the file-parsing layer separately (CSV quoting/
  sniffing, amount cleanup, header detection, a real XLSX round-trip built
  via Python openpyxl, and a hand-built stored-entry ZIP).
- `tests/test_standalone.py` gates CI: stale goldens, stale built HTML, a
  JS/Python divergence, or an ingest.js regression all fail the suite.

## Rebuilding after an engine change

```bash
python financial_tools/cap263a/standalone/goldens.py   # refresh vectors from Python engines
python financial_tools/cap263a/standalone/build.py     # re-inline everything into the HTML
node financial_tools/cap263a/standalone/test_parity.js # verify N/N
node financial_tools/cap263a/standalone/test_ingest.js # verify the file-ingest module
```

Headless browser verification (self-tests + all panels + UI smoke):

```bash
chromium --headless --dump-dom "file://$PWD/financial_tools/cap263a/standalone/cap263a_calculator.html#buildall" \
  | grep -o 'data-status="[^"]*"'
```
