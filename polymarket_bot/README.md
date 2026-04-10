# polymarket_bot

A pluggable, testable Polymarket trading bot framework. Ships with a
paper-trading backend so you can develop and backtest strategies without
real funds or network access.

## Layout

```
polymarket_bot/
  models.py          Market, Order, Position, Trade dataclasses
  client.py          Abstract MarketClient + in-memory PaperClient
  portfolio.py       Cash and position accounting, PnL, settlement
  risk.py            Position/notional caps and drawdown kill switch
  strategies/
    base.py          Strategy interface
    arbitrage.py     Cross-venue price-gap arbitrage
    market_making.py Two-sided quoter with inventory skew
    event_driven.py  News/event driven taker
  engine.py          Ties client + strategies + risk + portfolio together
  cli.py             Paper-trading demo (python -m polymarket_bot.cli)
  tests/             Unit tests (stdlib unittest, no deps)
```

## Running the demo

```
python -m polymarket_bot.cli --ticks 3 --verbose
```

The demo seeds three synthetic markets and wires up all three strategies
so you can see the full pipeline (strategies -> risk -> client -> portfolio)
execute end-to-end on every tick.

## Running the tests

```
python -m unittest discover -s polymarket_bot/tests -t .
```

The test suite uses only the standard library, so no `pip install` is
required.

## Writing a strategy

```python
from polymarket_bot.models import Order, OrderSide
from polymarket_bot.strategies.base import Strategy, StrategyContext


class BuyTheDip(Strategy):
    name = "buy_the_dip"

    def generate_orders(self, ctx: StrategyContext):
        orders = []
        for market in ctx.markets:
            if market.resolved:
                continue
            if market.best_ask < 0.20:
                orders.append(Order(market.market_id, OrderSide.BUY, market.best_ask, 10))
        return orders
```

Strategies are pure functions of the context — no IO, no state
required — which makes them trivial to unit-test.

## Plugging in a real Polymarket client

The engine depends only on the `MarketClient` abstract interface in
`client.py`. To trade live, implement a subclass that wraps
`py-clob-client` (or whichever SDK you prefer), plug it into the engine in
place of `PaperClient`, and everything else — strategies, risk, portfolio
accounting — works unchanged.

## Safety defaults

The bot is conservative by default:

- Paper trading only; the CLI never talks to Polymarket.
- Every order is routed through the risk manager, which caps:
  - single-order notional,
  - per-market exposure,
  - total gross exposure,
  - cash reserve (floor on available cash),
  - and a drawdown kill switch that halts new orders if equity falls
    more than 25% from its peak.

These defaults are deliberately tight — tune `RiskLimits` to your
appetite before running anywhere real, and always start with paper
trading.
