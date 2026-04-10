"""Trading engine.

The engine ties everything together:

1. Fetch current markets from the client.
2. Ask each strategy for proposed orders.
3. Run each order through the risk manager (which may shrink or reject).
4. Submit survivors to the client and book any immediate fills to the
   portfolio.
5. Update the risk manager's drawdown mark.

The engine is deliberately synchronous and single-threaded. A real
deployment can wrap ``tick()`` in an asyncio loop or a scheduler; keeping
the core logic pure-Python makes tests and backtests trivial.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import List, Sequence

from polymarket_bot.client import MarketClient
from polymarket_bot.models import Order, OrderStatus, Trade
from polymarket_bot.portfolio import Portfolio
from polymarket_bot.risk import RiskManager, RiskViolation
from polymarket_bot.strategies.base import Strategy, StrategyContext

log = logging.getLogger(__name__)


@dataclass
class TickReport:
    """Summary of what happened on a single engine tick."""

    proposed: int = 0
    submitted: int = 0
    rejected: int = 0
    fills: List[Trade] = field(default_factory=list)
    equity: float = 0.0
    halted: bool = False


@dataclass
class Engine:
    client: MarketClient
    portfolio: Portfolio
    risk: RiskManager
    strategies: Sequence[Strategy]

    def tick(self) -> TickReport:
        report = TickReport()
        markets = self.client.list_markets()
        marks = {m.market_id: m.mid for m in markets}

        # 1. Settle any newly resolved markets before new orders are placed.
        for m in markets:
            if m.resolved:
                self.portfolio.settle_market(m)

        # 2. Collect strategy proposals.
        ctx = StrategyContext(markets=markets, portfolio=self.portfolio, now=time.time())
        proposals: List[Order] = []
        for strat in self.strategies:
            try:
                proposals.extend(strat.generate_orders(ctx))
            except Exception:  # defensive: one bad strategy can't kill the loop
                log.exception("strategy %s crashed", strat.name)
        report.proposed = len(proposals)

        # 3. Risk-check and submit.
        for order in proposals:
            try:
                checked = self.risk.check(order)
            except RiskViolation as exc:
                log.info("risk rejected order on %s: %s", order.market_id, exc)
                report.rejected += 1
                continue

            submitted = self.client.place_order(checked)
            report.submitted += 1

            if submitted.status is OrderStatus.FILLED:
                trade = self._trade_for(submitted)
                if trade is not None:
                    self.portfolio.apply_trade(trade)
                    report.fills.append(trade)

        # 4. Update drawdown tracker with fresh equity.
        equity = self.portfolio.equity(marks)
        self.risk.mark(equity)
        report.equity = equity
        report.halted = self.risk.halted
        return report

    def _trade_for(self, order: Order) -> Trade | None:
        """Pull the matching fill out of the client's trade history."""
        fills = self.client.fills_since(order.created_at)
        for t in reversed(fills):
            if (
                t.market_id == order.market_id
                and t.side == order.side
                and abs(t.size - order.filled_size) < 1e-9
            ):
                return t
        return None
