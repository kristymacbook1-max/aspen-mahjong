"""Analyzes taxpayer facts to identify available revenue recognition methods,
supporting technical authorities, and generates technical position memos."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

from .authorities.base import AuthorityLookup, TechnicalAuthority
from .authority_database import get_authority_lookup


@dataclass
class TaxPosition:
    position_id: str
    title: str
    issue: str
    conclusion: str
    confidence_level: str  # should, more_likely_than_not, reasonable_basis
    tax_impact: Decimal
    authorities_supporting: List[str]  # citations
    authorities_adverse: List[str]
    analysis: str  # 3-5 paragraph technical analysis
    risk_assessment: str
    disclosure_required: bool
    form_8275_needed: bool
    method_change_required: bool
    recommended_action: str
    facts: str


@dataclass
class TechnicalMemo:
    title: str
    date: str
    taxpayer_name: str
    tax_year: int
    prepared_by: str
    issues: List[str]
    facts: str
    positions: List[TaxPosition]
    overall_recommendation: str
    filing_requirements: List[str]


def _cites(auths: List[TechnicalAuthority]) -> List[str]:
    return [a.citation for a in auths]


def _memo(issue: str, law: str, application: str, conclusion: str) -> str:
    return f"{issue}\n\n{law}\n\n{application}\n\n{conclusion}"


def _pos(pid, title, issue, conclusion, confidence, impact, sup, adv,
         analysis, risk, disclosure=False, f8275=False, mc_req=False,
         action="", facts=""):
    return TaxPosition(
        position_id=pid, title=title, issue=issue, conclusion=conclusion,
        confidence_level=confidence, tax_impact=impact,
        authorities_supporting=_cites(sup), authorities_adverse=_cites(adv),
        analysis=analysis, risk_assessment=risk,
        disclosure_required=disclosure, form_8275_needed=f8275,
        method_change_required=mc_req, recommended_action=action, facts=facts)


class PositionAnalyzer:
    """Identifies available tax positions and drafts technical memos."""

    def __init__(self, authority_lookup: Optional[AuthorityLookup] = None):
        self.lookup = authority_lookup or get_authority_lookup()

    def analyze_advance_payments(self, progress_collections: list,
                                 tax_year: int, company_name: str = "") -> List[TaxPosition]:
        positions: List[TaxPosition] = []
        tp = company_name or "taxpayer"
        idx = 0
        for pc in progress_collections:
            if not pc.is_advance_payment_under_451:
                continue
            idx += 1
            auth = self.lookup.for_position(["advance_payments", "451c"])
            sup, adv = auth["supporting"], auth["adverse"]
            amt = pc.amount_current
            conf = "should" if sup else "more_likely_than_not"
            analysis = _memo(
                f"The issue is whether {tp}'s {pc.name} progress collections "
                f"of ${amt:,.0f} qualify as advance payments eligible for "
                "deferral under IRC \u00a7451(c) and Treas. Reg. \u00a71.451-8.",
                "Under IRC \u00a7451(c), an accrual-method taxpayer may elect to "
                "defer the inclusion of advance payments to the extent they are "
                "not recognized in revenue in the taxable year of receipt. "
                "Treas. Reg. \u00a71.451-8 defines an advance payment as a "
                "payment received for goods, services, or other specified items "
                "before the taxpayer satisfies the related income inclusion obligation.",
                f"The {pc.name} collections represent payments received before "
                "the taxpayer has fulfilled its performance obligation. Because "
                "the payments are for goods or services to be provided in a "
                "future period, they satisfy the regulatory definition of "
                f"advance payments. The deferral method elected is '{pc.deferral_method}'.",
                f"It is our conclusion that the {pc.name} collections qualify "
                "as advance payments under \u00a7451(c) and are eligible for "
                "deferral under Treas. Reg. \u00a71.451-8.")
            positions.append(_pos(
                f"AP-{tax_year}-{idx:03d}",
                f"\u00a7451(c) Deferral \u2013 {pc.name}",
                f"Whether {pc.name} qualifies for deferral under \u00a7451(c)",
                "Eligible for deferral under \u00a7451(c).", conf, amt, sup, adv,
                analysis, "Low" if conf == "should" else "Moderate",
                mc_req=not pc.method_change_filed,
                action=("File Form 3115 to adopt the deferral method."
                        if not pc.method_change_filed
                        else "Continue applying the deferral method."),
                facts=f"{pc.name}: current balance ${amt:,.0f}, "
                      f"refundable={pc.is_refundable}, "
                      f"deferral_method={pc.deferral_method}."))
            if pc.method_change_filed:
                mc = self.lookup.for_position(["method_change", "451c"])
                positions.append(_pos(
                    f"AP-MC-{tax_year}-{idx:03d}",
                    f"Form 3115 / \u00a7481(a) Adjustment \u2013 {pc.name}",
                    "Whether the \u00a7481(a) adjustment is properly computed",
                    "\u00a7481(a) adjustment is supportable.", "should",
                    Decimal("0"), mc["supporting"], mc["adverse"],
                    _memo(
                        f"The issue is whether the \u00a7481(a) adjustment "
                        f"arising from {tp}'s adoption of the deferral method "
                        "for advance payments is properly computed.",
                        "Under \u00a7481(a), a taxpayer that changes its method "
                        "of accounting must take into account adjustments "
                        "necessary to prevent duplication or omission of income. "
                        "Rev. Proc. 2024-23 provides automatic consent procedures.",
                        f"The Form 3115 filed for {pc.name} reported a "
                        f"\u00a7481(a) adjustment. The change was filed in "
                        f"{pc.method_change_year or tax_year} under the "
                        "automatic consent procedures.",
                        "The \u00a7481(a) adjustment is properly computed and "
                        "the method change is effective."),
                    "Low", action="Verify Form 3115 was timely filed.",
                    facts=f"Method change filed: {pc.form_3115_reference}."))
        return positions

    def analyze_slot_reservations(self, progress_collections: list,
                                  tax_year: int, company_name: str = "") -> List[TaxPosition]:
        positions: List[TaxPosition] = []
        tp = company_name or "taxpayer"
        idx = 0
        for pc in progress_collections:
            if pc.is_advance_payment_under_451:
                continue
            idx += 1
            auth = self.lookup.for_position(["deposits", "slot_reservations"])
            sup, adv = auth["supporting"], auth["adverse"]
            amt = pc.amount_current
            conf = "more_likely_than_not" if sup else "reasonable_basis"
            ref = "refundable" if pc.is_refundable else "nonrefundable"
            analysis = _memo(
                f"The issue is whether {tp}'s {pc.name} collections of "
                f"${amt:,.0f} are deposits or advance payments subject to "
                "immediate inclusion.",
                "Under the Indianapolis Power framework, a payment is a "
                "deposit (not income) if the taxpayer has an unrestricted "
                "obligation to repay and lacks complete dominion over the "
                "funds. If the payment secures a right to purchase rather "
                "than constituting prepayment for goods or services, it is "
                "not an advance payment under \u00a7451(c).",
                f"The {pc.name} collections are characterized as {ref} "
                "payments that secure a production slot. Because these "
                "payments do not constitute prepayment for goods or services, "
                "they fall outside the definition of advance payments under "
                "Treas. Reg. \u00a71.451-8.",
                f"The {pc.name} collections are subject to immediate inclusion "
                "in gross income under the claim-of-right doctrine, as the "
                "taxpayer exercises dominion and control upon receipt.")
            is_rb = conf == "reasonable_basis"
            positions.append(_pos(
                f"SR-{tax_year}-{idx:03d}",
                f"Immediate Inclusion \u2013 {pc.name}",
                f"Whether {pc.name} is a deposit or includible income",
                "Includible in income upon receipt.", conf, amt, sup, adv,
                analysis,
                "Moderate" if conf == "more_likely_than_not" else "Elevated",
                disclosure=is_rb, f8275=is_rb,
                action="Include in income upon receipt.",
                facts=f"{pc.name}: ${amt:,.0f}, refundable={pc.is_refundable}, "
                      f"transferable={pc.is_transferable}."))
            if pc.triggers_migration:
                positions.append(_pos(
                    f"SR-MIG-{tax_year}-{idx:03d}",
                    f"Migration to Advance Payment \u2013 {pc.name}",
                    f"Whether {pc.name} migrates to advance payment status",
                    "Migration occurs upon trigger event.", "more_likely_than_not",
                    Decimal("0"), sup, adv,
                    _memo(
                        f"The issue is whether {pc.name} collections convert to "
                        "advance payments upon the occurrence of the migration "
                        f"trigger: {pc.migration_trigger}.",
                        "No specific statutory provision addresses the migration "
                        "of deposits to advance payments. However, general "
                        "principles suggest that the character of a payment is "
                        "determined by the rights and obligations at the time "
                        "of receipt.",
                        f"Upon {pc.migration_trigger}, the nature of the "
                        f"{pc.name} payment changes from a slot reservation to "
                        "a prepayment for goods, potentially qualifying for "
                        "\u00a7451(c) deferral.",
                        "The migration should be respected and the payment "
                        "reclassified as an advance payment eligible for "
                        "deferral going forward."),
                    "Moderate", disclosure=True, mc_req=True,
                    action="Monitor migration trigger and file Form 3115 "
                           "when migration occurs.",
                    facts=f"Migration trigger: {pc.migration_trigger}."))
        return positions

    def analyze_long_term_contracts(self, has_ltc: bool, company_name: str = "",
                                    tax_year: int = 0) -> List[TaxPosition]:
        if not has_ltc:
            return []
        auth = self.lookup.for_position(["long_term_contracts"])
        sup, adv = auth["supporting"], auth["adverse"]
        tp = company_name or "Taxpayer"
        pcm = _pos(
            f"LTC-PCM-{tax_year}-001", "PCM Requirement for Long-Term Contracts",
            "Whether contracts must use the percentage-of-completion method",
            "PCM is required under \u00a7460(a).", "should", Decimal("0"), sup, adv,
            _memo(
                f"The issue is whether {tp}'s long-term contracts must be "
                "accounted for under the percentage-of-completion method (PCM).",
                "IRC \u00a7460(a) generally requires that income from long-term "
                "contracts be determined under the PCM. A long-term contract is "
                "one for the manufacture, building, installation, or construction "
                "of property that is not completed within the taxable year.",
                f"{tp} enters into contracts spanning more than one taxable year "
                "for the manufacture of property. These contracts meet the "
                "definition of long-term contracts under \u00a7460(e).",
                "PCM is required under \u00a7460(a)."),
            "Low", action="Apply PCM to all qualifying long-term contracts.",
            facts=f"{company_name} has long-term contracts subject to \u00a7460.")
        exception = _pos(
            f"LTC-SCE-{tax_year}-002", "Small Contractor Exception",
            "Whether the small contractor exception under \u00a7460(e)(1)(B) applies",
            "Evaluate gross receipts for eligibility.", "more_likely_than_not",
            Decimal("0"), sup, adv,
            _memo(
                "The issue is whether the taxpayer qualifies for the small "
                "contractor exception from the PCM requirement.",
                "Under \u00a7460(e)(1)(B), a contract is exempt from PCM if it "
                "is expected to be completed within two years and the taxpayer's "
                "average annual gross receipts for the three preceding taxable "
                "years do not exceed $29 million (adjusted for inflation).",
                "The taxpayer must verify that its average annual gross receipts "
                "satisfy the threshold and that the contracts are expected to "
                "be completed within two years.",
                "If the gross receipts test is met, the exception permits use "
                "of an exempt method such as CCM."),
            "Moderate", action="Verify gross receipts threshold for eligibility.",
            facts="Small contractor exception analysis.")
        lookback = _pos(
            f"LTC-LBI-{tax_year}-003",
            "Look-Back Interest under \u00a7460(b)(2)",
            "Whether look-back interest applies to completed contracts",
            "Look-back interest computation required.", "should", Decimal("0"),
            sup, adv,
            _memo(
                "The issue is whether the taxpayer must compute look-back "
                "interest under \u00a7460(b)(2).",
                "\u00a7460(b)(2) requires a taxpayer using PCM to recompute "
                "contract income upon completion using actual costs and pay or "
                "receive interest on the resulting tax adjustment.",
                "For each long-term contract completed during the year, the "
                "taxpayer must apply Form 8697 to compute look-back interest "
                "based on the difference between estimated and actual "
                "allocation of contract price.",
                "Look-back interest applies and Form 8697 must be filed."),
            "Low", action="File Form 8697 for completed contracts.",
            facts="Look-back interest computation for completed LTCs.")
        return [pcm, exception, lookback]

    def analyze_method_changes(self, current_method: str, proposed_method: str,
                               estimated_481a: Decimal = Decimal("0"),
                               company_name: str = "",
                               tax_year: int = 0) -> List[TaxPosition]:
        auth = self.lookup.for_position(["method_change"])
        sup, adv = auth["supporting"], auth["adverse"]
        tp = company_name or "Taxpayer"
        spread_app = (
            "Because the adjustment is negative, it is taken in full in the "
            "year of change." if estimated_481a < 0 else
            "Because the adjustment is positive, it is spread ratably over "
            "four taxable years beginning with the year of change.")
        consent = _pos(
            f"MC-CON-{tax_year}-001",
            f"Method Change: {current_method} to {proposed_method}",
            "Whether automatic or non-automatic consent is required",
            "Automatic consent under Rev. Proc. 2024-23.", "should",
            estimated_481a, sup, adv,
            _memo(
                f"The issue is whether {tp}'s change from {current_method} to "
                f"{proposed_method} qualifies for automatic consent.",
                "Under \u00a7446(e), a taxpayer changing its method of "
                "accounting must obtain the Commissioner's consent. Rev. Proc. "
                "2024-23 provides a list of automatic changes that do not "
                "require advance consent.",
                f"The proposed change from {current_method} to "
                f"{proposed_method} should be reviewed against the designated "
                "automatic change numbers in Rev. Proc. 2024-23 to confirm "
                "eligibility for automatic consent.",
                "If the change is listed, automatic consent applies and "
                "Form 3115 is filed with the timely-filed return."),
            "Low", mc_req=True,
            action="File Form 3115 with timely-filed return.",
            facts=f"Change from {current_method} to {proposed_method}.")
        spread = _pos(
            f"MC-481-{tax_year}-002",
            "\u00a7481(a) Adjustment Spread Period",
            "Whether the \u00a7481(a) adjustment is spread or taken in full",
            "Negative adjustments taken in year 1; positive adjustments "
            "spread over 4 years.", "should", estimated_481a, sup, adv,
            _memo(
                "The issue is the proper spread period for the \u00a7481(a) "
                f"adjustment of ${estimated_481a:,.0f}.",
                "Under \u00a7481(a) and Rev. Proc. 2024-23, a negative "
                "\u00a7481(a) adjustment is taken into account entirely in "
                "the year of change. A positive adjustment is generally "
                "spread ratably over four taxable years.",
                f"The estimated \u00a7481(a) adjustment is "
                f"${estimated_481a:,.0f}. {spread_app}",
                "The spread period is properly applied."),
            "Low", mc_req=True,
            action="Compute \u00a7481(a) adjustment and apply spread.",
            facts=f"Estimated \u00a7481(a): ${estimated_481a:,.0f}.")
        audit = _pos(
            f"MC-AUD-{tax_year}-003",
            "Audit Protection for Method Change",
            "Whether audit protection is available",
            "Audit protection generally available for automatic changes.",
            "should", Decimal("0"), sup, adv,
            _memo(
                "The issue is whether audit protection is available.",
                "Rev. Proc. 2024-23 \u00a79.01 provides that the IRS will not "
                "require a taxpayer to change its method for a prior taxable "
                "year if the taxpayer files a timely Form 3115 for an "
                "automatic change.",
                f"{tp} intends to file Form 3115 under the automatic consent "
                "procedures. Provided the form is timely and properly filed, "
                "audit protection should be available for prior taxable years.",
                "Audit protection is available."),
            "Low", mc_req=True,
            action="Ensure Form 3115 is timely filed for audit protection.",
            facts="Audit protection analysis.")
        return [consent, spread, audit]

    def generate_technical_memo(self, company_name: str, tax_year: int,
                                positions: List[TaxPosition],
                                facts_summary: str) -> TechnicalMemo:
        filing_reqs: List[str] = []
        if any(p.method_change_required for p in positions):
            filing_reqs.append("Form 3115 (Application for Change in Accounting Method)")
        if any(p.form_8275_needed for p in positions):
            filing_reqs.append("Form 8275 (Disclosure Statement)")
        if any("8697" in p.recommended_action for p in positions):
            filing_reqs.append("Form 8697 (Interest Computation Under the Look-Back Method)")
        high_risk = any(p.risk_assessment in ("Elevated", "High") for p in positions)
        overall = (
            "Proceed with caution. Certain positions carry elevated risk and "
            "may require additional disclosure or documentation." if high_risk
            else "All identified positions are well-supported by technical "
                 "authority. Recommend proceeding with the positions as outlined.")
        return TechnicalMemo(
            title=f"Revenue Recognition Technical Position Memo \u2013 {company_name}",
            date="", taxpayer_name=company_name, tax_year=tax_year,
            prepared_by="Position Analyzer (automated)",
            issues=[p.issue for p in positions], facts=facts_summary,
            positions=positions, overall_recommendation=overall,
            filing_requirements=filing_reqs)

    def analyze_all(self, ten_k_data=None, company_name: str = "",
                    tax_year: int = 0) -> TechnicalMemo:
        from ..phase1.ten_k_analyzer import TenKInput
        all_positions: List[TaxPosition] = []
        facts_parts: List[str] = []
        name, year = company_name, tax_year
        if ten_k_data is not None and isinstance(ten_k_data, TenKInput):
            name = company_name or ten_k_data.company.name
            year = tax_year or ten_k_data.company.fiscal_year_end_year
            pcs = ten_k_data.deferred_revenue.progress_collections
            if pcs:
                facts_parts.append(f"{name} has {len(pcs)} progress collection categories.")
                all_positions.extend(self.analyze_advance_payments(pcs, year, name))
                all_positions.extend(self.analyze_slot_reservations(pcs, year, name))
            has_ltc = any("long-term" in s.name.lower() or "long term" in s.name.lower()
                          for s in ten_k_data.revenue_streams)
            if has_ltc:
                facts_parts.append(f"{name} has long-term contract revenue.")
                all_positions.extend(self.analyze_long_term_contracts(True, name, year))
        if not all_positions:
            facts_parts.append("No specific positions identified from data.")
        return self.generate_technical_memo(
            company_name=name, tax_year=year, positions=all_positions,
            facts_summary=" ".join(facts_parts))
