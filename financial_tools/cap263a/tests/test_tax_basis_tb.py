"""Runtime Pipeline Step 2 — tax-basis TB materialization."""

from decimal import Decimal

from financial_tools.cap263a.model import BookTaxDifference, TBLine
from financial_tools.cap263a.engines.tax_basis_tb import compute_tax_basis_tb


def _tb():
    return [
        TBLine("5000", "Direct labor", "100", "Production", amount=Decimal("1000000")),
        TBLine("6100", "Depreciation - plant", "100", "Production", amount=Decimal("500000")),
        TBLine("6100", "Depreciation - office", "400", "Admin", amount=Decimal("100000")),
    ]


def test_btd_applies_to_matching_line_and_ties():
    """Book depreciation 500,000 with a -80,000 BTD (tax depreciation lower in
    overhead) -> tax-basis line 420,000; book total 1,600,000 + (-80,000) =
    tax total 1,520,000, tie-check 0 by construction."""
    btds = [BookTaxDifference(btd_id="B1", acct_num="6100", cc_num="100",
                              description="Book-over-tax plant depreciation",
                              adjustment=Decimal("-80000"), affects_471=True)]
    out = compute_tax_basis_tb(_tb(), btds)
    plant = [l for l in out["tax_lines"] if l.acct_num == "6100" and l.cc_num == "100"][0]
    assert plant.amount == Decimal("420000")
    m1 = out["m1_reconciliation"]
    assert m1["book_total"] == Decimal("1600000")
    assert m1["tax_total"] == Decimal("1520000")
    assert m1["tie_check"] == Decimal("0")
    assert out["warnings"] == []
    # cost-center rollup reflects the adjusted figure
    assert out["cc_rollup"]["100"] == Decimal("1420000")


def test_acct_only_btd_with_single_match_applies():
    btds = [BookTaxDifference(acct_num="5000", description="§174 timing",
                              adjustment=Decimal("25000"))]
    out = compute_tax_basis_tb(_tb(), btds)
    labor = [l for l in out["tax_lines"] if l.acct_num == "5000"][0]
    assert labor.amount == Decimal("1025000")
    assert out["m1_reconciliation"]["tie_check"] == Decimal("0")


def test_ambiguous_acct_only_btd_warns_and_does_not_apply():
    """acct 6100 exists in two cost centers — an acct-only BTD must not be
    silently applied to either; it is reported unmatched with a split-it
    warning (the totals then intentionally do NOT move)."""
    btds = [BookTaxDifference(acct_num="6100", description="Depreciation BTD",
                              adjustment=Decimal("-50000"))]
    out = compute_tax_basis_tb(_tb(), btds)
    assert out["unmatched_btds"] == btds
    assert any("cost centers" in w for w in out["warnings"])
    # nothing applied -> tax equals book, so the tie-check flags the gap
    assert out["m1_reconciliation"]["tax_total"] == Decimal("1600000")
    assert out["m1_reconciliation"]["tie_check"] != Decimal("0")
    assert any("TIE-CHECK FAILED" in w for w in out["warnings"])


def test_unmatched_btd_carried_as_tax_only_line():
    """A BTD naming an account not on the TB becomes a standalone tax-only
    line (never silently dropped) so book + Σ(BTD) still equals tax."""
    btds = [BookTaxDifference(acct_num="9999", cc_num="500",
                              description="Reserve reversal",
                              adjustment=Decimal("30000"))]
    out = compute_tax_basis_tb(_tb(), btds)
    extra = [l for l in out["tax_lines"] if l.acct_num == "9999"]
    assert extra and extra[0].amount == Decimal("30000")
    assert extra[0].acct_desc.startswith("[BTD]")
    assert out["m1_reconciliation"]["tie_check"] == Decimal("0")
    assert any("matched no TB line" in w for w in out["warnings"])


def test_input_lines_not_mutated():
    lines = _tb()
    before = [l.amount for l in lines]
    compute_tax_basis_tb(lines, [BookTaxDifference(
        acct_num="6100", cc_num="100", adjustment=Decimal("-80000"))])
    assert [l.amount for l in lines] == before
