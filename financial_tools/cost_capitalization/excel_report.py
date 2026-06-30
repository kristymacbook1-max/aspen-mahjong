"""Cost Capitalization Excel Report Generator.

Produces an 11-tab workbook that prepares §266 / §263(a) / §263A cost
capitalization schedules from a department / cost-center based trial balance.
The workbook is built with LIVE in-cell formulas (SUMIF/SUMIFS, allocation
math, absorption ratio) so it doubles as a reusable annual template: edit a
trial-balance amount or an allocation percentage and every schedule recomputes.

Tabs:
  1. Instructions / Control
  2. Trial Balance (input + live capitalization helper columns)
  3. Cost Center Allocation (input + checksum)
  4. §266 Carrying Charges
  5. §263(a) Capitalization
  6. §263A UNICAP (absorption ratio + §263A(f) interest)
  7. Other Capitalization (§174A / §197 / §195 / IDC / §263(g) / §461(g))
  8. Capitalization Summary
  9. Reconciliation (account-tag vs allocation-overlay)
 10. Book-Tax / M-1 & Journal Entries
 11. IRS Practice Units (§263A examiner guidance)
 12. Authorities
"""

import os
import sys

from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from revenue_recognition.utils.excel_styles import (
    FONT_BODY, FONT_BODY_BOLD, FONT_COLUMN_HEADER, FILL_HIGHLIGHT_BLUE,
    FILL_HIGHLIGHT_GREEN, FILL_HIGHLIGHT_ORANGE, FILL_HIGHLIGHT_RED,
    THIN_BORDER, ALIGN_LEFT, ALIGN_RIGHT, ALIGN_CENTER,
    FMT_CURRENCY, FMT_PERCENT,
    apply_title, apply_section_header, apply_header_row, auto_fit_columns,
)
from authority_databases.cost_capitalization import COST_CAP_LOOKUP, PRACTICE_UNITS_263A
from cost_capitalization.analyzer import (
    PROV_DEDUCTIBLE, PROV_266, PROV_263A_ACQ, PROV_263A, PROV_MIXED, PROV_OTHER,
)

# Trial Balance sheet name and the helper-column layout used by formulas
TB_SHEET = "Trial Balance"
ALLOC_SHEET = "Cost Center Allocation"
TB_FIRST_DATA_ROW = 4
MIN_TEMPLATE_ROWS = 20  # blank input rows when run as an empty template


