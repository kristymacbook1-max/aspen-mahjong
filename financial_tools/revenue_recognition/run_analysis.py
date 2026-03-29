"""Main entry point for running revenue recognition analysis across all phases.

Usage:
    from financial_tools.revenue_recognition.run_analysis import RevenueRecognitionPipeline

    # Phase 1 only
    pipeline = RevenueRecognitionPipeline(company_name="Acme Corp")
    result = pipeline.run_phase1(ten_k_input)

    # Phase 2 (feeds from Phase 1)
    result = pipeline.run_phase2(phase2_input)

    # Phase 3 (feeds from Phase 1 + Phase 2)
    result = pipeline.run_phase3(phase3_input)

    # Or run all phases sequentially
    pipeline.run_all(ten_k_input, phase2_input, phase3_input)
"""

import os
from typing import Optional

from .phase1.ten_k_analyzer import TenKAnalyzer, TenKInput
from .phase1.excel_report import Phase1ExcelReport
from .phase2.trial_balance_analyzer import TrialBalanceAnalyzer, Phase2Input
from .phase2.excel_report import Phase2ExcelReport
from .phase3.contract_analyzer import ContractAnalyzer, Phase3Input
from .phase3.excel_report import Phase3ExcelReport


class RevenueRecognitionPipeline:
    """Orchestrates the three-phase revenue recognition analysis pipeline."""

    def __init__(self, company_name: str = "", output_dir: str = "output"):
        self.company_name = company_name
        self.output_dir = output_dir
        self.phase1_results = None
        self.phase2_results = None
        self.phase3_results = None

    def run_phase1(self, data: TenKInput) -> dict:
        """Run Phase 1: 10-K & Public Information Analysis.

        Args:
            data: TenKInput with company profile, revenue streams,
                  deferred revenue, disclosures, and financial statements.

        Returns:
            Analysis results dict and generates Excel workbook.
        """
        analyzer = TenKAnalyzer(data)
        self.phase1_results = analyzer.analyze()

        report = Phase1ExcelReport(self.phase1_results, output_dir=self.output_dir)
        filepath = report.generate()
        print(f"Phase 1 report generated: {filepath}")

        return self.phase1_results

    def run_phase2(self, data: Phase2Input) -> dict:
        """Run Phase 2: Trial Balance, Tax Return & Work Papers Analysis.

        Args:
            data: Phase2Input with trial balance, tax return data,
                  work papers, and optionally Phase 1 results.

        Returns:
            Analysis results dict and generates Excel workbook.
        """
        # Link Phase 1 results if available
        if self.phase1_results and data.phase1_results is None:
            data.phase1_results = self.phase1_results

        analyzer = TrialBalanceAnalyzer(data)
        self.phase2_results = analyzer.analyze()

        report = Phase2ExcelReport(
            self.phase2_results,
            company_name=self.company_name,
            output_dir=self.output_dir,
        )
        filepath = report.generate()
        print(f"Phase 2 report generated: {filepath}")

        return self.phase2_results

    def run_phase3(self, data: Phase3Input) -> dict:
        """Run Phase 3: Full Contract-Level Revenue Recognition Analysis.

        Args:
            data: Phase3Input with contracts, performance obligations,
                  and optionally Phase 1/2 results.

        Returns:
            Analysis results dict and generates Excel workbook.
        """
        # Link prior phase results if available
        if self.phase1_results and data.phase1_results is None:
            data.phase1_results = self.phase1_results
        if self.phase2_results and data.phase2_results is None:
            data.phase2_results = self.phase2_results

        analyzer = ContractAnalyzer(data)
        self.phase3_results = analyzer.analyze()

        report = Phase3ExcelReport(
            self.phase3_results,
            company_name=self.company_name,
            output_dir=self.output_dir,
        )
        filepath = report.generate()
        print(f"Phase 3 report generated: {filepath}")

        return self.phase3_results

    def run_all(self, phase1_data: TenKInput, phase2_data: Phase2Input,
                phase3_data: Phase3Input) -> dict:
        """Run all three phases sequentially.

        Returns:
            Combined results from all phases.
        """
        print(f"Starting revenue recognition analysis for {self.company_name}")
        print("=" * 60)

        print("\n--- Phase 1: 10-K & Public Information ---")
        self.run_phase1(phase1_data)

        print("\n--- Phase 2: Trial Balance & Tax Return ---")
        self.run_phase2(phase2_data)

        print("\n--- Phase 3: Contract-Level Analysis ---")
        self.run_phase3(phase3_data)

        print("\n" + "=" * 60)
        print("Analysis complete. Reports generated in:", self.output_dir)

        return {
            "phase1": self.phase1_results,
            "phase2": self.phase2_results,
            "phase3": self.phase3_results,
        }
