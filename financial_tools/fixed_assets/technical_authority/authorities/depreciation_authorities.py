"""Technical authorities for fixed asset depreciation.

Covers §168 MACRS, §179 expensing, §168(k) bonus depreciation, §1031
like-kind exchanges, cost segregation, and asset disposition rules.
"""

from .base import TechnicalAuthority

DEPRECIATION_AUTHORITIES = [
    # --- MACRS ---
    TechnicalAuthority(
        citation="IRC §168(a)",
        authority_type="statute",
        title="MACRS — General Rule",
        year=1986,
        relevance="MACRS is the required depreciation method for most tangible property",
        key_holding="The depreciation deduction under §167(a) for any tangible property shall be determined by using the applicable depreciation method, applicable recovery period, and applicable convention.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["MACRS", "168", "depreciation", "recovery period"],
    ),
    TechnicalAuthority(
        citation="IRC §168(b)",
        authority_type="statute",
        title="MACRS — Applicable Depreciation Methods",
        year=1986,
        relevance="200% DB for 3/5/7/10yr, 150% DB for 15/20yr, SL for nonresidential real (39yr) and residential (27.5yr)",
        key_holding="Applicable depreciation method: (1) 200% declining balance switching to SL for 3, 5, 7, 10-year property, (2) 150% declining balance switching to SL for 15, 20-year property, (3) straight-line for nonresidential real (39yr), residential rental (27.5yr), and ADS property.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["MACRS", "depreciation method", "200DB", "150DB", "straight-line"],
    ),
    TechnicalAuthority(
        citation="IRC §168(e)",
        authority_type="statute",
        title="MACRS — Classification of Property",
        year=1986,
        relevance="Recovery period classes based on ADR class lives",
        key_holding="Property is classified into recovery periods: 3-year (ADR ≤4), 5-year (ADR 4-10, autos, computers), 7-year (ADR 10-16, furniture, fixtures), 10-year (ADR 16-20), 15-year (land improvements, QIP), 20-year (ADR 25+), 27.5-year (residential rental), 39-year (nonresidential real).",
        taxpayer_favorable=True,
        weight="primary",
        topics=["MACRS", "classification", "recovery period", "ADR"],
    ),

    # --- Bonus Depreciation ---
    TechnicalAuthority(
        citation="IRC §168(k)",
        authority_type="statute",
        title="Bonus Depreciation — Additional First-Year Depreciation",
        year=2017,
        relevance="100% bonus depreciation (TCJA), phasing down 20%/year from 2023-2026",
        key_holding="In the case of qualified property, an additional depreciation deduction is allowed equal to the applicable percentage of the adjusted basis. TCJA set rate at 100% for property placed in service after 9/27/2017. Phase-down: 80% (2023), 60% (2024), 40% (2025), 20% (2026), 0% (2027+).",
        facts_summary="Qualified property: MACRS property with recovery period ≤20 years, computer software, water utility property, and QIP. Must be new (or used, post-TCJA) property. Anti-churning rules apply to related-party acquisitions.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["bonus depreciation", "168(k)", "100%", "phase-down", "TCJA"],
    ),

    # --- §179 ---
    TechnicalAuthority(
        citation="IRC §179(a)",
        authority_type="statute",
        title="§179 Expensing — Election to Expense",
        year=1986,
        relevance="Immediate expensing of qualifying property up to annual limit ($1.22M for 2024)",
        key_holding="A taxpayer may elect to treat the cost of qualifying §179 property as an expense rather than a capital expenditure. Annual limit: $1,220,000 for 2024 (inflation-adjusted). Phase-out begins when total §179 property placed in service exceeds $3,050,000.",
        facts_summary="§179 property: tangible personal property, off-the-shelf software, qualified real property (QIP, roofs, HVAC, fire protection, security). Cannot create or increase a loss.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["179", "expensing", "election", "annual limit"],
    ),

    # --- §1031 Like-Kind Exchanges ---
    TechnicalAuthority(
        citation="IRC §1031(a)",
        authority_type="statute",
        title="Like-Kind Exchanges — Nonrecognition",
        year=2017,
        relevance="Gain deferred on exchange of like-kind real property held for business or investment",
        key_holding="No gain or loss shall be recognized on the exchange of real property held for productive use in a trade or business or for investment if such real property is exchanged solely for real property of like kind which is to be held for productive use in a trade or business or for investment.",
        facts_summary="Post-TCJA: §1031 applies ONLY to real property (not personal property, intangibles, etc.). 45-day identification and 180-day exchange periods apply. Qualified intermediary required for deferred exchanges.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["1031", "like-kind exchange", "real property", "deferral"],
    ),
    TechnicalAuthority(
        citation="IRC §1031(a)(3)",
        authority_type="statute",
        title="§1031 Identification and Exchange Periods",
        year=1984,
        relevance="45-day identification window and 180-day exchange completion requirement",
        key_holding="Replacement property must be identified within 45 days after transfer of relinquished property, and received within the earlier of 180 days or the due date (with extensions) of the taxpayer's return for the year of transfer.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["1031", "45 days", "180 days", "identification", "timeline"],
    ),

    # --- Cost Segregation ---
    TechnicalAuthority(
        citation="Hospital Corp. of America v. Commissioner, 109 T.C. 21 (1997)",
        authority_type="case_law",
        title="Hospital Corp. — Cost Segregation Upheld",
        year=1997,
        relevance="Landmark case supporting cost segregation studies to reclassify building components",
        key_holding="Tax Court allowed reclassification of building components (carpet, vinyl tile, wall coverings, certain electrical, plumbing) from 39-year real property to 5-year or 7-year personal property based on cost segregation engineering study.",
        facts_summary="IRS initially challenged but the Tax Court held that properly documented engineering-based cost segregation studies are valid for reclassifying building components to shorter MACRS lives.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["cost segregation", "building components", "reclassification", "MACRS"],
    ),
    TechnicalAuthority(
        citation="IRS Audit Technique Guide — Cost Segregation (2004)",
        authority_type="notice",
        title="IRS Cost Segregation ATG",
        year=2004,
        relevance="IRS guidance on acceptable cost segregation methodologies",
        key_holding="The IRS recognizes engineering-based cost segregation studies as the preferred methodology. Acceptable approaches: detailed engineering approach, sampling/modeling, and residual estimation. Studies should be conducted by qualified professionals with construction/engineering expertise.",
        taxpayer_favorable=True,
        weight="substantial",
        topics=["cost segregation", "ATG", "engineering study", "methodology"],
    ),

    # --- Qualified Improvement Property ---
    TechnicalAuthority(
        citation="IRC §168(e)(6)",
        authority_type="statute",
        title="Qualified Improvement Property (QIP) — 15-Year Life",
        year=2020,
        relevance="QIP is 15-year MACRS property, eligible for bonus depreciation (CARES Act fix)",
        key_holding="Qualified improvement property is any improvement to an interior portion of a nonresidential building placed in service after the building was placed in service. QIP has a 15-year recovery period and is eligible for bonus depreciation.",
        facts_summary="CARES Act (2020) retroactively corrected the 'retail glitch' — QIP was supposed to be 15-year (bonus-eligible) under TCJA but was inadvertently assigned 39 years. Fix is retroactive to 2018.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["QIP", "qualified improvement property", "15-year", "bonus depreciation", "CARES Act"],
    ),

    # --- Dispositions ---
    TechnicalAuthority(
        citation="Treas. Reg. §1.168(i)-8",
        authority_type="regulation",
        title="Disposition of MACRS Property",
        year=2014,
        relevance="Rules for recognizing loss on partial disposition of MACRS assets",
        key_holding="A taxpayer may make a partial disposition election to recognize a loss when a portion of a MACRS asset is disposed of (e.g., replacing a roof). Without the election, the disposed component's basis remains in the original asset's depreciation pool.",
        facts_summary="Partial disposition election is made on a timely filed return (including extensions) or via Form 3115 for prior-year dispositions. Allows recognition of remaining basis as a loss.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["disposition", "partial disposition", "168(i)-8", "loss recognition"],
    ),

    # --- Method Changes ---
    TechnicalAuthority(
        citation="Rev. Proc. 2024-23 (CAM §6)",
        authority_type="rev_proc",
        title="Automatic Consent — Depreciation Method Changes",
        year=2024,
        relevance="Automatic method changes for depreciation including late bonus, §179, and cost segregation",
        key_holding="Various depreciation method changes qualify for automatic consent under Form 3115: change in depreciation method, recovery period, convention, and treatment of property. Includes changes to claim missed bonus depreciation, late §179 elections, and cost segregation reclassifications.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["depreciation", "method change", "automatic consent", "Form 3115", "cost segregation"],
    ),
]
