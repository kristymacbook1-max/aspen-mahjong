"""Expense Recognition Position Analyzer.

Analyzes tax positions related to expense recognition and generates
technical memoranda with supporting and adverse authorities.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from revenue_recognition.utils.currency_helpers import to_decimal, format_currency

from .authorities import (
    get_expense_authority_lookup,
    ECONOMIC_PERFORMANCE_AUTHORITIES,
    PREPAID_EXPENSE_AUTHORITIES,
    RECURRING_ITEM_AUTHORITIES,
    COMPENSATION_AUTHORITIES,
    INTEREST_LIMITATION_AUTHORITIES,
    RESEARCH_DEVELOPMENT_AUTHORITIES,
    RELATED_PARTY_AUTHORITIES,
)
from .authorities.base import TechnicalAuthority, AuthorityLookup


@dataclass
class TaxPosition:
    """A specific expense recognition tax position."""
    position_id: str
    title: str
    description: str
    irc_section: str
    amount: float = 0.0
    confidence_level: str = "more_likely_than_not"  # should / more_likely_than_not / substantial_authority
    position_type: str = ""        # economic_performance / prepaid / recurring_item / compensation / interest / rd / related_party
    supporting_authorities: List[TechnicalAuthority] = field(default_factory=list)
    adverse_authorities: List[TechnicalAuthority] = field(default_factory=list)
    analysis: str = ""
    recommendation: str = ""
    risk_level: str = "medium"


@dataclass
class TechnicalMemo:
    """A technical memorandum documenting one or more positions."""
    company_name: str
    prepared_by: str = "Tax Analysis Tool"
    date: str = ""
    positions: List[TaxPosition] = field(default_factory=list)
    executive_summary: str = ""
    overall_confidence: str = ""


class PositionAnalyzer:
    """Analyzes expense recognition positions with supporting authorities."""

    def __init__(self):
        self._lookup = get_expense_authority_lookup()

    def analyze_economic_performance(self, liability_name: str, ep_category: str,
                                     amount: float, is_recurring: bool = False) -> TaxPosition:
        """Analyze an economic performance position."""
        topics = ["economic performance", ep_category + " liability"]
        if is_recurring:
            topics.append("recurring item exception")

        authorities = self._lookup.for_position(topics)

        if ep_category == "payment":
            analysis = (
                f"The liability '{liability_name}' is classified as a payment liability under "
                f"§461(h)(2)(C). Economic performance occurs when payment is made. "
                f"The all-events test must also be met (liability fixed and determinable). "
            )
            if is_recurring:
                analysis += (
                    "The recurring item exception under §461(h)(3) may allow earlier deduction "
                    "if the liability is recurring, consistently treated, not material (or better matching), "
                    "and EP occurs within 8½ months after year end."
                )
            confidence = "should" if not is_recurring else "more_likely_than_not"
        elif ep_category == "service":
            analysis = (
                f"The liability '{liability_name}' arises from services provided TO the taxpayer. "
                f"Under §461(h)(2)(A)(i), economic performance occurs as services are provided. "
                f"Deduction is allowable as services are rendered, regardless of payment timing."
            )
            confidence = "should"
        elif ep_category == "property":
            analysis = (
                f"The liability '{liability_name}' arises from property provided TO the taxpayer. "
                f"Under §461(h)(2)(A)(ii), economic performance occurs as property is provided. "
                f"Deduction is allowable upon receipt of property."
            )
            confidence = "should"
        else:
            analysis = f"The economic performance category for '{liability_name}' needs determination."
            confidence = "substantial_authority"

        return TaxPosition(
            position_id=f"EP-{liability_name[:20].upper().replace(' ', '-')}",
            title=f"Economic Performance — {liability_name}",
            description=f"Deduction timing for {liability_name} under §461(h)",
            irc_section="§461(h)",
            amount=amount,
            confidence_level=confidence,
            position_type="economic_performance",
            supporting_authorities=authorities["supporting"],
            adverse_authorities=authorities["adverse"],
            analysis=analysis,
            recommendation=f"Classify as {ep_category} liability; {'apply recurring item exception' if is_recurring else 'deduct per EP rules'}",
            risk_level="low" if confidence == "should" else "medium",
        )

    def analyze_prepaid_expense(self, expense_name: str, amount: float,
                                period_months: int) -> TaxPosition:
        """Analyze a prepaid expense position under the 12-month rule."""
        topics = ["12-month rule", "prepaid expenses"]
        authorities = self._lookup.for_position(topics)

        qualifies = period_months <= 12
        if qualifies:
            analysis = (
                f"The prepaid expense '{expense_name}' covers a period of {period_months} months, "
                f"which does not exceed 12 months. Under Treas. Reg. §1.263(a)-4(f), "
                f"the taxpayer is not required to capitalize this amount, provided the benefit "
                f"does not extend beyond the end of the taxable year following the year of payment."
            )
            confidence = "should"
            recommendation = "Deduct under 12-month rule safe harbor"
        else:
            analysis = (
                f"The prepaid expense '{expense_name}' covers {period_months} months (>12). "
                f"It does not qualify for the 12-month rule and must be capitalized under "
                f"Treas. Reg. §1.263(a)-4 and amortized over the benefit period."
            )
            confidence = "should"
            recommendation = "Capitalize and amortize over benefit period"

        return TaxPosition(
            position_id=f"PP-{expense_name[:20].upper().replace(' ', '-')}",
            title=f"Prepaid Expense — {expense_name}",
            description=f"12-month rule analysis for {expense_name}",
            irc_section="Reg. §1.263(a)-4(f)",
            amount=amount,
            confidence_level=confidence,
            position_type="prepaid",
            supporting_authorities=authorities["supporting"],
            adverse_authorities=authorities["adverse"],
            analysis=analysis,
            recommendation=recommendation,
            risk_level="low",
        )

    def analyze_compensation(self, employee_name: str, total_comp: float,
                             is_covered: bool) -> TaxPosition:
        """Analyze a §162(m) compensation position."""
        topics = ["162(m)", "covered employee"] if is_covered else ["reasonable compensation"]
        authorities = self._lookup.for_position(topics)

        if is_covered and total_comp > 1_000_000:
            disallowed = total_comp - 1_000_000
            analysis = (
                f"{employee_name} is a covered employee under §162(m)(3). "
                f"Total compensation of {format_currency(total_comp)} exceeds the $1M limit. "
                f"The excess of {format_currency(disallowed)} is a permanent disallowance. "
                f"Post-TCJA, there is no performance-based compensation exception."
            )
            confidence = "should"
            recommendation = "Permanent M-1 adjustment required"
            risk = "high"
        elif is_covered:
            analysis = (
                f"{employee_name} is a covered employee but compensation of "
                f"{format_currency(total_comp)} does not exceed $1M. No disallowance."
            )
            confidence = "should"
            recommendation = "No adjustment needed; monitor for future years"
            risk = "low"
        else:
            analysis = (
                f"{employee_name} is not a covered employee. Compensation of "
                f"{format_currency(total_comp)} is deductible if reasonable under §162(a)(1)."
            )
            confidence = "should"
            recommendation = "Document reasonableness; no §162(m) limitation"
            risk = "low"

        return TaxPosition(
            position_id=f"COMP-{employee_name[:15].upper().replace(' ', '-')}",
            title=f"Compensation — {employee_name}",
            description=f"§162(m) / reasonableness analysis for {employee_name}",
            irc_section="§162(m)" if is_covered else "§162(a)(1)",
            amount=total_comp,
            confidence_level=confidence,
            position_type="compensation",
            supporting_authorities=authorities["supporting"],
            adverse_authorities=authorities["adverse"],
            analysis=analysis,
            recommendation=recommendation,
            risk_level=risk,
        )

    def analyze_interest_limitation(self, total_interest: float, ati: float,
                                    bii: float = 0) -> TaxPosition:
        """Analyze §163(j) interest limitation position."""
        topics = ["163(j)", "interest limitation"]
        authorities = self._lookup.for_position(topics)

        limit = bii + (ati * 0.30)
        disallowed = max(0, total_interest - limit)

        analysis = (
            f"Total business interest expense: {format_currency(total_interest)}. "
            f"ATI: {format_currency(ati)}. 30% ATI: {format_currency(ati * 0.30)}. "
            f"BII: {format_currency(bii)}. "
            f"Deductible amount: {format_currency(min(total_interest, limit))}. "
        )
        if disallowed > 0:
            analysis += f"Disallowed: {format_currency(disallowed)} (carries forward indefinitely under §163(j)(2))."
            risk = "high"
        else:
            analysis += "Interest is fully deductible — no limitation applies."
            risk = "low"

        return TaxPosition(
            position_id="INT-163J",
            title="§163(j) Business Interest Limitation",
            description="Business interest deduction limitation computation",
            irc_section="§163(j)",
            amount=total_interest,
            confidence_level="should",
            position_type="interest",
            supporting_authorities=authorities["supporting"],
            adverse_authorities=authorities["adverse"],
            analysis=analysis,
            recommendation="Carryforward disallowed interest; evaluate elections" if disallowed > 0 else "No action needed",
            risk_level=risk,
        )

    def analyze_rd_capitalization(self, total_rd: float, domestic: float,
                                  foreign: float) -> TaxPosition:
        """Analyze §174 R&D capitalization position."""
        topics = ["174", "R&D capitalization"]
        authorities = self._lookup.for_position(topics)

        dom_amort = domestic / 5 if domestic else 0
        for_amort = foreign / 15 if foreign else 0
        total_amort = dom_amort + for_amort
        book_tax_diff = total_rd - total_amort

        analysis = (
            f"Total R&D expenditures: {format_currency(total_rd)} "
            f"(domestic: {format_currency(domestic)}, foreign: {format_currency(foreign)}). "
            f"Under post-2022 §174, all specified R&E expenditures must be capitalized and "
            f"amortized (5 years domestic, 15 years foreign). "
            f"Current year amortization: {format_currency(total_amort)}. "
            f"Book-tax difference: {format_currency(book_tax_diff)} (temporary — DTA)."
        )

        return TaxPosition(
            position_id="RD-174",
            title="§174 R&D Capitalization",
            description="Mandatory capitalization and amortization of R&E expenditures",
            irc_section="§174",
            amount=total_rd,
            confidence_level="should",
            position_type="rd",
            supporting_authorities=authorities["supporting"],
            adverse_authorities=authorities["adverse"],
            analysis=analysis,
            recommendation="Ensure proper domestic/foreign allocation; verify software dev costs included",
            risk_level="medium" if book_tax_diff > 1_000_000 else "low",
        )

    def analyze_related_party(self, payee_name: str, amount: float,
                              deferred: float) -> TaxPosition:
        """Analyze §267 related party position."""
        topics = ["267", "related party", "matching rule"]
        authorities = self._lookup.for_position(topics)

        if deferred > 0:
            analysis = (
                f"Payment to related party '{payee_name}': {format_currency(amount)}. "
                f"Under §267(a)(2), deduction deferred until includible by payee. "
                f"Deferred amount: {format_currency(deferred)}. "
                f"Verify constructive ownership under §267(b)/(c)."
            )
            risk = "high"
            recommendation = "Align payment timing; document ownership analysis"
        else:
            analysis = (
                f"Payment to related party '{payee_name}': {format_currency(amount)}. "
                f"Amount is includible by payee in matching period — no deferral required."
            )
            risk = "low"
            recommendation = "Document matching; retain payee confirmation"

        return TaxPosition(
            position_id=f"RP-{payee_name[:15].upper().replace(' ', '-')}",
            title=f"§267 Related Party — {payee_name}",
            description=f"Related party matching analysis for {payee_name}",
            irc_section="§267(a)(2)",
            amount=amount,
            confidence_level="should",
            position_type="related_party",
            supporting_authorities=authorities["supporting"],
            adverse_authorities=authorities["adverse"],
            analysis=analysis,
            recommendation=recommendation,
            risk_level=risk,
        )

    def generate_technical_memo(self, company_name: str,
                                positions: List[TaxPosition]) -> TechnicalMemo:
        """Generate a technical memorandum from analyzed positions."""
        from datetime import date
        high_risk = [p for p in positions if p.risk_level == "high"]
        med_risk = [p for p in positions if p.risk_level == "medium"]

        total_amount = sum(p.amount for p in positions)
        summary = (
            f"This memorandum documents {len(positions)} expense recognition tax positions "
            f"for {company_name}, covering total amounts of {format_currency(total_amount)}. "
            f"{len(high_risk)} positions are high-risk, {len(med_risk)} are medium-risk."
        )

        # Determine overall confidence
        if all(p.confidence_level == "should" for p in positions):
            overall = "should"
        elif any(p.confidence_level == "substantial_authority" for p in positions):
            overall = "substantial_authority"
        else:
            overall = "more_likely_than_not"

        return TechnicalMemo(
            company_name=company_name,
            date=str(date.today()),
            positions=positions,
            executive_summary=summary,
            overall_confidence=overall,
        )

    def analyze_all(self, analysis_results: dict) -> TechnicalMemo:
        """Run all position analyses from Phase 1/2/3 results and generate memo."""
        positions = []
        company = analysis_results.get("company_name", analysis_results.get("company", {}).name
                                       if hasattr(analysis_results.get("company", {}), "name")
                                       else "Unknown")

        # Economic performance positions
        ep = analysis_results.get("economic_performance", {})
        for group_key in ["payment_liabilities", "service_liabilities",
                          "property_liabilities", "special_liabilities"]:
            for item in ep.get(group_key, []):
                if abs(to_decimal(item.get("timing_difference", 0))) > 0:
                    cat = group_key.replace("_liabilities", "")
                    pos = self.analyze_economic_performance(
                        item["name"], cat,
                        float(to_decimal(item.get("book_amount", item.get("timing_difference", 0)))),
                    )
                    positions.append(pos)

        # Interest
        il = analysis_results.get("interest_limitation", {})
        if il.get("is_limited"):
            pos = self.analyze_interest_limitation(
                float(to_decimal(il.get("total_interest", 0))),
                float(to_decimal(il.get("adjusted_taxable_income", 0))),
                float(to_decimal(il.get("business_interest_income", 0))),
            )
            positions.append(pos)

        # R&D
        rd = analysis_results.get("rd_capitalization", {})
        if to_decimal(rd.get("total_rd", 0)) > 0:
            pos = self.analyze_rd_capitalization(
                float(to_decimal(rd.get("total_rd", 0))),
                float(to_decimal(rd.get("domestic_rd", 0))),
                float(to_decimal(rd.get("foreign_rd", 0))),
            )
            positions.append(pos)

        # Related party
        rp = analysis_results.get("related_party", {})
        for item in rp.get("items", []):
            if to_decimal(item.get("deferred", 0)) > 0:
                pos = self.analyze_related_party(
                    item["payee_name"],
                    float(to_decimal(item["amount"])),
                    float(to_decimal(item["deferred"])),
                )
                positions.append(pos)

        return self.generate_technical_memo(company, positions)
