"""Transaction Cost Analysis Pipeline."""

import os
from datetime import datetime

from .phase1.ten_k_analyzer import TransactionCostAnalyzer, Phase1TransactionInput
from .phase1.excel_report import Phase1TransactionCostReport


class TransactionCostPipeline:

    def __init__(self, output_dir: str = "output/transaction_costs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def run_phase1(self, inp: Phase1TransactionInput, company_tag: str = None) -> dict:
        tag = company_tag or inp.company.ticker or inp.company.name.replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        analyzer = TransactionCostAnalyzer()
        results = analyzer.analyze(inp)

        report = Phase1TransactionCostReport()
        output_path = os.path.join(self.output_dir, f"{tag}_txn_costs_phase1_{timestamp}.xlsx")
        report.generate(results, output_path)

        results["_output_path"] = output_path
        return results
