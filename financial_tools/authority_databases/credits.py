"""Technical authority database for tax credits.

Covers §41 R&D credit, §45/§48 energy credits, §45C clinical testing,
§51 work opportunity credit, §47 rehabilitation credit, general business
credit rules (§38), and related authorities.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from revenue_recognition.technical_authority.authorities.base import (
    TechnicalAuthority, AuthorityLookup,
)

CREDIT_AUTHORITIES = [
    # --- General Business Credit ---
    TechnicalAuthority(
        citation="IRC §38(a)",
        authority_type="statute",
        title="General Business Credit — Allowance",
        year=1986,
        relevance="Aggregate of all component credits subject to limitation under §38(c)",
        key_holding="There shall be allowed as a credit against the tax the amount equal to the sum of the business credit carryforwards, the amount of the current year business credit, plus business credit carrybacks.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["general business credit", "38", "credit limitation"],
    ),
    TechnicalAuthority(
        citation="IRC §38(c)",
        authority_type="statute",
        title="General Business Credit — Limitation",
        year=1986,
        relevance="Credit limited to excess of net income tax over 25% of net regular tax liability above $25,000",
        key_holding="The general business credit for any taxable year shall not exceed the excess of the taxpayer's net income tax over the greater of: (1) the tentative minimum tax, or (2) 25% of so much of the net regular tax liability as exceeds $25,000.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["general business credit", "limitation", "38(c)"],
    ),
    TechnicalAuthority(
        citation="IRC §39(a)",
        authority_type="statute",
        title="Carryback and Carryforward of Business Credits",
        year=1986,
        relevance="Unused general business credits carry back 1 year, forward 20 years",
        key_holding="Unused business credits may be carried back 1 taxable year and carried forward 20 taxable years. The oldest credits are used first (FIFO ordering).",
        taxpayer_favorable=True,
        weight="primary",
        topics=["credit carryforward", "carryback", "39", "20-year"],
    ),

    # --- §41 R&D Credit ---
    TechnicalAuthority(
        citation="IRC §41(a)",
        authority_type="statute",
        title="Research Credit — General Rule",
        year=1981,
        relevance="Credit for increasing research activities — 20% of excess QREs over base amount",
        key_holding="There shall be allowed as a credit an amount equal to 20% of the excess of qualified research expenses (QREs) for the taxable year over the base amount. Alternative: 14% alternative simplified credit (ASC) computed as 14% of QREs exceeding 50% of average QREs for prior 3 years.",
        facts_summary="Made permanent by PATH Act (2015). §41(h) allows eligible small businesses to elect to apply credit against payroll taxes (up to $500,000/year for tax years beginning after 12/31/2022).",
        taxpayer_favorable=True,
        weight="primary",
        topics=["R&D credit", "41", "QRE", "base amount", "ASC"],
    ),
    TechnicalAuthority(
        citation="IRC §41(b)",
        authority_type="statute",
        title="Qualified Research Expenses Defined",
        year=1981,
        relevance="QREs = in-house research expenses + 65% of contract research expenses",
        key_holding="Qualified research expenses consist of: (1) in-house research expenses (wages for qualified services, supplies, and computer use charges), and (2) 65% of amounts paid for qualified research conducted by others (contract research). Basic research payments at 75%.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["R&D credit", "QRE", "in-house research", "contract research"],
    ),
    TechnicalAuthority(
        citation="IRC §41(d)",
        authority_type="statute",
        title="Qualified Research — 4-Part Test",
        year=1981,
        relevance="Research must meet 4-part test: §174 eligibility, technological uncertainty, process of experimentation, technological in nature",
        key_holding="Qualified research means research: (1) for which expenditures qualify under §174, (2) undertaken for the purpose of discovering information that is technological in nature, (3) the application of which is intended to be useful in the development of a new or improved business component, and (4) substantially all activities constitute a process of experimentation relating to function, performance, reliability, or quality.",
        facts_summary="The 4-part test must be met for ALL qualified research. Each business component is tested separately. Excludes: research after commercial production begins, adaptation of existing products, surveys/studies, certain software, foreign research, funded research.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["R&D credit", "4-part test", "qualified research", "technological uncertainty"],
    ),
    TechnicalAuthority(
        citation="IRC §41(h)",
        authority_type="statute",
        title="Payroll Tax Credit Election for Small Business",
        year=2015,
        relevance="Qualified small businesses may elect R&D credit against payroll taxes",
        key_holding="An eligible small business (gross receipts < $5M and no gross receipts for any year preceding the 5-year period) may elect to apply up to $500,000 of R&D credit against FICA payroll taxes. Extended to $500K by IRA 2022.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["R&D credit", "payroll tax", "startup", "41(h)"],
    ),

    # --- Treasury Regulations ---
    TechnicalAuthority(
        citation="Treas. Reg. §1.41-4(a)",
        authority_type="regulation",
        title="Qualified Research — 4-Part Test Regulations",
        year=2004,
        relevance="Detailed rules for applying the 4-part qualified research test",
        key_holding="Provides detailed guidance on each of the four requirements. 'Process of experimentation' means systematic evaluation of one or more alternatives to achieve a result where the capability or method of achieving that result is uncertain. '80% shrinking-back rule' allows credit on portion of activities meeting the test.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["R&D credit", "4-part test", "process of experimentation", "shrinking-back"],
    ),
    TechnicalAuthority(
        citation="Treas. Reg. §1.41-2",
        authority_type="regulation",
        title="Qualified Research Expenses",
        year=2004,
        relevance="What constitutes qualified wages, supplies, and contract research expenses",
        key_holding="QREs include: (1) wages for employees engaged in qualified research or directly supervising/supporting it, (2) amounts paid for supplies used in qualified research, and (3) 65% of contract research expenses. Wages must be W-2 wages; independent contractors excluded from in-house research wages.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["R&D credit", "QRE", "wages", "supplies", "contract research"],
    ),

    # --- Energy Credits (IRA 2022) ---
    TechnicalAuthority(
        citation="IRC §45 (as amended by IRA)",
        authority_type="statute",
        title="Production Tax Credit (PTC) for Renewable Energy",
        year=2022,
        relevance="Per-kWh credit for electricity produced from renewable sources",
        key_holding="Credit of 1.5¢/kWh (inflation-adjusted to ~2.75¢ for 2024) for electricity produced from wind, solar (pre-2022 placed-in-service), geothermal, biomass, landfill gas, trash, hydropower, and marine/hydrokinetic. Base credit × 5 if prevailing wage and apprenticeship requirements met.",
        facts_summary="IRA extended and modified PTC. Technology-neutral PTC (§45Y) applies for facilities placed in service after 12/31/2024. Direct pay and transferability options available.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["PTC", "45", "renewable energy", "production credit", "IRA"],
    ),
    TechnicalAuthority(
        citation="IRC §48 (as amended by IRA)",
        authority_type="statute",
        title="Investment Tax Credit (ITC) for Energy Property",
        year=2022,
        relevance="Percentage-of-basis credit for energy property investments",
        key_holding="30% credit (base rate 6%, × 5 for prevailing wage/apprenticeship) for solar, fuel cell, small wind, battery storage (new), geothermal heat pump, microgrid, and other qualifying energy property. Adders: 10% domestic content bonus, 10% energy community bonus.",
        facts_summary="IRA made major changes: added standalone storage, extended solar at 30%, created bonus credits. Technology-neutral ITC (§48E) applies for property placed in service after 12/31/2024. Direct pay available for tax-exempt entities and certain taxpayers.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["ITC", "48", "solar", "energy property", "IRA", "battery storage"],
    ),
    TechnicalAuthority(
        citation="IRC §45X",
        authority_type="statute",
        title="Advanced Manufacturing Production Credit",
        year=2022,
        relevance="Per-unit credit for domestic production of clean energy components",
        key_holding="Credit for domestic production of solar cells, solar wafers, PV cells, wind components, battery cells/modules, critical minerals, and inverters. Amount varies by component. Available for components produced and sold from 2023-2032.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["45X", "manufacturing", "clean energy", "IRA"],
    ),

    # --- Case Law ---
    TechnicalAuthority(
        citation="United States v. McFerrin, 570 F.3d 672 (5th Cir. 2009)",
        authority_type="case_law",
        title="McFerrin — R&D Credit 4-Part Test Applied",
        year=2009,
        relevance="Court analyzed each of the 4 requirements for §41 qualified research",
        key_holding="Taxpayer's concrete construction activities did not constitute qualified research because activities were not undertaken to discover information eliminating technological uncertainty. Routine application of known techniques is not qualified research.",
        taxpayer_favorable=False,
        weight="substantial",
        topics=["R&D credit", "4-part test", "technological uncertainty", "routine"],
    ),
    TechnicalAuthority(
        citation="Suder v. Commissioner, T.C. Memo 2014-201",
        authority_type="case_law",
        title="Suder — R&D Credit Documentation Requirements",
        year=2014,
        relevance="Importance of contemporaneous documentation for R&D credit claims",
        key_holding="Taxpayer's R&D credit claim was denied in part due to lack of contemporaneous documentation linking activities to specific business components and technological uncertainties. Estimates and after-the-fact reconstructions are subject to heightened scrutiny.",
        taxpayer_favorable=False,
        weight="substantial",
        topics=["R&D credit", "documentation", "substantiation"],
    ),
    TechnicalAuthority(
        citation="Union Carbide Corp. v. Commissioner, 97 T.C. 552 (1991)",
        authority_type="case_law",
        title="Union Carbide — §263A Applied to Self-Constructed Assets",
        year=1991,
        relevance="UNICAP applies to self-constructed assets including capitalized interest",
        key_holding="Taxpayer was required to capitalize indirect costs to self-constructed equipment under §263A, including a share of general and administrative expenses.",
        taxpayer_favorable=False,
        weight="substantial",
        topics=["263A", "self-constructed assets", "indirect costs"],
    ),

    # --- §45C Clinical Testing ---
    TechnicalAuthority(
        citation="IRC §45C",
        authority_type="statute",
        title="Orphan Drug Credit",
        year=1983,
        relevance="25% credit for clinical testing expenses for rare diseases/conditions",
        key_holding="A credit of 25% is allowed for qualified clinical testing expenses paid or incurred for testing of drugs designated under §526 of the FFDCA (orphan drugs). Qualified clinical testing expenses are defined similarly to §41 QREs but limited to human clinical testing for rare disease.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["orphan drug", "45C", "clinical testing", "rare disease"],
    ),

    # --- §51 Work Opportunity Credit ---
    TechnicalAuthority(
        citation="IRC §51",
        authority_type="statute",
        title="Work Opportunity Tax Credit (WOTC)",
        year=1996,
        relevance="Credit for hiring individuals from targeted groups",
        key_holding="Credit equal to 40% of first $6,000 of qualified first-year wages ($2,400 max per employee) for hiring members of targeted groups (veterans, SNAP recipients, ex-felons, designated community residents, etc.). 25% rate if employee works at least 120 but less than 400 hours.",
        facts_summary="Requires pre-screening (Form 8850 submitted within 28 days of hire). Currently extended through 12/31/2025.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["WOTC", "51", "hiring credit", "targeted groups"],
    ),

    # --- §47 Rehabilitation Credit ---
    TechnicalAuthority(
        citation="IRC §47",
        authority_type="statute",
        title="Rehabilitation Credit",
        year=1986,
        relevance="20% credit for qualified rehabilitation expenditures on certified historic structures",
        key_holding="A 20% credit is allowed for qualified rehabilitation expenditures with respect to a certified historic structure. Must be a 'substantial rehabilitation' (expenditures during 24-month period exceed the greater of adjusted basis or $5,000). Credit ratably claimed over 5 years.",
        facts_summary="TCJA changed from immediate credit to 5-year ratable claim for property placed in service after 12/31/2017.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["rehabilitation credit", "47", "historic structures"],
    ),

    # --- IRS Guidance ---
    TechnicalAuthority(
        citation="Notice 2024-44",
        authority_type="notice",
        title="IRA Energy Credit Guidance — Prevailing Wage & Apprenticeship",
        year=2024,
        relevance="Requirements for 5x bonus credit multiplier under IRA",
        key_holding="To qualify for the 5x credit multiplier, taxpayers must ensure that laborers and mechanics are paid prevailing wages (as determined by DOL) during construction AND for 5 years after placed in service. Apprenticeship requirements: applicable percentage of labor hours must be performed by qualified apprentices.",
        taxpayer_favorable=True,
        weight="substantial",
        topics=["IRA", "prevailing wage", "apprenticeship", "5x multiplier"],
    ),
    TechnicalAuthority(
        citation="Rev. Proc. 2024-19",
        authority_type="rev_proc",
        title="Energy Credit Transferability and Direct Pay",
        year=2024,
        relevance="Procedures for transferring energy credits under §6418 and direct pay under §6417",
        key_holding="Eligible taxpayers may elect to transfer all or a portion of eligible credits to unrelated taxpayers for cash consideration under §6418. Tax-exempt entities, state/local governments, and tribal entities may elect direct pay under §6417.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["credit transfer", "direct pay", "6418", "6417", "IRA"],
    ),
    TechnicalAuthority(
        citation="CCA 202302011",
        authority_type="cca",
        title="R&D Credit — Funded Research Exclusion",
        year=2023,
        relevance="When contract research is 'funded' and excluded from QREs",
        key_holding="Research is 'funded' if the taxpayer is not entitled to retain rights to the research results. If the payer retains substantially all rights, the performing party's research expenses are funded and do not qualify for the §41 credit.",
        taxpayer_favorable=False,
        weight="some",
        topics=["R&D credit", "funded research", "contract research"],
    ),
]


def get_credits_lookup() -> AuthorityLookup:
    """Return an AuthorityLookup loaded with credit authorities."""
    return AuthorityLookup(list(CREDIT_AUTHORITIES))
