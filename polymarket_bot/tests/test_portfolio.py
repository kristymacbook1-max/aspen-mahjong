import unittest

from polymarket_bot.models import Market, OrderSide, Trade
from polymarket_bot.portfolio import Portfolio


class PortfolioTests(unittest.TestCase):
    def test_buy_decrements_cash(self):
        p = Portfolio(cash=1000)
        p.apply_trade(Trade("m1", OrderSide.BUY, price=0.30, size=100))
        self.assertAlmostEqual(p.cash, 1000 - 30)
        self.assertAlmostEqual(p.position("m1").shares, 100)

    def test_sell_increments_cash(self):
        p = Portfolio(cash=1000)
        p.apply_trade(Trade("m1", OrderSide.BUY, price=0.30, size=100))
        p.apply_trade(Trade("m1", OrderSide.SELL, price=0.50, size=100))
        self.assertAlmostEqual(p.cash, 1000 - 30 + 50)
        self.assertEqual(p.position("m1").shares, 0)
        self.assertAlmostEqual(p.realized_pnl(), 20)

    def test_settle_winning_market(self):
        p = Portfolio(cash=1000)
        p.apply_trade(Trade("m1", OrderSide.BUY, price=0.30, size=100))
        m = Market("m1", "?", best_bid=0.4, best_ask=0.5, resolved=True, outcome=1.0)
        payout = p.settle_market(m)
        self.assertAlmostEqual(payout, 100.0)
        self.assertAlmostEqual(p.cash, 1000 - 30 + 100)
        self.assertEqual(p.position("m1").shares, 0)
        # realized pnl: (1.0 - 0.30) * 100
        self.assertAlmostEqual(p.realized_pnl(), 70)

    def test_settle_losing_market(self):
        p = Portfolio(cash=1000)
        p.apply_trade(Trade("m1", OrderSide.BUY, price=0.30, size=100))
        m = Market("m1", "?", best_bid=0.4, best_ask=0.5, resolved=True, outcome=0.0)
        payout = p.settle_market(m)
        self.assertEqual(payout, 0.0)
        self.assertAlmostEqual(p.cash, 1000 - 30)
        self.assertAlmostEqual(p.realized_pnl(), -30)

    def test_settle_unresolved_raises(self):
        p = Portfolio(cash=1000)
        m = Market("m1", "?", best_bid=0.4, best_ask=0.5)
        with self.assertRaises(ValueError):
            p.settle_market(m)

    def test_equity(self):
        p = Portfolio(cash=500)
        p.apply_trade(Trade("m1", OrderSide.BUY, price=0.30, size=100))
        # cash = 470, shares = 100 @ mark 0.45 => 45
        self.assertAlmostEqual(p.equity({"m1": 0.45}), 470 + 45)

    def test_unrealized_pnl_ignores_markless_positions(self):
        p = Portfolio(cash=500)
        p.apply_trade(Trade("m1", OrderSide.BUY, price=0.30, size=100))
        self.assertAlmostEqual(p.unrealized_pnl({}), 0.0)
        self.assertAlmostEqual(
            p.unrealized_pnl({"m1": 0.50}), (0.50 - 0.30) * 100
        )


if __name__ == "__main__":
    unittest.main()
