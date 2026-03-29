"""Entity type configurations for C-Corp (Form 1120) and Partnership (Form 1065) tax analysis.

Provides entity-specific tax logic including statutory rates, form requirements,
and partnership allocation/K-1 generation capabilities.
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict

from .currency_helpers import to_decimal, round_currency


@dataclass
class EntityConfig:
    """Configuration for an entity type that drives tax analysis behavior."""
    entity_type: str  # "c_corp" or "partnership"
    form_type: str  # "1120" or "1065"
    statutory_rate: float  # 0.21 for c_corp, 0.0 for partnership (pass-through)
    uses_schedule_m1: bool  # True for 1120, True for 1065
    uses_schedule_m3: bool  # True if total assets >= $10M
    uses_schedule_k1: bool  # False for 1120, True for 1065
    has_allocation_rules: bool  # True for partnership
    section_451c_available: bool  # True for both
    section_460_applicable: bool  # True for both (long-term contracts)
    label: str  # "C Corporation" or "Partnership"


def get_entity_config(
    entity_type: str,
    total_assets: Decimal = Decimal("0"),
) -> EntityConfig:
    """Factory function to create an EntityConfig based on entity type.

    Args:
        entity_type: Either "c_corp" or "partnership".
        total_assets: Total assets of the entity, used to determine Schedule M-3
            requirement (>= $10M threshold).

    Returns:
        EntityConfig populated with the correct defaults for the entity type.

    Raises:
        ValueError: If entity_type is not recognized.
    """
    total_assets = to_decimal(total_assets)
    uses_m3 = total_assets >= Decimal("10000000")

    if entity_type == "c_corp":
        return EntityConfig(
            entity_type="c_corp",
            form_type="1120",
            statutory_rate=0.21,
            uses_schedule_m1=True,
            uses_schedule_m3=uses_m3,
            uses_schedule_k1=False,
            has_allocation_rules=False,
            section_451c_available=True,
            section_460_applicable=True,
            label="C Corporation",
        )
    elif entity_type == "partnership":
        return EntityConfig(
            entity_type="partnership",
            form_type="1065",
            statutory_rate=0.0,
            uses_schedule_m1=True,
            uses_schedule_m3=uses_m3,
            uses_schedule_k1=True,
            has_allocation_rules=True,
            section_451c_available=True,
            section_460_applicable=True,
            label="Partnership",
        )
    else:
        raise ValueError(
            f"Unrecognized entity_type '{entity_type}'. "
            "Supported values: 'c_corp', 'partnership'."
        )


@dataclass
class PartnerAllocation:
    """Allocation of income and estimated tax to a single partner."""
    partner_name: str
    allocation_percentage: Decimal  # e.g., Decimal("0.25") for 25%
    allocated_income: Decimal = Decimal("0")
    estimated_tax: Decimal = Decimal("0")
    partner_marginal_rate: float = 0.37  # default top individual rate


class PartnershipTaxAnalysis:
    """Provides partnership-specific tax analysis including allocations,
    book-tax difference flow-through, and K-1 summary generation."""

    def allocate_to_partners(
        self,
        taxable_income: Decimal,
        partners: List[PartnerAllocation],
    ) -> List[PartnerAllocation]:
        """Allocate taxable income to partners based on their allocation percentages.

        Each partner's allocated_income is set to taxable_income * allocation_percentage,
        and estimated_tax is computed using the partner's marginal rate.

        Args:
            taxable_income: Total partnership taxable income to allocate.
            partners: List of PartnerAllocation with partner_name,
                allocation_percentage, and partner_marginal_rate populated.

        Returns:
            The same list of PartnerAllocation objects with allocated_income
            and estimated_tax filled in.
        """
        taxable_income = to_decimal(taxable_income)

        for partner in partners:
            pct = to_decimal(partner.allocation_percentage)
            allocated = round_currency(taxable_income * pct)
            partner.allocated_income = allocated
            partner.estimated_tax = round_currency(
                allocated * Decimal(str(partner.partner_marginal_rate))
            )

        return partners

    def compute_partner_tax_impact(
        self,
        book_tax_difference: Decimal,
        partners: List[PartnerAllocation],
    ) -> List[Dict]:
        """Show how a book-tax difference flows through to each partner.

        For each partner, the difference is allocated by their percentage
        and the tax impact is computed at their marginal rate.

        Args:
            book_tax_difference: The total book-tax difference at the
                partnership level (positive = book > tax).
            partners: List of PartnerAllocation with allocation_percentage
                and partner_marginal_rate populated.

        Returns:
            List of dicts, one per partner, with keys: partner_name,
            allocation_percentage, allocated_difference, marginal_rate,
            tax_impact.
        """
        book_tax_difference = to_decimal(book_tax_difference)
        results = []

        for partner in partners:
            pct = to_decimal(partner.allocation_percentage)
            allocated_diff = round_currency(book_tax_difference * pct)
            tax_impact = round_currency(
                allocated_diff * Decimal(str(partner.partner_marginal_rate))
            )
            results.append({
                "partner_name": partner.partner_name,
                "allocation_percentage": float(pct),
                "allocated_difference": allocated_diff,
                "marginal_rate": partner.partner_marginal_rate,
                "tax_impact": tax_impact,
            })

        return results

    def generate_k1_summary(
        self,
        allocations: List[PartnerAllocation],
        book_tax_differences: List[Dict],
    ) -> List[Dict]:
        """Produce a K-1 line item summary per partner.

        Combines income allocations with book-tax difference detail to
        create a per-partner summary suitable for Schedule K-1 preparation.

        Args:
            allocations: List of PartnerAllocation with allocated_income
                and estimated_tax already computed (e.g., from allocate_to_partners).
            book_tax_differences: List of dicts representing individual
                book-tax difference items. Each dict should contain at minimum:
                - description (str)
                - amount (Decimal or numeric) — the total partnership-level difference
                - type (str) — "temporary" or "permanent"

        Returns:
            List of dicts, one per partner, each containing:
            - partner_name
            - allocation_percentage
            - ordinary_income (allocated taxable income)
            - estimated_tax
            - book_tax_adjustments (list of allocated difference items)
            - total_temporary_differences
            - total_permanent_differences
        """
        partner_lookup: Dict[str, Dict] = {}

        for alloc in allocations:
            pct = to_decimal(alloc.allocation_percentage)
            partner_lookup[alloc.partner_name] = {
                "partner_name": alloc.partner_name,
                "allocation_percentage": float(pct),
                "ordinary_income": alloc.allocated_income,
                "estimated_tax": alloc.estimated_tax,
                "book_tax_adjustments": [],
                "total_temporary_differences": Decimal("0"),
                "total_permanent_differences": Decimal("0"),
            }

        for diff_item in book_tax_differences:
            total_amount = to_decimal(diff_item.get("amount", 0))
            description = diff_item.get("description", "")
            diff_type = (diff_item.get("type", "") or "").lower()

            for alloc in allocations:
                pct = to_decimal(alloc.allocation_percentage)
                allocated_amount = round_currency(total_amount * pct)

                summary = partner_lookup[alloc.partner_name]
                summary["book_tax_adjustments"].append({
                    "description": description,
                    "type": diff_type,
                    "allocated_amount": allocated_amount,
                })

                if diff_type == "temporary":
                    summary["total_temporary_differences"] += allocated_amount
                elif diff_type == "permanent":
                    summary["total_permanent_differences"] += allocated_amount

        return list(partner_lookup.values())


class CCorpTaxAnalysis:
    """Provides C-Corporation tax impact calculations at the standard 21% rate."""

    STATUTORY_RATE = Decimal("0.21")

    def compute_tax_impact(self, book_tax_difference: Decimal) -> Dict:
        """Compute the tax impact of a book-tax difference for a C-Corp.

        Args:
            book_tax_difference: The book-tax difference amount
                (positive = book income exceeds tax income).

        Returns:
            Dict with difference, statutory_rate, tax_impact, and
            dta_or_dtl indicator.
        """
        difference = to_decimal(book_tax_difference)
        tax_impact = round_currency(difference * self.STATUTORY_RATE)

        if difference > 0:
            dta_or_dtl = "DTL"
        elif difference < 0:
            dta_or_dtl = "DTA"
        else:
            dta_or_dtl = "None"

        return {
            "difference": difference,
            "statutory_rate": float(self.STATUTORY_RATE),
            "tax_impact": tax_impact,
            "dta_or_dtl": dta_or_dtl,
        }

    def compute_multi_item_impact(
        self,
        book_tax_differences: List[Dict],
    ) -> Dict:
        """Compute aggregate tax impact across multiple book-tax difference items.

        Args:
            book_tax_differences: List of dicts, each with at minimum:
                - description (str)
                - amount (Decimal or numeric)
                - type (str) — "temporary" or "permanent"

        Returns:
            Dict with items (list of per-item impacts), total_temporary,
            total_permanent, total_tax_impact, and net_dta_dtl.
        """
        items = []
        total_temporary = Decimal("0")
        total_permanent = Decimal("0")

        for diff_item in book_tax_differences:
            amount = to_decimal(diff_item.get("amount", 0))
            description = diff_item.get("description", "")
            diff_type = (diff_item.get("type", "") or "").lower()
            tax_impact = round_currency(amount * self.STATUTORY_RATE)

            items.append({
                "description": description,
                "type": diff_type,
                "amount": amount,
                "tax_impact": tax_impact,
            })

            if diff_type == "temporary":
                total_temporary += amount
            elif diff_type == "permanent":
                total_permanent += amount

        total_tax_impact = round_currency(
            (total_temporary + total_permanent) * self.STATUTORY_RATE
        )

        net_amount = total_temporary + total_permanent
        if net_amount > 0:
            net_dta_dtl = "Net DTL"
        elif net_amount < 0:
            net_dta_dtl = "Net DTA"
        else:
            net_dta_dtl = "None"

        return {
            "items": items,
            "total_temporary": total_temporary,
            "total_permanent": total_permanent,
            "total_tax_impact": total_tax_impact,
            "net_dta_dtl": net_dta_dtl,
        }
