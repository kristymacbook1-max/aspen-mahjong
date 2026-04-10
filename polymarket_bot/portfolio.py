"""Portfolio and cash accounting.

The portfolio is the single source of truth for positions, cash, and
realized PnL. Strategies read from it to decide on new orders; the engine
writes to it whenever the client reports a fill.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping

from polymarket_bot.models import Market, OrderSide, Position, Trade


@dataclass
class Portfolio:
    """Cash + open positions, with deterministic PnL accounting.

    ``cash`` is decremented on BUY fills and incremented on SELL fills.
    Resolution is modeled by calling ``settle_market`` once the market
    reports a final outcome.
    """

    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)
    trades: List[Trade] = field(default_factory=list)

    def position(self, market_id: str) -> Position:
        return self.positions.setdefault(market_id, Position(market_id))

    def apply_trade(self, trade: Trade) -> None:
        """Apply a fill: update cash, position, and the trade log."""
        self.trades.append(trade)
        if trade.side is OrderSide.BUY:
            self.cash -= trade.notional
        else:
            self.cash += trade.notional
        self.position(trade.market_id).apply_trade(trade)

    def settle_market(self, market: Market) -> float:
        """Collect winnings on a resolved market.

        Returns the cash delta. The position is zeroed and its realized
        PnL is booked against the opening VWAP so that total PnL
        (realized + unrealized) is conserved across settlement.
        """
        if not market.resolved or market.outcome is None:
            raise ValueError(f"market {market.market_id} is not resolved")

        pos = self.positions.get(market.market_id)
        if pos is None or pos.shares == 0:
            return 0.0

        payout = pos.shares * market.outcome  # outcome is 0.0 or 1.0
        self.cash += payout
        pos.realized_pnl += (market.outcome - pos.avg_price) * pos.shares
        pos.shares = 0.0
        pos.avg_price = 0.0
        return payout

    # ---- reporting ---------------------------------------------------

    def equity(self, marks: Mapping[str, float]) -> float:
        """Total account value: cash plus mark-to-market of open positions."""
        mtm = 0.0
        for mid, pos in self.positions.items():
            if pos.shares == 0:
                continue
            mark = marks.get(mid)
            if mark is None:
                continue
            mtm += pos.shares * mark
        return self.cash + mtm

    def realized_pnl(self) -> float:
        return sum(p.realized_pnl for p in self.positions.values())

    def unrealized_pnl(self, marks: Mapping[str, float]) -> float:
        total = 0.0
        for mid, pos in self.positions.items():
            mark = marks.get(mid)
            if mark is None:
                continue
            total += pos.unrealized_pnl(mark)
        return total

    def open_positions(self) -> Iterable[Position]:
        return (p for p in self.positions.values() if p.shares != 0)
