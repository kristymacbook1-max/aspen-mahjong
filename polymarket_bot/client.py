"""Market data and order execution clients.

The bot code depends only on the abstract ``MarketClient`` interface. A
production deployment plugs in a real Polymarket CLOB client; tests and
paper trading use ``PaperClient``, which keeps all state in memory and
matches orders against the public book.

This separation keeps the strategy, portfolio, and risk layers network-free
and deterministic under test.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from polymarket_bot.models import Market, Order, OrderSide, OrderStatus, Trade


class MarketClient(abc.ABC):
    """Abstract interface for reading market data and placing orders."""

    @abc.abstractmethod
    def list_markets(self) -> List[Market]:
        """Return all markets the client currently knows about."""

    @abc.abstractmethod
    def get_market(self, market_id: str) -> Market:
        """Return the current snapshot for one market."""

    @abc.abstractmethod
    def place_order(self, order: Order) -> Order:
        """Submit ``order`` and return it (possibly with fills applied)."""

    @abc.abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a resting order. Returns True if the order was live."""

    @abc.abstractmethod
    def fills_since(self, cursor: float) -> List[Trade]:
        """Return trades that occurred at-or-after ``cursor`` (unix secs)."""


@dataclass
class PaperClient(MarketClient):
    """In-memory matching engine for paper trading and tests.

    The client treats the quoted book as infinitely deep: a BUY that crosses
    the ask fills at the ask, a SELL that crosses the bid fills at the bid.
    Non-crossing orders rest in an internal book but are never matched
    against each other, which is a reasonable simplification for most
    prediction-market liquidity profiles.
    """

    markets: Dict[str, Market] = field(default_factory=dict)
    resting: Dict[str, Order] = field(default_factory=dict)
    history: List[Trade] = field(default_factory=list)

    # ---- setup helpers -----------------------------------------------

    def seed(self, markets: Iterable[Market]) -> None:
        for m in markets:
            self.markets[m.market_id] = m

    def update_market(self, market: Market) -> None:
        self.markets[market.market_id] = market

    def resolve_market(self, market_id: str, outcome: float) -> None:
        """Mark a market resolved; strategies can then collect winnings."""
        prior = self.markets[market_id]
        self.markets[market_id] = Market(
            market_id=prior.market_id,
            question=prior.question,
            best_bid=prior.best_bid,
            best_ask=prior.best_ask,
            last_price=outcome,
            resolved=True,
            outcome=outcome,
            liquidity=prior.liquidity,
        )

    # ---- MarketClient interface --------------------------------------

    def list_markets(self) -> List[Market]:
        return list(self.markets.values())

    def get_market(self, market_id: str) -> Market:
        return self.markets[market_id]

    def place_order(self, order: Order) -> Order:
        market = self.markets.get(order.market_id)
        if market is None or market.resolved:
            order.status = OrderStatus.REJECTED
            return order

        crosses = (
            order.side is OrderSide.BUY and order.price >= market.best_ask
        ) or (
            order.side is OrderSide.SELL and order.price <= market.best_bid
        )

        if not crosses:
            self.resting[order.order_id] = order
            return order

        fill_price = (
            market.best_ask if order.side is OrderSide.BUY else market.best_bid
        )
        trade = Trade(
            market_id=order.market_id,
            side=order.side,
            price=fill_price,
            size=order.size,
        )
        self.history.append(trade)
        order.filled_size = order.size
        order.status = OrderStatus.FILLED
        return order

    def cancel_order(self, order_id: str) -> bool:
        order = self.resting.pop(order_id, None)
        if order is None:
            return False
        order.status = OrderStatus.CANCELED
        return True

    def fills_since(self, cursor: float) -> List[Trade]:
        return [t for t in self.history if t.timestamp >= cursor]

    # ---- paper-only helpers ------------------------------------------

    def last_trade(self) -> Optional[Trade]:
        return self.history[-1] if self.history else None
