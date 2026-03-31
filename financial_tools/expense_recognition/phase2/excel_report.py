"""Phase 2 Expense Recognition Excel Report Generator.

Produces an 8-tab workbook from Phase 2 analysis results:
  1. Executive Summary
  2. Book-Tax Differences
  3. Trial Balance Summary
  4. Accrued Liability Rollforward
  5. Compensation & Benefits
  6. M-1/M-3 Adjustments
  7. Detailed Findings
  8. Phase 3 Roadmap
"""

import os
import sys
from decimal import Decimal
from openpyxl import Workbook

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from revenue_recognition.utils.excel_styles import (
    FONT_TITLE, FONT_SECTION_HEADER, FONT_COLUMN_HEADER, FONT_BODY,
    FONT_BODY_BOLD, FILL_SECTION, FILL_ALT_ROW, FILL_HIGHLIGHT_BLUE,
    THIN_BORDER, ALIGN_CENTER, ALIGN_LEFT, ALIGN_RIGHT, ALIGN_WRAP,
    FMT_CURRENCY, apply_header_row, apply_section_header, apply_title,
    auto_fit_columns, write_data_row, format_currency_cell,
    get_risk_font, get_risk_fill,
)
from revenue_recognition.utils.currency_helpers import to_decimal, format_currency


