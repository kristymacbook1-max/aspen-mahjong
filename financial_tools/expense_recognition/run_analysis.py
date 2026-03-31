"""Expense Recognition Analysis Pipeline.

Orchestrates the 3-phase expense recognition analysis with optional
technical authority report generation.

Usage (called conversationally by Claude):
    from financial_tools.expense_recognition.run_analysis import ExpenseRecognitionPipeline
    pipeline = ExpenseRecognitionPipeline()
    results = pipeline.run_phase1(input_data)
    results = pipeline.run_all(phase1_input, phase2_input, phase3_input)
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from expense_recognition.phase1.ten_k_analyzer import TenKExpenseAnalyzer, TenKExpenseInput
from expense_recognition.phase1.excel_report import Phase1ExpenseReport
from expense_recognition.phase2.trial_balance_analyzer import TrialBalanceExpenseAnalyzer, Phase2ExpenseInput
from expense_recognition.phase2.excel_report import Phase2ExpenseReport
from expense_recognition.phase3.expense_analyzer import ExpenseAnalyzer, Phase3ExpenseInput
from expense_recognition.phase3.excel_report import Phase3ExpenseReport
from expense_recognition.technical_authority.position_analyzer import PositionAnalyzer
from expense_recognition.technical_authority.excel_report import TechnicalAuthorityReport


class ExpenseRecognitionPipeline:
    """Orchestrates the full expense recognition analysis pipeline."""

    def __init__(self, output_dir: str = "output/expense_recognition"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def run_phase1(self, inp: TenKExpenseInput, company_tag: str = None) -> dict:
        """Run Phase 1 analysis from 10-K/public data."""
        tag = company_tag or inp.company.ticker or inp.company.name.replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        analyzer = TenKExpenseAnalyzer()
        results = analyzer.analyze(inp)

        report = Phase1ExpenseReport()
        output_path = os.path.join(
            self.output_dir, f"{tag}_expense_phase1_{timestamp}.xlsx"
        )
        report.generate(results, output_path)

        results["_output_path"] = output_path
        results["_phase"] = 1
        return results

    def run_phase2(self, inp: Phase2ExpenseInput, phase1_results: dict = None,
                   company_tag: str = None) -> dict:
        """Run Phase 2 analysis from trial balance/tax return."""
        tag = company_tag or inp.company_name.replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if phase1_results and not inp.phase1_findings:
            inp.phase1_findings = phase1_results.get("findings", [])

        analyzer = TrialBalanceExpenseAnalyzer()
        results = analyzer.analyze(inp)

        report = Phase2ExpenseReport()
        output_path = os.path.join(
            self.output_dir, f"{tag}_expense_phase2_{timestamp}.xlsx"
        )
        report.generate(results, output_path)

        results["_output_path"] = output_path
        results["_phase"] = 2
        return results

    def run_phase3(self, inp: Phase3ExpenseInput, company_tag: str = None) -> dict:
        """Run Phase 3 contract/invoice-level analysis."""
        tag = company_tag or inp.company_name.replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        analyzer = ExpenseAnalyzer()
        results = analyzer.analyze(inp)

        report = Phase3ExpenseReport()
        output_path = os.path.join(
            self.output_dir, f"{tag}_expense_phase3_{timestamp}.xlsx"
        )
        report.generate(results, output_path)

        results["_output_path"] = output_path
        results["_phase"] = 3
        return results

    def run_technical_authority(self, analysis_results: dict,
                                company_tag: str = None) -> dict:
        """Generate technical authority report from any phase results."""
        company = analysis_results.get("company_name", "Unknown")
        tag = company_tag or company.replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        analyzer = PositionAnalyzer()
        memo = analyzer.analyze_all(analysis_results)

        report = TechnicalAuthorityReport()
        output_path = os.path.join(
            self.output_dir, f"{tag}_expense_authority_{timestamp}.xlsx"
        )
        report.generate(memo, output_path)

        return {
            "memo": memo,
            "_output_path": output_path,
        }

    def run_all(self, phase1_input: TenKExpenseInput,
                phase2_input: Phase2ExpenseInput = None,
                phase3_input: Phase3ExpenseInput = None,
                company_tag: str = None) -> dict:
        """Run all phases sequentially, linking results forward."""
        tag = company_tag or phase1_input.company.ticker or phase1_input.company.name.replace(" ", "_")

        p1 = self.run_phase1(phase1_input, tag)
        results = {"phase1": p1}

        if phase2_input:
            p2 = self.run_phase2(phase2_input, phase1_results=p1, company_tag=tag)
            results["phase2"] = p2

        if phase3_input:
            p3 = self.run_phase3(phase3_input, company_tag=tag)
            results["phase3"] = p3

        # Generate technical authority report from most detailed phase
        best_phase = results.get("phase3") or results.get("phase2") or p1
        auth = self.run_technical_authority(best_phase, company_tag=tag)
        results["authority"] = auth

        return results
