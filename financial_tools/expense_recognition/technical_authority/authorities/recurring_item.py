"""Technical authorities for the §461(h)(3) recurring item exception.

The recurring item exception allows accrual-method taxpayers to deduct certain
recurring liabilities before economic performance occurs, provided specific
conditions are met.
"""

from .base import TechnicalAuthority

RECURRING_ITEM_AUTHORITIES = [
    TechnicalAuthority(
        citation="IRC §461(h)(3)(A)",
        authority_type="statute",
        title="Recurring Item Exception — Requirements",
        year=1984,
        relevance="Core recurring item exception — 4 requirements for deduction before EP",
        key_holding="The all-events test shall be treated as met with respect to any recurring item if: (1) the all-events test (without regard to EP) is met during the taxable year, (2) economic performance occurs within the shorter of 8½ months after close of taxable year or a reasonable period, (3) the item is recurring in nature and the taxpayer consistently treats similar items as incurred in the taxable year, and (4) either the item is not material or accrual results in more proper matching against income.",
        facts_summary="Four cumulative requirements: all-events test met (w/o EP), EP within 8.5 months, recurring and consistent treatment, not material or better matching.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["recurring item exception", "economic performance", "all-events test"],
    ),
    TechnicalAuthority(
        citation="IRC §461(h)(3)(B)",
        authority_type="statute",
        title="Recurring Item Exception — Limitation",
        year=1984,
        relevance="Workers' comp and tort liabilities excluded from recurring item exception",
        key_holding="The recurring item exception shall not apply to any item described in §461(h)(2)(B) — i.e., workers' compensation or tort liabilities.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["recurring item exception", "workers compensation", "tort liability", "exclusion"],
    ),

    # --- Treasury Regulations ---
    TechnicalAuthority(
        citation="Treas. Reg. §1.461-5(a)",
        authority_type="regulation",
        title="Recurring Item Exception — General Rule",
        year=1992,
        relevance="Detailed recurring item exception rules and requirements",
        key_holding="A liability that is not otherwise deductible until EP occurs may be treated as incurred in the year the all-events test is met (w/o EP) if the recurring item exception applies. The liability must also meet EP within 8½ months after close of the year.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["recurring item exception", "economic performance", "8.5 months"],
    ),
    TechnicalAuthority(
        citation="Treas. Reg. §1.461-5(b)(1)",
        authority_type="regulation",
        title="Recurring Item Exception — Recurring Requirement",
        year=1992,
        relevance="Definition of 'recurring in nature' for the exception",
        key_holding="A liability is recurring if it can generally be expected to be incurred from one taxable year to the next. The fact that a liability is not incurred every year does not disqualify it if it is the type of liability that can be expected to recur.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["recurring item exception", "recurring in nature"],
    ),
    TechnicalAuthority(
        citation="Treas. Reg. §1.461-5(b)(3)",
        authority_type="regulation",
        title="Recurring Item Exception — Materiality",
        year=1992,
        relevance="Materiality safe harbor: ≤ lesser of 10% of prior year expenses or $10M (as applied in practice)",
        key_holding="An item is not material if it is not material in amount. Whether an item is material is determined based on the particular facts and circumstances. The amount of the item relative to the taxpayer's other expense items is relevant.",
        facts_summary="No bright-line test in regulations; practitioners commonly use lesser of $10M or 10% of recurring expenses as rule of thumb.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["recurring item exception", "materiality"],
    ),
    TechnicalAuthority(
        citation="Treas. Reg. §1.461-5(b)(4)",
        authority_type="regulation",
        title="Recurring Item Exception — Better Matching",
        year=1992,
        relevance="Alternative to materiality — accrual provides more proper matching",
        key_holding="If the item is material, the recurring item exception still applies if accrual of the liability in the earlier year results in a better matching of the liability against the income to which it relates.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["recurring item exception", "matching", "materiality"],
    ),
    TechnicalAuthority(
        citation="Treas. Reg. §1.461-5(c)",
        authority_type="regulation",
        title="Recurring Item Exception — Method of Accounting",
        year=1992,
        relevance="Adopting or changing to recurring item exception requires Form 3115",
        key_holding="Use of the recurring item exception is a method of accounting. A change to or from the recurring item exception is a change in method of accounting requiring consent under §446(e).",
        taxpayer_favorable=True,
        weight="primary",
        topics=["recurring item exception", "method change", "Form 3115"],
    ),

    # --- Case Law ---
    TechnicalAuthority(
        citation="Ohmart Corp. v. Commissioner, T.C. Memo 1995-47",
        authority_type="case_law",
        title="Ohmart — Recurring Item Exception Applied",
        year=1995,
        relevance="Successful application of recurring item exception to accrued liabilities",
        key_holding="Tax Court allowed deduction under recurring item exception where liability was recurring in nature, consistently treated, and economic performance occurred within 8.5 months after year end.",
        taxpayer_favorable=True,
        weight="substantial",
        topics=["recurring item exception", "accrued liabilities"],
    ),

    # --- IRS Guidance ---
    TechnicalAuthority(
        citation="Rev. Proc. 2024-23 (CAM §16.12)",
        authority_type="rev_proc",
        title="Automatic Consent — Recurring Item Exception",
        year=2024,
        relevance="Automatic method change for adopting recurring item exception",
        key_holding="Taxpayers may obtain automatic consent to change to or from the recurring item exception method by filing Form 3115 with the timely filed return. CAM number applies.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["recurring item exception", "method change", "Form 3115", "automatic consent"],
    ),
    TechnicalAuthority(
        citation="CCA 200843024",
        authority_type="cca",
        title="Recurring Item Exception — State Income Taxes",
        year=2008,
        relevance="Recurring item exception applied to state income tax accruals",
        key_holding="Accrued state income taxes may qualify for the recurring item exception if all four requirements are met, allowing deduction before the taxes are actually paid.",
        taxpayer_favorable=True,
        weight="some",
        topics=["recurring item exception", "state taxes", "payment liability"],
    ),
]
