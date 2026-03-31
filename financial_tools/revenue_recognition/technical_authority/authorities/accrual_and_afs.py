"""Technical authorities for accrual method, all events test, and IRC §451(b) AFS rule."""

from .base import TechnicalAuthority

ACCRUAL_AFS_AUTHORITIES = [
    # ── STATUTES ──────────────────────────────────────────────────────────
    TechnicalAuthority(
        citation="IRC §451(a)",
        authority_type="statute",
        title="General Rule for Taxable Year of Inclusion",
        year=1954,
        relevance="accrual method; general timing rule for income inclusion",
        key_holding=(
            "An item of gross income is includable in the taxable year in which "
            "it is received by the taxpayer, unless under the taxpayer's method of "
            "accounting it is to be properly accounted for in a different period. "
            "For accrual method taxpayers, this defers to the all events test "
            "developed under regulations and case law."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["accrual_method", "all_events_test"],
        related_citations=["IRC §451(b)", "Treas. Reg. 1.451-1(a)"],
    ),
    TechnicalAuthority(
        citation="IRC §451(b)",
        authority_type="statute",
        title="Special Rule for Applicable Financial Statement Income Inclusion",
        year=2017,
        relevance=(
            "AFS income inclusion rule added by TCJA; accelerates income "
            "recognition for accrual method taxpayers with an AFS"
        ),
        key_holding=(
            "For accrual method taxpayers with an applicable financial statement, "
            "income must be recognized for tax purposes no later than the taxable "
            "year in which that income is recognized as revenue on the AFS. This "
            "rule, added by the Tax Cuts and Jobs Act of 2017, creates a financial "
            "statement conformity requirement that can accelerate income inclusion "
            "relative to the traditional all events test."
        ),
        taxpayer_favorable=False,
        weight="primary",
        topics=["451b", "afs", "financial_statement_conformity", "accrual_method"],
        related_citations=[
            "IRC §451(a)",
            "IRC §451(b)(3)",
            "Treas. Reg. 1.451-3",
            "Notice 2018-35",
        ],
    ),
    TechnicalAuthority(
        citation="IRC §451(b)(3)",
        authority_type="statute",
        title="Definition of Applicable Financial Statement",
        year=2017,
        relevance="defines which financial statements qualify as an AFS under §451(b)",
        key_holding=(
            "An applicable financial statement is defined in order of priority as: "
            "(1) a 10-K or other annual statement filed with the SEC; "
            "(2) an audited financial statement used for credit, reporting to "
            "partners/shareholders, or any other substantial non-tax purpose; or "
            "(3) a financial statement filed with a federal agency other than the "
            "IRS or SEC."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["451b", "afs", "financial_statement_conformity"],
        related_citations=["IRC §451(b)", "Treas. Reg. 1.451-3"],
    ),

    # ── REGULATIONS ───────────────────────────────────────────────────────
    TechnicalAuthority(
        citation="Treas. Reg. 1.451-1(a)",
        authority_type="regulation",
        title="General Rule for Taxable Year of Inclusion — Accrual Method",
        year=1957,
        relevance="all events test for accrual method income recognition",
        key_holding=(
            "Under the accrual method, income is includable in the taxable year "
            "when all the events have occurred that fix the right to receive such "
            "income and the amount thereof can be determined with reasonable "
            "accuracy. This two-prong standard — the all events test — is the "
            "foundational timing rule for accrual basis taxpayers."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["accrual_method", "all_events_test"],
        related_citations=[
            "IRC §451(a)",
            "Spring City Foundry Co. v. Commissioner, 292 U.S. 182 (1934)",
        ],
    ),
    TechnicalAuthority(
        citation="Treas. Reg. 1.451-3",
        authority_type="regulation",
        title="AFS Income Inclusion Rule Regulations",
        year=2021,
        relevance=(
            "final regulations implementing §451(b) AFS income inclusion rule; "
            "interaction with other Code provisions"
        ),
        key_holding=(
            "These final regulations, issued in 2021, implement the AFS income "
            "inclusion rule under IRC §451(b). They specify how AFS revenue "
            "recognition interacts with other Code provisions, define the treatment "
            "of multi-year contracts and variable consideration, and provide "
            "ordering rules when §451(b) and other income acceleration provisions "
            "both apply."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["451b", "afs", "financial_statement_conformity", "accrual_method"],
        related_citations=[
            "IRC §451(b)",
            "IRC §451(b)(3)",
            "Notice 2018-35",
        ],
    ),

    # ── CASE LAW ──────────────────────────────────────────────────────────
    TechnicalAuthority(
        citation="United States v. General Dynamics Corp., 481 U.S. 239 (1987)",
        authority_type="case_law",
        title="All Events Test — Deductions; Right Must Be Fixed",
        year=1987,
        relevance="all events test; requirement that liability be fixed, not contingent",
        key_holding=(
            "The Supreme Court held that the all events test requires that a "
            "liability be fixed and not merely contingent before an accrual method "
            "taxpayer may take a deduction. Although the case addressed deductions, "
            "the Court's articulation of the all events test applies equally to the "
            "income side and remains the leading modern authority on the 'fixed "
            "right' prong."
        ),
        facts_summary=(
            "General Dynamics sought to deduct estimated future costs of providing "
            "medical benefits to employees who had not yet filed claims. The IRS "
            "disallowed the deduction on the ground that the liability was not yet "
            "fixed."
        ),
        taxpayer_favorable=False,
        weight="primary",
        topics=["all_events_test", "accrual_method"],
        related_citations=[
            "Treas. Reg. 1.451-1(a)",
            "Spring City Foundry Co. v. Commissioner, 292 U.S. 182 (1934)",
        ],
    ),
    TechnicalAuthority(
        citation="Spring City Foundry Co. v. Commissioner, 292 U.S. 182 (1934)",
        authority_type="case_law",
        title="Accrual of Income When Right to Receive Becomes Fixed",
        year=1934,
        relevance="accrual method; income accrues when right to receive is fixed",
        key_holding=(
            "The Supreme Court held that an accrual method taxpayer must include "
            "income in the year when the right to receive it becomes fixed, "
            "regardless of when cash is actually collected. This foundational case "
            "established that accrual of income depends on the right to receive, "
            "not actual receipt."
        ),
        facts_summary=(
            "Spring City Foundry sold goods on account and sought to defer income "
            "recognition until payment was received. The Court held that income "
            "accrued at the time of sale when the right to payment was established."
        ),
        taxpayer_favorable=False,
        weight="primary",
        topics=["accrual_method", "all_events_test"],
        related_citations=[
            "Treas. Reg. 1.451-1(a)",
            "Continental Tie & Lumber Co. v. United States, 286 U.S. 290 (1932)",
        ],
    ),
    TechnicalAuthority(
        citation="Continental Tie & Lumber Co. v. United States, 286 U.S. 290 (1932)",
        authority_type="case_law",
        title="Accrual of Income When All Events Have Occurred",
        year=1932,
        relevance="accrual method; early articulation of the all events test",
        key_holding=(
            "The Supreme Court held that income accrues for tax purposes when all "
            "the events have occurred that establish the taxpayer's right to "
            "receive it. This is one of the earliest Supreme Court articulations "
            "of what became known as the all events test for accrual method "
            "taxpayers."
        ),
        facts_summary=(
            "Continental Tie & Lumber Co. contracted to sell railroad ties and "
            "disputed the year in which income from the sales should be recognized. "
            "The Court looked to when the right to receive payment was established."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["accrual_method", "all_events_test"],
        related_citations=[
            "Spring City Foundry Co. v. Commissioner, 292 U.S. 182 (1934)",
            "Treas. Reg. 1.451-1(a)",
        ],
    ),
    TechnicalAuthority(
        citation="Hallmark Cards Inc. v. Commissioner, T.C. Memo 2008-141",
        authority_type="case_law",
        title="All Events Test — Right to Payment Must Be Unconditional",
        year=2008,
        relevance="all events test for accrual of revenue; conditional vs. unconditional right",
        key_holding=(
            "The Tax Court held that the all events test for income inclusion "
            "requires that the taxpayer's right to payment be unconditional and "
            "not subject to contingencies. Where the right to retain payment "
            "remained contingent on future events, the all events test was not "
            "satisfied."
        ),
        facts_summary=(
            "Hallmark Cards received advance payments from retailers but was "
            "obligated to accept returns of unsold merchandise. The court examined "
            "whether the right to retain payments was unconditional."
        ),
        taxpayer_favorable=True,
        weight="substantial",
        topics=["all_events_test", "accrual_method"],
        related_citations=[
            "United States v. General Dynamics Corp., 481 U.S. 239 (1987)",
            "Treas. Reg. 1.451-1(a)",
        ],
    ),

    # ── IRS GUIDANCE ──────────────────────────────────────────────────────
    TechnicalAuthority(
        citation="Notice 2018-35",
        authority_type="notice",
        title="Initial Guidance on TCJA §451(b) and §451(c) Provisions",
        year=2018,
        relevance=(
            "initial IRS guidance on new AFS income inclusion rule and advance "
            "payment deferral under TCJA"
        ),
        key_holding=(
            "The IRS provided transitional guidance on the new §451(b) AFS income "
            "inclusion rule and the §451(c) advance payment deferral rule enacted "
            "by TCJA. The notice described the intended scope of the new "
            "provisions and announced that forthcoming regulations would address "
            "the interaction of §451(b) with existing methods of accounting."
        ),
        taxpayer_favorable=True,
        weight="substantial",
        topics=["451b", "afs", "financial_statement_conformity"],
        related_citations=[
            "IRC §451(b)",
            "IRC §451(c)",
            "Treas. Reg. 1.451-3",
        ],
    ),
    TechnicalAuthority(
        citation="Rev. Rul. 2003-10",
        authority_type="rev_rul",
        title="Timing of Income Inclusion — Estimated and Contingent Amounts",
        year=2003,
        relevance=(
            "accrual method timing of income for estimated or contingent amounts"
        ),
        key_holding=(
            "The IRS ruled that an accrual method taxpayer must include income "
            "when the all events test is met, even if the exact amount has not yet "
            "been finally determined, provided the amount can be estimated with "
            "reasonable accuracy. Contingent amounts that cannot be reasonably "
            "estimated are not yet accruable."
        ),
        taxpayer_favorable=True,
        weight="substantial",
        topics=["accrual_method", "all_events_test"],
        related_citations=[
            "Treas. Reg. 1.451-1(a)",
            "IRC §451(a)",
        ],
    ),
    TechnicalAuthority(
        citation="CCA 202153011",
        authority_type="cca",
        title="Application of AFS Conformity Rule Under §451(b)",
        year=2021,
        relevance="AFS conformity rule; application of §451(b) to specific revenue items",
        key_holding=(
            "The Chief Counsel's office addressed the application of the AFS "
            "income inclusion rule under §451(b), concluding that revenue "
            "recognized on an applicable financial statement must be included in "
            "taxable income no later than the year of AFS recognition, even where "
            "the traditional all events test might permit later inclusion."
        ),
        taxpayer_favorable=False,
        weight="some",
        topics=["451b", "afs", "financial_statement_conformity", "accrual_method"],
        related_citations=[
            "IRC §451(b)",
            "Treas. Reg. 1.451-3",
            "Notice 2018-35",
        ],
    ),
]
