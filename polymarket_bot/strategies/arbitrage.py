"""Cross-market arbitrage strategy.

The canonical setup in prediction markets is two books on the same
underlying question — e.g. "Will Candidate A win?" on Polymarket and the
equivalent contract on a competing venue — priced slightly differently.
When the spread is wide enough to clear fees, the bot buys the cheap side
and sells the expensive side to lock in a near-riskless profit.

This strategy works on pairs of binary markets that resolve to the same
outcome. Feed the pairs in at construction time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from polymarket_bot.models import Market, Order, OrderSide
from polymarket_bot.strategies.base import Strategy, StrategyContext


@dataclass
class ArbitragePair:
    """Two market_ids that resolve to the same outcome."""

    cheap_id: str  # placeholder label; which side is cheap is decided at runtime
    expensive_id: str


class ArbitrageStrategy(Strategy):
    """Detect and exploit price gaps between paired binary markets.

    Parameters:
        pairs: Iterable of (market_id_a, market_id_b) tuples that are
            economically equivalent.
        min_edge: Minimum price gap required before the bot acts. Must
            exceed expected round-trip fees and slippage; defaults to
            2 cents (0.02).
        max_size: Maximum share size per leg on a single arb.
    """

    name = "arbitrage"

    def __init__(
        self,
        pairs: Sequence[Tuple[str, str]],
        min_edge: float = 0.02,
        max_size: float = 100.0,
    ) -> None:
        if min_edge <= 0:
            raise ValueError("min_edge must be positive")
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        self._pairs = [tuple(p) for p in pairs]
        self._min_edge = min_edge
        self._max_size = max_size

    def generate_orders(self, ctx: StrategyContext) -> List[Order]:
        book: Dict[str, Market] = {m.market_id: m for m in ctx.markets}
        orders: List[Order] = []

        for a_id, b_id in self._pairs:
            a = book.get(a_id)
            b = book.get(b_id)
            if a is None or b is None or a.resolved or b.resolved:
                continue

            # If A's ask is well below B's bid, buy A and sell B.
            if b.best_bid - a.best_ask >= self._min_edge:
                size = self._size_for(a, b)
                if size > 0:
                    orders.append(Order(a_id, OrderSide.BUY, a.best_ask, size))
                    orders.append(Order(b_id, OrderSide.SELL, b.best_bid, size))
                continue

            if a.best_bid - b.best_ask >= self._min_edge:
                size = self._size_for(b, a)
                if size > 0:
                    orders.append(Order(b_id, OrderSide.BUY, b.best_ask, size))
                    orders.append(Order(a_id, OrderSide.SELL, a.best_bid, size))

        return orders

    def _size_for(self, cheap: Market, expensive: Market) -> float:
        """Cap by the shallower side of the book and the strategy's max."""
        liquidity_cap = min(cheap.liquidity, expensive.liquidity)
        if liquidity_cap <= 0:
            return self._max_size
        return min(self._max_size, liquidity_cap)
