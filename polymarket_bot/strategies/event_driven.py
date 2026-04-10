"""Event-driven strategy.

Consumes a queue of ``NewsEvent`` objects (classified by an upstream
feed, e.g. an LLM pipeline reading wires and social media) and reacts by
moving the bot's fair value for affected markets. When the fair value is
sufficiently far from the current book, the strategy takes liquidity.

This module is intentionally transport-agnostic: wire it up to a real
news feed, a webhook, or a tick replayer in a backtest. The strategy
itself only sees a list of events per tick.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Deque, Dict, List, Sequence
from collections import deque

from polymarket_bot.models import Order, OrderSide
from polymarket_bot.strategies.base import Strategy, StrategyContext


@dataclass(frozen=True)
class NewsEvent:
    """A single classified headline.

    Attributes:
        market_id: Which market this event bears on.
        impact: Signed value in [-1.0, 1.0]; positive pushes YES up.
        confidence: Feed's self-reported confidence in [0.0, 1.0].
        timestamp: Unix seconds at which the event was observed.
    """

    market_id: str
    impact: float
    confidence: float
    timestamp: float


class EventDrivenStrategy(Strategy):
    """Take the book when news implies a large mispricing.

    The strategy maintains a fair-value estimate per market, seeded from
    the book midpoint. Each news event nudges fair value by
    ``impact * confidence * sensitivity``, clamped to (0, 1). When the
    book crosses the fair value by more than ``threshold``, the strategy
    places a marketable order.
    """

    name = "event_driven"

    def __init__(
        self,
        sensitivity: float = 0.1,
        threshold: float = 0.03,
        order_size: float = 50.0,
    ) -> None:
        if not 0 < sensitivity <= 1.0:
            raise ValueError("sensitivity must be in (0,1]")
        if threshold <= 0:
            raise ValueError("threshold must be positive")
        self._sensitivity = sensitivity
        self._threshold = threshold
        self._order_size = order_size
        self._fair_value: Dict[str, float] = {}
        self._pending: Deque[NewsEvent] = deque()

    def ingest(self, events: Sequence[NewsEvent]) -> None:
        """Queue events to be consumed on the next ``generate_orders`` call."""
        self._pending.extend(events)

    def fair_value(self, market_id: str) -> float | None:
        return self._fair_value.get(market_id)

    def generate_orders(self, ctx: StrategyContext) -> List[Order]:
        # Bucket pending events by market so we apply them in one pass.
        bucket: Dict[str, List[NewsEvent]] = defaultdict(list)
        while self._pending:
            ev = self._pending.popleft()
            bucket[ev.market_id].append(ev)

        market_index = {m.market_id: m for m in ctx.markets}
        orders: List[Order] = []

        # Seed fair values for any markets we haven't tracked yet.
        for m in ctx.markets:
            self._fair_value.setdefault(m.market_id, m.mid)

        for mid, events in bucket.items():
            market = market_index.get(mid)
            if market is None or market.resolved:
                continue
            fv = self._fair_value[mid]
            for ev in events:
                fv = _clip(
                    fv + ev.impact * ev.confidence * self._sensitivity,
                    0.01,
                    0.99,
                )
            self._fair_value[mid] = fv

        # Emit orders wherever the book is far enough from fair value.
        for mid, fv in self._fair_value.items():
            market = market_index.get(mid)
            if market is None or market.resolved:
                continue
            if fv - market.best_ask >= self._threshold:
                orders.append(
                    Order(mid, OrderSide.BUY, market.best_ask, self._order_size)
                )
            elif market.best_bid - fv >= self._threshold:
                orders.append(
                    Order(mid, OrderSide.SELL, market.best_bid, self._order_size)
                )

        return orders


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))
