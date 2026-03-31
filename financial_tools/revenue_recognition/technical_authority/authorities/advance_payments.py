"""Technical authorities for advance payment income recognition."""

from .base import TechnicalAuthority

ADVANCE_PAYMENT_AUTHORITIES = [
    # ─── STATUTES ───────────────────────────────────────────────────────

    TechnicalAuthority(
        citation="IRC §451(a)",
        authority_type="statute",
        title="General Rule for Taxable Year of Inclusion",
        year=1986,
        relevance="advance_payments, accrual_method, income_inclusion",
        key_holding=(
            "Under the accrual method of accounting, an item of gross income is "
            "included in the taxable year in which all events have occurred that fix "
            "the right to receive the income and the amount can be determined with "
            "reasonable accuracy. This general rule governs the timing of income "
            "recognition for accrual-method taxpayers."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["advance_payments", "accrual_method", "income_inclusion", "451a"],
        related_citations=["IRC §451(c)", "Treas. Reg. 1.451-8"],
    ),
    TechnicalAuthority(
        citation="IRC §451(c)",
        authority_type="statute",
        title="Advance Payment Deferral Election (TCJA 2017)",
        year=2017,
        relevance="advance_payments, deferral, 451c",
        key_holding=(
            "Codified by the Tax Cuts and Jobs Act of 2017 (effective for tax years "
            "beginning after December 31, 2017), §451(c) allows accrual-method "
            "taxpayers to elect to defer the inclusion of advance payments to the "
            "extent not recognized as revenue in the taxpayer's applicable financial "
            "statement in the year of receipt. The deferred amount must be included "
            "no later than the following taxable year."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["advance_payments", "451c", "deferral", "TCJA"],
        related_citations=[
            "IRC §451(a)",
            "Treas. Reg. 1.451-8",
            "Rev. Proc. 2004-34",
        ],
    ),

    # ─── REGULATIONS ────────────────────────────────────────────────────

    TechnicalAuthority(
        citation="Treas. Reg. 1.451-8",
        authority_type="regulation",
        title="Advance Payment Final Regulations",
        year=2021,
        relevance="advance_payments, deferral, 451c, AFS",
        key_holding=(
            "Final regulations under §451(c) define an 'advance payment' as any "
            "payment received by the taxpayer in which any portion is taken into "
            "revenue in a subsequent taxable year on the taxpayer's applicable "
            "financial statement (AFS). Taxpayers may elect the full inclusion method "
            "(include entire payment in year of receipt) or the deferral method "
            "(include in the year of receipt only to the extent recognized on the "
            "AFS, with the remainder included the following year)."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["advance_payments", "451c", "deferral", "AFS", "regulation"],
        related_citations=[
            "IRC §451(c)",
            "Rev. Proc. 2004-34",
            "Former Treas. Reg. 1.451-5",
        ],
    ),
    TechnicalAuthority(
        citation="Former Treas. Reg. 1.451-5",
        authority_type="regulation",
        title="Pre-TCJA Advance Payment Rules for Goods (Superseded)",
        year=1971,
        relevance="advance_payments, deferral, goods",
        key_holding=(
            "Former regulation providing a limited deferral method for advance "
            "payments for goods. Allowed accrual-method taxpayers to defer advance "
            "payments related to future sales of goods to the year in which the "
            "goods were shipped or otherwise disposed of. This regulation has been "
            "superseded by Treas. Reg. 1.451-8 under the TCJA framework."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["advance_payments", "deferral", "goods", "superseded"],
        related_citations=["Treas. Reg. 1.451-8", "IRC §451(c)"],
        notes="Superseded by Treas. Reg. 1.451-8 for tax years beginning after 2017.",
    ),

    # ─── CASE LAW ───────────────────────────────────────────────────────

    TechnicalAuthority(
        citation="Schlude v. Commissioner, 372 U.S. 128 (1963)",
        authority_type="case_law",
        title="Schlude v. Commissioner",
        year=1963,
        relevance="advance_payments, prepaid_income, claim_of_right",
        key_holding=(
            "The Supreme Court held that a dance studio operating on the accrual "
            "method must include prepaid lesson fees in gross income in the year of "
            "receipt under the claim-of-right doctrine. The taxpayer's system of "
            "deferring income to match the period in which lessons were given was "
            "rejected as not clearly reflecting income."
        ),
        facts_summary=(
            "Dance studio received advance payments for lesson packages. Taxpayer "
            "attempted to defer recognition of income until lessons were actually "
            "provided to students."
        ),
        taxpayer_favorable=False,
        weight="primary",
        topics=["advance_payments", "claim_of_right", "prepaid_income", "deferral"],
        related_citations=[
            "American Automobile Association v. United States, 367 U.S. 687 (1961)",
            "Artnell Co. v. Commissioner, 400 F.2d 981 (7th Cir. 1968)",
        ],
    ),
    TechnicalAuthority(
        citation="American Automobile Association v. United States, 367 U.S. 687 (1961)",
        authority_type="case_law",
        title="American Automobile Association v. United States",
        year=1961,
        relevance="advance_payments, prepaid_dues, income_inclusion",
        key_holding=(
            "The Supreme Court held that prepaid membership dues received by AAA "
            "must be included in gross income in the year received, even though the "
            "services to which the dues related would be performed over a twelve-month "
            "period. The Court rejected the taxpayer's prorated deferral method as "
            "an impermissible departure from clear reflection of income."
        ),
        facts_summary=(
            "AAA received annual membership dues in advance and sought to prorate "
            "the income over the membership period on the basis that services were "
            "rendered over time."
        ),
        taxpayer_favorable=False,
        weight="primary",
        topics=["advance_payments", "prepaid_income", "membership_dues", "deferral"],
        related_citations=[
            "Schlude v. Commissioner, 372 U.S. 128 (1963)",
        ],
    ),
    TechnicalAuthority(
        citation="Artnell Co. v. Commissioner, 400 F.2d 981 (7th Cir. 1968)",
        authority_type="case_law",
        title="Artnell Co. v. Commissioner",
        year=1968,
        relevance="advance_payments, deferral, fixed_performance",
        key_holding=(
            "The Seventh Circuit held that advance ticket sales for specific future "
            "baseball games could be deferred to the year in which the games were "
            "played, distinguishing Schlude and AAA. Where the obligation to perform "
            "is fixed and definite as to both time and place, deferral of advance "
            "payments is permissible because it clearly reflects income."
        ),
        facts_summary=(
            "The Chicago White Sox received advance payments for tickets to games "
            "scheduled in future tax years. The obligation to play the games was "
            "fixed by the league schedule."
        ),
        taxpayer_favorable=True,
        weight="substantial",
        topics=["advance_payments", "deferral", "fixed_performance", "ticket_sales"],
        related_citations=[
            "Schlude v. Commissioner, 372 U.S. 128 (1963)",
            "American Automobile Association v. United States, 367 U.S. 687 (1961)",
            "Tampa Bay Devil Rays v. Commissioner, T.C. Memo 2002-248",
        ],
    ),
    TechnicalAuthority(
        citation="Tampa Bay Devil Rays v. Commissioner, T.C. Memo 2002-248",
        authority_type="case_law",
        title="Tampa Bay Devil Rays v. Commissioner",
        year=2002,
        relevance="advance_payments, deposits, ticket_sales",
        key_holding=(
            "The Tax Court addressed the distinction between advance payments and "
            "deposits in the context of season ticket purchases. Amounts received "
            "as deposits that are subject to a genuine restriction on use and a "
            "repayment obligation may be excluded from income, whereas unrestricted "
            "advance payments must be included under applicable authorities."
        ),
        facts_summary=(
            "The Tampa Bay Devil Rays received payments from season ticket holders "
            "prior to the start of the baseball season, and the IRS challenged the "
            "characterization of certain amounts as refundable deposits."
        ),
        taxpayer_favorable=True,
        weight="substantial",
        topics=["advance_payments", "deposits", "ticket_sales", "deferral"],
        related_citations=[
            "Artnell Co. v. Commissioner, 400 F.2d 981 (7th Cir. 1968)",
            "Commissioner v. Indianapolis Power & Light Co., 493 U.S. 203 (1990)",
        ],
    ),
    TechnicalAuthority(
        citation="Westpac Pacific Food v. Commissioner, 451 F.3d 970 (9th Cir. 2006)",
        authority_type="case_law",
        title="Westpac Pacific Food v. Commissioner",
        year=2006,
        relevance="advance_payments, gift_cards, deferral",
        key_holding=(
            "The Ninth Circuit held that unredeemed gift card proceeds constitute "
            "advance payments eligible for deferral under Rev. Proc. 2004-34. The "
            "court recognized that gift card sales represent prepayments for future "
            "goods or services and are within the scope of the IRS administrative "
            "deferral method."
        ),
        facts_summary=(
            "A Burger King franchisee received proceeds from gift card sales and "
            "sought to defer income recognition until the cards were redeemed by "
            "customers."
        ),
        taxpayer_favorable=True,
        weight="substantial",
        topics=["advance_payments", "gift_cards", "deferral", "451c"],
        related_citations=[
            "Rev. Proc. 2004-34",
            "IRC §451(c)",
            "Treas. Reg. 1.451-8",
        ],
    ),

    # ─── REVENUE PROCEDURES ────────────────────────────────────────────

    TechnicalAuthority(
        citation="Rev. Proc. 2004-34",
        authority_type="rev_proc",
        title="IRS Administrative Deferral Method for Advance Payments",
        year=2004,
        relevance="advance_payments, deferral, 451c, AFS",
        key_holding=(
            "Establishes the one-year deferral method for advance payments: a "
            "taxpayer includes the advance payment in gross income in the year of "
            "receipt to the extent recognized as revenue on its applicable financial "
            "statement, and defers the remaining amount to the next succeeding "
            "taxable year. This foundational administrative guidance was subsequently "
            "codified in IRC §451(c) by the TCJA."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["advance_payments", "deferral", "451c", "AFS", "rev_proc"],
        related_citations=[
            "IRC §451(c)",
            "Treas. Reg. 1.451-8",
            "Rev. Proc. 2004-34 §4",
        ],
    ),
    TechnicalAuthority(
        citation="Rev. Proc. 2004-34 §4",
        authority_type="rev_proc",
        title="Qualifying Advance Payments Definition (Rev. Proc. 2004-34 §4)",
        year=2004,
        relevance="advance_payments, deferral, qualifying_payments",
        key_holding=(
            "Section 4 of Rev. Proc. 2004-34 defines qualifying advance payments "
            "to include payments for services, the sale of goods, the use of "
            "intellectual property (including licensing), the occupancy or use of "
            "property, and certain other specified categories. Payments that do not "
            "fall within these categories are not eligible for the administrative "
            "deferral method."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["advance_payments", "deferral", "qualifying_payments", "451c"],
        related_citations=[
            "Rev. Proc. 2004-34",
            "IRC §451(c)",
            "Treas. Reg. 1.451-8",
        ],
    ),

    # ─── CCAs / TAMs / PLRs ────────────────────────────────────────────

    TechnicalAuthority(
        citation="CCA 201520017",
        authority_type="cca",
        title="Advance Payments for Services Under Rev. Proc. 2004-34",
        year=2015,
        relevance="advance_payments, services, deferral",
        key_holding=(
            "The Chief Counsel advised that advance payments received for services "
            "qualify for deferral under Rev. Proc. 2004-34 where the taxpayer "
            "properly identifies the payments as advance payments and applies the "
            "one-year deferral method consistently. The CCA reinforces the "
            "applicability of the deferral method to service-based advance payments."
        ),
        taxpayer_favorable=True,
        weight="some",
        topics=["advance_payments", "deferral", "services", "451c"],
        related_citations=["Rev. Proc. 2004-34", "IRC §451(c)"],
    ),
    TechnicalAuthority(
        citation="TAM 200437030",
        authority_type="tam",
        title="Prepaid Subscription Revenue as Advance Payments",
        year=2004,
        relevance="advance_payments, subscriptions, deferral",
        key_holding=(
            "The IRS National Office concluded that prepaid subscription revenue "
            "constitutes advance payments eligible for deferral treatment. The TAM "
            "analyzed the subscription payments under the advance payment framework "
            "and confirmed that amounts received for future delivery of publications "
            "meet the definition of advance payments for services or goods."
        ),
        taxpayer_favorable=True,
        weight="some",
        topics=["advance_payments", "deferral", "subscriptions", "prepaid_income"],
        related_citations=["Rev. Proc. 2004-34", "IRC §451(c)"],
    ),
    TechnicalAuthority(
        citation="PLR 200725017",
        authority_type="plr",
        title="Software Maintenance Contracts Qualify for Advance Payment Deferral",
        year=2007,
        relevance="advance_payments, software, deferral, maintenance_contracts",
        key_holding=(
            "The IRS ruled that advance payments received for software maintenance "
            "contracts qualify as advance payments eligible for the one-year deferral "
            "method under Rev. Proc. 2004-34. The ruling confirms that payments for "
            "future software support and updates fall within the qualifying advance "
            "payment categories."
        ),
        taxpayer_favorable=True,
        weight="some",
        topics=["advance_payments", "deferral", "software", "maintenance_contracts", "451c"],
        related_citations=[
            "Rev. Proc. 2004-34",
            "IRC §451(c)",
            "Treas. Reg. 1.451-8",
        ],
        notes="PLRs may not be cited as precedent but indicate IRS position.",
    ),
]
