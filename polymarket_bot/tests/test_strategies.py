import unittest

from polymarket_bot.models import Market, OrderSide, Trade
from polymarket_bot.portfolio import Portfolio
from polymarket_bot.strategies import (
    ArbitrageStrategy,
    EventDrivenStrategy,
    MarketMakingStrategy,
    NewsEvent,
)
from polymarket_bot.strategies.base import StrategyContext


def _ctx(markets, cash=10_000):
    return StrategyContext(markets=markets, portfolio=Portfolio(cash=cash), now=0.0)


class ArbitrageTests(unittest.TestCase):
    def test_fires_when_edge_exceeds_threshold(self):
        strat = ArbitrageStrategy(pairs=[("A", "B")], min_edge=0.02, max_size=50)
        markets = [
            Market("A", "?", best_bid=0.47, best_ask=0.48, liquidity=100),
            Market("B", "?", best_bid=0.54, best_ask=0.55, liquidity=100),
        ]
        orders = strat.generate_orders(_ctx(markets))
        self.assertEqual(len(orders), 2)
        buy = next(o for o in orders if o.side is OrderSide.BUY)
        sell = next(o for o in orders if o.side is OrderSide.SELL)
        self.assertEqual(buy.market_id, "A")
        self.assertAlmostEqual(buy.price, 0.48)
        self.assertEqual(sell.market_id, "B")
        self.assertAlmostEqual(sell.price, 0.54)

    def test_symmetric_direction(self):
        strat = ArbitrageStrategy(pairs=[("A", "B")], min_edge=0.02, max_size=50)
        markets = [
            Market("A", "?", best_bid=0.60, best_ask=0.62, liquidity=100),
            Market("B", "?", best_bid=0.45, best_ask=0.50, liquidity=100),
        ]
        orders = strat.generate_orders(_ctx(markets))
        buy = next(o for o in orders if o.side is OrderSide.BUY)
        self.assertEqual(buy.market_id, "B")

    def test_no_edge_no_orders(self):
        strat = ArbitrageStrategy(pairs=[("A", "B")], min_edge=0.02)
        markets = [
            Market("A", "?", best_bid=0.49, best_ask=0.50),
            Market("B", "?", best_bid=0.50, best_ask=0.51),
        ]
        self.assertEqual(strat.generate_orders(_ctx(markets)), [])

    def test_skips_resolved_markets(self):
        strat = ArbitrageStrategy(pairs=[("A", "B")], min_edge=0.02)
        markets = [
            Market("A", "?", best_bid=0.40, best_ask=0.42,
                   resolved=True, outcome=1.0),
            Market("B", "?", best_bid=0.55, best_ask=0.56),
        ]
        self.assertEqual(strat.generate_orders(_ctx(markets)), [])

    def test_invalid_params_rejected(self):
        with self.assertRaises(ValueError):
            ArbitrageStrategy(pairs=[("A", "B")], min_edge=0)
        with self.assertRaises(ValueError):
            ArbitrageStrategy(pairs=[("A", "B")], max_size=0)


class MarketMakingTests(unittest.TestCase):
    def test_emits_two_sided_quote(self):
        strat = MarketMakingStrategy(market_ids=["M"], edge=0.02, quote_size=10)
        markets = [Market("M", "?", best_bid=0.30, best_ask=0.60)]
        orders = strat.generate_orders(_ctx(markets))
        self.assertEqual(len(orders), 2)
        bid = next(o for o in orders if o.side is OrderSide.BUY)
        ask = next(o for o in orders if o.side is OrderSide.SELL)
        self.assertLess(bid.price, ask.price)
        # centered on mid = 0.45 with +/- 0.02 edge
        self.assertAlmostEqual(bid.price, 0.43, places=3)
        self.assertAlmostEqual(ask.price, 0.47, places=3)

    def test_inventory_skew_long_lowers_center(self):
        strat = MarketMakingStrategy(
            market_ids=["M"], edge=0.02, quote_size=10,
            max_inventory=100, max_skew=0.05,
        )
        portfolio = Portfolio(cash=1000)
        portfolio.apply_trade(Trade("M", OrderSide.BUY, price=0.40, size=100))
        ctx = StrategyContext(
            markets=[Market("M", "?", best_bid=0.30, best_ask=0.60)],
            portfolio=portfolio,
            now=0.0,
        )
        orders = strat.generate_orders(ctx)
        bid = next(o for o in orders if o.side is OrderSide.BUY)
        ask = next(o for o in orders if o.side is OrderSide.SELL)
        # max skew applied, so center = 0.45 - 0.05 = 0.40
        self.assertAlmostEqual(bid.price, 0.38, places=3)
        self.assertAlmostEqual(ask.price, 0.42, places=3)

    def test_skips_resolved_markets(self):
        strat = MarketMakingStrategy(market_ids=["M"], edge=0.02, quote_size=10)
        markets = [Market("M", "?", best_bid=0.30, best_ask=0.60,
                          resolved=True, outcome=1.0)]
        self.assertEqual(strat.generate_orders(_ctx(markets)), [])

    def test_skips_tight_market(self):
        """If our edge would cross the existing book, we must not quote."""
        strat = MarketMakingStrategy(market_ids=["M"], edge=0.05, quote_size=10)
        markets = [Market("M", "?", best_bid=0.49, best_ask=0.51)]
        self.assertEqual(strat.generate_orders(_ctx(markets)), [])


class EventDrivenTests(unittest.TestCase):
    def test_buys_when_fair_value_above_ask(self):
        strat = EventDrivenStrategy(sensitivity=1.0, threshold=0.03, order_size=25)
        strat.ingest([NewsEvent("M", impact=1.0, confidence=1.0, timestamp=0.0)])
        markets = [Market("M", "?", best_bid=0.40, best_ask=0.42)]
        orders = strat.generate_orders(_ctx(markets))
        self.assertEqual(len(orders), 1)
        self.assertIs(orders[0].side, OrderSide.BUY)

    def test_sells_when_fair_value_below_bid(self):
        strat = EventDrivenStrategy(sensitivity=1.0, threshold=0.03, order_size=25)
        strat.ingest([NewsEvent("M", impact=-1.0, confidence=1.0, timestamp=0.0)])
        markets = [Market("M", "?", best_bid=0.58, best_ask=0.60)]
        orders = strat.generate_orders(_ctx(markets))
        self.assertEqual(len(orders), 1)
        self.assertIs(orders[0].side, OrderSide.SELL)

    def test_below_threshold_no_order(self):
        strat = EventDrivenStrategy(sensitivity=0.01, threshold=0.05, order_size=10)
        strat.ingest([NewsEvent("M", impact=0.2, confidence=0.5, timestamp=0.0)])
        markets = [Market("M", "?", best_bid=0.49, best_ask=0.51)]
        self.assertEqual(strat.generate_orders(_ctx(markets)), [])

    def test_fair_value_updates_sticky(self):
        strat = EventDrivenStrategy(sensitivity=0.5, threshold=0.05, order_size=10)
        markets = [Market("M", "?", best_bid=0.49, best_ask=0.51)]
        strat.ingest([NewsEvent("M", impact=1.0, confidence=1.0, timestamp=0.0)])
        strat.generate_orders(_ctx(markets))
        # Fair value bumped from mid (0.5) by 0.5 => 1.0 clipped to 0.99.
        self.assertAlmostEqual(strat.fair_value("M"), 0.99)


if __name__ == "__main__":
    unittest.main()
