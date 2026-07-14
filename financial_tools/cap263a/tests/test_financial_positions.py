"""§263(g) straddle carrying charges + §263(h) short-sale payments in lieu.
Hand-computed goldens in docstrings."""

from decimal import Decimal

from financial_tools.cap263a.engines.financial_positions import (
    ShortSalePayment, StraddlePosition, compute_263g, compute_263h)


def test_263g_net_capitalization():
    """Charges 10,000 (interest 8,000 + storage 2,000) − offsets 3,500
    (interest income 1,000 + sec-loan 500 + dividends net of DRD 2,000)
    = 6,500 capitalized; the offset remainder 3,500 stays deductible."""
    pos = StraddlePosition(position_id="S1", interest_to_carry=Decimal("8000"),
                           insurance_storage_transport=Decimal("2000"),
                           interest_income=Decimal("1000"),
                           securities_loan_payments=Decimal("500"),
                           dividends_net_of_drd=Decimal("2000"),
                           is_straddle_position=True)
    out = compute_263g([pos])
    assert out["items"][0]["treatment"] == "straddle_capitalize_263g"
    assert out["capitalized_total"] == Decimal("6500")
    assert out["deductible_total"] == Decimal("3500")


def test_263g_offsets_floor_at_zero():
    pos = StraddlePosition(position_id="S2", interest_to_carry=Decimal("1000"),
                           interest_income=Decimal("5000"),
                           is_straddle_position=True)
    out = compute_263g([pos])
    assert out["capitalized_total"] == Decimal("0")
    assert out["deductible_total"] == Decimal("1000")
    assert "OFFSETS-EXCEED-CHARGES" in out["items"][0]["flags"]


def test_263g_hedge_and_nonstraddle_and_unknown():
    hedge = StraddlePosition(position_id="H", interest_to_carry=Decimal("100"),
                             is_identified_hedge=True)
    non = StraddlePosition(position_id="N", interest_to_carry=Decimal("200"),
                           is_straddle_position=False)
    unk = StraddlePosition(position_id="U", interest_to_carry=Decimal("300"),
                           interest_income=Decimal("50"))
    out = compute_263g([hedge, non, unk])
    assert out["items"][0]["treatment"] == "hedging_excluded"
    assert out["items"][1]["treatment"] == "not_straddle_deduct"
    assert out["items"][2]["treatment"] == "open_question_capitalize_pending"
    # unknown: conservative capitalize of the NET (300-50=250)
    assert out["items"][2]["capitalized"] == Decimal("250")
    assert len(out["open_questions"]) == 1
    assert any("NON-STRADDLE-DEDUCTIBILITY" in w for w in out["warnings"])
    assert out["capitalized_total"] == Decimal("250")
    assert out["deductible_total"] == Decimal("100") + Decimal("200") + Decimal("50")


def test_263g_negative_guard():
    out = compute_263g([StraddlePosition(position_id="X",
                                         interest_to_carry=Decimal("-5"),
                                         is_straddle_position=True)])
    assert out["items"][0]["treatment"] == "sme_review"
    assert out["capitalized_total"] == Decimal("0")


def test_263h_windows():
    """45 days exactly -> capitalized; 46 -> deductible; extraordinary at
    300 days -> still capitalized (1-year window); 366 -> deductible."""
    ps = [ShortSalePayment(payment_id="P1", payment_in_lieu=Decimal("1000"),
                           days_short_sale_open=45),
          ShortSalePayment(payment_id="P2", payment_in_lieu=Decimal("1000"),
                           days_short_sale_open=46),
          ShortSalePayment(payment_id="P3", payment_in_lieu=Decimal("2000"),
                           days_short_sale_open=300, extraordinary_dividend=True),
          ShortSalePayment(payment_id="P4", payment_in_lieu=Decimal("2000"),
                           days_short_sale_open=366, extraordinary_dividend=True)]
    out = compute_263h(ps)
    treatments = [i["treatment"] for i in out["items"]]
    assert treatments == ["capitalize_263h_to_closing_stock_basis",
                          "deductible_held_past_window",
                          "capitalize_263h_to_closing_stock_basis",
                          "deductible_held_past_window"]
    assert out["capitalized_total"] == Decimal("3000")
    assert out["deductible_total"] == Decimal("3000")
    assert sum(1 for w in out["warnings"]
               if "263H-SUSPENSION-NOT-COMPUTED" in w) == 1


def test_263h_unknown_days_conservative():
    out = compute_263h([ShortSalePayment(payment_id="U",
                                         payment_in_lieu=Decimal("500"))])
    assert out["items"][0]["treatment"] == "open_question_capitalize_pending"
    assert out["capitalized_total"] == Decimal("500")
    assert len(out["open_questions"]) == 1


def test_263h_negative_guard():
    out = compute_263h([ShortSalePayment(payment_id="X",
                                         payment_in_lieu=Decimal("-1"),
                                         days_short_sale_open=10)])
    assert out["items"][0]["treatment"] == "sme_review"
