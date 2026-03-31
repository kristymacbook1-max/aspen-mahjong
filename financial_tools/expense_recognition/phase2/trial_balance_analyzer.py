"""Phase 2 Expense Recognition Analyzer — Trial Balance / Tax Return Analysis.

Uses trial balance, tax return data, and work papers to perform detailed
expense recognition analysis including book-tax difference identification,
§461(h) economic performance testing, M-1/M-3 adjustment computation, and
DTA/DTL impact calculations.
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
from revenue_recognition.utils.entity_types import get_entity_config, EntityConfig


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TrialBalanceAccount:
    account_number: str
    account_name: str
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    category: str = ""          # expense / liability / asset / equity
    subcategory: str = ""       # cogs / sga / compensation / interest / rd / depreciation / other
    tax_treatment: str = ""     # deductible / capitalized / limited / deferred / permanent


@dataclass
class ExpenseAccountMapping:
    account_number: str
    book_description: str = ""
    tax_line: str = ""           # e.g. "Line 26 - Other deductions"
    form_schedule: str = ""      # e.g. "1120 Pg 1", "Sch M-1"
    tax_amount: Decimal = Decimal("0")
    book_tax_difference: Decimal = Decimal("0")
    difference_type: str = ""    # temporary / permanent
    irc_section: str = ""
    notes: str = ""


@dataclass
class AccruedLiabilityRollforward:
    liability_name: str
    beginning_balance: Decimal = Decimal("0")
    additions: Decimal = Decimal("0")
    payments_settlements: Decimal = Decimal("0")
    ending_balance: Decimal = Decimal("0")
    tax_deduction_current_year: Decimal = Decimal("0")
    economic_performance_category: str = ""  # payment / service / property
    timing_difference: Decimal = Decimal("0")


@dataclass
class TaxReturnExpenseData:
    entity_type: str = "c_corp"
    form_type: str = "1120"
    total_deductions: Decimal = Decimal("0")
    cogs_claimed: Decimal = Decimal("0")
    compensation_deducted: Decimal = Decimal("0")
    interest_deducted: Decimal = Decimal("0")
    depreciation_deducted: Decimal = Decimal("0")
    rd_amortization: Decimal = Decimal("0")
    other_deductions: Decimal = Decimal("0")
    section_162m_addback: Decimal = Decimal("0")
    section_163j_disallowed: Decimal = Decimal("0")
    section_267_deferred: Decimal = Decimal("0")


@dataclass
class WorkPaperExpenseItem:
    description: str
    book_amount: Decimal = Decimal("0")
    tax_amount: Decimal = Decimal("0")
    difference: Decimal = Decimal("0")
    difference_type: str = ""     # temporary / permanent
    irc_section: str = ""
    m1_adjustment: Decimal = Decimal("0")
    category: str = ""
    recommendation: str = ""
    confidence_level: str = ""    # should / more_likely_than_not / substantial_authority


@dataclass
class Phase2ExpenseInput:
    company_name: str = ""
    entity_type: str = "c_corp"
    fiscal_year: int = 2024
    total_assets: Decimal = Decimal("0")
    trial_balance_accounts: List[TrialBalanceAccount] = field(default_factory=list)
    expense_mappings: List[ExpenseAccountMapping] = field(default_factory=list)
    accrued_liability_rollforwards: List[AccruedLiabilityRollforward] = field(default_factory=list)
    tax_return_data: TaxReturnExpenseData = field(default_factory=TaxReturnExpenseData)
    work_paper_items: List[WorkPaperExpenseItem] = field(default_factory=list)
    phase1_findings: List[Dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class TrialBalanceExpenseAnalyzer:
    """Phase 2 analyzer: detailed expense recognition from trial balance and
    tax return data."""

    def analyze(self, inp: Phase2ExpenseInput) -> dict:
        self._input = inp
        self._entity = get_entity_config(inp.entity_type, inp.total_assets)

        book_tax = self._analyze_book_tax_differences()
        ep_detail = self._analyze_economic_performance_detail()
        prepaid = self._analyze_prepaid_expenses_detail()
        comp = self._analyze_compensation_detail()
        interest = self._analyze_interest_detail()
        rd = self._analyze_rd_detail()
        s267 = self._analyze_section_267()
        reserves = self._analyze_reserves_detail()
        m1 = self._compute_m1_adjustments(book_tax, ep_detail, comp, interest, rd, s267, reserves)
        tax_impact = self._compute_total_tax_impact(m1)
        findings = self._generate_findings(book_tax, ep_detail, comp, interest, rd, s267, reserves)
        roadmap = self._generate_phase3_roadmap(findings)

        return {
            "company_name": inp.company_name,
            "entity_config": self._entity,
            "fiscal_year": inp.fiscal_year,
            "book_tax_differences": book_tax,
            "economic_performance": ep_detail,
            "prepaid_detail": prepaid,
            "compensation": comp,
            "interest": interest,
            "rd": rd,
            "section_267": s267,
            "reserves": reserves,
            "m1_adjustments": m1,
            "tax_impact": tax_impact,
            "findings": findings,
            "phase3_roadmap": roadmap,
            "tax_return_data": inp.tax_return_data,
        }

    # ---- Book-Tax Differences ----

    def _analyze_book_tax_differences(self) -> dict:
        differences = []
        total_temporary = Decimal("0")
        total_permanent = Decimal("0")

        for mapping in self._input.expense_mappings:
            diff = to_decimal(mapping.book_tax_difference)
            if diff == 0:
                continue
            diff_type = (mapping.difference_type or "temporary").lower()
            differences.append({
                "account": mapping.account_number,
                "description": mapping.book_description,
                "tax_line": mapping.tax_line,
                "book_tax_difference": diff,
                "type": diff_type,
                "irc_section": mapping.irc_section,
                "notes": mapping.notes,
            })
            if diff_type == "temporary":
                total_temporary += diff
            else:
                total_permanent += diff

        # Also scan TB accounts for unmapped differences
        mapped_accounts = {m.account_number for m in self._input.expense_mappings}
        for acct in self._input.trial_balance_accounts:
            if acct.account_number in mapped_accounts:
                continue
            if acct.category != "expense":
                continue
            book_amt = to_decimal(acct.debit) - to_decimal(acct.credit)
            if acct.tax_treatment in ("limited", "deferred", "permanent"):
                differences.append({
                    "account": acct.account_number,
                    "description": f"{acct.account_name} (unmapped)",
                    "tax_line": "TBD",
                    "book_tax_difference": book_amt,
                    "type": "temporary" if acct.tax_treatment != "permanent" else "permanent",
                    "irc_section": "",
                    "notes": "Identified from TB — needs mapping",
                })
                if acct.tax_treatment != "permanent":
                    total_temporary += book_amt
                else:
                    total_permanent += book_amt

        return {
            "items": differences,
            "total_temporary": total_temporary,
            "total_permanent": total_permanent,
            "total": total_temporary + total_permanent,
            "count": len(differences),
        }

    # ---- Economic Performance Detail ----

    def _analyze_economic_performance_detail(self) -> dict:
        results = []

        for rf in self._input.accrued_liability_rollforwards:
            beg = to_decimal(rf.beginning_balance)
            add = to_decimal(rf.additions)
            pay = to_decimal(rf.payments_settlements)
            end = to_decimal(rf.ending_balance)
            tax_ded = to_decimal(rf.tax_deduction_current_year)
            book_expense = add  # book expense = additions to accrual
            timing = book_expense - tax_ded

            ep_cat = (rf.economic_performance_category or "").lower()
            if ep_cat == "payment":
                ep_rule = "Deductible when paid — tax deduction = payments/settlements"
                expected_tax = pay
            elif ep_cat == "service":
                ep_rule = "Deductible when services provided"
                expected_tax = tax_ded
            elif ep_cat == "property":
                ep_rule = "Deductible when property provided"
                expected_tax = tax_ded
            else:
                ep_rule = "Determine applicable EP category"
                expected_tax = tax_ded

            results.append({
                "name": rf.liability_name,
                "beginning_balance": beg,
                "additions": add,
                "payments": pay,
                "ending_balance": end,
                "book_expense": book_expense,
                "tax_deduction": tax_ded,
                "expected_tax_deduction": expected_tax,
                "timing_difference": timing,
                "ep_category": rf.economic_performance_category,
                "ep_rule": ep_rule,
                "variance_from_expected": tax_ded - expected_tax,
            })

        total_timing = sum(to_decimal(r["timing_difference"]) for r in results)

        return {
            "items": results,
            "total_timing_difference": total_timing,
            "count": len(results),
        }

    # ---- Prepaid Detail ----

    def _analyze_prepaid_expenses_detail(self) -> dict:
        prepaid_accounts = [
            a for a in self._input.trial_balance_accounts
            if a.subcategory == "prepaid" or "prepaid" in a.account_name.lower()
        ]
        items = []
        for acct in prepaid_accounts:
            balance = to_decimal(acct.debit) - to_decimal(acct.credit)
            items.append({
                "account": acct.account_number,
                "name": acct.account_name,
                "balance": balance,
                "tax_treatment": acct.tax_treatment,
            })

        return {
            "items": items,
            "total_prepaid": sum(to_decimal(i["balance"]) for i in items),
            "count": len(items),
        }

    # ---- Compensation Detail ----

    def _analyze_compensation_detail(self) -> dict:
        comp_accounts = [
            a for a in self._input.trial_balance_accounts
            if a.subcategory == "compensation"
        ]
        total_book_comp = sum(
            to_decimal(a.debit) - to_decimal(a.credit) for a in comp_accounts
        )
        tax_comp = to_decimal(self._input.tax_return_data.compensation_deducted)
        s162m = to_decimal(self._input.tax_return_data.section_162m_addback)

        return {
            "accounts": [
                {"number": a.account_number, "name": a.account_name,
                 "amount": to_decimal(a.debit) - to_decimal(a.credit)}
                for a in comp_accounts
            ],
            "total_book_compensation": total_book_comp,
            "tax_compensation_deducted": tax_comp,
            "section_162m_addback": s162m,
            "book_tax_difference": total_book_comp - tax_comp,
            "timing_component": total_book_comp - tax_comp - s162m,
            "permanent_component": s162m,
        }

    # ---- Interest Detail ----

    def _analyze_interest_detail(self) -> dict:
        interest_accounts = [
            a for a in self._input.trial_balance_accounts
            if a.subcategory == "interest"
        ]
        total_book = sum(
            to_decimal(a.debit) - to_decimal(a.credit) for a in interest_accounts
        )
        tax_deducted = to_decimal(self._input.tax_return_data.interest_deducted)
        disallowed = to_decimal(self._input.tax_return_data.section_163j_disallowed)

        return {
            "accounts": [
                {"number": a.account_number, "name": a.account_name,
                 "amount": to_decimal(a.debit) - to_decimal(a.credit)}
                for a in interest_accounts
            ],
            "total_book_interest": total_book,
            "tax_interest_deducted": tax_deducted,
            "section_163j_disallowed": disallowed,
            "book_tax_difference": total_book - tax_deducted,
        }

    # ---- R&D Detail ----

    def _analyze_rd_detail(self) -> dict:
        rd_accounts = [
            a for a in self._input.trial_balance_accounts
            if a.subcategory == "rd" or "r&d" in a.account_name.lower()
            or "research" in a.account_name.lower()
        ]
        total_book = sum(
            to_decimal(a.debit) - to_decimal(a.credit) for a in rd_accounts
        )
        tax_amort = to_decimal(self._input.tax_return_data.rd_amortization)

        return {
            "accounts": [
                {"number": a.account_number, "name": a.account_name,
                 "amount": to_decimal(a.debit) - to_decimal(a.credit)}
                for a in rd_accounts
            ],
            "total_book_rd": total_book,
            "tax_amortization": tax_amort,
            "book_tax_difference": total_book - tax_amort,
        }

    # ---- §267 ----

    def _analyze_section_267(self) -> dict:
        deferred = to_decimal(self._input.tax_return_data.section_267_deferred)
        items = [
            wp for wp in self._input.work_paper_items
            if "267" in (wp.irc_section or "")
        ]
        return {
            "total_deferred": deferred,
            "work_paper_items": [
                {
                    "description": wp.description,
                    "book_amount": wp.book_amount,
                    "tax_amount": wp.tax_amount,
                    "difference": wp.difference,
                    "recommendation": wp.recommendation,
                }
                for wp in items
            ],
            "count": len(items),
        }

    # ---- Reserves Detail ----

    def _analyze_reserves_detail(self) -> dict:
        reserve_items = [
            wp for wp in self._input.work_paper_items
            if wp.category in ("reserve", "contingency", "accrual")
        ]
        return {
            "items": [
                {
                    "description": wp.description,
                    "book_amount": wp.book_amount,
                    "tax_amount": wp.tax_amount,
                    "difference": wp.difference,
                    "type": wp.difference_type,
                    "irc_section": wp.irc_section,
                    "recommendation": wp.recommendation,
                    "confidence": wp.confidence_level,
                }
                for wp in reserve_items
            ],
            "total_difference": sum(to_decimal(wp.difference) for wp in reserve_items),
            "count": len(reserve_items),
        }

    # ---- M-1/M-3 Adjustments ----

    def _compute_m1_adjustments(self, book_tax, ep_detail, comp, interest, rd,
                                s267, reserves) -> dict:
        adjustments = []

        # From mapped book-tax differences
        for item in book_tax["items"]:
            adjustments.append({
                "description": item["description"],
                "book_amount": Decimal("0"),
                "tax_amount": Decimal("0"),
                "adjustment": item["book_tax_difference"],
                "type": item["type"],
                "irc_section": item["irc_section"],
                "source": "Book-Tax Mapping",
            })

        # Economic performance timing
        for item in ep_detail["items"]:
            td = to_decimal(item["timing_difference"])
            if td != 0:
                adjustments.append({
                    "description": f"EP Timing — {item['name']}",
                    "book_amount": item["book_expense"],
                    "tax_amount": item["tax_deduction"],
                    "adjustment": td,
                    "type": "temporary",
                    "irc_section": "§461(h)",
                    "source": "Economic Performance",
                })

        # Compensation — §162(m) permanent
        if to_decimal(comp["permanent_component"]) != 0:
            adjustments.append({
                "description": "§162(m) Executive Compensation Disallowance",
                "book_amount": comp["total_book_compensation"],
                "tax_amount": comp["tax_compensation_deducted"],
                "adjustment": comp["permanent_component"],
                "type": "permanent",
                "irc_section": "§162(m)",
                "source": "Compensation",
            })

        # Compensation — timing
        if to_decimal(comp["timing_component"]) != 0:
            adjustments.append({
                "description": "Compensation Timing (deferred comp, bonuses)",
                "book_amount": Decimal("0"),
                "tax_amount": Decimal("0"),
                "adjustment": comp["timing_component"],
                "type": "temporary",
                "irc_section": "§404(a)(5)",
                "source": "Compensation",
            })

        # §163(j)
        disallowed = to_decimal(interest["section_163j_disallowed"])
        if disallowed != 0:
            adjustments.append({
                "description": "§163(j) Business Interest Limitation",
                "book_amount": interest["total_book_interest"],
                "tax_amount": interest["tax_interest_deducted"],
                "adjustment": disallowed,
                "type": "temporary",
                "irc_section": "§163(j)",
                "source": "Interest",
            })

        # §174
        rd_diff = to_decimal(rd["book_tax_difference"])
        if rd_diff != 0:
            adjustments.append({
                "description": "§174 R&D Capitalization",
                "book_amount": rd["total_book_rd"],
                "tax_amount": rd["tax_amortization"],
                "adjustment": rd_diff,
                "type": "temporary",
                "irc_section": "§174",
                "source": "R&D",
            })

        # §267
        s267_deferred = to_decimal(s267["total_deferred"])
        if s267_deferred != 0:
            adjustments.append({
                "description": "§267 Related Party Deduction Deferral",
                "book_amount": Decimal("0"),
                "tax_amount": Decimal("0"),
                "adjustment": s267_deferred,
                "type": "temporary",
                "irc_section": "§267",
                "source": "Related Party",
            })

        total_temp = sum(to_decimal(a["adjustment"]) for a in adjustments if a["type"] == "temporary")
        total_perm = sum(to_decimal(a["adjustment"]) for a in adjustments if a["type"] == "permanent")
        rate = Decimal(str(self._entity.statutory_rate))

        return {
            "adjustments": adjustments,
            "total_temporary": total_temp,
            "total_permanent": total_perm,
            "total_adjustments": total_temp + total_perm,
            "dta_impact": round_currency(total_temp * rate) if total_temp < 0 else Decimal("0"),
            "dtl_impact": round_currency(total_temp * rate) if total_temp > 0 else Decimal("0"),
            "count": len(adjustments),
        }

    # ---- Total Tax Impact ----

    def _compute_total_tax_impact(self, m1) -> dict:
        rate = Decimal(str(self._entity.statutory_rate))
        temp = to_decimal(m1["total_temporary"])
        perm = to_decimal(m1["total_permanent"])

        return {
            "total_temporary_differences": temp,
            "total_permanent_differences": perm,
            "statutory_rate": float(rate),
            "temporary_tax_impact": round_currency(temp * rate),
            "permanent_tax_impact": round_currency(perm * rate),
            "total_tax_impact": round_currency((temp + perm) * rate),
            "net_dta_dtl": "DTA" if temp < 0 else ("DTL" if temp > 0 else "None"),
        }

    # ---- Findings ----

    def _generate_findings(self, book_tax, ep_detail, comp, interest, rd, s267, reserves) -> list:
        findings = []

        for item in book_tax["items"]:
            diff = abs(to_decimal(item["book_tax_difference"]))
            if diff > Decimal("100000"):
                risk = "high" if diff > Decimal("5000000") else ("medium" if diff > Decimal("1000000") else "low")
                findings.append({
                    "area": "Book-Tax Difference",
                    "description": item["description"],
                    "book_tax_difference": item["book_tax_difference"],
                    "type": item["type"],
                    "irc_section": item["irc_section"],
                    "risk_level": risk,
                    "recommendation": item.get("notes", "Review for accuracy"),
                })

        for item in ep_detail["items"]:
            td = to_decimal(item["timing_difference"])
            if abs(td) > Decimal("100000"):
                findings.append({
                    "area": "Economic Performance",
                    "description": f"{item['name']}: {item['ep_rule']}",
                    "book_tax_difference": td,
                    "type": "temporary",
                    "irc_section": "§461(h)",
                    "risk_level": "high" if abs(td) > Decimal("5000000") else "medium",
                    "recommendation": f"Verify {item['ep_category']} EP timing with supporting documents",
                })

        if to_decimal(comp["permanent_component"]) > Decimal("0"):
            findings.append({
                "area": "Compensation",
                "description": f"§162(m) permanent disallowance: {format_currency(comp['permanent_component'])}",
                "book_tax_difference": comp["permanent_component"],
                "type": "permanent",
                "irc_section": "§162(m)",
                "risk_level": "high",
                "recommendation": "Verify covered employee identification; review compensation structures",
            })

        if to_decimal(interest["section_163j_disallowed"]) > 0:
            findings.append({
                "area": "Interest",
                "description": f"§163(j) disallowed: {format_currency(interest['section_163j_disallowed'])}",
                "book_tax_difference": interest["section_163j_disallowed"],
                "type": "temporary",
                "irc_section": "§163(j)",
                "risk_level": "high",
                "recommendation": "Review ATI computation; evaluate exceptions and elections",
            })

        if to_decimal(rd["book_tax_difference"]) > Decimal("1000000"):
            findings.append({
                "area": "R&D",
                "description": f"§174 book-tax diff: {format_currency(rd['book_tax_difference'])}",
                "book_tax_difference": rd["book_tax_difference"],
                "type": "temporary",
                "irc_section": "§174",
                "risk_level": "medium",
                "recommendation": "Verify domestic/foreign split; review amortization schedules",
            })

        findings.sort(key=lambda f: (
            {"high": 0, "medium": 1, "low": 2}.get(f["risk_level"], 3),
            -abs(to_decimal(f["book_tax_difference"])),
        ))

        return findings

    # ---- Phase 3 Roadmap ----

    def _generate_phase3_roadmap(self, findings) -> list:
        roadmap = [
            {
                "priority": 1,
                "area": "Vendor Contract Review",
                "description": "Review vendor contracts for EP category classification and timing analysis",
                "data_needed": "Top vendor contracts, service agreements, purchase orders",
            },
            {
                "priority": 2,
                "area": "Reserve Documentation",
                "description": "Test all-events and EP requirements per reserve with supporting documentation",
                "data_needed": "Reserve schedules, legal opinions, settlement documents",
            },
        ]

        if any(f["area"] == "Compensation" for f in findings):
            roadmap.append({
                "priority": 3,
                "area": "Compensation Contracts",
                "description": "Review employment agreements, deferred comp plans, equity plans",
                "data_needed": "Employment agreements, plan documents, vesting schedules",
            })

        if any(f["area"] == "Economic Performance" for f in findings):
            roadmap.append({
                "priority": 4,
                "area": "Invoice-Level EP Testing",
                "description": "Test economic performance at invoice level for material accruals",
                "data_needed": "AP aging detail, invoice copies, payment records",
            })

        return roadmap
