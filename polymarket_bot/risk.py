"""Risk management.

Every order a strategy wants to place is routed through the risk manager,
which can reject it, shrink it, or trip a global kill switch. The goal is
to cap the blast radius of a strategy bug or a bad market tick — the
"long-tail" failure mode that liquidates the naive predictive agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from polymarket_bot.models import Order, OrderSide
from polymarket_bot.portfolio import Portfolio


class RiskViolation(Exception):
    """Raised when an order cannot be sized down to fit the risk envelope."""


@dataclass(frozen=True)
class RiskLimits:
    """Hard risk parameters. All values are inclusive upper bounds.

    Attributes:
        max_order_notional: Largest $ cost of a single order.
        max_position_notional: Largest $ exposure in one market.
        max_gross_notional: Sum of absolute $ exposure across all markets.
        min_cash_reserve: Floor on cash; BUYs that would breach this are
            rejected so the bot always has money to cover fees and losses.
        max_drawdown_pct: Global kill switch. When equity drops by more
            than this fraction of its peak, all new orders are blocked.
    """

    max_order_notional: float = 500.0
    max_position_notional: float = 2_000.0
    max_gross_notional: float = 10_000.0
    min_cash_reserve: float = 0.0
    max_drawdown_pct: float = 0.25


@dataclass
class RiskManager:
    """Stateful risk checks against a ``Portfolio``.

    The manager tracks peak equity internally so the drawdown check is
    path-dependent: a bot that made $500 and gave back $125 is at the
    25% drawdown limit even if its nominal equity is still above the
    starting balance.
    """

    limits: RiskLimits
    portfolio: Portfolio
    _peak_equity: Optional[float] = None
    _halted: bool = False

    def mark(self, equity: float) -> None:
        """Update peak equity and trip the kill switch if needed."""
        if self._peak_equity is None or equity > self._peak_equity:
            self._peak_equity = equity
        if self._peak_equity <= 0:
            return
        drawdown = 1.0 - (equity / self._peak_equity)
        if drawdown >= self.limits.max_drawdown_pct:
            self._halted = True

    @property
    def halted(self) -> bool:
        return self._halted

    def reset_halt(self) -> None:
        """Manual override. Use sparingly — drawdown halts exist for a reason."""
        self._halted = False
        self._peak_equity = None

    def check(self, order: Order) -> Order:
        """Return an order sized to fit the risk envelope.

        Raises ``RiskViolation`` if the order cannot be shrunk to a
        non-trivial size (for example, because the kill switch is tripped
        or the market already holds the full position limit).
        """
        if self._halted:
            raise RiskViolation("risk kill switch is tripped")

        max_size = order.size

        # 1. Single-order notional cap.
        if order.notional > self.limits.max_order_notional:
            max_size = min(max_size, self.limits.max_order_notional / order.price)

        # 2. Per-market position cap.
        pos = self.portfolio.position(order.market_id)
        current_notional = abs(pos.shares) * order.price
        same_side = (
            (order.side is OrderSide.BUY and pos.shares >= 0)
            or (order.side is OrderSide.SELL and pos.shares <= 0)
        )
        if same_side:
            headroom = self.limits.max_position_notional - current_notional
            if headroom <= 0:
                raise RiskViolation(
                    f"position cap reached for {order.market_id}"
                )
            max_size = min(max_size, headroom / order.price)

        # 3. Gross portfolio exposure cap.
        gross = sum(
            abs(p.shares) * order.price  # approximate: use order price as mark
            for p in self.portfolio.positions.values()
            if p.market_id != order.market_id
        ) + current_notional
        if same_side:
            gross_headroom = self.limits.max_gross_notional - gross
            if gross_headroom <= 0:
                raise RiskViolation("gross exposure cap reached")
            max_size = min(max_size, gross_headroom / order.price)

        # 4. Cash reserve for BUY orders.
        if order.side is OrderSide.BUY:
            spendable = self.portfolio.cash - self.limits.min_cash_reserve
            if spendable <= 0:
                raise RiskViolation("cash reserve would be breached")
            max_size = min(max_size, spendable / order.price)

        if max_size <= 0:
            raise RiskViolation("risk check produced non-positive size")

        # Round to 4 decimals to avoid floating-point dust orders.
        sized = round(min(order.size, max_size), 4)
        if sized <= 0:
            raise RiskViolation("sized order collapsed to zero")

        if sized == order.size:
            return order
        return Order(
            market_id=order.market_id,
            side=order.side,
            price=order.price,
            size=sized,
        )
