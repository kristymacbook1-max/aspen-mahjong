"""Phase 1 Partnership Tax Analyzer — Public Data / K-1 Analysis.

Analyzes partnership tax provisions including §704(b) allocations,
§704(c) contributed property, §754/§743(b) basis adjustments,
§707 disguised sales, §751 hot assets, and distribution rules.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional, Dict
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from revenue_recognition.utils.currency_helpers import (
    to_decimal, round_currency, format_currency, format_millions, pct_change,
)
from revenue_recognition.utils.entity_types import get_entity_config


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PartnershipProfile:
    name: str
    ein: str = ""
    entity_type: str = "partnership"
    fiscal_year_end: str = "12/31"
    tax_year: int = 2024
    total_assets: Decimal = Decimal("0")
    industry: str = ""
    has_754_election: bool = False
    is_bba_partnership: bool = True
    number_of_partners: int = 0


@dataclass
class PartnerInfo:
    """Individual partner data."""
    name: str
    partner_type: str = "general"  # general / limited / managing_member
    entity_type: str = "individual"  # individual / c_corp / partnership / s_corp / trust
    ownership_pct: Decimal = Decimal("0")
    profit_pct: Decimal = Decimal("0")
    loss_pct: Decimal = Decimal("0")
    capital_account_beginning: Decimal = Decimal("0")
    capital_account_ending: Decimal = Decimal("0")
    outside_basis: Decimal = Decimal("0")
    share_of_recourse_liabilities: Decimal = Decimal("0")
    share_of_nonrecourse_liabilities: Decimal = Decimal("0")
    share_of_qnr_liabilities: Decimal = Decimal("0")
    is_related_party: bool = False


@dataclass
class ContributedProperty:
    """§704(c) contributed property with built-in gain/loss."""
    description: str
    contributing_partner: str = ""
    date_contributed: str = ""
    fmv_at_contribution: Decimal = Decimal("0")
    tax_basis_at_contribution: Decimal = Decimal("0")
    current_book_value: Decimal = Decimal("0")
    current_tax_basis: Decimal = Decimal("0")
    section_704c_method: str = ""  # traditional / curative / remedial
    remaining_builtin_gain: Decimal = Decimal("0")
    remaining_builtin_loss: Decimal = Decimal("0")
    property_type: str = ""  # real_property / personal_property / intangible


@dataclass
class PartnershipAllocation:
    """K-1 allocation items."""
    item_description: str
    total_amount: Decimal = Decimal("0")
    allocation_type: str = "income"  # income / gain / loss / deduction / credit
    has_special_allocation: bool = False
    special_allocation_rationale: str = ""


@dataclass
class PartnershipDistribution:
    """Distribution to partner."""
    partner_name: str
    distribution_type: str = "operating"  # operating / liquidating / guaranteed_payment
    cash_distributed: Decimal = Decimal("0")
    property_fmv: Decimal = Decimal("0")
    property_basis: Decimal = Decimal("0")
    is_in_kind: bool = False


@dataclass
class Phase1PartnershipInput:
    partnership: PartnershipProfile = field(default_factory=PartnershipProfile)
    partners: List[PartnerInfo] = field(default_factory=list)
    contributed_properties: List[ContributedProperty] = field(default_factory=list)
    allocations: List[PartnershipAllocation] = field(default_factory=list)
    distributions: List[PartnershipDistribution] = field(default_factory=list)
    total_partnership_income: Decimal = Decimal("0")
    total_partnership_assets_book: Decimal = Decimal("0")
    total_partnership_assets_tax: Decimal = Decimal("0")
    total_liabilities: Decimal = Decimal("0")
    recourse_liabilities: Decimal = Decimal("0")
    nonrecourse_liabilities: Decimal = Decimal("0")


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class PartnershipTaxAnalyzer:
    """Phase 1 analyzer for partnership tax provisions."""

    def analyze(self, inp: Phase1PartnershipInput) -> dict:
        self._input = inp

        allocations = self._analyze_allocations()
        sec704c = self._analyze_section_704c()
        basis_adj = self._analyze_basis_adjustments()
        distributions = self._analyze_distributions()
        hot_assets = self._analyze_hot_assets()
        liabilities = self._analyze_liabilities()
        findings = self._generate_findings(allocations, sec704c, basis_adj, distributions, hot_assets, liabilities)
        roadmap = self._generate_phase2_recommendations(findings)

        return {
            "partnership": inp.partnership,
            "allocation_analysis": allocations,
            "section_704c_analysis": sec704c,
            "basis_adjustment_analysis": basis_adj,
            "distribution_analysis": distributions,
            "hot_asset_analysis": hot_assets,
            "liability_analysis": liabilities,
            "findings": findings,
            "phase2_roadmap": roadmap,
        }

    def _analyze_allocations(self) -> dict:
        """Analyze §704(b) allocations for substantial economic effect."""
        items = []
        total_special = Decimal("0")

        for alloc in self._input.allocations:
            amt = to_decimal(alloc.total_amount)
            items.append({
                "description": alloc.item_description,
                "amount": amt,
                "type": alloc.allocation_type,
                "has_special_allocation": alloc.has_special_allocation,
                "rationale": alloc.special_allocation_rationale,
                "see_test": "Must satisfy substantial economic effect or be in accordance with PIP" if alloc.has_special_allocation else "Pro rata allocation — generally acceptable",
            })
            if alloc.has_special_allocation:
                total_special += abs(amt)

        return {
            "items": items,
            "total_allocations": sum(to_decimal(a["amount"]) for a in items),
            "special_allocation_count": sum(1 for a in items if a["has_special_allocation"]),
            "total_special_allocations": total_special,
            "count": len(items),
        }

    def _analyze_section_704c(self) -> dict:
        """Analyze §704(c) contributed property with built-in gain/loss."""
        items = []
        total_builtin_gain = Decimal("0")
        total_builtin_loss = Decimal("0")

        for prop in self._input.contributed_properties:
            fmv = to_decimal(prop.fmv_at_contribution)
            basis = to_decimal(prop.tax_basis_at_contribution)
            builtin = fmv - basis
            remaining = to_decimal(prop.remaining_builtin_gain) - to_decimal(prop.remaining_builtin_loss)

            items.append({
                "description": prop.description,
                "contributing_partner": prop.contributing_partner,
                "fmv_at_contribution": fmv,
                "tax_basis": basis,
                "initial_builtin": builtin,
                "remaining_builtin": remaining,
                "method": prop.section_704c_method or "traditional",
                "property_type": prop.property_type,
                "ceiling_rule_risk": prop.section_704c_method == "traditional" and builtin > Decimal("0"),
            })

            if builtin > Decimal("0"):
                total_builtin_gain += builtin
            else:
                total_builtin_loss += abs(builtin)

        return {
            "items": items,
            "total_builtin_gain": total_builtin_gain,
            "total_builtin_loss": total_builtin_loss,
            "net_builtin": total_builtin_gain - total_builtin_loss,
            "count": len(items),
            "has_ceiling_rule_risk": any(i["ceiling_rule_risk"] for i in items),
        }

    def _analyze_basis_adjustments(self) -> dict:
        """Analyze §754 election and §743(b)/§734(b) basis adjustments."""
        partnership = self._input.partnership
        has_754 = partnership.has_754_election
        book_assets = to_decimal(self._input.total_partnership_assets_book)
        tax_assets = to_decimal(self._input.total_partnership_assets_tax)
        book_tax_diff = book_assets - tax_assets

        # Check for substantial built-in loss (mandatory §743(b) adjustment)
        substantial_bil = tax_assets > book_assets and (tax_assets - book_assets) > Decimal("250000")

        return {
            "has_754_election": has_754,
            "book_assets": book_assets,
            "tax_assets": tax_assets,
            "book_tax_difference": book_tax_diff,
            "substantial_built_in_loss": substantial_bil,
            "mandatory_743b_note": "Mandatory §743(b) adjustment required regardless of §754 election — substantial built-in loss exceeds $250K" if substantial_bil else None,
            "recommendation": (
                "§754 election is in effect — §743(b) adjustments required on transfers"
                if has_754
                else "Consider §754 election to allow basis step-up on partner transfers/deaths"
            ),
        }

    def _analyze_distributions(self) -> dict:
        """Analyze distributions for gain recognition and disguised sale risk."""
        items = []
        total_cash = Decimal("0")
        total_property = Decimal("0")
        disguised_sale_risk = []

        for dist in self._input.distributions:
            cash = to_decimal(dist.cash_distributed)
            prop_fmv = to_decimal(dist.property_fmv)
            prop_basis = to_decimal(dist.property_basis)

            # Find partner's outside basis
            partner_basis = Decimal("0")
            for p in self._input.partners:
                if p.name == dist.partner_name:
                    partner_basis = to_decimal(p.outside_basis)
                    break

            gain_recognized = max(Decimal("0"), cash - partner_basis) if cash > partner_basis else Decimal("0")

            items.append({
                "partner": dist.partner_name,
                "type": dist.distribution_type,
                "cash": cash,
                "property_fmv": prop_fmv,
                "property_basis": prop_basis,
                "partner_outside_basis": partner_basis,
                "gain_recognized": gain_recognized,
                "is_in_kind": dist.is_in_kind,
            })
            total_cash += cash
            total_property += prop_fmv

        return {
            "items": items,
            "total_cash_distributed": total_cash,
            "total_property_distributed": total_property,
            "total_gain_recognized": sum(to_decimal(i["gain_recognized"]) for i in items),
            "count": len(items),
        }

    def _analyze_hot_assets(self) -> dict:
        """Identify §751 hot assets (unrealized receivables and inventory)."""
        # In Phase 1, we flag the presence of potential hot assets based on partnership profile
        has_receivables = any(
            a.allocation_type == "income" and "receivable" in a.item_description.lower()
            for a in self._input.allocations
        )
        has_inventory = any(
            "inventory" in a.item_description.lower()
            for a in self._input.allocations
        )

        return {
            "has_potential_hot_assets": has_receivables or has_inventory,
            "has_unrealized_receivables": has_receivables,
            "has_inventory_items": has_inventory,
            "note": "§751(a) applies to sales/exchanges; §751(b) applies to disproportionate distributions. "
                    "Detailed hot asset analysis requires trial balance and asset-by-asset review in Phase 2.",
        }

    def _analyze_liabilities(self) -> dict:
        """Analyze §752 liability allocations."""
        total = to_decimal(self._input.total_liabilities)
        recourse = to_decimal(self._input.recourse_liabilities)
        nonrecourse = to_decimal(self._input.nonrecourse_liabilities)

        partner_allocations = []
        for p in self._input.partners:
            recourse_share = to_decimal(p.share_of_recourse_liabilities)
            nr_share = to_decimal(p.share_of_nonrecourse_liabilities)
            qnr_share = to_decimal(p.share_of_qnr_liabilities)
            total_share = recourse_share + nr_share + qnr_share

            partner_allocations.append({
                "partner": p.name,
                "recourse": recourse_share,
                "nonrecourse": nr_share,
                "qualified_nonrecourse": qnr_share,
                "total": total_share,
                "outside_basis_impact": total_share,
            })

        return {
            "total_liabilities": total,
            "recourse": recourse,
            "nonrecourse": nonrecourse,
            "partner_allocations": partner_allocations,
            "note": "Recourse liabilities allocated to partner bearing economic risk of loss (§1.752-2). "
                    "Nonrecourse allocated: (1) minimum gain, (2) §704(c) minimum gain, (3) profits interest.",
        }

    def _generate_findings(self, allocations, sec704c, basis_adj, distributions, hot_assets, liabilities) -> list:
        findings = []

        if allocations["special_allocation_count"] > 0:
            findings.append({
                "area": "Special Allocations",
                "description": f"{allocations['special_allocation_count']} special allocations totaling "
                               f"{format_currency(allocations['total_special_allocations'])} — must satisfy §704(b) SEE test",
                "amount": allocations["total_special_allocations"],
                "risk_level": "high",
                "recommendation": "Review partnership agreement for capital account maintenance, DRO/QIO, and liquidation provisions",
            })

        if sec704c["count"] > 0:
            findings.append({
                "area": "§704(c) Contributed Property",
                "description": f"{sec704c['count']} contributed properties with net built-in "
                               f"{'gain' if sec704c['net_builtin'] > 0 else 'loss'} of {format_currency(abs(sec704c['net_builtin']))}",
                "amount": abs(sec704c["net_builtin"]),
                "risk_level": "high" if sec704c["has_ceiling_rule_risk"] else "medium",
                "recommendation": "Evaluate §704(c) method (traditional vs. curative vs. remedial); address ceiling rule issues",
            })

        if basis_adj["substantial_built_in_loss"]:
            findings.append({
                "area": "Mandatory §743(b) Adjustment",
                "description": "Substantial built-in loss exceeds $250K — mandatory basis adjustment required",
                "amount": abs(basis_adj["book_tax_difference"]),
                "risk_level": "high",
                "recommendation": "§743(b) adjustment required on any transfer regardless of §754 election",
            })

        if distributions["total_gain_recognized"] > Decimal("0"):
            findings.append({
                "area": "Distribution Gain Recognition",
                "description": f"Gain recognized on distributions: {format_currency(distributions['total_gain_recognized'])}",
                "amount": distributions["total_gain_recognized"],
                "risk_level": "medium",
                "recommendation": "Verify partner outside basis computations; review for §707(a)(2)(B) disguised sale risk",
            })

        if hot_assets["has_potential_hot_assets"]:
            findings.append({
                "area": "§751 Hot Assets",
                "description": "Partnership has potential hot assets (unrealized receivables/inventory)",
                "amount": Decimal("0"),
                "risk_level": "medium",
                "recommendation": "Detailed §751 analysis needed for any sales/exchanges of partnership interests or disproportionate distributions",
            })

        findings.sort(key=lambda f: ({"high": 0, "medium": 1, "low": 2}.get(f["risk_level"], 3),
                                     -abs(to_decimal(f["amount"]))))
        return findings

    def _generate_phase2_recommendations(self, findings) -> list:
        recs = [
            {"priority": 1, "area": "Partnership Agreement Review",
             "description": "Analyze partnership agreement for capital account, allocation, and distribution provisions",
             "data_needed": "Partnership agreement (LPA/LLC agreement), amendments, side letters"},
            {"priority": 2, "area": "Capital Account Analysis",
             "description": "Verify §704(b) capital accounts maintained per Reg. §1.704-1(b)(2)(iv)",
             "data_needed": "Form 1065, Schedules K/K-1, capital account reconciliation, §704(b) book balance sheet"},
        ]

        if any(f["area"] == "§704(c) Contributed Property" for f in findings):
            recs.append({"priority": 3, "area": "§704(c) Allocation Detail",
                        "description": "Perform property-by-property §704(c) allocation under selected method",
                        "data_needed": "Contribution documentation, appraisals, depreciation schedules, §704(c) layers"})

        if not self._input.partnership.has_754_election:
            recs.append({"priority": 4, "area": "§754 Election Analysis",
                        "description": "Evaluate whether §754 election would be beneficial",
                        "data_needed": "Recent/pending transfers, FMV of partnership assets, inside/outside basis comparison"})

        return recs
