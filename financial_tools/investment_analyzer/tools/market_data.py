"""Market data fetcher with caching layer.

Wraps yfinance to pull stock prices, financials, and key metrics.
Caches results with a configurable TTL to respect API rate limits.
"""

import time
from dataclasses import dataclass, field
from typing import Optional

import yfinance as yf
import pandas as pd


@dataclass
class StockSnapshot:
    """Point-in-time snapshot of a stock's key data."""
    ticker: str
    company_name: str
    sector: str
    industry: str
    current_price: float
    market_cap: float
    pe_ratio: Optional[float]
    forward_pe: Optional[float]
    peg_ratio: Optional[float]
    price_to_book: Optional[float]
    dividend_yield: Optional[float]
    beta: Optional[float]
    fifty_two_week_high: float
    fifty_two_week_low: float
    avg_volume: int
    revenue_ttm: Optional[float]
    net_income_ttm: Optional[float]
    free_cash_flow: Optional[float]
    debt_to_equity: Optional[float]
    return_on_equity: Optional[float]
    profit_margin: Optional[float]
    revenue_growth: Optional[float]
    earnings_growth: Optional[float]
    recommendation: Optional[str]


@dataclass
class HistoricalData:
    """Historical price and volume data."""
    ticker: str
    period: str
    prices: pd.DataFrame  # columns: Open, High, Low, Close, Volume
    returns_1m: Optional[float] = None
    returns_3m: Optional[float] = None
    returns_6m: Optional[float] = None
    returns_1y: Optional[float] = None
    volatility_annualized: Optional[float] = None


@dataclass
class FinancialStatements:
    """Core financial statements."""
    ticker: str
    income_statement: Optional[pd.DataFrame] = None
    balance_sheet: Optional[pd.DataFrame] = None
    cash_flow: Optional[pd.DataFrame] = None


@dataclass
class _CacheEntry:
    data: object
    timestamp: float


