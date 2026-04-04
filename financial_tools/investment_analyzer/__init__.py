"""AI Investment Analyzer - Analyzes stock market data and drafts investment proposals.

Uses a pipeline architecture (research → analyze → write) powered by the
Anthropic Claude API with tool-use for real-time market data retrieval.
"""

from .run_analysis import InvestmentAnalyzerPipeline

__all__ = ["InvestmentAnalyzerPipeline"]
