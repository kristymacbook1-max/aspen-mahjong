"""Phase F golden tests — compute_174 (§174/§174A).

Every expected figure is hand-derived in the test docstrings.
"""

from decimal import Decimal

from financial_tools.cap263a.engines.re_capitalization import compute_174
from financial_tools.cap263a.model import REExpenditure


def _foreign(amount="150000", re_id="F1", **kw):
    return REExpenditure(re_id=re_id, description="foreign lab",
                         amount=Decimal(amount), domestic=False,
                         tax_year=2026, **kw)


def _domestic(amount="120000", re_id="D1", **kw):
    return REExpenditure(re_id=re_id, description="domestic lab",
                         amount=Decimal(amount), domestic=True,
                         tax_year=2026, **kw)


def test_foreign_mandatory_180_month_mid_year():
    """Foreign 150,000: mandatory §174(a) capitalization, 180 months,
    mid-year convention. Year-1 amortization = 150,000 × 12/180 / 2
    = 10,000 / 2 = 5,000."""
    out = compute_174([_foreign()])
    assert out["capitalized_total"] == Decimal("150000")
    assert out["current_year_deduction"] == Decimal("0")
    [item] = out["amortizable_items"]
    assert item.category == "re_pool"
    assert item.recovery_months == 180
    assert item.convention == "mid-year"
    assert item.first_year_amortization() == Decimal("5000")


def test_domestic_default_fully_deductible_no_item():
    """Domestic 120,000, no election: §174A(a) default current expensing —
    full 120,000 deduction, NO AmortizableItem posted."""
    out = compute_174([_domestic()])
    assert out["current_year_deduction"] == Decimal("120000")
    assert out["capitalized_total"] == Decimal("0")
    assert out["amortizable_items"] == []
    assert out["items"][0]["treatment"] == "domestic_default_expense"


def test_domestic_elected_60_months():
    """Domestic 120,000 with the §174A(c) election, 60 months, mid-year:
    year-1 amortization = 120,000 × 12/60 / 2 = 24,000 / 2 = 12,000."""
    out = compute_174([_domestic()], domestic_capitalization_election=True,
                      elected_period_months=60)
    assert out["capitalized_total"] == Decimal("120000")
    assert out["current_year_deduction"] == Decimal("0")
    [item] = out["amortizable_items"]
    assert item.recovery_months == 60
    assert item.convention == "mid-year"
    assert item.first_year_amortization() == Decimal("12000")
    # §174A(c) ratable-start month is a documented data gap.
    assert "DATA GAP" in item.notes or "data gap" in item.notes.lower()


def test_elected_period_below_60_floored_with_warning():
    """§174A(c) requires ≥60 months: 36 requested → floored to 60,
    ELECTED-PERIOD-BELOW-60 warning."""
    out = compute_174([_domestic()], domestic_capitalization_election=True,
                      elected_period_months=36)
    assert out["amortizable_items"][0].recovery_months == 60
    assert any("ELECTED-PERIOD-BELOW-60" in w for w in out["warnings"])


def test_catchup_one_year():
    """One-year catch-up of remaining 2022-2024 basis 90,000: entire 90,000
    deducted in the first year beginning after 12/31/2024."""
    out = compute_174([], catchup_method="one_year",
                      remaining_2022_2024_basis=Decimal("90000"))
    assert out["current_year_deduction"] == Decimal("90000")
    assert out["catchup"]["current_year_deduction"] == Decimal("90000")
    assert out["catchup"]["following_year_deduction"] == Decimal("0")


def test_catchup_two_year_50_50_flagged():
    """Two-year catch-up of 90,000: 90,000/2 = 45,000 this year, 45,000
    next year, CATCHUP-SPLIT-UNVERIFIED flag (exact ratable split pends a
    Rev. Proc. 2025-28 primary read)."""
    out = compute_174([], catchup_method="two_year",
                      remaining_2022_2024_basis=Decimal("90000"))
    assert out["current_year_deduction"] == Decimal("45000")
    assert out["catchup"]["current_year_deduction"] == Decimal("45000")
    assert out["catchup"]["following_year_deduction"] == Decimal("45000")
    assert any("CATCHUP-SPLIT-UNVERIFIED" in w for w in out["warnings"])


