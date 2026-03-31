"""Phase 1 CAMT Analyzer — 10-K / Public Data Analysis.

Identifies whether the Corporate Alternative Minimum Tax (§55, as amended
by IRA 2022) applies and estimates the tentative minimum tax from publicly
available financial statements.  CAMT applies to "applicable corporations"
with average annual adjusted financial statement income (AFSI) ≥ $1 billion
over a 3-year period.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional, Dict
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from revenue_recognition.utils.currency_helpers import (
    to_decimal, round_currency, format_currency, format_millions, pct_change,
)
from revenue_recognition.utils.entity_types import get_entity_config


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CompanyProfile:
    name: str
    ticker: str = ""
    entity_type: str = "c_corp"
    fiscal_year_end: str = "12/31"
    tax_year: int = 2024
    is_public: bool = True
    industry: str = ""


@dataclass
class FinancialStatementIncome:
    """Adjusted Financial Statement Income (AFSI) components."""
    year: int
    pretax_book_income: Decimal = Decimal("0")      # from income statement
    # Adjustments to reach AFSI
    federal_income_tax_expense: Decimal = Decimal("0")  # added back
    foreign_income_taxes: Decimal = Decimal("0")
    depreciation_adjustment: Decimal = Decimal("0")  # §56A(c)(13) — use tax depreciation
    amortization_adjustment: Decimal = Decimal("0")
    stock_comp_adjustment: Decimal = Decimal("0")     # use tax deduction amounts
    pension_adjustment: Decimal = Decimal("0")
    other_adjustments: Decimal = Decimal("0")
    # Resulting AFSI
    afsi: Decimal = Decimal("0")


@dataclass
class CAMTThresholdTest:
    """3-year average AFSI test for applicable corporation status."""
    year1_afsi: Decimal = Decimal("0")
    year2_afsi: Decimal = Decimal("0")
    year3_afsi: Decimal = Decimal("0")
    three_year_average: Decimal = Decimal("0")
    threshold: Decimal = Decimal("1000000000")  # $1 billion
    is_applicable_corporation: bool = False


@dataclass
class CAMTComputation:
    """Tentative minimum tax computation."""
    afsi: Decimal = Decimal("0")
    camt_foreign_tax_credit: Decimal = Decimal("0")
    tentative_minimum_tax: Decimal = Decimal("0")   # 15% of AFSI
    regular_tax_plus_base_erosion: Decimal = Decimal("0")
    camt_liability: Decimal = Decimal("0")           # excess of TMT over regular tax


@dataclass
class CAMTAdjustmentItem:
    """Individual AFSI adjustment item."""
    description: str
    book_amount: Decimal = Decimal("0")
    tax_adjustment: Decimal = Decimal("0")
    adjusted_amount: Decimal = Decimal("0")
    irc_section: str = ""
    notes: str = ""


@dataclass
class Phase1CAMTInput:
    company: CompanyProfile = field(default_factory=CompanyProfile)
    financial_statement_income: List[FinancialStatementIncome] = field(default_factory=list)
    adjustment_items: List[CAMTAdjustmentItem] = field(default_factory=list)
    regular_tax_liability: Decimal = Decimal("0")
    base_erosion_minimum_tax: Decimal = Decimal("0")
    prior_year_camt_credit: Decimal = Decimal("0")


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class CAMTAnalyzer:
    """Phase 1 CAMT analyzer using public 10-K data."""

    def analyze(self, inp: Phase1CAMTInput) -> dict:
        self._input = inp

        threshold = self._test_applicable_corporation()
        afsi = self._compute_afsi()
        computation = self._compute_camt(afsi, threshold)
        adjustments = self._analyze_adjustments()
        findings = self._generate_findings(threshold, computation, adjustments)
        roadmap = self._generate_phase2_recommendations(findings)

        return {
            "company": inp.company,
            "threshold_test": threshold,
            "afsi_computation": afsi,
            "camt_computation": computation,
            "adjustments": adjustments,
            "findings": findings,
            "phase2_roadmap": roadmap,
        }

    def _test_applicable_corporation(self) -> CAMTThresholdTest:
        fsi_list = sorted(self._input.financial_statement_income, key=lambda x: x.year)
        afsi_values = [to_decimal(f.afsi) for f in fsi_list[-3:]]

        while len(afsi_values) < 3:
            afsi_values.insert(0, Decimal("0"))

        avg = round_currency(sum(afsi_values) / 3)
        threshold = Decimal("1000000000")

        return CAMTThresholdTest(
            year1_afsi=afsi_values[0],
            year2_afsi=afsi_values[1],
            year3_afsi=afsi_values[2],
            three_year_average=avg,
            threshold=threshold,
            is_applicable_corporation=avg >= threshold,
        )

    def _compute_afsi(self) -> dict:
        current_fsi = None
        for f in self._input.financial_statement_income:
            if f.year == self._input.company.tax_year:
                current_fsi = f
                break

        if not current_fsi:
            current_fsi = self._input.financial_statement_income[-1] if self._input.financial_statement_income else FinancialStatementIncome(year=self._input.company.tax_year)

        pretax = to_decimal(current_fsi.pretax_book_income)
        adjustments = {
            "depreciation": to_decimal(current_fsi.depreciation_adjustment),
            "amortization": to_decimal(current_fsi.amortization_adjustment),
            "stock_compensation": to_decimal(current_fsi.stock_comp_adjustment),
            "pension": to_decimal(current_fsi.pension_adjustment),
            "other": to_decimal(current_fsi.other_adjustments),
        }
        total_adj = sum(adjustments.values())
        afsi = pretax + total_adj

        return {
            "year": current_fsi.year,
            "pretax_book_income": pretax,
            "adjustments": adjustments,
            "total_adjustments": total_adj,
            "afsi": afsi,
        }

    def _compute_camt(self, afsi_result: dict, threshold: CAMTThresholdTest) -> CAMTComputation:
        if not threshold.is_applicable_corporation:
            return CAMTComputation(afsi=afsi_result["afsi"])

        afsi_amount = to_decimal(afsi_result["afsi"])
        camt_ftc = to_decimal(self._input.financial_statement_income[-1].foreign_income_taxes) if self._input.financial_statement_income else Decimal("0")

        tentative = round_currency(afsi_amount * Decimal("0.15"))
        tentative_net = max(Decimal("0"), tentative - camt_ftc)
        regular = to_decimal(self._input.regular_tax_liability)
        base_erosion = to_decimal(self._input.base_erosion_minimum_tax)
        regular_plus_beat = regular + base_erosion

        camt_liability = max(Decimal("0"), tentative_net - regular_plus_beat)
        prior_credit = to_decimal(self._input.prior_year_camt_credit)
        camt_liability = max(Decimal("0"), camt_liability - prior_credit)

        return CAMTComputation(
            afsi=afsi_amount,
            camt_foreign_tax_credit=camt_ftc,
            tentative_minimum_tax=tentative_net,
            regular_tax_plus_base_erosion=regular_plus_beat,
            camt_liability=camt_liability,
        )

    def _analyze_adjustments(self) -> list:
        results = []
        for adj in self._input.adjustment_items:
            results.append({
                "description": adj.description,
                "book_amount": adj.book_amount,
                "tax_adjustment": adj.tax_adjustment,
                "adjusted_amount": adj.adjusted_amount,
                "irc_section": adj.irc_section,
                "notes": adj.notes,
                "impact": "Increases AFSI" if to_decimal(adj.tax_adjustment) > 0 else "Decreases AFSI",
            })
        return results

    def _generate_findings(self, threshold, computation, adjustments) -> list:
        findings = []

        if threshold.is_applicable_corporation:
            findings.append({
                "area": "Applicable Corporation Status",
                "description": f"3-year average AFSI of {format_millions(threshold.three_year_average)} exceeds $1B threshold",
                "amount": threshold.three_year_average,
                "risk_level": "high",
                "recommendation": "CAMT applies — prepare Form 4626",
            })
        else:
            findings.append({
                "area": "Applicable Corporation Status",
                "description": f"3-year average AFSI of {format_millions(threshold.three_year_average)} below $1B threshold",
                "amount": threshold.three_year_average,
                "risk_level": "low",
                "recommendation": "CAMT does not apply — continue monitoring",
            })

        if to_decimal(computation.camt_liability) > 0:
            findings.append({
                "area": "CAMT Liability",
                "description": f"Estimated CAMT liability: {format_currency(computation.camt_liability)}",
                "amount": computation.camt_liability,
                "risk_level": "high",
                "recommendation": "Evaluate AFSI reduction strategies; review depreciation and stock comp adjustments",
            })

        for adj in adjustments:
            if abs(to_decimal(adj["tax_adjustment"])) > Decimal("10000000"):
                findings.append({
                    "area": "AFSI Adjustment",
                    "description": f"{adj['description']}: {adj['impact']}",
                    "amount": adj["tax_adjustment"],
                    "risk_level": "medium",
                    "recommendation": f"Verify adjustment under {adj['irc_section']}",
                })

        return findings

    def _generate_phase2_recommendations(self, findings) -> list:
        return [
            {
                "priority": 1,
                "area": "AFSI Computation",
                "description": "Build detailed AFSI from trial balance with all §56A adjustments",
                "data_needed": "Trial balance, tax depreciation schedules, stock comp detail, pension actuarial reports",
            },
            {
                "priority": 2,
                "area": "Depreciation Adjustment",
                "description": "§56A(c)(13): replace book depreciation with tax depreciation in AFSI",
                "data_needed": "Fixed asset register, book vs tax depreciation schedules",
            },
            {
                "priority": 3,
                "area": "CAMT Foreign Tax Credit",
                "description": "Compute CAMT FTC under §59(l) — separate from regular FTC",
                "data_needed": "Foreign tax credit worksheets, Form 1118, country-by-country data",
            },
        ]
