"""Phase 2: Trial Balance Revenue Recognition Analyzer.

Analyzes general ledger trial balance data to identify book-tax differences,
timing issues, and revenue recognition adjustments.

Input: Trial balance data (account-level detail), Phase 1 results.
Output: Structured findings for Excel report.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from decimal import Decimal

from ..utils.currency_helpers import to_decimal, pct_change, pct_of_total, variance


@dataclass
class TrialBalanceAccount:
    """A single general ledger account from the trial balance."""
    account_number: str
    account_name: str
    account_type: str = ""  # revenue, deferred_revenue, contract_asset, ar, cogs, expense, other
    beginning_balance: Decimal = Decimal("0")
    ending_balance: Decimal = Decimal("0")
    debits: Decimal = Decimal("0")
    credits: Decimal = Decimal("0")
    department: str = ""
    entity: str = ""
    notes: str = ""


@dataclass
class RevenueAccountMapping:
    """Maps a GL account to a revenue stream and recognition category."""
    account_number: str
    revenue_stream: str = ""
    recognition_type: str = ""  # point-in-time, over-time, subscription, license
    tax_treatment: str = ""  # same-as-book, deferred, accelerated, method-difference
    book_tax_difference: Decimal = Decimal("0")
    notes: str = ""


@dataclass
class DeferredRevenueRollforward:
    """Deferred revenue rollforward schedule from GL detail."""
    category: str = ""
    opening_balance: Decimal = Decimal("0")
    additions: Decimal = Decimal("0")  # new billings / deferrals
    recognized: Decimal = Decimal("0")  # released to revenue
    adjustments: Decimal = Decimal("0")  # FX, reclasses, etc.
    closing_balance: Decimal = Decimal("0")
    notes: str = ""


@dataclass
class TaxReturnData:
    """Key data from the tax return (Form 1120/1065)."""
    form_type: str = "1120"  # 1120, 1065, 1120-S
    tax_year: int = 0
    # Gross receipts
    gross_receipts_line: Decimal = Decimal("0")  # Line 1a on 1120
    returns_and_allowances: Decimal = Decimal("0")
    net_receipts: Decimal = Decimal("0")
    # Schedule M-1 / M-3 items
    book_income: Decimal = Decimal("0")
    tax_income: Decimal = Decimal("0")
    # Revenue-related M-1 adjustments
    m1_revenue_adjustments: List[Dict] = field(default_factory=list)
    # e.g., [{"description": "Advance payments deferred", "book_amount": X, "tax_amount": Y}]
    # Method of accounting
    accounting_method: str = ""  # cash, accrual, hybrid
    revenue_recognition_method: str = ""
    # Section 451 elections
    section_451c_election: bool = False
    section_451b_afs: bool = False  # applicable financial statement conformity
    # Deferred revenue for tax
    tax_deferred_revenue_current: Decimal = Decimal("0")
    tax_deferred_revenue_prior: Decimal = Decimal("0")


@dataclass
class WorkPaperItem:
    """A work paper entry supporting a tax return position."""
    description: str
    category: str = ""  # revenue_timing, deferred_revenue, variable_consideration, etc.
    book_amount: Decimal = Decimal("0")
    tax_amount: Decimal = Decimal("0")
    difference: Decimal = Decimal("0")
    permanent_or_temporary: str = ""  # permanent, temporary
    dta_or_dtl: str = ""  # DTA (deferred tax asset) or DTL (deferred tax liability)
    supporting_reference: str = ""
    notes: str = ""


@dataclass
class Phase2Input:
    """Complete input data for Phase 2 analysis."""
    trial_balance: List[TrialBalanceAccount] = field(default_factory=list)
    account_mappings: List[RevenueAccountMapping] = field(default_factory=list)
    deferred_rollforwards: List[DeferredRevenueRollforward] = field(default_factory=list)
    tax_return: TaxReturnData = field(default_factory=TaxReturnData)
    work_papers: List[WorkPaperItem] = field(default_factory=list)
    phase1_results: Optional[dict] = None


class TrialBalanceAnalyzer:
    """Analyzes trial balance and tax return data for revenue recognition issues."""

    def __init__(self, data: Phase2Input):
        self.data = data
        self.findings = []
        self.book_tax_differences = []
        self.adjustments = []
        self.metrics = {}

    def analyze(self) -> dict:
        """Run all Phase 2 analyses."""
        self._categorize_accounts()
        self._analyze_revenue_accounts()
        self._analyze_deferred_revenue_rollforward()
        self._analyze_book_vs_tax()
        self._analyze_m1_adjustments()
        self._analyze_451_elections()
        self._analyze_work_paper_positions()
        self._compute_adjustment_opportunities()
        self._cross_reference_phase1()
        self._compute_summary_metrics()

        return {
            "findings": self.findings,
            "book_tax_differences": self.book_tax_differences,
            "adjustments": self.adjustments,
            "metrics": self.metrics,
            "trial_balance_summary": self._summarize_tb(),
            "deferred_rollforwards": self.data.deferred_rollforwards,
            "tax_return": self.data.tax_return,
            "work_papers": self.data.work_papers,
        }

    def _categorize_accounts(self):
        """Group trial balance accounts by type."""
        self.revenue_accounts = []
        self.deferred_accounts = []
        self.ar_accounts = []
        self.contract_asset_accounts = []
        self.other_accounts = []

        for acct in self.data.trial_balance:
            acct_type = acct.account_type.lower()
            if acct_type == "revenue":
                self.revenue_accounts.append(acct)
            elif acct_type == "deferred_revenue":
                self.deferred_accounts.append(acct)
            elif acct_type == "ar":
                self.ar_accounts.append(acct)
            elif acct_type == "contract_asset":
                self.contract_asset_accounts.append(acct)
            else:
                self.other_accounts.append(acct)

    def _analyze_revenue_accounts(self):
        """Analyze revenue accounts for anomalies and opportunities."""
        total_revenue = sum(a.ending_balance for a in self.revenue_accounts)
        self.metrics["total_revenue_tb"] = total_revenue

        for acct in self.revenue_accounts:
            if total_revenue != 0:
                pct = pct_of_total(acct.ending_balance, total_revenue)
            else:
                pct = None

            # Check for unusual activity
            net_change = acct.ending_balance - acct.beginning_balance
            if acct.beginning_balance != 0:
                change_pct = pct_change(acct.ending_balance, acct.beginning_balance)
            else:
                change_pct = None

            if change_pct is not None and abs(change_pct) > 0.25:
                self.findings.append({
                    "category": "Revenue Account Anomaly",
                    "account": f"{acct.account_number} - {acct.account_name}",
                    "finding": f"Significant change of {change_pct:.1%} YoY",
                    "detail": f"Beginning: ${float(acct.beginning_balance):,.0f}, "
                              f"Ending: ${float(acct.ending_balance):,.0f}, "
                              f"Net change: ${float(net_change):,.0f}",
                    "risk_level": "High" if abs(change_pct) > 0.50 else "Medium",
                    "recommendation": "Investigate cause of change; verify recognition timing",
                })

            # Check for debit balances in revenue accounts (unusual)
            if acct.debits > acct.credits and acct.ending_balance > 0:
                self.findings.append({
                    "category": "Revenue Account Anomaly",
                    "account": f"{acct.account_number} - {acct.account_name}",
                    "finding": "Revenue account has net debit activity",
                    "detail": f"Debits: ${float(acct.debits):,.0f}, Credits: ${float(acct.credits):,.0f}. "
                              "May indicate reversals, returns, or mispostings.",
                    "risk_level": "Medium",
                    "recommendation": "Review debit entries for proper classification",
                })

    def _analyze_deferred_revenue_rollforward(self):
        """Analyze the deferred revenue rollforward for recognition patterns."""
        for rf in self.data.deferred_rollforwards:
            # Validate rollforward ties out
            expected_close = rf.opening_balance + rf.additions - rf.recognized + rf.adjustments
            diff = rf.closing_balance - expected_close
            if abs(diff) > Decimal("1"):
                self.findings.append({
                    "category": "Deferred Revenue Rollforward",
                    "account": rf.category,
                    "finding": "Rollforward does not reconcile",
                    "detail": f"Expected closing: ${float(expected_close):,.0f}, "
                              f"Actual closing: ${float(rf.closing_balance):,.0f}, "
                              f"Difference: ${float(diff):,.0f}",
                    "risk_level": "High",
                    "recommendation": "Investigate unreconciled difference",
                })

            # Recognition rate
            if rf.opening_balance != 0:
                rec_rate = float(rf.recognized / rf.opening_balance)
                self.findings.append({
                    "category": "Deferred Revenue Rollforward",
                    "account": rf.category,
                    "finding": f"Recognition rate: {rec_rate:.1%} of opening balance",
                    "detail": f"Recognized ${float(rf.recognized):,.0f} from "
                              f"${float(rf.opening_balance):,.0f} opening balance. "
                              f"Additions: ${float(rf.additions):,.0f}.",
                    "risk_level": "Low",
                    "recommendation": "Compare recognition rate to prior years and tax treatment",
                })

            # Net growth in deferred
            if rf.additions > rf.recognized:
                net_growth = rf.additions - rf.recognized
                self.findings.append({
                    "category": "Deferred Revenue Rollforward",
                    "account": rf.category,
                    "finding": "Net deferred revenue growth",
                    "detail": f"Additions (${float(rf.additions):,.0f}) exceed recognition "
                              f"(${float(rf.recognized):,.0f}) by ${float(net_growth):,.0f}. "
                              "Growing deferred balance may create tax deferral opportunity.",
                    "risk_level": "Medium",
                    "recommendation": "Evaluate §451(c) deferral election for tax purposes",
                })

    def _analyze_book_vs_tax(self):
        """Compare book revenue to tax return gross receipts."""
        tr = self.data.tax_return
        total_tb_revenue = self.metrics.get("total_revenue_tb", Decimal("0"))

        if tr.gross_receipts_line and total_tb_revenue:
            book_tax_diff = total_tb_revenue - tr.net_receipts
            self.metrics["book_tax_revenue_difference"] = book_tax_diff

            if abs(book_tax_diff) > Decimal("1000"):
                self.book_tax_differences.append({
                    "item": "Total Revenue / Gross Receipts",
                    "book_amount": total_tb_revenue,
                    "tax_amount": tr.net_receipts,
                    "difference": book_tax_diff,
                    "type": "Temporary" if abs(book_tax_diff) > 0 else "None",
                    "explanation": "Difference between book revenue and tax gross receipts",
                    "action": "Reconcile to M-1/M-3; identify specific timing differences",
                })

        # Book vs tax deferred revenue
        if tr.tax_deferred_revenue_current > 0:
            dr_accounts_total = sum(a.ending_balance for a in self.deferred_accounts)
            dr_diff = dr_accounts_total - tr.tax_deferred_revenue_current
            self.metrics["deferred_rev_book_tax_diff"] = dr_diff

            self.book_tax_differences.append({
                "item": "Deferred Revenue",
                "book_amount": dr_accounts_total,
                "tax_amount": tr.tax_deferred_revenue_current,
                "difference": dr_diff,
                "type": "Temporary",
                "explanation": "Book deferred revenue vs. tax deferred advance payments",
                "action": "Evaluate whether additional amounts qualify for §451(c) deferral",
            })

    def _analyze_m1_adjustments(self):
        """Analyze Schedule M-1/M-3 revenue adjustments."""
        for adj in self.data.tax_return.m1_revenue_adjustments:
            diff = to_decimal(adj.get("book_amount", 0)) - to_decimal(adj.get("tax_amount", 0))
            self.book_tax_differences.append({
                "item": adj.get("description", "M-1 Adjustment"),
                "book_amount": to_decimal(adj.get("book_amount", 0)),
                "tax_amount": to_decimal(adj.get("tax_amount", 0)),
                "difference": diff,
                "type": adj.get("type", "Temporary"),
                "explanation": adj.get("explanation", "Schedule M-1/M-3 adjustment"),
                "action": "Verify adjustment is properly supported and maximized",
            })

            if abs(diff) > Decimal("100000"):
                self.findings.append({
                    "category": "M-1 Adjustment",
                    "account": adj.get("description", ""),
                    "finding": f"Significant book-tax adjustment: ${float(diff):,.0f}",
                    "detail": f"Book: ${float(to_decimal(adj.get('book_amount', 0))):,.0f}, "
                              f"Tax: ${float(to_decimal(adj.get('tax_amount', 0))):,.0f}",
                    "risk_level": "High",
                    "recommendation": "Verify supporting documentation; assess sustainability",
                })

    def _analyze_451_elections(self):
        """Analyze IRC §451 elections and opportunities."""
        tr = self.data.tax_return

        if not tr.section_451c_election:
            # Check if they have deferred revenue but no election
            dr_balance = sum(a.ending_balance for a in self.deferred_accounts)
            if dr_balance > Decimal("100000"):
                self.findings.append({
                    "category": "§451(c) Election",
                    "account": "N/A",
                    "finding": "No §451(c) advance payment deferral election in place",
                    "detail": f"Book deferred revenue of ${float(dr_balance):,.0f} exists, "
                              "but no §451(c) election is in effect. This election allows "
                              "one-year deferral of advance payments for tax purposes.",
                    "risk_level": "High",
                    "recommendation": "Evaluate filing §451(c) election — potential significant deferral",
                })
                self.adjustments.append({
                    "type": "Opportunity",
                    "description": "File §451(c) advance payment deferral election",
                    "estimated_impact": dr_balance,
                    "tax_impact": float(dr_balance) * 0.21,
                    "timing": "Temporary — reverses in following year",
                    "implementation": "File Form 3115 for change in accounting method",
                    "risk": "Low — well-established IRS guidance (Rev. Proc. 2004-34)",
                })
        else:
            self.findings.append({
                "category": "§451(c) Election",
                "account": "N/A",
                "finding": "§451(c) election is in place",
                "detail": "Advance payment deferral election is active. "
                          "Verify all qualifying advance payments are being deferred.",
                "risk_level": "Low",
                "recommendation": "Confirm deferral is maximized across all revenue streams",
            })

        if not tr.section_451b_afs and tr.accounting_method == "accrual":
            self.findings.append({
                "category": "§451(b) AFS",
                "account": "N/A",
                "finding": "§451(b) applicable financial statement rule may apply",
                "detail": "Accrual method taxpayer may be subject to §451(b) AFS income "
                          "inclusion rule. Revenue must be recognized for tax no later than "
                          "when recognized on the applicable financial statement.",
                "risk_level": "Medium",
                "recommendation": "Confirm §451(b) compliance; identify any acceleration risk",
            })

    def _analyze_work_paper_positions(self):
        """Analyze tax work paper positions for opportunities."""
        for wp in self.data.work_papers:
            if wp.difference != 0:
                self.book_tax_differences.append({
                    "item": wp.description,
                    "book_amount": wp.book_amount,
                    "tax_amount": wp.tax_amount,
                    "difference": wp.difference,
                    "type": wp.permanent_or_temporary,
                    "explanation": wp.notes,
                    "action": f"Review {wp.supporting_reference}" if wp.supporting_reference else "Review supporting documentation",
                })

            # Check for DTA items that may indicate overpayment
            if wp.dta_or_dtl == "DTA" and wp.difference > Decimal("50000"):
                self.findings.append({
                    "category": "Deferred Tax Asset",
                    "account": wp.description,
                    "finding": f"Significant DTA of ${float(wp.difference * Decimal('0.21')):,.0f}",
                    "detail": f"Book-tax difference of ${float(wp.difference):,.0f} creates "
                              f"deferred tax asset. Category: {wp.category}.",
                    "risk_level": "Medium",
                    "recommendation": "Verify DTA will reverse; assess valuation allowance need",
                })

    def _compute_adjustment_opportunities(self):
        """Identify potential adjustments based on combined analysis."""
        # Look at account mappings for method differences
        for mapping in self.data.account_mappings:
            if mapping.tax_treatment == "method-difference" and mapping.book_tax_difference != 0:
                self.adjustments.append({
                    "type": "Method Difference",
                    "description": f"Account {mapping.account_number}: "
                                   f"{mapping.revenue_stream} — method difference",
                    "estimated_impact": mapping.book_tax_difference,
                    "tax_impact": float(mapping.book_tax_difference) * 0.21,
                    "timing": "Depends on method",
                    "implementation": "May require Form 3115",
                    "risk": "Medium — depends on specific method change",
                })

    def _cross_reference_phase1(self):
        """Cross-reference Phase 2 findings with Phase 1 opportunities."""
        if not self.data.phase1_results:
            return

        phase1_opps = self.data.phase1_results.get("opportunities", [])
        for opp in phase1_opps:
            if opp["risk_level"] == "High":
                # Check if we found corresponding Phase 2 evidence
                matched = False
                for finding in self.findings:
                    if opp["category"].lower() in finding["category"].lower():
                        matched = True
                        finding["phase1_cross_ref"] = opp["finding"]
                        break

                if not matched:
                    self.findings.append({
                        "category": "Phase 1 Cross-Reference",
                        "account": "N/A",
                        "finding": f"Phase 1 high-priority item not yet resolved: {opp['finding']}",
                        "detail": f"Phase 1 identified: {opp['detail'][:200]}",
                        "risk_level": "Medium",
                        "recommendation": "Requires additional investigation in Phase 3 with contracts",
                    })

    def _compute_summary_metrics(self):
        """Compute summary metrics for the Phase 2 analysis."""
        # Total book-tax differences
        total_temp_diff = sum(
            to_decimal(d["difference"]) for d in self.book_tax_differences
            if d.get("type", "").lower() == "temporary"
        )
        total_perm_diff = sum(
            to_decimal(d["difference"]) for d in self.book_tax_differences
            if d.get("type", "").lower() == "permanent"
        )
        self.metrics["total_temporary_differences"] = total_temp_diff
        self.metrics["total_permanent_differences"] = total_perm_diff
        self.metrics["estimated_tax_impact_temporary"] = float(total_temp_diff) * 0.21

        # Total adjustment opportunities
        total_adj_impact = sum(
            to_decimal(a.get("estimated_impact", 0)) for a in self.adjustments
        )
        self.metrics["total_adjustment_opportunity"] = total_adj_impact
        self.metrics["total_tax_savings_opportunity"] = float(total_adj_impact) * 0.21

        self.metrics["finding_count"] = len(self.findings)
        self.metrics["book_tax_diff_count"] = len(self.book_tax_differences)
        self.metrics["adjustment_count"] = len(self.adjustments)

    def _summarize_tb(self):
        """Create a summary of trial balance by account type."""
        summary = {}
        for acct in self.data.trial_balance:
            acct_type = acct.account_type or "other"
            if acct_type not in summary:
                summary[acct_type] = {
                    "count": 0,
                    "total_beginning": Decimal("0"),
                    "total_ending": Decimal("0"),
                    "total_debits": Decimal("0"),
                    "total_credits": Decimal("0"),
                }
            summary[acct_type]["count"] += 1
            summary[acct_type]["total_beginning"] += acct.beginning_balance
            summary[acct_type]["total_ending"] += acct.ending_balance
            summary[acct_type]["total_debits"] += acct.debits
            summary[acct_type]["total_credits"] += acct.credits
        return summary
