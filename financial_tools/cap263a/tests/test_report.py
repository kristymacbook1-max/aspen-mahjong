"""Report generation: must not crash on edge-case inputs."""

import os
from decimal import Decimal

from openpyxl import load_workbook

from financial_tools.cap263a.model import TBLine
from financial_tools.cap263a.analysis import analyze, EntityProfile
from financial_tools.cap263a.report import CapitalizationReport


def test_empty_trial_balance_does_not_crash(tmp_path):
    """A zero-row TB used to invert the conditional-formatting range
    (O4:O3) and crash workbook generation entirely."""
    r = analyze([], EntityProfile())
    path = os.path.join(tmp_path, "empty.xlsx")
    out = CapitalizationReport().generate(r, path)
    wb = load_workbook(out)
    assert "Summary Dashboard" in wb.sheetnames
    assert "Classified TB" in wb.sheetnames


def test_normal_trial_balance_generates_five_tabs(tmp_path):
    lines = [
        TBLine("5000", "Direct labor", "100", "Production", amount=Decimal("1000000")),
        TBLine("7000", "Advertising", "400", "Marketing", amount=Decimal("200000")),
    ]
    r = analyze(lines, EntityProfile(avg_gross_receipts=Decimal("75000000")))
    path = os.path.join(tmp_path, "tb.xlsx")
    out = CapitalizationReport().generate(r, path)
    wb = load_workbook(out)
    # Full ordered list, not just a subset/index-0 check — a set-based
    # assertion here wouldn't catch tabs 2-5 silently reordering.
    assert wb.sheetnames == ["Summary Dashboard", "Classified TB", "Asset Basis Schedule",
                             "Adjusted IS", "Method Changes"]


def test_review_workflow_surfaces(tmp_path):
    """The Classified TB must be workable as a review queue: autofilter,
    frozen header, provenance columns, and a bucket-name data validation
    (a typo'd bucket silently drops the line from the Summary SUMIFS)."""
    lines = [
        TBLine("5000", "Direct labor", "100", "Production", amount=Decimal("1000000")),
        TBLine("7000", "Advertising", "400", "Marketing", amount=Decimal("200000")),
    ]
    r = analyze(lines, EntityProfile(avg_gross_receipts=Decimal("75000000")))
    path = os.path.join(tmp_path, "tb.xlsx")
    wb = load_workbook(CapitalizationReport().generate(r, path))
    tb = wb["Classified TB"]
    assert tb.auto_filter.ref and tb.auto_filter.ref.startswith("A3:")
    assert tb.freeze_panes == "A4"
    assert tb.cell(3, 17).value == "Method (why)"
    assert tb.cell(3, 18).value == "Zone"
    assert tb.cell(4, 17).value          # provenance actually populated
    assert len(tb.data_validations.dataValidation) == 1


def test_no_label_stored_as_broken_formula(tmp_path):
    """A label written as "= Adjusted currently-deductible" was stored by
    openpyxl as a formula and rendered #NAME? in Excel."""
    r = analyze([], EntityProfile())
    path = os.path.join(tmp_path, "empty.xlsx")
    wb = load_workbook(CapitalizationReport().generate(r, path))
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if c.data_type == "f":   # formula cells must look like formulas
                    assert str(c.value).startswith("="), (ws.title, c.coordinate)
                    assert not str(c.value).startswith("= "), (ws.title, c.coordinate)


def test_warnings_render_on_summary(tmp_path):
    """UNICAP computation warnings (unimplemented method, stale threshold,
    negative pools) must be visible in the workpaper itself, not just stderr."""
    lines = [TBLine("5000", "Direct labor", "100", "Production", amount=Decimal("100000"))]
    r = analyze(lines, EntityProfile(avg_gross_receipts=Decimal("75000000"),
                                     method="MSPM", tax_year=2027))
    path = os.path.join(tmp_path, "warn.xlsx")
    wb = load_workbook(CapitalizationReport().generate(r, path))
    summ = wb["Summary Dashboard"]
    cautions = [c.value for row in summ.iter_rows() for c in row
                if isinstance(c.value, str) and c.value.startswith("⚠")]
    assert any("MSPM" in c for c in cautions)
    assert any("2027" in c for c in cautions)