class MarketDataFetcher:
    """Fetches and caches market data from Yahoo Finance.

    Args:
        cache_ttl: Cache time-to-live in seconds. Default 15 minutes.
    """

    def __init__(self, cache_ttl: int = 900):
        self.cache_ttl = cache_ttl
        self._cache: dict[str, _CacheEntry] = {}

    def _get_cached(self, key: str) -> Optional[object]:
        entry = self._cache.get(key)
        if entry and (time.time() - entry.timestamp) < self.cache_ttl:
            return entry.data
        return None

    def _set_cached(self, key: str, data: object) -> None:
        self._cache[key] = _CacheEntry(data=data, timestamp=time.time())

    def get_snapshot(self, ticker: str) -> StockSnapshot:
        """Get current stock snapshot with key metrics."""
        cache_key = f"snapshot:{ticker}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        stock = yf.Ticker(ticker)
        info = stock.info

        snapshot = StockSnapshot(
            ticker=ticker.upper(),
            company_name=info.get("longName", ticker),
            sector=info.get("sector", "Unknown"),
            industry=info.get("industry", "Unknown"),
            current_price=info.get("currentPrice", info.get("regularMarketPrice", 0.0)),
            market_cap=info.get("marketCap", 0),
            pe_ratio=info.get("trailingPE"),
            forward_pe=info.get("forwardPE"),
            peg_ratio=info.get("pegRatio"),
            price_to_book=info.get("priceToBook"),
            dividend_yield=info.get("dividendYield"),
            beta=info.get("beta"),
            fifty_two_week_high=info.get("fiftyTwoWeekHigh", 0.0),
            fifty_two_week_low=info.get("fiftyTwoWeekLow", 0.0),
            avg_volume=info.get("averageVolume", 0),
            revenue_ttm=info.get("totalRevenue"),
            net_income_ttm=info.get("netIncomeToCommon"),
            free_cash_flow=info.get("freeCashflow"),
            debt_to_equity=info.get("debtToEquity"),
            return_on_equity=info.get("returnOnEquity"),
            profit_margin=info.get("profitMargins"),
            revenue_growth=info.get("revenueGrowth"),
            earnings_growth=info.get("earningsGrowth"),
            recommendation=info.get("recommendationKey"),
        )

        self._set_cached(cache_key, snapshot)
        return snapshot

    def get_historical(self, ticker: str, period: str = "1y") -> HistoricalData:
        """Get historical price data and compute return metrics.

        Args:
            ticker: Stock ticker symbol.
            period: Data period - 1mo, 3mo, 6mo, 1y, 2y, 5y, max.
        """
        cache_key = f"historical:{ticker}:{period}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)

        if hist.empty:
            return HistoricalData(ticker=ticker, period=period, prices=hist)

        close = hist["Close"]
        daily_returns = close.pct_change().dropna()

        def _period_return(days: int) -> Optional[float]:
            if len(close) >= days:
                return (close.iloc[-1] / close.iloc[-days] - 1)
            return None

        result = HistoricalData(
            ticker=ticker.upper(),
            period=period,
            prices=hist,
            returns_1m=_period_return(21),
            returns_3m=_period_return(63),
            returns_6m=_period_return(126),
            returns_1y=_period_return(252),
            volatility_annualized=(
                float(daily_returns.std() * (252 ** 0.5)) if len(daily_returns) > 1 else None
            ),
        )

        self._set_cached(cache_key, result)
        return result

    def get_financials(self, ticker: str) -> FinancialStatements:
        """Get income statement, balance sheet, and cash flow statement."""
        cache_key = f"financials:{ticker}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        stock = yf.Ticker(ticker)

        result = FinancialStatements(
            ticker=ticker.upper(),
            income_statement=stock.income_stmt if not stock.income_stmt.empty else None,
            balance_sheet=stock.balance_sheet if not stock.balance_sheet.empty else None,
            cash_flow=stock.cashflow if not stock.cashflow.empty else None,
        )

        self._set_cached(cache_key, result)
        return result

    def get_peer_comparison(self, ticker: str, peers: Optional[list[str]] = None) -> list[StockSnapshot]:
        """Get snapshots for a stock and its peers for comparison.

        If peers not provided, attempts to infer from yfinance recommendations.
        """
        if peers is None:
            stock = yf.Ticker(ticker)
            try:
                recs = stock.recommendations
                if recs is not None and not recs.empty:
                    peers = []  # yfinance doesn't reliably provide peers
            except Exception:
                peers = []
            if not peers:
                peers = []

        all_tickers = [ticker] + peers
        return [self.get_snapshot(t) for t in all_tickers]

    def format_snapshot_text(self, snapshot: StockSnapshot) -> str:
        """Format a snapshot as readable text for LLM consumption."""
        def _fmt(val, fmt_type="number"):
            if val is None:
                return "N/A"
            if fmt_type == "currency":
                if abs(val) >= 1e12:
                    return f"${val/1e12:.2f}T"
                if abs(val) >= 1e9:
                    return f"${val/1e9:.2f}B"
                if abs(val) >= 1e6:
                    return f"${val/1e6:.2f}M"
                return f"${val:,.2f}"
            if fmt_type == "percent":
                return f"{val*100:.2f}%"
            if fmt_type == "ratio":
                return f"{val:.2f}"
            return f"{val:,.2f}"

        return f"""=== {snapshot.company_name} ({snapshot.ticker}) ===
Sector: {snapshot.sector} | Industry: {snapshot.industry}

PRICE DATA:
  Current Price: ${snapshot.current_price:,.2f}
  52-Week Range: ${snapshot.fifty_two_week_low:,.2f} - ${snapshot.fifty_two_week_high:,.2f}
  Market Cap: {_fmt(snapshot.market_cap, 'currency')}
  Avg Volume: {snapshot.avg_volume:,}

VALUATION:
  P/E (Trailing): {_fmt(snapshot.pe_ratio, 'ratio')}
  P/E (Forward): {_fmt(snapshot.forward_pe, 'ratio')}
  PEG Ratio: {_fmt(snapshot.peg_ratio, 'ratio')}
  Price/Book: {_fmt(snapshot.price_to_book, 'ratio')}

FUNDAMENTALS:
  Revenue (TTM): {_fmt(snapshot.revenue_ttm, 'currency')}
  Net Income (TTM): {_fmt(snapshot.net_income_ttm, 'currency')}
  Free Cash Flow: {_fmt(snapshot.free_cash_flow, 'currency')}
  Profit Margin: {_fmt(snapshot.profit_margin, 'percent')}
  ROE: {_fmt(snapshot.return_on_equity, 'percent')}
  Debt/Equity: {_fmt(snapshot.debt_to_equity, 'ratio')}

GROWTH:
  Revenue Growth: {_fmt(snapshot.revenue_growth, 'percent')}
  Earnings Growth: {_fmt(snapshot.earnings_growth, 'percent')}

RISK:
  Beta: {_fmt(snapshot.beta, 'ratio')}
  Dividend Yield: {_fmt(snapshot.dividend_yield, 'percent')}
  Analyst Consensus: {snapshot.recommendation or 'N/A'}
"""

    def format_historical_text(self, hist: HistoricalData) -> str:
        """Format historical data as readable text for LLM consumption."""
        def _fmt_ret(val):
            return f"{val*100:+.2f}%" if val is not None else "N/A"

        return f"""=== Historical Performance ({hist.ticker}, {hist.period}) ===
  1-Month Return: {_fmt_ret(hist.returns_1m)}
  3-Month Return: {_fmt_ret(hist.returns_3m)}
  6-Month Return: {_fmt_ret(hist.returns_6m)}
  1-Year Return: {_fmt_ret(hist.returns_1y)}
  Annualized Volatility: {_fmt_ret(hist.volatility_annualized) if hist.volatility_annualized else 'N/A'}
  Data Points: {len(hist.prices)} trading days
"""
