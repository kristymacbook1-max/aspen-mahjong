"""Technical Authority Excel Report for Expense Recognition.

Produces a 5-tab workbook:
  1. Executive Summary
  2. Technical Positions
  3. Authority Analysis
  4. Technical Memo (print-friendly)
  5. Filing Requirements
"""

import os
import sys
from decimal import Decimal
from openpyxl import Workbook

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from revenue_recognition.utils.excel_styles import (
    FONT_TITLE, FONT_SECTION_HEADER, FONT_COLUMN_HEADER, FONT_BODY,
    FONT_BODY_BOLD, FILL_SECTION, FILL_ALT_ROW, FILL_HIGHLIGHT_BLUE,
    FILL_HIGHLIGHT_GREEN, FILL_HIGHLIGHT_RED, FILL_HIGHLIGHT_ORANGE,
    THIN_BORDER, ALIGN_CENTER, ALIGN_LEFT, ALIGN_RIGHT, ALIGN_WRAP,
    FMT_CURRENCY, apply_header_row, apply_section_header, apply_title,
    auto_fit_columns, write_data_row, format_currency_cell,
    get_risk_font, get_risk_fill,
)
from revenue_recognition.utils.currency_helpers import to_decimal, format_currency

from .position_analyzer import TechnicalMemo, TaxPosition


