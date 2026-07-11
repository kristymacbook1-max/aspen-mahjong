"""Engagement ingestion — every schedule, any supported upload format.

Formats (BUILD_PLAN.md Phase A + Runtime Pipeline Step 1):
  - .xlsx  one multi-sheet workbook; sheets are routed to schedule parsers by
           title hints (alias-based headers per schedule, same discipline as
           reader.py's TB reader, which is reused verbatim for the TB sheet).
  - .csv   one schedule per file (header row + alias matching).
  - .json  one engagement object: {"trial_balance": [...], "btd": [...],
           "fixed_assets": [...], "cip": [...], "debt": [...], "re": [...],
           "transaction_costs": [...], "intangibles": [...], "startup": [...],
           "qualified_expenditures": [...], "ppa": [...]} — field names may be
           dataclass field names or any header alias.

Missing schedules degrade gracefully (empty lists); structural issues
accumulate in EngagementData.validation (ERRORs block, WARNs don't).
"""

import csv
import json
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

from openpyxl import load_workbook

from .model import (BookTaxDifference, CIPProject, CIPSnapshot, DebtInstrument,
                    EngagementData, FixedAsset, IntangibleItem,
                    PurchasePriceAllocation, QualifiedExpenditureElection,
                    REExpenditure, StartupOrgCostPool, TBLine,
                    TransactionCostItem, ValidationReport)
from .reader import _to_decimal, read_trial_balance

# --------------------------------------------------------------------------
# coercers
# --------------------------------------------------------------------------

_TRUE = {"true", "yes", "y", "1", "x", "t", "domestic", "us", "u.s."}
_FALSE = {"false", "no", "n", "0", "", "f", "none", "foreign", "non-us"}


def _to_bool(v) -> bool:
    """Truthy/falsy table with domestic/foreign aliases (a 'Domestic?' column
    populated 'foreign' previously coerced True via bool(str) — flipping
    mandatory 15-year foreign R&E capitalization into current expensing;
    red-team finding). Unrecognized strings still fall back to bool(s) —
    schedule authors should stick to yes/no."""
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    s = str(v).strip().lower()
    if s in _TRUE:
        return True
    if s in _FALSE:
        return False
    return bool(s)


def _to_date(v) -> Optional[date]:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d", "%d-%b-%Y",
                "%B %d, %Y", "%b %d, %Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _to_int(v) -> int:
    try:
        return int(Decimal(str(v)))
    except Exception:
        return 0


# --------------------------------------------------------------------------
# schedule specs: aliases -> dataclass field, plus per-field coercers.
# every spec key is the dataclass field name; aliases are lowercase.
# --------------------------------------------------------------------------

def _spec(**fields):
    return fields


