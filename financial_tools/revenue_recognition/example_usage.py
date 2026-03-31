"""Example usage of the Revenue Recognition analysis tool.

This script demonstrates how to run each phase with sample data.
"""

from decimal import Decimal
from datetime import date

from phase1.ten_k_analyzer import (
    TenKInput, CompanyProfile, RevenueStream, DeferredRevenueData,
    ContractAssetData, RevenueDisclosures, IncomeStatementData, BalanceSheetData,
)
from phase2.trial_balance_analyzer import (
    Phase2Input, TrialBalanceAccount, RevenueAccountMapping,
    DeferredRevenueRollforward, TaxReturnData, WorkPaperItem,
)
from phase3.contract_analyzer import (
    Phase3Input, Contract, PerformanceObligation, VariableConsideration,
    ContractModification,
)
from run_analysis import RevenueRecognitionPipeline


def build_phase1_data() -> TenKInput:
    """Build sample Phase 1 data from a fictional 10-K."""
    return TenKInput(
        company=CompanyProfile(
            name="TechStream Inc.",
            ticker="TSTR",
            cik="0001234567",
            sic_code="7372",
            industry="Software & SaaS",
            fiscal_year_end_month=12,
            filing_date="2026-02-28",
        ),
        revenue_streams=[
            RevenueStream(
                name="SaaS Subscriptions",
                description="Cloud-based software subscriptions recognized ratably",
                recognition_method="Over-time (time-based)",
                amount_current=Decimal("85000000"),
                amount_prior=Decimal("68000000"),
                amount_two_years_prior=Decimal("55000000"),
                geographic_breakdown={
                    "North America": Decimal("55000000"),
                    "Europe": Decimal("20000000"),
                    "Asia-Pacific": Decimal("10000000"),
                },
            ),
            RevenueStream(
                name="Professional Services",
                description="Implementation and consulting services",
                recognition_method="Over-time (input method)",
                amount_current=Decimal("25000000"),
                amount_prior=Decimal("22000000"),
                amount_two_years_prior=Decimal("18000000"),
            ),
            RevenueStream(
                name="License Revenue",
                description="On-premise perpetual licenses",
                recognition_method="Point-in-time",
                amount_current=Decimal("10000000"),
                amount_prior=Decimal("15000000"),
                amount_two_years_prior=Decimal("20000000"),
                notes="Declining as customers migrate to SaaS",
            ),
        ],
        deferred_revenue=DeferredRevenueData(
            current_balance=Decimal("42000000"),
            prior_balance=Decimal("33000000"),
            current_portion=Decimal("35000000"),
            noncurrent_portion=Decimal("7000000"),
            revenue_recognized_from_opening=Decimal("28000000"),
        ),
        contract_assets=ContractAssetData(
            current_balance=Decimal("8000000"),
            prior_balance=Decimal("5500000"),
            impairment_losses=Decimal("200000"),
        ),
        disclosures=RevenueDisclosures(
            asc606_policy_summary=(
                "Revenue is recognized when control transfers to the customer. "
                "SaaS subscriptions are recognized ratably over the contract term. "
                "Professional services are recognized using the input method based on costs incurred."
            ),
            significant_judgments=[
                "Determination of standalone selling prices for bundled arrangements",
                "Assessment of variable consideration constraints for volume discounts",
            ],
            variable_consideration_types=["Volume discounts", "Service level credits", "Early termination penalties"],
            remaining_performance_obligations=Decimal("95000000"),
            rpo_expected_timing="65% within 12 months, 30% within 24 months, 5% thereafter",
            disaggregation_dimensions=["Product type", "Geography", "Timing of recognition"],
        ),
        income_statement=IncomeStatementData(
            total_revenue_current=Decimal("120000000"),
            total_revenue_prior=Decimal("105000000"),
            total_revenue_two_years_prior=Decimal("93000000"),
            cost_of_revenue_current=Decimal("42000000"),
            cost_of_revenue_prior=Decimal("38000000"),
            operating_income_current=Decimal("30000000"),
            operating_income_prior=Decimal("25000000"),
            net_income_current=Decimal("22000000"),
            net_income_prior=Decimal("18000000"),
            income_tax_expense_current=Decimal("7500000"),
            income_tax_expense_prior=Decimal("6200000"),
            pretax_income_current=Decimal("28000000"),
            pretax_income_prior=Decimal("23000000"),
        ),
        balance_sheet=BalanceSheetData(
            accounts_receivable_current=Decimal("32000000"),
            accounts_receivable_prior=Decimal("25000000"),
            allowance_for_doubtful_current=Decimal("1500000"),
            allowance_for_doubtful_prior=Decimal("1200000"),
            total_assets_current=Decimal("200000000"),
            total_assets_prior=Decimal("175000000"),
        ),
        auditor_name="Big Four LLP",
        audit_opinion_type="Unqualified",
        risk_factors_revenue_related=[
            "Customer concentration: top 10 customers represent 35% of revenue",
            "Transition from license to SaaS model creates revenue timing uncertainty",
        ],
    )


