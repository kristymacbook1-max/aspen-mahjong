"""§1060 residual-method golden tests — compute_1060_allocation.

Every expected figure is hand-derived in the test docstrings.
"""

from decimal import Decimal

from financial_tools.cap263a.engines.purchase_price_allocation import (
    compute_1060_allocation)
from financial_tools.cap263a.model import PurchasePriceAllocation

FMVS = {"I": Decimal("50000"), "II": Decimal("100000"),
        "III": Decimal("150000"), "IV": Decimal("200000"),
        "V": Decimal("300000"), "VI": Decimal("100000")}   # ΣI-VI = 900,000


def test_full_waterfall_positive_class_vii_residual():
    """Consideration 1,000,000 against Class I-VI FMVs summing to 900,000
    (50k + 100k + 150k + 200k + 300k + 100k): every class fills to FMV in
    order; Class VII (goodwill/going concern) = 1,000,000 − 900,000 =
    100,000. No warnings."""
    out = compute_1060_allocation(PurchasePriceAllocation(
        transaction_id="ACQ1", aggregate_consideration=Decimal("1000000"),
        class_fmv=dict(FMVS)))
    for cls, fmv in FMVS.items():
        assert out["by_class"][cls] == fmv
    assert out["by_class"]["VII"] == Decimal("100000")
    assert out["class_vii_residual"] == Decimal("100000")
    assert out["warnings"] == []


def test_shortfall_proportional_in_short_class_zero_after():
    """Consideration 400,000 < ΣI-VI FMV 900,000: I 50,000 + II 100,000 +
    III 150,000 = 300,000 fill fully; remaining 100,000 < Class IV FMV
    200,000 → Class IV takes the 100,000 remainder (allocated within the
    class in proportion to FMV per §1.338-6(b)), Classes V/VI take 0,
    Class VII = 0, CONSIDERATION-BELOW-CLASS-FMV warning fires."""
    out = compute_1060_allocation(PurchasePriceAllocation(
        transaction_id="ACQ2", aggregate_consideration=Decimal("400000"),
        class_fmv=dict(FMVS)))
    assert out["by_class"]["I"] == Decimal("50000")
    assert out["by_class"]["II"] == Decimal("100000")
    assert out["by_class"]["III"] == Decimal("150000")
    assert out["by_class"]["IV"] == Decimal("100000")   # short class
    assert out["by_class"]["V"] == Decimal("0")
    assert out["by_class"]["VI"] == Decimal("0")
    assert out["by_class"]["VII"] == Decimal("0")
    assert out["class_vii_residual"] == Decimal("0")
    assert any("CONSIDERATION-BELOW-CLASS-FMV" in w for w in out["warnings"])


def test_negative_consideration_errors():
    """Negative aggregate consideration is a data error — no allocation,
    NEGATIVE-CONSIDERATION flag."""
    out = compute_1060_allocation(PurchasePriceAllocation(
        transaction_id="ACQ3", aggregate_consideration=Decimal("-1"),
        class_fmv=dict(FMVS)))
    assert out["by_class"] == {}
    assert out["class_vii_residual"] == Decimal("0")
    assert any("NEGATIVE-CONSIDERATION" in w for w in out["warnings"])


def test_missing_classes_treated_as_zero_fmv():
    """Only Classes IV and V supplied (inventory 80,000 + tangibles
    120,000), consideration 250,000: I/II/III/VI allocate 0; IV = 80,000,
    V = 120,000; Class VII residual = 250,000 − 200,000 = 50,000."""
    out = compute_1060_allocation(PurchasePriceAllocation(
        transaction_id="ACQ4", aggregate_consideration=Decimal("250000"),
        class_fmv={"IV": Decimal("80000"), "V": Decimal("120000")}))
    assert out["by_class"]["I"] == Decimal("0")
    assert out["by_class"]["IV"] == Decimal("80000")
    assert out["by_class"]["V"] == Decimal("120000")
    assert out["by_class"]["VII"] == Decimal("50000")
    assert out["warnings"] == []
