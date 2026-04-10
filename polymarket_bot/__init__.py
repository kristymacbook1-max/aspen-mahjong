"""Polymarket trading bot framework.

A pluggable, testable framework for automated trading on Polymarket-style
prediction markets. Ships with a paper-trading backend so strategies can be
developed and back-tested without real funds or network access.

Modules:
    models       -- Market, Order, Position, Trade dataclasses
    client       -- Abstract client + in-memory paper client
    portfolio    -- Position and PnL tracking
    risk         -- Risk manager with position limits and kill switch
    strategies   -- Arbitrage, market making, event-driven strategies
    engine       -- Main trading loop wiring it all together
    cli          -- Command-line entry point
"""

from polymarket_bot.models import Market, Order, OrderSide, Position, Trade
from polymarket_bot.portfolio import Portfolio
from polymarket_bot.risk import RiskLimits, RiskManager, RiskViolation

__all__ = [
    "Market",
    "Order",
    "OrderSide",
    "Portfolio",
    "Position",
    "RiskLimits",
    "RiskManager",
    "RiskViolation",
    "Trade",
]
