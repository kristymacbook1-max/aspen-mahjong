"""Reader: debit/credit netting (a two-column TB must not zero out credits)."""

import os
from decimal import Decimal

from openpyxl import Workbook
from financial_tools.cap263a.reader import read_trial_balance


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
