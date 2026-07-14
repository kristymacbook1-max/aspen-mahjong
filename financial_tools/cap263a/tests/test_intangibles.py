"""Phase G golden tests — compute_263a4_5 (§1.263(a)-4/-5, §195/§248/§709)
and route_demolition (§280B).

Every expected figure is hand-derived in the test docstrings.
"""

from datetime import date
from decimal import Decimal

from financial_tools.cap263a.engines.intangibles import (compute_263a4_5,
                                                         route_demolition)
from financial_tools.cap263a.model import (IntangibleItem, StartupOrgCostPool,
                                           TransactionCostItem)


def _run(txn=(), intang=(), pools=(), **kw):
    return compute_263a4_5(list(txn), list(intang), list(pools), **kw)


# --- §1.263(a)-4(f) 12-month rule -----------------------------------------

def test_twelve_month_rule_passes_prong_a_boundary():
    """Prong (a) governs: benefit_start 2026-02-01, payment_year 2026.
    Prong (a) = start + 12 months = 2027-02-01; prong (b) = Dec 31 of
    2026+1 = 2027-12-31. Earlier = 2027-02-01. benefit_end exactly
    2027-02-01 (ON the boundary) → NOT capitalized; amount 8,000 fully
    deductible, no AmortizableItem."""
    it = IntangibleItem(item_id="I1", amount=Decimal("8000"),
                        benefit_start=date(2026, 2, 1),
                        benefit_end=date(2027, 2, 1), payment_year=2026)
    out = _run(intang=[it])
    assert out["intangible_items"][0]["treatment"] == "twelve_month_rule_deduct"
    assert out["deductible_total"] == Decimal("8000")
    assert out["capitalized_total"] == Decimal("0")
    assert out["amortizable_items"] == []


def test_twelve_month_rule_fails_one_day_past_prong_a():
    """Same dates but benefit_end 2027-02-02 — one day past the earlier-of
    boundary (prong (a) 2027-02-01) → capitalized in full (8,000)."""
    it = IntangibleItem(item_id="I2", amount=Decimal("8000"),
                        benefit_start=date(2026, 2, 1),
                        benefit_end=date(2027, 2, 2), payment_year=2026)
    out = _run(intang=[it])
    assert out["capitalized_total"] == Decimal("8000")
    assert out["deductible_total"] == Decimal("0")


def test_twelve_month_rule_prong_b_binds_before_prong_a():
    """Prong (b) governs: benefit_start 2026-11-01, payment_year 2025.
    Prong (a) = 2027-11-01; prong (b) = Dec 31 of 2025+1 = 2026-12-31.
    Earlier = 2026-12-31. benefit_end 2027-01-15 is INSIDE 12 months of the
    start but PAST prong (b) → capitalized, proving the rule is earlier-of,
    not later-of."""
    it = IntangibleItem(item_id="I3", amount=Decimal("6000"),
                        benefit_start=date(2026, 11, 1),
                        benefit_end=date(2027, 1, 15), payment_year=2025)
    out = _run(intang=[it])
    assert out["capitalized_total"] == Decimal("6000")
    # And with benefit_end on prong (b) itself, it passes:
    it2 = IntangibleItem(item_id="I3b", amount=Decimal("6000"),
                         benefit_start=date(2026, 11, 1),
                         benefit_end=date(2026, 12, 31), payment_year=2025)
    out2 = _run(intang=[it2])
    assert out2["deductible_total"] == Decimal("6000")
    assert out2["capitalized_total"] == Decimal("0")


# --- §1.263(a)-4(e)(4) $5,000 facilitative-cost cliff -----------------------

def _capitalized_intangible(**kw):
    """An intangible that FAILS the 12-month rule (2-year benefit)."""
    base = dict(item_id="C1", amount=Decimal("20000"),
                benefit_start=date(2026, 1, 1), benefit_end=date(2028, 1, 1),
                payment_year=2026)
    base.update(kw)
    return IntangibleItem(**base)


def test_facilitative_5000_exactly_deductible():
    """Facilitative aggregate exactly 5,000 (≤ cliff): facilitative costs
    deductible; only the 20,000 intangible itself capitalizes."""
    out = _run(intang=[_capitalized_intangible(
        facilitative_costs=Decimal("5000"))])
    assert out["deductible_total"] == Decimal("5000")
    assert out["capitalized_total"] == Decimal("20000")
    assert "E4-DE-MINIMIS-DEDUCTED" in out["intangible_items"][0]["flags"]


def test_facilitative_5001_all_capitalized_no_partial():
    """Facilitative aggregate 5,001 (> cliff): the ENTIRE 5,001 capitalizes
    (no $5,000-exempt partial relief) → capitalized 20,000 + 5,001 =
    25,001; deductible 0."""
    out = _run(intang=[_capitalized_intangible(
        facilitative_costs=Decimal("5001"))])
    assert out["deductible_total"] == Decimal("0")
    assert out["capitalized_total"] == Decimal("25001")
    assert "E4-CLIFF-ALL-CAPITALIZED" in out["intangible_items"][0]["flags"]


