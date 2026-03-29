"""Phase 1: 10-K & Public Information Revenue Recognition Opportunity Analyzer.

This module analyzes publicly available 10-K filing data to identify
revenue recognition opportunities, risks, and areas for further investigation.

Input: Company financial data extracted from 10-K filings (manually entered or parsed).
Output: Excel workbook with opportunity analysis across multiple dimensions.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from decimal import Decimal


@dataclass
class CompanyProfile:
    """Basic company information from public filings."""
    name: str
    ticker: Optional[str] = None
    cik: Optional[str] = None
    sic_code: Optional[str] = None
    industry: str = ""
    fiscal_year_end_month: int = 12
    filing_date: Optional[str] = None
    reporting_currency: str = "USD"


@dataclass
class RevenueStream:
    """A distinct revenue stream disclosed in the 10-K."""
    name: str
    description: str = ""
    recognition_method: str = ""  # point-in-time, over-time, subscription, license, etc.
    amount_current: Decimal = Decimal("0")
    amount_prior: Decimal = Decimal("0")
    amount_two_years_prior: Decimal = Decimal("0")
    geographic_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    customer_concentration_pct: Optional[float] = None  # % from largest customer
    notes: str = ""


@dataclass
class DeferredRevenueData:
    """Deferred revenue / contract liability data from the balance sheet."""
    current_balance: Decimal = Decimal("0")
    prior_balance: Decimal = Decimal("0")
    current_portion: Decimal = Decimal("0")
    noncurrent_portion: Decimal = Decimal("0")
    revenue_recognized_from_opening: Decimal = Decimal("0")  # recognized from prior-year deferred
    notes: str = ""


@dataclass
class ContractAssetData:
    """Contract asset / unbilled receivable data from the balance sheet."""
    current_balance: Decimal = Decimal("0")
    prior_balance: Decimal = Decimal("0")
    impairment_losses: Decimal = Decimal("0")
    notes: str = ""


@dataclass
class RevenueDisclosures:
    """Key revenue-related disclosures from the 10-K notes."""
    asc606_policy_summary: str = ""
    significant_judgments: List[str] = field(default_factory=list)
    variable_consideration_types: List[str] = field(default_factory=list)
    contract_cost_capitalized: Decimal = Decimal("0")
    remaining_performance_obligations: Decimal = Decimal("0")
    rpo_expected_timing: str = ""  # e.g., "60% within 1 year, 40% within 2 years"
    disaggregation_dimensions: List[str] = field(default_factory=list)  # geography, product, timing
    significant_changes_noted: List[str] = field(default_factory=list)
    related_party_revenue: Decimal = Decimal("0")
    notes: str = ""


@dataclass
class IncomeStatementData:
    """Key income statement figures for ratio analysis."""
    total_revenue_current: Decimal = Decimal("0")
    total_revenue_prior: Decimal = Decimal("0")
    total_revenue_two_years_prior: Decimal = Decimal("0")
    cost_of_revenue_current: Decimal = Decimal("0")
    cost_of_revenue_prior: Decimal = Decimal("0")
    operating_income_current: Decimal = Decimal("0")
    operating_income_prior: Decimal = Decimal("0")
    net_income_current: Decimal = Decimal("0")
    net_income_prior: Decimal = Decimal("0")
    income_tax_expense_current: Decimal = Decimal("0")
    income_tax_expense_prior: Decimal = Decimal("0")
    pretax_income_current: Decimal = Decimal("0")
    pretax_income_prior: Decimal = Decimal("0")


@dataclass
class BalanceSheetData:
    """Key balance sheet figures relevant to revenue recognition."""
    accounts_receivable_current: Decimal = Decimal("0")
    accounts_receivable_prior: Decimal = Decimal("0")
    allowance_for_doubtful_current: Decimal = Decimal("0")
    allowance_for_doubtful_prior: Decimal = Decimal("0")
    total_assets_current: Decimal = Decimal("0")
    total_assets_prior: Decimal = Decimal("0")


@dataclass
class TenKInput:
    """Complete input data for Phase 1 analysis from a 10-K filing."""
    company: CompanyProfile
    revenue_streams: List[RevenueStream] = field(default_factory=list)
    deferred_revenue: DeferredRevenueData = field(default_factory=DeferredRevenueData)
    contract_assets: ContractAssetData = field(default_factory=ContractAssetData)
    disclosures: RevenueDisclosures = field(default_factory=RevenueDisclosures)
    income_statement: IncomeStatementData = field(default_factory=IncomeStatementData)
    balance_sheet: BalanceSheetData = field(default_factory=BalanceSheetData)
    auditor_name: str = ""
    audit_opinion_type: str = ""  # unqualified, qualified, adverse, disclaimer
    restatements: List[str] = field(default_factory=list)
    risk_factors_revenue_related: List[str] = field(default_factory=list)


class TenKAnalyzer:
    """Analyzes 10-K data to identify revenue recognition opportunities."""

    # Thresholds for flagging
    DEFERRED_REV_GROWTH_THRESHOLD = 0.15  # 15% YoY growth flags review
    AR_TO_REVENUE_HIGH = 0.25  # AR > 25% of revenue flags review
    REVENUE_GROWTH_VS_AR_GROWTH_GAP = 0.10  # AR growing 10%+ faster than revenue
    GROSS_MARGIN_CHANGE_THRESHOLD = 0.03  # 3pp change in gross margin
    CUSTOMER_CONCENTRATION_THRESHOLD = 0.10  # 10% from single customer
    RPO_SIGNIFICANT_THRESHOLD = 0.20  # RPO > 20% of annual revenue

    def __init__(self, data: TenKInput):
        self.data = data
        self.opportunities = []
        self.risks = []
        self.metrics = {}

    def analyze(self) -> dict:
        """Run all analyses and return structured results."""
        self._compute_revenue_metrics()
        self._analyze_revenue_trends()
        self._analyze_deferred_revenue()
        self._analyze_contract_assets()
        self._analyze_receivables()
        self._analyze_disclosure_quality()
        self._analyze_rpo()
        self._analyze_tax_implications()
        self._assess_overall_risk()

        return {
            "company": self.data.company,
            "metrics": self.metrics,
            "opportunities": self.opportunities,
            "risks": self.risks,
            "revenue_streams": self.data.revenue_streams,
            "deferred_revenue": self.data.deferred_revenue,
            "contract_assets": self.data.contract_assets,
            "disclosures": self.data.disclosures,
        }

    def _compute_revenue_metrics(self):
        """Compute key financial metrics from the income statement and balance sheet."""
        inc = self.data.income_statement
        bs = self.data.balance_sheet

        # Revenue growth
        if inc.total_revenue_prior and inc.total_revenue_prior != 0:
            self.metrics["revenue_growth_yoy"] = float(
                (inc.total_revenue_current - inc.total_revenue_prior) / abs(inc.total_revenue_prior)
            )
        else:
            self.metrics["revenue_growth_yoy"] = None

        if inc.total_revenue_two_years_prior and inc.total_revenue_two_years_prior != 0:
            self.metrics["revenue_growth_2yr"] = float(
                (inc.total_revenue_prior - inc.total_revenue_two_years_prior)
                / abs(inc.total_revenue_two_years_prior)
            )
        else:
            self.metrics["revenue_growth_2yr"] = None

        # Gross margin
        if inc.total_revenue_current and inc.total_revenue_current != 0:
            self.metrics["gross_margin_current"] = float(
                (inc.total_revenue_current - inc.cost_of_revenue_current) / inc.total_revenue_current
            )
        else:
            self.metrics["gross_margin_current"] = None

        if inc.total_revenue_prior and inc.total_revenue_prior != 0:
            self.metrics["gross_margin_prior"] = float(
                (inc.total_revenue_prior - inc.cost_of_revenue_prior) / inc.total_revenue_prior
            )
        else:
            self.metrics["gross_margin_prior"] = None

        # AR to revenue ratio
        if inc.total_revenue_current and inc.total_revenue_current != 0:
            self.metrics["ar_to_revenue"] = float(
                bs.accounts_receivable_current / inc.total_revenue_current
            )
        else:
            self.metrics["ar_to_revenue"] = None

        # AR growth
        if bs.accounts_receivable_prior and bs.accounts_receivable_prior != 0:
            self.metrics["ar_growth_yoy"] = float(
                (bs.accounts_receivable_current - bs.accounts_receivable_prior)
                / abs(bs.accounts_receivable_prior)
            )
        else:
            self.metrics["ar_growth_yoy"] = None

        # Days sales outstanding
        if inc.total_revenue_current and inc.total_revenue_current != 0:
            self.metrics["dso"] = float(
                bs.accounts_receivable_current / (inc.total_revenue_current / Decimal("365"))
            )
        else:
            self.metrics["dso"] = None

        # Deferred revenue to revenue ratio
        dr = self.data.deferred_revenue
        if inc.total_revenue_current and inc.total_revenue_current != 0:
            self.metrics["deferred_rev_to_revenue"] = float(
                dr.current_balance / inc.total_revenue_current
            )
        else:
            self.metrics["deferred_rev_to_revenue"] = None

        # Effective tax rate
        if inc.pretax_income_current and inc.pretax_income_current != 0:
            self.metrics["effective_tax_rate"] = float(
                inc.income_tax_expense_current / inc.pretax_income_current
            )
        else:
            self.metrics["effective_tax_rate"] = None

    def _analyze_revenue_trends(self):
        """Identify opportunities from revenue trend analysis."""
        growth = self.metrics.get("revenue_growth_yoy")
        prior_growth = self.metrics.get("revenue_growth_2yr")

        if growth is not None and prior_growth is not None:
            if growth > prior_growth + 0.10:
                self.opportunities.append({
                    "category": "Revenue Trend",
                    "finding": "Revenue growth accelerating significantly",
                    "detail": f"Current YoY growth {growth:.1%} vs prior {prior_growth:.1%}. "
                              "Investigate whether acceleration is from organic growth, "
                              "acquisitions, or changes in recognition timing.",
                    "risk_level": "Medium",
                    "phase2_action": "Compare to trial balance detail for timing of recognition",
                })
            elif growth < prior_growth - 0.10:
                self.risks.append({
                    "category": "Revenue Trend",
                    "finding": "Revenue growth decelerating significantly",
                    "detail": f"Current YoY growth {growth:.1%} vs prior {prior_growth:.1%}. "
                              "May indicate deferred revenue buildup or recognition slowdown.",
                    "risk_level": "Medium",
                    "phase2_action": "Review deferred revenue rollforward in trial balance",
                })

        # Gross margin shift
        gm_current = self.metrics.get("gross_margin_current")
        gm_prior = self.metrics.get("gross_margin_prior")
        if gm_current is not None and gm_prior is not None:
            gm_change = gm_current - gm_prior
            if abs(gm_change) >= self.GROSS_MARGIN_CHANGE_THRESHOLD:
                direction = "increase" if gm_change > 0 else "decrease"
                self.opportunities.append({
                    "category": "Margin Analysis",
                    "finding": f"Significant gross margin {direction}",
                    "detail": f"Gross margin moved from {gm_prior:.1%} to {gm_current:.1%} "
                              f"({gm_change:+.1%}). May indicate revenue mix shift, "
                              "pricing changes, or cost allocation changes.",
                    "risk_level": "Medium",
                    "phase2_action": "Analyze revenue stream margins in trial balance",
                })

        # Revenue stream mix analysis
        for stream in self.data.revenue_streams:
            if stream.amount_prior and stream.amount_prior != 0:
                stream_growth = float(
                    (stream.amount_current - stream.amount_prior) / abs(stream.amount_prior)
                )
                if growth is not None and abs(stream_growth - growth) > 0.15:
                    self.opportunities.append({
                        "category": "Revenue Mix",
                        "finding": f"'{stream.name}' growing differently from total revenue",
                        "detail": f"Stream growth {stream_growth:.1%} vs total {growth:.1%}. "
                                  f"Recognition method: {stream.recognition_method}. "
                                  "Investigate whether mix shift impacts tax timing.",
                        "risk_level": "Low",
                        "phase2_action": "Map to specific GL accounts in trial balance",
                    })

    def _analyze_deferred_revenue(self):
        """Analyze deferred revenue for recognition opportunities."""
        dr = self.data.deferred_revenue
        inc = self.data.income_statement

        if dr.prior_balance and dr.prior_balance != 0:
            dr_growth = float((dr.current_balance - dr.prior_balance) / abs(dr.prior_balance))
            self.metrics["deferred_rev_growth"] = dr_growth

            if dr_growth > self.DEFERRED_REV_GROWTH_THRESHOLD:
                self.opportunities.append({
                    "category": "Deferred Revenue",
                    "finding": "Deferred revenue growing faster than threshold",
                    "detail": f"Deferred revenue grew {dr_growth:.1%} YoY. "
                              f"Current balance: ${dr.current_balance:,.0f}. "
                              "Growing deferred revenue may indicate conservative recognition "
                              "or changing business model. Review for potential earlier recognition.",
                    "risk_level": "High",
                    "phase2_action": "Obtain deferred revenue rollforward schedule from trial balance",
                })
            elif dr_growth < -self.DEFERRED_REV_GROWTH_THRESHOLD:
                self.risks.append({
                    "category": "Deferred Revenue",
                    "finding": "Deferred revenue declining significantly",
                    "detail": f"Deferred revenue declined {dr_growth:.1%} YoY. "
                              "May indicate accelerated recognition or shrinking backlog.",
                    "risk_level": "Medium",
                    "phase2_action": "Review recognition timing in work papers",
                })

        # Revenue recognized from opening deferred balance
        if dr.revenue_recognized_from_opening and dr.prior_balance and dr.prior_balance != 0:
            recognition_rate = float(dr.revenue_recognized_from_opening / dr.prior_balance)
            self.metrics["deferred_rev_recognition_rate"] = recognition_rate
            self.opportunities.append({
                "category": "Deferred Revenue",
                "finding": "Deferred revenue recognition rate analysis",
                "detail": f"{recognition_rate:.1%} of opening deferred revenue recognized in current year. "
                          f"Amount: ${dr.revenue_recognized_from_opening:,.0f} from "
                          f"${dr.prior_balance:,.0f} opening balance. "
                          "Evaluate whether recognition timing aligns with tax positions.",
                "risk_level": "Low",
                "phase2_action": "Tie to specific contract groups in tax return work papers",
            })

    def _analyze_contract_assets(self):
        """Analyze contract assets / unbilled receivables."""
        ca = self.data.contract_assets

        if ca.current_balance > 0:
            if ca.prior_balance and ca.prior_balance != 0:
                ca_growth = float((ca.current_balance - ca.prior_balance) / abs(ca.prior_balance))
                self.metrics["contract_asset_growth"] = ca_growth

                if ca_growth > 0.20:
                    self.opportunities.append({
                        "category": "Contract Assets",
                        "finding": "Contract assets growing significantly",
                        "detail": f"Contract assets grew {ca_growth:.1%} to ${ca.current_balance:,.0f}. "
                                  "Indicates revenue recognized ahead of billing. "
                                  "Evaluate tax treatment of unbilled amounts.",
                        "risk_level": "Medium",
                        "phase2_action": "Reconcile contract assets to trial balance unbilled AR",
                    })

            if ca.impairment_losses > 0:
                self.risks.append({
                    "category": "Contract Assets",
                    "finding": "Contract asset impairment recorded",
                    "detail": f"Impairment of ${ca.impairment_losses:,.0f} on contract assets. "
                              "Review deductibility and timing for tax purposes.",
                    "risk_level": "Medium",
                    "phase2_action": "Review impairment analysis in work papers for tax deductibility",
                })

    def _analyze_receivables(self):
        """Analyze accounts receivable relative to revenue."""
        ar_ratio = self.metrics.get("ar_to_revenue")
        ar_growth = self.metrics.get("ar_growth_yoy")
        rev_growth = self.metrics.get("revenue_growth_yoy")
        dso = self.metrics.get("dso")

        if ar_ratio is not None and ar_ratio > self.AR_TO_REVENUE_HIGH:
            self.risks.append({
                "category": "Receivables",
                "finding": "High AR-to-revenue ratio",
                "detail": f"AR is {ar_ratio:.1%} of annual revenue (DSO: {dso:.0f} days). "
                          "May indicate aggressive revenue recognition or collection issues.",
                "risk_level": "High",
                "phase2_action": "Age AR in trial balance; review bad debt reserve adequacy",
            })

        if ar_growth is not None and rev_growth is not None:
            gap = ar_growth - rev_growth
            if gap > self.REVENUE_GROWTH_VS_AR_GROWTH_GAP:
                self.risks.append({
                    "category": "Receivables",
                    "finding": "AR growing faster than revenue",
                    "detail": f"AR growth {ar_growth:.1%} vs revenue growth {rev_growth:.1%} "
                              f"(gap: {gap:.1%}). Classic indicator of potential recognition issues.",
                    "risk_level": "High",
                    "phase2_action": "Detailed AR aging and revenue cutoff testing in Phase 2",
                })

    def _analyze_disclosure_quality(self):
        """Assess the quality and completeness of revenue disclosures."""
        disc = self.data.disclosures

        if disc.significant_judgments:
            for judgment in disc.significant_judgments:
                self.opportunities.append({
                    "category": "Disclosure Analysis",
                    "finding": "Significant judgment area identified",
                    "detail": f"Management judgment: {judgment}. "
                              "Areas of judgment create opportunities for tax-favorable positions.",
                    "risk_level": "Medium",
                    "phase2_action": "Review supporting documentation in work papers",
                })

        if disc.variable_consideration_types:
            self.opportunities.append({
                "category": "Variable Consideration",
                "finding": "Variable consideration elements present",
                "detail": f"Types: {', '.join(disc.variable_consideration_types)}. "
                          "Variable consideration creates timing differences between "
                          "book and tax recognition.",
                "risk_level": "Medium",
                "phase2_action": "Quantify variable consideration impact from tax return",
            })

        if disc.significant_changes_noted:
            for change in disc.significant_changes_noted:
                self.risks.append({
                    "category": "Disclosure Analysis",
                    "finding": "Significant change in revenue recognition noted",
                    "detail": change,
                    "risk_level": "High",
                    "phase2_action": "Assess book-tax impact of the change",
                })

        if disc.related_party_revenue > 0:
            self.risks.append({
                "category": "Related Parties",
                "finding": "Related party revenue present",
                "detail": f"Related party revenue: ${disc.related_party_revenue:,.0f}. "
                          "Review for arm's length pricing and recognition timing.",
                "risk_level": "Medium",
                "phase2_action": "Review transfer pricing documentation",
            })

    def _analyze_rpo(self):
        """Analyze remaining performance obligations."""
        disc = self.data.disclosures
        inc = self.data.income_statement

        if disc.remaining_performance_obligations > 0 and inc.total_revenue_current > 0:
            rpo_ratio = float(
                disc.remaining_performance_obligations / inc.total_revenue_current
            )
            self.metrics["rpo_to_revenue"] = rpo_ratio

            if rpo_ratio > self.RPO_SIGNIFICANT_THRESHOLD:
                self.opportunities.append({
                    "category": "Performance Obligations",
                    "finding": "Significant remaining performance obligations",
                    "detail": f"RPO of ${disc.remaining_performance_obligations:,.0f} "
                              f"is {rpo_ratio:.1%} of annual revenue. "
                              f"Timing: {disc.rpo_expected_timing}. "
                              "Large RPO indicates future revenue visibility; "
                              "review expected timing for tax planning opportunities.",
                    "risk_level": "Low",
                    "phase2_action": "Map RPO to specific contract categories for tax timing analysis",
                })

    def _analyze_tax_implications(self):
        """Identify revenue recognition tax opportunities."""
        etr = self.metrics.get("effective_tax_rate")
        inc = self.data.income_statement

        if etr is not None:
            if etr > 0.25:
                self.opportunities.append({
                    "category": "Tax Rate",
                    "finding": "Effective tax rate above statutory rate",
                    "detail": f"ETR of {etr:.1%} exceeds 21% statutory rate. "
                              "Revenue timing differences may contribute to higher ETR. "
                              "Evaluate deferral opportunities.",
                    "risk_level": "Medium",
                    "phase2_action": "Analyze rate reconciliation in tax return for revenue timing items",
                })
            elif etr < 0.15:
                self.risks.append({
                    "category": "Tax Rate",
                    "finding": "Effective tax rate well below statutory rate",
                    "detail": f"ETR of {etr:.1%} is significantly below 21%. "
                              "Review for sustainability and any revenue-related tax positions.",
                    "risk_level": "Low",
                    "phase2_action": "Review tax provision work papers for revenue-related adjustments",
                })

        # Book-tax difference indicators
        dr = self.data.deferred_revenue
        if dr.current_balance > 0 and inc.total_revenue_current > 0:
            self.opportunities.append({
                "category": "Book-Tax Differences",
                "finding": "Deferred revenue creates potential book-tax timing difference",
                "detail": f"Deferred revenue balance of ${dr.current_balance:,.0f}. "
                          "Under IRC §451(c), advance payments may be deferred one year for tax. "
                          "Evaluate whether full deferral election is being utilized.",
                "risk_level": "High",
                "phase2_action": "Compare book deferred revenue to tax deferred revenue on return",
            })

        # Restatement risk
        if self.data.restatements:
            for restatement in self.data.restatements:
                self.risks.append({
                    "category": "Restatement",
                    "finding": "Revenue-related restatement history",
                    "detail": restatement,
                    "risk_level": "High",
                    "phase2_action": "Review amended returns and carryforward impacts",
                })

    def _assess_overall_risk(self):
        """Compute an overall risk score based on findings."""
        high_count = sum(1 for o in self.opportunities + self.risks if o["risk_level"] == "High")
        medium_count = sum(1 for o in self.opportunities + self.risks if o["risk_level"] == "Medium")

        score = high_count * 3 + medium_count * 1
        if score >= 8:
            self.metrics["overall_risk_assessment"] = "High"
        elif score >= 4:
            self.metrics["overall_risk_assessment"] = "Medium"
        else:
            self.metrics["overall_risk_assessment"] = "Low"

        self.metrics["opportunity_count"] = len(self.opportunities)
        self.metrics["risk_count"] = len(self.risks)
        self.metrics["high_priority_items"] = high_count
