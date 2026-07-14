"""Cost Capitalization Analysis Pipeline.

Usage (called conversationally by Claude):
    from financial_tools.cost_capitalization.run_analysis import CostCapitalizationPipeline
    pipeline = CostCapitalizationPipeline()
    results = pipeline.run(inp, company_tag="Acme")
    print(results["_output_path"])
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from cost_capitalization.analyzer import (
    CostCapitalizationAnalyzer, CostCapitalizationInput,
)
from cost_capitalization.excel_report import CostCapitalizationReport
from cost_capitalization.excel_report_lean import CostCapitalizationLeanReport


class CostCapitalizationPipeline:
    """Orchestrates the cost capitalization analysis and workbook generation."""

    def __init__(self, output_dir: str = "output/cost_capitalization"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def run(self, inp: CostCapitalizationInput, company_tag: str = None,
            style: str = "lean") -> dict:
        """style='lean' -> one-tab auto-classified calc (default);
        style='full' -> the expanded 12-tab workpaper."""
        tag = company_tag or inp.company_name.replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        analyzer = CostCapitalizationAnalyzer()
        if style == "full":
            results = analyzer.analyze(inp)
            report = CostCapitalizationReport()
            suffix = "cost_cap_full"
        else:
            results = analyzer.analyze_lean(inp)
            report = CostCapitalizationLeanReport()
            suffix = "cost_cap"

        output_path = os.path.join(self.output_dir, f"{tag}_{suffix}_{timestamp}.xlsx")
        report.generate(results, output_path)
        results["_output_path"] = output_path
        return results
