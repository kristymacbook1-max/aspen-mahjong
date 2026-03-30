"""Technical authorities for §267 related party matching rules.

Covers deduction deferral for payments to related parties, constructive
ownership, and the matching principle.
"""

from .base import TechnicalAuthority

RELATED_PARTY_AUTHORITIES = [
    TechnicalAuthority(
        citation="IRC §267(a)(2)",
        authority_type="statute",
        title="Related Party Matching Rule",
        year=1986,
        relevance="Core matching rule — deduction deferred until amount includible by related payee",
        key_holding="If an accrual-method payor and cash-method payee are related persons under §267(b), and the payee does not include the amount in income in the payee's taxable year ending within or with the payor's taxable year, the payor's deduction is deferred until the payee's taxable year in which the amount is includible.",
        facts_summary="Prevents related-party mismatch: payor accrues deduction but related payee doesn't include in income. Deduction deferred until matching.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["267", "related party", "matching rule", "deduction deferral"],
    ),
    TechnicalAuthority(
        citation="IRC §267(a)(3)",
        authority_type="statute",
        title="Payments to Foreign Related Persons",
        year=1986,
        relevance="Deduction for payments to foreign related persons — deferred until paid",
        key_holding="If the person to whom the payment is to be made is a foreign person, no deduction shall be allowed until paid. All-events and EP tests irrelevant for this purpose.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["267", "foreign related party", "deduction deferral"],
    ),
    TechnicalAuthority(
        citation="IRC §267(b)",
        authority_type="statute",
        title="Related Persons Defined",
        year=1986,
        relevance="Definition of related persons — direct and constructive ownership",
        key_holding="Related persons include: members of a family (§267(c)(4)), individual and >50%-owned corporation, two corporations in the same controlled group, grantor and fiduciary, fiduciary and beneficiary, corporation and partnership with >50% common ownership, S corp and >2% shareholder, and others.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["267", "related persons", "constructive ownership", "controlled group"],
    ),
    TechnicalAuthority(
        citation="IRC §267(c)",
        authority_type="statute",
        title="Constructive Ownership Rules",
        year=1986,
        relevance="Constructive ownership — attribution rules for determining related-party status",
        key_holding="Stock owned directly or indirectly by or for a corporation, partnership, estate, or trust is constructively owned proportionately by shareholders, partners, or beneficiaries. Family attribution: stock owned by siblings, spouse, ancestors, and lineal descendants.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["267", "constructive ownership", "attribution"],
    ),
    TechnicalAuthority(
        citation="IRC §267(e)",
        authority_type="statute",
        title="Special Rules for Pass-Through Entities",
        year=1986,
        relevance="§267 applies to partnerships and their partners/related persons",
        key_holding="If a deduction is allowable to a partnership and the person to whom the payment is made is a partner or related to a partner, the matching rule of §267(a)(2) applies.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["267", "partnership", "pass-through", "partner deductions"],
    ),

    # --- Regulations ---
    TechnicalAuthority(
        citation="Treas. Reg. §1.267(a)-2(c)",
        authority_type="regulation",
        title="Unpaid Expenses — Related Persons",
        year=1957,
        relevance="Mechanics of deduction deferral for unpaid related-party expenses",
        key_holding="If an accrual-method taxpayer and a related person use different taxable years, the accrual-method taxpayer cannot deduct the expense until the taxable year of the related payee in which the amount is includible in income.",
        taxpayer_favorable=False,
        weight="primary",
        topics=["267", "unpaid expenses", "deferral mechanics"],
    ),

    # --- Case Law ---
    TechnicalAuthority(
        citation="Holdcroft Transportation Co. v. Commissioner, 153 F.2d 323 (8th Cir. 1946)",
        authority_type="case_law",
        title="Holdcroft — Related Party Deduction Disallowed",
        year=1946,
        relevance="Early case applying §267 loss disallowance between related parties",
        key_holding="Losses on transactions between related parties are disallowed under §267(a)(1). The relationship between the parties, not the economic substance of the transaction, controls.",
        taxpayer_favorable=False,
        weight="substantial",
        topics=["267", "loss disallowance", "related party"],
    ),
    TechnicalAuthority(
        citation="Shea Co. v. Commissioner, T.C. Memo 2007-15",
        authority_type="case_law",
        title="Shea — §267 Applied to Bonus Accruals",
        year=2007,
        relevance="§267 matching applied to deferred compensation between related parties",
        key_holding="Bonus accruals by partnership to related individuals were subject to §267(a)(2) matching. Deduction deferred until amounts included in payees' income.",
        taxpayer_favorable=False,
        weight="some",
        topics=["267", "bonus accrual", "partnership", "compensation"],
    ),

    # --- IRS Guidance ---
    TechnicalAuthority(
        citation="Rev. Rul. 2008-29, 2008-1 C.B. 1149",
        authority_type="rev_rul",
        title="§267 and Employee Bonus Accruals",
        year=2008,
        relevance="Bonus accruals to >50% owner-employees subject to §267",
        key_holding="If an accrual-method employer accrues a bonus to an employee who is a >50% owner (and thus a related party under §267), the deduction is deferred until the bonus is paid and included in the employee's income. The 2½-month rule of §404(a)(5) also applies.",
        taxpayer_favorable=False,
        weight="substantial",
        topics=["267", "bonus accrual", "owner-employee", "2.5 month rule"],
    ),
    TechnicalAuthority(
        citation="CCA 201024023",
        authority_type="cca",
        title="§267 Constructive Ownership — Partnership Context",
        year=2010,
        relevance="Constructive ownership in partnership structures",
        key_holding="In determining related-party status under §267, stock ownership is attributed through partnerships under §267(c)(1). A partner's proportionate share of partnership-owned stock is attributed to the partner.",
        taxpayer_favorable=False,
        weight="some",
        topics=["267", "constructive ownership", "partnership", "attribution"],
    ),
]
