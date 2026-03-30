"""Technical authorities for §197 intangible amortization.

Covers §197 15-year amortization of acquired intangibles, anti-churning
rules, self-created intangibles, goodwill, covenants not to compete,
customer-based intangibles, and related disposition rules.
"""

from .base import TechnicalAuthority

INTANGIBLES_197_AUTHORITIES = [
    # --- Core Statute ---
    TechnicalAuthority(
        citation="IRC §197(a)",
        authority_type="statute",
        title="§197 Amortization of Goodwill and Certain Other Intangibles",
        year=1993,
        relevance="15-year straight-line amortization for acquired §197 intangibles",
        key_holding="A taxpayer shall be entitled to an amortization deduction with respect to any amortizable §197 intangible. The amount of such deduction shall be determined by amortizing the adjusted basis of such intangible ratably over the 15-year period beginning with the month in which such intangible was acquired.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["197", "intangibles", "amortization", "15-year", "goodwill"],
    ),
    TechnicalAuthority(
        citation="IRC §197(d)",
        authority_type="statute",
        title="§197 Intangible — Definition",
        year=1993,
        relevance="Defines the categories of intangibles subject to §197",
        key_holding="Section 197 intangibles include: (1) goodwill, (2) going concern value, (3) workforce in place, (4) business books and records, (5) patents/copyrights/formulas/processes/designs/know-how, (6) customer-based intangibles, (7) supplier-based intangibles, (8) licenses/permits/rights granted by governmental units, (9) covenants not to compete, (10) franchises/trademarks/trade names.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["197", "intangibles", "goodwill", "covenant not to compete", "customer list"],
    ),
    TechnicalAuthority(
        citation="IRC §197(e)",
        authority_type="statute",
        title="§197 Exclusions — Self-Created and Certain Other Intangibles",
        year=1993,
        relevance="Certain intangibles excluded from §197 treatment",
        key_holding="Section 197 does NOT apply to: (1) interests in a corporation/partnership/trust, (2) interests under financial instruments, (3) interests in land, (4) most computer software (off-the-shelf: 3-year amortization under §167), (5) interests under existing leases of tangible property, (6) interests under existing indebtedness, (7) sports franchises, (8) mortgage servicing rights. Self-created intangibles are generally excluded unless they relate to customer-based intangibles, supplier-based intangibles, or certain other categories.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["197", "exclusions", "self-created", "software", "computer software"],
    ),
    TechnicalAuthority(
        citation="IRC §197(f)(1)",
        authority_type="statute",
        title="§197 — Treatment of Certain Dispositions",
        year=1993,
        relevance="Loss disallowed on disposition of §197 intangible if related intangibles retained",
        key_holding="If a taxpayer disposes of a §197 intangible and retains other §197 intangibles acquired in the same transaction, no loss is recognized. Instead, the adjusted basis of the disposed intangible is reallocated to the remaining §197 intangibles from that transaction.",
        facts_summary="This anti-loss rule prevents cherry-picking losses on individual intangibles while retaining related assets. Only when ALL §197 intangibles from a single acquisition are disposed of can a loss be recognized.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["197", "disposition", "loss disallowance", "anti-abuse"],
    ),
    TechnicalAuthority(
        citation="IRC §197(f)(9)",
        authority_type="statute",
        title="§197 Anti-Churning Rules",
        year=1993,
        relevance="Prevents amortization of intangibles held before §197 enactment via related-party transfers",
        key_holding="Anti-churning rules prevent a taxpayer from obtaining §197 amortization for intangibles that would not have been amortizable before §197's enactment (8/10/1993) through related-party transactions. Applies when intangible was held or used by taxpayer or related person at any time during the transition period, or if acquired from a related person.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["197", "anti-churning", "related party", "pre-1993"],
    ),

    # --- Regulations ---
    TechnicalAuthority(
        citation="Treas. Reg. §1.197-2(b)",
        authority_type="regulation",
        title="Amortizable §197 Intangibles — Detailed Rules",
        year=2000,
        relevance="Detailed rules for determining which intangibles qualify under §197",
        key_holding="An amortizable §197 intangible is a §197 intangible that is acquired by the taxpayer and held in connection with the conduct of a trade or business or an activity described in §212. Acquisition includes purchase, contribution to capital, and transfer at death. Created intangibles generally do not qualify unless specifically included (e.g., customer-based intangibles created through the acquisition of a trade or business).",
        taxpayer_favorable=True,
        weight="primary",
        topics=["197", "amortizable", "acquisition", "trade or business"],
    ),
    TechnicalAuthority(
        citation="Treas. Reg. §1.197-2(g)",
        authority_type="regulation",
        title="Treatment of Contingent Amounts — §197",
        year=2000,
        relevance="Rules for amortizing contingent purchase price allocable to §197 intangibles",
        key_holding="Contingent amounts paid for §197 intangibles are added to the basis of the intangible when paid or incurred. Amortization of additional amounts begins in the month the contingent amount is paid or incurred, over the remaining 15-year amortization period.",
        taxpayer_favorable=True,
        weight="primary",
        topics=["197", "contingent consideration", "earnout", "amortization"],
    ),

    # --- Case Law ---
    TechnicalAuthority(
        citation="Newark Morning Ledger Co. v. United States, 507 U.S. 546 (1993)",
        authority_type="case_law",
        title="Newark Morning Ledger — Pre-§197 Intangible Amortization",
        year=1993,
        relevance="Supreme Court held customer-based intangible could be amortized if limited useful life proven",
        key_holding="Before §197, the Supreme Court held that an intangible asset (newspaper subscriber list) was depreciable under §167 if the taxpayer could prove the asset had an ascertainable value separate from goodwill and a limited useful life that could be determined with reasonable accuracy. This case helped prompt Congress to enact §197.",
        facts_summary="Newark Morning Ledger purchased a newspaper business and allocated a portion of the purchase price to 'paid subscribers.' The IRS challenged the deduction, asserting the list was indistinguishable from goodwill. The Supreme Court reversed, holding the taxpayer proved the list had a determinable useful life.",
        taxpayer_favorable=True,
        weight="substantial",
        topics=["197", "intangibles", "customer list", "useful life", "goodwill"],
    ),
    TechnicalAuthority(
        citation="Frontier Chevrolet Co. v. Commissioner, T.C. Memo 2011-67",
        authority_type="case_law",
        title="Frontier Chevrolet — Auto Dealer Framework Agreement Not §197",
        year=2011,
        relevance="Dealer framework agreement with manufacturer was not an amortizable §197 intangible",
        key_holding="Tax Court held that an auto dealer's framework agreement with its manufacturer was not an amortizable §197 intangible because it was an interest under an existing contract (excluded under §197(e)(4)(B)) rather than a customer-based intangible or franchise.",
        taxpayer_favorable=False,
        weight="some",
        topics=["197", "franchise", "dealer agreement", "exclusion"],
    ),
    TechnicalAuthority(
        citation="Recovery Group, Inc. v. Commissioner, T.C. Memo 2010-76",
        authority_type="case_law",
        title="Recovery Group — Covenant Not to Compete Valuation",
        year=2010,
        relevance="Substance-over-form analysis of covenant not to compete allocations",
        key_holding="The Tax Court scrutinized the allocation of purchase price to a covenant not to compete, requiring economic substance and enforceable restrictive terms. Nominal or unreasonable allocations to covenants will be recharacterized. The covenant must have independent economic significance apart from goodwill.",
        taxpayer_favorable=False,
        weight="some",
        topics=["197", "covenant not to compete", "valuation", "allocation"],
    ),
]
