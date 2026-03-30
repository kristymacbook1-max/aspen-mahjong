"""Phase 1 Transaction Cost Analyzer — 10-K / Public Data Analysis.

Analyzes transaction costs for proper capitalization vs. deduction under
§263(a), INDOPCO, and the §1.263(a)-5 regulations (facilitating costs for
acquisitions, reorganizations, stock issuances, and other transactions).
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
    total_revenue: Decimal = Decimal("0")
    industry: str = ""


@dataclass
class Transaction:
    """A corporate transaction with associated costs to analyze."""
    transaction_id: str
    description: str
    transaction_type: str = ""    # acquisition / disposition / reorganization / stock_issuance / debt_issuance / ipo / spinoff / merger
    date: str = ""
    total_value: Decimal = Decimal("0")
    status: str = ""              # completed / pending / abandoned
    counterparty: str = ""


@dataclass
class TransactionCostItem:
    """Individual cost associated with a transaction."""
    cost_id: str
    transaction_id: str
    description: str
    vendor: str = ""
    amount: Decimal = Decimal("0")
    cost_type: str = ""           # legal / investment_banking / accounting / due_diligence / regulatory / financing / integration / other
    facilitates_transaction: bool = True
    current_treatment: str = ""   # capitalized / deducted
    proper_treatment: str = ""    # capitalize / deduct / allocate
    irc_section: str = ""
    notes: str = ""


@dataclass
class DebtIssuanceCost:
    """Costs associated with debt issuance/refinancing."""
    description: str
    amount: Decimal = Decimal("0")
    debt_instrument: str = ""
    debt_term_years: int = 0
    amortization_method: str = ""   # straight_line / effective_interest
    current_year_amortization: Decimal = Decimal("0")


@dataclass
class Phase1TransactionInput:
    company: CompanyProfile = field(default_factory=CompanyProfile)
    transactions: List[Transaction] = field(default_factory=list)
    cost_items: List[TransactionCostItem] = field(default_factory=list)
    debt_issuance_costs: List[DebtIssuanceCost] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class TransactionCostAnalyzer:
    """Phase 1 analyzer for transaction cost capitalization/deduction."""

    def analyze(self, inp: Phase1TransactionInput) -> dict:
        self._input = inp
        self._entity = get_entity_config(inp.company.entity_type, inp.company.total_assets)

        transaction_results = self._analyze_transactions()
        cost_classification = self._classify_costs()
        debt_costs = self._analyze_debt_issuance()
        abandoned_transactions = self._analyze_abandoned_transactions()
        findings = self._generate_findings(transaction_results, cost_classification, debt_costs, abandoned_transactions)
        roadmap = self._generate_phase2_recommendations(findings)

        return {
            "company": inp.company,
            "entity_config": self._entity,
            "transaction_results": transaction_results,
            "cost_classification": cost_classification,
            "debt_issuance": debt_costs,
            "abandoned_transactions": abandoned_transactions,
            "findings": findings,
            "phase2_roadmap": roadmap,
        }

    def _analyze_transactions(self) -> list:
        results = []
        costs_by_txn = {}
        for c in self._input.cost_items:
            costs_by_txn.setdefault(c.transaction_id, []).append(c)

        for txn in self._input.transactions:
            costs = costs_by_txn.get(txn.transaction_id, [])
            total_costs = sum(to_decimal(c.amount) for c in costs)
            capitalize = sum(to_decimal(c.amount) for c in costs if c.proper_treatment == "capitalize")
            deduct = sum(to_decimal(c.amount) for c in costs if c.proper_treatment == "deduct")

            results.append({
                "transaction": txn,
                "cost_count": len(costs),
                "total_costs": total_costs,
                "amount_to_capitalize": capitalize,
                "amount_to_deduct": deduct,
                "amount_to_allocate": total_costs - capitalize - deduct,
                "pct_deductible": float(deduct / total_costs) if total_costs else 0,
            })

        return results

    def _classify_costs(self) -> dict:
        """Classify costs under Reg. 1.263(a)-5 framework."""
        capitalize = []
        deduct = []
        allocate = []

        for cost in self._input.cost_items:
            ct = (cost.cost_type or "").lower()
            txn_type = ""
            for txn in self._input.transactions:
                if txn.transaction_id == cost.transaction_id:
                    txn_type = (txn.transaction_type or "").lower()
                    break

            # Apply Reg. 1.263(a)-5 rules
            if cost.facilitates_transaction:
                if ct in ("investment_banking", "regulatory", "financing"):
                    # Inherently facilitative — must capitalize
                    proper = "capitalize"
                    rule = "Reg. 1.263(a)-5(e)(2): Inherently facilitative — must capitalize"
                elif ct == "due_diligence":
                    # Facilitative if after bright-line date
                    proper = "capitalize"
                    rule = "Reg. 1.263(a)-5(e)(1): Due diligence costs that facilitate the transaction"
                elif ct == "legal":
                    # May be allocable between facilitative and non-facilitative
                    proper = "allocate"
                    rule = "Reg. 1.263(a)-5(e): Legal costs — allocate between facilitative and non-facilitative"
                elif ct == "integration":
                    # Post-closing integration costs are generally deductible
                    proper = "deduct"
                    rule = "Post-closing integration costs — generally deductible under §162"
                else:
                    proper = "capitalize"
                    rule = "Reg. 1.263(a)-5: Costs facilitating a covered transaction"
            else:
                proper = "deduct"
                rule = "Non-facilitative — deductible under §162"

            cost.proper_treatment = proper
            entry = {
                "cost_id": cost.cost_id,
                "transaction_id": cost.transaction_id,
                "description": cost.description,
                "vendor": cost.vendor,
                "amount": cost.amount,
                "cost_type": cost.cost_type,
                "current_treatment": cost.current_treatment,
                "proper_treatment": proper,
                "rule": rule,
                "mismatch": cost.current_treatment != proper and cost.current_treatment != "",
            }

            if proper == "capitalize":
                capitalize.append(entry)
            elif proper == "deduct":
                deduct.append(entry)
            else:
                allocate.append(entry)

        total_cap = sum(to_decimal(c["amount"]) for c in capitalize)
        total_ded = sum(to_decimal(c["amount"]) for c in deduct)
        total_alloc = sum(to_decimal(c["amount"]) for c in allocate)

        return {
            "capitalize": capitalize,
            "deduct": deduct,
            "allocate": allocate,
            "total_capitalize": total_cap,
            "total_deduct": total_ded,
            "total_allocate": total_alloc,
            "mismatches": [c for c in capitalize + deduct + allocate if c["mismatch"]],
        }

    def _analyze_debt_issuance(self) -> dict:
        items = []
        total_costs = Decimal("0")
        total_amort = Decimal("0")

        for dic in self._input.debt_issuance_costs:
            amt = to_decimal(dic.amount)
            amort = to_decimal(dic.current_year_amortization)
            if dic.debt_term_years and amt and not amort:
                amort = round_currency(amt / Decimal(str(dic.debt_term_years)))

            items.append({
                "description": dic.description,
                "amount": amt,
                "instrument": dic.debt_instrument,
                "term": dic.debt_term_years,
                "annual_amortization": amort,
                "rule": "§163(e)(5) / Reg. 1.446-5: Debt issuance costs amortized over life of debt using constant yield method",
            })
            total_costs += amt
            total_amort += amort

        return {
            "items": items,
            "total_costs": total_costs,
            "total_annual_amortization": total_amort,
        }

    def _analyze_abandoned_transactions(self) -> dict:
        abandoned = []
        for txn_result in self._analyze_transactions():
            if txn_result["transaction"].status == "abandoned":
                abandoned.append({
                    "transaction": txn_result["transaction"],
                    "total_costs": txn_result["total_costs"],
                    "rule": "Rev. Rul. 73-580: Costs of abandoned transaction deductible as loss in year abandoned",
                    "treatment": "deduct",
                })

        return {
            "items": abandoned,
            "total": sum(to_decimal(a["total_costs"]) for a in abandoned),
        }

    def _generate_findings(self, transactions, classification, debt, abandoned) -> list:
        findings = []

        for m in classification["mismatches"]:
            findings.append({
                "area": "Cost Classification Mismatch",
                "description": f"{m['description']}: currently {m['current_treatment']}, should be {m['proper_treatment']}",
                "amount": m["amount"],
                "risk_level": "high",
                "recommendation": f"Reclassify per {m['rule']}",
            })

        if to_decimal(classification["total_allocate"]) > 0:
            findings.append({
                "area": "Cost Allocation Needed",
                "description": f"Costs requiring allocation between facilitative and non-facilitative: {format_currency(classification['total_allocate'])}",
                "amount": classification["total_allocate"],
                "risk_level": "medium",
                "recommendation": "Obtain detailed invoices to allocate between capitalize/deduct",
            })

        if abandoned["items"]:
            findings.append({
                "area": "Abandoned Transaction",
                "description": f"Abandoned transaction costs available for deduction: {format_currency(abandoned['total'])}",
                "amount": abandoned["total"],
                "risk_level": "medium",
                "recommendation": "Document abandonment; deduct under Rev. Rul. 73-580",
            })

        findings.sort(key=lambda f: ({"high": 0, "medium": 1, "low": 2}.get(f["risk_level"], 3), -abs(to_decimal(f["amount"]))))
        return findings

    def _generate_phase2_recommendations(self, findings) -> list:
        return [
            {"priority": 1, "area": "Invoice Review", "description": "Review invoices from advisors to classify facilitative vs. non-facilitative", "data_needed": "Advisor invoices, engagement letters, fee agreements"},
            {"priority": 2, "area": "Bright-Line Date Analysis", "description": "Determine bright-line date for each transaction to classify pre/post costs", "data_needed": "Board minutes, LOI dates, transaction timelines"},
            {"priority": 3, "area": "Success-Based Fee Analysis", "description": "Analyze success-based fees under Rev. Proc. 2011-29 safe harbor", "data_needed": "Fee arrangements, success fee calculations"},
        ]
