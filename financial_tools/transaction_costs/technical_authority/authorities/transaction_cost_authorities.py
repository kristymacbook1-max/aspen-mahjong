"""Technical authorities for transaction cost capitalization.

Covers §263(a), INDOPCO, Reg. 1.263(a)-5 (facilitating costs), Rev. Proc.
2011-29 (success-based fee safe harbor), debt issuance costs, and
abandoned transaction losses.
"""

from .base import TechnicalAuthority

TRANSACTION_COST_AUTHORITIES = [
    TechnicalAuthority(
        citation="IRC §263(a)",
        authority_type="statute",
        title="Capital Expenditures — General Rule",
        year=1986,
        relevance="No deduction for capital expenditures — amounts paid for permanent improvements or acquisitions",
        key_holding="No deduction shall be allowed for any amount paid out for new buildings or for permanent improvements or betterments made to increase the value of any property or estate, or for any amount expended in restoring property or in making good the exhaustion thereof.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["263(a)", "capitalization", "transaction costs"],
    ),
    TechnicalAuthority(
        citation="INDOPCO, Inc. v. Commissioner, 503 U.S. 79 (1992)",
        authority_type="case_law",
        title="INDOPCO — Significant Future Benefits = Capitalize",
        year=1992,
        relevance="Investment banking and legal fees for friendly takeover must be capitalized",
        key_holding="A taxpayer's expenditure that produces significant benefits extending beyond the current taxable year is not deductible as an ordinary and necessary business expense but must be capitalized. Investment banking fees, legal fees, and other professional fees incurred in connection with a friendly acquisition must be capitalized.",
        facts_summary="National Starch (INDOPCO) incurred $2.2M in investment banking fees in connection with a friendly takeover by Unilever. Supreme Court held all costs must be capitalized because they produced significant long-term benefits.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["INDOPCO", "capitalization", "future benefits", "transaction costs"],
    ),
    TechnicalAuthority(
        citation="Treas. Reg. §1.263(a)-5(a)",
        authority_type="regulation",
        title="Amounts Paid to Facilitate Transactions — General Rule",
        year=2004,
        relevance="Costs that facilitate certain transactions must be capitalized",
        key_holding="A taxpayer must capitalize an amount paid to facilitate a transaction described in §1.263(a)-5(e)(1) (covered transactions). Covered transactions include: acquisitions of a trade or business, changes in capital structure, and certain reorganizations.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["facilitative costs", "263(a)-5", "transaction costs", "capitalization"],
    ),
    TechnicalAuthority(
        citation="Treas. Reg. §1.263(a)-5(e)(1)",
        authority_type="regulation",
        title="Covered Transactions List",
        year=2004,
        relevance="Types of transactions to which facilitative cost rules apply",
        key_holding="Covered transactions include: (1) taxable or tax-free acquisitions of assets of a trade or business, (2) taxable acquisitions of stock/ownership interests, (3) tax-free reorganizations (§368), (4) certain formations/liquidations, (5) stock issuances, (6) borrowings, and (7) writing of options.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["covered transactions", "263(a)-5", "acquisitions", "reorganizations"],
    ),
    TechnicalAuthority(
        citation="Treas. Reg. §1.263(a)-5(e)(2)",
        authority_type="regulation",
        title="Inherently Facilitative Costs",
        year=2004,
        relevance="Certain costs are inherently facilitative regardless of when incurred",
        key_holding="The following costs are inherently facilitative of a covered transaction and must be capitalized regardless of when they are incurred: (1) securing an appraisal/fairness opinion, (2) structuring the transaction, (3) preparing/reviewing transaction documents, (4) obtaining regulatory approval, (5) obtaining shareholder approval, (6) conveying property, and (7) negotiating the transaction.",
        facts_summary="Inherently facilitative costs must be capitalized even if incurred before the bright-line date. This is the most important list for transaction cost analysis.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["inherently facilitative", "263(a)-5(e)(2)", "capitalization"],
    ),
    TechnicalAuthority(
        citation="Treas. Reg. §1.263(a)-5(e)(1) — Bright-Line Date",
        authority_type="regulation",
        title="Bright-Line Date for Non-Inherently Facilitative Costs",
        year=2004,
        relevance="Costs are facilitative only if incurred on or after the bright-line date (unless inherently facilitative)",
        key_holding="An amount paid in the process of investigating or pursuing a covered transaction facilitates the transaction only if the amount is paid on or after the earlier of: (1) the date on which a letter of intent or similar agreement is signed, or (2) the date on which the board of directors authorizes the transaction.",
        facts_summary="Non-inherently facilitative costs incurred BEFORE the bright-line date are deductible. After the bright-line date, they are facilitative and must be capitalized.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["bright-line date", "263(a)-5", "investigation costs", "pre-LOI"],
    ),
    TechnicalAuthority(
        citation="Treas. Reg. §1.263(a)-5(g)",
        authority_type="regulation",
        title="Employee Compensation — Not Required to Capitalize",
        year=2004,
        relevance="Employee compensation (including bonuses) need not be capitalized as transaction costs",
        key_holding="Amounts paid as employee compensation (including bonuses and commission) are not required to be capitalized as amounts that facilitate a covered transaction, even if the employees are directly involved in the transaction.",
        facts_summary="Important exception: internal employee time spent on transactions is deductible. Only third-party costs must be analyzed for capitalization.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["employee compensation", "263(a)-5(g)", "deductible", "transaction costs"],
    ),

    # --- Success-Based Fees ---
    TechnicalAuthority(
        citation="Rev. Proc. 2011-29, 2011-18 I.R.B. 746",
        authority_type="rev_proc",
        title="Success-Based Fee Safe Harbor — 70/30 Allocation",
        year=2011,
        relevance="Safe harbor: 70% of success-based fees are facilitative (capitalize), 30% deductible",
        key_holding="A taxpayer that pays a success-based fee in connection with a covered transaction may elect to treat 70% of the fee as an amount that facilitates the transaction (capitalize) and 30% as an amount that does not facilitate (deduct), without detailed allocation.",
        facts_summary="Elective safe harbor. Alternative: taxpayer can establish actual allocation with contemporaneous documentation showing time/effort split between facilitative and non-facilitative activities.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["success-based fee", "Rev. Proc. 2011-29", "70/30", "safe harbor"],
    ),

    # --- Debt Issuance Costs ---
    TechnicalAuthority(
        citation="Treas. Reg. §1.446-5",
        authority_type="regulation",
        title="Debt Issuance Costs — Amortization",
        year=1994,
        relevance="Debt issuance costs amortized over life of debt using constant yield method",
        key_holding="Debt issuance costs are capitalized and amortized over the term of the debt using the constant yield (effective interest) method. This applies to costs of issuing bonds, obtaining loans, and similar financing transactions.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["debt issuance costs", "446-5", "amortization", "constant yield"],
    ),

    # --- Abandoned Transactions ---
    TechnicalAuthority(
        citation="Rev. Rul. 73-580, 1973-2 C.B. 86",
        authority_type="rev_rul",
        title="Abandoned Transaction — Loss Deduction",
        year=1973,
        relevance="Capitalized transaction costs deductible as loss when transaction is abandoned",
        key_holding="Costs that were properly capitalized as transaction costs become deductible as an ordinary loss under §165 when the transaction is permanently abandoned. The taxpayer must establish that the transaction has been permanently abandoned and will not be revived.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["abandoned transaction", "loss deduction", "165", "Rev. Rul. 73-580"],
    ),

    # --- Case Law ---
    TechnicalAuthority(
        citation="A.E. Staley Mfg. Co. v. Commissioner, 119 F.3d 482 (7th Cir. 1997)",
        authority_type="case_law",
        title="A.E. Staley — Origin of the Claim Test for Transaction Costs",
        year=1997,
        relevance="Origin-of-the-claim test: transaction costs must be analyzed based on the nature of the transaction, not the taxpayer's purpose",
        key_holding="The 'origin of the claim' test governs whether expenditures are capital or ordinary. Costs whose origin lies in the transaction itself (defense of a hostile takeover, restructuring) must be capitalized. The taxpayer's subjective purpose is not controlling.",
        taxpayer_favorable=False,
        weight="substantial",
        topics=["origin of claim", "transaction costs", "hostile takeover"],
    ),
    TechnicalAuthority(
        citation="Wells Fargo & Co. v. Commissioner, 224 F.3d 874 (8th Cir. 2000)",
        authority_type="case_law",
        title="Wells Fargo — Investigatory Costs Deductible",
        year=2000,
        relevance="Pre-decision investigatory costs of potential acquisition are deductible",
        key_holding="Costs incurred in investigating whether to acquire a target company are deductible as ordinary business expenses if incurred before the taxpayer makes a final decision to acquire. Post-decision costs that facilitate the acquisition must be capitalized.",
        facts_summary="Important pre-Reg. 1.263(a)-5 case. The bright-line date concept in the 2004 regulations codified similar principles.",
        taxpayer_favorable=True,
        weight="substantial",
        topics=["investigatory costs", "pre-decision", "deductible", "acquisition"],
    ),

    # --- Method Change ---
    TechnicalAuthority(
        citation="Rev. Proc. 2024-23 (CAM §10.11)",
        authority_type="rev_proc",
        title="Automatic Consent — Transaction Cost Capitalization",
        year=2024,
        relevance="Automatic method change for transaction cost capitalization",
        key_holding="A taxpayer may obtain automatic consent to change its method of accounting for transaction costs to comply with Reg. 1.263(a)-5. Filed on Form 3115 with the timely return.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["method change", "Form 3115", "automatic consent", "transaction costs"],
    ),
]
