"""Phase 1 Expense Recognition Analyzer — 10-K / Public Data Analysis.

Identifies expense recognition opportunities from publicly available financial
data (10-K filings, proxy statements).  Covers §461(h) economic performance,
prepaid expenses (12-month rule), §162(m) compensation, §163(j) interest
limitation, §174 R&D capitalization, §267 related-party matching, and
reserves/contingencies analysis.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional, Dict
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from revenue_recognition.utils.currency_helpers import (
    to_decimal, round_currency, format_currency, format_millions,
    pct_change, pct_of_total,
)
from revenue_recognition.utils.entity_types import get_entity_config, EntityConfig


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CompanyProfile:
    name: str
    ticker: str = ""
    entity_type: str = "c_corp"          # c_corp | partnership
    fiscal_year_end: str = "12/31"
    total_assets: Decimal = Decimal("0")
    total_revenue: Decimal = Decimal("0")
    industry: str = ""
    tax_year: int = 2024


@dataclass
class ExpenseCategory:
    name: str
    description: str = ""
    book_amount_current: Decimal = Decimal("0")
    book_amount_prior: Decimal = Decimal("0")
    tax_treatment: str = ""              # deductible / capitalized / limited / deferred
    irc_section: str = ""
    economic_performance_category: str = ""  # payment / service / property / special / n/a
    timing_difference: Decimal = Decimal("0")
    is_recurring_item_eligible: bool = False
    method_change_opportunity: str = ""
    risk_level: str = "low"              # high / medium / low


@dataclass
class AccruedLiability:
    name: str
    book_balance_current: Decimal = Decimal("0")
    book_balance_prior: Decimal = Decimal("0")
    tax_deductible_current: Decimal = Decimal("0")
    timing_rule: str = ""                # e.g. "deductible when paid"
    economic_performance_met: bool = False
    all_events_test_met: bool = False
    recurring_item_exception: bool = False


@dataclass
class PrepaidExpense:
    name: str
    amount: Decimal = Decimal("0")
    period_covered_months: int = 0
    qualifies_12_month_rule: bool = False
    current_treatment: str = ""          # capitalized / expensed
    optimal_treatment: str = ""


@dataclass
class CompensationItem:
    name: str
    employee_type: str = "other"         # covered_employee / officer / other
    book_expense: Decimal = Decimal("0")
    tax_deductible: Decimal = Decimal("0")
    section_162m_limited: bool = False
    deferred_comp_rules: str = ""
    timing: str = ""                     # current / deferred


@dataclass
class InterestExpense:
    total_interest: Decimal = Decimal("0")
    business_interest_income: Decimal = Decimal("0")
    floor_plan_interest: Decimal = Decimal("0")
    adjusted_taxable_income: Decimal = Decimal("0")
    limitation_amount: Decimal = Decimal("0")
    disallowed_amount: Decimal = Decimal("0")
    carryforward_available: Decimal = Decimal("0")


@dataclass
class RDExpense:
    total_rd: Decimal = Decimal("0")
    domestic_rd: Decimal = Decimal("0")
    foreign_rd: Decimal = Decimal("0")
    current_year_amortization: Decimal = Decimal("0")
    book_tax_difference: Decimal = Decimal("0")
    amortization_period_domestic: int = 5   # years
    amortization_period_foreign: int = 15


@dataclass
class RelatedPartyExpense:
    payee_name: str
    relationship: str = ""               # e.g. "parent", "subsidiary", "common control"
    amount: Decimal = Decimal("0")
    payee_tax_year_end: str = ""
    amount_includible_by_payee: Decimal = Decimal("0")
    deduction_deferred: Decimal = Decimal("0")


@dataclass
class IncomeStatementExpenses:
    cogs: Decimal = Decimal("0")
    sga: Decimal = Decimal("0")
    rd_expense: Decimal = Decimal("0")
    depreciation_amortization: Decimal = Decimal("0")
    interest_expense: Decimal = Decimal("0")
    restructuring_charges: Decimal = Decimal("0")
    other_expense: Decimal = Decimal("0")
    total_operating_expenses: Decimal = Decimal("0")
    income_tax_expense: Decimal = Decimal("0")


@dataclass
class BalanceSheetLiabilities:
    accounts_payable: Decimal = Decimal("0")
    accrued_liabilities: Decimal = Decimal("0")
    accrued_compensation: Decimal = Decimal("0")
    deferred_revenue: Decimal = Decimal("0")
    current_portion_ltd: Decimal = Decimal("0")
    long_term_debt: Decimal = Decimal("0")
    deferred_tax_liabilities: Decimal = Decimal("0")
    pension_obligations: Decimal = Decimal("0")
    other_liabilities: Decimal = Decimal("0")


@dataclass
class TenKExpenseInput:
    company: CompanyProfile = field(default_factory=CompanyProfile)
    expense_categories: List[ExpenseCategory] = field(default_factory=list)
    accrued_liabilities: List[AccruedLiability] = field(default_factory=list)
    prepaid_expenses: List[PrepaidExpense] = field(default_factory=list)
    compensation_items: List[CompensationItem] = field(default_factory=list)
    interest_expense: InterestExpense = field(default_factory=InterestExpense)
    rd_expense: RDExpense = field(default_factory=RDExpense)
    related_party_expenses: List[RelatedPartyExpense] = field(default_factory=list)
    income_statement: IncomeStatementExpenses = field(default_factory=IncomeStatementExpenses)
    balance_sheet: BalanceSheetLiabilities = field(default_factory=BalanceSheetLiabilities)


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class TenKExpenseAnalyzer:
    """Phase 1 analyzer: identifies expense recognition opportunities from
    publicly available 10-K data."""

    def analyze(self, inp: TenKExpenseInput) -> dict:
        self._input = inp
        self._entity = get_entity_config(
            inp.company.entity_type,
            inp.company.total_assets,
        )

        economic_perf = self._analyze_economic_performance()
        prepaid = self._analyze_prepaid_expenses()
        recurring = self._analyze_recurring_items()
        compensation = self._analyze_compensation()
        interest = self._analyze_interest_limitation()
        rd = self._analyze_rd_capitalization()
        related = self._analyze_related_party()
        reserves = self._analyze_reserves()
        opportunities = self._compute_total_opportunities(
            economic_perf, prepaid, recurring, compensation,
            interest, rd, related, reserves,
        )
        findings = self._generate_findings(
            economic_perf, prepaid, recurring, compensation,
            interest, rd, related, reserves,
        )
        roadmap = self._generate_phase2_recommendations(findings)

        return {
            "company": inp.company,
            "entity_config": self._entity,
            "economic_performance": economic_perf,
            "prepaid_expenses": prepaid,
            "recurring_items": recurring,
            "compensation": compensation,
            "interest_limitation": interest,
            "rd_capitalization": rd,
            "related_party": related,
            "reserves": reserves,
            "total_opportunities": opportunities,
            "findings": findings,
            "phase2_roadmap": roadmap,
            "income_statement": inp.income_statement,
            "balance_sheet": inp.balance_sheet,
            "expense_categories": inp.expense_categories,
        }

    # ---- §461(h) Economic Performance ----

    def _analyze_economic_performance(self) -> dict:
        payment_liabilities = []
        service_liabilities = []
        property_liabilities = []
        special_liabilities = []

        for cat in self._input.expense_categories:
            ep_cat = (cat.economic_performance_category or "").lower()
            entry = {
                "name": cat.name,
                "book_amount": cat.book_amount_current,
                "prior_amount": cat.book_amount_prior,
                "tax_treatment": cat.tax_treatment,
                "irc_section": cat.irc_section,
                "timing_difference": cat.timing_difference,
                "risk_level": cat.risk_level,
            }
            if ep_cat == "payment":
                entry["rule"] = "Deductible when PAID (§461(h)(2)(C))"
                entry["examples"] = "Taxes, insurance premiums, warranty claims, rebates"
                payment_liabilities.append(entry)
            elif ep_cat == "service":
                entry["rule"] = "Deductible when services PROVIDED to taxpayer (§461(h)(2)(A)(i))"
                entry["examples"] = "Consulting, maintenance, legal services"
                service_liabilities.append(entry)
            elif ep_cat == "property":
                entry["rule"] = "Deductible when property PROVIDED to taxpayer (§461(h)(2)(A)(ii))"
                entry["examples"] = "Inventory, supplies, equipment purchases"
                property_liabilities.append(entry)
            elif ep_cat == "special":
                entry["rule"] = "Special rules apply (workers' comp, tort, contested liabilities)"
                entry["examples"] = "Workers' comp, tort liabilities, contested amounts"
                special_liabilities.append(entry)

        total_timing = sum(
            to_decimal(e["timing_difference"])
            for group in [payment_liabilities, service_liabilities,
                          property_liabilities, special_liabilities]
            for e in group
        )

        return {
            "payment_liabilities": payment_liabilities,
            "service_liabilities": service_liabilities,
            "property_liabilities": property_liabilities,
            "special_liabilities": special_liabilities,
            "total_timing_differences": total_timing,
            "summary": (
                f"Identified {len(payment_liabilities)} payment liabilities, "
                f"{len(service_liabilities)} service liabilities, "
                f"{len(property_liabilities)} property liabilities, "
                f"{len(special_liabilities)} special-rule liabilities. "
                f"Total timing differences: {format_currency(total_timing)}."
            ),
        }

    # ---- Prepaid Expenses / 12-Month Rule ----

    def _analyze_prepaid_expenses(self) -> dict:
        results = []
        total_savings = Decimal("0")

        for pe in self._input.prepaid_expenses:
            qualifies = pe.period_covered_months <= 12 and pe.period_covered_months > 0
            pe.qualifies_12_month_rule = qualifies

            if qualifies and pe.current_treatment == "capitalized":
                savings = pe.amount
                pe.optimal_treatment = "expensed under 12-month rule"
            elif not qualifies and pe.current_treatment == "expensed":
                savings = Decimal("0") - pe.amount  # over-deduction risk
                pe.optimal_treatment = "capitalize under Treas. Reg. 1.263(a)-4"
            else:
                savings = Decimal("0")
                pe.optimal_treatment = pe.current_treatment

            total_savings += savings
            results.append({
                "name": pe.name,
                "amount": pe.amount,
                "period_months": pe.period_covered_months,
                "qualifies_12_month": qualifies,
                "current_treatment": pe.current_treatment,
                "optimal_treatment": pe.optimal_treatment,
                "savings": savings,
                "authority": "Treas. Reg. 1.263(a)-4(f)",
            })

        return {
            "items": results,
            "total_savings": total_savings,
            "count": len(results),
        }

    # ---- Recurring Item Exception §461(h)(3) ----

    def _analyze_recurring_items(self) -> dict:
        eligible = []
        ineligible = []

        for liab in self._input.accrued_liabilities:
            amt = to_decimal(liab.book_balance_current)
            revenue = to_decimal(self._input.company.total_revenue)
            threshold = min(Decimal("10000000"), revenue * Decimal("0.10")) if revenue else Decimal("10000000")

            meets_amount_test = amt <= threshold
            meets_recurring = liab.recurring_item_exception
            meets_all_events = liab.all_events_test_met

            entry = {
                "name": liab.name,
                "amount": amt,
                "threshold": threshold,
                "meets_amount_test": meets_amount_test,
                "meets_recurring_test": meets_recurring,
                "meets_all_events_test": meets_all_events,
                "eligible": meets_amount_test and meets_recurring and meets_all_events,
                "economic_performance_met": liab.economic_performance_met,
                "timing_rule": liab.timing_rule,
            }

            if entry["eligible"]:
                eligible.append(entry)
            else:
                ineligible.append(entry)

        total_eligible = sum(to_decimal(e["amount"]) for e in eligible)

        return {
            "eligible": eligible,
            "ineligible": ineligible,
            "total_eligible_amount": total_eligible,
            "summary": (
                f"{len(eligible)} liabilities qualify for recurring item exception "
                f"(§461(h)(3)), totaling {format_currency(total_eligible)}. "
                f"{len(ineligible)} do not qualify."
            ),
        }

    # ---- §162(m) / Compensation ----

    def _analyze_compensation(self) -> dict:
        items = []
        total_disallowed = Decimal("0")
        total_deferred_timing = Decimal("0")
        limit = Decimal("1000000")

        for comp in self._input.compensation_items:
            book = to_decimal(comp.book_expense)
            tax = to_decimal(comp.tax_deductible)

            if comp.employee_type == "covered_employee" and book > limit:
                disallowed = book - limit
                comp.section_162m_limited = True
            elif comp.section_162m_limited:
                disallowed = book - tax
            else:
                disallowed = Decimal("0")

            timing_diff = book - tax - disallowed
            total_disallowed += disallowed
            total_deferred_timing += abs(timing_diff)

            items.append({
                "name": comp.name,
                "employee_type": comp.employee_type,
                "book_expense": book,
                "tax_deductible": tax,
                "section_162m_disallowed": disallowed,
                "timing_difference": timing_diff,
                "deferred_comp_rules": comp.deferred_comp_rules,
                "timing": comp.timing,
                "risk_level": "high" if disallowed > Decimal("0") else "low",
            })

        return {
            "items": items,
            "total_162m_disallowed": total_disallowed,
            "total_deferred_timing": total_deferred_timing,
            "covered_employee_count": sum(
                1 for c in self._input.compensation_items
                if c.employee_type == "covered_employee"
            ),
            "summary": (
                f"§162(m) disallowed deductions: {format_currency(total_disallowed)}. "
                f"Deferred compensation timing differences: {format_currency(total_deferred_timing)}."
            ),
        }

    # ---- §163(j) Interest Limitation ----

    def _analyze_interest_limitation(self) -> dict:
        ie = self._input.interest_expense
        total = to_decimal(ie.total_interest)
        bii = to_decimal(ie.business_interest_income)
        fpi = to_decimal(ie.floor_plan_interest)
        ati = to_decimal(ie.adjusted_taxable_income)

        # §163(j): deductible = BII + 30% ATI + floor plan interest
        limit_30_pct = round_currency(ati * Decimal("0.30"))
        deductible = bii + limit_30_pct + fpi
        disallowed = max(Decimal("0"), total - deductible)
        carryforward = to_decimal(ie.carryforward_available) + disallowed

        return {
            "total_interest": total,
            "business_interest_income": bii,
            "floor_plan_interest": fpi,
            "adjusted_taxable_income": ati,
            "thirty_pct_ati": limit_30_pct,
            "deductible_amount": min(total, deductible),
            "disallowed_amount": disallowed,
            "carryforward": carryforward,
            "is_limited": disallowed > Decimal("0"),
            "effective_rate": (
                float(min(total, deductible) / total) if total > 0 else 1.0
            ),
            "summary": (
                f"Total interest: {format_currency(total)}. "
                f"30% ATI limit: {format_currency(limit_30_pct)}. "
                f"Disallowed: {format_currency(disallowed)}. "
                f"Carryforward: {format_currency(carryforward)}."
            ),
        }

    # ---- §174 R&D Capitalization ----

    def _analyze_rd_capitalization(self) -> dict:
        rd = self._input.rd_expense
        total = to_decimal(rd.total_rd)
        domestic = to_decimal(rd.domestic_rd)
        foreign = to_decimal(rd.foreign_rd)

        # Post-2022: mandatory capitalization and amortization
        # Domestic: 5 years (60 months) midpoint convention
        # Foreign: 15 years (180 months) midpoint convention
        domestic_annual = round_currency(domestic / Decimal("5")) if domestic else Decimal("0")
        foreign_annual = round_currency(foreign / Decimal("15")) if foreign else Decimal("0")
        total_amort = domestic_annual + foreign_annual

        book_tax_diff = total - total_amort  # book expenses full amount; tax only amortization

        return {
            "total_rd": total,
            "domestic_rd": domestic,
            "foreign_rd": foreign,
            "domestic_annual_amortization": domestic_annual,
            "foreign_annual_amortization": foreign_annual,
            "total_amortization": total_amort,
            "book_tax_difference": book_tax_diff,
            "is_material": book_tax_diff > Decimal("1000000"),
            "summary": (
                f"Total R&D: {format_currency(total)} "
                f"(domestic {format_currency(domestic)}, foreign {format_currency(foreign)}). "
                f"§174 amortization: {format_currency(total_amort)}/yr. "
                f"Book-tax difference: {format_currency(book_tax_diff)}."
            ),
        }

    # ---- §267 Related Party ----

    def _analyze_related_party(self) -> dict:
        items = []
        total_deferred = Decimal("0")

        for rp in self._input.related_party_expenses:
            amt = to_decimal(rp.amount)
            includible = to_decimal(rp.amount_includible_by_payee)
            deferred = amt - includible
            rp.deduction_deferred = deferred
            total_deferred += max(Decimal("0"), deferred)

            items.append({
                "payee_name": rp.payee_name,
                "relationship": rp.relationship,
                "amount": amt,
                "payee_year_end": rp.payee_tax_year_end,
                "includible_by_payee": includible,
                "deferred": max(Decimal("0"), deferred),
                "risk_level": "high" if deferred > Decimal("0") else "low",
                "rule": "§267(a)(2): deduction deferred until includible by related payee",
            })

        return {
            "items": items,
            "total_deferred": total_deferred,
            "count": len(items),
            "summary": (
                f"{len(items)} related-party expenses identified. "
                f"Total deferred under §267: {format_currency(total_deferred)}."
            ),
        }

    # ---- Reserves & Contingencies ----

    def _analyze_reserves(self) -> dict:
        items = []
        total_timing = Decimal("0")

        for liab in self._input.accrued_liabilities:
            book = to_decimal(liab.book_balance_current)
            tax = to_decimal(liab.tax_deductible_current)
            diff = book - tax

            items.append({
                "name": liab.name,
                "book_balance": book,
                "tax_deductible": tax,
                "timing_difference": diff,
                "all_events_met": liab.all_events_test_met,
                "ep_met": liab.economic_performance_met,
                "recurring_exception": liab.recurring_item_exception,
                "timing_rule": liab.timing_rule,
                "risk_level": "high" if abs(diff) > Decimal("5000000") else (
                    "medium" if abs(diff) > Decimal("1000000") else "low"
                ),
            })
            total_timing += diff

        return {
            "items": items,
            "total_timing_difference": total_timing,
            "count": len(items),
            "summary": (
                f"{len(items)} accrued liabilities / reserves analyzed. "
                f"Total book-tax timing difference: {format_currency(total_timing)}."
            ),
        }

    # ---- Aggregation ----

    def _compute_total_opportunities(self, economic_perf, prepaid, recurring,
                                     compensation, interest, rd, related,
                                     reserves) -> dict:
        rate = Decimal(str(self._entity.statutory_rate))

        items = [
            ("Economic Performance Timing", economic_perf["total_timing_differences"]),
            ("Prepaid Expense Optimization", prepaid["total_savings"]),
            ("Recurring Item Exception", recurring["total_eligible_amount"]),
            ("§162(m) Disallowance (permanent)", compensation["total_162m_disallowed"]),
            ("§163(j) Disallowed Interest", interest["disallowed_amount"]),
            ("§174 R&D Book-Tax Difference", rd["book_tax_difference"]),
            ("§267 Related Party Deferrals", related["total_deferred"]),
            ("Reserve Timing Differences", reserves["total_timing_difference"]),
        ]

        total_differences = sum(to_decimal(amt) for _, amt in items)
        tax_impact = round_currency(total_differences * rate) if rate else Decimal("0")

        return {
            "line_items": [
                {"category": cat, "amount": amt, "tax_impact": round_currency(amt * rate) if rate else Decimal("0")}
                for cat, amt in items
            ],
            "total_book_tax_differences": total_differences,
            "estimated_tax_impact": tax_impact,
            "statutory_rate": float(rate),
        }

    # ---- Findings ----

    def _generate_findings(self, economic_perf, prepaid, recurring,
                           compensation, interest, rd, related, reserves) -> list:
        findings = []

        # Economic performance findings
        for cat_name, liabilities in [
            ("Payment", economic_perf["payment_liabilities"]),
            ("Service", economic_perf["service_liabilities"]),
            ("Property", economic_perf["property_liabilities"]),
            ("Special", economic_perf["special_liabilities"]),
        ]:
            for item in liabilities:
                if to_decimal(item["timing_difference"]) != 0:
                    findings.append({
                        "area": "Economic Performance",
                        "description": f"{item['name']}: {cat_name} liability — {item['rule']}",
                        "amount": item["timing_difference"],
                        "risk_level": item["risk_level"],
                        "irc_section": item.get("irc_section", "§461(h)"),
                        "recommendation": f"Verify {cat_name.lower()} liability timing; consider recurring item exception if eligible",
                    })

        # Prepaid findings
        for item in prepaid["items"]:
            if to_decimal(item["savings"]) != 0:
                findings.append({
                    "area": "Prepaid Expenses",
                    "description": f"{item['name']}: {item['current_treatment']} → {item['optimal_treatment']}",
                    "amount": item["savings"],
                    "risk_level": "medium",
                    "irc_section": "Reg. 1.263(a)-4(f)",
                    "recommendation": "Evaluate 12-month rule qualification; may require Form 3115",
                })

        # §162(m)
        if to_decimal(compensation["total_162m_disallowed"]) > 0:
            findings.append({
                "area": "Compensation",
                "description": f"§162(m) permanent disallowance: {format_currency(compensation['total_162m_disallowed'])}",
                "amount": compensation["total_162m_disallowed"],
                "risk_level": "high",
                "irc_section": "§162(m)",
                "recommendation": "Review covered employee identification; evaluate compensation structure alternatives",
            })

        # §163(j)
        if interest["is_limited"]:
            findings.append({
                "area": "Interest Limitation",
                "description": f"§163(j) disallowed interest: {format_currency(interest['disallowed_amount'])}",
                "amount": interest["disallowed_amount"],
                "risk_level": "high",
                "irc_section": "§163(j)",
                "recommendation": "Model ATI optimization; evaluate electing real property or farming business exceptions",
            })

        # §174
        if rd["is_material"]:
            findings.append({
                "area": "R&D Capitalization",
                "description": f"§174 book-tax difference: {format_currency(rd['book_tax_difference'])}",
                "amount": rd["book_tax_difference"],
                "risk_level": "medium",
                "irc_section": "§174",
                "recommendation": "Verify domestic vs. foreign allocation; review §41 credit interplay",
            })

        # §267
        if to_decimal(related["total_deferred"]) > 0:
            findings.append({
                "area": "Related Party",
                "description": f"§267 deferred deductions: {format_currency(related['total_deferred'])}",
                "amount": related["total_deferred"],
                "risk_level": "high",
                "irc_section": "§267",
                "recommendation": "Align payment timing with payee inclusion; review constructive ownership",
            })

        # Reserves
        for item in reserves["items"]:
            if item["risk_level"] in ("high", "medium"):
                findings.append({
                    "area": "Reserves & Contingencies",
                    "description": f"{item['name']}: book-tax diff {format_currency(item['timing_difference'])}",
                    "amount": item["timing_difference"],
                    "risk_level": item["risk_level"],
                    "irc_section": "§461",
                    "recommendation": f"Test all-events + EP requirements; {'recurring item exception available' if item['recurring_exception'] else 'recurring item exception NOT available'}",
                })

        findings.sort(key=lambda f: (
            {"high": 0, "medium": 1, "low": 2}.get(f["risk_level"], 3),
            -abs(to_decimal(f["amount"])),
        ))

        return findings

    # ---- Phase 2 Roadmap ----

    def _generate_phase2_recommendations(self, findings) -> list:
        recommendations = [
            {
                "priority": 1,
                "area": "Trial Balance Mapping",
                "description": "Map expense GL accounts to tax return lines; identify all book-tax differences",
                "data_needed": "Trial balance, tax return (Form 1120/1065), prior-year work papers",
            },
            {
                "priority": 2,
                "area": "Accrued Liability Rollforward",
                "description": "Build rollforward for each accrued liability to test §461(h) timing",
                "data_needed": "Accrued liability schedules, payment histories, supporting invoices",
            },
            {
                "priority": 3,
                "area": "Compensation Detail",
                "description": "Obtain covered employee detail for §162(m); review deferred comp plans",
                "data_needed": "Proxy statement detail, deferred comp plan documents, Form W-2 data",
            },
        ]

        if any(f["area"] == "Interest Limitation" for f in findings):
            recommendations.append({
                "priority": 4,
                "area": "§163(j) Build-Up",
                "description": "Build ATI computation from trial balance; verify add-backs",
                "data_needed": "Form 8990, depreciation schedules, partnership income detail",
            })

        if any(f["area"] == "R&D Capitalization" for f in findings):
            recommendations.append({
                "priority": 5,
                "area": "§174 Detail",
                "description": "Classify R&D by domestic/foreign; verify amortization schedules",
                "data_needed": "R&D cost study, project-level detail, foreign activity breakdown",
            })

        if any(f["area"] == "Related Party" for f in findings):
            recommendations.append({
                "priority": 6,
                "area": "Related Party Review",
                "description": "Verify §267 ownership; match deduction to payee inclusion timing",
                "data_needed": "Intercompany agreements, payee tax returns or confirmations",
            })

        return recommendations