def build_phase2_data() -> Phase2Input:
    """Build sample Phase 2 data from trial balance and tax return."""
    return Phase2Input(
        trial_balance=[
            TrialBalanceAccount("4000", "SaaS Subscription Revenue", "revenue",
                                Decimal("68000000"), Decimal("85000000"),
                                Decimal("2000000"), Decimal("87000000")),
            TrialBalanceAccount("4100", "Professional Services Revenue", "revenue",
                                Decimal("22000000"), Decimal("25000000"),
                                Decimal("500000"), Decimal("25500000")),
            TrialBalanceAccount("4200", "License Revenue", "revenue",
                                Decimal("15000000"), Decimal("10000000"),
                                Decimal("1000000"), Decimal("11000000")),
            TrialBalanceAccount("2300", "Deferred Revenue - Current", "deferred_revenue",
                                Decimal("28000000"), Decimal("35000000"),
                                Decimal("28000000"), Decimal("35000000")),
            TrialBalanceAccount("2310", "Deferred Revenue - Non-Current", "deferred_revenue",
                                Decimal("5000000"), Decimal("7000000"),
                                Decimal("3000000"), Decimal("5000000")),
            TrialBalanceAccount("1200", "Accounts Receivable", "ar",
                                Decimal("25000000"), Decimal("32000000"),
                                Decimal("120000000"), Decimal("113000000")),
            TrialBalanceAccount("1210", "Contract Assets / Unbilled AR", "contract_asset",
                                Decimal("5500000"), Decimal("8000000"),
                                Decimal("8000000"), Decimal("5500000")),
        ],
        account_mappings=[
            RevenueAccountMapping("4000", "SaaS Subscriptions", "over-time",
                                  "deferred", Decimal("5000000"),
                                  "Tax defers advance payments under §451(c)"),
            RevenueAccountMapping("4100", "Professional Services", "over-time",
                                  "same-as-book", Decimal("0")),
            RevenueAccountMapping("4200", "License Revenue", "point-in-time",
                                  "same-as-book", Decimal("0")),
        ],
        deferred_rollforwards=[
            DeferredRevenueRollforward(
                "SaaS Subscriptions",
                Decimal("28000000"), Decimal("40000000"), Decimal("33000000"),
                Decimal("0"), Decimal("35000000"),
            ),
            DeferredRevenueRollforward(
                "Professional Services",
                Decimal("5000000"), Decimal("12000000"), Decimal("10000000"),
                Decimal("0"), Decimal("7000000"),
            ),
        ],
        tax_return=TaxReturnData(
            form_type="1120",
            tax_year=2025,
            gross_receipts_line=Decimal("118000000"),
            returns_and_allowances=Decimal("3000000"),
            net_receipts=Decimal("115000000"),
            book_income=Decimal("22000000"),
            tax_income=Decimal("20000000"),
            m1_revenue_adjustments=[
                {
                    "description": "Advance payments deferred under §451(c)",
                    "book_amount": Decimal("120000000"),
                    "tax_amount": Decimal("115000000"),
                    "type": "Temporary",
                    "explanation": "SaaS advance payments deferred one year for tax",
                },
            ],
            accounting_method="accrual",
            section_451c_election=True,
            section_451b_afs=True,
            tax_deferred_revenue_current=Decimal("38000000"),
            tax_deferred_revenue_prior=Decimal("30000000"),
        ),
        work_papers=[
            WorkPaperItem(
                "SaaS advance payment deferral",
                "revenue_timing",
                Decimal("85000000"), Decimal("80000000"),
                Decimal("5000000"), "temporary", "DTL",
                "WP-Rev-01",
                "Advance payments for annual SaaS subscriptions deferred under §451(c)",
            ),
            WorkPaperItem(
                "Contract asset — unbilled revenue",
                "revenue_timing",
                Decimal("8000000"), Decimal("8000000"),
                Decimal("0"), "temporary", "",
                "WP-Rev-02",
                "Unbilled AR recognized same for book and tax",
            ),
        ],
    )


