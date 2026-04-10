"""Pluggable trading strategies."""

from polymarket_bot.strategies.arbitrage import ArbitrageStrategy
from polymarket_bot.strategies.base import Strategy, StrategyContext
from polymarket_bot.strategies.event_driven import EventDrivenStrategy, NewsEvent
from polymarket_bot.strategies.market_making import MarketMakingStrategy

__all__ = [
    "ArbitrageStrategy",
    "EventDrivenStrategy",
    "MarketMakingStrategy",
    "NewsEvent",
    "Strategy",
    "StrategyContext",
]
