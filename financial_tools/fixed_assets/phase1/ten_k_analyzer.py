"""Phase 1 Fixed Asset / Depreciation Analyzer — 10-K / Public Data Analysis.

Analyzes fixed asset depreciation for book-tax differences, §168 MACRS
classification, §179 expensing, bonus depreciation (§168(k)), §1031
like-kind exchanges, and asset disposition rules.
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
class FixedAssetCategory:
    """Summary of a fixed asset category from 10-K."""
    name: str
    gross_book_value: Decimal = Decimal("0")
    accumulated_depreciation: Decimal = Decimal("0")
    net_book_value: Decimal = Decimal("0")
    book_useful_life_years: int = 0
    book_method: str = ""              # straight_line / declining_balance / units_of_production
    macrs_class: str = ""              # 3yr / 5yr / 7yr / 10yr / 15yr / 20yr / 27.5yr / 39yr
    macrs_method: str = ""             # GDS-200DB / GDS-150DB / GDS-SL / ADS-SL
    bonus_eligible: bool = True
    section_179_eligible: bool = False
    current_year_additions: Decimal = Decimal("0")
    current_year_dispositions: Decimal = Decimal("0")
    book_depreciation_current: Decimal = Decimal("0")
    tax_depreciation_current: Decimal = Decimal("0")


@dataclass
class BonusDepreciationAnalysis:
    total_qualifying_additions: Decimal = Decimal("0")
    bonus_rate: Decimal = Decimal("0.60")   # 60% for 2024, phasing down
    bonus_amount: Decimal = Decimal("0")
    regular_first_year: Decimal = Decimal("0")
    total_first_year_deduction: Decimal = Decimal("0")


@dataclass
class Section179Analysis:
    total_qualifying_property: Decimal = Decimal("0")
    section_179_limit: Decimal = Decimal("1220000")     # 2024 limit
    phase_out_threshold: Decimal = Decimal("3050000")   # 2024
    total_placed_in_service: Decimal = Decimal("0")
    phase_out_reduction: Decimal = Decimal("0")
    available_179: Decimal = Decimal("0")
    elected_179: Decimal = Decimal("0")


@dataclass
class LikeKindExchange:
    description: str
    relinquished_property: str = ""
    replacement_property: str = ""
    fmv_relinquished: Decimal = Decimal("0")
    adjusted_basis_relinquished: Decimal = Decimal("0")
    boot_received: Decimal = Decimal("0")
    gain_recognized: Decimal = Decimal("0")
    deferred_gain: Decimal = Decimal("0")
    replacement_basis: Decimal = Decimal("0")


@dataclass
class Phase1FixedAssetInput:
    company: CompanyProfile = field(default_factory=CompanyProfile)
    asset_categories: List[FixedAssetCategory] = field(default_factory=list)
    bonus_analysis: BonusDepreciationAnalysis = field(default_factory=BonusDepreciationAnalysis)
    section_179: Section179Analysis = field(default_factory=Section179Analysis)
    like_kind_exchanges: List[LikeKindExchange] = field(default_factory=list)
    total_capex: Decimal = Decimal("0")


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class FixedAssetAnalyzer:
    """Phase 1 analyzer for fixed assets and depreciation."""

    def analyze(self, inp: Phase1FixedAssetInput) -> dict:
        self._input = inp
        self._entity = get_entity_config(inp.company.entity_type, inp.company.total_assets)

        depreciation = self._analyze_depreciation()
        bonus = self._analyze_bonus_depreciation()
        s179 = self._analyze_section_179()
        lke = self._analyze_like_kind_exchanges()
        cost_seg = self._identify_cost_segregation_opportunities()
        findings = self._generate_findings(depreciation, bonus, s179, lke, cost_seg)
        roadmap = self._generate_phase2_recommendations(findings)

        return {
            "company": inp.company,
            "entity_config": self._entity,
            "depreciation_analysis": depreciation,
            "bonus_depreciation": bonus,
            "section_179": s179,
            "like_kind_exchanges": lke,
            "cost_segregation": cost_seg,
            "findings": findings,
            "phase2_roadmap": roadmap,
        }

    def _analyze_depreciation(self) -> dict:
        items = []
        total_book = Decimal("0")
        total_tax = Decimal("0")

        for cat in self._input.asset_categories:
            book_dep = to_decimal(cat.book_depreciation_current)
            tax_dep = to_decimal(cat.tax_depreciation_current)
            diff = book_dep - tax_dep

            items.append({
                "name": cat.name,
                "gross_value": cat.gross_book_value,
                "net_book_value": cat.net_book_value,
                "book_life": cat.book_useful_life_years,
                "book_method": cat.book_method,
                "macrs_class": cat.macrs_class,
                "macrs_method": cat.macrs_method,
                "book_depreciation": book_dep,
                "tax_depreciation": tax_dep,
                "difference": diff,
                "bonus_eligible": cat.bonus_eligible,
                "additions": cat.current_year_additions,
                "dispositions": cat.current_year_dispositions,
            })
            total_book += book_dep
            total_tax += tax_dep

        return {
            "items": items,
            "total_book_depreciation": total_book,
            "total_tax_depreciation": total_tax,
            "total_difference": total_book - total_tax,
            "count": len(items),
        }

    def _analyze_bonus_depreciation(self) -> dict:
        ba = self._input.bonus_analysis
        qualifying = to_decimal(ba.total_qualifying_additions)
        rate = to_decimal(ba.bonus_rate)

        # 2024: 60%, 2025: 40%, 2026: 20%, 2027+: 0%
        year = self._input.company.tax_year
        if year <= 2022:
            rate = Decimal("1.00")
        elif year == 2023:
            rate = Decimal("0.80")
        elif year == 2024:
            rate = Decimal("0.60")
        elif year == 2025:
            rate = Decimal("0.40")
        elif year == 2026:
            rate = Decimal("0.20")
        else:
            rate = Decimal("0.00")

        bonus = round_currency(qualifying * rate)

        return {
            "qualifying_additions": qualifying,
            "bonus_rate": float(rate),
            "bonus_rate_pct": f"{float(rate)*100:.0f}%",
            "bonus_amount": bonus,
            "phase_down_note": f"Bonus depreciation is {float(rate)*100:.0f}% for {year} (phasing down from 100% in 2022)",
            "year": year,
        }

    def _analyze_section_179(self) -> dict:
        s = self._input.section_179
        qualifying = to_decimal(s.total_qualifying_property)
        limit = to_decimal(s.section_179_limit)
        threshold = to_decimal(s.phase_out_threshold)
        total_pis = to_decimal(s.total_placed_in_service)

        phase_out = max(Decimal("0"), total_pis - threshold)
        available = max(Decimal("0"), limit - phase_out)
        elected = min(qualifying, available)

        return {
            "qualifying_property": qualifying,
            "limit": limit,
            "phase_out_threshold": threshold,
            "total_placed_in_service": total_pis,
            "phase_out_reduction": phase_out,
            "available": available,
            "elected": elected,
            "is_phased_out": phase_out > 0,
        }

    def _analyze_like_kind_exchanges(self) -> dict:
        results = []
        total_deferred = Decimal("0")

        for lke in self._input.like_kind_exchanges:
            fmv = to_decimal(lke.fmv_relinquished)
            basis = to_decimal(lke.adjusted_basis_relinquished)
            boot = to_decimal(lke.boot_received)
            realized_gain = fmv - basis
            recognized = min(realized_gain, boot) if boot > 0 else Decimal("0")
            deferred = realized_gain - recognized
            replacement_basis = basis + recognized - boot + to_decimal(lke.replacement_basis or Decimal("0"))

            results.append({
                "description": lke.description,
                "relinquished": lke.relinquished_property,
                "replacement": lke.replacement_property,
                "fmv": fmv,
                "basis": basis,
                "realized_gain": realized_gain,
                "boot": boot,
                "recognized_gain": recognized,
                "deferred_gain": deferred,
                "replacement_basis": replacement_basis,
            })
            total_deferred += deferred

        return {
            "items": results,
            "total_deferred_gain": total_deferred,
            "count": len(results),
        }

    def _identify_cost_segregation_opportunities(self) -> dict:
        """Identify potential cost segregation study opportunities."""
        candidates = []
        for cat in self._input.asset_categories:
            macrs = (cat.macrs_class or "").lower()
            if macrs in ("39yr", "27.5yr") and to_decimal(cat.gross_book_value) > Decimal("1000000"):
                candidates.append({
                    "name": cat.name,
                    "gross_value": cat.gross_book_value,
                    "current_class": cat.macrs_class,
                    "potential_reclassification": "5yr, 7yr, or 15yr components (land improvements, fixtures, specialty systems)",
                    "estimated_acceleration": round_currency(to_decimal(cat.gross_book_value) * Decimal("0.20")),
                    "note": "Cost segregation study recommended to reclassify components to shorter MACRS lives",
                })

        return {
            "candidates": candidates,
            "count": len(candidates),
            "total_potential_acceleration": sum(to_decimal(c["estimated_acceleration"]) for c in candidates),
        }

    def _generate_findings(self, depreciation, bonus, s179, lke, cost_seg) -> list:
        findings = []

        diff = to_decimal(depreciation["total_difference"])
        if abs(diff) > Decimal("1000000"):
            findings.append({
                "area": "Book-Tax Depreciation",
                "description": f"Total depreciation difference: {format_currency(diff)}",
                "amount": diff,
                "risk_level": "medium",
                "recommendation": "Verify MACRS classifications; review for missed bonus depreciation",
            })

        if to_decimal(bonus["bonus_amount"]) > Decimal("0"):
            findings.append({
                "area": "Bonus Depreciation",
                "description": f"Bonus depreciation at {bonus['bonus_rate_pct']}: {format_currency(bonus['bonus_amount'])}",
                "amount": bonus["bonus_amount"],
                "risk_level": "low",
                "recommendation": bonus["phase_down_note"],
            })

        if cost_seg["count"] > 0:
            findings.append({
                "area": "Cost Segregation",
                "description": f"{cost_seg['count']} properties may benefit from cost segregation study — potential acceleration: {format_currency(cost_seg['total_potential_acceleration'])}",
                "amount": cost_seg["total_potential_acceleration"],
                "risk_level": "high",
                "recommendation": "Commission cost segregation study for 39-year/27.5-year properties",
            })

        if lke["total_deferred_gain"] > Decimal("0"):
            findings.append({
                "area": "Like-Kind Exchanges",
                "description": f"Deferred gain on §1031 exchanges: {format_currency(lke['total_deferred_gain'])}",
                "amount": lke["total_deferred_gain"],
                "risk_level": "medium",
                "recommendation": "Verify §1031 qualification; track replacement basis",
            })

        findings.sort(key=lambda f: ({"high": 0, "medium": 1, "low": 2}.get(f["risk_level"], 3), -abs(to_decimal(f["amount"]))))
        return findings

    def _generate_phase2_recommendations(self, findings) -> list:
        recs = [
            {"priority": 1, "area": "Fixed Asset Register", "description": "Obtain detailed FAR with MACRS classes, placed-in-service dates, and methods", "data_needed": "Fixed asset register, Form 4562, depreciation schedules"},
            {"priority": 2, "area": "Bonus Depreciation Detail", "description": "Verify bonus depreciation elections and qualified property", "data_needed": "Asset addition detail, placed-in-service dates, property types"},
        ]

        if any(f["area"] == "Cost Segregation" for f in findings):
            recs.append({"priority": 3, "area": "Cost Segregation Study", "description": "Engage cost segregation specialist for qualifying properties", "data_needed": "Building blueprints, construction invoices, appraisals"})

        if any(f["area"] == "Like-Kind Exchanges" for f in findings):
            recs.append({"priority": 4, "area": "§1031 Documentation", "description": "Review §1031 exchange documentation and identification timelines", "data_needed": "Exchange agreements, QI records, identification letters"})

        return recs
