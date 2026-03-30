"""Fixed Asset / Depreciation Analysis Pipeline."""

import os
from datetime import datetime

from .phase1.ten_k_analyzer import FixedAssetAnalyzer, Phase1FixedAssetInput
from .phase1.excel_report import Phase1FixedAssetReport


class FixedAssetPipeline:

    def __init__(self, output_dir: str = "output/fixed_assets"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def run_phase1(self, inp: Phase1FixedAssetInput, company_tag: str = None) -> dict:
        tag = company_tag or inp.company.ticker or inp.company.name.replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        analyzer = FixedAssetAnalyzer()
        results = analyzer.analyze(inp)

        report = Phase1FixedAssetReport()
        output_path = os.path.join(self.output_dir, f"{tag}_fixed_assets_phase1_{timestamp}.xlsx")
        report.generate(results, output_path)

        results["_output_path"] = output_path
        return results
