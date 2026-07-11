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
from openpyxl.utils import get_column_letter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from revenue_recognition.utils.excel_styles import (
    FONT_BODY, FONT_BODY_BOLD, FILL_HIGHLIGHT_BLUE, FILL_HIGHLIGHT_GREEN,
    FILL_HIGHLIGHT_ORANGE, FILL_HIGHLIGHT_RED, THIN_BORDER, ALIGN_LEFT, ALIGN_RIGHT,
    FMT_PERCENT,
    apply_title, apply_section_header, apply_header_row,
)
from .analysis import BUCKETS, CAPITALIZED_BUCKETS

# Accounting-style negatives for a tax workpaper: ($1,234), not -$1,234.
# (The shared style module's format has no negative section.)
FMT_CURRENCY = '"$"#,##0;("$"#,##0)'


def _defuse(v):
    """Spreadsheet-injection defense: a trial balance comes from an untrusted
    source, and openpyxl stores any string beginning with =, +, -, or @ as an
    ACTIVE FORMULA — so a client account description like
    =HYPERLINK("http://evil","click") would execute when a reviewer opens the
    workbook. Prefix a formula-guard apostrophe (Excel's standard neutralizer;
    it renders the text literally and marks the cell text-typed)."""
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@"):
        return "'" + v
    return v

