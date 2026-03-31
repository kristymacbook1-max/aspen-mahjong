"""Technical authorities for accounting method changes (IRC §§446, 481)."""

from .base import TechnicalAuthority

METHOD_CHANGE_AUTHORITIES = [
    # -------------------------------------------------------------------------
    # STATUTES
    # -------------------------------------------------------------------------
    TechnicalAuthority(
        citation="IRC §446(a)",
        authority_type="statute",
        title="General Rule for Methods of Accounting",
        year=1954,
        relevance="accounting method changes — general rule",
        key_holding=(
            "Taxable income shall be computed under the method of accounting on "
            "the basis of which the taxpayer regularly computes income in keeping "
            "the taxpayer's books. The method used must clearly reflect income."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["method_change", "446"],
        related_citations=["IRC §446(b)", "IRC §446(e)", "Treas. Reg. 1.446-1(e)"],
    ),
    TechnicalAuthority(
        citation="IRC §446(b)",
        authority_type="statute",
        title="Exceptions — IRS Authority to Impose Method",
        year=1954,
        relevance="accounting method changes — IRS authority to impose method",
        key_holding=(
            "If no method of accounting has been regularly used by the taxpayer, "
            "or if the method used does not clearly reflect income, the "
            "computation of taxable income shall be made under such method as, "
            "in the opinion of the Secretary, does clearly reflect income."
        ),
        taxpayer_favorable=False,
        weight="primary",
        topics=["method_change", "446"],
        related_citations=["IRC §446(a)", "IRC §446(e)"],
    ),
    TechnicalAuthority(
        citation="IRC §446(e)",
        authority_type="statute",
        title="Requirement of Consent for Method Changes",
        year=1954,
        relevance="accounting method changes — consent requirement",
        key_holding=(
            "A taxpayer who changes the method of accounting on the basis of "
            "which the taxpayer regularly computes income in keeping the "
            "taxpayer's books shall, before computing taxable income under the "
            "new method, secure the consent of the Secretary. Consent is "
            "obtained by filing Form 3115."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["method_change", "446", "form_3115"],
        related_citations=[
            "IRC §446(a)",
            "Treas. Reg. 1.446-1(e)",
            "Rev. Proc. 2015-13",
        ],
    ),
    TechnicalAuthority(
        citation="IRC §481(a)",
        authority_type="statute",
        title="Adjustments Required by Changes in Method of Accounting",
        year=1954,
        relevance="accounting method changes — §481(a) adjustment",
        key_holding=(
            "When a taxpayer's method of accounting is changed, the adjustments "
            "necessary to prevent amounts from being duplicated or omitted shall "
            "be taken into account. The §481(a) adjustment captures the "
            "cumulative difference between the old and new methods as of the "
            "beginning of the year of change."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["method_change", "481", "481a_adjustment"],
        related_citations=[
            "IRC §481(b)",
            "Treas. Reg. 1.481-1",
            "Treas. Reg. 1.481-4",
            "Rev. Proc. 2015-13",
        ],
    ),
    TechnicalAuthority(
        citation="IRC §481(b)",
        authority_type="statute",
        title="Limitation on Tax for §481(a) Adjustments",
        year=1954,
        relevance="accounting method changes — tax limitation on adjustments",
        key_holding=(
            "If the §481(a) adjustment results in a substantial increase in "
            "taxable income, the tax attributable to the adjustment is limited "
            "by allocating the increase over a three-year period. This prevents "
            "bunching of income in the year of change."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["method_change", "481", "481a_adjustment"],
        related_citations=["IRC §481(a)", "Treas. Reg. 1.481-4"],
    ),

    # -------------------------------------------------------------------------
    # REGULATIONS
    # -------------------------------------------------------------------------
    TechnicalAuthority(
        citation="Treas. Reg. 1.446-1(e)",
        authority_type="regulation",
        title="Procedures for Obtaining Consent to Change Accounting Method",
        year=1977,
        relevance="accounting method changes — consent procedures",
        key_holding=(
            "A taxpayer must secure IRS consent before changing a method of "
            "accounting for federal income tax purposes. The regulations "
            "prescribe procedures for requesting consent, including filing "
            "requirements and the form of application (Form 3115)."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["method_change", "446", "form_3115", "automatic_consent"],
        related_citations=[
            "IRC §446(e)",
            "Rev. Proc. 2015-13",
            "Rev. Proc. 2024-23",
        ],
    ),
    TechnicalAuthority(
        citation="Treas. Reg. 1.481-1",
        authority_type="regulation",
        title="Computation of §481(a) Adjustment",
        year=1964,
        relevance="accounting method changes — computing the adjustment",
        key_holding=(
            "The §481(a) adjustment is the net amount of adjustments determined "
            "as of the beginning of the year of change necessary to prevent "
            "duplication or omission of income and deductions. The regulation "
            "details the computation methodology and the items included."
        ),
        taxpayer_favorable=True,
        weight="substantial",
        topics=["method_change", "481", "481a_adjustment"],
        related_citations=["IRC §481(a)", "Treas. Reg. 1.481-4"],
    ),
    TechnicalAuthority(
        citation="Treas. Reg. 1.481-4",
        authority_type="regulation",
        title="Spread Period for §481(a) Adjustments",
        year=1964,
        relevance="accounting method changes — adjustment spread period",
        key_holding=(
            "Provides rules for spreading the §481(a) adjustment over an "
            "appropriate period. The spread period prevents taxpayers from "
            "realizing disproportionate tax consequences in the year of change "
            "due to the cumulative nature of the adjustment."
        ),
        taxpayer_favorable=True,
        weight="substantial",
        topics=["method_change", "481", "481a_adjustment"],
        related_citations=[
            "IRC §481(a)",
            "IRC §481(b)",
            "Treas. Reg. 1.481-1",
            "Rev. Proc. 2015-13",
        ],
    ),

    # -------------------------------------------------------------------------
    # REVENUE PROCEDURES
    # -------------------------------------------------------------------------
    TechnicalAuthority(
        citation="Rev. Proc. 2015-13",
        authority_type="rev_proc",
        title="General Procedures for Automatic Consent Method Changes",
        year=2015,
        relevance="accounting method changes — automatic and non-automatic consent procedures",
        key_holding=(
            "Establishes the general procedures for both automatic and "
            "non-automatic consent to change a method of accounting. Automatic "
            "changes are filed with the return; non-automatic changes require "
            "advance IRS ruling. Provides audit protection for voluntary changes "
            "and specifies the §481(a) spread: one year for negative adjustments, "
            "four years for positive adjustments."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=[
            "method_change",
            "446",
            "481",
            "form_3115",
            "automatic_consent",
            "481a_adjustment",
        ],
        related_citations=[
            "IRC §446(e)",
            "IRC §481(a)",
            "Treas. Reg. 1.446-1(e)",
            "Rev. Proc. 2024-23",
            "Rev. Proc. 2002-9",
        ],
    ),
    TechnicalAuthority(
        citation="Rev. Proc. 2024-23",
        authority_type="rev_proc",
        title="List of Automatic Accounting Method Changes",
        year=2024,
        relevance="accounting method changes — automatic change catalog",
        key_holding=(
            "Provides the current comprehensive list of accounting method "
            "changes eligible for automatic consent under Rev. Proc. 2015-13. "
            "Covers changes including advance payment methods, long-term "
            "contract methods, depreciation, and revenue recognition methods. "
            "Each designated change number specifies terms, conditions, and any "
            "limitations on the automatic consent."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["method_change", "446", "form_3115", "automatic_consent"],
        related_citations=[
            "Rev. Proc. 2015-13",
            "IRC §446(e)",
            "Treas. Reg. 1.446-1(e)",
        ],
    ),
    TechnicalAuthority(
        citation="Rev. Proc. 2002-9",
        authority_type="rev_proc",
        title="Predecessor Automatic Consent Procedures (Superseded)",
        year=2002,
        relevance="accounting method changes — prior automatic consent procedures",
        key_holding=(
            "Former revenue procedure governing automatic consent method "
            "changes, now superseded by Rev. Proc. 2015-13. Historical "
            "significance for understanding the evolution of automatic consent "
            "procedures and for interpreting older method change filings."
        ),
        taxpayer_favorable=True,
        weight="limited",
        topics=["method_change", "446", "form_3115", "automatic_consent"],
        related_citations=["Rev. Proc. 2015-13", "IRC §446(e)"],
        notes="Superseded by Rev. Proc. 2015-13.",
    ),

    # -------------------------------------------------------------------------
    # CASE LAW
    # -------------------------------------------------------------------------
    TechnicalAuthority(
        citation="Graff Chevrolet Co. v. Campbell, 343 F.2d 568 (5th Cir. 1965)",
        authority_type="case_law",
        title="Section 481(a) Adjustment Protects Against Income Duplication",
        year=1965,
        relevance="accounting method changes — §481(a) prevents duplication",
        key_holding=(
            "The Fifth Circuit held that the §481(a) adjustment mechanism is "
            "specifically designed to prevent duplication of income when a "
            "taxpayer changes accounting methods. The adjustment ensures that "
            "items of income or deduction are accounted for exactly once across "
            "the transition between methods."
        ),
        facts_summary=(
            "Automobile dealer changed accounting method and contested the IRS "
            "approach to computing the transition adjustment, arguing it caused "
            "income to be recognized twice."
        ),
        taxpayer_favorable=True,
        weight="substantial",
        topics=["method_change", "481", "481a_adjustment"],
        related_citations=["IRC §481(a)", "Treas. Reg. 1.481-1"],
    ),
    TechnicalAuthority(
        citation="Advertisers Exchange Inc. v. Commissioner, 25 T.C. 1086 (1956)",
        authority_type="case_law",
        title="Distinguishing Method Change from Correction of Error",
        year=1956,
        relevance="accounting method changes — change vs. error correction",
        key_holding=(
            "The Tax Court drew the critical distinction between a change in "
            "method of accounting, which requires IRS consent and triggers "
            "§481(a), and a mere correction of an error in applying an existing "
            "method, which does not. A method change involves a consistent "
            "pattern of treatment adopted by the taxpayer."
        ),
        facts_summary=(
            "Taxpayer argued its altered treatment of income items was a "
            "correction of error rather than a change in method, avoiding the "
            "consent requirement and §481(a) adjustment."
        ),
        taxpayer_favorable=True,
        weight="substantial",
        topics=["method_change", "446"],
        related_citations=[
            "IRC §446(e)",
            "IRC §481(a)",
            "Rev. Rul. 90-38",
        ],
    ),
    TechnicalAuthority(
        citation="Wayne Bolt & Nut Co. v. Commissioner, T.C. Memo 1981-371",
        authority_type="case_law",
        title="Scope of §481(a) Adjustment",
        year=1981,
        relevance="accounting method changes — scope of adjustment",
        key_holding=(
            "The Tax Court addressed the breadth of the §481(a) adjustment, "
            "holding that the adjustment must encompass all items affected by "
            "the change in method. The entire cumulative effect of the prior "
            "method must be captured to prevent omission or duplication."
        ),
        facts_summary=(
            "Manufacturing company changed its accounting method and disputed "
            "the scope of the §481(a) adjustment the IRS computed for the "
            "transition."
        ),
        taxpayer_favorable=True,
        weight="some",
        topics=["method_change", "481", "481a_adjustment"],
        related_citations=["IRC §481(a)", "Treas. Reg. 1.481-1"],
    ),

    # -------------------------------------------------------------------------
    # REVENUE RULINGS
    # -------------------------------------------------------------------------
    TechnicalAuthority(
        citation="Rev. Rul. 90-38",
        authority_type="rev_rul",
        title="Distinguishing Change in Method vs. Change in Facts",
        year=1990,
        relevance="accounting method changes — method change vs. factual change",
        key_holding=(
            "A change in the underlying facts does not constitute a change in "
            "method of accounting requiring IRS consent under §446(e). A change "
            "in method occurs only when the taxpayer adopts a different "
            "accounting treatment for the same type of item. A change in facts "
            "may warrant different treatment without triggering §481(a)."
        ),
        taxpayer_favorable=True,
        weight="substantial",
        topics=["method_change", "446"],
        related_citations=[
            "IRC §446(e)",
            "IRC §481(a)",
            "Advertisers Exchange Inc. v. Commissioner, 25 T.C. 1086 (1956)",
        ],
    ),
]