# --- recovery routing -------------------------------------------------------

def test_197_acquired_with_business_180_months_full_month():
    """Acquired-with-business intangible 90,000 → §197: 180 months,
    full-month convention. Year-1 amortization = 90,000 × 12/180 = 6,000
    (no mid-year halving)."""
    out = _run(intang=[_capitalized_intangible(
        item_id="G1", amount=Decimal("90000"), acquired_with_business=True)])
    [item] = out["amortizable_items"]
    assert item.recovery_months == 180
    assert item.convention == "full-month"
    assert item.first_year_amortization() == Decimal("6000")


def test_benefit_term_recovery_months():
    """Non-§197 capitalized intangible with benefit 2026-01-01→2028-01-01:
    recovery = 24 months (benefit_end − benefit_start)."""
    out = _run(intang=[_capitalized_intangible()])
    assert out["amortizable_items"][0].recovery_months == 24


def test_indefinite_life_flagged_not_defaulted():
    """Capitalized intangible with no §197 route and no benefit dates:
    recovery None + INDEFINITE-LIFE-SME-REVIEW (12-month rule cannot be
    tested without dates → conservative capitalization)."""
    out = _run(intang=[IntangibleItem(item_id="N1", amount=Decimal("7500"),
                                      payment_year=2026)])
    [item] = out["amortizable_items"]
    assert item.recovery_months is None
    assert "INDEFINITE-LIFE-SME-REVIEW" in item.flags
    assert any("INDEFINITE-LIFE-SME-REVIEW" in w for w in out["warnings"])


def test_prior_capitalized_basis_posts_delta():
    """Capitalized 20,000 with prior_capitalized_basis 12,000: reconcile()
    posts only the 8,000 delta; the gross 20,000 stays on the item row."""
    out = _run(intang=[_capitalized_intangible(
        prior_capitalized_basis=Decimal("12000"))])
    row = out["intangible_items"][0]
    assert row["capitalized"] == Decimal("20000")     # gross visible
    assert row["posted_basis"] == Decimal("8000")     # delta posted
    assert out["amortizable_items"][0].basis == Decimal("8000")
    assert out["capitalized_total"] == Decimal("8000")
    assert any("BASIS-RECONCILED" in w for w in out["warnings"])


# --- §1.263(a)-5 transaction costs ------------------------------------------

def test_success_fee_100000_elected_70_30():
    """Success-based fee 100,000 in a covered transaction with the Rev.
    Proc. 2011-29 election: 100,000 × 70% = 70,000 deductible;
    100,000 − 70,000 = 30,000 capitalized. Irrevocable, per-transaction."""
    tc = TransactionCostItem(item_id="S1", transaction_id="T1",
                             amount=Decimal("100000"),
                             covered_transaction=True, success_based=True)
    out = _run(txn=[tc], success_fee_elections=frozenset({"T1"}))
    row = out["transaction_items"][0]
    assert row["deductible"] == Decimal("70000")
    assert row["capitalized"] == Decimal("30000")
    assert "REV-PROC-2011-29-IRREVOCABLE" in row["flags"]


def test_pre_bright_line_investigatory_deductible():
    """Covered transaction, NOT inherently facilitative, incurred 2026-01-15
    before the 2026-03-01 bright-line date → investigatory, deductible."""
    tc = TransactionCostItem(item_id="B1", transaction_id="T2",
                             amount=Decimal("40000"), covered_transaction=True,
                             incurred_date=date(2026, 1, 15),
                             bright_line_date=date(2026, 3, 1))
    out = _run(txn=[tc])
    assert out["transaction_items"][0]["deductible"] == Decimal("40000")
    assert out["transaction_items"][0]["capitalized"] == Decimal("0")


def test_inherently_facilitative_capitalized_regardless_of_date():
    """Inherently facilitative cost incurred BEFORE the bright-line date
    still capitalizes — the investigatory carve-out never reaches it."""
    tc = TransactionCostItem(item_id="B2", transaction_id="T2",
                             amount=Decimal("25000"), covered_transaction=True,
                             inherently_facilitative=True,
                             incurred_date=date(2026, 1, 15),
                             bright_line_date=date(2026, 3, 1))
    out = _run(txn=[tc])
    assert out["transaction_items"][0]["capitalized"] == Decimal("25000")
    assert out["transaction_items"][0]["deductible"] == Decimal("0")


def test_post_bright_line_capitalized_and_non_covered_deductible():
    post = TransactionCostItem(item_id="B3", transaction_id="T2",
                               amount=Decimal("10000"),
                               covered_transaction=True,
                               incurred_date=date(2026, 4, 1),
                               bright_line_date=date(2026, 3, 1))
    noncov = TransactionCostItem(item_id="B4", transaction_id="T3",
                                 amount=Decimal("3000"))
    out = _run(txn=[post, noncov])
    assert out["transaction_items"][0]["capitalized"] == Decimal("10000")
    assert out["transaction_items"][1]["deductible"] == Decimal("3000")
    assert out["transaction_items"][1]["treatment"] == "deductible_162"


