import unittest

from polymarket_bot.client import PaperClient
from polymarket_bot.engine import Engine
from polymarket_bot.models import Market, Order, OrderSide
from polymarket_bot.portfolio import Portfolio
from polymarket_bot.risk import RiskLimits, RiskManager
from polymarket_bot.strategies import ArbitrageStrategy, EventDrivenStrategy, NewsEvent
from polymarket_bot.strategies.base import Strategy, StrategyContext


class _CannedStrategy(Strategy):
    """Strategy that returns a preset list of orders, for engine testing."""

    name = "canned"

    def __init__(self, orders):
        self._orders = orders

    def generate_orders(self, ctx: StrategyContext):
        return list(self._orders)


class EngineTests(unittest.TestCase):
    def _build(self, strategies):
        client = PaperClient()
        client.seed(
            [
                Market("A", "?", best_bid=0.48, best_ask=0.50, liquidity=500),
                Market("B", "?", best_bid=0.53, best_ask=0.55, liquidity=500),
            ]
        )
        portfolio = Portfolio(cash=5_000)
        risk = RiskManager(
            limits=RiskLimits(
                max_order_notional=500,
                max_position_notional=2_000,
                max_gross_notional=5_000,
                min_cash_reserve=0,
                max_drawdown_pct=0.25,
            ),
            portfolio=portfolio,
        )
        return Engine(client=client, portfolio=portfolio, risk=risk, strategies=strategies), client, portfolio

    def test_arbitrage_round_trip(self):
        strat = ArbitrageStrategy(pairs=[("A", "B")], min_edge=0.02, max_size=20)
        engine, client, portfolio = self._build([strat])

        report = engine.tick()

        # 0.53 - 0.50 = 0.03 edge => BUY A + SELL B
        self.assertEqual(report.proposed, 2)
        self.assertEqual(report.submitted, 2)
        self.assertEqual(len(report.fills), 2)

        self.assertAlmostEqual(portfolio.position("A").shares, 20)
        self.assertAlmostEqual(portfolio.position("B").shares, -20)
        # Cash delta: -0.50*20 + 0.53*20 = 0.6 in favor of the trader.
        self.assertAlmostEqual(portfolio.cash, 5_000 + (0.53 - 0.50) * 20)
        _ = client

    def test_strategy_exception_does_not_crash_tick(self):
        class _Bad(Strategy):
            name = "bad"
            def generate_orders(self, ctx):
                raise RuntimeError("boom")

        engine, _, _ = self._build([_Bad()])
        report = engine.tick()
        self.assertEqual(report.proposed, 0)
        self.assertEqual(report.submitted, 0)

    def test_risk_rejection_counted(self):
        # Order sized to breach max_position_notional instantly (2000 limit).
        canned = _CannedStrategy([
            Order("A", OrderSide.BUY, price=0.50, size=100_000),
        ])
        engine, _, portfolio = self._build([canned])
        report = engine.tick()
        # Risk manager shrinks, not rejects, so submitted=1
        self.assertEqual(report.submitted, 1)
        # Cash spent is bounded by max_order_notional = 500
        self.assertGreaterEqual(portfolio.cash, 5_000 - 500 - 1e-6)

    def test_market_settlement_pays_out(self):
        canned = _CannedStrategy([
            Order("A", OrderSide.BUY, price=0.50, size=100),
        ])
        engine, client, portfolio = self._build([canned])
        engine.tick()  # fills 100 shares @ 0.50
        self.assertAlmostEqual(portfolio.position("A").shares, 100)

        client.resolve_market("A", outcome=1.0)
        # Remove strategy so second tick just settles.
        engine.strategies = []
        engine.tick()
        self.assertEqual(portfolio.position("A").shares, 0)
        # Bought 100 @ 0.50 = -50, payout +100 => net +50 cash delta
        self.assertAlmostEqual(portfolio.cash, 5_000 + 50)

    def test_event_strategy_end_to_end(self):
        strat = EventDrivenStrategy(sensitivity=1.0, threshold=0.03, order_size=20)
        strat.ingest([NewsEvent("A", impact=1.0, confidence=1.0, timestamp=0.0)])
        engine, _, portfolio = self._build([strat])
        report = engine.tick()
        self.assertGreaterEqual(len(report.fills), 1)
        self.assertGreater(portfolio.position("A").shares, 0)


if __name__ == "__main__":
    unittest.main()
