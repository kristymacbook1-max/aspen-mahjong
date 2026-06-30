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


class CostCapitalizationPipeline:
    """Orchestrates the cost capitalization analysis and workbook generation."""

    def __init__(self, output_dir: str = "output/cost_capitalization"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def run(self, inp: CostCapitalizationInput, company_tag: str = None) -> dict:
        tag = company_tag or inp.company_name.replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        analyzer = CostCapitalizationAnalyzer()
        results = analyzer.analyze(inp)

        report = CostCapitalizationReport()
        output_path = os.path.join(
            self.output_dir, f"{tag}_cost_cap_{timestamp}.xlsx"
        )
        report.generate(results, output_path)

        results["_output_path"] = output_path
        return results
