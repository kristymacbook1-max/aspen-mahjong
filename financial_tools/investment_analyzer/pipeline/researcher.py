"""Research stage - gathers all raw data for analysis.

This is the data ingestion layer. It pulls market data, financials,
historical prices, and news sentiment, then packages everything into
a structured research bundle for the Analyst stage.
"""

from dataclasses import dataclass, field
from typing import Optional

from ..tools.market_data import (
    MarketDataFetcher,
    StockSnapshot,
    HistoricalData,
    FinancialStatements,
)
from ..tools.news_sentiment import NewsSentimentFetcher, NewsSentimentResult


@dataclass
class ResearchBundle:
    """All raw data collected for a single ticker."""
    ticker: str
    snapshot: Optional[StockSnapshot] = None
    historical: Optional[HistoricalData] = None
    financials: Optional[FinancialStatements] = None
    news_sentiment: Optional[NewsSentimentResult] = None
    sec_filings: str = ""
    peer_snapshots: list[StockSnapshot] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class ResearchStage:
    """Gathers comprehensive market data for analysis.

    Args:
        market_fetcher: MarketDataFetcher instance (shared for caching).
        news_fetcher: NewsSentimentFetcher instance.
    """

    def __init__(
        self,
        market_fetcher: Optional[MarketDataFetcher] = None,
        news_fetcher: Optional[NewsSentimentFetcher] = None,
    ):
        self.market = market_fetcher or MarketDataFetcher()
        self.news = news_fetcher or NewsSentimentFetcher()

    def research(
        self,
        ticker: str,
        peers: Optional[list[str]] = None,
        include_news: bool = True,
        include_sec: bool = True,
        historical_period: str = "1y",
    ) -> ResearchBundle:
        """Run full research pipeline for a ticker.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL").
            peers: Optional list of peer tickers for comparison.
            include_news: Whether to fetch news sentiment.
            include_sec: Whether to fetch SEC filing data.
            historical_period: Period for historical data.

        Returns:
            ResearchBundle with all collected data.
        """
        bundle = ResearchBundle(ticker=ticker.upper())

        # Snapshot (current metrics)
        try:
            bundle.snapshot = self.market.get_snapshot(ticker)
        except Exception as e:
            bundle.errors.append(f"Snapshot fetch failed: {e}")

        # Historical price data
        try:
            bundle.historical = self.market.get_historical(ticker, historical_period)
        except Exception as e:
            bundle.errors.append(f"Historical data fetch failed: {e}")

        # Financial statements
        try:
            bundle.financials = self.market.get_financials(ticker)
        except Exception as e:
            bundle.errors.append(f"Financials fetch failed: {e}")

        # News sentiment
        if include_news:
            try:
                bundle.news_sentiment = self.news.get_news_sentiment(ticker)
            except Exception as e:
                bundle.errors.append(f"News sentiment fetch failed: {e}")

        # SEC filings
        if include_sec:
            try:
                bundle.sec_filings = self.news.get_sec_filings_summary(ticker)
            except Exception as e:
                bundle.errors.append(f"SEC filings fetch failed: {e}")

        # Peer comparison
        if peers:
            try:
                bundle.peer_snapshots = [
                    self.market.get_snapshot(p) for p in peers
                ]
            except Exception as e:
                bundle.errors.append(f"Peer comparison fetch failed: {e}")

        return bundle

    def format_research_text(self, bundle: ResearchBundle) -> str:
        """Format entire research bundle as text for LLM consumption."""
        sections = []

        if bundle.snapshot:
            sections.append(self.market.format_snapshot_text(bundle.snapshot))

        if bundle.historical:
            sections.append(self.market.format_historical_text(bundle.historical))

        if bundle.financials:
            fin = bundle.financials
            sections.append(f"=== Financial Statements ({bundle.ticker}) ===")
            if fin.income_statement is not None:
                sections.append("Income Statement (most recent periods):")
                sections.append(fin.income_statement.to_string())
                sections.append("")
            if fin.balance_sheet is not None:
                sections.append("Balance Sheet (most recent periods):")
                sections.append(fin.balance_sheet.to_string())
                sections.append("")
            if fin.cash_flow is not None:
                sections.append("Cash Flow Statement (most recent periods):")
                sections.append(fin.cash_flow.to_string())
                sections.append("")

        if bundle.news_sentiment:
            sections.append(self.news.format_news_text(bundle.news_sentiment))

        if bundle.sec_filings:
            sections.append(f"=== Recent SEC Filings ({bundle.ticker}) ===")
            sections.append(bundle.sec_filings)
            sections.append("")

        if bundle.peer_snapshots:
            sections.append("=== Peer Comparison ===")
            for peer in bundle.peer_snapshots:
                sections.append(self.market.format_snapshot_text(peer))

        if bundle.errors:
            sections.append("=== Data Collection Warnings ===")
            for err in bundle.errors:
                sections.append(f"  - {err}")

        return "\n".join(sections)
