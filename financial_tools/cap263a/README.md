# cap263a — §263A / §263(a) / §266 Capitalization Tool

A rebuild of the uploaded FTA/EY §263A classifier. The original had a strong
classification *brain* wrapped in broken plumbing: four divergent engine
implementations (Python / VBA / array-formula / two `=PY()` blobs) that gave
different answers, a taxonomy copied seven inconsistent ways, dollar amounts
never carried through (a labeler, not a calc), real tax bugs, a functionally
broken cost-center reclassification map, missing regimes (§266, §263(a)
transaction/intangible, the repair-reg branch), and zero tests.

This rebuild keeps the differentiated model — layered keyword/fuzzy scoring +
cost-center "zone" reclassification + confidence/flags — over **one** data-driven
taxonomy, carries dollars through the full capitalization hierarchy, and emits
the FTA 5-tab workbook.

## Architecture (single source of truth)

```
taxonomy/*.yaml     132 categories on a multi-method schema + CC zones/reclass + lexicon
taxonomy.py         loader + validator (every cross-reference must resolve)
engine.py           one deterministic scored pass (L1 keyword/rule + CC-zone reclass
                    + optional L2 rapidfuzz); L3 semantic is an opt-in plugin
reader.py           robust TB reader that carries dollar AMOUNTS through
analysis.py         dollars -> waterfall buckets; §263A UNICAP (SSCM + SPM absorption);
                    EntityProfile with the §448(c) small-business exception
report.py           FTA 5-tab workbook (Summary Dashboard waterfall, Classified TB,
                    Asset Basis, Adjusted IS, Method Changes) — live SUMIFS + tie-checks
export_reference.py the ONE taxonomy->hidden-sheets exporter
build_pyexcel.py    assembles the =PY() workbook from the real engine source
pipeline.py / cli.py   trial balance in -> workbook out
tests/              33 tests: validation, golden classifications, tax-fix regression,
                    UNICAP math, and single-source parity (exported == CLI)
```

## Usage

```bash
pip install -r financial_tools/cap263a/requirements.txt

# CLI (authoritative)
python -m financial_tools.cap263a.cli TB.xlsx --entity "Acme Inc" \
    --gross-receipts 75000000 --ending-inventory 6000000 \
    --ape 2000000 --avoided-rate 0.06 --designated

# Python
from financial_tools.cap263a import classify, read_trial_balance
from financial_tools.cap263a.pipeline import CapitalizationPipeline
from financial_tools.cap263a.analysis import EntityProfile

# Python-in-Excel workbook (same engine as the CLI, by construction)
from financial_tools.cap263a.build_pyexcel import build_pyexcel_workbook
build_pyexcel_workbook("263A_PyInExcel.xlsx")
```

## Tax fixes applied (verified against the IRS §263A Practice Units)

- Officer compensation → mixed-service allocable (was Non-Operating — the #1
  producer audit issue).
- Capitalizable interest re-tiered to §263A(f) (was Non-Operating).
- `FO-PTAX` no longer flagged as labor; `EX-BID` treated as capitalizable.
- 5 dead cost-center reclass targets corrected (`MSC-RENT`→`MSC-CORPRENT`, …).
- `VAGUE-*` accounts route to **suspense/review**, never to direct labor.
- Added regimes: §266 carrying charges, §263(a) transaction/intangible, §263(a)
  tangible (repair vs improvement/BAR), §263A(f) interest, negative §263A.

## Deferred (data contracts defined; compute later)

- Per-asset Asset Basis detail (needs a beginning balance sheet); currently by
  regime.
- Full MSPM two-ratio and SRM combined-ratio methods (SPM is implemented; codes
  carry the P/S/pre-production distinctions for these).
- Layer 3 semantic similarity plugin (sentence-transformers; off by default).
- Live Form 3115 DCN mapping to the current Rev. Proc. (DCNs shown are
  representative).

Not in scope: the EY-strategy platform modules (§168(n), §163(j), §45X/§48D,
cost seg).
