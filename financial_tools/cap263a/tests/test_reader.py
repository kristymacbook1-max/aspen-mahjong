"""Reader: debit/credit netting (a two-column TB must not zero out credits)."""

import os
from decimal import Decimal

import pytest
from openpyxl import Workbook
from financial_tools.cap263a.reader import read_trial_balance, _to_decimal


def test_debit_credit_netting(tmp_path):
    wb = Workbook(); ws = wb.active; ws.title = "TB"
    ws.append(["Account Number", "Account Description", "Cost Center", "Debit", "Credit"])
    ws.append(["4000", "Sales revenue", "Sales", "", 500000])     # credit-only
    ws.append(["5000", "Direct labor", "Plant", 300000, ""])      # debit-only
    ws.append(["6000", "Net line", "Plant", 100000, 40000])       # both
    p = os.path.join(tmp_path, "dc.xlsx"); wb.save(p)
    lines = read_trial_balance(p)
    amounts = {l.acct_desc: l.amount for l in lines}
    assert amounts["Sales revenue"] == Decimal("-500000")   # not zero
    assert amounts["Direct labor"] == Decimal("300000")
    assert amounts["Net line"] == Decimal("60000")          # debit - credit


def test_single_amount_column_still_works(tmp_path):
    wb = Workbook(); ws = wb.active; ws.title = "TB"
    ws.append(["Account Number", "Account Description", "Amount"])
    ws.append(["5000", "Direct labor", 300000])
    p = os.path.join(tmp_path, "amt.xlsx"); wb.save(p)
    lines = read_trial_balance(p)
    assert lines[0].amount == Decimal("300000")


def test_no_amount_or_debit_credit_column_raises(tmp_path):
    """A TB with only account/description columns must error, not silently
    produce $0 for every line."""
    wb = Workbook(); ws = wb.active; ws.title = "TB"
    ws.append(["Account Number", "Account Description"])
    ws.append(["5000", "Direct labor"])
    p = os.path.join(tmp_path, "noamt.xlsx"); wb.save(p)
    with pytest.raises(ValueError, match="amount, debit, or credit"):
        read_trial_balance(p)


def test_formula_error_strings_are_skipped(tmp_path):
    """A broken formula cached as '#REF!'/'#N/A' must not become a phantom
    line item polluting totals."""
    wb = Workbook(); ws = wb.active; ws.title = "TB"
    ws.append(["Account Number", "Account Description", "Amount"])
    ws.append(["5000", "Direct labor", 300000])
    ws.append(["6000", "#REF!", 999999])
    ws.append(["7000", "#N/A", 888888])
    p = os.path.join(tmp_path, "err.xlsx"); wb.save(p)
    lines = read_trial_balance(p)
    assert len(lines) == 1
    assert lines[0].acct_desc == "Direct labor"


def test_ambiguous_sheets_require_explicit_choice(tmp_path):
    """Two equally-plausible sheets with no hint match must not silently pick
    the first one in workbook order — that risks reading a stale/wrong TB."""
    wb = Workbook()
    ws1 = wb.active; ws1.title = "2023 Data"
    ws1.append(["Account Number", "Account Description", "Amount"])
    ws1.append(["5000", "Direct labor", 300000])
    ws2 = wb.create_sheet("2024 Data")
    ws2.append(["Account Number", "Account Description", "Amount"])
    ws2.append(["5000", "Direct labor", 400000])
    p = os.path.join(tmp_path, "ambiguous.xlsx"); wb.save(p)
    with pytest.raises(ValueError, match="Multiple candidate sheets"):
        read_trial_balance(p)
    # explicit sheet= still works
    lines = read_trial_balance(p, sheet="2024 Data")
    assert lines[0].amount == Decimal("400000")


def test_accounting_negative_with_dollar_sign_and_space():
    """"$ (1,234.00)" (dollar sign, space, then parens) must parse as a real
    negative, not silently zero out."""
    assert _to_decimal("$ (1,234.00)") == Decimal("-1234.00")
    assert _to_decimal("$(1,234,567.89)") == Decimal("-1234567.89")
