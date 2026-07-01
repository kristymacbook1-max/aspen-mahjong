"""Phase 2: dollars-through-the-hierarchy + waterfall bucketing."""

from decimal import Decimal
from financial_tools.cap263a.model import TBLine
from financial_tools.cap263a.analysis import analyze, EntityProfile


def _tb():
    return [
        TBLine("5000", "Direct labor", "100", "Production", amount=Decimal("1000000")),
        TBLine("5100", "Factory depreciation", "100", "Plant", amount=Decimal("500000")),
        TBLine("6000", "Warehouse storage and handling", "200", "Warehouse", amount=Decimal("300000")),
        TBLine("7000", "Advertising", "400", "Marketing", amount=Decimal("200000")),
        TBLine("8000", "Officer compensation", "400", "Executive", amount=Decimal("400000")),
        TBLine("1000", "Accounts receivable", "", "", amount=Decimal("999")),
    ]


def test_amounts_carry_through_and_tie():
    r = analyze(_tb(), EntityProfile(avg_gross_receipts=Decimal("75000000")))
    assert r["tie_check"] == Decimal("0")
    # AR is a balance-sheet line, excluded from the IS total
    assert r["is_total"] == Decimal("2400000")


def test_bucketing():
    r = analyze(_tb(), EntityProfile(avg_gross_receipts=Decimal("75000000")))
    b = r["bucket_totals"]
    assert b["Inventory §471"] == Decimal("1500000")      # labor + factory dep
    assert b["§263A Additional"] == Decimal("300000")     # warehouse storage
    assert b["Deductible"] == Decimal("200000")           # advertising
    assert b["Mixed (allocable)"] == Decimal("400000")    # officer comp (allocable)


def test_small_business_exemption_turns_off_unicap():
    r = analyze(_tb(), EntityProfile(avg_gross_receipts=Decimal("1000000")))
    b = r["bucket_totals"]
    # under the §448(c) threshold: §471 / additional / mixed all fall to deductible
    assert b["Inventory §471"] == Decimal("0")
    assert b["§263A Additional"] == Decimal("0")
    assert b["Deductible"] >= Decimal("1800000")