class TechnicalAuthorityReport:
    """Generates the Technical Authority Excel workbook for expense recognition."""

    def generate(self, memo: TechnicalMemo, output_path: str) -> str:
        self._memo = memo
        self._wb = Workbook()
        self._wb.remove(self._wb.active)

        self._create_executive_summary()
        self._create_positions()
        self._create_authority_analysis()
        self._create_technical_memo()
        self._create_filing_requirements()

        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        self._wb.save(output_path)
        return output_path

    # ------------------------------------------------------------------
    def _create_executive_summary(self):
        ws = self._wb.create_sheet("Executive Summary")
        apply_title(ws, 1, 1, 5, f"Technical Authority Report — {self._memo.company_name}")
        row = 3

        ws.cell(row=row, column=1, value="Prepared By:").font = FONT_BODY_BOLD
        ws.cell(row=row, column=2, value=self._memo.prepared_by).font = FONT_BODY
        row += 1
        ws.cell(row=row, column=1, value="Date:").font = FONT_BODY_BOLD
        ws.cell(row=row, column=2, value=self._memo.date).font = FONT_BODY
        row += 1
        ws.cell(row=row, column=1, value="Overall Confidence:").font = FONT_BODY_BOLD
        ws.cell(row=row, column=2, value=self._memo.overall_confidence.replace("_", " ").title()).font = FONT_BODY
        row += 1
        ws.cell(row=row, column=1, value="Positions Analyzed:").font = FONT_BODY_BOLD
        ws.cell(row=row, column=2, value=len(self._memo.positions)).font = FONT_BODY
        row += 2

        apply_section_header(ws, row, 1, 5, "Executive Summary")
        row += 1
        ws.cell(row=row, column=1, value=self._memo.executive_summary).font = FONT_BODY
        ws.cell(row=row, column=1).alignment = ALIGN_WRAP
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
        row += 2

        apply_section_header(ws, row, 1, 5, "Position Overview")
        row += 1
        headers = ["Position", "IRC Section", "Amount", "Confidence", "Risk"]
        for i, h in enumerate(headers, 1):
            ws.cell(row=row, column=i, value=h)
        apply_header_row(ws, row, 1, len(headers))
        row += 1

        for pos in self._memo.positions:
            write_data_row(ws, row, [
                pos.title, pos.irc_section,
                pos.amount,
                pos.confidence_level.replace("_", " ").title(),
                pos.risk_level.upper(),
            ], alternate=(row % 2 == 0))
            format_currency_cell(ws.cell(row=row, column=3))
            ws.cell(row=row, column=5).font = get_risk_font(pos.risk_level)
            row += 1

        auto_fit_columns(ws)

    # ------------------------------------------------------------------
    def _create_positions(self):
        ws = self._wb.create_sheet("Technical Positions")
        apply_title(ws, 1, 1, 6, "Detailed Tax Position Analysis")
        row = 3

        for pos in self._memo.positions:
            apply_section_header(ws, row, 1, 6, f"{pos.position_id}: {pos.title}")
            row += 1

            details = [
                ("IRC Section", pos.irc_section),
                ("Amount", format_currency(pos.amount)),
                ("Confidence Level", pos.confidence_level.replace("_", " ").title()),
                ("Risk Level", pos.risk_level.upper()),
                ("Position Type", pos.position_type.replace("_", " ").title()),
            ]
            for label, val in details:
                ws.cell(row=row, column=1, value=label).font = FONT_BODY_BOLD
                ws.cell(row=row, column=2, value=val).font = FONT_BODY
                row += 1

            ws.cell(row=row, column=1, value="Analysis").font = FONT_BODY_BOLD
            row += 1
            ws.cell(row=row, column=1, value=pos.analysis).font = FONT_BODY
            ws.cell(row=row, column=1).alignment = ALIGN_WRAP
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
            row += 1

            ws.cell(row=row, column=1, value="Recommendation").font = FONT_BODY_BOLD
            ws.cell(row=row, column=2, value=pos.recommendation).font = FONT_BODY
            row += 2

        auto_fit_columns(ws)

    # ------------------------------------------------------------------
    def _create_authority_analysis(self):
        ws = self._wb.create_sheet("Authority Analysis")
        apply_title(ws, 1, 1, 7, "Supporting & Adverse Authorities")
        row = 3

        for pos in self._memo.positions:
            apply_section_header(ws, row, 1, 7, pos.title)
            row += 1

            # Supporting
            ws.cell(row=row, column=1, value="SUPPORTING AUTHORITIES").font = FONT_BODY_BOLD
            ws.cell(row=row, column=1).fill = FILL_HIGHLIGHT_GREEN
            row += 1

            if pos.supporting_authorities:
                headers = ["Citation", "Type", "Year", "Weight", "Key Holding"]
                for i, h in enumerate(headers, 1):
                    ws.cell(row=row, column=i, value=h)
                apply_header_row(ws, row, 1, len(headers))
                row += 1

                for auth in pos.supporting_authorities[:8]:
                    write_data_row(ws, row, [
                        auth.citation, auth.authority_type, auth.year,
                        auth.weight, auth.key_holding[:120] + "..." if len(auth.key_holding) > 120 else auth.key_holding,
                    ], alternate=(row % 2 == 0))
                    row += 1
            else:
                ws.cell(row=row, column=1, value="None identified").font = FONT_BODY
                row += 1

            row += 1
            # Adverse
            ws.cell(row=row, column=1, value="ADVERSE AUTHORITIES").font = FONT_BODY_BOLD
            ws.cell(row=row, column=1).fill = FILL_HIGHLIGHT_RED
            row += 1

            if pos.adverse_authorities:
                headers = ["Citation", "Type", "Year", "Weight", "Key Holding"]
                for i, h in enumerate(headers, 1):
                    ws.cell(row=row, column=i, value=h)
                apply_header_row(ws, row, 1, len(headers))
                row += 1

                for auth in pos.adverse_authorities[:8]:
                    write_data_row(ws, row, [
                        auth.citation, auth.authority_type, auth.year,
                        auth.weight, auth.key_holding[:120] + "..." if len(auth.key_holding) > 120 else auth.key_holding,
                    ], alternate=(row % 2 == 0))
                    row += 1
            else:
                ws.cell(row=row, column=1, value="None identified").font = FONT_BODY
                row += 1

            row += 2

        auto_fit_columns(ws)

    # ------------------------------------------------------------------
    def _create_technical_memo(self):
        ws = self._wb.create_sheet("Technical Memo")
        apply_title(ws, 1, 1, 1, "TECHNICAL MEMORANDUM")
        row = 3

        # Header block
        header_lines = [
            f"TO: Tax File — {self._memo.company_name}",
            f"FROM: {self._memo.prepared_by}",
            f"DATE: {self._memo.date}",
            f"RE: Expense Recognition Tax Position Analysis",
        ]
        for line in header_lines:
            ws.cell(row=row, column=1, value=line).font = FONT_BODY_BOLD
            row += 1
        row += 1

        # Summary
        ws.cell(row=row, column=1, value="I. EXECUTIVE SUMMARY").font = FONT_BODY_BOLD
        row += 1
        ws.cell(row=row, column=1, value=self._memo.executive_summary).font = FONT_BODY
        ws.cell(row=row, column=1).alignment = ALIGN_WRAP
        row += 2

        # Each position
        for i, pos in enumerate(self._memo.positions, 1):
            ws.cell(row=row, column=1, value=f"II.{i}. {pos.title}").font = FONT_BODY_BOLD
            row += 1

            ws.cell(row=row, column=1, value="Issue:").font = FONT_BODY_BOLD
            row += 1
            ws.cell(row=row, column=1, value=pos.description).font = FONT_BODY
            row += 1

            ws.cell(row=row, column=1, value="Analysis:").font = FONT_BODY_BOLD
            row += 1
            ws.cell(row=row, column=1, value=pos.analysis).font = FONT_BODY
            ws.cell(row=row, column=1).alignment = ALIGN_WRAP
            row += 1

            ws.cell(row=row, column=1, value="Authorities:").font = FONT_BODY_BOLD
            row += 1
            for auth in (pos.supporting_authorities + pos.adverse_authorities)[:6]:
                prefix = "[Supporting]" if auth.taxpayer_favorable else "[Adverse]"
                ws.cell(row=row, column=1, value=f"  {prefix} {auth.citation}: {auth.key_holding[:100]}").font = FONT_BODY
                ws.cell(row=row, column=1).alignment = ALIGN_WRAP
                row += 1

            ws.cell(row=row, column=1, value=f"Conclusion: {pos.confidence_level.replace('_', ' ').title()} — {pos.recommendation}").font = FONT_BODY_BOLD
            row += 2

        # Set column width for readability
        ws.column_dimensions['A'].width = 100

    # ------------------------------------------------------------------
    def _create_filing_requirements(self):
        ws = self._wb.create_sheet("Filing Requirements")
        apply_title(ws, 1, 1, 5, "Filing Requirements & Method Changes")
        row = 3

        headers = ["Position", "Form Required", "Method Change?", "§481(a)?", "Deadline"]
        for i, h in enumerate(headers, 1):
            ws.cell(row=row, column=i, value=h)
        apply_header_row(ws, row, 1, len(headers))
        row += 1

        for pos in self._memo.positions:
            form = ""
            method_change = "No"
            s481a = "No"
            deadline = "With timely filed return"

            if pos.position_type == "economic_performance":
                form = "Form 3115 (if changing method)"
                method_change = "Possibly"
                s481a = "Yes (if method change)"
            elif pos.position_type == "prepaid":
                form = "Form 3115 (if changing treatment)"
                method_change = "Possibly"
                s481a = "Yes (if method change)"
            elif pos.position_type == "compensation":
                form = "Schedule M-1/M-3 adjustment"
                method_change = "No"
            elif pos.position_type == "interest":
                form = "Form 8990"
                method_change = "No"
            elif pos.position_type == "rd":
                form = "Form 3115 (if first year)"
                method_change = "Yes (first year implementing)"
                s481a = "Yes"
            elif pos.position_type == "related_party":
                form = "Schedule M-1/M-3 adjustment"
                method_change = "No"

            write_data_row(ws, row, [
                pos.title, form, method_change, s481a, deadline,
            ], alternate=(row % 2 == 0))
            row += 1

        auto_fit_columns(ws)