def test_abandoned_transaction_capitalized_becomes_loss():
    """Inherently facilitative 25,000, transaction abandoned: the
    capitalized-to-date amount converts to a deductible loss
    (Rev. Rul. 73-580) — nothing left in the capitalized bucket."""
    tc = TransactionCostItem(item_id="A1", transaction_id="T4",
                             amount=Decimal("25000"), covered_transaction=True,
                             inherently_facilitative=True,
                             transaction_abandoned=True)
    out = _run(txn=[tc])
    row = out["transaction_items"][0]
    assert row["capitalized"] == Decimal("0")
    assert row["deductible"] == Decimal("25000")
    assert "ABANDONED-TRANSACTION-LOSS-73-580" in row["flags"]
    assert any("73-580" in w for w in out["warnings"])


# --- §195/§248/§709 start-up pools -------------------------------------------

def test_startup_52000_first_year_3000_remainder_49000():
    """Total 52,000: excess over 50,000 = 2,000; first-year deduction =
    min(52,000, max(0, 5,000 − 2,000)) = 3,000; remainder 49,000 over 180
    months. Commencement July 2026 → months-in-service = 12 − 7 + 1 = 6;
    year-1 amortization = 49,000 × 6/180 = 1,633.33."""
    pool = StartupOrgCostPool(pool_id="P1", total=Decimal("52000"),
                              business_commencement=date(2026, 7, 1))
    out = _run(pools=[pool])
    row = out["startup_items"][0]
    assert row["first_year_deduction"] == Decimal("3000")
    assert row["amortizable_remainder"] == Decimal("49000")
    assert row["first_year_amortization"] == Decimal("1633.33")
    [item] = out["amortizable_items"]
    assert item.basis == Decimal("49000")
    assert item.recovery_months == 180


def test_startup_30000_full_5000_deduction():
    """Total 30,000 (≤ 50,000, no phase-out): 5,000 first-year deduction,
    25,000/180 remainder. Commencement Jan 2026 → 12 months in service;
    year-1 amortization = 25,000 × 12/180 = 1,666.67."""
    pool = StartupOrgCostPool(pool_id="P2", total=Decimal("30000"),
                              business_commencement=date(2026, 1, 15))
    out = _run(pools=[pool])
    row = out["startup_items"][0]
    assert row["first_year_deduction"] == Decimal("5000")
    assert row["amortizable_remainder"] == Decimal("25000")
    assert row["first_year_amortization"] == Decimal("1666.67")


def test_startup_56000_phased_out_to_zero():
    """Total 56,000: excess 6,000 wipes the 5,000 allowance —
    max(0, 5,000 − 6,000) = 0 first-year deduction; all 56,000 amortizes
    over 180 months."""
    pool = StartupOrgCostPool(pool_id="P3", total=Decimal("56000"),
                              business_commencement=date(2026, 1, 1))
    out = _run(pools=[pool])
    row = out["startup_items"][0]
    assert row["first_year_deduction"] == Decimal("0")
    assert row["amortizable_remainder"] == Decimal("56000")


def test_syndication_permanently_capitalized_no_amortization():
    """§709(b) syndication pool 15,000: no $5,000 deduction, no 180-month
    schedule — recovery None + SYNDICATION-PERMANENTLY-CAPITALIZED."""
    pool = StartupOrgCostPool(pool_id="P4", kind="syndication",
                              total=Decimal("15000"),
                              business_commencement=date(2026, 1, 1))
    out = _run(pools=[pool])
    row = out["startup_items"][0]
    assert row["first_year_deduction"] == Decimal("0")
    assert "SYNDICATION-PERMANENTLY-CAPITALIZED" in row["flags"]
    [item] = out["amortizable_items"]
    assert item.recovery_months is None
    assert item.first_year_amortization() == Decimal("0")
    assert out["capitalized_total"] == Decimal("15000")
    assert out["deductible_total"] == Decimal("0")


# --- §280B demolition ---------------------------------------------------------

def test_280b_voluntary_demolition_routes_to_land():
    """Voluntary demolition: cost 30,000 + remaining structure basis
    70,000 → one land AmortizableItem of 100,000, no recovery period,
    §280B flag — never a deductible loss."""
    out = route_demolition(Decimal("30000"), Decimal("70000"))
    [item] = out["amortizable_items"]
    assert item.category == "land"
    assert item.basis == Decimal("100000")
    assert item.recovery_months is None
    assert "§280B-CAPITALIZED-TO-LAND" in item.flags
    assert any("§280B" in w for w in out["warnings"])


def test_280b_casualty_flags_sme_nothing_routed():
    """Casualty demolition: Notice 90-21 carve-out is a SME call —
    CASUALTY-EXCEPTION-SME-REVIEW flag, nothing auto-routed."""
    out = route_demolition(Decimal("30000"), Decimal("70000"), casualty=True)
    assert out["amortizable_items"] == []
    assert any("CASUALTY-EXCEPTION-SME-REVIEW" in w for w in out["warnings"])
