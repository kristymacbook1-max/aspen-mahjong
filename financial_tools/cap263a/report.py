"""FTA 5-tab capitalization workbook.

Tab 1 Summary Dashboard (dollar waterfall) · Tab 2 Classified TB ·
Tab 3 Asset Basis Schedule · Tab 4 Adjusted IS · Tab 5 Method Changes.

Reuses the repo's shared Excel styling (revenue_recognition/utils/excel_styles)
and the live-formula + tie-check pattern from cost_capitalization. The Summary
waterfall reads the Classified TB via SUMIFS, so editing a line's Cap % or
Bucket recomputes the whole dashboard.
"""

import os
import sys

from openpyxl import Workbook

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from revenue_recognition.utils.excel_styles import (
    FONT_BODY, FONT_BODY_BOLD, FILL_HIGHLIGHT_BLUE, FILL_HIGHLIGHT_GREEN,
    FILL_HIGHLIGHT_ORANGE, FILL_HIGHLIGHT_RED, THIN_BORDER, ALIGN_LEFT, ALIGN_RIGHT,
    FMT_CURRENCY, FMT_PERCENT,
    apply_title, apply_section_header, apply_header_row,
)
from .analysis import BUCKETS, CAPITALIZED_BUCKETS

TB_SHEET = "Classified TB"
_TB_HEADERS = [
    "Account #", "Account Description", "Cost Center", "Amount", "Bucket",
    "Cap %", "Cap Amount", "Code", "Tier 1", "MSPM", "Resale", "Self-Const",
    "Interest", "Authority", "Conf", "Flags",
]
_TB_FIRST = 4  # first data row on Classified TB


