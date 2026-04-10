"""Base class for trading strategies.

A strategy is a pure function of market state and portfolio state: given a
snapshot of the world, it returns a list of ``Order`` objects it would
like to place. The engine is responsible for routing those orders through
the risk manager and the client.

Keeping strategies side-effect free makes them trivial to unit-test — no
mocks, no time travel, just ``generate_orders(ctx)`` and assert on the
result.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import List, Sequence

from polymarket_bot.models import Market, Order
from polymarket_bot.portfolio import Portfolio


@dataclass
class StrategyContext:
    """Read-only snapshot passed to a strategy on every tick."""

    markets: Sequence[Market]
    portfolio: Portfolio
    now: float


class Strategy(abc.ABC):
    """Interface every trading strategy implements."""

    name: str = "strategy"

    @abc.abstractmethod
    def generate_orders(self, ctx: StrategyContext) -> List[Order]:
        """Return the orders the strategy would like to submit."""
