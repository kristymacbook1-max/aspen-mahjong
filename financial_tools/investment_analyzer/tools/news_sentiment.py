"""News and sentiment data fetcher.

Uses Alpha Vantage news sentiment API and SEC EDGAR for filings.
Falls back gracefully when API keys are not available.
"""

import os
import time
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class NewsArticle:
    """A single news article with sentiment."""
    title: str
    source: str
    url: str
    published: str
    summary: str
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None


@dataclass
class NewsSentimentResult:
    """Collection of news articles and aggregate sentiment for a ticker."""
    ticker: str
    articles: list[NewsArticle]
    avg_sentiment: Optional[float] = None
    article_count: int = 0


class NewsSentimentFetcher:
    """Fetches news sentiment data from Alpha Vantage and SEC EDGAR.

    Args:
        alpha_vantage_key: API key for Alpha Vantage. Falls back to
            ALPHA_VANTAGE_API_KEY env var.
        cache_ttl: Cache TTL in seconds. Default 30 minutes.
    """

    ALPHA_VANTAGE_BASE = "https://www.alphavantage.co/query"
    SEC_EDGAR_BASE = "https://efts.sec.gov/LATEST/search-index?q="

    def __init__(
        self,
        alpha_vantage_key: Optional[str] = None,
        cache_ttl: int = 1800,
    ):
        self.alpha_vantage_key = alpha_vantage_key or os.getenv("ALPHA_VANTAGE_API_KEY")
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, object]] = {}

    def _get_cached(self, key: str) -> Optional[object]:
        if key in self._cache:
            ts, data = self._cache[key]
            if (time.time() - ts) < self.cache_ttl:
                return data
        return None

    def _set_cached(self, key: str, data: object) -> None:
        self._cache[key] = (time.time(), data)

    def get_news_sentiment(
        self, ticker: str, limit: int = 10
    ) -> NewsSentimentResult:
        """Fetch recent news with sentiment scores for a ticker.

        Uses Alpha Vantage News Sentiment API if key is available.
        Returns empty result if no API key is configured.
        """
        cache_key = f"news:{ticker}:{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        if not self.alpha_vantage_key:
            return NewsSentimentResult(
                ticker=ticker, articles=[], article_count=0
            )

        try:
            resp = requests.get(
                self.ALPHA_VANTAGE_BASE,
                params={
                    "function": "NEWS_SENTIMENT",
                    "tickers": ticker,
                    "limit": limit,
                    "apikey": self.alpha_vantage_key,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            articles = []
            for item in data.get("feed", [])[:limit]:
                # Find ticker-specific sentiment
                ticker_sentiment = None
                for ts in item.get("ticker_sentiment", []):
                    if ts.get("ticker", "").upper() == ticker.upper():
                        ticker_sentiment = ts
                        break

                articles.append(
                    NewsArticle(
                        title=item.get("title", ""),
                        source=item.get("source", ""),
                        url=item.get("url", ""),
                        published=item.get("time_published", ""),
                        summary=item.get("summary", ""),
                        sentiment_score=(
                            float(ticker_sentiment["ticker_sentiment_score"])
                            if ticker_sentiment
                            else None
                        ),
                        sentiment_label=(
                            ticker_sentiment.get("ticker_sentiment_label")
                            if ticker_sentiment
                            else None
                        ),
                    )
                )

            scored = [a.sentiment_score for a in articles if a.sentiment_score is not None]
            avg = sum(scored) / len(scored) if scored else None

            result = NewsSentimentResult(
                ticker=ticker.upper(),
                articles=articles,
                avg_sentiment=avg,
                article_count=len(articles),
            )

            self._set_cached(cache_key, result)
            return result

        except (requests.RequestException, KeyError, ValueError):
            return NewsSentimentResult(
                ticker=ticker, articles=[], article_count=0
            )

    def get_sec_filings_summary(self, ticker: str) -> str:
        """Fetch recent SEC filing references for a ticker.

        Returns a text summary of recent filings from EDGAR full-text search.
        """
        cache_key = f"sec:{ticker}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            resp = requests.get(
                f"https://efts.sec.gov/LATEST/search-index",
                params={
                    "q": f'"{ticker}"',
                    "dateRange": "custom",
                    "startdt": "2024-01-01",
                    "forms": "10-K,10-Q,8-K",
                },
                headers={"User-Agent": "InvestmentAnalyzer/1.0 research@example.com"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            filings = []
            for hit in data.get("hits", {}).get("hits", [])[:5]:
                source = hit.get("_source", {})
                filings.append(
                    f"- {source.get('form_type', 'N/A')} filed {source.get('file_date', 'N/A')}: "
                    f"{source.get('display_names', [''])[0] if source.get('display_names') else ticker}"
                )

            result = "\n".join(filings) if filings else "No recent SEC filings found."
            self._set_cached(cache_key, result)
            return result

        except (requests.RequestException, KeyError, ValueError):
            return "SEC EDGAR data unavailable."

    def format_news_text(self, result: NewsSentimentResult) -> str:
        """Format news sentiment as readable text for LLM consumption."""
        if not result.articles:
            return f"=== News Sentiment ({result.ticker}) ===\nNo recent news articles available.\n"

        lines = [f"=== News Sentiment ({result.ticker}) ==="]
        if result.avg_sentiment is not None:
            label = (
                "Bullish" if result.avg_sentiment > 0.15
                else "Bearish" if result.avg_sentiment < -0.15
                else "Neutral"
            )
            lines.append(f"Overall Sentiment: {label} (score: {result.avg_sentiment:.3f})")
        lines.append(f"Articles Analyzed: {result.article_count}\n")

        for i, article in enumerate(result.articles[:5], 1):
            sentiment = ""
            if article.sentiment_label:
                sentiment = f" [{article.sentiment_label}]"
            lines.append(f"{i}. {article.title}{sentiment}")
            lines.append(f"   Source: {article.source} | {article.published}")
            if article.summary:
                lines.append(f"   {article.summary[:200]}...")
            lines.append("")

        return "\n".join(lines)