TB_SHEET = "Classified TB"
_TB_HEADERS = [
    "Account #", "Account Description", "Cost Center", "Amount", "Bucket",
    "Cap %", "Cap Amount", "Code", "Tier 1", "MSPM", "Resale", "Self-Const",
    "Interest", "Authority", "Conf", "Flags", "Method (why)", "Zone",
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
        # Engagement-level tabs render only when their engines actually ran
        # (run_engagement path) — the legacy TB-only path keeps exactly the
        # original five tabs, which existing tests pin by name.
        if result.get("tax_basis_tb"):
            self._create_tax_basis_tab()
        if result.get("basis_amortization") or result.get("interest_263af") \
                or result.get("sca"):
            self._create_basis_amortization_tab()
        if any(result.get(k) for k in ("re_174", "intangibles_263a45",
                                       "qualified_59e", "ppa_1060")):
            self._create_engine_results_tab()
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
    def _interest_stub(self) -> float:
        """Legacy scalar §263A(f) stub: APE × avoided-cost rate. §263A(i)
        exempts a small business from ALL of §263A including (f), so the
        exemption zeroes this too. (The real per-unit engine is Phase D.)"""
        p = self._r["profile"]
        if p.small_business_exempt or not p.has_designated_property:
            return 0.0
        return float(p.accumulated_production_expenditures) * float(p.avoided_cost_rate)

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
        cell = ws.cell(r, c, _defuse(v))
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
            # provenance: which rules fired + the detected cost-center zone —
            # the audit trail a reviewer needs to defend the coding on exam
            self._label(ws, r, 17, cl.method)
            self._label(ws, r, 18, cl.notes.replace("zone=", ""))
        self._tb_last = max(_TB_FIRST + len(rows) - 1, _TB_FIRST)

        last_col = get_column_letter(len(_TB_HEADERS))
        if rows:
            # review workflow: filterable, frozen header, red = review (<40),
            # orange = low-confidence (<70)
            ws.auto_filter.ref = f"A3:{last_col}{self._tb_last}"
            ws.freeze_panes = "A4"
            from openpyxl.formatting.rule import CellIsRule
            ws.conditional_formatting.add(
                f"O{_TB_FIRST}:O{self._tb_last}",
                CellIsRule(operator="lessThan", formula=["40"], fill=FILL_HIGHLIGHT_RED))
            ws.conditional_formatting.add(
                f"O{_TB_FIRST}:O{self._tb_last}",
                CellIsRule(operator="lessThan", formula=["70"], fill=FILL_HIGHLIGHT_ORANGE))
            # guard the live SUMIFS: Bucket must be one of the known bucket names
            # (a typo silently drops the line from the Summary waterfall)
            from openpyxl.worksheet.datavalidation import DataValidation
            dv = DataValidation(
                type="list", formula1='"' + ",".join(BUCKETS) + '"', allow_blank=True,
                errorTitle="Unknown bucket",
                error="Bucket must match one of the waterfall bucket names exactly, "
                      "or the line silently drops out of the Summary SUMIFS.")
            ws.add_data_validation(dv)
            dv.add(f"E{_TB_FIRST}:E{self._tb_last}")
        widths = {"B": 34, "C": 22, "D": 15, "E": 18, "N": 40, "P": 8}
        for col, w in {"A": 12, **widths, "H": 14, "I": 20, "Q": 24, "R": 12}.items():
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
        threshold_label = f"${p.sec448_threshold:,.0f}"
        if p.sec448_threshold_is_estimate:
            threshold_label += f"  (2026 figure — VERIFY, TY {p.tax_year} not on file)"
        for lbl, val in [
            ("Entity type", p.entity_type),
            ("§448(c) 3-yr avg gross receipts", f"${p.avg_gross_receipts:,.0f}"),
            ("§448(c) threshold", threshold_label),
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
        # No leading "=" in the label: openpyxl stores any "="-prefixed string
        # as a formula, which Excel then renders as #NAME?.
        self._label(ws, row, 1, "Adjusted currently-deductible", bold=True)
        adj = self._money(ws, row, 3, None, bold=True, fill=FILL_HIGHLIGHT_GREEN)
        adj.value = f"=C{start_row}-C{cap_total_row}-C{mixed_row}"
        adjusted_row = row
        row += 1
        note = self._label(
            ws, row, 1,
            "Bucket/Cap % edits recompute this waterfall live; the UNICAP block below "
            "and tabs 3-5 are computed at generation — re-run the CLI after overrides.")
        note.font = FONT_BODY
        row += 2

        apply_section_header(ws, row, 1, 4, "Checks")
        row += 1
        self._label(ws, row, 1, "Override check: adjusted − classified deductible "
                    "(0 = no analyst Cap%/Bucket overrides; ≠0 flags overrides)", bold=True)
        tie = self._money(ws, row, 3, None, fill=FILL_HIGHLIGHT_ORANGE)
        # This live formula DOES react to analyst edits (the Python-side
        # partition tie_check is 0 by construction and is not a correctness
        # check). A non-zero value here flags Cap%/Bucket overrides.
        ded = self._sumifs("Deductible", "D")[1:] + "+" + self._sumifs("Non-Operating", "D")[1:]
        tie.value = f"=C{adjusted_row}-(" + ded + ")"
        row += 1
        self._label(ws, row, 1, "Lines needing review (REVIEW flag / conf < 40)", bold=True)
        self._label(ws, row, 3, str(self._r["review_count"]))
        row += 1
        self._label(ws, row, 1, "Lines with any flag (incl. LOW-CONF / AMBIGUOUS / CC-*)", bold=True)
        self._label(ws, row, 3, str(self._r.get("flagged_count", "")))
        row += 2

        # --- warnings the workpaper must document (computation + data quality) ---
        cautions = list(self._r["unicap"].get("warnings", []) or [])
        cautions += list(self._r.get("bucket_warnings", []) or [])
        cautions += list(self._r.get("data_quality", []) or [])
        if cautions:
            apply_section_header(ws, row, 1, 4, "Cautions — resolve before signing")
            row += 1
            for w in cautions:
                cell = self._label(ws, row, 1, "⚠ " + str(w))
                cell.fill = FILL_HIGHLIGHT_ORANGE
                ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
                row += 1
            row += 1

        # --- §263A UNICAP computation ---
        u = self._r["unicap"]
        method = u.get("method", "SPM")
        apply_section_header(ws, row, 1, 4, f"§263A UNICAP ({method})")
        row += 1
        if u.get("exempt"):
            self._label(ws, row, 1, u["note"])
        else:
            # Method-specific intermediates: each engine returns its own
            # ratio-table shape (a KeyError here shipped once — the Summary
            # indexed SPM-only keys for every method; see TAX_DECISIONS §16).
            common_top = [
                ("Mixed-service SSCM allocation ratio", u["mixed_alloc_ratio"], True),
                ("Mixed capitalized to §263A", u["mixed_capitalized"], False),
                ("Mixed remaining deductible", u["mixed_deductible"], False),
            ]
            if method == "MSPM":
                method_rows = [
                    ("Pre-production additional §263A pool", u["pre_production_pool"], False),
                    ("Pre-production absorption ratio", u["pre_production_ratio"], True),
                    ("Residual pre-production §263A (rolled to production)",
                     u["residual_pre_production_263A"], False),
                    ("Direct materials adjustment", u["direct_materials_adjustment"], False),
                    ("Production absorption ratio", u["production_ratio"], True),
                    ("Pre-production §471 on hand at year end",
                     u["pre_production_471_on_hand"], False),
                    ("Production §471 on hand at year end",
                     u["production_471_on_hand"], False),
                ]
            elif method == "SRM":
                method_rows = [
                    ("Purchasing ratio", u["purchasing_ratio"], True),
                    ("Storage & handling ratio", u["storage_handling_ratio"], True),
                    ("Combined absorption ratio", u["combined_ratio"], True),
                    ("§471 costs in ending inventory", u["ending_inventory_471"], False),
                ]
            else:
                method_rows = [
                    ("§471 cost pool", u["sec471_pool"], False),
                    ("Additional §263A pool (incl. mixed)", u["additional_263a_pool"], False),
                    ("SPM absorption ratio", u["absorption_ratio"], True),
                    ("§471 costs in ending inventory", u["ending_inventory_471"], False),
                ]
            for lbl, val, pct in common_top + method_rows + [
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
             u.get("additional_capitalized_to_inventory", 0),
             {"MSPM": "MSPM Reg §1.263A-2(c)", "SRM": "SRM Reg §1.263A-3(d)"}.get(
                 u.get("method", "SPM"), "SPM Reg §1.263A-2(b)")),
            ("§263A(f) interest (avoided-cost stub — see Method Changes tab)",
             self._interest_stub(), "Reg §1.263A-9"),
            ("§266 carrying charges (elective)", b["§266 Carrying"], "Reg §1.266-1"),
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
        b0 = self._r["bucket_totals"]
        row = 5
        apply_section_header(ws, row, 1, 4, "§263A(f) interest capitalization (avoided cost)")
        row += 1
        ape = float(p.accumulated_production_expenditures)
        rate = float(p.avoided_cost_rate)
        interest = self._interest_stub()
        exempt_note = " (n/a — §263A(i) small-business exempt)" if p.small_business_exempt else ""
        for lbl, val, pct in [
            ("Designated property?",
             ("Yes" if p.has_designated_property else "No") + exempt_note, None),
            ("Accumulated production expenditures", ape, False),
            ("Avoided-cost rate", rate, True),
            ("Interest capitalized (§263A(f))", interest, False),
            ("§263A(f)-coded lines on classified TB (reference — reconcile before filing)",
             float(b0["§263A(f) Interest"]), False),
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

    # ------------------------------------------------------------------
    # Engagement-level tabs (run_engagement path only)
    # ------------------------------------------------------------------
    def _create_tax_basis_tab(self):
        tb = self._r["tax_basis_tb"]
        ws = self._scaffold(
            "Tax-Basis TB",
            "Runtime Pipeline Step 2: book TB + book-tax differences = the tax-basis "
            "trial balance every downstream computation classifies. The M-1 block "
            "ties by construction; a nonzero tie-check means a BTD was dropped.")
        row = 5
        apply_section_header(ws, row, 1, 3, "M-1 reconciliation")
        row += 1
        m1 = tb["m1_reconciliation"]
        for lbl, key in [("Book P&L total", "book_total"),
                         ("Book-tax differences applied", "btd_total"),
                         ("Tax-basis P&L total", "tax_total"),
                         ("Tie-check (must be 0)", "tie_check")]:
            self._label(ws, row, 1, lbl, bold=True)
            self._money(ws, row, 2, float(m1[key]),
                        fill=FILL_HIGHLIGHT_GREEN if key == "tax_total" else None)
            row += 1
        row += 1
        apply_section_header(ws, row, 1, 3, "Tax-basis totals by cost center")
        row += 1
        for h_i, h in enumerate(["Cost center", "Tax-basis total"]):
            ws.cell(row, 1 + h_i, h)
        apply_header_row(ws, row, 1, 2)
        row += 1
        for cc, amt in sorted(tb["cc_rollup"].items()):
            self._label(ws, row, 1, cc or "(none)")
            self._money(ws, row, 2, float(amt))
            row += 1
        for w in tb["warnings"]:
            self._label(ws, row, 1, f"⚠ {w}")
            row += 1
        ws.column_dimensions["A"].width = 44
        ws.column_dimensions["B"].width = 18

    def _create_basis_amortization_tab(self):
        ws = self._scaffold(
            "Basis & Amortization",
            "The shared Basis & Amortization Schedule — every engine's capitalized "
            "postings in one place (Phases C/D/F/G/H), with first-year amortization "
            "under each item's own convention. recovery = blank means capitalized "
            "with no amortization (land, syndication, indefinite-life pending SME).")
        row = 5
        items = self._r.get("basis_amortization") or []
        if items:
            apply_section_header(ws, row, 1, 7, "Capitalized items (AmortizableItem rows)")
            row += 1
            headers = ["Item", "Category", "Basis", "Recovery (mo)", "Convention",
                       "Year-1 amortization", "Source / flags"]
            for i, h in enumerate(headers):
                ws.cell(row, 1 + i, h)
            apply_header_row(ws, row, 1, len(headers))
            row += 1
            total_basis = total_amort = 0.0
            for it in items:
                self._label(ws, row, 1, f"{it.item_id} {it.description}".strip())
                self._label(ws, row, 2, it.category)
                self._money(ws, row, 3, float(it.basis))
                self._label(ws, row, 4, str(it.recovery_months or ""))
                self._label(ws, row, 5, it.convention)
                amort = float(it.first_year_amortization())
                self._money(ws, row, 6, amort)
                self._label(ws, row, 7, "; ".join([it.source] + list(it.flags)).strip("; "))
                total_basis += float(it.basis)
                total_amort += amort
                row += 1
            self._label(ws, row, 1, "Total", bold=True)
            self._money(ws, row, 3, total_basis, bold=True, fill=FILL_HIGHLIGHT_GREEN)
            self._money(ws, row, 6, total_amort, bold=True)
            row += 2
        interest = self._r.get("interest_263af")
        if interest:
            apply_section_header(ws, row, 1, 7, "§263A(f) interest by unit (avoided-cost method)")
            row += 1
            for i, h in enumerate(["Unit", "Avg excess expenditures", "Traced interest",
                                   "Excess amount", "Total capitalized",
                                   "Book already capitalized", "Tax delta to post"]):
                ws.cell(row, 1 + i, h)
            apply_header_row(ws, row, 1, 7)
            row += 1
            for uid, u in interest["per_unit"].items():
                self._label(ws, row, 1, uid)
                self._money(ws, row, 2, float(u["average_excess"]))
                self._money(ws, row, 3, float(u["traced_interest"]))
                self._money(ws, row, 4, float(u["excess_expenditure_amount"]))
                self._money(ws, row, 5, float(u["total_capitalized"]))
                self._money(ws, row, 6, float(u["book_capitalized_interest"]))
                self._money(ws, row, 7, float(u["tax_delta_to_post"]))
                row += 1
            self._label(ws, row, 1, "Total capitalized (traced + excess)", bold=True)
            self._money(ws, row, 5, float(interest["total_capitalized"]), bold=True,
                        fill=FILL_HIGHLIGHT_GREEN)
            row += 2
        sca = self._r.get("sca")
        if sca:
            apply_section_header(ws, row, 1, 6, "Self-constructed assets (Phase C allocation)")
            row += 1
            for i, h in enumerate(["Asset", "Book cost (A)", "Indirect §263A",
                                   "Mixed §263A", "Additional (B)", "Adjusted basis pre-interest"]):
                ws.cell(row, 1 + i, h)
            apply_header_row(ws, row, 1, 6)
            row += 1
            for aid, a in sca["per_asset"].items():
                self._label(ws, row, 1, aid)
                for ci, key in enumerate(["book_cost", "indirect_263a", "mixed_263a",
                                          "additional_263a", "adjusted_basis_pre_interest"]):
                    self._money(ws, row, 2 + ci, float(a[key]))
                row += 1
        for col, width in (("A", 40), ("B", 18), ("C", 16), ("D", 14),
                           ("E", 14), ("F", 18), ("G", 30)):
            ws.column_dimensions[col].width = width

    def _create_engine_results_tab(self):
        ws = self._scaffold(
            "Engine Results",
            "§174/§174A, §1.263(a)-4/-5 + start-up, §59(e), and §1060 engine outputs. "
            "Detail rows live on Basis & Amortization; this tab is the per-regime "
            "summary plus every engine warning (nothing is stderr-only).")
        row = 5
        re_out = self._r.get("re_174")
        if re_out:
            apply_section_header(ws, row, 1, 4, "§174/§174A research & experimental")
            row += 1
            for lbl, val in [("Capitalized (foreign + elected domestic)",
                              re_out["capitalized_total"]),
                             ("Current-year deduction (expensed domestic + catch-up)",
                              re_out["current_year_deduction"])]:
                self._label(ws, row, 1, lbl, bold=True)
                self._money(ws, row, 2, float(val))
                row += 1
            row += 1
        ig = self._r.get("intangibles_263a45")
        if ig:
            apply_section_header(ws, row, 1, 4,
                                 "§1.263(a)-4/-5 intangibles, transaction costs, start-up")
            row += 1
            for lbl, val in [("Capitalized (posted deltas)", ig["capitalized_total"]),
                             ("Currently deductible", ig["deductible_total"])]:
                self._label(ws, row, 1, lbl, bold=True)
                self._money(ws, row, 2, float(val))
                row += 1
            row += 1
        qe = self._r.get("qualified_59e")
        if qe:
            apply_section_header(ws, row, 1, 4, "§59(e) qualified-expenditure elections")
            row += 1
            if qe["items"]:
                for it in qe["items"]:
                    self._label(ws, row, 1, f"{it.get('item_id', '')} ({it.get('category', '')})")
                    self._money(ws, row, 2, float(it.get("amount", 0)))
                    row += 1
            else:
                self._label(ws, row, 1, "No items scheduled (see gating warning below).")
                row += 1
            row += 1
        for ppa in self._r.get("ppa_1060") or []:
            apply_section_header(ws, row, 1, 4, "§1060 purchase price allocation (Form 8594)")
            row += 1
            for klass, amt in ppa["by_class"].items():
                self._label(ws, row, 1, f"Class {klass}")
                self._money(ws, row, 2, float(amt))
                row += 1
            self._label(ws, row, 1, "Class VII (goodwill/going concern, residual)", bold=True)
            self._money(ws, row, 2, float(ppa["class_vii_residual"]),
                        fill=FILL_HIGHLIGHT_GREEN)
            row += 2
        warnings_ = self._r.get("all_warnings") or []
        if warnings_:
            apply_section_header(ws, row, 1, 4, "All engine warnings")
            row += 1
            for w in warnings_:
                self._label(ws, row, 1, f"⚠ {w}")
                row += 1
        ws.column_dimensions["A"].width = 56
        ws.column_dimensions["B"].width = 18