def build_phase3_data() -> Phase3Input:
    """Build sample Phase 3 data with contracts."""
    return Phase3Input(
        contracts=[
            Contract(
                id="C-2025-001",
                customer_name="MegaCorp Industries",
                description="3-year SaaS platform + implementation",
                contract_date=date(2025, 1, 15),
                start_date=date(2025, 3, 1),
                end_date=date(2028, 2, 28),
                total_transaction_price=Decimal("2400000"),
                performance_obligations=[
                    PerformanceObligation(
                        id="PO-001-A",
                        description="SaaS Platform Access (36 months)",
                        type="license_right_to_access",
                        satisfaction_pattern="over-time-time",
                        standalone_selling_price=Decimal("2000000"),
                        allocated_transaction_price=Decimal("1920000"),
                        service_start=date(2025, 3, 1),
                        service_end=date(2028, 2, 28),
                        book_revenue_recognized=Decimal("640000"),
                        book_revenue_deferred=Decimal("1280000"),
                        tax_revenue_recognized=Decimal("800000"),
                        tax_treatment_notes="Tax recognizes billing-based under §451(c); "
                                            "book uses ratable recognition",
                    ),
                    PerformanceObligation(
                        id="PO-001-B",
                        description="Implementation Services",
                        type="service",
                        satisfaction_pattern="over-time-input",
                        standalone_selling_price=Decimal("500000"),
                        allocated_transaction_price=Decimal("480000"),
                        costs_incurred=Decimal("350000"),
                        total_estimated_costs=Decimal("400000"),
                        book_revenue_recognized=Decimal("420000"),
                        book_revenue_deferred=Decimal("60000"),
                        tax_revenue_recognized=Decimal("420000"),
                    ),
                ],
                variable_consideration=[
                    VariableConsideration(
                        type="discount",
                        description="Volume discount if seats exceed 500",
                        estimated_amount=Decimal("120000"),
                        constrained_amount=Decimal("80000"),
                        estimation_method="most_likely_amount",
                        constraint_rationale="Not highly probable seats will exceed threshold",
                        book_treatment="$80K included in transaction price",
                        tax_treatment="Full $120K may be includable for tax",
                        book_tax_difference=Decimal("40000"),
                    ),
                ],
                tax_method="accrual",
                section_451c_applicable=True,
                advance_payment_amount=Decimal("800000"),
            ),
            Contract(
                id="C-2025-002",
                customer_name="SmallBiz LLC",
                description="Annual SaaS subscription",
                contract_date=date(2025, 7, 1),
                start_date=date(2025, 7, 1),
                end_date=date(2026, 6, 30),
                total_transaction_price=Decimal("60000"),
                performance_obligations=[
                    PerformanceObligation(
                        id="PO-002-A",
                        description="SaaS Annual Subscription",
                        type="license_right_to_access",
                        satisfaction_pattern="over-time-time",
                        standalone_selling_price=Decimal("60000"),
                        allocated_transaction_price=Decimal("60000"),
                        service_start=date(2025, 7, 1),
                        service_end=date(2026, 6, 30),
                        book_revenue_recognized=Decimal("30000"),
                        book_revenue_deferred=Decimal("30000"),
                        tax_revenue_recognized=Decimal("60000"),
                        tax_treatment_notes="Full amount taxable in year of receipt under §451(c) "
                                            "(recognized in AFS within next year)",
                    ),
                ],
                tax_method="accrual",
                section_451c_applicable=True,
                advance_payment_amount=Decimal("60000"),
            ),
        ],
        reporting_period_end=date(2025, 12, 31),
        tax_year=2025,
        statutory_rate=0.21,
    )


def main():
    """Run the full three-phase analysis with sample data."""
    pipeline = RevenueRecognitionPipeline(
        company_name="TechStream Inc.",
        output_dir="output/revenue_recognition",
    )

    # Phase 1
    phase1_data = build_phase1_data()
    pipeline.run_phase1(phase1_data)

    # Phase 2
    phase2_data = build_phase2_data()
    pipeline.run_phase2(phase2_data)

    # Phase 3
    phase3_data = build_phase3_data()
    pipeline.run_phase3(phase3_data)

    print("\nDone! Check the output/ directory for Excel reports.")


if __name__ == "__main__":
    main()
