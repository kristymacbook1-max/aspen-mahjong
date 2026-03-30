"""Technical authorities for IRC §460 long-term contract accounting."""

from .base import TechnicalAuthority

LONG_TERM_CONTRACT_AUTHORITIES = [
    # -------------------------------------------------------------------------
    # STATUTES
    # -------------------------------------------------------------------------
    TechnicalAuthority(
        citation="IRC §460(a)",
        authority_type="statute",
        title="Long-Term Contracts — General Rule Requiring Percentage-of-Completion Method",
        year=1986,
        relevance="Percentage-of-completion method requirement for long-term contracts",
        key_holding=(
            "In the case of any long-term contract, the taxable income from such "
            "contract shall be determined under the percentage-of-completion method. "
            "This provision establishes PCM as the default required method for long-term "
            "contracts, overriding the taxpayer's general method of accounting."
        ),
        taxpayer_favorable=False,
        weight="primary",
        topics=["long_term_contracts", "460", "pcm"],
        related_citations=[
            "IRC §460(b)",
            "IRC §460(e)",
            "IRC §460(f)",
            "Treas. Reg. 1.460-4",
        ],
    ),
    TechnicalAuthority(
        citation="IRC §460(b)",
        authority_type="statute",
        title="Long-Term Contracts — Percentage-of-Completion Method Requirements",
        year=1986,
        relevance="PCM computation: costs incurred divided by estimated total costs",
        key_holding=(
            "The percentage of completion is determined by comparing costs allocated to "
            "the contract and incurred before the close of the taxable year with the "
            "estimated total contract costs. Income is recognized in each taxable year "
            "in proportion to the cumulative percentage of completion as of the end of "
            "that year."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["long_term_contracts", "460", "pcm"],
        related_citations=[
            "IRC §460(a)",
            "IRC §460(b)(5)",
            "Treas. Reg. 1.460-4",
            "Treas. Reg. 1.460-5",
        ],
    ),
    TechnicalAuthority(
        citation="IRC §460(b)(5)",
        authority_type="statute",
        title="Long-Term Contracts — Look-Back Interest Requirement",
        year=1986,
        relevance="Look-back method for recalculating interest on PCM contracts",
        key_holding=(
            "Upon completion of a long-term contract accounted for under the PCM, the "
            "taxpayer must apply the look-back method to determine whether the amount of "
            "tax paid in prior years was correct based on actual (rather than estimated) "
            "contract price and costs. Interest is charged or credited to account for "
            "any underpayment or overpayment."
        ),
        taxpayer_favorable=False,
        weight="primary",
        topics=["long_term_contracts", "460", "pcm", "look_back"],
        related_citations=[
            "IRC §460(b)",
            "Treas. Reg. 1.460-6",
        ],
    ),
    TechnicalAuthority(
        citation="IRC §460(e)(1)(A)",
        authority_type="statute",
        title="Construction Contract Exception for Small Contractors",
        year=1986,
        relevance="Exception from PCM for qualifying small construction contracts",
        key_holding=(
            "A construction contract is exempt from the PCM requirement if the contract "
            "is expected to be completed within two years and is performed by a taxpayer "
            "whose average annual gross receipts for the three preceding taxable years "
            "do not exceed the applicable threshold. Qualifying taxpayers may use the "
            "completed contract method or other exempt method."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["long_term_contracts", "460", "pcm", "ccm"],
        related_citations=[
            "IRC §460(a)",
            "IRC §460(e)(1)(B)",
            "Treas. Reg. 1.460-4",
        ],
    ),
    TechnicalAuthority(
        citation="IRC §460(e)(1)(B)",
        authority_type="statute",
        title="Home Construction Contract Exception",
        year=1986,
        relevance="Exception from PCM for home construction contracts",
        key_holding=(
            "A home construction contract is exempt from the PCM requirement. A home "
            "construction contract is any construction contract where 80 percent or more "
            "of the estimated total contract costs are reasonably expected to be "
            "attributable to the building, construction, reconstruction, or rehabilitation "
            "of dwelling units in buildings containing four or fewer dwelling units."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["long_term_contracts", "460", "ccm"],
        related_citations=[
            "IRC §460(a)",
            "IRC §460(e)(1)(A)",
            "Treas. Reg. 1.460-4",
        ],
    ),
    TechnicalAuthority(
        citation="IRC §460(f)",
        authority_type="statute",
        title="Long-Term Contract Defined",
        year=1986,
        relevance="Definition of long-term contract for IRC §460 purposes",
        key_holding=(
            "A long-term contract is any contract for the manufacture, building, "
            "installation, or construction of property that is not completed within the "
            "taxable year in which it is entered into. The definition encompasses a broad "
            "range of production-type contracts spanning more than one taxable year."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["long_term_contracts", "460"],
        related_citations=[
            "IRC §460(a)",
            "Treas. Reg. 1.460-1",
            "Rev. Rul. 69-314",
        ],
    ),
    # -------------------------------------------------------------------------
    # REGULATIONS
    # -------------------------------------------------------------------------
    TechnicalAuthority(
        citation="Treas. Reg. 1.460-1",
        authority_type="regulation",
        title="Long-Term Contracts — General Rules",
        year=1995,
        relevance="General rules and definitions for long-term contract accounting",
        key_holding=(
            "Provides comprehensive rules for determining whether a contract is a "
            "long-term contract, including the definition of manufacturing, building, "
            "installation, and construction contracts. Also addresses contract "
            "commencement and completion dates, and the allocation of contracts between "
            "long-term and non-long-term components."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["long_term_contracts", "460"],
        related_citations=[
            "IRC §460(f)",
            "Treas. Reg. 1.460-4",
            "Treas. Reg. 1.460-5",
        ],
    ),
    TechnicalAuthority(
        citation="Treas. Reg. 1.460-4",
        authority_type="regulation",
        title="Methods of Accounting for Long-Term Contracts",
        year=1995,
        relevance="Detailed PCM and CCM accounting rules for long-term contracts",
        key_holding=(
            "Prescribes the percentage-of-completion method and the completed contract "
            "method rules in detail, including the 10-percent method under PCM. Addresses "
            "the computation of cumulative income, the treatment of contract price "
            "adjustments, and the interaction between PCM and the alternative minimum tax."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["long_term_contracts", "460", "pcm", "ccm"],
        related_citations=[
            "IRC §460(a)",
            "IRC §460(b)",
            "IRC §460(e)",
            "Treas. Reg. 1.460-5",
        ],
    ),
    TechnicalAuthority(
        citation="Treas. Reg. 1.460-5",
        authority_type="regulation",
        title="Cost Allocation Rules for Long-Term Contracts",
        year=1995,
        relevance="Cost allocation to long-term contracts under PCM",
        key_holding=(
            "Specifies which costs must be allocated to long-term contracts for purposes "
            "of computing the completion percentage, including direct material and labor "
            "costs and certain indirect costs. Provides rules for simplified cost-to-cost "
            "allocation and distinguishes between allocable contract costs and period costs."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["long_term_contracts", "460", "pcm"],
        related_citations=[
            "IRC §460(b)",
            "Treas. Reg. 1.460-4",
        ],
    ),
    TechnicalAuthority(
        citation="Treas. Reg. 1.460-6",
        authority_type="regulation",
        title="Look-Back Method",
        year=1995,
        relevance="Application of the look-back method upon contract completion",
        key_holding=(
            "Provides detailed rules for applying the look-back method required by "
            "IRC §460(b)(5), including computation of hypothetical underpayments and "
            "overpayments of tax, the applicable interest rate, and the simplified "
            "marginal impact method as an alternative to the full look-back calculation."
        ),
        taxpayer_favorable=True,
        weight="primary",
        topics=["long_term_contracts", "460", "look_back", "pcm"],
        related_citations=[
            "IRC §460(b)(5)",
            "Treas. Reg. 1.460-4",
        ],
    ),
    # -------------------------------------------------------------------------
    # CASE LAW
    # -------------------------------------------------------------------------
    TechnicalAuthority(
        citation="Sierracin Corp. v. Commissioner, 90 T.C. 457 (1988)",
        authority_type="case_law",
        title="Definition and Scope of Long-Term Manufacturing Contracts",
        year=1988,
        relevance="Scope of long-term manufacturing contract definition",
        key_holding=(
            "The Tax Court addressed the definition of a long-term manufacturing "
            "contract and the circumstances under which a contract qualifies for "
            "long-term contract accounting. The court examined the nature of the "
            "manufacturing activity and the contractual terms to determine eligibility."
        ),
        facts_summary=(
            "Sierracin Corp. manufactured aircraft transparencies under multi-year "
            "government contracts. The IRS challenged the taxpayer's use of long-term "
            "contract accounting methods, arguing certain contracts did not qualify."
        ),
        taxpayer_favorable=True,
        weight="substantial",
        topics=["long_term_contracts", "460", "pcm"],
        related_citations=[
            "IRC §460(f)",
            "Treas. Reg. 1.460-1",
        ],
    ),
    TechnicalAuthority(
        citation="Braddock v. United States, 434 F.2d 631 (9th Cir. 1970)",
        authority_type="case_law",
        title="Completed Contract Method — When a Contract Is Complete",
        year=1970,
        relevance="Determination of contract completion under the completed contract method",
        key_holding=(
            "The Ninth Circuit held that a contract is not complete for purposes of the "
            "completed contract method until all obligations under the contract have been "
            "substantially performed. Disputes or minor punch-list items do not "
            "necessarily prevent a finding of completion."
        ),
        facts_summary=(
            "The taxpayer used the completed contract method for a construction project "
            "and deferred income recognition. The IRS argued the contract was complete "
            "in an earlier year, resulting in earlier income recognition."
        ),
        taxpayer_favorable=True,
        weight="substantial",
        topics=["long_term_contracts", "460", "ccm"],
        related_citations=[
            "IRC §460(e)",
            "Treas. Reg. 1.460-4",
        ],
    ),
    TechnicalAuthority(
        citation="Thompson-King-Tate Inc. v. United States, 296 F.2d 290 (6th Cir. 1961)",
        authority_type="case_law",
        title="Long-Term Contract Accounting Methods",
        year=1961,
        relevance="Permissible accounting methods for long-term contracts",
        key_holding=(
            "The Sixth Circuit upheld the taxpayer's use of a long-term contract "
            "accounting method, finding that the method clearly reflected income. The "
            "court recognized the importance of matching income recognition with the "
            "performance of work over the contract period."
        ),
        facts_summary=(
            "Thompson-King-Tate, a construction company, used a long-term contract "
            "accounting method to report income from multi-year construction projects. "
            "The IRS challenged the method, asserting it did not clearly reflect income."
        ),
        taxpayer_favorable=True,
        weight="substantial",
        topics=["long_term_contracts", "460", "pcm", "ccm"],
        related_citations=[
            "IRC §460(a)",
            "Treas. Reg. 1.460-4",
        ],
    ),
    # -------------------------------------------------------------------------
    # REVENUE RULINGS
    # -------------------------------------------------------------------------
    TechnicalAuthority(
        citation="Rev. Rul. 69-314",
        authority_type="rev_rul",
        title="Definition of Long-Term Contract for Tax Purposes",
        year=1969,
        relevance="IRS guidance on the definition of a long-term contract",
        key_holding=(
            "A long-term contract for tax accounting purposes is a building, "
            "installation, construction, or manufacturing contract that is not completed "
            "within the taxable year in which it is entered into. The ruling provides "
            "guidance on distinguishing long-term contracts from other types of agreements."
        ),
        taxpayer_favorable=True,
        weight="substantial",
        topics=["long_term_contracts", "460"],
        related_citations=[
            "IRC §460(f)",
            "Treas. Reg. 1.460-1",
        ],
    ),
]
