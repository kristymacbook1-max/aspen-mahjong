import unittest

from polymarket_bot.models import Order, OrderSide, Trade
from polymarket_bot.portfolio import Portfolio
from polymarket_bot.risk import RiskLimits, RiskManager, RiskViolation


def _make(cash=10_000, **overrides):
    limits = RiskLimits(
        max_order_notional=500,
        max_position_notional=2_000,
        max_gross_notional=5_000,
        min_cash_reserve=100,
        max_drawdown_pct=0.25,
        **overrides,
    )
    portfolio = Portfolio(cash=cash)
    return portfolio, RiskManager(limits=limits, portfolio=portfolio)


class RiskManagerTests(unittest.TestCase):
    def test_passes_small_order(self):
        _, risk = _make()
        order = Order("m1", OrderSide.BUY, price=0.50, size=100)  # notional 50
        checked = risk.check(order)
        self.assertAlmostEqual(checked.size, 100)

    def test_shrinks_oversized_order(self):
        _, risk = _make()
        order = Order("m1", OrderSide.BUY, price=0.50, size=2_000)  # notional 1000
        checked = risk.check(order)
        # capped by max_order_notional = 500 -> size = 1000
        self.assertAlmostEqual(checked.size, 1000)

    def test_rejects_when_cash_reserve_breached(self):
        _, risk = _make(cash=50)
        order = Order("m1", OrderSide.BUY, price=0.50, size=100)
        with self.assertRaises(RiskViolation):
            risk.check(order)

    def test_cash_reserve_shrinks_buy(self):
        portfolio, risk = _make(cash=200)  # spendable = 100
        order = Order("m1", OrderSide.BUY, price=0.50, size=1000)
        checked = risk.check(order)
        # spendable / price = 100 / 0.5 = 200 shares; then also capped by
        # max_order_notional = 500 -> 1000 shares; the tighter cap wins.
        self.assertAlmostEqual(checked.size, 200)
        _ = portfolio  # unused

    def test_position_cap_enforced(self):
        portfolio, risk = _make()
        # Fill the position up to cap.
        portfolio.apply_trade(Trade("m1", OrderSide.BUY, price=0.50, size=4_000))
        # Current notional at 0.50 mark = 2000 -> headroom = 0.
        order = Order("m1", OrderSide.BUY, price=0.50, size=1)
        with self.assertRaises(RiskViolation):
            risk.check(order)

    def test_position_cap_allows_opposite_side(self):
        portfolio, risk = _make()
        portfolio.apply_trade(Trade("m1", OrderSide.BUY, price=0.50, size=4_000))
        # Selling reduces exposure; the per-market cap must not block it.
        order = Order("m1", OrderSide.SELL, price=0.60, size=100)
        checked = risk.check(order)
        self.assertAlmostEqual(checked.size, 100)

    def test_drawdown_kill_switch(self):
        _, risk = _make()
        risk.mark(10_000)       # peak
        risk.mark(7_000)        # 30% drawdown
        self.assertTrue(risk.halted)
        with self.assertRaises(RiskViolation):
            risk.check(Order("m1", OrderSide.BUY, price=0.5, size=10))

    def test_reset_halt(self):
        _, risk = _make()
        risk.mark(10_000)
        risk.mark(7_000)
        risk.reset_halt()
        self.assertFalse(risk.halted)
        checked = risk.check(Order("m1", OrderSide.BUY, price=0.5, size=10))
        self.assertAlmostEqual(checked.size, 10)


if __name__ == "__main__":
    unittest.main()
