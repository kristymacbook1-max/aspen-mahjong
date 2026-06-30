"""Section 263A / 263(a) / 266 cost capitalization workpaper builder.

Prepares cost capitalization schedules from a department / cost-center based
trial balance, with columns for capitalization under the required and elective
provisions of IRC §266 (carrying charges), §263(a) (acquisition / improvement
costs), and §263A (UNICAP) — plus related capitalization regimes (§174A, §197,
§195/§248/§709, IDC, §263(g), §461(g)).

Usage (called conversationally by Claude):
    from financial_tools.cost_capitalization.run_analysis import CostCapitalizationPipeline
    pipeline = CostCapitalizationPipeline()
    results = pipeline.run(inp, company_tag="Acme")
"""

from .analyzer import (
    CostCenter,
    TrialBalanceLine,
    AllocationOverlay,
    Section263AInputs,
    Section266Election,
    Section263aElection,
    SmallBusinessTest,
    CostCapitalizationInput,
    CostCapitalizationAnalyzer,
)
from .run_analysis import CostCapitalizationPipeline

__all__ = [
    "CostCenter",
    "TrialBalanceLine",
    "AllocationOverlay",
    "Section263AInputs",
    "Section266Election",
    "Section263aElection",
    "SmallBusinessTest",
    "CostCapitalizationInput",
    "CostCapitalizationAnalyzer",
    "CostCapitalizationPipeline",
]
