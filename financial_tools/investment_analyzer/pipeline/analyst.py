"""Analyst stage - evaluates research data and produces structured analysis.

Uses the Anthropic Claude API to reason over the research bundle and produce
a structured analysis covering valuation, risk, growth, and tax considerations.
"""

import json
import os
from dataclasses import dataclass
from typing import Optional

import anthropic

from .researcher import ResearchBundle, ResearchStage


@dataclass
class AnalysisResult:
    """Structured output from the analyst stage."""
    ticker: str
    company_name: str
    investment_thesis: str
    valuation_assessment: str
    risk_analysis: str
    growth_outlook: str
    tax_considerations: str
    bear_case: str
    bull_case: str
    overall_rating: str  # Strong Buy, Buy, Hold, Sell, Strong Sell
    confidence_level: str  # High, Medium, Low
    key_metrics_summary: dict
    raw_analysis: str


ANALYST_SYSTEM_PROMPT = """You are a senior financial analyst at an investment research firm.
You produce rigorous, data-driven investment analyses. You are thorough but concise.

IMPORTANT GUIDELINES:
- Base ALL conclusions on the provided data. Do not fabricate numbers.
- If data is missing or insufficient, explicitly flag it.
- Always present both bull and bear cases with equal rigor.
- Include specific numbers and ratios to support every claim.
- Evaluate tax efficiency: consider whether the asset generates ordinary income vs.
  capital gains, whether it's suited for tax-advantaged accounts, and any K-1 or
  partnership tax complexity.
- Rate the investment on this scale: Strong Buy, Buy, Hold, Sell, Strong Sell.
- Rate your confidence: High (comprehensive data), Medium (some gaps), Low (limited data).

DISCLAIMER: All analysis is for educational and research purposes only.
This does not constitute financial advice."""

ANALYST_USER_PROMPT = """Analyze the following research data and produce a structured investment analysis.

RESEARCH DATA:
{research_text}

Respond with a JSON object containing exactly these fields:
{{
    "investment_thesis": "2-3 sentence summary of why this asset is or isn't worth buying",
    "valuation_assessment": "Analysis of current valuation vs. historical and peers. Is it overpriced, fairly valued, or undervalued? Use specific P/E, PEG, P/B numbers.",
    "risk_analysis": "Key risks including volatility, debt levels, sector risks, and macro factors. Reference beta and debt/equity specifically.",
    "growth_outlook": "Revenue and earnings growth trajectory. Is growth accelerating or decelerating? Use specific growth rates.",
    "tax_considerations": "Tax efficiency analysis: dividend tax treatment, capital gains profile, suitability for tax-advantaged vs taxable accounts, any K-1 complexity.",
    "bear_case": "The strongest argument AGAINST this investment. Be specific and rigorous.",
    "bull_case": "The strongest argument FOR this investment. Be specific and rigorous.",
    "overall_rating": "One of: Strong Buy, Buy, Hold, Sell, Strong Sell",
    "confidence_level": "One of: High, Medium, Low",
    "key_metrics_summary": {{
        "current_price": number,
        "fair_value_estimate": "your estimated fair value or range",
        "pe_vs_sector_avg": "comparison string",
        "key_strength": "single biggest strength",
        "key_risk": "single biggest risk"
    }}
}}

Return ONLY the JSON object, no other text."""


class AnalystStage:
    """Runs Claude-powered financial analysis on research data.

    Args:
        api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
        model: Claude model to use.
        research_stage: Optional shared ResearchStage for formatting.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        research_stage: Optional[ResearchStage] = None,
    ):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY")
        )
        self.model = model
        self.research_stage = research_stage or ResearchStage()

    def analyze(self, bundle: ResearchBundle) -> AnalysisResult:
        """Run analyst stage on a research bundle.

        Args:
            bundle: ResearchBundle from the research stage.

        Returns:
            AnalysisResult with structured analysis.
        """
        research_text = self.research_stage.format_research_text(bundle)

        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=ANALYST_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": ANALYST_USER_PROMPT.format(research_text=research_text),
                }
            ],
        )

        raw_text = message.content[0].text.strip()

        # Parse JSON from response, handling markdown code blocks
        json_text = raw_text
        if json_text.startswith("```"):
            lines = json_text.split("\n")
            json_text = "\n".join(lines[1:-1])

        try:
            analysis = json.loads(json_text)
        except json.JSONDecodeError:
            # If JSON parsing fails, return raw analysis
            return AnalysisResult(
                ticker=bundle.ticker,
                company_name=bundle.snapshot.company_name if bundle.snapshot else bundle.ticker,
                investment_thesis="Analysis parsing failed. See raw_analysis.",
                valuation_assessment="",
                risk_analysis="",
                growth_outlook="",
                tax_considerations="",
                bear_case="",
                bull_case="",
                overall_rating="Hold",
                confidence_level="Low",
                key_metrics_summary={},
                raw_analysis=raw_text,
            )

        return AnalysisResult(
            ticker=bundle.ticker,
            company_name=bundle.snapshot.company_name if bundle.snapshot else bundle.ticker,
            investment_thesis=analysis.get("investment_thesis", ""),
            valuation_assessment=analysis.get("valuation_assessment", ""),
            risk_analysis=analysis.get("risk_analysis", ""),
            growth_outlook=analysis.get("growth_outlook", ""),
            tax_considerations=analysis.get("tax_considerations", ""),
            bear_case=analysis.get("bear_case", ""),
            bull_case=analysis.get("bull_case", ""),
            overall_rating=analysis.get("overall_rating", "Hold"),
            confidence_level=analysis.get("confidence_level", "Low"),
            key_metrics_summary=analysis.get("key_metrics_summary", {}),
            raw_analysis=raw_text,
        )
