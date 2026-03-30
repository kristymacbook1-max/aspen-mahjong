"""Technical authorities for §174 R&D capitalization and amortization.

Covers the post-2022 mandatory capitalization requirement, domestic vs. foreign
amortization periods, and interaction with §41 R&D credit.
"""

from .base import TechnicalAuthority

RESEARCH_DEVELOPMENT_AUTHORITIES = [
    TechnicalAuthority(
        citation="IRC §174(a)",
        authority_type="statute",
        title="§174 Research and Experimental Expenditures — Amortization",
        year=2017,
        relevance="Post-2022: mandatory capitalization and amortization of R&E expenditures",
        key_holding="For amounts paid or incurred in taxable years beginning after December 31, 2021, specified research or experimental expenditures shall be charged to capital account and amortized ratably over the applicable period (5 years domestic, 15 years foreign).",
        facts_summary="TCJA §13206 eliminated the option to currently deduct R&E expenditures. Effective for tax years beginning after 12/31/2021. Mid-year convention applies (deduction begins in the midpoint of the year expenditure is paid or incurred).",
        taxpayer_favorable=False,
        weight="primary",
        topics=["174", "R&D capitalization", "amortization", "TCJA"],
    ),
    TechnicalAuthority(
        citation="IRC §174(b)(1)",
        authority_type="statute",
        title="Domestic R&E — 5-Year Amortization",
        year=2017,
        relevance="Domestic R&E: 5-year amortization period",
        key_holding="Specified research or experimental expenditures which are not attributable to research conducted outside the United States shall be amortized ratably over a 5-year period beginning with the midpoint of the taxable year in which such expenditures are paid or incurred.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["174", "domestic R&D", "5-year amortization"],
    ),
    TechnicalAuthority(
        citation="IRC §174(b)(2)",
        authority_type="statute",
        title="Foreign R&E — 15-Year Amortization",
        year=2017,
        relevance="Foreign R&E: 15-year amortization period",
        key_holding="Specified research or experimental expenditures attributable to research conducted outside the United States shall be amortized ratably over a 15-year period beginning with the midpoint of the taxable year.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["174", "foreign R&D", "15-year amortization"],
    ),
    TechnicalAuthority(
        citation="IRC §174(c)",
        authority_type="statute",
        title="Specified R&E Expenditures Defined",
        year=2017,
        relevance="Definition of what constitutes specified R&E expenditures subject to capitalization",
        key_holding="Specified research or experimental expenditures means research or experimental expenditures paid or incurred by the taxpayer during such taxable year in connection with the taxpayer's trade or business. Includes software development costs (§174(c)(3)).",
        facts_summary="Importantly includes software development costs, which were previously subject to separate rules under Rev. Proc. 2000-50.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["174", "R&D definition", "software development"],
    ),

    # --- Treasury Regulations / Guidance ---
    TechnicalAuthority(
        citation="Notice 2023-63 (modified by Notice 2024-12)",
        authority_type="notice",
        title="Interim Guidance on §174 Capitalization",
        year=2023,
        relevance="Comprehensive interim guidance on §174 amortization requirements",
        key_holding="Provides guidance on: (1) definition of specified R&E expenditures, (2) determination of domestic vs. foreign, (3) cost allocation methods, (4) disposition of property with capitalized §174 costs, (5) interaction with §41 R&D credit, and (6) mid-year convention application.",
        facts_summary="Key clarifications: software development costs are §174 costs. Contract research costs are §174 costs to the party bearing economic risk. Labor costs include allocable share of compensation and benefits.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["174", "interim guidance", "software", "contract research", "cost allocation"],
    ),
    TechnicalAuthority(
        citation="Treas. Reg. §1.174-2(a)",
        authority_type="regulation",
        title="Definition of Research and Experimental Expenditures (Pre-TCJA Regs)",
        year=1994,
        relevance="Definition of R&E — still relevant for determining what qualifies as §174 costs",
        key_holding="Research and experimental expenditures means expenditures incurred in connection with the taxpayer's trade or business which represent research and development costs in the experimental or laboratory sense. Includes all costs incident to the development or improvement of a product.",
        facts_summary="These regulations, while predating TCJA §174 amendments, still provide guidance on what constitutes R&E expenditures. Product includes any pilot model, process, formula, invention, technique, patent, or similar property.",
        taxpayer_favorable=True,
        weight="substantial",
        topics=["174", "R&D definition", "experimental", "product development"],
    ),

    # --- Case Law ---
    TechnicalAuthority(
        citation="Snow v. Commissioner, 416 U.S. 500 (1974)",
        authority_type="case_law",
        title="Snow — §174 Applies to Depreciable Property Development",
        year=1974,
        relevance="§174 can apply to costs of developing depreciable property",
        key_holding="Section 174 can apply to expenditures for research and experimentation even if the research leads to the development of depreciable property. The expenditures need not be for activities that are uncertain in nature.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["174", "depreciable property", "R&D definition"],
    ),
    TechnicalAuthority(
        citation="Suzy's Zoo v. Commissioner, 114 T.C. 1 (2000)",
        authority_type="case_law",
        title="Suzy's Zoo — Graphic Design Not R&E",
        year=2000,
        relevance="Quality control and aesthetic design costs are NOT §174 R&E",
        key_holding="Costs of developing greeting card designs through artistic and aesthetic processes are not research and experimental expenditures under §174. §174 requires activities aimed at discovering information that would eliminate uncertainty about the development or improvement of a product.",
        taxpayer_favorable=False,
        weight="substantial",
        topics=["174", "R&D definition", "artistic", "uncertainty"],
    ),

    # --- §41 Credit Interaction ---
    TechnicalAuthority(
        citation="IRC §41(a)",
        authority_type="statute",
        title="Research Credit — General Rule",
        year=1981,
        relevance="§41 R&D credit — computed on qualified research expenses, interacts with §174 amounts",
        key_holding="There shall be allowed as a credit against tax an amount equal to the sum of 20% of the excess of qualified research expenses over the base amount, plus 20% of basic research payments. The §280C(c) election reduces the credit but allows full §174 deduction.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["R&D credit", "41", "174 interaction", "qualified research expenses"],
    ),
    TechnicalAuthority(
        citation="IRC §280C(c)",
        authority_type="statute",
        title="§280C — Reduction of §174 Deduction for §41 Credit",
        year=1986,
        relevance="§174 deduction reduced by §41 credit unless §280C(c)(3) election made",
        key_holding="The amount of §174 deduction must be reduced by the amount of the §41 credit. Alternatively, taxpayer may elect under §280C(c)(3) to take a reduced credit (80% of the otherwise allowable credit) and claim the full §174 deduction.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["280C", "R&D credit", "174 interaction", "reduced credit election"],
    ),
]
