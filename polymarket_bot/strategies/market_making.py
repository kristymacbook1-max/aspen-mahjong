"""Market making strategy.

A market maker earns the spread by quoting both sides. This implementation
centers its quotes on the book midpoint and steps inside the current
spread by ``edge``, creating a two-sided quote that earns roughly
``2 * edge`` per round-trip when both legs fill.

Inventory control is handled by skewing the midpoint: when the bot is
long, it quotes lower (making its ask cheaper) to encourage selling and
vice versa. The skew magnitude is capped by ``max_skew``.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence

from polymarket_bot.models import Market, Order, OrderSide
from polymarket_bot.strategies.base import Strategy, StrategyContext


class MarketMakingStrategy(Strategy):
    """Symmetric two-sided quoter with inventory skew."""

    name = "market_making"

    def __init__(
        self,
        market_ids: Sequence[str],
        edge: float = 0.01,
        quote_size: float = 50.0,
        max_inventory: float = 200.0,
        max_skew: float = 0.03,
    ) -> None:
        if edge <= 0:
            raise ValueError("edge must be positive")
        if quote_size <= 0:
            raise ValueError("quote_size must be positive")
        if max_inventory <= 0:
            raise ValueError("max_inventory must be positive")
        self._market_ids = list(market_ids)
        self._edge = edge
        self._quote_size = quote_size
        self._max_inventory = max_inventory
        self._max_skew = max_skew

    def generate_orders(self, ctx: StrategyContext) -> List[Order]:
        wanted: Iterable[Market] = (
            m for m in ctx.markets if m.market_id in self._market_ids and not m.resolved
        )
        orders: List[Order] = []

        for m in wanted:
            # Our quoted spread would be 2*edge. If the book is already
            # tighter than that, passive quotes would sit behind the
            # existing market and never fill — skip it.
            if m.spread < 2 * self._edge:
                continue

            pos = ctx.portfolio.position(m.market_id)
            skew = self._inventory_skew(pos.shares)
            center = _clip(m.mid - skew, 0.01, 0.99)

            bid_price = round(_clip(center - self._edge, 0.01, 0.99), 3)
            ask_price = round(_clip(center + self._edge, 0.01, 0.99), 3)
            if ask_price <= bid_price:
                continue

            # Do not cross the existing book — that would be a taker trade.
            if bid_price >= m.best_ask or ask_price <= m.best_bid:
                continue

            orders.append(Order(m.market_id, OrderSide.BUY, bid_price, self._quote_size))
            orders.append(Order(m.market_id, OrderSide.SELL, ask_price, self._quote_size))

        return orders

    def _inventory_skew(self, shares: float) -> float:
        """Linear skew clamped at ``max_skew``."""
        if self._max_inventory == 0:
            return 0.0
        ratio = max(-1.0, min(1.0, shares / self._max_inventory))
        return ratio * self._max_skew


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))
