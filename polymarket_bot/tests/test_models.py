import unittest

from polymarket_bot.models import Market, Order, OrderSide, Position, Trade


class MarketTests(unittest.TestCase):
    def test_mid_and_spread(self):
        m = Market("m1", "?", best_bid=0.4, best_ask=0.5)
        self.assertAlmostEqual(m.mid, 0.45)
        self.assertAlmostEqual(m.spread, 0.1)

    def test_invalid_book_raises(self):
        with self.assertRaises(ValueError):
            Market("m1", "?", best_bid=0.6, best_ask=0.5)
        with self.assertRaises(ValueError):
            Market("m1", "?", best_bid=-0.1, best_ask=0.5)

    def test_resolved_requires_binary_outcome(self):
        with self.assertRaises(ValueError):
            Market("m1", "?", best_bid=0.4, best_ask=0.5, resolved=True, outcome=0.5)


class OrderTests(unittest.TestCase):
    def test_notional(self):
        o = Order("m1", OrderSide.BUY, price=0.3, size=100)
        self.assertAlmostEqual(o.notional, 30.0)

    def test_invalid_price_rejected(self):
        with self.assertRaises(ValueError):
            Order("m1", OrderSide.BUY, price=1.1, size=1)
        with self.assertRaises(ValueError):
            Order("m1", OrderSide.BUY, price=0.0, size=1)

    def test_invalid_size_rejected(self):
        with self.assertRaises(ValueError):
            Order("m1", OrderSide.BUY, price=0.5, size=0)


class PositionTests(unittest.TestCase):
    def test_open_long_updates_vwap(self):
        p = Position("m1")
        p.apply_trade(Trade("m1", OrderSide.BUY, price=0.30, size=100))
        p.apply_trade(Trade("m1", OrderSide.BUY, price=0.40, size=100))
        self.assertAlmostEqual(p.shares, 200)
        self.assertAlmostEqual(p.avg_price, 0.35)
        self.assertAlmostEqual(p.realized_pnl, 0.0)

    def test_partial_close_realizes_pnl(self):
        p = Position("m1")
        p.apply_trade(Trade("m1", OrderSide.BUY, price=0.30, size=100))
        p.apply_trade(Trade("m1", OrderSide.SELL, price=0.50, size=40))
        self.assertAlmostEqual(p.shares, 60)
        self.assertAlmostEqual(p.avg_price, 0.30)
        self.assertAlmostEqual(p.realized_pnl, (0.50 - 0.30) * 40)

    def test_full_close_zeros_position(self):
        p = Position("m1")
        p.apply_trade(Trade("m1", OrderSide.BUY, price=0.30, size=100))
        p.apply_trade(Trade("m1", OrderSide.SELL, price=0.25, size=100))
        self.assertEqual(p.shares, 0)
        self.assertEqual(p.avg_price, 0)
        self.assertAlmostEqual(p.realized_pnl, (0.25 - 0.30) * 100)

    def test_flip_long_to_short(self):
        p = Position("m1")
        p.apply_trade(Trade("m1", OrderSide.BUY, price=0.30, size=50))
        p.apply_trade(Trade("m1", OrderSide.SELL, price=0.40, size=120))
        # 50 shares closed at +0.10, remaining 70 short opened at 0.40
        self.assertAlmostEqual(p.shares, -70)
        self.assertAlmostEqual(p.avg_price, 0.40)
        self.assertAlmostEqual(p.realized_pnl, 0.10 * 50)

    def test_unrealized_pnl(self):
        p = Position("m1")
        p.apply_trade(Trade("m1", OrderSide.BUY, price=0.30, size=100))
        self.assertAlmostEqual(p.unrealized_pnl(0.45), (0.45 - 0.30) * 100)
        self.assertAlmostEqual(p.unrealized_pnl(0.20), (0.20 - 0.30) * 100)

    def test_mismatched_market_rejected(self):
        p = Position("m1")
        with self.assertRaises(ValueError):
            p.apply_trade(Trade("m2", OrderSide.BUY, 0.3, 10))


if __name__ == "__main__":
    unittest.main()