_SPECS = {
    "btd": (BookTaxDifference, _spec(
        btd_id=(["btd id", "btd #", "id"], str),
        acct_num=(["account number", "acct number", "acct #", "account", "gl account"], str),
        cc_num=(["cost center", "cc", "cc #", "dept", "department", "cost center number"], str),
        description=(["description", "btd description", "difference description"], str),
        adjustment=(["adjustment", "tax minus book", "btd amount", "amount",
                     "tax-book difference", "difference"], _to_decimal),
        category=(["category", "type", "btd type"], str),
        affects_471=(["affects 471", "affects §471", "in 471 costs", "embedded in 471"], _to_bool),
    )),
    "fixed_assets": (FixedAsset, _spec(
        asset_id=(["asset id", "asset #", "asset number", "id"], str),
        description=(["description", "asset description", "asset name"], str),
        asset_type=(["asset type", "type", "property type", "category"], str),
        class_life=(["class life", "macrs life", "recovery period", "life"], _to_decimal),
        cost=(["cost", "book cost", "gross book value", "basis", "original cost"], _to_decimal),
        placed_in_service=(["placed in service", "pis date", "pis", "in service date",
                            "placed in service date"], _to_date),
        cc_num=(["cost center", "cc", "cc #", "dept", "department"], str),
        book_capitalized_interest=(["book capitalized interest", "capitalized interest",
                                    "book cap interest"], _to_decimal),
        is_improvement=(["is improvement", "improvement"], _to_bool),
        demolition_event=(["demolition", "demolition event", "demolished"], _to_bool),
    )),
    "cip": (CIPProject, _spec(
        project_id=(["project id", "project #", "cip id", "id", "project"], str),
        description=(["description", "project description", "project name"], str),
        linked_asset_id=(["linked asset id", "asset id", "target asset", "asset"], str),
        is_real_property=(["is real property", "real property", "real"], _to_bool),
        class_life=(["class life", "recovery period", "life"], _to_decimal),
        total_estimated_cost=(["total estimated cost", "estimated cost", "budget"], _to_decimal),
        production_start=(["production start", "start date", "construction start"], _to_date),
        production_complete=(["production complete", "completion date", "complete date"], _to_date),
        is_improvement=(["is improvement", "improvement"], _to_bool),
        mid_production_purchase_price=(["mid production purchase price",
                                        "purchase price"], _to_decimal),
        unit_id=(["unit id", "unit"], str),
        is_common_feature=(["is common feature", "common feature"], _to_bool),
        contract_role=(["contract role", "role"], str),
        book_capitalized_interest=(["book capitalized interest",
                                    "capitalized interest"], _to_decimal),
    )),
    "debt": (DebtInstrument, _spec(
        debt_id=(["debt id", "loan id", "debt #", "loan #", "id", "loan"], str),
        description=(["description", "loan description", "lender"], str),
        principal=(["principal", "average outstanding", "avg outstanding",
                    "outstanding", "balance"], _to_decimal),
        rate=(["rate", "interest rate", "annual rate"], _to_decimal),
        interest_incurred=(["interest incurred", "interest", "interest expense"], _to_decimal),
        traced_to=(["traced to", "traced project", "project id", "traced"], str),
        related_party_below_afr=(["related party below afr", "below afr"], _to_bool),
        non_interest_bearing=(["non interest bearing", "non-interest bearing"], _to_bool),
        personal_or_qualified_residence=(["personal", "qualified residence"], _to_bool),
        tax_exempt_org_nonbusiness=(["tax exempt", "tax-exempt nonbusiness"], _to_bool),
        disallowed_163_8T=(["disallowed 163-8t", "disallowed"], _to_bool),
    )),
    "re": (REExpenditure, _spec(
        re_id=(["re id", "project id", "id", "project"], str),
        description=(["description", "project description"], str),
        amount=(["amount", "expenditure", "cost"], _to_decimal),
        domestic=(["domestic", "is domestic", "us"], _to_bool),
        tax_year=(["tax year", "year", "year incurred"], _to_int),
        software_development=(["software development", "software", "software dev"], _to_bool),
        book_capitalized_amount=(["book capitalized amount", "book capitalized"], _to_decimal),
    )),
    "transaction_costs": (TransactionCostItem, _spec(
        item_id=(["item id", "id"], str),
        transaction_id=(["transaction id", "transaction", "deal id", "deal"], str),
        description=(["description", "cost description"], str),
        amount=(["amount", "cost", "fee"], _to_decimal),
        cost_type=(["cost type", "type"], str),
        covered_transaction=(["covered transaction", "covered"], _to_bool),
        inherently_facilitative=(["inherently facilitative", "facilitative"], _to_bool),
        incurred_date=(["incurred date", "date incurred", "date"], _to_date),
        bright_line_date=(["bright line date", "bright-line date"], _to_date),
        success_based=(["success based", "success-based", "success fee"], _to_bool),
        transaction_abandoned=(["abandoned", "transaction abandoned"], _to_bool),
    )),
    "intangibles": (IntangibleItem, _spec(
        item_id=(["item id", "intangible id", "id"], str),
        description=(["description", "intangible description"], str),
        amount=(["amount", "cost"], _to_decimal),
        category=(["category", "intangible category", "type"], str),
        acquired_with_business=(["acquired with business", "with business",
                                 "197 eligible", "§197"], _to_bool),
        benefit_start=(["benefit start", "start date", "rights start"], _to_date),
        benefit_end=(["benefit end", "end date", "rights end"], _to_date),
        payment_year=(["payment year", "year paid", "year"], _to_int),
        facilitative_costs=(["facilitative costs", "facilitative"], _to_decimal),
        prior_capitalized_basis=(["prior capitalized basis", "prior basis"], _to_decimal),
    )),
    "startup": (StartupOrgCostPool, _spec(
        pool_id=(["pool id", "id"], str),
        kind=(["kind", "type", "pool type"], str),
        total=(["total", "amount", "total costs"], _to_decimal),
        business_commencement=(["business commencement", "commencement date",
                                "business start", "start date"], _to_date),
    )),
    "qualified_expenditures": (QualifiedExpenditureElection, _spec(
        item_id=(["item id", "id"], str),
        category=(["category", "type"], str),
        amount=(["amount", "expenditure"], _to_decimal),
        elected=(["elected", "59e election", "elect"], _to_bool),
        election_year=(["election year", "year"], _to_int),
    )),
}

