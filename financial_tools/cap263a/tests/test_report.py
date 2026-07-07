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
