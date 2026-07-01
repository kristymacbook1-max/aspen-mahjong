"""Build the Python-in-Excel (=PY()) workbook from the real engine source.

The embedded code is ASSEMBLED FROM the actual model/taxonomy/engine/export
modules (relative imports + file/YAML loading stripped) plus an xl()-based
bootstrap that rebuilds the taxonomy from the hidden reference sheets and
classifies the Raw TB. Because it is the same source, the workbook and the CLI
produce identical classifications — the single-source-of-truth guarantee.

`build_engine_source()` is unit-tested (parity vs the canonical engine) so the
blob can't silently drift.
"""

import os
import re

from openpyxl import Workbook
from .export_reference import export_reference_sheets

_HERE = os.path.dirname(__file__)
# Order matters: model -> taxonomy -> export_reference -> engine
_SOURCE_FILES = ["model.py", "taxonomy.py", "export_reference.py", "engine.py"]

# lines to drop when inlining (relative imports, file/yaml loading, caching)
_STRIP = re.compile(
    r"^\s*(from \.|import yaml|from functools import lru_cache|"
    r"from \.\w+ import|@lru_cache|_DIR\s*=|def _load\(|from openpyxl)")


def _strip_module(src: str) -> str:
    out, skip_load = [], False
    for line in src.splitlines():
        if line.startswith("def _load("):          # drop the yaml file loader body
            skip_load = True
            continue
        if skip_load:
            if line and not line[0].isspace():
                skip_load = False
            else:
                continue
        if _STRIP.match(line):
            continue
        out.append(line)
    return "\n".join(out)


_SHIM = '''
# --- Python-in-Excel shim (no file/yaml/package access) ---
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, List, Dict
try:
    from rapidfuzz import fuzz
    HAS_FUZZY = True
except Exception:
    HAS_FUZZY = False
def lru_cache(*a, **k):
    def deco(fn): return fn
    return deco
_TAX = None
def get_taxonomy():
    return _TAX
'''

_BOOTSTRAP = '''
# --- bootstrap: rebuild taxonomy from hidden sheets, classify the Raw TB ---
import pandas as pd
def _rows(name):
    df = xl(name + "[#All]", headers=True)
    return df.values.tolist()
_data = reference_data_from_rows(_rows("_Categories"), _rows("_CCZones"),
                                 _rows("_CCReclass"), _rows("_GenericMap"),
                                 _rows("_Lexicon"))
_TAX = Taxonomy.from_data(**_data)
_tb = xl("RawTB[#All]", headers=True)
_out = []
for _r in _tb.itertuples(index=False):
    c = classify(acct_num=str(getattr(_r, "Account_Number", "") or ""),
                 acct_desc=str(getattr(_r, "Account_Description", "") or ""),
                 cc_num=str(getattr(_r, "Cost_Center", "") or ""),
                 cc_desc=str(getattr(_r, "Cost_Center_Description", "") or ""),
                 tax=_TAX)
    _out.append([c.code, c.tier1, c.treatment["mspm"], c.treatment["resale"],
                 c.treatment["self_const"], c.treatment["interest"],
                 c.confidence, ", ".join(c.flags), c.authority])
pd.DataFrame(_out, columns=["Code","Tier1","MSPM","Resale","SelfConst","Interest",
                            "Confidence","Flags","Authority"])
'''


def build_engine_source(with_bootstrap: bool = True) -> str:
    parts = [_SHIM]
    for fname in _SOURCE_FILES:
        with open(os.path.join(_HERE, fname)) as fh:
            parts.append(f"# ===== {fname} =====")
            parts.append(_strip_module(fh.read()))
    if with_bootstrap:
        parts.append(_BOOTSTRAP)
    return "\n".join(parts)


def build_pyexcel_workbook(output_path: str, sample_rows=None) -> str:
    wb = Workbook()
    inst = wb.active
    inst.title = "Instructions"
    for i, line in enumerate([
        "§263A / §263(a) / §266 Capitalization — Python-in-Excel edition", "",
        "1. Paste your trial balance into the 'Raw TB' sheet (keep the header row).",
        "2. On the 'Classify' sheet, click cell A1, and in the formula bar enter =PY(",
        "   then paste the entire contents of the 'PY Code' sheet cell A1, and press",
        "   Ctrl+Shift+Enter.",
        "3. Results spill from A1. Confidence < 40 and REVIEW flags need a look.", "",
        "This engine is assembled from the same Python source as the CLI, so the",
        "results are identical by construction. The taxonomy lives in the hidden",
        "_Categories/_CCZones/_CCReclass/_GenericMap/_Lexicon sheets (single source).",
    ]):
        inst.cell(i + 1, 1, line)
    inst.column_dimensions["A"].width = 90

    tb = wb.create_sheet("Raw TB")
    tb.append(["Account Number", "Account Description", "Cost Center",
               "Cost Center Description", "Amount"])
    for r in (sample_rows or []):
        tb.append(r)
    # named range RawTB over the header+data (Excel table would be ideal; a named
    # range keeps openpyxl simple)
    from openpyxl.workbook.defined_name import DefinedName
    last = tb.max_row
    wb.defined_names.add(DefinedName("RawTB", attr_text=f"'Raw TB'!$A$1:$E${max(last,2)}"))

    wb.create_sheet("Classify")
    code_ws = wb.create_sheet("PY Code")
    code_ws["A1"] = build_engine_source(with_bootstrap=True)
    code_ws.column_dimensions["A"].width = 120

    export_reference_sheets(wb)          # hidden _Categories etc. (single exporter)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    wb.save(output_path)
    return output_path