# Sheet-title hints per schedule. Matching is WORD-BOUNDED (red-team: the
# bare substring "cip" matched inside "Muni-CIP-al Bonds" and "prinCIPal",
# silently swallowing entire debt schedules; the bare "assets" hint routed
# "Intangible Assets" to the fixed-asset parser). More-specific schedules
# are listed FIRST so "Intangible Assets" resolves before "asset register".
_SHEET_HINTS = {
    "intangibles": ["intangible", "intangibles", "263(a)-4"],
    "transaction_costs": ["transaction cost", "transaction costs",
                          "deal cost", "deal costs", "263(a)-5"],
    "qualified_expenditures": ["59(e)", "qualified expenditure",
                               "qualified expenditures", "59e"],
    "ppa": ["purchase price", "8594", "ppa", "1060"],
    "btd": ["btd", "book-tax", "book tax", "m-1", "schedule m"],
    "fixed_assets": ["fixed asset", "fixed assets", "asset register",
                     "fa schedule"],
    "cip": ["cip", "construction in progress", "construction-in-progress"],
    # bare "loan"/"research" routed "Loan Covenant Fees" to debt and
    # "Research Building Depreciation" (a FIXED-ASSET sheet) to R&E — the
    # latter booked a phantom $850k §174 deduction (round-3 red team).
    # Single-word hints must be schedule-unambiguous.
    "debt": ["debt", "loans", "interest schedule", "borrowings",
             "debt schedule", "loan schedule"],
    "re": ["r&e", "174", "r&d", "research schedule", "r&e schedule",
           "research expenditures", "research & experimental"],
    "startup": ["start-up", "startup", "organizational", "org cost",
                "org costs"],
}


def _hint_matches(title: str) -> List[str]:
    """All schedule kinds a title matches (for ambiguity warnings).
    Underscores/hyphens read as spaces so 'fixed_assets.csv' matches the
    multi-word 'fixed asset' hint."""
    t = title.strip().lower().replace("_", " ").replace("-", " ")
    words = set(re.findall(r"[\w&()]+", t))
    out = []
    for kind, hints in _SHEET_HINTS.items():
        for h in hints:
            h_norm = h.replace("-", " ")
            if (" " in h_norm and h_norm in t) or (h_norm in words):
                out.append(kind)
                break
    return out


# --------------------------------------------------------------------------
# generic row-table parsing
# --------------------------------------------------------------------------

def _rows_from_ws(ws) -> List[Dict[str, object]]:
    """Worksheet -> list of {lowercased header: value} dicts (row 1 = header)."""
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(h or "").strip().lower() for h in rows[0]]
    out = []
    for raw in rows[1:]:
        if raw is None or all(v in (None, "") for v in raw):
            continue
        out.append({h: v for h, v in zip(headers, raw) if h})
    return out


