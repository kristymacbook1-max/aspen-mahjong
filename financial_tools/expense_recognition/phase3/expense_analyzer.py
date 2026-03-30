"""Phase 3 Expense Recognition Analyzer — Contract / Invoice Level Analysis.

Performs detailed §461(h) economic performance testing per expense item,
12-month rule testing, recurring item exception analysis, reserve testing,
and compensation contract analysis.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional, Dict
from datetime import date, timedelta
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
class ExpenseContract:
    contract_id: str
    vendor_name: str
    description: str = ""
    contract_type: str = ""          # service / property / payment / mixed
    total_value: Decimal = Decimal("0")
    annual_amount: Decimal = Decimal("0")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    payment_terms: str = ""          # e.g. "net 30", "quarterly in advance"
    is_related_party: bool = False
    related_party_relationship: str = ""


@dataclass
class ExpenseLineItem:
    line_id: str
    contract_id: str = ""
    description: str = ""
    amount: Decimal = Decimal("0")
    expense_date: Optional[date] = None
    payment_date: Optional[date] = None
    service_period_start: Optional[date] = None
    service_period_end: Optional[date] = None
    economic_performance_category: str = ""   # payment / service / property
    economic_performance_date: Optional[date] = None
    all_events_test_met_date: Optional[date] = None
    book_accrual_date: Optional[date] = None
    tax_deduction_date: Optional[date] = None
    timing_difference: Decimal = Decimal("0")
    is_prepaid: bool = False
    qualifies_12_month_rule: bool = False
    is_recurring_item: bool = False
    recurring_item_eligible: bool = False


@dataclass
class ReserveItem:
    reserve_name: str
    book_balance: Decimal = Decimal("0")
    reserve_type: str = ""               # warranty / litigation / environmental / restructuring / other
    probability_of_payment: float = 0.0
    estimated_payment_date: Optional[date] = None
    all_events_test_met: bool = False
    economic_performance_met: bool = False
    tax_deductible_amount: Decimal = Decimal("0")
    timing_difference: Decimal = Decimal("0")


@dataclass
class CompensationContract:
    employee_name: str
    title: str = ""
    is_covered_employee: bool = False
    base_salary: Decimal = Decimal("0")
    bonus: Decimal = Decimal("0")
    equity_comp: Decimal = Decimal("0")
    deferred_comp: Decimal = Decimal("0")
    total_book_expense: Decimal = Decimal("0")
    section_162m_limit: Decimal = Decimal("1000000")
    disallowed_amount: Decimal = Decimal("0")
    deferred_comp_timing: str = ""       # current / deferred_to_payment
    vesting_schedule: str = ""


@dataclass
class Phase3ExpenseInput:
    company_name: str = ""
    entity_type: str = "c_corp"
    fiscal_year: int = 2024
    fiscal_year_end: Optional[date] = None
    expense_contracts: List[ExpenseContract] = field(default_factory=list)
    expense_line_items: List[ExpenseLineItem] = field(default_factory=list)
    reserve_items: List[ReserveItem] = field(default_factory=list)
    compensation_contracts: List[CompensationContract] = field(default_factory=list)
    interest_detail: Dict = field(default_factory=dict)
    rd_detail: Dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class ExpenseAnalyzer:
    """Phase 3 analyzer: contract/invoice-level expense recognition with
    detailed §461(h) economic performance testing."""

    def analyze(self, inp: Phase3ExpenseInput) -> dict:
        self._input = inp
        self._entity = get_entity_config(inp.entity_type)
        self._fy_end = inp.fiscal_year_end or date(inp.fiscal_year, 12, 31)

        contract_results = self._analyze_all_contracts()
        reserves = self._analyze_reserves()
        compensation = self._analyze_compensation_contracts()
        schedule = self._build_expense_schedule()
        reconciliation = self._compute_book_tax_reconciliation(
            contract_results, reserves, compensation,
        )
        findings = self._generate_findings(
            contract_results, reserves, compensation,
        )
        impl_plan = self._generate_implementation_plan(findings)

        return {
            "company_name": inp.company_name,
            "entity_config": self._entity,
            "fiscal_year": inp.fiscal_year,
            "contract_results": contract_results,
            "reserves": reserves,
            "compensation": compensation,
            "expense_schedule": schedule,
            "book_tax_reconciliation": reconciliation,
            "findings": findings,
            "implementation_plan": impl_plan,
        }

    # ---- Economic Performance Testing ----

    def _test_economic_performance(self, item: ExpenseLineItem) -> dict:
        """Apply §461(h) economic performance test to a single line item."""
        ep_cat = (item.economic_performance_category or "").lower()
        result = {
            "line_id": item.line_id,
            "amount": item.amount,
            "ep_category": ep_cat,
            "all_events_met": item.all_events_test_met_date is not None,
            "all_events_date": item.all_events_test_met_date,
            "ep_met": False,
            "ep_date": None,
            "tax_deduction_year": None,
            "timing_difference": Decimal("0"),
            "rule_applied": "",
            "notes": "",
        }

        if ep_cat == "payment":
            # Payment liabilities: EP occurs when PAYMENT is made
            # Applies to: taxes, insurance, warranty claims, rebates
            result["rule_applied"] = "§461(h)(2)(C) — Payment liability: EP when paid"
            if item.payment_date:
                result["ep_met"] = True
                result["ep_date"] = item.payment_date
                result["tax_deduction_year"] = item.payment_date.year
            else:
                result["notes"] = "Payment date unknown — deduction deferred until payment"

        elif ep_cat == "service":
            # Service liabilities: EP occurs when services are PROVIDED to taxpayer
            result["rule_applied"] = "§461(h)(2)(A)(i) — Service liability: EP when services provided"
            if item.service_period_end and item.service_period_end <= self._fy_end:
                result["ep_met"] = True
                result["ep_date"] = item.service_period_end
                result["tax_deduction_year"] = item.service_period_end.year
            elif item.service_period_end:
                result["notes"] = f"Services not fully provided until {item.service_period_end}"
            elif item.economic_performance_date:
                result["ep_met"] = True
                result["ep_date"] = item.economic_performance_date
                result["tax_deduction_year"] = item.economic_performance_date.year

        elif ep_cat == "property":
            # Property liabilities: EP occurs when property is PROVIDED to taxpayer
            result["rule_applied"] = "§461(h)(2)(A)(ii) — Property liability: EP when property provided"
            if item.economic_performance_date:
                result["ep_met"] = True
                result["ep_date"] = item.economic_performance_date
                result["tax_deduction_year"] = item.economic_performance_date.year
            else:
                result["notes"] = "Property delivery date unknown — verify receipt"

        else:
            result["rule_applied"] = "EP category not classified — needs review"
            result["notes"] = "Classify as payment, service, or property liability"

        # Compute timing difference
        book_year = item.book_accrual_date.year if item.book_accrual_date else self._input.fiscal_year
        tax_year = result["tax_deduction_year"] or (self._input.fiscal_year + 1)
        if book_year != tax_year:
            result["timing_difference"] = item.amount
        else:
            result["timing_difference"] = Decimal("0")

        return result

    # ---- 12-Month Rule ----

    def _test_12_month_rule(self, item: ExpenseLineItem) -> dict:
        """Test Treas. Reg. 1.263(a)-4(f) 12-month rule qualification."""
        result = {
            "line_id": item.line_id,
            "qualifies": False,
            "reason": "",
            "benefit_period_months": 0,
            "treatment": "",
        }

        if not item.is_prepaid:
            result["reason"] = "Not a prepaid expense"
            result["treatment"] = "Normal accrual"
            return result

        if item.service_period_start and item.service_period_end:
            delta = item.service_period_end - item.service_period_start
            months = delta.days / 30.44
            result["benefit_period_months"] = int(months)

            # Must not extend beyond end of tax year following payment year
            payment_year = item.payment_date.year if item.payment_date else self._input.fiscal_year
            deadline = date(payment_year + 1, 12, 31)

            if months <= 12 and item.service_period_end <= deadline:
                result["qualifies"] = True
                result["reason"] = "Benefit period ≤ 12 months and does not extend beyond following tax year"
                result["treatment"] = "Deductible when paid under 12-month rule"
            elif months > 12:
                result["reason"] = f"Benefit period is {int(months)} months (>12)"
                result["treatment"] = "Must capitalize and amortize under Reg. 1.263(a)-4"
            else:
                result["reason"] = f"Extends beyond {deadline}"
                result["treatment"] = "Must capitalize — extends beyond following tax year"
        else:
            result["reason"] = "Service period dates not provided"
            result["treatment"] = "Cannot determine — need service period dates"

        return result

    # ---- Recurring Item Exception ----

    def _test_recurring_item_exception(self, item: ExpenseLineItem) -> dict:
        """Test §461(h)(3) recurring item exception."""
        result = {
            "line_id": item.line_id,
            "eligible": False,
            "meets_recurring_test": item.is_recurring_item,
            "meets_consistency_test": False,
            "meets_materiality_or_matching": False,
            "reason": "",
        }

        if not item.is_recurring_item:
            result["reason"] = "Not a recurring item"
            return result

        # Must be consistently treated
        result["meets_consistency_test"] = True  # assumed if flagged as recurring

        # Must be either: not material, OR provides better matching
        amt = to_decimal(item.amount)
        revenue = to_decimal(Decimal("0"))  # would need company revenue
        if amt <= Decimal("10000000"):
            result["meets_materiality_or_matching"] = True

        if result["meets_recurring_test"] and result["meets_consistency_test"] and result["meets_materiality_or_matching"]:
            result["eligible"] = True
            result["reason"] = "Qualifies: recurring, consistent, meets materiality test"
        else:
            result["reason"] = "Does not meet all 3 requirements for recurring item exception"

        return result

    # ---- Contract Analysis ----

    def _analyze_all_contracts(self) -> list:
        results = []
        items_by_contract = {}
        for item in self._input.expense_line_items:
            items_by_contract.setdefault(item.contract_id, []).append(item)

        for contract in self._input.expense_contracts:
            items = items_by_contract.get(contract.contract_id, [])
            result = self._analyze_contract_expenses(contract, items)
            results.append(result)

        # Handle orphan line items (no contract)
        contract_ids = {c.contract_id for c in self._input.expense_contracts}
        orphans = [i for i in self._input.expense_line_items if i.contract_id not in contract_ids]
        if orphans:
            orphan_contract = ExpenseContract(
                contract_id="ORPHAN",
                vendor_name="Unassigned Line Items",
                description="Line items not linked to a contract",
            )
            results.append(self._analyze_contract_expenses(orphan_contract, orphans))

        return results

    def _analyze_contract_expenses(self, contract: ExpenseContract,
                                   items: List[ExpenseLineItem]) -> dict:
        ep_results = []
        twelve_mo_results = []
        recurring_results = []
        total_book = Decimal("0")
        total_tax = Decimal("0")
        total_timing = Decimal("0")

        for item in items:
            ep = self._test_economic_performance(item)
            ep_results.append(ep)

            twelve_mo = self._test_12_month_rule(item)
            twelve_mo_results.append(twelve_mo)

            recurring = self._test_recurring_item_exception(item)
            recurring_results.append(recurring)

            total_book += to_decimal(item.amount)
            if ep["ep_met"] and ep["tax_deduction_year"] == self._input.fiscal_year:
                total_tax += to_decimal(item.amount)
            total_timing += to_decimal(ep["timing_difference"])

        return {
            "contract": {
                "id": contract.contract_id,
                "vendor": contract.vendor_name,
                "description": contract.description,
                "type": contract.contract_type,
                "total_value": contract.total_value,
                "annual_amount": contract.annual_amount,
                "is_related_party": contract.is_related_party,
                "relationship": contract.related_party_relationship,
            },
            "line_item_count": len(items),
            "ep_results": ep_results,
            "twelve_month_results": twelve_mo_results,
            "recurring_results": recurring_results,
            "total_book_expense": total_book,
            "total_tax_deduction": total_tax,
            "total_timing_difference": total_timing,
        }

    # ---- Reserves ----

    def _analyze_reserves(self) -> dict:
        results = []
        total_book = Decimal("0")
        total_tax = Decimal("0")

        for reserve in self._input.reserve_items:
            book = to_decimal(reserve.book_balance)
            tax = to_decimal(reserve.tax_deductible_amount)
            diff = book - tax

            # All-events test analysis
            ae_analysis = "Met" if reserve.all_events_test_met else "NOT met — liability not fixed and determinable"

            # EP analysis by reserve type
            ep_type = (reserve.reserve_type or "").lower()
            if ep_type == "warranty":
                ep_rule = "Payment liability — EP when claims paid (§461(h)(2)(C))"
                ep_category = "payment"
            elif ep_type == "litigation":
                ep_rule = "Payment liability — EP when judgment paid or settled"
                ep_category = "payment"
            elif ep_type == "environmental":
                ep_rule = "Service/property liability — EP as remediation services provided"
                ep_category = "service"
            elif ep_type == "restructuring":
                ep_rule = "Mixed — employee severance (payment); lease termination (payment)"
                ep_category = "payment"
            else:
                ep_rule = "Determine applicable EP category based on underlying obligation"
                ep_category = "unknown"

            results.append({
                "name": reserve.reserve_name,
                "book_balance": book,
                "tax_deductible": tax,
                "timing_difference": diff,
                "reserve_type": reserve.reserve_type,
                "probability": reserve.probability_of_payment,
                "estimated_payment": reserve.estimated_payment_date,
                "all_events_analysis": ae_analysis,
                "all_events_met": reserve.all_events_test_met,
                "ep_met": reserve.economic_performance_met,
                "ep_category": ep_category,
                "ep_rule": ep_rule,
            })

            total_book += book
            total_tax += tax

        return {
            "items": results,
            "total_book": total_book,
            "total_tax": total_tax,
            "total_timing_difference": total_book - total_tax,
            "count": len(results),
        }

    # ---- Compensation Contracts ----

    def _analyze_compensation_contracts(self) -> dict:
        results = []
        total_disallowed = Decimal("0")
        total_deferred = Decimal("0")
        limit = Decimal("1000000")

        for comp in self._input.compensation_contracts:
            total_book = to_decimal(comp.total_book_expense)
            if total_book == 0:
                total_book = (to_decimal(comp.base_salary) + to_decimal(comp.bonus)
                              + to_decimal(comp.equity_comp) + to_decimal(comp.deferred_comp))

            disallowed = Decimal("0")
            if comp.is_covered_employee:
                if total_book > limit:
                    disallowed = total_book - limit

            # Deferred comp timing
            deferred_amount = to_decimal(comp.deferred_comp)
            timing = comp.deferred_comp_timing or "current"

            total_disallowed += disallowed
            if timing == "deferred_to_payment":
                total_deferred += deferred_amount

            results.append({
                "employee": comp.employee_name,
                "title": comp.title,
                "is_covered": comp.is_covered_employee,
                "base_salary": comp.base_salary,
                "bonus": comp.bonus,
                "equity_comp": comp.equity_comp,
                "deferred_comp": comp.deferred_comp,
                "total_book": total_book,
                "section_162m_disallowed": disallowed,
                "deferred_timing": timing,
                "vesting": comp.vesting_schedule,
                "tax_deductible": total_book - disallowed - (deferred_amount if timing == "deferred_to_payment" else Decimal("0")),
            })

        return {
            "items": results,
            "total_162m_disallowed": total_disallowed,
            "total_deferred": total_deferred,
            "count": len(results),
        }

    # ---- Expense Schedule ----

    def _build_expense_schedule(self) -> list:
        schedule = []
        for item in self._input.expense_line_items:
            book_date = item.book_accrual_date or date(self._input.fiscal_year, 12, 31)
            tax_date = item.tax_deduction_date or item.payment_date or item.economic_performance_date
            schedule.append({
                "line_id": item.line_id,
                "description": item.description,
                "amount": item.amount,
                "book_accrual_date": book_date,
                "tax_deduction_date": tax_date,
                "timing_matches": (
                    book_date.year == tax_date.year if tax_date else False
                ),
            })
        schedule.sort(key=lambda x: x["book_accrual_date"])
        return schedule

    # ---- Book-Tax Reconciliation ----

    def _compute_book_tax_reconciliation(self, contracts, reserves, compensation) -> dict:
        categories = {}

        for cr in contracts:
            ctype = cr["contract"]["type"] or "Other"
            if ctype not in categories:
                categories[ctype] = {"book": Decimal("0"), "tax": Decimal("0")}
            categories[ctype]["book"] += to_decimal(cr["total_book_expense"])
            categories[ctype]["tax"] += to_decimal(cr["total_tax_deduction"])

        # Reserves
        categories["Reserves & Contingencies"] = {
            "book": reserves["total_book"],
            "tax": reserves["total_tax"],
        }

        # Compensation
        total_comp_book = sum(to_decimal(c["total_book"]) for c in compensation["items"])
        total_comp_tax = sum(to_decimal(c["tax_deductible"]) for c in compensation["items"])
        categories["Compensation"] = {
            "book": total_comp_book,
            "tax": total_comp_tax,
        }

        items = []
        grand_book = Decimal("0")
        grand_tax = Decimal("0")
        for cat, vals in categories.items():
            diff = vals["book"] - vals["tax"]
            items.append({
                "category": cat,
                "book_amount": vals["book"],
                "tax_amount": vals["tax"],
                "difference": diff,
            })
            grand_book += vals["book"]
            grand_tax += vals["tax"]

        return {
            "items": items,
            "total_book": grand_book,
            "total_tax": grand_tax,
            "total_difference": grand_book - grand_tax,
        }

    # ---- Findings ----

    def _generate_findings(self, contracts, reserves, compensation) -> list:
        findings = []

        for cr in contracts:
            td = to_decimal(cr["total_timing_difference"])
            if abs(td) > Decimal("100000"):
                risk = "high" if abs(td) > Decimal("5000000") else ("medium" if abs(td) > Decimal("1000000") else "low")
                findings.append({
                    "area": "Contract Expense",
                    "description": f"{cr['contract']['vendor']}: {cr['contract']['description']}",
                    "book_tax_difference": td,
                    "risk_level": risk,
                    "recommendation": "Review EP timing per line item; consider recurring item exception",
                    "contract_id": cr["contract"]["id"],
                })

            # Flag related party contracts
            if cr["contract"]["is_related_party"]:
                findings.append({
                    "area": "Related Party Contract",
                    "description": f"{cr['contract']['vendor']} ({cr['contract']['relationship']})",
                    "book_tax_difference": td,
                    "risk_level": "high",
                    "recommendation": "§267 matching — verify payee inclusion timing",
                    "contract_id": cr["contract"]["id"],
                })

        for res in reserves["items"]:
            td = to_decimal(res["timing_difference"])
            if abs(td) > Decimal("100000"):
                findings.append({
                    "area": "Reserve",
                    "description": f"{res['name']} ({res['reserve_type']}): AE {'met' if res['all_events_met'] else 'NOT met'}, EP {'met' if res['ep_met'] else 'NOT met'}",
                    "book_tax_difference": td,
                    "risk_level": "high" if not res["all_events_met"] else "medium",
                    "recommendation": res["ep_rule"],
                    "contract_id": "",
                })

        if to_decimal(compensation["total_162m_disallowed"]) > 0:
            findings.append({
                "area": "Compensation",
                "description": f"§162(m) disallowance: {format_currency(compensation['total_162m_disallowed'])}",
                "book_tax_difference": compensation["total_162m_disallowed"],
                "risk_level": "high",
                "recommendation": "Permanent difference — review covered employee identification",
                "contract_id": "",
            })

        findings.sort(key=lambda f: (
            {"high": 0, "medium": 1, "low": 2}.get(f["risk_level"], 3),
            -abs(to_decimal(f["book_tax_difference"])),
        ))

        return findings

    # ---- Implementation Plan ----

    def _generate_implementation_plan(self, findings) -> list:
        plan = []
        areas_with_findings = {f["area"] for f in findings}

        if "Contract Expense" in areas_with_findings:
            plan.append({
                "priority": 1,
                "action": "File Form 3115 for §461(h) Economic Performance Method Change",
                "description": "Change accounting method for expense accruals not meeting EP requirements",
                "irc_section": "§461(h), §446(e)",
                "form": "Form 3115",
                "section_481a": True,
                "deadline": "Due with timely filed return (including extensions)",
            })

        if "Reserve" in areas_with_findings:
            plan.append({
                "priority": 2,
                "action": "Document Reserve Tax Positions",
                "description": "Prepare documentation supporting all-events test and EP for each reserve",
                "irc_section": "§461(a), §461(h)",
                "form": "Tax work paper",
                "section_481a": False,
                "deadline": "Before filing return",
            })

        if "Compensation" in areas_with_findings:
            plan.append({
                "priority": 3,
                "action": "§162(m) Covered Employee Analysis",
                "description": "Document covered employee identification and compensation components",
                "irc_section": "§162(m)",
                "form": "Tax work paper",
                "section_481a": False,
                "deadline": "Before filing return",
            })

        if "Related Party Contract" in areas_with_findings:
            plan.append({
                "priority": 4,
                "action": "§267 Related Party Deduction Review",
                "description": "Match deduction timing to payee inclusion; document ownership analysis",
                "irc_section": "§267(a)(2)",
                "form": "Tax work paper",
                "section_481a": False,
                "deadline": "Before filing return",
            })

        plan.append({
            "priority": len(plan) + 1,
            "action": "Prepare Technical Memoranda",
            "description": "Draft technical memos for all material positions taken",
            "irc_section": "Various",
            "form": "Tax memo",
            "section_481a": False,
            "deadline": "With return preparation",
        })

        return plan
