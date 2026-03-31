"""Technical authorities for NOL and loss limitation rules.

Covers §172 NOL deduction (80% limitation, unlimited carryforward), §382/§383
NOL limitation post-ownership change, §469 passive activity losses, §465
at-risk limitations, and §461(l) excess business loss limitation.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from revenue_recognition.technical_authority.authorities.base import TechnicalAuthority, AuthorityLookup

NOL_LOSS_LIMITATION_AUTHORITIES = [
    # --- §172 NOL ---
    TechnicalAuthority(
        citation="IRC §172(a)",
        authority_type="statute",
        title="Net Operating Loss Deduction — General Rule",
        year=2017,
        relevance="NOL deduction allowed as a carryforward; post-TCJA no carryback (with exceptions)",
        key_holding="A net operating loss deduction is allowed equal to the aggregate of NOL carryovers to the taxable year. Post-TCJA, NOLs arising in tax years beginning after 12/31/2017 can only be carried forward (no carryback), except for certain farming losses and insurance company NOLs.",
        facts_summary="Pre-TCJA NOLs (arising before 1/1/2018) retain their 2-year carryback / 20-year carryforward rules. CARES Act temporarily restored 5-year carryback for NOLs arising in 2018-2020.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["NOL", "172", "carryforward", "carryback", "TCJA"],
    ),
    TechnicalAuthority(
        citation="IRC §172(a)(2)",
        authority_type="statute",
        title="NOL 80% Limitation",
        year=2017,
        relevance="Post-TCJA NOLs limited to 80% of taxable income",
        key_holding="NOLs arising in tax years beginning after 12/31/2017 are limited to 80% of taxable income (computed without regard to the NOL deduction). Pre-TCJA NOLs are not subject to this limitation and can offset 100% of taxable income.",
        facts_summary="The 80% limitation was suspended for 2018-2020 by the CARES Act. Starting 2021, the 80% limitation applies to post-2017 NOLs. Ordering: pre-2018 NOLs (100% offset) are used first, then post-2017 NOLs (80% limit).",
        taxpayer_favorable=False,
        weight="primary",
        topics=["NOL", "80%", "limitation", "TCJA", "CARES Act"],
    ),

    # --- §382 NOL Limitation ---
    TechnicalAuthority(
        citation="IRC §382(a)",
        authority_type="statute",
        title="§382 Limitation on NOL Carryforwards After Ownership Change",
        year=1986,
        relevance="Annual limitation on use of pre-change NOLs after an ownership change",
        key_holding="If an ownership change occurs with respect to a loss corporation, the amount of the taxable income of the new loss corporation for any post-change year which may be offset by pre-change losses shall not exceed the §382 limitation for such year.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["382", "NOL", "ownership change", "limitation"],
    ),
    TechnicalAuthority(
        citation="IRC §382(b)",
        authority_type="statute",
        title="§382 Limitation — Calculation",
        year=1986,
        relevance="Annual §382 limitation = FMV of loss corp × long-term tax-exempt rate",
        key_holding="The §382 limitation for any post-change year is the fair market value of the stock of the old loss corporation immediately before the ownership change multiplied by the long-term tax-exempt rate. Unused §382 limitation carries forward to subsequent years.",
        facts_summary="Long-term tax-exempt rate is published monthly by IRS (e.g., ~5% range in 2024-2025). If loss corp has net unrealized built-in gains (NUBIG), recognized built-in gains in the recognition period (5 years) increase the §382 limitation.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["382", "limitation", "FMV", "long-term tax-exempt rate", "NUBIG"],
    ),
    TechnicalAuthority(
        citation="IRC §382(g)",
        authority_type="statute",
        title="§382 Ownership Change — Definition",
        year=1986,
        relevance="Ownership change occurs when 5% shareholders increase ownership by >50 points over 3-year testing period",
        key_holding="An ownership change occurs if the percentage of stock owned by one or more 5-percent shareholders has increased by more than 50 percentage points over the lowest percentage owned by such shareholders at any time during the testing period (generally 3 years). Includes direct and indirect ownership changes.",
        facts_summary="5-percent shareholders include any person holding 5% or more of the loss corporation's stock. Public shareholders are generally aggregated into a single 5% shareholder group. Testing period: the shorter of 3 years or the period since the last ownership change.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["382", "ownership change", "5-percent shareholder", "testing period", "50 percentage points"],
    ),
    TechnicalAuthority(
        citation="IRC §382(h)",
        authority_type="statute",
        title="§382 Built-In Gains and Losses",
        year=1986,
        relevance="NUBIG increases §382 limit; NUBIL treated as pre-change loss subject to limitation",
        key_holding="Net unrealized built-in gain (NUBIG): recognized built-in gains during the 5-year recognition period increase the §382 limitation. Net unrealized built-in loss (NUBIL): recognized built-in losses during the recognition period are treated as pre-change losses subject to the §382 limitation. Threshold: NUBIG/NUBIL must exceed the lesser of 15% of FMV of assets or $10M.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["382", "NUBIG", "NUBIL", "built-in gain", "built-in loss", "recognition period"],
    ),

    # --- §383 ---
    TechnicalAuthority(
        citation="IRC §383",
        authority_type="statute",
        title="§383 — Limitation on Certain Credits and Capital Losses",
        year=1986,
        relevance="§382-type limitation applies to pre-change credits and capital losses",
        key_holding="If an ownership change occurs, the amount of pre-change capital losses and excess credits (general business credits, minimum tax credits, foreign tax credits) that may be used in any post-change year is limited in a manner similar to §382. The §382 limitation absorbs income first, then remaining limitation capacity is available for credits.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["383", "credits", "capital losses", "ownership change", "382"],
    ),

    # --- §469 Passive Activity Losses ---
    TechnicalAuthority(
        citation="IRC §469(a)",
        authority_type="statute",
        title="Passive Activity Loss Limitation — General Rule",
        year=1986,
        relevance="Passive activity losses can only offset passive activity income",
        key_holding="The passive activity loss for any taxable year shall not be allowed. The disallowed passive activity loss is carried forward and treated as a deduction allocable to passive activities in the next taxable year. Upon a fully taxable disposition of the entire interest, all suspended passive losses are allowed.",
        facts_summary="Applies to individuals, estates, trusts, closely held C corporations, and personal service corporations. Does NOT apply to widely held C corporations (§469(a)(2)).",
        taxpayer_favorable=False,
        weight="primary",
        topics=["469", "passive activity", "loss limitation", "suspended losses"],
    ),
    TechnicalAuthority(
        citation="IRC §469(c)",
        authority_type="statute",
        title="Passive Activity Defined",
        year=1986,
        relevance="Activity in which taxpayer does not materially participate",
        key_holding="A passive activity is any activity which involves the conduct of a trade or business in which the taxpayer does not materially participate. Rental activity is generally treated as passive regardless of participation, subject to the real estate professional exception.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["469", "passive activity", "material participation", "rental activity"],
    ),
    TechnicalAuthority(
        citation="IRC §469(h)",
        authority_type="statute",
        title="Material Participation — Tests",
        year=1986,
        relevance="Seven tests under Temp. Reg. §1.469-5T for determining material participation",
        key_holding="A taxpayer materially participates if involved in operations on a regular, continuous, and substantial basis. Temp. Reg. §1.469-5T provides 7 tests: (1) 500+ hours, (2) substantially all participation, (3) 100+ hours and no one participates more, (4) significant participation activities totaling 500+ hours, (5) material participation in 5 of 10 prior years, (6) personal service activity with participation in 3 prior years, (7) facts and circumstances (100+ hour minimum).",
        taxpayer_favorable=True,
        weight="primary",
        topics=["469", "material participation", "500 hours", "seven tests"],
    ),
    TechnicalAuthority(
        citation="IRC §469(c)(7)",
        authority_type="statute",
        title="Real Estate Professional Exception",
        year=1993,
        relevance="Rental real estate not automatically passive for qualifying real estate professionals",
        key_holding="A qualifying taxpayer's rental real estate activities are not automatically treated as passive. Requirements: (1) more than 50% of personal services performed in real property trades or businesses, and (2) more than 750 hours of services in real property trades or businesses in which taxpayer materially participates.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["469", "real estate professional", "rental", "750 hours"],
    ),

    # --- §465 At-Risk ---
    TechnicalAuthority(
        citation="IRC §465(a)",
        authority_type="statute",
        title="At-Risk Limitation",
        year=1976,
        relevance="Deductions limited to amount taxpayer has at risk in the activity",
        key_holding="Deductions from an activity are allowed only to the extent of the aggregate amount the taxpayer is at risk for such activity at the close of the taxable year. At-risk amount includes: (1) cash contributed, (2) adjusted basis of property contributed, (3) amounts borrowed for which taxpayer is personally liable, (4) amounts borrowed secured by property (other than property used in the activity).",
        facts_summary="Nonrecourse financing generally is NOT at risk, except qualified nonrecourse financing for real estate activities (secured by real property, from qualified lenders). Applied before §469 passive activity rules.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["465", "at-risk", "nonrecourse", "qualified nonrecourse financing"],
    ),
    TechnicalAuthority(
        citation="IRC §465(b)(6)",
        authority_type="statute",
        title="Qualified Nonrecourse Financing — Real Estate Exception",
        year=1986,
        relevance="Nonrecourse financing from qualified lenders counts as at-risk for real estate",
        key_holding="Qualified nonrecourse financing is treated as an amount at risk for real estate activities. Requirements: (1) borrowed from a qualified lender (bank, insurance company, pension fund, or unrelated person in the lending business), (2) secured by real property used in the activity, (3) no person is personally liable for repayment. Seller financing does not qualify.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["465", "qualified nonrecourse", "real estate", "at-risk"],
    ),

    # --- §461(l) Excess Business Loss ---
    TechnicalAuthority(
        citation="IRC §461(l)",
        authority_type="statute",
        title="Excess Business Loss Limitation",
        year=2017,
        relevance="Noncorporate taxpayers: business losses limited to $289K/$578K (2024 single/MFJ)",
        key_holding="For noncorporate taxpayers, the excess business loss for the taxable year is not allowed. An excess business loss is the aggregate deductions from trades or businesses exceeding aggregate gross income/gain from such trades or businesses plus a threshold amount ($289,000 single / $578,000 MFJ for 2024, inflation-adjusted). Disallowed amounts treated as NOL carryforward.",
        facts_summary="Originally enacted by TCJA for 2018-2025, extended through 2028 by Inflation Reduction Act. Applied after §469 passive activity rules. Applies to noncorporate taxpayers (individuals, trusts, estates). Does not apply to C corporations.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["461(l)", "excess business loss", "threshold", "noncorporate", "TCJA"],
    ),

    # --- Key Case Law ---
    TechnicalAuthority(
        citation="Libson Shops, Inc. v. Koehler, 353 U.S. 382 (1957)",
        authority_type="case_law",
        title="Libson Shops — Pre-§382 NOL Limitation Principle",
        year=1957,
        relevance="Pre-§382 Supreme Court case establishing continuity of business enterprise for NOL carryovers",
        key_holding="The Supreme Court held that NOL carryovers should not be available to offset income from a different business following a merger. This continuity-of-business-enterprise principle was later codified and expanded in §382.",
        taxpayer_favorable=False,
        weight="some",
        topics=["382", "NOL", "continuity of business enterprise", "merger"],
    ),
    TechnicalAuthority(
        citation="Treas. Reg. §1.382-2T",
        authority_type="regulation",
        title="§382 — Definition of Ownership Change (Temporary Regulations)",
        year=1987,
        relevance="Detailed rules for testing ownership changes including segregation and public group rules",
        key_holding="Provides detailed rules for determining ownership changes, including: (1) identification of 5-percent shareholders, (2) aggregation of public shareholders, (3) segregation rules for public offerings, (4) options treated as exercised if they would cause an ownership change, (5) testing date rules, (6) small issuance exception.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["382", "ownership change", "5-percent shareholder", "public group", "options"],
    ),
    TechnicalAuthority(
        citation="Notice 2003-65, 2003-2 C.B. 747",
        authority_type="notice",
        title="§382 NUBIG/NUBIL — Safe Harbor Methods",
        year=2003,
        relevance="IRS safe harbor methods for computing NUBIG/NUBIL (§338 approach and §1374 approach)",
        key_holding="Provides two safe harbor methods for determining NUBIG/NUBIL: (1) the §1374 approach (generally taxpayer-favorable, identifies only items that would be recognized in a taxable sale), and (2) the §338 approach (hypothetical sale of all assets at FMV). Taxpayers may use either method pending final regulations.",
        facts_summary="The §1374 approach is generally preferred by taxpayers as it tends to produce a higher NUBIG or lower NUBIL. IRS has indicated it may issue regulations modifying these approaches.",
        taxpayer_favorable=True,
        weight="substantial",
        topics=["382", "NUBIG", "NUBIL", "safe harbor", "338 approach", "1374 approach"],
    ),
]


def get_nol_loss_limitation_lookup() -> AuthorityLookup:
    return AuthorityLookup(list(NOL_LOSS_LIMITATION_AUTHORITIES))