def test_retroactive_mutually_exclusive_with_catchup_and_deadline():
    """small_business_retroactive together with a catch-up method → the
    mutual-exclusivity warning; the retroactive election always surfaces the
    July 6, 2026 amended-return deadline."""
    out = compute_174([], catchup_method="one_year",
                      remaining_2022_2024_basis=Decimal("10000"),
                      small_business_retroactive=True)
    assert any("MUTUALLY-EXCLUSIVE" in w for w in out["warnings"])
    assert any("July 6, 2026" in w for w in out["warnings"])


def test_retroactive_alone_emits_deadline_warning():
    out = compute_174([], small_business_retroactive=True)
    assert any("July 6, 2026" in w for w in out["warnings"])
    assert not any("MUTUALLY-EXCLUSIVE" in w for w in out["warnings"])


def test_foreign_disposal_no_loss_174d_warning():
    """Disposal of a foreign item: no loss, amortization continues
    (§174(d)) — the AmortizableItem stays on the schedule with full basis."""
    out = compute_174([_foreign()], disposal_events=["F1"])
    [item] = out["amortizable_items"]
    assert item.basis == Decimal("150000")          # amortization continues
    assert "DISPOSAL-NO-LOSS-174D" in item.flags
    assert any("§174(d)" in w for w in out["warnings"])
    # foreign disposal is the CONFIRMED case — no elective-domestic flag
    assert "§174D-DOMESTIC-ELECTIVE-UNVERIFIED" not in item.flags


def test_elected_domestic_disposal_flags_unverified():
    """Disposal of an elected-domestic item: conservative no-loss treatment
    PLUS §174D-DOMESTIC-ELECTIVE-UNVERIFIED (whether post-OBBBA §174(d)
    reaches §174A(c)-elected basis is an open primary-text question)."""
    out = compute_174([_domestic()], domestic_capitalization_election=True,
                      disposal_events=["D1"])
    [item] = out["amortizable_items"]
    assert "§174D-DOMESTIC-ELECTIVE-UNVERIFIED" in item.flags
    assert any("§174D-DOMESTIC-ELECTIVE-UNVERIFIED" in w
               for w in out["warnings"])


def test_book_capitalized_reconciliation_posts_delta_only():
    """Foreign 150,000 with book_capitalized_amount 50,000: reconcile() →
    posted basis = 150,000 − 50,000 = 100,000 (delta only); the gross
    150,000 stays visible on the item row. Year-1 amortization on the
    posted delta = 100,000 × 12/180 / 2 = 3,333.33."""
    out = compute_174([_foreign(book_capitalized_amount=Decimal("50000"))])
    row = out["items"][0]
    assert row["tax_required_capitalized"] == Decimal("150000")   # gross
    assert row["posted_basis"] == Decimal("100000")               # delta
    [item] = out["amortizable_items"]
    assert item.basis == Decimal("100000")
    assert item.first_year_amortization() == Decimal("3333.33")
    assert any("BASIS-RECONCILED" in w for w in out["warnings"])
    assert out["capitalized_total"] == Decimal("100000")


def test_book_exceeds_tax_required_flags_not_negative():
    """Book 200,000 > tax-required 150,000: no negative posting — delta 0,
    BOOK-EXCEEDS-TAX-REQUIRED flag from the shared reconcile() helper."""
    out = compute_174([_foreign(book_capitalized_amount=Decimal("200000"))])
    assert out["amortizable_items"][0].basis == Decimal("0")
    assert any("BOOK-EXCEEDS-TAX-REQUIRED" in w for w in out["warnings"])