class CostCapitalizationReport:
    """Generates the cost capitalization workbook."""

    def generate(self, results: dict, output_path: str) -> str:
        self._r = results
        self._inp = results["_input"]
        self._wb = Workbook()
        self._wb.remove(self._wb.active)

        # Number of trial-balance rows (reserve template rows if empty)
        self._n_rows = max(len(self._inp.trial_balance), MIN_TEMPLATE_ROWS)
        self._tb_last_row = TB_FIRST_DATA_ROW + self._n_rows - 1

        self._create_instructions()
        self._create_trial_balance()
        self._create_allocation()
        self._create_266()
        self._create_263a()
        self._create_unicap()
        self._create_other_cap()
        self._create_summary()
        self._create_reconciliation()
        self._create_booktax()
        self._create_practice_units()
        self._create_authorities()

        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        self._wb.save(output_path)
        return output_path

    # ------------------------------------------------------------------
    # Small styling helpers
    # ------------------------------------------------------------------
    def _label(self, ws, row, col, text, bold=False):
        c = ws.cell(row=row, column=col, value=text)
        c.font = FONT_BODY_BOLD if bold else FONT_BODY
        c.alignment = ALIGN_LEFT
        return c

    def _money(self, ws, row, col, value):
        c = ws.cell(row=row, column=col, value=value)
        c.number_format = FMT_CURRENCY
        c.font = FONT_BODY
        c.alignment = ALIGN_RIGHT
        c.border = THIN_BORDER
        return c

    def _pct(self, ws, row, col, value):
        c = ws.cell(row=row, column=col, value=value)
        c.number_format = FMT_PERCENT
        c.font = FONT_BODY
        c.alignment = ALIGN_RIGHT
        c.border = THIN_BORDER
        return c

    def _headers(self, ws, row, labels, start_col=1):
        for i, lab in enumerate(labels):
            ws.cell(row=row, column=start_col + i, value=lab)
        apply_header_row(ws, row, start_col, start_col + len(labels) - 1)

    # ------------------------------------------------------------------
    # 1. Instructions / Control
    # ------------------------------------------------------------------
    def _create_instructions(self):
        ws = self._wb.create_sheet("Instructions")
        apply_title(ws, 1, 1, 6,
                    f"Cost Capitalization Workpaper — {self._r['company_name']} "
                    f"(TY {self._r['tax_year']})")
        row = 3
        apply_section_header(ws, row, 1, 6, "Entity & Method")
        row += 1
        facts = [
            ("Entity type", self._r["entity_type"]),
            ("Tax year", self._r["tax_year"]),
            ("§263A method", self._inp.section_263a.method),
            ("§448(c) gross receipts (3-yr avg)",
             f"${self._inp.small_business.avg_annual_gross_receipts:,.0f}"),
            ("§448(c) threshold",
             f"${self._inp.small_business.threshold:,.0f}"),
            ("Small-business UNICAP exemption (§263A(i)/§471(c))",
             "YES — UNICAP not required" if self._r["small_business_exempt"] else "No"),
            ("De minimis safe harbor ceiling (§1.263(a)-1(f))",
             f"${self._inp.section_263a_elections.de_minimis_ceiling:,.0f} "
             f"({'AFS' if self._inp.section_263a_elections.has_afs else 'non-AFS'})"),
        ]
        for label, val in facts:
            self._label(ws, row, 1, label, bold=True)
            self._label(ws, row, 3, str(val))
            row += 1

        row += 1
        apply_section_header(ws, row, 1, 6, "How to use this workbook")
        row += 1
        steps = [
            "1. Enter the department/cost-center trial balance on the 'Trial Balance' tab.",
            "   Tag each account in the Provision column: deductible, 266, 263(a), 263A, mixed, other_cap.",
            "   For 'other_cap' rows, enter the section (e.g. 174A, 197, 195) in the Other Cap § column.",
            "2. For 'mixed' accounts, set the cost center's allocation % on the 'Cost Center Allocation' tab.",
            "   The checksum column flags any cost center whose percentages do not total 100%.",
            "3. The §266, §263(a), §263A, Other Capitalization, Summary and Reconciliation tabs are",
            "   driven by LIVE formulas — they recompute automatically when you edit inputs.",
            "4. Enter the §263A UNICAP inputs on the '§263A UNICAP' tab to compute the absorption ratio.",
            "5. Review the Reconciliation tab: account-level tagging vs cost-center allocation overlay.",
            "6. Authorities tab cites the governing statute/regulation for each provision.",
        ]
        for s in steps:
            self._label(ws, row, 1, s)
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
            row += 1

        row += 1
        apply_section_header(ws, row, 1, 6, "Color legend")
        row += 1
        legend = [
            (FILL_HIGHLIGHT_BLUE, "Input header / column to fill in"),
            (FILL_HIGHLIGHT_GREEN, "Computed capitalization (live formula)"),
            (FILL_HIGHLIGHT_ORANGE, "Review / attention"),
            (FILL_HIGHLIGHT_RED, "Error — allocation does not total 100% / variance"),
        ]
        for fill, text in legend:
            c = ws.cell(row=row, column=1, value="")
            c.fill = fill
            c.border = THIN_BORDER
            self._label(ws, row, 2, text)
            row += 1

        auto_fit_columns(ws, max_width=70)

    # ------------------------------------------------------------------
    # 2. Trial Balance (input + helper formula columns)
    # ------------------------------------------------------------------
    def _create_trial_balance(self):
        ws = self._wb.create_sheet(TB_SHEET)
        apply_title(ws, 1, 1, 12, f"Department / Cost-Center Trial Balance — {self._r['company_name']}")
        self._headers(ws, 3, [
            "Account #", "Account Name", "Cost Center", "Book Category",
            "Provision", "Amount", "Other Cap §",
            "Cap §266", "Cap §263(a)", "Cap §263A", "Other Cap", "Deductible",
        ])

        # Data validation drop-down for the Provision column (E)
        dv = DataValidation(
            type="list",
            formula1='"deductible,266,263(a),263A,mixed,other_cap"',
            allow_blank=True,
        )
        ws.add_data_validation(dv)

        lines = self._inp.trial_balance
        for i in range(self._n_rows):
            r = TB_FIRST_DATA_ROW + i
            line = lines[i] if i < len(lines) else None
            if line:
                self._label(ws, r, 1, line.account_number)
                self._label(ws, r, 2, line.account_name)
                self._label(ws, r, 3, line.cost_center_code)
                self._label(ws, r, 4, line.book_category)
                self._label(ws, r, 5, line.provision)
                self._money(ws, r, 6, float(line.amount))
                self._label(ws, r, 7, line.other_cap_section)
            else:
                for col in range(1, 8):
                    ws.cell(row=r, column=col).border = THIN_BORDER
                self._money(ws, r, 6, None)
            dv.add(ws.cell(row=r, column=5))

            # Live capitalization helper formulas (H..L)
            alloc = f"'{ALLOC_SHEET}'"
            # Allocation cells store percentages as fractions (0.80 = 80%), so the
            # mixed-cost split multiplies by the looked-up fraction directly.
            ws.cell(row=r, column=8,  # Cap §266
                    value=(f'=IF($E{r}="{PROV_266}",$F{r},'
                           f'IF($E{r}="{PROV_MIXED}",$F{r}*IFERROR(VLOOKUP($C{r},{alloc}!$A:$F,3,FALSE),0),0))'))
            ws.cell(row=r, column=9,  # Cap §263(a)
                    value=(f'=IF($E{r}="{PROV_263A_ACQ}",$F{r},'
                           f'IF($E{r}="{PROV_MIXED}",$F{r}*IFERROR(VLOOKUP($C{r},{alloc}!$A:$F,4,FALSE),0),0))'))
            ws.cell(row=r, column=10,  # Cap §263A
                    value=(f'=IF($E{r}="{PROV_263A}",$F{r},'
                           f'IF($E{r}="{PROV_MIXED}",$F{r}*IFERROR(VLOOKUP($C{r},{alloc}!$A:$F,5,FALSE),0),0))'))
            ws.cell(row=r, column=11,  # Other Cap
                    value=f'=IF($E{r}="{PROV_OTHER}",$F{r},0)')
            ws.cell(row=r, column=12,  # Deductible
                    value=(f'=IF($E{r}="{PROV_DEDUCTIBLE}",$F{r},'
                           f'IF($E{r}="{PROV_MIXED}",$F{r}*IFERROR(VLOOKUP($C{r},{alloc}!$A:$F,6,FALSE),0),0))'))
            for col in range(8, 13):
                cc = ws.cell(row=r, column=col)
                cc.number_format = FMT_CURRENCY
                cc.alignment = ALIGN_RIGHT
                cc.border = THIN_BORDER
                cc.fill = FILL_HIGHLIGHT_GREEN

        # Total row
        tr = self._tb_last_row + 1
        self._label(ws, tr, 1, "TOTAL", bold=True)
        for col in range(6, 13):
            cl = ws.cell(row=tr, column=col).column_letter
            c = ws.cell(row=tr, column=col,
                        value=f"=SUM({cl}{TB_FIRST_DATA_ROW}:{cl}{self._tb_last_row})")
            c.number_format = FMT_CURRENCY
            c.font = FONT_BODY_BOLD
            c.alignment = ALIGN_RIGHT
            c.border = THIN_BORDER
        auto_fit_columns(ws, max_width=28)

    # ------------------------------------------------------------------
    # 3. Cost Center Allocation
    # ------------------------------------------------------------------
    def _create_allocation(self):
        ws = self._wb.create_sheet(ALLOC_SHEET)
        apply_title(ws, 1, 1, 7, "Cost Center Allocation — split mixed spend across provisions")
        self._headers(ws, 3, [
            "Cost Center", "Name", "% §266", "% §263(a)", "% §263A", "% Deductible", "Checksum",
        ])
        cc_names = {c.code: c.name for c in self._inp.cost_centers}
        overlays = self._inp.allocations
        n = max(len(overlays), len(self._inp.cost_centers), 10)
        for i in range(n):
            r = 4 + i
            ov = overlays[i] if i < len(overlays) else None
            if ov:
                self._label(ws, r, 1, ov.cost_center_code)
                self._label(ws, r, 2, cc_names.get(ov.cost_center_code, ""))
                self._pct(ws, r, 3, float(ov.pct_266) / 100)
                self._pct(ws, r, 4, float(ov.pct_263a_acq) / 100)
                self._pct(ws, r, 5, float(ov.pct_263A) / 100)
                self._pct(ws, r, 6, float(ov.pct_deductible) / 100)
            else:
                for col in (1, 2):
                    ws.cell(row=r, column=col).border = THIN_BORDER
                for col in range(3, 7):
                    c = ws.cell(row=r, column=col)
                    c.number_format = FMT_PERCENT
                    c.border = THIN_BORDER
                    c.fill = FILL_HIGHLIGHT_BLUE
            # Checksum = sum of the four percentages
            chk = ws.cell(row=r, column=7, value=f"=SUM(C{r}:F{r})")
            chk.number_format = FMT_PERCENT
            chk.alignment = ALIGN_RIGHT
            chk.border = THIN_BORDER

        # Conditional flag: checksum not 100% and not 0% -> red
        from openpyxl.formatting.rule import CellIsRule
        red = FILL_HIGHLIGHT_RED
        rng = f"G4:G{4 + n - 1}"
        ws.conditional_formatting.add(
            rng, CellIsRule(operator="between", formula=["0.0001", "0.9999"], fill=red))
        ws.conditional_formatting.add(
            rng, CellIsRule(operator="greaterThan", formula=["1.0001"], fill=red))
        self._label(ws, 4 + n + 1, 1,
                    "Checksum must equal 100% (or 0% if the cost center has no mixed spend).")
        auto_fit_columns(ws, max_width=24)

    # ------------------------------------------------------------------
    # Shared: by-cost-center rollup block driven by SUMIF on a TB helper col
    # ------------------------------------------------------------------
    def _cc_rollup(self, ws, start_row, tb_col_letter):
        """Write a 'by cost center' table summing a TB helper column via SUMIF."""
        self._headers(ws, start_row, ["Cost Center", "Name", "Capitalized"])
        r = start_row + 1
        centers = self._inp.cost_centers or []
        # fall back to distinct codes on the TB if no cost_centers provided
        if not centers:
            seen = []
            for line in self._inp.trial_balance:
                if line.cost_center_code not in [c for c in seen]:
                    seen.append(line.cost_center_code)
            codes = seen
        else:
            codes = [c.code for c in centers]
        names = {c.code: c.name for c in centers}
        for code in codes:
            self._label(ws, r, 1, code)
            self._label(ws, r, 2, names.get(code, ""))
            c = ws.cell(row=r, column=3,
                        value=(f"=SUMIF('{TB_SHEET}'!$C${TB_FIRST_DATA_ROW}:$C${self._tb_last_row},"
                               f"$A{r},'{TB_SHEET}'!${tb_col_letter}${TB_FIRST_DATA_ROW}:"
                               f"${tb_col_letter}${self._tb_last_row})"))
            c.number_format = FMT_CURRENCY
            c.alignment = ALIGN_RIGHT
            c.border = THIN_BORDER
            r += 1
        # total
        self._label(ws, r, 1, "TOTAL", bold=True)
        c = ws.cell(row=r, column=3, value=f"=SUM(C{start_row + 1}:C{r - 1})")
        c.number_format = FMT_CURRENCY
        c.font = FONT_BODY_BOLD
        c.alignment = ALIGN_RIGHT
        c.border = THIN_BORDER
        return r

    def _tb_total(self, col_letter):
        return (f"=SUM('{TB_SHEET}'!{col_letter}{TB_FIRST_DATA_ROW}:"
                f"{col_letter}{self._tb_last_row})")

    # ------------------------------------------------------------------
    # 4. §266 Carrying Charges
    # ------------------------------------------------------------------
    def _create_266(self):
        ws = self._wb.create_sheet("§266 Carrying Charges")
        apply_title(ws, 1, 1, 4, "§266 — Elective Capitalization of Carrying Charges")
        row = 3
        apply_section_header(ws, row, 1, 4, "Total capitalized under §266 (live)")
        row += 1
        self._label(ws, row, 1, "Total §266 carrying charges capitalized", bold=True)
        c = self._money(ws, row, 3, None)
        c.value = self._tb_total("H")
        c.font = FONT_BODY_BOLD
        c.fill = FILL_HIGHLIGHT_GREEN
        row += 2

        apply_section_header(ws, row, 1, 4, "Elections in effect (Reg §1.266-1)")
        row += 1
        el = self._inp.section_266
        for label, on, cite in [
            ("Unimproved/unproductive real property (annual election)",
             el.unimproved_real_property, "§1.266-1(b)(1)(i)"),
            ("Real property in development/construction (project election)",
             el.development_real_property, "§1.266-1(b)(1)(ii)"),
            ("Personal property (to install / first use)",
             el.personal_property, "§1.266-1(b)(1)(iii)"),
            ("Commissioner catch-all (sound accounting)",
             el.commissioner_catchall, "§1.266-1(b)(1)(iv)/(b)(2)"),
        ]:
            self._label(ws, row, 1, label)
            self._label(ws, row, 3, "ELECTED" if on else "—", bold=on)
            self._label(ws, row, 4, cite)
            row += 1
        row += 1
        self._label(ws, row, 1,
                    "Ordering: §263A applies first (mandatory); §266 is a residual election only if "
                    "no material distortion. Election by statement on the original return; no IRS consent.")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        row += 2
        self._cc_rollup(ws, row, "H")
        auto_fit_columns(ws, max_width=60)

    # ------------------------------------------------------------------
    # 5. §263(a) Capitalization
    # ------------------------------------------------------------------
    def _create_263a(self):
        ws = self._wb.create_sheet("§263(a) Capitalization")
        apply_title(ws, 1, 1, 4, "§263(a) — Acquisition & Improvement Capitalization")
        row = 3
        apply_section_header(ws, row, 1, 4, "Total capitalized under §263(a) (live)")
        row += 1
        self._label(ws, row, 1, "Total §263(a) costs capitalized", bold=True)
        c = self._money(ws, row, 3, None)
        c.value = self._tb_total("I")
        c.font = FONT_BODY_BOLD
        c.fill = FILL_HIGHLIGHT_GREEN
        row += 2

        apply_section_header(ws, row, 1, 4, "Safe harbors & elections")
        row += 1
        el = self._inp.section_263a_elections
        rows = [
            ("De minimis safe harbor (§1.263(a)-1(f))",
             "ELECTED" if el.de_minimis_safe_harbor else "—",
             f"Ceiling ${el.de_minimis_ceiling:,.0f} ({'AFS' if el.has_afs else 'non-AFS'}); not indexed"),
            ("Small taxpayer safe harbor (§1.263(a)-3(h))",
             "ELECTED" if el.small_taxpayer_safe_harbor else "—",
             "GR <= $10M; building basis <= $1M; spend <= lesser of $10k or 2%"),
            ("Routine maintenance safe harbor (§1.263(a)-3(i))",
             "APPLIED" if el.routine_maintenance else "—",
             ">1x in 10 yrs (buildings) / ADS class life"),
            ("Capitalize repairs election (§1.263(a)-3(n))",
             "ELECTED" if el.capitalize_repairs_election else "—",
             "Annual irrevocable; book conformity"),
            ("Success-fee 70% safe harbor (Rev. Proc. 2011-29)",
             "ELECTED" if el.success_fee_70_safe_harbor else "—",
             "70% deductible / 30% capitalized on success-based fees"),
        ]
        self._headers(ws, row, ["Provision", "Status", "Key parameter"])
        row += 1
        for prov, status, param in rows:
            self._label(ws, row, 1, prov)
            self._label(ws, row, 2, status, bold=(status != "—"))
            self._label(ws, row, 3, param)
            row += 1
        row += 1
        self._label(ws, row, 1,
                    "Improvement test: capitalize Betterments, Restorations, Adaptations (BRA), "
                    "measured against the unit of property / nine building systems.")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        row += 2
        self._cc_rollup(ws, row, "I")
        auto_fit_columns(ws, max_width=60)

    # ------------------------------------------------------------------
    # 6. §263A UNICAP
    # ------------------------------------------------------------------
    def _create_unicap(self):
        ws = self._wb.create_sheet("§263A UNICAP")
        apply_title(ws, 1, 1, 4, "§263A — Uniform Capitalization (UNICAP)")
        row = 3
        s = self._inp.section_263a
        sb = self._inp.small_business

        apply_section_header(ws, row, 1, 4, "Small-business exception (§263A(i) / §448(c))")
        row += 1
        self._label(ws, row, 1, "3-yr avg gross receipts")
        self._money(ws, row, 3, float(sb.avg_annual_gross_receipts))
        row += 1
        self._label(ws, row, 1, f"§448(c) threshold (TY {sb.tax_year})")
        self._money(ws, row, 3, float(sb.threshold))
        row += 1
        self._label(ws, row, 1, "UNICAP required?", bold=True)
        st = "NO — small-business exempt" if sb.exempt else "YES"
        cell = self._label(ws, row, 3, st, bold=True)
        cell.fill = FILL_HIGHLIGHT_ORANGE if sb.exempt else FILL_HIGHLIGHT_GREEN
        row += 2

        apply_section_header(ws, row, 1, 4,
                             f"Absorption ratio — method: {s.method}")
        row += 1
        # Input cells, then live formulas referencing them
        self._label(ws, row, 1, "§471 costs incurred (current year)", bold=True)
        r471 = row
        self._money(ws, row, 3, float(s.section_471_costs)).fill = FILL_HIGHLIGHT_BLUE
        row += 1

        if s.method == "simplified_resale":
            self._label(ws, row, 1, "Storage & handling costs", bold=True)
            r_sh = row
            self._money(ws, row, 3, float(s.storage_handling_costs)).fill = FILL_HIGHLIGHT_BLUE
            row += 1
            self._label(ws, row, 1, "Purchasing costs", bold=True)
            r_pu = row
            self._money(ws, row, 3, float(s.purchasing_costs)).fill = FILL_HIGHLIGHT_BLUE
            row += 1
            self._label(ws, row, 1, "Absorption ratio = (storage+handling+purchasing) / §471", bold=True)
            ratio_row = row
            c = self._pct(ws, row, 3,
                          value=None) if False else ws.cell(row=row, column=3)
            c.value = f"=IFERROR((C{r_sh}+C{r_pu})/C{r471},0)"
            c.number_format = FMT_PERCENT
            c.alignment = ALIGN_RIGHT
            c.border = THIN_BORDER
            c.fill = FILL_HIGHLIGHT_GREEN
            row += 1
        else:
            self._label(ws, row, 1, "Additional §263A costs incurred (current year)", bold=True)
            r_add = row
            self._money(ws, row, 3, float(s.additional_263a_costs)).fill = FILL_HIGHLIGHT_BLUE
            row += 1
            self._label(ws, row, 1, "Absorption ratio = additional §263A / §471 costs", bold=True)
            ratio_row = row
            c = ws.cell(row=row, column=3, value=f"=IFERROR(C{r_add}/C{r471},0)")
            c.number_format = FMT_PERCENT
            c.alignment = ALIGN_RIGHT
            c.border = THIN_BORDER
            c.fill = FILL_HIGHLIGHT_GREEN
            row += 1

        self._label(ws, row, 1, "§471 costs in ending inventory", bold=True)
        r_end = row
        self._money(ws, row, 3, float(s.ending_inventory_471)).fill = FILL_HIGHLIGHT_BLUE
        row += 1
        self._label(ws, row, 1, "Additional §263A costs capitalized to ending inventory", bold=True)
        c = ws.cell(row=row, column=3, value=f"=C{r_end}*C{ratio_row}")
        c.number_format = FMT_CURRENCY
        c.font = FONT_BODY_BOLD
        c.alignment = ALIGN_RIGHT
        c.border = THIN_BORDER
        c.fill = FILL_HIGHLIGHT_GREEN
        row += 2

        apply_section_header(ws, row, 1, 4, "§263A(f) interest capitalization (avoided-cost)")
        row += 1
        self._label(ws, row, 1, "Designated property?")
        self._label(ws, row, 3, "Yes" if s.designated_property else "No")
        row += 1
        self._label(ws, row, 1, "Accumulated production expenditures")
        r_ape = row
        self._money(ws, row, 3, float(s.accumulated_production_expenditures)).fill = FILL_HIGHLIGHT_BLUE
        row += 1
        self._label(ws, row, 1, "Avoided-cost interest rate")
        r_rate = row
        cc = self._pct(ws, row, 3, float(s.avoided_cost_rate))
        cc.fill = FILL_HIGHLIGHT_BLUE
        row += 1
        self._label(ws, row, 1, "Interest capitalized (§263A(f))", bold=True)
        c = ws.cell(row=row, column=3,
                    value=(f"=IF(\"{('Y' if s.designated_property else 'N')}\"=\"Y\","
                           f"C{r_ape}*C{r_rate},0)"))
        c.number_format = FMT_CURRENCY
        c.font = FONT_BODY_BOLD
        c.alignment = ALIGN_RIGHT
        c.border = THIN_BORDER
        c.fill = FILL_HIGHLIGHT_GREEN
        row += 2

        self._label(ws, row, 1,
                    "Current-year operating costs tagged §263A on the trial balance:")
        c = self._money(ws, row, 3, None)
        c.value = self._tb_total("J")
        c.fill = FILL_HIGHLIGHT_GREEN
        auto_fit_columns(ws, max_width=60)

    # ------------------------------------------------------------------
    # 7. Other Capitalization
    # ------------------------------------------------------------------
    def _create_other_cap(self):
        ws = self._wb.create_sheet("Other Capitalization")
        apply_title(ws, 1, 1, 4,
                    "Other Capitalization Regimes (§174A / §197 / §195 / IDC / §263(g) / §461(g))")
        row = 3
        apply_section_header(ws, row, 1, 4, "Total tagged 'other_cap' (live)")
        row += 1
        self._label(ws, row, 1, "Total other capitalization", bold=True)
        c = self._money(ws, row, 3, None)
        c.value = self._tb_total("K")
        c.font = FONT_BODY_BOLD
        c.fill = FILL_HIGHLIGHT_GREEN
        row += 2

        apply_section_header(ws, row, 1, 4, "By section (SUMIFS on Other Cap § tag)")
        row += 1
        self._headers(ws, row, ["Section", "Amount", "Recovery treatment"])
        row += 1
        treatments = {
            "174A": "Domestic R&E — current expensing default; elect cap >= 60 mo. Foreign R&E 15-yr (§174).",
            "174": "Foreign R&E — REQUIRED 15-year amortization.",
            "197": "Acquired intangibles — mandatory 15-year (180-mo) straight-line.",
            "195": "Start-up — $5,000 + 180-mo amortization (phase-out over $50k).",
            "248": "Corporate org — $5,000 + 180-mo amortization.",
            "709": "Partnership org — $5,000 + 180-mo; syndication permanently capitalized.",
            "263(c)": "IDC — expense or §59(e) 60-mo amortization.",
            "263(g)": "Straddle interest/carrying charges — capitalized into basis.",
            "461(g)": "Prepaid interest — spread over loan; points exception for residence.",
        }
        sections = sorted(self._r["other_cap_by_section"].keys()) or list(treatments.keys())
        for sec in sections:
            self._label(ws, row, 1, sec)
            c = ws.cell(row=row, column=2,
                        value=(f"=SUMIFS('{TB_SHEET}'!$K${TB_FIRST_DATA_ROW}:$K${self._tb_last_row},"
                               f"'{TB_SHEET}'!$G${TB_FIRST_DATA_ROW}:$G${self._tb_last_row},$A{row})"))
            c.number_format = FMT_CURRENCY
            c.alignment = ALIGN_RIGHT
            c.border = THIN_BORDER
            self._label(ws, row, 3, treatments.get(sec, ""))
            row += 1
        auto_fit_columns(ws, max_width=70)

    # ------------------------------------------------------------------
    # 8. Capitalization Summary
    # ------------------------------------------------------------------
    def _create_summary(self):
        ws = self._wb.create_sheet("Capitalization Summary")
        apply_title(ws, 1, 1, 4, "Capitalization Summary — by provision")
        row = 3
        self._headers(ws, row, ["Provision", "Capitalized", "Authority"])
        row += 1
        provisions = [
            ("§266 Carrying charges", "H", "IRC §266 / Reg §1.266-1"),
            ("§263(a) Acquisition & improvement", "I", "IRC §263(a) / Reg §1.263(a)-1..-5"),
            ("§263A UNICAP (operating costs tagged)", "J", "IRC §263A / Reg §1.263A-1..-15"),
            ("Other capitalization (§174A/§197/§195…)", "K", "see Other Capitalization tab"),
        ]
        first = row
        for label, col, cite in provisions:
            self._label(ws, row, 1, label, bold=True)
            c = self._money(ws, row, 2, None)
            c.value = self._tb_total(col)
            self._label(ws, row, 3, cite)
            row += 1
        # Total capitalized
        self._label(ws, row, 1, "TOTAL CAPITALIZED", bold=True)
        c = ws.cell(row=row, column=2, value=f"=SUM(B{first}:B{row - 1})")
        c.number_format = FMT_CURRENCY
        c.font = FONT_BODY_BOLD
        c.alignment = ALIGN_RIGHT
        c.border = THIN_BORDER
        c.fill = FILL_HIGHLIGHT_GREEN
        cap_total_row = row
        row += 1
        # Deductible remainder
        self._label(ws, row, 1, "Deductible (remainder)", bold=True)
        c = self._money(ws, row, 2, None)
        c.value = self._tb_total("L")
        row += 1
        # Grand total ties to TB
        self._label(ws, row, 1, "Trial balance grand total (check)", bold=True)
        c = ws.cell(row=row, column=2,
                    value=f"=B{cap_total_row}+B{row - 1}")
        c.number_format = FMT_CURRENCY
        c.font = FONT_BODY_BOLD
        c.alignment = ALIGN_RIGHT
        c.border = THIN_BORDER
        row += 1
        self._label(ws, row, 1, "  (should equal Trial Balance!F total)")
        c = self._money(ws, row, 2, None)
        c.value = self._tb_total("F")
        row += 2

        # By cost center (all capitalization columns H+I+J+K)
        apply_section_header(ws, row, 1, 4, "By cost center (total capitalized H+I+J+K)")
        row += 1
        self._headers(ws, row, ["Cost Center", "Name", "Capitalized"])
        row += 1
        centers = self._inp.cost_centers or []
        codes = [c.code for c in centers] if centers else sorted(
            {l.cost_center_code for l in self._inp.trial_balance})
        names = {c.code: c.name for c in centers}
        block_first = row
        for code in codes:
            self._label(ws, row, 1, code)
            self._label(ws, row, 2, names.get(code, ""))
            parts = []
            for col in ("H", "I", "J", "K"):
                parts.append(
                    f"SUMIF('{TB_SHEET}'!$C${TB_FIRST_DATA_ROW}:$C${self._tb_last_row},"
                    f"$A{row},'{TB_SHEET}'!${col}${TB_FIRST_DATA_ROW}:${col}${self._tb_last_row})")
            c = ws.cell(row=row, column=3, value="=" + "+".join(parts))
            c.number_format = FMT_CURRENCY
            c.alignment = ALIGN_RIGHT
            c.border = THIN_BORDER
            row += 1
        self._label(ws, row, 1, "TOTAL", bold=True)
        c = ws.cell(row=row, column=3, value=f"=SUM(C{block_first}:C{row - 1})")
        c.number_format = FMT_CURRENCY
        c.font = FONT_BODY_BOLD
        c.alignment = ALIGN_RIGHT
        c.border = THIN_BORDER
        auto_fit_columns(ws, max_width=45)

    # ------------------------------------------------------------------
    # 9. Reconciliation (account-tag vs allocation-overlay)
    # ------------------------------------------------------------------
    def _create_reconciliation(self):
        ws = self._wb.create_sheet("Reconciliation")
        apply_title(ws, 1, 1, 5, "Reconciliation — account-level tagging vs cost-center allocation")
        row = 3

        # Helper block: per cost center, total spend and allocated amounts
        apply_section_header(ws, row, 1, 6, "Allocation-overlay method (each cost center's total spend allocated)")
        row += 1
        self._headers(ws, row, ["Cost Center", "Total Spend", "→ §266", "→ §263(a)", "→ §263A", "→ Deductible"])
        row += 1
        centers = self._inp.cost_centers or []
        codes = [c.code for c in centers] if centers else sorted(
            {l.cost_center_code for l in self._inp.trial_balance})
        ov_first = row
        for code in codes:
            self._label(ws, row, 1, code)
            # Total spend for this CC
            c = ws.cell(row=row, column=2,
                        value=(f"=SUMIF('{TB_SHEET}'!$C${TB_FIRST_DATA_ROW}:$C${self._tb_last_row},"
                               f"$A{row},'{TB_SHEET}'!$F${TB_FIRST_DATA_ROW}:$F${self._tb_last_row})"))
            c.number_format = FMT_CURRENCY
            c.alignment = ALIGN_RIGHT
            c.border = THIN_BORDER
            # allocated columns: total * VLOOKUP allocation % /100
            for j, alloc_col in enumerate([3, 4, 5, 6]):  # %266,%263(a),%263A,%deductible
                cell = ws.cell(row=row, column=3 + j,
                               value=(f"=$B{row}*IFERROR(VLOOKUP($A{row},"
                                      f"'{ALLOC_SHEET}'!$A:$F,{alloc_col},FALSE),0)"))
                cell.number_format = FMT_CURRENCY
                cell.alignment = ALIGN_RIGHT
                cell.border = THIN_BORDER
            row += 1
        ov_last = row - 1
        self._label(ws, row, 1, "Overlay total", bold=True)
        for col in range(2, 7):
            cl = ws.cell(row=row, column=col).column_letter
            c = ws.cell(row=row, column=col, value=f"=SUM({cl}{ov_first}:{cl}{ov_last})")
            c.number_format = FMT_CURRENCY
            c.font = FONT_BODY_BOLD
            c.alignment = ALIGN_RIGHT
            c.border = THIN_BORDER
        overlay_total_row = row
        row += 2

        # Reconciliation table
        apply_section_header(ws, row, 1, 5, "Account-tag vs allocation-overlay")
        row += 1
        self._headers(ws, row, ["Provision", "Account-tag method", "Allocation-overlay", "Variance"])
        row += 1
        # account-tag totals come from TB helper columns; overlay from the block above
        recon_rows = [
            ("§266", "H", "C"),
            ("§263(a)", "I", "D"),
            ("§263A", "J", "E"),
            ("Deductible", "L", "F"),
        ]
        for label, tb_col, ov_col in recon_rows:
            self._label(ws, row, 1, label, bold=True)
            c1 = self._money(ws, row, 2, None)
            c1.value = self._tb_total(tb_col)
            c2 = self._money(ws, row, 3, None)
            c2.value = f"={ov_col}{overlay_total_row}"
            c3 = ws.cell(row=row, column=4, value=f"=B{row}-C{row}")
            c3.number_format = FMT_CURRENCY
            c3.alignment = ALIGN_RIGHT
            c3.border = THIN_BORDER
            row += 1
        # flag non-zero variance
        from openpyxl.formatting.rule import CellIsRule
        ws.conditional_formatting.add(
            f"D{row - len(recon_rows)}:D{row - 1}",
            CellIsRule(operator="notEqual", formula=["0"], fill=FILL_HIGHLIGHT_ORANGE))
        row += 1
        self._label(ws, row, 1,
                    "Variance = where account-level tags and cost-center allocation overlays disagree. "
                    "Investigate non-zero rows.")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
        auto_fit_columns(ws, max_width=40)

    # ------------------------------------------------------------------
    # 10. Book-Tax / M-1 & Journal Entries
    # ------------------------------------------------------------------
    def _create_booktax(self):
        ws = self._wb.create_sheet("Book-Tax & JE")
        apply_title(ws, 1, 1, 4, "Book-Tax (M-1/M-3) Adjustments & Journal Entries")
        row = 3
        apply_section_header(ws, row, 1, 4, "Schedule M-1 / M-3 capitalization adjustments")
        row += 1
        self._headers(ws, row, ["Adjustment", "Amount", "Type"])
        row += 1
        items = [
            ("Costs capitalized under §266 (book-deducted)", "H", "Temporary"),
            ("Costs capitalized under §263(a) (book-deducted)", "I", "Temporary"),
            ("Additional §263A costs capitalized to inventory", "J", "Temporary"),
            ("Other capitalization (§174A/§197/§195…)", "K", "Temporary"),
        ]
        first = row
        for label, col, typ in items:
            self._label(ws, row, 1, label)
            c = self._money(ws, row, 2, None)
            c.value = self._tb_total(col)
            self._label(ws, row, 3, typ)
            row += 1
        self._label(ws, row, 1, "Total book-to-tax capitalization addback", bold=True)
        c = ws.cell(row=row, column=2, value=f"=SUM(B{first}:B{row - 1})")
        c.number_format = FMT_CURRENCY
        c.font = FONT_BODY_BOLD
        c.alignment = ALIGN_RIGHT
        c.border = THIN_BORDER
        c.fill = FILL_HIGHLIGHT_GREEN
        row += 2

        apply_section_header(ws, row, 1, 4, "Illustrative tax journal entry")
        row += 1
        self._headers(ws, row, ["Account", "Debit", "Credit"])
        row += 1
        self._label(ws, row, 1, "Dr  Capitalized cost / inventory (asset)")
        c = self._money(ws, row, 2, None)
        c.value = f"=B{row - 3 - len(items)}" if False else "=B" + str(first + len(items))
        row += 1
        self._label(ws, row, 1, "  Cr  Expense (reverse book deduction)")
        c = self._money(ws, row, 3, None)
        c.value = "=B" + str(first + len(items))
        row += 2
        self._label(ws, row, 1,
                    "Capitalized amounts increase asset/inventory basis and are recovered via "
                    "depreciation/amortization, COGS, or on disposition per each provision.")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        auto_fit_columns(ws, max_width=55)

    # ------------------------------------------------------------------
    # 11. IRS Practice Units (§263A examiner guidance)
    # ------------------------------------------------------------------
    def _create_practice_units(self):
        ws = self._wb.create_sheet("IRS Practice Units")
        apply_title(ws, 1, 1, 7, "IRS LB&I Practice Units — §263A Examiner Guidance")
        self._label(ws, 2, 1,
                    "Practice Units are IRS training / audit roadmaps — not authoritative law and "
                    "not citable as precedent. Current to 2026-06-30.")
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=7)
        self._headers(ws, 3, [
            "Practice Unit", "Type", "Date / Status", "Governing regs",
            "Examiner process steps", "Examiner focus", "Key points / URL",
        ])
        row = 4
        for pu in PRACTICE_UNITS_263A:
            key_block = pu["key_points"]
            if pu.get("current_note"):
                key_block += "\n\n[Current law: " + pu["current_note"] + "]"
            key_block += "\n\nDCN: " + pu["dcn"] + "\n" + pu["url"]
            vals = [
                pu["title"], pu["unit_type"], pu["date"], pu["regs"],
                pu["process"], pu["examiner_focus"], key_block,
            ]
            for i, v in enumerate(vals):
                c = ws.cell(row=row, column=1 + i, value=v)
                c.font = FONT_BODY
                c.alignment = ALIGN_LEFT
                c.border = THIN_BORDER
            row += 1
        widths = {"A": 34, "B": 18, "C": 30, "D": 34, "E": 70, "F": 55, "G": 60}
        for col, w in widths.items():
            ws.column_dimensions[col].width = w

    # ------------------------------------------------------------------
    # 12. Authorities
    # ------------------------------------------------------------------
    def _create_authorities(self):
        ws = self._wb.create_sheet("Authorities")
        apply_title(ws, 1, 1, 6, "Technical Authorities — Cost Capitalization")
        self._headers(ws, 3, [
            "Citation", "Type", "Title", "Req/Elec", "Key Holding", "Topics",
        ])
        row = 4
        for a in COST_CAP_LOOKUP.authorities:
            re_flag = "Favorable/Elective" if a.taxpayer_favorable else "Required/Adverse"
            vals = [
                a.citation, a.authority_type, a.title, re_flag,
                a.key_holding, ", ".join(a.topics),
            ]
            for i, v in enumerate(vals):
                c = ws.cell(row=row, column=1 + i, value=v)
                c.font = FONT_BODY
                c.alignment = ALIGN_LEFT
                c.border = THIN_BORDER
            row += 1
        # widen the key-holding column, wrap text
        ws.column_dimensions["A"].width = 28
        ws.column_dimensions["B"].width = 14
        ws.column_dimensions["C"].width = 36
        ws.column_dimensions["D"].width = 18
        ws.column_dimensions["E"].width = 80
        ws.column_dimensions["F"].width = 40
        for r in range(4, row):
            ws.cell(row=r, column=5).alignment = ALIGN_LEFT
