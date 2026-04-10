"""Command-line entry point.

Runs a small paper-trading demo against a synthetic market so you can
verify the full pipeline (strategies → risk → client → portfolio) without
network access or Polymarket credentials.

Usage:
    python -m polymarket_bot.cli            # single tick
    python -m polymarket_bot.cli --ticks 5  # run for 5 ticks
"""

from __future__ import annotations

import argparse
import logging
import sys

from polymarket_bot.client import PaperClient
from polymarket_bot.engine import Engine
from polymarket_bot.models import Market
from polymarket_bot.portfolio import Portfolio
from polymarket_bot.risk import RiskLimits, RiskManager
from polymarket_bot.strategies import (
    ArbitrageStrategy,
    EventDrivenStrategy,
    MarketMakingStrategy,
    NewsEvent,
)


def build_demo_engine() -> tuple[Engine, PaperClient, EventDrivenStrategy]:
    client = PaperClient()
    client.seed(
        [
            Market("POLY-A", "Will X happen?", best_bid=0.48, best_ask=0.50, liquidity=500),
            Market("ALT-A", "Will X happen? (alt venue)", best_bid=0.53, best_ask=0.55, liquidity=500),
            Market("POLY-B", "Will Y happen?", best_bid=0.40, best_ask=0.42, liquidity=500),
        ]
    )
    portfolio = Portfolio(cash=10_000.0)
    risk = RiskManager(
        limits=RiskLimits(
            max_order_notional=500,
            max_position_notional=2_000,
            max_gross_notional=10_000,
            min_cash_reserve=100,
            max_drawdown_pct=0.25,
        ),
        portfolio=portfolio,
    )
    event_strategy = EventDrivenStrategy(sensitivity=0.2, threshold=0.03, order_size=40)
    engine = Engine(
        client=client,
        portfolio=portfolio,
        risk=risk,
        strategies=[
            ArbitrageStrategy(pairs=[("POLY-A", "ALT-A")], min_edge=0.02, max_size=40),
            MarketMakingStrategy(market_ids=["POLY-B"], edge=0.01, quote_size=20),
            event_strategy,
        ],
    )
    return engine, client, event_strategy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Polymarket paper-trading demo")
    parser.add_argument("--ticks", type=int, default=1, help="Number of engine ticks to run")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable debug logging"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    engine, _client, event_strategy = build_demo_engine()

    # Inject a news event so the event-driven strategy has something to do.
    event_strategy.ingest(
        [NewsEvent(market_id="POLY-B", impact=0.8, confidence=0.9, timestamp=0.0)]
    )

    for i in range(args.ticks):
        report = engine.tick()
        print(
            f"tick {i + 1}: proposed={report.proposed} submitted={report.submitted} "
            f"rejected={report.rejected} fills={len(report.fills)} "
            f"equity={report.equity:.2f} halted={report.halted}"
        )
        for trade in report.fills:
            print(f"  fill: {trade.side.value} {trade.size} @ {trade.price} [{trade.market_id}]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
