"""Technical authority database for cost capitalization.

Covers the required and elective capitalization provisions of IRC §266
(carrying charges), §263(a) (acquisition / improvement costs, the "repair
regs"), and §263A (UNICAP), plus related capitalization regimes (§174A R&E,
§197, §195/§248/§709, IDC, §263(g), §461(g), §168(k)/§179).

Verified against IRS.gov, eCFR, Cornell LII, Rev. Procs. 2025-28 & 2025-32,
T.D. 9843, and P.L. 119-21 (OBBBA); current as of 2026-06-30. §263A UNICAP and
§471(c) small-business entries are also covered in inventory.py — refer there
for the inventory-method context.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from revenue_recognition.technical_authority.authorities.base import (
    TechnicalAuthority, AuthorityLookup,
)

COST_CAPITALIZATION_AUTHORITIES = [
    # ----------------------------------------------------------------- §266
    TechnicalAuthority(
        citation="IRC §266",
        authority_type="statute",
        title="Carrying Charges — Elective Capitalization",
        year=1986,
        relevance="266 elective capitalization of taxes and carrying charges",
        key_holding="No deduction is allowed for taxes and carrying charges chargeable to "
                    "capital account if the taxpayer elects to treat them as so chargeable. "
                    "Purely enabling/elective; mechanics delegated to Reg §1.266-1.",
        facts_summary="Lets a taxpayer forgo a current deduction and add otherwise-deductible "
                      "taxes and carrying charges to the property's basis.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["266", "carrying charges", "capitalization election", "basis"],
    ),
    TechnicalAuthority(
        citation="Reg §1.266-1(b)(1)(i)",
        authority_type="regulation",
        title="§266 — Unimproved and Unproductive Real Property",
        year=1957,
        relevance="266 carrying charges on unimproved investment land",
        key_holding="Election to capitalize annual taxes, mortgage interest, and other carrying "
                    "charges on unimproved/unproductive real property. Made on a YEAR-TO-YEAR "
                    "(annual) basis, effective only for the year elected.",
        facts_summary="Key post-TCJA planning tool: capitalizing investment-land property taxes "
                      "sidesteps the $10,000 SALT cap (§164(b)(6)) by preserving them as basis.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["266", "unimproved real property", "investment land", "annual election", "SALT cap"],
    ),
    TechnicalAuthority(
        citation="Reg §1.266-1(b)(1)(ii)",
        authority_type="regulation",
        title="§266 — Real Property in Development / Construction",
        year=1957,
        relevance="266 capitalization of construction-period interest, taxes, development costs",
        key_holding="Election to capitalize loan interest, specified payroll/material taxes, and "
                    "other necessary development/construction expenditures to completion. "
                    "PROJECT-PERIOD election that binds for the entire development period (may "
                    "span multiple tax years).",
        taxpayer_favorable=True,
        weight="substantial",
        topics=["266", "development real property", "construction-period interest", "project election"],
    ),
    TechnicalAuthority(
        citation="Reg §1.266-1(b)(1)(iii)",
        authority_type="regulation",
        title="§266 — Personal Property",
        year=1957,
        relevance="266 capitalization of interest/taxes/carrying charges on personal property",
        key_holding="Election to capitalize loan interest, taxes, storage, transportation, and "
                    "insurance on personal property up to the later of installation or first use.",
        taxpayer_favorable=True,
        weight="some",
        topics=["266", "personal property", "storage", "transportation", "insurance"],
    ),
    TechnicalAuthority(
        citation="Reg §1.266-1(b)(1)(iv) / (b)(2)",
        authority_type="regulation",
        title="§266 — Commissioner Catch-All / 'Otherwise Deductible' Gate",
        year=1957,
        relevance="266 catch-all for other carrying charges chargeable to capital account",
        key_holding="Permits capitalization of any other otherwise-deductible taxes/carrying "
                    "charges that, under sound accounting principles, the Commissioner considers "
                    "chargeable to capital account. §266 can NEVER capitalize a non-deductible item.",
        notes="Ordering: §263A is mandatory and applies FIRST; §266 is a residual election "
              "available only if it does not materially distort any computation.",
        taxpayer_favorable=True,
        weight="some",
        topics=["266", "catch-all", "sound accounting", "otherwise deductible", "263A ordering"],
    ),
    TechnicalAuthority(
        citation="Reg §1.266-1(c)",
        authority_type="regulation",
        title="§266 — Manner of Making the Election",
        year=1957,
        relevance="266 election mechanics",
        key_holding="Election made by a statement filed with the timely original return for the "
                    "year. No IRS consent needed to elect. Unimproved-land election is annual; "
                    "development/personal-property elections bind for the full applicable period.",
        taxpayer_favorable=True,
        weight="substantial",
        topics=["266", "election statement", "original return", "no IRS consent"],
    ),

    # -------------------------------------------------------------- §263(a)
    TechnicalAuthority(
        citation="IRC §263(a)",
        authority_type="statute",
        title="Capital Expenditures — General Rule",
        year=1986,
        relevance="263(a) required capitalization of improvements and acquisitions",
        key_holding="No current deduction for new buildings, permanent improvements or betterments "
                    "that increase the value of property, or for restoring property/making good "
                    "exhaustion for which depreciation has been allowed. Such amounts are capitalized.",
        facts_summary="Statutory exceptions preserve deductions under §§173, 174/174A, 179, 190, "
                      "263(c), 616, and others.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["263(a)", "capital expenditure", "permanent improvement", "betterment", "restoration"],
    ),
    TechnicalAuthority(
        citation="Reg §1.263(a)-1(f)",
        authority_type="regulation",
        title="De Minimis Safe Harbor Election",
        year=2013,
        relevance="263(a) de minimis safe harbor to deduct small-dollar acquisitions",
        key_holding="Annual irrevocable election to deduct amounts paid to acquire/produce tangible "
                    "property below a per-item/per-invoice ceiling: $5,000 with an Applicable "
                    "Financial Statement (AFS), $2,500 without (Notice 2015-82).",
        facts_summary="Verified NOT inflation-indexed; thresholds unchanged through 2026 (no OBBBA "
                      "change). Election statement attached to the timely original return.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["263(a)", "de minimis safe harbor", "AFS", "$2,500", "$5,000"],
    ),
    TechnicalAuthority(
        citation="Reg §1.263(a)-2",
        authority_type="regulation",
        title="Amounts Paid to Acquire or Produce Tangible Property",
        year=2013,
        relevance="263(a) capitalization of acquisition and inherently facilitative costs",
        key_holding="Must capitalize amounts paid to acquire/produce a unit of property, including "
                    "amounts that facilitate the acquisition. INHERENTLY FACILITATIVE costs (broker "
                    "fees, appraisals, title/transfer, surveys) are always capitalized into basis.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["263(a)", "acquisition costs", "inherently facilitative", "transaction costs"],
    ),
    TechnicalAuthority(
        citation="Reg §1.263(a)-3",
        authority_type="regulation",
        title="Amounts Paid to Improve Tangible Property (BRA / RABI)",
        year=2013,
        relevance="263(a) improvement standards — betterment, restoration, adaptation",
        key_holding="Must capitalize amounts resulting in a Betterment, Restoration, or Adaptation "
                    "to a new/different use (BRA tests), measured against the unit of property — for "
                    "buildings, the structure and each of nine building systems (HVAC, plumbing, "
                    "electrical, escalators, elevators, fire-protection, security, gas, and others).",
        taxpayer_favorable=False,
        weight="primary",
        topics=["263(a)", "betterment", "restoration", "adaptation", "BRA", "unit of property",
                "building systems"],
    ),
    TechnicalAuthority(
        citation="Reg §1.263(a)-3(h)",
        authority_type="regulation",
        title="Small Taxpayer Safe Harbor for Buildings",
        year=2013,
        relevance="263(a) small-taxpayer safe harbor to deduct building repairs/improvements",
        key_holding="Qualifying small taxpayer (avg annual gross receipts <= $10,000,000) may deduct "
                    "amounts for repairs/maintenance/improvements on a building with unadjusted basis "
                    "<= $1,000,000 if total such amounts <= the lesser of $10,000 or 2% of basis.",
        taxpayer_favorable=True,
        weight="substantial",
        topics=["263(a)", "small taxpayer safe harbor", "$10,000,000", "$1,000,000", "2%"],
    ),
    TechnicalAuthority(
        citation="Reg §1.263(a)-3(i)",
        authority_type="regulation",
        title="Routine Maintenance Safe Harbor",
        year=2013,
        relevance="263(a) routine maintenance deductible",
        key_holding="Recurring activities to keep a unit of property in ordinarily efficient "
                    "operating condition are deductible if reasonably expected to be performed more "
                    "than once over the property's ADS class life (buildings: more than once in 10 "
                    "years). Not an election — a safe harbor applied when criteria are met.",
        taxpayer_favorable=True,
        weight="substantial",
        topics=["263(a)", "routine maintenance safe harbor", "10-year", "ADS class life"],
    ),
    TechnicalAuthority(
        citation="Reg §1.263(a)-3(n)",
        authority_type="regulation",
        title="Election to Capitalize Repair and Maintenance Costs",
        year=2013,
        relevance="263(a) elective capitalization of book-capitalized repairs",
        key_holding="A taxpayer that capitalizes repair/maintenance costs on its books may elect to "
                    "capitalize them for tax and depreciate. Annual irrevocable election; statement "
                    "on the timely original return.",
        taxpayer_favorable=True,
        weight="some",
        topics=["263(a)", "capitalize repairs election", "book conformity"],
    ),
    TechnicalAuthority(
        citation="Reg §1.263(a)-4",
        authority_type="regulation",
        title="Amounts Paid to Acquire or Create Intangibles (12-Month Rule)",
        year=2004,
        relevance="263(a) capitalization of acquired/created intangibles",
        key_holding="Must capitalize amounts to acquire/create intangibles and to facilitate their "
                    "creation. 12-MONTH RULE: no capitalization for a right/benefit not extending "
                    "beyond the earlier of 12 months or the end of the next tax year. $5,000 "
                    "per-transaction de minimis for facilitative costs.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["263(a)", "intangibles", "12-month rule", "created intangibles", "$5,000"],
    ),
    TechnicalAuthority(
        citation="Reg §1.263(a)-5",
        authority_type="regulation",
        title="Transaction Costs — Acquisitions, Reorganizations, Restructurings",
        year=2004,
        relevance="263(a) capitalization of transaction costs that facilitate a business acquisition",
        key_holding="Must capitalize amounts that facilitate acquisitions of a trade/business, "
                    "reorganizations, and capital transactions. For a covered transaction, a "
                    "BRIGHT-LINE DATE rule deducts pre-decision investigatory costs (except "
                    "inherently facilitative ones, always capitalized).",
        facts_summary="Rev. Proc. 2011-29 success-based-fee safe harbor: elect to treat 70% of a "
                      "success-based fee as deductible and capitalize 30%.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["263(a)", "transaction costs", "covered transaction", "bright-line date",
                "success-based fees", "Rev Proc 2011-29"],
    ),
    TechnicalAuthority(
        citation="Rev. Proc. 2011-29",
        authority_type="rev_proc",
        title="Success-Based Fee 70% Safe Harbor",
        year=2011,
        relevance="263(a) elective 70/30 split for success-based transaction fees",
        key_holding="In lieu of documenting the non-facilitative portion, an electing taxpayer may "
                    "treat 70% of a success-based fee in a covered transaction as deductible and "
                    "capitalize the remaining 30%. Irrevocable, per-transaction election.",
        taxpayer_favorable=True,
        weight="substantial",
        topics=["263(a)", "success-based fees", "70% safe harbor", "covered transaction"],
    ),

    # --------------------------------------------------------------- §263A
    TechnicalAuthority(
        citation="IRC §263A",
        authority_type="statute",
        title="Uniform Capitalization (UNICAP) — General Rule",
        year=2017,
        relevance="263A required capitalization of production and resale costs",
        key_holding="Direct costs and an allocable share of indirect costs that directly benefit or "
                    "are incurred by reason of production or resale must be capitalized to "
                    "inventory/property. §263A(i) exempts taxpayers (non-tax-shelters) meeting the "
                    "§448(c) gross-receipts test (covers producers, resellers, and interest cap).",
        facts_summary="§448(c) threshold: $30M (2024) / $31M (2025) / $32M (2026).",
        taxpayer_favorable=False,
        weight="primary",
        topics=["263A", "UNICAP", "produced property", "acquired for resale", "small business exception",
                "448(c)"],
    ),
    TechnicalAuthority(
        citation="Reg §1.263A-1",
        authority_type="regulation",
        title="UNICAP — General Rules; §471 vs Additional §263A Costs",
        year=1993,
        relevance="263A allocation of direct and indirect costs",
        key_holding="Splits costs into §471 costs (capitalized under the pre-§263A method) and "
                    "ADDITIONAL §263A costs. Defines capitalizable indirect costs and the simplified "
                    "service cost method (labor-based or production-cost allocation ratio).",
        facts_summary="Non-capitalizable: selling/marketing/distribution, §174 R&E, §165 losses, "
                      "income taxes, §179, on-site retail storage.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["263A", "section 471 costs", "additional 263A costs", "mixed service costs",
                "simplified service cost"],
    ),
    TechnicalAuthority(
        citation="Reg §1.263A-2",
        authority_type="regulation",
        title="UNICAP — Producers (SPM / MSPM)",
        year=2018,
        relevance="263A simplified production method absorption ratio",
        key_holding="Producers may elect the Simplified Production Method (absorption ratio = "
                    "additional §263A costs / §471 costs, applied to §471 costs in ending inventory) "
                    "or the Modified Simplified Production Method (dual pre-production and production "
                    "ratios, T.D. 9843). SPM negatives allowed only if gross receipts <= $50M; MSPM "
                    "allows negatives.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["263A", "producers", "SPM", "MSPM", "absorption ratio", "negative adjustments",
                "$50M"],
    ),
    TechnicalAuthority(
        citation="Reg §1.263A-3",
        authority_type="regulation",
        title="UNICAP — Resellers (SRM)",
        year=1994,
        relevance="263A simplified resale method absorption ratio",
        key_holding="Resellers capitalize purchasing, handling, and storage costs. The Simplified "
                    "Resale Method combined absorption ratio = storage/handling ratio + purchasing "
                    "ratio, applied to §471 costs on hand. Negatives permitted (no $50M limit).",
        taxpayer_favorable=False,
        weight="primary",
        topics=["263A", "resellers", "SRM", "purchasing", "storage", "handling", "471(c)"],
    ),
    TechnicalAuthority(
        citation="Reg §1.263A-4",
        authority_type="regulation",
        title="UNICAP — Farming Business",
        year=1994,
        relevance="263A capitalization of preproductive farming costs",
        key_holding="Preproductive-period costs of producing plants/animals are capitalized unless "
                    "an election out (§263A(d)(3)) is made. §263A does not apply to plants with a "
                    "preproductive period of 2 years or less for non-accrual taxpayers.",
        taxpayer_favorable=False,
        weight="some",
        topics=["263A", "farming", "preproductive period", "election out", "2-year exception"],
    ),
    TechnicalAuthority(
        citation="Reg §1.263A-7",
        authority_type="regulation",
        title="UNICAP — Changing Methods / Revaluing Inventory",
        year=1994,
        relevance="263A method change and §481(a) adjustment",
        key_holding="On a §263A method change, beginning inventory is revalued; the difference is "
                    "the §481(a) adjustment. Revaluation via facts-and-circumstances, weighted "
                    "average, or 3-year average method.",
        taxpayer_favorable=False,
        weight="some",
        topics=["263A", "method change", "481(a)", "inventory revaluation"],
    ),
    TechnicalAuthority(
        citation="Reg §§1.263A-8 to -15",
        authority_type="regulation",
        title="UNICAP — Capitalization of Interest (Avoided-Cost Method)",
        year=1995,
        relevance="263A(f) interest capitalization on designated property",
        key_holding="Interest allocable to producing DESIGNATED PROPERTY must be capitalized via "
                    "the avoided-cost method (traced debt first, then a nontraced weighted-average "
                    "rate on excess expenditures). Designated property = all real property; or "
                    "tangible personal property with class life >= 20 yrs, or production period > 2 "
                    "yrs, or > 1 yr and cost > $1,000,000. Production period starts at 5% of "
                    "accumulated production expenditures (personal) / first physical activity (real).",
        taxpayer_favorable=False,
        weight="substantial",
        topics=["263A", "263A(f)", "interest capitalization", "avoided cost", "designated property",
                "accumulated production expenditures"],
    ),

    # ----------------------------------------------------- Related regimes
    TechnicalAuthority(
        citation="IRC §174 / §174A",
        authority_type="statute",
        title="Research & Experimental Expenditures",
        year=2025,
        relevance="other capitalization — R&E expensing vs amortization",
        key_holding="OBBBA (P.L. 119-21, §70302) added §174A restoring CURRENT EXPENSING of DOMESTIC "
                    "R&E for tax years beginning after 12/31/2024 (elective capitalization over not "
                    "less than 60 months). FOREIGN R&E remains REQUIRED to be capitalized and "
                    "amortized over 15 years under §174.",
        facts_summary="Transition for 2022-2024 capitalized domestic amounts (1-yr or 2-yr "
                      "catch-up); small-business (§448(c) <= $31M) retroactive election with amended-"
                      "return deadline 7/6/2026 (Rev. Proc. 2025-28).",
        taxpayer_favorable=True,
        weight="primary",
        topics=["other_cap", "174", "174A", "R&E", "software development", "OBBBA", "foreign research"],
    ),
    TechnicalAuthority(
        citation="IRC §197",
        authority_type="statute",
        title="Amortization of Acquired Intangibles",
        year=1993,
        relevance="other capitalization — 15-year amortization of acquired intangibles",
        key_holding="Capitalized cost of an amortizable §197 intangible (goodwill, going-concern, "
                    "workforce, customer lists, covenants not to compete, etc., acquired with a "
                    "business) is amortized straight-line over exactly 15 years. Anti-churning rules "
                    "apply.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["other_cap", "197", "acquired intangibles", "goodwill", "anti-churning"],
    ),
    TechnicalAuthority(
        citation="IRC §195 / §248 / §709",
        authority_type="statute",
        title="Start-up, Corporate, and Partnership Organizational Costs",
        year=2004,
        relevance="other capitalization — start-up and organizational expenditures",
        key_holding="Start-up (§195), corporate organizational (§248), and partnership "
                    "organizational (§709) costs are capitalized with an elective $5,000 immediate "
                    "deduction (reduced dollar-for-dollar above $50,000) plus 180-month amortization. "
                    "Partnership SYNDICATION costs (§709) are permanently capitalized — no deduction "
                    "or amortization.",
        taxpayer_favorable=True,
        weight="substantial",
        topics=["other_cap", "195", "248", "709", "start-up costs", "organizational costs",
                "syndication"],
    ),
    TechnicalAuthority(
        citation="IRC §263(c) / §59(e)",
        authority_type="statute",
        title="Intangible Drilling Costs (IDC)",
        year=1986,
        relevance="other capitalization — IDC expense or elective 60-month amortization",
        key_holding="Operators may elect to expense IDC under §263(c) or capitalize and amortize "
                    "over 60 months under §59(e) to avoid the AMT preference. Integrated oil "
                    "companies must capitalize 30% over 60 months (§291(b)).",
        taxpayer_favorable=True,
        weight="some",
        topics=["other_cap", "263(c)", "59(e)", "IDC", "oil and gas", "AMT"],
    ),
    TechnicalAuthority(
        citation="IRC §263(g)",
        authority_type="statute",
        title="Interest and Carrying Charges on Straddles",
        year=1986,
        relevance="other capitalization — straddle interest into basis",
        key_holding="No deduction for interest and carrying charges allocable to personal property "
                    "that is part of a straddle; the disallowed amount is charged to the property's "
                    "capital account (basis). Does not apply to §1256(e) hedging.",
        taxpayer_favorable=False,
        weight="some",
        topics=["other_cap", "263(g)", "straddles", "interest capitalization", "carrying charges"],
    ),
    TechnicalAuthority(
        citation="IRC §461(g)",
        authority_type="statute",
        title="Prepaid Interest / Points",
        year=1986,
        relevance="other capitalization — prepaid interest spread over the loan",
        key_holding="A cash-method taxpayer must charge prepaid interest to a capital account and "
                    "deduct it ratably over the loan period. Exception: points on debt to purchase/"
                    "improve a principal residence may be currently deductible.",
        taxpayer_favorable=False,
        weight="some",
        topics=["other_cap", "461(g)", "prepaid interest", "points", "principal residence"],
    ),
    TechnicalAuthority(
        citation="IRC §168(k) / §179",
        authority_type="statute",
        title="Bonus Depreciation and §179 Expensing (Cost Recovery)",
        year=2025,
        relevance="other capitalization — cost recovery of capitalized tangible property",
        key_holding="OBBBA permanently restored 100% bonus depreciation for qualified property "
                    "acquired and placed in service after 1/19/2025. §179 expensing limit is "
                    "$2,560,000 with a $4,090,000 phase-out threshold for 2026 (Rev. Proc. 2025-32).",
        taxpayer_favorable=True,
        weight="substantial",
        topics=["other_cap", "168(k)", "179", "bonus depreciation", "cost recovery", "OBBBA"],
    ),
    TechnicalAuthority(
        citation="INDOPCO, Inc. v. Commissioner, 503 U.S. 79 (1992)",
        authority_type="case_law",
        title="Future-Benefit Capitalization Doctrine",
        year=1992,
        relevance="capitalization doctrine — significant future benefit",
        key_holding="Creation of a separate and distinct asset is not a prerequisite to "
                    "capitalization; expenditures yielding significant future benefits must be "
                    "capitalized under §263(a). Later made administrable by Reg §§1.263(a)-4 and -5.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["263(a)", "INDOPCO", "future benefit", "intangibles", "transaction costs"],
    ),
]


# ---------------------------------------------------------------------------
# IRS LB&I Practice Units (§263A examiner guidance)
#
# Titles, types, dates, governing regs, process steps and examiner-focus items
# verified across IRS PDF snippets + KPMG/Bloomberg/Orbitax/Tax Adviser
# (current to 2026-06-30). Practice Units are training/audit roadmaps — NOT
# authoritative law and may not be cited as precedent. Exact alphanumeric DCNs
# print only on the (egress-blocked) PDF cover pages; where a DCN could not be
# independently confirmed it is flagged rather than fabricated.
# ---------------------------------------------------------------------------

PRACTICE_UNITS_263A = [
    {
        "title": "Interest Capitalization for Self-Constructed Assets",
        "unit_type": "LB&I Process Unit",
        "date": "rev. ~Feb 2021 (supersedes 5/29/2018, 3/13/2019, 1/27/2020 versions)",
        "dcn": "UIL IRC 263A; printed DCN on PDF cover — not independently verified",
        "regs": "Treas. Reg. §§1.263A-8 to -12 (avoided-cost method)",
        "topic": "interest",
        "process": (
            "Identify designated property -> determine unit of property -> determine "
            "production period (start = first physical production activity; end = ready to "
            "place in service / hold for sale) -> set computation period & measurement dates "
            "(>= quarterly when computation period is the tax year) -> identify eligible debt "
            "-> compute accumulated production expenditures (APE) per unit per date -> "
            "capitalize traced-debt interest first, then weighted-average nontraced rate on the "
            "excess-expenditure amount -> compute §481(a) on any Service-imposed method change."
        ),
        "key_points": (
            "Designated property = all real property; or tangible personal property with class "
            "life >= 20 yrs, or production period > 2 yrs, or > 1 yr & cost > $1M. NOT designated "
            "if production period <= 90 days AND total production expenditures <= $1,000,000 / "
            "number of production days."
        ),
        "examiner_focus": (
            "Failure to capitalize §263A(f) interest on self-constructed designated property; "
            "understated APE; improperly excluding property from designated-property scope; not "
            "applying traced debt first; too few measurement dates; shortened production period."
        ),
        "url": "https://www.irs.gov/pub/fatca/int_practice_units/interest_cap_self_construed.pdf",
        "current_note": (
            "Final regs TD 10034 (Oct 2, 2025) narrowed interest capitalization for IMPROVEMENTS "
            "to designated property and eliminated the associated-property rule — the 2021 unit "
            "is now partly superseded on those points."
        ),
        "favorable": False,
    },
    {
        "title": "Section 263A Costs for Self-Constructed Assets",
        "unit_type": "LB&I Concept Unit",
        "date": "posted 9/16/2021 (reflects final regs T.D. 9843, eff. TY on/after 11/20/2018)",
        "dcn": "UIL 263A.03-00 (Capitalization of Costs); printed DCN on PDF cover",
        "regs": "Treas. Reg. §1.263A-1 (general); §1.263A-2(a) (definition of produce)",
        "topic": "capitalization",
        "process": (
            "Determine whether the taxpayer produced a self-constructed asset (built for own use, "
            "not inventory) -> confirm 'produce' (build/install/manufacture/construct/develop/"
            "improve/create/raise/grow) -> capture the three cost buckets (§471 costs; additional "
            "§263A costs; §263A(f) interest) -> capitalize direct material + direct labor -> "
            "allocate indirect costs and mixed service costs to the asset -> confirm timing & "
            "cost recovery."
        ),
        "key_points": (
            "Three cost buckets: (1) §471 costs (non-interest costs capitalized on the financial "
            "statements); (2) additional §263A costs (required by §263A but not in §471 costs); "
            "(3) §263A(f) interest (cross-refs the interest unit). Mixed service costs allocated "
            "via the Simplified Service Cost Method (labor-based or production-cost ratio), with a "
            "90% de minimis all-or-nothing election."
        ),
        "examiner_focus": (
            "Whether produced property is identified; completeness of §471 vs additional §263A "
            "costs; proper allocation of indirect & mixed service costs; timing; cost recovery."
        ),
        "url": "https://www.irs.gov/pub/fatca/int_practice_units/self-constructed-assets.pdf",
        "current_note": "",
        "favorable": False,
    },
    {
        "title": "Producer's 263A Computation",
        "unit_type": "LB&I Process Unit",
        "date": "updated 11/22/2024 (supersedes 12/14/2020); focuses on SPM (pre-2018 final regs)",
        "dcn": "DCN COR-P-020 (corroborated; not visually confirmed)",
        "regs": "Treas. Reg. §1.263A-2(b)(3) (Simplified Production Method)",
        "topic": "producers",
        "process": (
            "Identify §471 costs and additional §263A costs -> determine additional §263A costs "
            "allocable to production -> apply the SPM absorption ratio to §471 costs in ending "
            "inventory -> test whether the allocation method is reasonable (service-dept and "
            "officer-comp allocations) -> apply §446/§481(a) method-change rules if needed."
        ),
        "key_points": (
            "SPM absorption ratio = additional §263A costs incurred / §471 costs incurred, "
            "multiplied by §471 costs remaining in ending inventory. Unit focuses on SPM and does "
            "not address the 11/20/2018 final regs (MSPM / negatives)."
        ),
        "examiner_focus": (
            "§471 vs additional §263A misclassification; missed service-dept and officer-comp "
            "allocations to production; absorption-ratio mechanics; unfiled method changes."
        ),
        "url": "https://www.irs.gov/pub/irs-lbi/producer-263A-computation.pdf",
        "current_note": "",
        "favorable": False,
    },
    {
        "title": "Modified Simplified Production Method (MSPM)",
        "unit_type": "LB&I Concept Unit",
        "date": "reflects final regs T.D. 9843 (eff. TY on/after 11/20/2018)",
        "dcn": "printed DCN on PDF cover — not independently verified",
        "regs": "Treas. Reg. §1.263A-2(c) (Modified Simplified Production Method)",
        "topic": "producers",
        "process": (
            "Separate additional §263A costs (incl. negatives) into pre-production and production "
            "pools -> compute the pre-production absorption ratio and the production absorption "
            "ratio -> apply each to the corresponding §471 costs remaining on hand at year-end."
        ),
        "key_points": (
            "Two-ratio method corrects the SPM's over-capitalization to raw materials. Capitalized "
            "= (pre-production ratio x pre-production §471 costs on hand) + (production ratio x "
            "production §471 costs on hand). Under the SPM, 'large producers' (avg annual gross "
            "receipts > $50M for the 3 prior years) may NOT include negative adjustments; under "
            "the MSPM they MAY. Historic Absorption Ratio (HAR) election available after 3 "
            "consecutive years on a simplified method (election statement, not a method change)."
        ),
        "examiner_focus": (
            "Correct pre-production vs production bifurcation (incl. negatives); ratios applied to "
            "the right §471 cost pools; the $50M negative-adjustment test; HAR eligibility."
        ),
        "url": "https://www.irs.gov/pub/fatca/int_practice_units/modified-simplified-production.pdf",
        "current_note": "",
        "favorable": False,
    },
    {
        "title": "Examining a Reseller's 263A Computation",
        "unit_type": "LB&I Process Unit",
        "date": "rev. 11/07/2024 (PDF) / 12/06/2024 (commentary), supersedes 9/17/2021",
        "dcn": "DCN COR-P-021 (corroborated; not visually confirmed)",
        "regs": "Treas. Reg. §1.263A-3 (property acquired for resale); Simplified Resale Method",
        "topic": "resellers",
        "process": (
            "Identify §471 costs first -> determine whether the taxpayer is properly a reseller and "
            "the extent of any production activities -> identify additional §263A costs (purchasing, "
            "storage, handling + their mixed service costs) -> capitalize to ending inventory via "
            "the Simplified Resale Method -> consider exceptions, self-constructed assets, and "
            "method-change implications."
        ),
        "key_points": (
            "SRM: additional §263A costs to ending inventory = §471 costs on hand x combined "
            "absorption ratio, where combined ratio = storage & handling ratio + purchasing ratio. "
            "Resellers with non-de-minimis production must use SPM/MSPM instead. De minimis "
            "production: producer-gross-receipts < 10% AND production-labor < 10% of totals. "
            "Purchasing-labor 1/3-2/3 rule; 90-10 dual-function storage rule; negatives permitted; "
            "HAR available after 3 consecutive SRM years."
        ),
        "examiner_focus": (
            "Improper SRM use despite production activity; understated §471 base; excluded "
            "purchasing/storage/handling costs; mis-applied 1/3-2/3 labor rule; missed "
            "self-constructed-asset capitalization; unsupported negatives / LIFO decrements."
        ),
        "url": "https://www.irs.gov/pub/fatca/int_practice_units/examining-reseller-irc263a.pdf",
        "current_note": "",
        "favorable": False,
    },
    {
        "title": "Alternative Method for Determining Section 471 Costs",
        "unit_type": "LB&I Concept Unit",
        "date": "reflects final regs (eff. TY on/after 11/20/2018)",
        "dcn": "printed DCN on PDF cover — not independently verified",
        "regs": "Treas. Reg. §1.263A-1(d)(2)(iii)",
        "topic": "capitalization",
        "process": (
            "Determine eligibility for the alternative method -> verify the taxpayer uses "
            "financial-statement inventory costs as its §471 costs -> confirm the resulting §471 / "
            "additional §263A split is correct."
        ),
        "key_points": (
            "Defines the §471-cost vs additional-§263A-cost dichotomy underlying all UNICAP "
            "computations. The alternative method lets eligible taxpayers treat book inventory "
            "costs as §471 costs instead of recomputing actual tax amounts; misclassification "
            "distorts the simplified-method absorption ratio."
        ),
        "examiner_focus": (
            "Eligibility; book-to-tax differences; consistency of the §471 vs additional §263A "
            "split (not used to under-absorb)."
        ),
        "url": "https://www.irs.gov/pub/fatca/int_practice_units/alternative-method-471-costs.pdf",
        "current_note": "",
        "favorable": False,
    },
    {
        "title": "IRC 481(a) Adjustment for IRC 263A Adjustments",
        "unit_type": "LB&I Concept Unit",
        "date": "publication date on PDF cover — not confirmed from snippets",
        "dcn": "printed DCN on PDF cover — not independently verified",
        "regs": "IRC §§446 / 481(a); Treas. Reg. §1.263A-7 (revaluing inventory)",
        "topic": "capitalization",
        "process": (
            "Identify whether the §263A method is permissible -> if impermissible, initiate an "
            "involuntary §446/§481(a) change -> recompute beginning/ending capitalized §263A costs "
            "under the correct method -> compute the §481(a) adjustment plus current-year effect."
        ),
        "key_points": (
            "§481(a) adjustment = beginning inventory under old §263A method - beginning inventory "
            "under new method; worked examples across FIFO/LIFO and non-inventory property."
        ),
        "examiner_focus": (
            "Identifying the method-change issue; §481(a) vs current-year adjustment; avoiding "
            "duplication/omission of capitalized costs."
        ),
        "url": "https://www.irs.gov/pub/fatca/irc-481a-adjustments-for-irc-263A.pdf",
        "current_note": "",
        "favorable": False,
    },
]


def _practice_units_as_authorities():
    """Expose the Practice Units as TechnicalAuthority records for search."""
    out = []
    for pu in PRACTICE_UNITS_263A:
        out.append(TechnicalAuthority(
            citation=f"IRS LB&I Practice Unit — {pu['title']}",
            authority_type="practice_unit",
            title=pu["title"],
            year=2024 if "2024" in pu["date"] else 2021,
            relevance=f"263A examiner guidance — {pu['topic']}",
            key_holding=pu["key_points"],
            facts_summary="Process: " + pu["process"],
            taxpayer_favorable=pu["favorable"],
            weight="some",  # sub-regulatory; not citable as precedent
            topics=["263A", "practice unit", pu["topic"]],
            url=pu["url"],
            notes=("Examiner focus: " + pu["examiner_focus"]
                   + ((" | " + pu["current_note"]) if pu["current_note"] else "")),
        ))
    return out


class CostCapAuthorityLookup(AuthorityLookup):
    """Lookup pre-loaded with the cost capitalization authority database."""

    def __init__(self):
        super().__init__(list(COST_CAPITALIZATION_AUTHORITIES)
                         + _practice_units_as_authorities())


# Module-level singleton for convenience
COST_CAP_LOOKUP = CostCapAuthorityLookup()
