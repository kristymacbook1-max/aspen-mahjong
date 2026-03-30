"""Partnership Tax Analysis Pipeline."""

import os
from datetime import datetime

from .phase1.ten_k_analyzer import PartnershipTaxAnalyzer, Phase1PartnershipInput
from .phase1.excel_report import Phase1PartnershipReport


class PartnershipTaxPipeline:

    def __init__(self, output_dir: str = "output/partnership_tax"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def run_phase1(self, inp: Phase1PartnershipInput, company_tag: str = None) -> dict:
        tag = company_tag or inp.partnership.name.replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        analyzer = PartnershipTaxAnalyzer()
        results = analyzer.analyze(inp)

        report = Phase1PartnershipReport()
        output_path = os.path.join(self.output_dir, f"{tag}_partnership_tax_phase1_{timestamp}.xlsx")
        report.generate(results, output_path)

        results["_output_path"] = output_path
        return results