class CapitalizationReport:
    def generate(self, result: dict, output_path: str) -> str:
        self._r = result
        self._wb = Workbook()
        self._wb.remove(self._wb.active)
        self._create_classified_tb()      # build first: Summary references it
        self._n = len([r for r in result["rows"]])
        self._create_summary()
        self._create_asset_basis()
        self._create_adjusted_is()
        self._create_method_changes()
        # order tabs: Summary first. The offset must be relative to Summary
        # Dashboard's OWN current index (it's created 2nd, right after
        # Classified TB, not last) — a fixed "-(total sheets - 1)" offset only
        # lands correctly if the sheet being moved happens to be the last one,
        # which silently failed to reorder anything here.
        idx = self._wb.sheetnames.index("Summary Dashboard")
        self._wb.move_sheet("Summary Dashboard", -idx)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        self._wb.save(output_path)
        return output_path

    # ------------------------------------------------------------------
    def _money(self, ws, r, c, v, fill=None, bold=False):
        cell = ws.cell(r, c, v)
        cell.number_format = FMT_CURRENCY
        cell.font = FONT_BODY_BOLD if bold else FONT_BODY
        cell.alignment = ALIGN_RIGHT
        cell.border = THIN_BORDER
        if fill:
            cell.fill = fill
        return cell

    def _label(self, ws, r, c, v, bold=False):
        cell = ws.cell(r, c, v)
        cell.font = FONT_BODY_BOLD if bold else FONT_BODY
        cell.alignment = ALIGN_LEFT
        return cell

    # ------------------------------------------------------------------
    def _create_classified_tb(self):
        ws = self._wb.create_sheet(TB_SHEET)
        apply_title(ws, 1, 1, len(_TB_HEADERS), "Classified Trial Balance")
        for i, h in enumerate(_TB_HEADERS):
            ws.cell(3, 1 + i, h)
        apply_header_row(ws, 3, 1, len(_TB_HEADERS))

        rows = self._r["rows"]
        for i, cr in enumerate(rows):
            r = _TB_FIRST + i
            ln, cl = cr.line, cr.cls
            self._label(ws, r, 1, ln.acct_num)
            self._label(ws, r, 2, ln.acct_desc)
            self._label(ws, r, 3, ln.cc_desc or ln.cc_num)
            self._money(ws, r, 4, float(ln.amount))
            self._label(ws, r, 5, cr.bucket)
            capdefault = 1.0 if cr.bucket in CAPITALIZED_BUCKETS else 0.0
            cp = ws.cell(r, 6, capdefault)
            cp.number_format = FMT_PERCENT
            cp.alignment = ALIGN_RIGHT
            cp.border = THIN_BORDER
            cp.fill = FILL_HIGHLIGHT_BLUE
            ca = ws.cell(r, 7, f"=D{r}*F{r}")      # live: cap amount
            ca.number_format = FMT_CURRENCY
            ca.alignment = ALIGN_RIGHT
            ca.border = THIN_BORDER
            ca.fill = FILL_HIGHLIGHT_GREEN
            self._label(ws, r, 8, cl.code)
            self._label(ws, r, 9, cl.tier1)
            self._label(ws, r, 10, cl.treatment.get("mspm"))
            self._label(ws, r, 11, cl.treatment.get("resale"))
            self._label(ws, r, 12, cl.treatment.get("self_const"))
            self._label(ws, r, 13, cl.treatment.get("interest"))
            self._label(ws, r, 14, cl.authority)
            cf = ws.cell(r, 15, cl.confidence)
            cf.alignment = ALIGN_RIGHT
            cf.border = THIN_BORDER
            self._label(ws, r, 16, ", ".join(cl.flags))
        self._tb_last = max(_TB_FIRST + len(rows) - 1, _TB_FIRST)

        # conditional flag: low-confidence rows (skip on an empty TB — an
        # inverted O4:O3 range crashes openpyxl's ConditionalFormatting)
        if rows:
            from openpyxl.formatting.rule import CellIsRule
            ws.conditional_formatting.add(
                f"O{_TB_FIRST}:O{self._tb_last}",
                CellIsRule(operator="lessThan", formula=["40"], fill=FILL_HIGHLIGHT_ORANGE))
        widths = {"B": 34, "C": 22, "D": 15, "E": 18, "N": 40, "P": 8}
        for col, w in {"A": 12, **widths, "H": 14, "I": 20}.items():
            ws.column_dimensions[col].width = w

    def _sumifs(self, bucket, col="G"):
        return (f"=SUMIFS('{TB_SHEET}'!${col}${_TB_FIRST}:${col}${self._tb_last},"
                f"'{TB_SHEET}'!$E${_TB_FIRST}:$E${self._tb_last},\"{bucket}\")")

    # ------------------------------------------------------------------
    def _create_summary(self):
        ws = self._wb.create_sheet("Summary Dashboard")
        p = self._r["profile"]
        apply_title(ws, 1, 1, 4,
                    f"Capitalization Summary — {p.entity_name or 'Entity'} (TY {p.tax_year})")
        row = 3
        apply_section_header(ws, row, 1, 4, "Entity & exemption")
        row += 1
        for lbl, val in [
            ("Entity type", p.entity_type),
            ("§448(c) 3-yr avg gross receipts", f"${p.avg_gross_receipts:,.0f}"),
            ("§448(c) threshold", f"${p.sec448_threshold:,.0f}"),
            ("Small-business exempt (§263A(i))",
             "YES — UNICAP off" if p.small_business_exempt else "No"),
            ("De minimis ceiling", f"${p.de_minimis_ceiling:,.0f}"),
        ]:
            self._label(ws, row, 1, lbl, bold=True)
            self._label(ws, row, 3, str(val))
            row += 1
        row += 1

        apply_section_header(ws, row, 1, 4, "Capitalization waterfall")
        row += 1
        self._label(ws, row, 1, "Starting income-statement total", bold=True)
        start_row = row
        c = self._money(ws, row, 3, None, bold=True)
        # sum of all bucket totals (every IS line lands in exactly one bucket)
        c.value = "=" + "+".join(self._sumifs(b, "D")[1:] for b in BUCKETS)
        row += 1
        # less each capitalized bucket (from live Cap Amount col G)
        cap_rows = []
        for b in CAPITALIZED_BUCKETS:
            self._label(ws, row, 1, f"  less: {b}")
            cc = self._money(ws, row, 3, None)
            cc.value = self._sumifs(b, "G")
            cap_rows.append(row)
            row += 1
        self._label(ws, row, 1, "Total capitalized", bold=True)
        tc = self._money(ws, row, 3, None, fill=FILL_HIGHLIGHT_GREEN, bold=True)
        tc.value = f"=SUM(C{cap_rows[0]}:C{cap_rows[-1]})"
        cap_total_row = row
        row += 1
        self._label(ws, row, 1, "  Mixed service (pending §263A allocation)")
        mc = self._money(ws, row, 3, None, fill=FILL_HIGHLIGHT_ORANGE)
        mc.value = self._sumifs("Mixed (allocable)", "D")
        mixed_row = row
        row += 1
        self._label(ws, row, 1, "= Adjusted currently-deductible", bold=True)
        adj = self._money(ws, row, 3, None, bold=True, fill=FILL_HIGHLIGHT_GREEN)
        adj.value = f"=C{start_row}-C{cap_total_row}-C{mixed_row}"
        row += 2

        apply_section_header(ws, row, 1, 4, "Checks")
        row += 1
        self._label(ws, row, 1, "Tie check: adjusted − classified deductible (0 = no overrides)", bold=True)
        tie = self._money(ws, row, 3, None, fill=FILL_HIGHLIGHT_ORANGE)
        # adjusted deductible should equal Deductible + Non-Operating buckets when
        # no Cap % has been overridden; a non-zero value flags analyst overrides.
        ded = self._sumifs("Deductible", "D")[1:] + "+" + self._sumifs("Non-Operating", "D")[1:]
        tie.value = f"=C{row-3}-(" + ded + ")"
        row += 1
        self._label(ws, row, 1, "Lines flagged for review", bold=True)
        self._label(ws, row, 3, str(self._r["review_count"]))
        row += 2

        # --- §263A UNICAP computation ---
        u = self._r["unicap"]
        apply_section_header(ws, row, 1, 4, "§263A UNICAP")
        row += 1
        if u.get("exempt"):
            self._label(ws, row, 1, u["note"])
        else:
            for lbl, val, pct in [
                ("Mixed-service SSCM allocation ratio", u["mixed_alloc_ratio"], True),
                ("Mixed capitalized to §263A", u["mixed_capitalized"], False),
                ("Mixed remaining deductible", u["mixed_deductible"], False),
                ("§471 cost pool", u["sec471_pool"], False),
                ("Additional §263A pool (incl. mixed)", u["additional_263a_pool"], False),
                ("SPM absorption ratio", u["absorption_ratio"], True),
                ("§471 costs in ending inventory", u["ending_inventory_471"], False),
                ("Additional §263A capitalized to ending inventory",
                 u["additional_capitalized_to_inventory"], False),
                ("Adjusted deductible after mixed allocation",
                 u["adjusted_deductible_post"], False),
            ]:
                self._label(ws, row, 1, lbl, bold=True)
                cell = ws.cell(row, 3, float(val))
                cell.number_format = FMT_PERCENT if pct else FMT_CURRENCY
                cell.alignment = ALIGN_RIGHT
                cell.border = THIN_BORDER
                if "absorption" in lbl or "capitalized to ending" in lbl:
                    cell.fill = FILL_HIGHLIGHT_GREEN
                row += 1
        for col, w in {"A": 46, "C": 20}.items():
            ws.column_dimensions[col].width = w

    # ------------------------------------------------------------------
    def _scaffold(self, name, note):
        ws = self._wb.create_sheet(name)
        apply_title(ws, 1, 1, 4, name)
        self._label(ws, 3, 1, note)
        ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=6)
        ws.column_dimensions["A"].width = 30
        return ws

    def _create_asset_basis(self):
        ws = self._scaffold(
            "Asset Basis Schedule",
            "Capitalization additions by regime. Per-asset original basis is seeded from "
            "beginning balance-sheet detail when provided; otherwise additions are shown by regime.")
        row = 5
        self._headers = ["Regime", "Capitalized additions", "Authority"]
        for i, h in enumerate(self._headers):
            ws.cell(row, 1 + i, h)
        apply_header_row(ws, row, 1, 3)
        row += 1
        b = self._r["bucket_totals"]
        u = self._r["unicap"]
        items = [
            ("§263(a) Mandatory (tangible + transaction/intangible)", b["§263(a) Mandatory"],
             "Reg §1.263(a)-2/-3/-4/-5"),
            ("§263(a) Elective (safe-harbor capitalize)", b["§263(a) Elective"],
             "Reg §1.263(a)-1(f)/-3(h)(i)(n)"),
            ("§263A additional cost to ending inventory",
             u.get("additional_capitalized_to_inventory", 0), "SPM Reg §1.263A-2(b)"),
            ("§263A(f) interest (see Method Changes tab)", 0, "Reg §1.263A-9"),
        ]
        first = row
        for lbl, val, auth in items:
            self._label(ws, row, 1, lbl)
            self._money(ws, row, 2, float(val))
            self._label(ws, row, 3, auth)
            row += 1
        self._label(ws, row, 1, "Total basis additions", bold=True)
        c = ws.cell(row, 2, f"=SUM(B{first}:B{row-1})")
        c.number_format = FMT_CURRENCY
        c.font = FONT_BODY_BOLD
        c.alignment = ALIGN_RIGHT
        c.border = THIN_BORDER
        c.fill = FILL_HIGHLIGHT_GREEN
        ws.column_dimensions["A"].width = 52
        ws.column_dimensions["B"].width = 22
        ws.column_dimensions["C"].width = 30

    def _create_adjusted_is(self):
        ws = self._scaffold(
            "Adjusted IS",
            "Income-statement expenses remaining deductible after all capitalization layers.")
        row = 5
        for i, h in enumerate(["Account #", "Description", "Cost Center", "Amount", "Basis"]):
            ws.cell(row, 1 + i, h)
        apply_header_row(ws, row, 1, 5)
        row += 1
        first = row
        for cr in self._r["rows"]:
            if cr.bucket in ("Deductible", "Non-Operating"):
                self._label(ws, row, 1, cr.line.acct_num)
                self._label(ws, row, 2, cr.line.acct_desc)
                self._label(ws, row, 3, cr.line.cc_desc or cr.line.cc_num)
                self._money(ws, row, 4, float(cr.line.amount))
                self._label(ws, row, 5, cr.bucket)
                row += 1
        # plus the deductible remainder of mixed-service costs
        u = self._r["unicap"]
        self._label(ws, row, 1, "", )
        self._label(ws, row, 2, "Mixed-service deductible remainder (post-SSCM)", bold=True)
        self._money(ws, row, 4, float(u.get("mixed_deductible", 0)))
        row += 1
        self._label(ws, row, 1, "TOTAL remaining deductible", bold=True)
        c = ws.cell(row, 4, f"=SUM(D{first}:D{row-1})")
        c.number_format = FMT_CURRENCY
        c.font = FONT_BODY_BOLD
        c.alignment = ALIGN_RIGHT
        c.border = THIN_BORDER
        c.fill = FILL_HIGHLIGHT_GREEN
        ws.column_dimensions["B"].width = 40
        ws.column_dimensions["C"].width = 22
        ws.column_dimensions["D"].width = 16

    def _create_method_changes(self):
        ws = self._scaffold(
            "Method Changes",
            "§263A(f) interest capitalization and accounting-method-change candidates. "
            "DCNs are representative (confirm against the current Rev. Proc. list); "
            "§481(a) = catch-up on adopting the proper method.")
        p = self._r["profile"]
        u = self._r["unicap"]
        row = 5
        apply_section_header(ws, row, 1, 4, "§263A(f) interest capitalization (avoided cost)")
        row += 1
        ape = float(p.accumulated_production_expenditures)
        rate = float(p.avoided_cost_rate)
        interest = ape * rate if p.has_designated_property else 0.0
        for lbl, val, pct in [
            ("Designated property?", "Yes" if p.has_designated_property else "No", None),
            ("Accumulated production expenditures", ape, False),
            ("Avoided-cost rate", rate, True),
            ("Interest capitalized (§263A(f))", interest, False),
        ]:
            self._label(ws, row, 1, lbl, bold=True)
            if pct is None:
                self._label(ws, row, 3, str(val))
            else:
                c = ws.cell(row, 3, val)
                c.number_format = FMT_PERCENT if pct else FMT_CURRENCY
                c.alignment = ALIGN_RIGHT
                c.border = THIN_BORDER
                if "Interest capitalized" in lbl:
                    c.fill = FILL_HIGHLIGHT_GREEN
            row += 1
        row += 1

        apply_section_header(ws, row, 1, 4, "Accounting-method-change candidates")
        row += 1
        for i, h in enumerate(["Regime / issue", "Amount", "Repr. DCN", "§481(a) note"]):
            ws.cell(row, 1 + i, h)
        apply_header_row(ws, row, 1, 4)
        row += 1
        b = self._r["bucket_totals"]
        candidates = [
            ("§263A UNICAP (additional costs to inventory)",
             float(u.get("additional_capitalized_to_inventory", 0)), "DCN 22",
             "§481(a) on beginning inventory revaluation (Reg §1.263A-7)"),
            ("§263(a) tangible / repair regs",
             float(b["§263(a) Mandatory"] + b["§263(a) Elective"]), "DCN 184-193",
             "Cut-off or §481(a) per change"),
            ("§263A(f) interest capitalization", interest, "DCN 22",
             "§481(a) if not previously capitalizing"),
            ("§266 carrying-charge election", float(b["§266 Carrying"]), "n/a (annual election)",
             "Statement on original return; no §481(a)"),
        ]
        for lbl, val, dcn, note in candidates:
            self._label(ws, row, 1, lbl)
            self._money(ws, row, 2, val)
            self._label(ws, row, 3, dcn)
            self._label(ws, row, 4, note)
            row += 1
        ws.column_dimensions["A"].width = 44
        ws.column_dimensions["B"].width = 16
        ws.column_dimensions["C"].width = 16
        ws.column_dimensions["D"].width = 46
