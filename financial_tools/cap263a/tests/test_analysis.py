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


def test_unicap_absorption_and_sscm():
    from decimal import Decimal as D
    lines = _tb()
    p = EntityProfile(avg_gross_receipts=D("75000000"), ending_inventory_471=D("1000000"))
    r = analyze(lines, p)
    u = r["unicap"]
    assert not u["exempt"]
    # SSCM ratio = production labor / total labor; officer comp is mixed (not labor)
    assert D("0") < u["mixed_alloc_ratio"] <= D("1")
    # absorption ratio = additional pool / §471 pool; capitalized = ending inv * ratio
    expected = (u["ending_inventory_471"] * u["absorption_ratio"]).quantize(D("0.01"))
    assert u["additional_capitalized_to_inventory"] == expected


def test_unicap_exempt_when_small():
    from decimal import Decimal as D
    r = analyze(_tb(), EntityProfile(avg_gross_receipts=D("1000000")))
    assert r["unicap"]["exempt"] is True
    assert r["unicap"]["additional_capitalized_to_inventory"] == D("0")


def test_sscm_labor_ratio_excludes_excluded_tier_labor():
    """Reg §1.263A-1(h): the SSCM ratio denominator is production + mixed-service
    labor only. Sales-commission labor (Excluded tier, is_labor=True) must not
    dilute it — a prior bug summed ALL is_labor rows regardless of tier,
    understating the capitalizable mixed-service share whenever sales/R&D
    compensation was large relative to production labor."""
    lines = [
        TBLine("5000", "Direct labor", "100", "Production", amount=Decimal("100000")),
        TBLine("8000", "Officer compensation", "400", "Executive", amount=Decimal("50000")),
        TBLine("9000", "Sales commissions", "500", "Sales", amount=Decimal("850000")),
    ]
    p = EntityProfile(avg_gross_receipts=Decimal("75000000"), ending_inventory_471=Decimal("0"))
    r = analyze(lines, p)
    u = r["unicap"]
    # denominator must be production (100k) + mixed-service officer comp (50k) = 150k,
    # NOT + sales commissions (850k) = 1,000,000
    assert u["total_labor"] == Decimal("150000"), f"got {u['total_labor']}"
    assert u["mixed_alloc_ratio"] == Decimal("0.666667")
