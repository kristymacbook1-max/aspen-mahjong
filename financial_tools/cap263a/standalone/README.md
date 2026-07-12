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

The keyword **classifier is not embedded** — the Trial Balance tab takes
analyst-assigned tiers (the same review step the desktop tool routes
low-confidence lines to). Everything numeric downstream is a faithful port.

## How parity is enforced

- Arithmetic is exact decimal (BigInt), mirroring Python `Decimal` — 28-digit
  half-even division, half-even/half-up quantization per engine.
- `goldens.py` runs 75 scenario specs through the **Python** engines →
  `goldens.json`. `test_parity.js` (Node) and the in-file **Self-Tests tab**
  run the identical specs through the **JS** engines and compare every number.
- `tests/test_standalone.py` gates CI: stale goldens, stale built HTML, or a
  JS/Python divergence all fail the suite.

## Rebuilding after an engine change

```bash
python financial_tools/cap263a/standalone/goldens.py   # refresh vectors from Python engines
python financial_tools/cap263a/standalone/build.py     # re-inline everything into the HTML
node financial_tools/cap263a/standalone/test_parity.js # verify 75/75
```

Headless browser verification (self-tests + all panels + UI smoke):

```bash
chromium --headless --dump-dom "file://$PWD/financial_tools/cap263a/standalone/cap263a_calculator.html#buildall" \
  | grep -o 'data-status="[^"]*"'
```
