"""CLI: clean error handling instead of raw tracebacks, and input validation."""

import os

from openpyxl import Workbook

from financial_tools.cap263a.cli import main


def _make_tb(path):
    wb = Workbook(); ws = wb.active; ws.title = "TB"
    ws.append(["Account Number", "Account Description", "Amount"])
    ws.append(["5000", "Direct labor", 300000])
    wb.save(path)


def test_missing_file_returns_clean_error(tmp_path, capsys):
    rc = main([str(tmp_path / "does_not_exist.xlsx")])
    assert rc == 1
    err = capsys.readouterr().err
    assert "error:" in err
    assert "Traceback" not in err


def test_negative_gross_receipts_rejected(tmp_path, capsys):
    tb = tmp_path / "tb.xlsx"; _make_tb(tb)
    rc = main([str(tb), "--gross-receipts", "-500"])
    assert rc == 1
    assert "must be >= 0" in capsys.readouterr().err


def test_valid_run_succeeds(tmp_path, capsys):
    tb = tmp_path / "tb.xlsx"; _make_tb(tb)
    out_dir = tmp_path / "out"
    rc = main([str(tb), "--gross-receipts", "75000000", "--out-dir", str(out_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Workbook:" in out
    assert os.path.exists(out_dir)
