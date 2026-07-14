"""TBLine coercion: any constructor other than reader.py must not hand
non-Decimal amounts downstream into analyze()'s Decimal arithmetic."""

from decimal import Decimal

from financial_tools.cap263a.model import TBLine


def test_none_amount_coerces_to_zero():
    assert TBLine(amount=None).amount == Decimal("0")


def test_float_amount_coerces_to_decimal():
    l = TBLine(amount=1234.56)
    assert l.amount == Decimal("1234.56")
    assert isinstance(l.amount, Decimal)


def test_int_amount_coerces_to_decimal():
    l = TBLine(amount=100)
    assert l.amount == Decimal("100")
    assert isinstance(l.amount, Decimal)


def test_decimal_amount_passes_through():
    l = TBLine(amount=Decimal("500.25"))
    assert l.amount == Decimal("500.25")
