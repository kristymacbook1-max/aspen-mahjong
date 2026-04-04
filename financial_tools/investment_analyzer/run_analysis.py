"""Main entry point for running investment analysis.

Usage:
    from financial_tools.investment_analyzer.run_analysis import InvestmentAnalyzerPipeline

    # Analyze a single stock
    pipeline = InvestmentAnalyzerPipeline()
    proposal = pipeline.analyze_stock("AAPL")
    print(proposal)

    # Analyze with peer comparison
    proposal = pipeline.analyze_stock("AAPL", peers=["MSFT", "GOOGL"])

    # Analyze multiple stocks (portfolio-level)
    proposals = pipeline.analyze_portfolio(["AAPL", "MSFT", "GOOGL"])

    # Save proposals to files
    pipeline.analyze_and_save("AAPL", output_dir="output")
"""

import os
import json
from datetime import datetime
from typing import Optional

from .tools.market_data import MarketDataFetcher
from .tools.news_sentiment import NewsSentimentFetcher
from .pipeline.researcher import ResearchStage, ResearchBundle
from .pipeline.analyst import AnalystStage, AnalysisResult
from .pipeline.writer import WriterStage


class InvestmentAnalyzerPipeline:
    """Orchestrates the full investment analysis pipeline.

    Three-stage pipeline: Research → Analyze → Write

    Args:
        anthropic_api_key: API key for Claude. Falls back to ANTHROPIC_API_KEY env var.
        alpha_vantage_key: API key for news data. Falls back to ALPHA_VANTAGE_API_KEY env var.
        model: Claude model to use for analysis and writing.
        cache_ttl: Cache TTL in seconds for market data.
        use_static_writer: If True, skip LLM call for proposal writing (saves API credits).
    """

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        alpha_vantage_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        cache_ttl: int = 900,
        use_static_writer: bool = False,
    ):
        self.market_fetcher = MarketDataFetcher(cache_ttl=cache_ttl)
        self.news_fetcher = NewsSentimentFetcher(alpha_vantage_key=alpha_vantage_key)

        self.research_stage = ResearchStage(
            market_fetcher=self.market_fetcher,
            news_fetcher=self.news_fetcher,
        )
        self.analyst_stage = AnalystStage(
            api_key=anthropic_api_key,
            model=model,
            research_stage=self.research_stage,
        )
        self.writer_stage = WriterStage(
            api_key=anthropic_api_key,
            model=model,
        )
        self.use_static_writer = use_static_writer

    def research(
        self,
        ticker: str,
        peers: Optional[list[str]] = None,
    ) -> ResearchBundle:
        """Run only the research stage (data gathering).

        Args:
            ticker: Stock ticker symbol.
            peers: Optional list of peer tickers.

        Returns:
            ResearchBundle with all collected data.
        """
        return self.research_stage.research(ticker, peers=peers)

    def analyze(self, bundle: ResearchBundle) -> AnalysisResult:
        """Run only the analysis stage on existing research.

        Args:
            bundle: ResearchBundle from research stage.

        Returns:
            AnalysisResult with structured analysis.
        """
        return self.analyst_stage.analyze(bundle)

    def write(
        self,
        analysis: AnalysisResult,
        bundle: Optional[ResearchBundle] = None,
    ) -> str:
        """Run only the writer stage to produce a proposal.

        Args:
            analysis: AnalysisResult from analyst stage.
            bundle: Optional research bundle for additional context.

        Returns:
            Markdown proposal document.
        """
        if self.use_static_writer:
            return self.writer_stage.write_proposal_static(analysis)
        return self.writer_stage.write_proposal(
            analysis, bundle=bundle, research_stage=self.research_stage
        )

    def analyze_stock(
        self,
        ticker: str,
        peers: Optional[list[str]] = None,
    ) -> str:
        """Run the full pipeline: Research → Analyze → Write.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL").
            peers: Optional list of peer tickers for comparison.

        Returns:
            Complete Markdown investment proposal.
        """
        bundle = self.research(ticker, peers=peers)
        analysis = self.analyze(bundle)
        proposal = self.write(analysis, bundle=bundle)
        return proposal

    def analyze_portfolio(
        self,
        tickers: list[str],
    ) -> dict[str, str]:
        """Analyze multiple stocks and return proposals for each.

        Args:
            tickers: List of ticker symbols.

        Returns:
            Dict mapping ticker to Markdown proposal.
        """
        proposals = {}
        for ticker in tickers:
            proposals[ticker] = self.analyze_stock(ticker)
        return proposals

    def analyze_and_save(
        self,
        ticker: str,
        peers: Optional[list[str]] = None,
        output_dir: str = "output",
    ) -> str:
        """Run full pipeline and save proposal to a file.

        Args:
            ticker: Stock ticker symbol.
            peers: Optional peer tickers.
            output_dir: Directory to save the proposal.

        Returns:
            Path to the saved proposal file.
        """
        proposal = self.analyze_stock(ticker, peers=peers)

        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ticker.upper()}_proposal_{timestamp}.md"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w") as f:
            f.write(proposal)

        return filepath

    def get_research_summary(self, ticker: str) -> dict:
        """Get a quick data summary without full analysis (no LLM calls).

        Useful for quick lookups or building watchlists.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Dict with key metrics.
        """
        bundle = self.research(ticker)
        snapshot = bundle.snapshot

        if not snapshot:
            return {"ticker": ticker, "error": "Failed to fetch data"}

        return {
            "ticker": snapshot.ticker,
            "company_name": snapshot.company_name,
            "current_price": snapshot.current_price,
            "market_cap": snapshot.market_cap,
            "pe_ratio": snapshot.pe_ratio,
            "sector": snapshot.sector,
            "dividend_yield": snapshot.dividend_yield,
            "beta": snapshot.beta,
            "recommendation": snapshot.recommendation,
            "returns": {
                "1m": bundle.historical.returns_1m if bundle.historical else None,
                "3m": bundle.historical.returns_3m if bundle.historical else None,
                "1y": bundle.historical.returns_1y if bundle.historical else None,
            },
            "news_sentiment": (
                bundle.news_sentiment.avg_sentiment
                if bundle.news_sentiment
                else None
            ),
        }
