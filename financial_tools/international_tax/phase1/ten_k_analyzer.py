"""Phase 1 International Tax Analyzer — 10-K / Public Data Analysis.

Analyzes international tax provisions including §951A GILTI, §250 FDII,
§904 FTC limitation, Subpart F income, and outbound transfer rules.
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
    total_assets: Decimal = Decimal("0")
    industry: str = ""


@dataclass
class CFCEntity:
    """Controlled foreign corporation data from 10-K."""
    name: str
    jurisdiction: str = ""
    functional_currency: str = "USD"
    tested_income: Decimal = Decimal("0")
    tested_loss: Decimal = Decimal("0")
    qbai: Decimal = Decimal("0")  # Qualified Business Asset Investment
    specified_interest_expense: Decimal = Decimal("0")
    subpart_f_income: Decimal = Decimal("0")
    foreign_taxes_paid: Decimal = Decimal("0")
    earnings_and_profits: Decimal = Decimal("0")
    effective_tax_rate: Decimal = Decimal("0")


@dataclass
class FDIIAnalysis:
    """Foreign-Derived Intangible Income data."""
    deduction_eligible_income: Decimal = Decimal("0")  # DEI
    foreign_derived_dei: Decimal = Decimal("0")  # FDDEI
    qbai_domestic: Decimal = Decimal("0")  # Domestic QBAI
    deemed_intangible_income: Decimal = Decimal("0")
    fdii_amount: Decimal = Decimal("0")
    fdii_deduction: Decimal = Decimal("0")
    domestic_revenue: Decimal = Decimal("0")
    foreign_revenue: Decimal = Decimal("0")


@dataclass
class FTCData:
    """Foreign tax credit data."""
    category: str  # general, passive, GILTI, foreign_branch
    foreign_source_income: Decimal = Decimal("0")
    foreign_taxes_paid: Decimal = Decimal("0")
    us_tax_rate: Decimal = Decimal("0.21")
    ftc_limitation: Decimal = Decimal("0")
    credits_allowed: Decimal = Decimal("0")
    excess_credits: Decimal = Decimal("0")
    excess_limitation: Decimal = Decimal("0")


@dataclass
class Phase1InternationalInput:
    company: CompanyProfile = field(default_factory=CompanyProfile)
    cfcs: List[CFCEntity] = field(default_factory=list)
    fdii: FDIIAnalysis = field(default_factory=FDIIAnalysis)
    ftc_data: List[FTCData] = field(default_factory=list)
    worldwide_income: Decimal = Decimal("0")
    us_source_income: Decimal = Decimal("0")
    foreign_source_income: Decimal = Decimal("0")
    total_foreign_taxes: Decimal = Decimal("0")
    has_check_the_box_elections: bool = False
    has_treaty_positions: bool = False


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class InternationalTaxAnalyzer:
    """Phase 1 analyzer for international tax provisions."""

    def analyze(self, inp: Phase1InternationalInput) -> dict:
        self._input = inp
        self._entity = get_entity_config(inp.company.entity_type, inp.company.total_assets)

        gilti = self._analyze_gilti()
        fdii = self._analyze_fdii()
        ftc = self._analyze_ftc()
        subpart_f = self._analyze_subpart_f()
        findings = self._generate_findings(gilti, fdii, ftc, subpart_f)
        roadmap = self._generate_phase2_recommendations(findings)

        return {
            "company": inp.company,
            "entity_config": self._entity,
            "gilti_analysis": gilti,
            "fdii_analysis": fdii,
            "ftc_analysis": ftc,
            "subpart_f_analysis": subpart_f,
            "findings": findings,
            "phase2_roadmap": roadmap,
        }

    def _analyze_gilti(self) -> dict:
        """Compute GILTI inclusion under §951A."""
        total_tested_income = Decimal("0")
        total_tested_loss = Decimal("0")
        total_qbai = Decimal("0")
        total_spec_interest = Decimal("0")
        total_foreign_taxes = Decimal("0")
        cfc_details = []

        for cfc in self._input.cfcs:
            tested_income = to_decimal(cfc.tested_income)
            tested_loss = to_decimal(cfc.tested_loss)
            qbai = to_decimal(cfc.qbai)

            total_tested_income += tested_income
            total_tested_loss += tested_loss
            total_qbai += qbai
            total_spec_interest += to_decimal(cfc.specified_interest_expense)
            total_foreign_taxes += to_decimal(cfc.foreign_taxes_paid)

            cfc_details.append({
                "name": cfc.name,
                "jurisdiction": cfc.jurisdiction,
                "tested_income": tested_income,
                "tested_loss": tested_loss,
                "qbai": qbai,
                "foreign_taxes": cfc.foreign_taxes_paid,
                "effective_rate": cfc.effective_tax_rate,
            })

        net_tested_income = max(Decimal("0"), total_tested_income - total_tested_loss)
        deemed_tangible_return = round_currency(total_qbai * Decimal("0.10") - total_spec_interest)
        deemed_tangible_return = max(Decimal("0"), deemed_tangible_return)
        gilti_inclusion = max(Decimal("0"), net_tested_income - deemed_tangible_return)

        # §250 deduction (50% for 2024, 37.5% after 2025)
        year = self._input.company.tax_year
        deduction_rate = Decimal("0.50") if year <= 2025 else Decimal("0.375")
        gilti_deduction = round_currency(gilti_inclusion * deduction_rate)
        effective_rate = Decimal("0.105") if year <= 2025 else Decimal("0.13125")

        # §78 gross-up for deemed paid FTC
        gross_up = total_foreign_taxes  # Simplified
        taxable_gilti = gilti_inclusion + gross_up - gilti_deduction

        return {
            "cfc_details": cfc_details,
            "total_tested_income": total_tested_income,
            "total_tested_loss": total_tested_loss,
            "net_tested_income": net_tested_income,
            "total_qbai": total_qbai,
            "deemed_tangible_return": deemed_tangible_return,
            "gilti_inclusion": gilti_inclusion,
            "section_250_deduction_rate": float(deduction_rate),
            "gilti_deduction": gilti_deduction,
            "section_78_gross_up": gross_up,
            "taxable_gilti": taxable_gilti,
            "effective_rate": float(effective_rate),
            "cfc_count": len(self._input.cfcs),
        }

    def _analyze_fdii(self) -> dict:
        """Compute FDII deduction under §250."""
        fdii = self._input.fdii
        dei = to_decimal(fdii.deduction_eligible_income)
        fddei = to_decimal(fdii.foreign_derived_dei)
        qbai = to_decimal(fdii.qbai_domestic)

        deemed_tangible_return = round_currency(qbai * Decimal("0.10"))
        deemed_intangible_income = max(Decimal("0"), dei - deemed_tangible_return)

        if dei > Decimal("0"):
            foreign_ratio = fddei / dei
        else:
            foreign_ratio = Decimal("0")

        fdii_amount = round_currency(deemed_intangible_income * foreign_ratio)

        year = self._input.company.tax_year
        deduction_rate = Decimal("0.375") if year <= 2025 else Decimal("0.21875")
        fdii_deduction = round_currency(fdii_amount * deduction_rate)
        effective_rate = Decimal("0.13125") if year <= 2025 else Decimal("0.16406")

        return {
            "dei": dei,
            "fddei": fddei,
            "domestic_qbai": qbai,
            "deemed_tangible_return": deemed_tangible_return,
            "deemed_intangible_income": deemed_intangible_income,
            "foreign_ratio": float(foreign_ratio),
            "fdii_amount": fdii_amount,
            "deduction_rate": float(deduction_rate),
            "fdii_deduction": fdii_deduction,
            "effective_rate": float(effective_rate),
            "tax_savings": round_currency(fdii_deduction * Decimal("0.21")),
        }

    def _analyze_ftc(self) -> dict:
        """Analyze FTC limitation under §904."""
        worldwide = to_decimal(self._input.worldwide_income)
        us_tax = round_currency(worldwide * Decimal("0.21"))
        basket_results = []

        for ftc in self._input.ftc_data:
            fsi = to_decimal(ftc.foreign_source_income)
            taxes_paid = to_decimal(ftc.foreign_taxes_paid)

            if worldwide > Decimal("0"):
                limitation = round_currency(us_tax * (fsi / worldwide))
            else:
                limitation = Decimal("0")

            credits_allowed = min(taxes_paid, limitation)
            excess_credits = max(Decimal("0"), taxes_paid - limitation)
            excess_limitation = max(Decimal("0"), limitation - taxes_paid)

            basket_results.append({
                "category": ftc.category,
                "foreign_source_income": fsi,
                "foreign_taxes_paid": taxes_paid,
                "limitation": limitation,
                "credits_allowed": credits_allowed,
                "excess_credits": excess_credits,
                "excess_limitation": excess_limitation,
                "effective_foreign_rate": float(taxes_paid / fsi) if fsi > 0 else 0.0,
            })

        total_credits = sum(to_decimal(b["credits_allowed"]) for b in basket_results)
        total_excess_credits = sum(to_decimal(b["excess_credits"]) for b in basket_results)

        return {
            "baskets": basket_results,
            "worldwide_income": worldwide,
            "us_tax_before_ftc": us_tax,
            "total_credits_allowed": total_credits,
            "total_excess_credits": total_excess_credits,
            "net_us_tax": us_tax - total_credits,
            "basket_count": len(basket_results),
        }

    def _analyze_subpart_f(self) -> dict:
        """Analyze Subpart F income inclusions."""
        subpart_f_items = []
        total_subpart_f = Decimal("0")

        for cfc in self._input.cfcs:
            sf = to_decimal(cfc.subpart_f_income)
            if sf > Decimal("0"):
                subpart_f_items.append({
                    "cfc_name": cfc.name,
                    "jurisdiction": cfc.jurisdiction,
                    "subpart_f_income": sf,
                    "foreign_taxes": cfc.foreign_taxes_paid,
                })
                total_subpart_f += sf

        return {
            "items": subpart_f_items,
            "total_subpart_f": total_subpart_f,
            "count": len(subpart_f_items),
        }

    def _generate_findings(self, gilti, fdii, ftc, subpart_f) -> list:
        findings = []

        if to_decimal(gilti["gilti_inclusion"]) > Decimal("0"):
            findings.append({
                "area": "GILTI Inclusion",
                "description": f"GILTI inclusion of {format_currency(gilti['gilti_inclusion'])} "
                               f"with §250 deduction of {format_currency(gilti['gilti_deduction'])} "
                               f"(effective rate: {gilti['effective_rate']*100:.1f}%)",
                "amount": gilti["gilti_inclusion"],
                "risk_level": "high",
                "recommendation": "Review QBAI to maximize deemed tangible income return; consider GILTI high-tax exclusion",
            })

        if to_decimal(fdii["fdii_deduction"]) > Decimal("0"):
            findings.append({
                "area": "FDII Deduction",
                "description": f"FDII deduction of {format_currency(fdii['fdii_deduction'])} — "
                               f"effective rate on foreign-derived income: {fdii['effective_rate']*100:.3f}%",
                "amount": fdii["fdii_deduction"],
                "risk_level": "medium",
                "recommendation": "Verify FDDEI documentation; ensure substantiation of foreign use",
            })

        if to_decimal(ftc["total_excess_credits"]) > Decimal("0"):
            findings.append({
                "area": "Excess Foreign Tax Credits",
                "description": f"Excess FTCs of {format_currency(ftc['total_excess_credits'])} — "
                               f"carryforward available (1yr back / 10yr forward)",
                "amount": ftc["total_excess_credits"],
                "risk_level": "medium",
                "recommendation": "Review expense allocation under §861 to maximize FTC limitation; consider cross-crediting opportunities",
            })

        if to_decimal(subpart_f["total_subpart_f"]) > Decimal("0"):
            findings.append({
                "area": "Subpart F Income",
                "description": f"Total Subpart F income: {format_currency(subpart_f['total_subpart_f'])}",
                "amount": subpart_f["total_subpart_f"],
                "risk_level": "medium",
                "recommendation": "Review for high-tax exception; verify CFC status and US shareholder determination",
            })

        findings.sort(key=lambda f: ({"high": 0, "medium": 1, "low": 2}.get(f["risk_level"], 3),
                                     -abs(to_decimal(f["amount"]))))
        return findings

    def _generate_phase2_recommendations(self, findings) -> list:
        recs = [
            {"priority": 1, "area": "CFC Analysis",
             "description": "Obtain detailed CFC-by-CFC tested income, QBAI, and foreign tax data",
             "data_needed": "Form 5471, Form 8992, CFC financials, E&P computations"},
            {"priority": 2, "area": "FTC Limitation",
             "description": "Perform detailed §861 expense allocation and apportionment",
             "data_needed": "R&D expense detail, interest expense, SG&A allocation basis, asset values"},
        ]

        if any(f["area"] == "FDII Deduction" for f in findings):
            recs.append({"priority": 3, "area": "FDII Substantiation",
                        "description": "Review FDDEI documentation and foreign-use substantiation",
                        "data_needed": "Export sales data, service agreements, customer locations"})

        recs.append({"priority": 4, "area": "Transfer Pricing",
                    "description": "Review intercompany pricing under §482 and documentation",
                    "data_needed": "Transfer pricing study, intercompany agreements, benchmarking analysis"})

        return recs
