"""Technical authorities for deposit vs. income characterization and slot reservations."""

from .base import TechnicalAuthority

DEPOSIT_AUTHORITIES = [
    # -------------------------------------------------------------------------
    # STATUTES & REGULATIONS
    # -------------------------------------------------------------------------
    TechnicalAuthority(
        citation="IRC §451(a)",
        authority_type="statute",
        title="General Rule for Taxable Year of Inclusion",
        year=1986,
        relevance="Deposit vs. income characterization; timing of income inclusion",
        key_holding=(
            "An item of gross income is included in the taxable year in which it is "
            "received by the taxpayer, unless under the method of accounting used it is "
            "properly accounted for in a different period. This is the baseline rule "
            "against which deposit and advance payment treatment is measured."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["deposits", "slot_reservations", "dominion", "claim_of_right"],
        related_citations=[
            "Treas. Reg. 1.451-8(a)(1)",
            "Commissioner v. Glenshaw Glass Co., 348 U.S. 426 (1955)",
        ],
    ),
    TechnicalAuthority(
        citation="Treas. Reg. 1.451-8(a)(1)",
        authority_type="regulation",
        title="Definition of Advance Payment",
        year=2021,
        relevance="Deposit vs. advance payment characterization; defines what qualifies as an advance payment",
        key_holding=(
            "An advance payment is a payment received by an accrual-method taxpayer for "
            "goods, services, or other specified items to the extent the payment is "
            "included in revenue in an applicable financial statement for a subsequent "
            "taxable year. Refundable deposits that do not constitute payment for goods "
            "or services are excluded from the definition of advance payment."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["deposits", "slot_reservations"],
        related_citations=[
            "IRC §451(a)",
            "Rev. Rul. 72-519",
        ],
    ),

    # -------------------------------------------------------------------------
    # CASE LAW
    # -------------------------------------------------------------------------
    TechnicalAuthority(
        citation="Commissioner v. Indianapolis Power & Light Co., 493 U.S. 203 (1990)",
        authority_type="case_law",
        title="Indianapolis Power — Deposit vs. Income Framework",
        year=1990,
        relevance="Landmark deposit vs. income framework; complete dominion test",
        key_holding=(
            "Customer deposits held by a utility are not taxable income where customers "
            "retain an unqualified right to demand return of the deposit. The critical "
            "test is whether the taxpayer has 'complete dominion' over the funds. Because "
            "the utility's obligation to refund was unconditional, the deposits were not income."
        ),
        facts_summary=(
            "Indianapolis Power & Light required certain customers to make deposits as "
            "security for payment of future electric bills. Customers with satisfactory "
            "payment history could obtain refunds. The IRS argued the deposits were "
            "advance payments for electricity and thus income upon receipt. The Supreme "
            "Court disagreed, holding that the deposits were not income because the "
            "customers retained the right to repayment."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["deposits", "slot_reservations", "dominion"],
        related_citations=[
            "Commissioner v. Glenshaw Glass Co., 348 U.S. 426 (1955)",
            "North American Oil Consolidated v. Burnet, 286 U.S. 417 (1932)",
            "City Gas Co. of Florida v. Commissioner, 74 T.C. 386 (1980)",
        ],
        notes=(
            "This is the controlling authority for deposit vs. income analysis. For slot "
            "reservations: since slot reservation payments are typically (a) non-refundable, "
            "(b) transferable, and (c) provide an immediate right to the holder, they fail "
            "the Indianapolis Power deposit test and constitute income upon receipt. There "
            "is no direct authority specifically addressing 'slot reservation payments' by "
            "name; the analysis relies on applying this framework by analogy."
        ),
    ),
    TechnicalAuthority(
        citation="Oak Industries Inc. v. Commissioner, 96 T.C. 559 (1991)",
        authority_type="case_law",
        title="Oak Industries — Payment Characterization / Substance Over Form",
        year=1991,
        relevance="Payment characterization analysis; substance over form in determining deposit, advance payment, or current income",
        key_holding=(
            "The Tax Court applied a substance-over-form analysis to determine whether "
            "a payment constituted a deposit, advance payment, or current income. The "
            "economic substance of the transaction, not its label, controls the tax "
            "characterization of payments received."
        ),
        facts_summary=(
            "Oak Industries made payments in connection with a debt restructuring. The "
            "court examined the economic substance of the payments to determine their "
            "proper tax characterization, looking beyond the labels used by the parties."
        ),
        taxpayer_favorable=True,
        weight="substantial",
        topics=["deposits", "slot_reservations"],
        related_citations=[
            "Commissioner v. Indianapolis Power & Light Co., 493 U.S. 203 (1990)",
        ],
    ),
    TechnicalAuthority(
        citation="Commissioner v. Glenshaw Glass Co., 348 U.S. 426 (1955)",
        authority_type="case_law",
        title="Glenshaw Glass — Definition of Gross Income",
        year=1955,
        relevance="Foundational definition of gross income; complete dominion requirement",
        key_holding=(
            "Gross income includes all undeniable accessions to wealth, clearly realized, "
            "over which the taxpayer has complete dominion. This three-part test is the "
            "foundational standard for determining whether a receipt constitutes income "
            "and underpins the deposit vs. income analysis."
        ),
        facts_summary=(
            "Glenshaw Glass received punitive damages in an antitrust suit. The Supreme "
            "Court held the damages were gross income, articulating the broad definition "
            "of income as any accession to wealth that is clearly realized and over which "
            "the taxpayer has complete dominion."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["deposits", "dominion", "claim_of_right"],
        related_citations=[
            "Commissioner v. Indianapolis Power & Light Co., 493 U.S. 203 (1990)",
            "North American Oil Consolidated v. Burnet, 286 U.S. 417 (1932)",
        ],
    ),
    TechnicalAuthority(
        citation="North American Oil Consolidated v. Burnet, 286 U.S. 417 (1932)",
        authority_type="case_law",
        title="North American Oil — Claim of Right Doctrine",
        year=1932,
        relevance="Claim of right doctrine; unrestricted receipt as income",
        key_holding=(
            "If a taxpayer receives funds under a claim of right and without restriction "
            "as to their disposition, the funds constitute taxable income in the year of "
            "receipt, even if an obligation to repay may arise in a later year. This "
            "doctrine is adverse to taxpayers seeking deposit treatment for unrestricted funds."
        ),
        facts_summary=(
            "North American Oil received income from oil properties during litigation "
            "over ownership. The Supreme Court held the income was taxable in the year "
            "received because the company had an unrestricted claim of right to the "
            "funds, even though the dispute remained unresolved."
        ),
        taxpayer_favorable=False,
        weight="primary",
        topics=["deposits", "slot_reservations", "claim_of_right", "dominion"],
        related_citations=[
            "Commissioner v. Glenshaw Glass Co., 348 U.S. 426 (1955)",
            "Commissioner v. Indianapolis Power & Light Co., 493 U.S. 203 (1990)",
        ],
        notes=(
            "For slot reservations: non-refundable slot payments are received under a "
            "claim of right with no restriction on the recipient's use, supporting "
            "characterization as income upon receipt under this doctrine."
        ),
    ),
    TechnicalAuthority(
        citation="Westinghouse Electric Corp. v. United States, 598 F.2d 759 (3d Cir. 1979)",
        authority_type="case_law",
        title="Westinghouse Electric — Progress Payments on Long-Term Contracts",
        year=1979,
        relevance="Characterization of payments received during production; deposit vs. advance payment",
        key_holding=(
            "Progress payments received on long-term manufacturing contracts may be "
            "treated as deposits rather than income where the taxpayer retains an "
            "obligation to perform and the payments are subject to adjustment. The "
            "characterization depends on the terms and economic substance of the arrangement."
        ),
        facts_summary=(
            "Westinghouse received progress payments from the government during the "
            "manufacture of turbines under long-term contracts. The court analyzed "
            "whether the payments constituted income upon receipt or deposits subject "
            "to future adjustment based on contract performance."
        ),
        taxpayer_favorable=True,
        weight="substantial",
        topics=["deposits"],
        related_citations=[
            "Commissioner v. Indianapolis Power & Light Co., 493 U.S. 203 (1990)",
            "Oak Industries Inc. v. Commissioner, 96 T.C. 559 (1991)",
        ],
    ),
    TechnicalAuthority(
        citation="City Gas Co. of Florida v. Commissioner, 74 T.C. 386 (1980)",
        authority_type="case_law",
        title="City Gas — Utility Connection Fees as Deposits vs. Income",
        year=1980,
        relevance="Utility connection fees; deposit vs. income characterization",
        key_holding=(
            "Non-refundable connection fees charged by a utility constitute income upon "
            "receipt, not deposits, because customers have no right to demand return of "
            "the funds. The absence of a refund obligation is a key indicator that a "
            "payment is income rather than a deposit."
        ),
        facts_summary=(
            "City Gas of Florida charged customers non-refundable fees to connect to "
            "its gas distribution system. The Tax Court held these fees were income "
            "upon receipt because there was no obligation to refund and the utility "
            "had complete dominion over the funds."
        ),
        taxpayer_favorable=False,
        weight="substantial",
        topics=["deposits", "slot_reservations", "dominion"],
        related_citations=[
            "Commissioner v. Indianapolis Power & Light Co., 493 U.S. 203 (1990)",
            "Rev. Rul. 72-519",
        ],
        notes=(
            "Directly analogous to slot reservation fees: non-refundable fees for "
            "access to a service or resource are income upon receipt. Supports the "
            "conclusion that non-refundable slot reservation payments fail the deposit "
            "test under Indianapolis Power."
        ),
    ),

    # -------------------------------------------------------------------------
    # REVENUE RULINGS
    # -------------------------------------------------------------------------
    TechnicalAuthority(
        citation="Rev. Rul. 72-519",
        authority_type="rev_rul",
        title="Retainers and Deposits — Refundable vs. Non-Refundable",
        year=1972,
        relevance="Distinguishing non-refundable payments (income) from refundable deposits (not income)",
        key_holding=(
            "Non-refundable payments received as retainers or fees constitute income "
            "upon receipt. Refundable deposits, by contrast, are not income because "
            "the recipient does not have unrestricted use of the funds. The refundability "
            "of a payment is a critical factor in the deposit vs. income determination."
        ),
        taxpayer_favorable=True,
        weight="substantial",
        topics=["deposits", "slot_reservations"],
        related_citations=[
            "Commissioner v. Indianapolis Power & Light Co., 493 U.S. 203 (1990)",
            "City Gas Co. of Florida v. Commissioner, 74 T.C. 386 (1980)",
        ],
        notes=(
            "For slot reservations: since slot reservation payments are non-refundable, "
            "they fall on the income side of the Rev. Rul. 72-519 framework and are "
            "includible in gross income upon receipt."
        ),
    ),

    # -------------------------------------------------------------------------
    # CCAs / TAMs
    # -------------------------------------------------------------------------
    TechnicalAuthority(
        citation="CCA 200851039",
        authority_type="cca",
        title="Deposit vs. Advance Payment Characterization Analysis",
        year=2008,
        relevance="IRS analysis of deposit vs. advance payment characterization",
        key_holding=(
            "The IRS Chief Counsel analyzed whether payments received constituted "
            "deposits or advance payments, applying the Indianapolis Power framework. "
            "Payments where the recipient has no obligation to refund and retains "
            "complete dominion are advance payments includible in income, not deposits."
        ),
        taxpayer_favorable=False,
        weight="some",
        topics=["deposits", "slot_reservations", "dominion"],
        related_citations=[
            "Commissioner v. Indianapolis Power & Light Co., 493 U.S. 203 (1990)",
            "Rev. Rul. 72-519",
        ],
    ),
    TechnicalAuthority(
        citation="TAM 200043015",
        authority_type="tam",
        title="Non-Refundable Fees as Income Upon Receipt",
        year=2000,
        relevance="Non-refundable fee characterization; income upon receipt",
        key_holding=(
            "Non-refundable fees are includible in gross income upon receipt because "
            "the taxpayer has complete dominion over the funds and no obligation to "
            "return them. The non-refundable nature of a fee is determinative in "
            "distinguishing income from a deposit."
        ),
        taxpayer_favorable=False,
        weight="some",
        topics=["deposits", "slot_reservations", "dominion"],
        related_citations=[
            "Commissioner v. Indianapolis Power & Light Co., 493 U.S. 203 (1990)",
            "City Gas Co. of Florida v. Commissioner, 74 T.C. 386 (1980)",
            "Rev. Rul. 72-519",
        ],
        notes=(
            "Supports characterization of non-refundable slot reservation payments as "
            "income upon receipt. The TAM's reasoning aligns with the Indianapolis Power "
            "framework and City Gas holding."
        ),
    ),
]
