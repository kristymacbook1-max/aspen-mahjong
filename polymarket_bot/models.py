"""Core data models for the Polymarket trading bot.

Polymarket binary markets resolve to YES (1.0) or NO (0.0). Prices trade
between 0 and 1 and can be read as implied probabilities. A fill at 0.30
followed by a YES resolution pays out at 1.00, so the trader earns 0.70 per
share; the same fill under a NO resolution loses 0.30 per share.
"""

from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


class OrderSide(enum.Enum):
    """Side of a limit order.

    BUY takes the ask and is long the outcome. SELL takes the bid and is
    short. On a YES/NO market, a SELL of YES is economically equivalent to
    a BUY of NO at (1 - price).
    """

    BUY = "buy"
    SELL = "sell"


class OrderStatus(enum.Enum):
    OPEN = "open"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELED = "canceled"
    REJECTED = "rejected"


@dataclass(frozen=True)
class Market:
    """A binary prediction market.

    Attributes:
        market_id: Stable identifier (condition id on Polymarket).
        question: Human-readable question, e.g. "Will X happen by Y?".
        best_bid: Highest price someone will pay for YES (0 < bid < ask < 1).
        best_ask: Lowest price someone will sell YES for.
        last_price: Most recent trade price, or None if untraded.
        resolved: True once the market has settled.
        outcome: 1.0 for YES, 0.0 for NO, None if unresolved.
        liquidity: Total $ of quoted size on the book (used for sizing).
    """

    market_id: str
    question: str
    best_bid: float
    best_ask: float
    last_price: Optional[float] = None
    resolved: bool = False
    outcome: Optional[float] = None
    liquidity: float = 0.0

    def __post_init__(self) -> None:
        if not (0.0 <= self.best_bid <= self.best_ask <= 1.0):
            raise ValueError(
                f"invalid book for {self.market_id}: "
                f"bid={self.best_bid} ask={self.best_ask}"
            )
        if self.resolved and self.outcome not in (0.0, 1.0):
            raise ValueError(
                f"resolved market {self.market_id} must have outcome 0.0 or 1.0"
            )

    @property
    def mid(self) -> float:
        """Midpoint of the current book."""
        return (self.best_bid + self.best_ask) / 2.0

    @property
    def spread(self) -> float:
        return self.best_ask - self.best_bid


@dataclass
class Order:
    """A limit order resting on (or recently submitted to) the book."""

    market_id: str
    side: OrderSide
    price: float
    size: float
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: OrderStatus = OrderStatus.OPEN
    filled_size: float = 0.0
    created_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not 0.0 < self.price < 1.0:
            raise ValueError(f"order price must be in (0,1), got {self.price}")
        if self.size <= 0:
            raise ValueError(f"order size must be positive, got {self.size}")

    @property
    def remaining(self) -> float:
        return max(0.0, self.size - self.filled_size)

    @property
    def notional(self) -> float:
        """Dollar cost at the limit price for the full order size."""
        return self.price * self.size


@dataclass(frozen=True)
class Trade:
    """A completed fill. Trades are append-only audit records."""

    market_id: str
    side: OrderSide
    price: float
    size: float
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)

    @property
    def notional(self) -> float:
        return self.price * self.size

    @property
    def signed_size(self) -> float:
        """Positive for BUY, negative for SELL."""
        return self.size if self.side is OrderSide.BUY else -self.size


@dataclass
class Position:
    """Aggregated position in one market.

    Tracks net shares (can be negative for shorts) and the VWAP of the
    current exposure. Realized PnL accumulates as positions are closed or
    reduced; unrealized PnL is computed on demand against a mark price.
    """

    market_id: str
    shares: float = 0.0
    avg_price: float = 0.0
    realized_pnl: float = 0.0

    def apply_trade(self, trade: Trade) -> None:
        """Update the position for a new fill.

        If the trade adds to the existing side, we update the VWAP.
        If it reduces or flips, we realize PnL on the closed portion.
        """
        if trade.market_id != self.market_id:
            raise ValueError(
                f"trade market {trade.market_id} does not match position "
                f"{self.market_id}"
            )

        delta = trade.signed_size
        # Same direction (or opening from flat): update the VWAP.
        if self.shares == 0 or (self.shares > 0) == (delta > 0):
            new_shares = self.shares + delta
            if new_shares == 0:
                self.avg_price = 0.0
            else:
                self.avg_price = (
                    self.avg_price * self.shares + trade.price * delta
                ) / new_shares
            self.shares = new_shares
            return

        # Opposite direction: realize PnL on the closed portion.
        closing = min(abs(delta), abs(self.shares))
        if self.shares > 0:
            # Long being reduced by a SELL at trade.price.
            self.realized_pnl += (trade.price - self.avg_price) * closing
        else:
            # Short being reduced by a BUY at trade.price.
            self.realized_pnl += (self.avg_price - trade.price) * closing

        new_shares = self.shares + delta
        if new_shares == 0:
            self.shares = 0.0
            self.avg_price = 0.0
        elif (new_shares > 0) == (self.shares > 0):
            # Position reduced but not flipped.
            self.shares = new_shares
        else:
            # Position flipped past zero; the leftover opens a new position
            # at the trade price.
            self.shares = new_shares
            self.avg_price = trade.price

    def unrealized_pnl(self, mark_price: float) -> float:
        """Mark-to-market PnL on the open portion of the position."""
        if self.shares == 0:
            return 0.0
        return (mark_price - self.avg_price) * self.shares

    def notional(self, mark_price: float) -> float:
        """Absolute dollar exposure at the mark price."""
        return abs(self.shares) * mark_price