class Phase2ExpenseReport:
    """Generates the Phase 2 expense recognition Excel workbook."""

    def generate(self, results: dict, output_path: str) -> str:
        self._r = results
        self._wb = Workbook()
        self._wb.remove(self._wb.active)

        self._create_executive_summary()
        self._create_book_tax_differences()
        self._create_trial_balance_summary()
        self._create_accrued_rollforward()
        self._create_compensation()
        self._create_m1_adjustments()
        self._create_findings()
        self._create_phase3_roadmap()

        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        self._wb.save(output_path)
        return output_path

    # ------------------------------------------------------------------
    def _create_executive_summary(self):
        ws = self._wb.create_sheet("Executive Summary")
        apply_title(ws, 1, 1, 5, f"Phase 2 Expense Analysis — {self._r['company_name']}")
        row = 3

        apply_section_header(ws, row, 1, 5, "Key Metrics")
        row += 1
        ti = self._r["tax_impact"]
        metrics = [
            ("Total Temporary Differences", ti["total_temporary_differences"]),
            ("Total Permanent Differences", ti["total_permanent_differences"]),
            ("Temporary Tax Impact", ti["temporary_tax_impact"]),
            ("Permanent Tax Impact", ti["permanent_tax_impact"]),
            ("Total Tax Impact", ti["total_tax_impact"]),
            ("Net DTA/DTL", None),
        ]
        for label, val in metrics:
            ws.cell(row=row, column=1, value=label).font = FONT_BODY_BOLD
            if val is not None:
                c = ws.cell(row=row, column=2, value=float(to_decimal(val)))
                format_currency_cell(c)
            else:
                ws.cell(row=row, column=2, value=ti["net_dta_dtl"]).font = FONT_BODY
            row += 1

        row += 1
        apply_section_header(ws, row, 1, 5, "Top Findings")
        row += 1
        for f in self._r["findings"][:6]:
            ws.cell(row=row, column=1, value=f["area"]).font = FONT_BODY_BOLD
            ws.cell(row=row, column=2, value=f["description"]).font = FONT_BODY
            c = ws.cell(row=row, column=3, value=float(to_decimal(f["book_tax_difference"])))
            format_currency_cell(c)
            ws.cell(row=row, column=4, value=f["risk_level"].upper()).font = get_risk_font(f["risk_level"])
            row += 1

        auto_fit_columns(ws)

    # ------------------------------------------------------------------
    def _create_book_tax_differences(self):
        ws = self._wb.create_sheet("Book-Tax Differences")
        apply_title(ws, 1, 1, 7, "Complete Book-Tax Difference Listing")
        row = 3

        headers = ["Account", "Description", "Book-Tax Diff", "Type",
                    "IRC Section", "Notes"]
        for i, h in enumerate(headers, 1):
            ws.cell(row=row, column=i, value=h)
        apply_header_row(ws, row, 1, len(headers))
        row += 1

        for item in self._r["book_tax_differences"]["items"]:
            write_data_row(ws, row, [
                item["account"], item["description"],
                float(to_decimal(item["book_tax_difference"])),
                item["type"], item["irc_section"], item["notes"],
            ], alternate=(row % 2 == 0))
            format_currency_cell(ws.cell(row=row, column=3))
            row += 1

        row += 1
        bt = self._r["book_tax_differences"]
        for label, val in [("Total Temporary", bt["total_temporary"]),
                           ("Total Permanent", bt["total_permanent"]),
                           ("Grand Total", bt["total"])]:
            ws.cell(row=row, column=1, value=label).font = FONT_BODY_BOLD
            c = ws.cell(row=row, column=3, value=float(to_decimal(val)))
            format_currency_cell(c)
            c.font = FONT_BODY_BOLD
            row += 1

        auto_fit_columns(ws)

    # ------------------------------------------------------------------
    def _create_trial_balance_summary(self):
        ws = self._wb.create_sheet("Trial Balance Summary")
        apply_title(ws, 1, 1, 6, "Expense Account Summary by Category")
        row = 3

        # Group TB accounts by subcategory
        from collections import defaultdict
        groups = defaultdict(list)
        for mapping in self._r.get("book_tax_differences", {}).get("items", []):
            groups[mapping.get("irc_section", "Other")].append(mapping)

        for section, items in sorted(groups.items()):
            apply_section_header(ws, row, 1, 6, section or "Other")
            row += 1
            headers = ["Account", "Description", "Book-Tax Diff", "Type"]
            for i, h in enumerate(headers, 1):
                ws.cell(row=row, column=i, value=h)
            apply_header_row(ws, row, 1, len(headers))
            row += 1

            for item in items:
                write_data_row(ws, row, [
                    item["account"], item["description"],
                    float(to_decimal(item["book_tax_difference"])), item["type"],
                ], alternate=(row % 2 == 0))
                format_currency_cell(ws.cell(row=row, column=3))
                row += 1
            row += 1

        auto_fit_columns(ws)

    # ------------------------------------------------------------------
    def _create_accrued_rollforward(self):
        ws = self._wb.create_sheet("Accrued Liability Rollforward")
        apply_title(ws, 1, 1, 9, "Accrued Liability Rollforward & EP Analysis")
        row = 3

        headers = ["Liability", "Beg Balance", "Additions", "Payments",
                    "End Balance", "Tax Deduction", "EP Category",
                    "Timing Diff", "EP Rule"]
        for i, h in enumerate(headers, 1):
            ws.cell(row=row, column=i, value=h)
        apply_header_row(ws, row, 1, len(headers))
        row += 1

        for item in self._r["economic_performance"]["items"]:
            write_data_row(ws, row, [
                item["name"],
                float(to_decimal(item["beginning_balance"])),
                float(to_decimal(item["additions"])),
                float(to_decimal(item["payments"])),
                float(to_decimal(item["ending_balance"])),
                float(to_decimal(item["tax_deduction"])),
                item["ep_category"],
                float(to_decimal(item["timing_difference"])),
                item["ep_rule"],
            ], alternate=(row % 2 == 0))
            for col in [2, 3, 4, 5, 6, 8]:
                format_currency_cell(ws.cell(row=row, column=col))
            row += 1

        row += 1
        ws.cell(row=row, column=1, value="Total Timing Difference").font = FONT_BODY_BOLD
        c = ws.cell(row=row, column=8, value=float(self._r["economic_performance"]["total_timing_difference"]))
        format_currency_cell(c)
        c.font = FONT_BODY_BOLD

        auto_fit_columns(ws)

    # ------------------------------------------------------------------
    def _create_compensation(self):
        ws = self._wb.create_sheet("Compensation & Benefits")
        apply_title(ws, 1, 1, 5, "Compensation Analysis")
        row = 3

        comp = self._r["compensation"]
        lines = [
            ("Total Book Compensation", comp["total_book_compensation"]),
            ("Tax Compensation Deducted", comp["tax_compensation_deducted"]),
            ("Total Book-Tax Difference", comp["book_tax_difference"]),
            ("§162(m) Permanent Disallowance", comp["permanent_component"]),
            ("Timing Component (deferred comp, etc.)", comp["timing_component"]),
        ]
        for label, val in lines:
            ws.cell(row=row, column=1, value=label).font = FONT_BODY_BOLD
            c = ws.cell(row=row, column=2, value=float(to_decimal(val)))
            format_currency_cell(c)
            ws.cell(row=row, column=1).border = THIN_BORDER
            c.border = THIN_BORDER
            row += 1

        if comp["accounts"]:
            row += 1
            apply_section_header(ws, row, 1, 5, "Compensation GL Accounts")
            row += 1
            headers = ["Account #", "Account Name", "Amount"]
            for i, h in enumerate(headers, 1):
                ws.cell(row=row, column=i, value=h)
            apply_header_row(ws, row, 1, len(headers))
            row += 1
            for acct in comp["accounts"]:
                write_data_row(ws, row, [
                    acct["number"], acct["name"], float(to_decimal(acct["amount"])),
                ], alternate=(row % 2 == 0))
                format_currency_cell(ws.cell(row=row, column=3))
                row += 1

        auto_fit_columns(ws)

    # ------------------------------------------------------------------
    def _create_m1_adjustments(self):
        ws = self._wb.create_sheet("M-1 M-3 Adjustments")
        apply_title(ws, 1, 1, 7, "Schedule M-1/M-3 Adjustments")
        row = 3

        headers = ["Description", "Adjustment", "Type", "IRC Section", "Source"]
        for i, h in enumerate(headers, 1):
            ws.cell(row=row, column=i, value=h)
        apply_header_row(ws, row, 1, len(headers))
        row += 1

        m1 = self._r["m1_adjustments"]
        for adj in m1["adjustments"]:
            write_data_row(ws, row, [
                adj["description"],
                float(to_decimal(adj["adjustment"])),
                adj["type"].capitalize(),
                adj["irc_section"],
                adj["source"],
            ], alternate=(row % 2 == 0))
            format_currency_cell(ws.cell(row=row, column=2))
            row += 1

        row += 1
        for label, val in [("Total Temporary", m1["total_temporary"]),
                           ("Total Permanent", m1["total_permanent"]),
                           ("Grand Total", m1["total_adjustments"])]:
            ws.cell(row=row, column=1, value=label).font = FONT_BODY_BOLD
            c = ws.cell(row=row, column=2, value=float(to_decimal(val)))
            format_currency_cell(c)
            c.font = FONT_BODY_BOLD
            row += 1

        row += 1
        ws.cell(row=row, column=1, value="DTA Impact").font = FONT_BODY_BOLD
        c = ws.cell(row=row, column=2, value=float(m1["dta_impact"]))
        format_currency_cell(c)
        row += 1
        ws.cell(row=row, column=1, value="DTL Impact").font = FONT_BODY_BOLD
        c = ws.cell(row=row, column=2, value=float(m1["dtl_impact"]))
        format_currency_cell(c)

        auto_fit_columns(ws)

    # ------------------------------------------------------------------
    def _create_findings(self):
        ws = self._wb.create_sheet("Detailed Findings")
        apply_title(ws, 1, 1, 7, "Phase 2 Detailed Findings")
        row = 3

        headers = ["Area", "Description", "Book-Tax Diff", "Type",
                    "IRC Section", "Risk", "Recommendation"]
        for i, h in enumerate(headers, 1):
            ws.cell(row=row, column=i, value=h)
        apply_header_row(ws, row, 1, len(headers))
        row += 1

        for f in self._r["findings"]:
            write_data_row(ws, row, [
                f["area"], f["description"],
                float(to_decimal(f["book_tax_difference"])),
                f["type"], f["irc_section"],
                f["risk_level"].upper(), f["recommendation"],
            ], alternate=(row % 2 == 0))
            format_currency_cell(ws.cell(row=row, column=3))
            ws.cell(row=row, column=6).font = get_risk_font(f["risk_level"])
            row += 1

        auto_fit_columns(ws)

    # ------------------------------------------------------------------
    def _create_phase3_roadmap(self):
        ws = self._wb.create_sheet("Phase 3 Roadmap")
        apply_title(ws, 1, 1, 4, "Phase 3 Recommendations")
        row = 3

        headers = ["Priority", "Area", "Description", "Data Needed"]
        for i, h in enumerate(headers, 1):
            ws.cell(row=row, column=i, value=h)
        apply_header_row(ws, row, 1, len(headers))
        row += 1

        for item in self._r["phase3_roadmap"]:
            write_data_row(ws, row, [
                item["priority"], item["area"],
                item["description"], item["data_needed"],
            ], alternate=(row % 2 == 0))
            row += 1

        auto_fit_columns(ws)