def _rows_from_csv(path) -> List[Dict[str, object]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [{k.strip().lower(): v for k, v in row.items() if k}
                for row in csv.DictReader(f)]


def _parse_rows(kind: str, rows: List[Dict[str, object]],
                source: str, report: ValidationReport) -> list:
    """Alias-match each row dict into the schedule's dataclass."""
    cls, spec = _SPECS[kind]
    out = []
    for i, row in enumerate(rows):
        kwargs = {}
        for fieldname, (aliases, coerce) in spec.items():
            val = row.get(fieldname.replace("_", " "))
            if val is None:
                val = row.get(fieldname)
            if val is None:
                for a in aliases:
                    if a in row:
                        val = row[a]
                        break
            if val is not None:
                kwargs[fieldname] = coerce(val) if coerce is not str else str(val).strip()
        if not kwargs:
            continue
        obj = cls(**kwargs)
        obj.row_index = i + 2
        obj.source_sheet = source
        out.append(obj)
    return out


def _parse_ppa(rows: List[Dict[str, object]], source: str) -> List[PurchasePriceAllocation]:
    """PPA sheet: one row per (transaction, class) or wide per-class columns."""
    by_txn: Dict[str, PurchasePriceAllocation] = {}
    for i, row in enumerate(rows):
        txn = str(row.get("transaction id") or row.get("transaction") or
                  row.get("deal") or "T1").strip()
        ppa = by_txn.setdefault(txn, PurchasePriceAllocation(
            transaction_id=txn, row_index=i + 2, source_sheet=source))
        cons = row.get("aggregate consideration") or row.get("consideration") \
            or row.get("purchase price")
        if cons is not None:
            ppa.aggregate_consideration = _to_decimal(cons)
        klass = str(row.get("class") or "").strip().upper()
        fmv = row.get("fmv") or row.get("fair market value")
        if klass and fmv is not None:
            ppa.class_fmv[klass] = _to_decimal(fmv)
        for k in ("I", "II", "III", "IV", "V", "VI"):
            v = row.get(f"class {k.lower()}") or row.get(f"class_{k.lower()}")
            if v is not None:
                ppa.class_fmv[k] = _to_decimal(v)
    return list(by_txn.values())


def _parse_cip_snapshots(rows: List[Dict[str, object]],
                         projects: List[CIPProject], report: ValidationReport):
    """A 'CIP Snapshots' table (project id, measurement date, cumulative APE)
    attaches dated APE snapshots to their projects."""
    by_id = {p.project_id: p for p in projects}
    for row in rows:
        pid = str(row.get("project id") or row.get("project") or "").strip()
        d = _to_date(row.get("measurement date") or row.get("date"))
        ape = row.get("cumulative ape") or row.get("ape") or row.get("cumulative")
        if not pid or d is None or ape is None:
            continue
        proj = by_id.get(pid)
        if proj is None:
            report.warnings.append(f"CIP snapshot references unknown project {pid!r}")
            continue
        proj.snapshots.append(CIPSnapshot(measurement_date=d, cumulative_ape=_to_decimal(ape)))
    for p in projects:
        p.snapshots.sort(key=lambda s: s.measurement_date or date.min)


def _merge_engagements(dst: EngagementData, src: EngagementData):
    """Fold a nested engagement (a JSON file inside a directory) into dst."""
    for attr in ("tb_lines", "btds", "fixed_assets", "cip_projects", "debts",
                 "re_expenditures", "transaction_costs", "intangibles",
                 "startup_pools", "qualified_expenditures",
                 "purchase_price_allocations"):
        getattr(dst, attr).extend(getattr(src, attr))
    dst.validation.errors.extend(src.validation.errors)
    dst.validation.warnings.extend(src.validation.warnings)


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def _validate(data: EngagementData):
    rep = data.validation
    # duplicate PKs
    for label, items, key in (("FixedAsset", data.fixed_assets, "asset_id"),
                              ("CIPProject", data.cip_projects, "project_id"),
                              ("DebtInstrument", data.debts, "debt_id")):
        seen = set()
        for it in items:
            k = getattr(it, key)
            if k and k in seen:
                rep.errors.append(f"Duplicate {label} {key}={k!r}")
            seen.add(k)
    # FK resolution
    asset_ids = {a.asset_id for a in data.fixed_assets}
    project_ids = {p.project_id for p in data.cip_projects}
    for p in data.cip_projects:
        if p.linked_asset_id and p.linked_asset_id not in asset_ids:
            rep.errors.append(
                f"CIP project {p.project_id!r}: linked_asset_id={p.linked_asset_id!r} "
                f"does not resolve to a FixedAsset")
    for d in data.debts:
        if d.traced_to and d.traced_to not in project_ids:
            rep.errors.append(
                f"Debt {d.debt_id!r}: traced_to={d.traced_to!r} does not resolve "
                f"to a CIP project")
    # sanity warnings
    for a in data.fixed_assets:
        if a.cost < 0:
            rep.warnings.append(f"FixedAsset {a.asset_id!r} has negative cost {a.cost}")
    for d in data.debts:
        if d.interest_incurred < 0:
            rep.warnings.append(f"Debt {d.debt_id!r} has negative interest incurred")


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------

def read_engagement(path=None, *, tb_sheet=None, **schedule_paths) -> EngagementData:
    """Read an engagement from any supported upload shape.

    `path` may be a .xlsx workbook (multi-sheet, routed by title hints), a
    .json engagement file, or a directory of per-schedule .csv/.xlsx files.
    Individual schedules may also be passed explicitly as keyword paths
    (tb_path=..., btd_path=..., assets_path=..., cip_path=..., debt_path=...,
    re_path=..., txncost_path=..., intangibles_path=..., startup_path=...,
    qualified_path=..., ppa_path=...) — explicit paths win over routing.
    """
    data = EngagementData()
    rep = data.validation

    kw_to_kind = {"btd_path": "btd", "assets_path": "fixed_assets",
                  "cip_path": "cip", "debt_path": "debt", "re_path": "re",
                  "txncost_path": "transaction_costs",
                  "intangibles_path": "intangibles", "startup_path": "startup",
                  "qualified_path": "qualified_expenditures", "ppa_path": "ppa"}

    def ingest_rows(kind, rows, source):
        if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
            rep.errors.append(
                f"Schedule {kind!r} from {source}: expected a LIST of row "
                f"objects, got {type(rows).__name__} — schedule skipped.")
            return
        if kind == "ppa":
            data.purchase_price_allocations.extend(_parse_ppa(rows, source))
            return
        parsed = _parse_rows(kind, rows, source, rep)
        if rows and not parsed:
            # data rows in, zero objects out = a misrouted/misheaded sheet
            # silently vanishing (red-team: an entire debt schedule was lost)
            rep.warnings.append(
                f"Schedule {kind!r} from {source}: {len(rows)} data rows "
                f"parsed to ZERO records — headers matched no known alias "
                f"(was this sheet routed to the right schedule?).")
        getattr(data, {"btd": "btds", "fixed_assets": "fixed_assets",
                       "cip": "cip_projects", "debt": "debts",
                       "re": "re_expenditures",
                       "transaction_costs": "transaction_costs",
                       "intangibles": "intangibles",
                       "startup": "startup_pools",
                       "qualified_expenditures": "qualified_expenditures"}[kind]
                ).extend(parsed)

    def ingest_file(kind, p):
        p = Path(p)
        if p.suffix.lower() == ".csv":
            ingest_rows(kind, _rows_from_csv(p), p.name)
        elif p.suffix.lower() in (".xlsx", ".xlsm"):
            wb = load_workbook(p, data_only=True)
            ingest_rows(kind, _rows_from_ws(wb.worksheets[0]), p.name)
        elif p.suffix.lower() == ".json":
            with open(p, encoding="utf-8") as f:
                ingest_rows(kind, json.load(f), p.name)
        else:
            rep.errors.append(f"Unsupported format for {kind}: {p.name}")

    if path is not None:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Engagement source not found: {p}")
        if p.is_dir():
            for child in sorted(p.iterdir()):
                stem = child.stem
                if child.suffix.lower() not in (".csv", ".xlsx", ".xlsm", ".json"):
                    continue
                if child.suffix.lower() == ".json":
                    # an engagement.json inside a directory was silently
                    # skipped (matched no hint) — recurse into it instead
                    data_sub = read_engagement(child)
                    _merge_engagements(data, data_sub)
                    continue
                if "snapshot" in stem.lower():
                    rows = (_rows_from_csv(child) if child.suffix.lower() == ".csv"
                            else _rows_from_ws(load_workbook(child, data_only=True).worksheets[0]))
                    _parse_cip_snapshots(rows, data.cip_projects, rep)
                    continue
                hits = _hint_matches(stem)
                if len(hits) > 1:
                    rep.warnings.append(
                        f"{child.name}: filename matches multiple schedules "
                        f"({', '.join(hits)}) — routed to {hits[0]!r}; rename "
                        f"the file if that's wrong.")
                if hits:
                    ingest_file(hits[0], child)
                elif any(h in stem.lower() for h in ("tb", "trial")):
                    if child.suffix.lower() == ".csv":
                        rep.errors.append(
                            f"{child.name}: trial balances must be .xlsx (the "
                            f"TB reader needs the workbook structure) — "
                            f"convert the CSV or pass it as a JSON "
                            f"trial_balance array.")
                    else:
                        try:
                            data.tb_lines = read_trial_balance(child)
                        except ValueError as e:
                            rep.errors.append(f"{child.name}: {e}")
                else:
                    # a data file matching no hint previously vanished with
                    # zero output (round-3: the round-2 fix warned on
                    # misroutes but not no-routes)
                    rep.warnings.append(
                        f"{child.name}: filename matches no schedule hint — "
                        f"file NOT ingested. Rename it (e.g. 'debt.csv', "
                        f"'fixed_assets.csv') or pass it explicitly.")
        elif p.suffix.lower() == ".json":
            with open(p, encoding="utf-8-sig") as f:   # BOM-tolerant
                doc = json.load(f)
            if not isinstance(doc, dict):
                rep.errors.append(
                    f"{p.name}: an engagement JSON must be an object of "
                    f"schedule arrays, got {type(doc).__name__}.")
                doc = {}
            for key, kind in (("trial_balance", None), ("btd", "btd"),
                              ("fixed_assets", "fixed_assets"), ("cip", "cip"),
                              ("debt", "debt"), ("re", "re"),
                              ("transaction_costs", "transaction_costs"),
                              ("intangibles", "intangibles"),
                              ("startup", "startup"),
                              ("qualified_expenditures", "qualified_expenditures"),
                              ("ppa", "ppa")):
                rows = doc.get(key)
                if not rows:
                    continue
                if not isinstance(rows, list) or \
                        any(not isinstance(r, dict) for r in rows):
                    rep.errors.append(
                        f"{p.name}: schedule {key!r} must be a list of row "
                        f"objects — skipped.")
                    continue
                if key == "trial_balance":
                    data.tb_lines = [
                        TBLine(acct_num=str(r.get("acct_num", "")),
                               acct_desc=str(r.get("acct_desc", r.get("description", ""))),
                               cc_num=str(r.get("cc_num", "")),
                               cc_desc=str(r.get("cc_desc", "")),
                               amount=_to_decimal(r.get("amount")),
                               row_index=i + 1)
                        for i, r in enumerate(rows)]
                else:
                    ingest_rows(kind, [{str(k).strip().lower().replace("_", " "): v
                                        for k, v in r.items()} for r in rows], p.name)
            cip_snaps = doc.get("cip_snapshots")
            if cip_snaps:
                _parse_cip_snapshots(
                    [{str(k).strip().lower().replace("_", " "): v for k, v in r.items()}
                     for r in cip_snaps], data.cip_projects, rep)
            # dated debt balances — without this, Phase D's snapshot traced-
            # debt/WAIR mechanics could NEVER see a dated balance through the
            # reader (red-team, confirmed): {"debt_balances": [{"debt_id":
            # ..., "date": ..., "outstanding": ...}]}
            debt_bals = doc.get("debt_balances")
            if debt_bals:
                by_id = {d.debt_id: d for d in data.debts}
                for r in debt_bals:
                    did = str(r.get("debt_id") or r.get("loan_id") or "").strip()
                    d_ = _to_date(r.get("date") or r.get("measurement_date"))
                    amt = r.get("outstanding") or r.get("balance")
                    debt = by_id.get(did)
                    if debt is None or d_ is None or amt is None:
                        rep.warnings.append(
                            f"debt_balances row skipped (debt_id={did!r}): "
                            f"unknown debt, bad date, or missing amount.")
                        continue
                    debt.outstanding_by_date[d_.isoformat()] = _to_decimal(amt)
        elif p.suffix.lower() in (".xlsx", ".xlsm"):
            wb = load_workbook(p, data_only=True)
            snapshot_rows = None
            for ws in wb.worksheets:
                title = ws.title.strip()
                if "snapshot" in title.lower():
                    snapshot_rows = _rows_from_ws(ws)
                    continue
                hits = _hint_matches(title)
                if len(hits) > 1:
                    rep.warnings.append(
                        f"Sheet {title!r} matches multiple schedules "
                        f"({', '.join(hits)}) — routed to {hits[0]!r}; rename "
                        f"the sheet if that's wrong.")
                if hits:
                    ingest_rows(hits[0], _rows_from_ws(ws), title)
            try:
                data.tb_lines = read_trial_balance(p, sheet=tb_sheet)
            except ValueError as e:
                # a real, structural TB problem (ambiguous sheets, missing
                # amount column) was previously swallowed as "no TB found" —
                # the message said the opposite of the truth (red-team)
                rep.errors.append(f"Trial balance could not be read from "
                                  f"{p.name}: {e}")
            if snapshot_rows:
                _parse_cip_snapshots(snapshot_rows, data.cip_projects, rep)
        else:
            rep.errors.append(f"Unsupported engagement file format: {p.name}")

    tb_path = schedule_paths.pop("tb_path", None)
    if tb_path:
        data.tb_lines = read_trial_balance(tb_path, sheet=tb_sheet)
    for kwname, sched_path in schedule_paths.items():
        kind = kw_to_kind.get(kwname)
        if kind is None:
            raise TypeError(f"Unknown schedule path argument {kwname!r}")
        if sched_path:
            ingest_file(kind, sched_path)

    _validate(data)
    return data
