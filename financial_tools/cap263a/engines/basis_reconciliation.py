"""Runtime Pipeline Step 3b — shared book-vs-tax-required basis reconciliation.

One helper Phases C/D/F/G and the Gate-4 BAR routing all call before posting
to the Basis & Amortization Schedule: given what the books already capitalized
and what the tax rules require, post only the DELTA. If book exceeds
tax-required, FLAG rather than silently post a negative (differing book/tax
conventions need review, not an automatic reversal). Deliberately NOT called
for inventory (§263A additional costs are never book-capitalized by
definition — see BUILD_PLAN.md's Basis Reconciliation section, item (1)).
"""

from decimal import Decimal
from typing import List, Tuple


def reconcile(book_capitalized: Decimal, tax_required: Decimal,
              label: str) -> Tuple[Decimal, List[str]]:
    """Return (delta_to_post, warnings). delta = max(0, required - book)."""
    book_capitalized = Decimal(str(book_capitalized or 0))
    tax_required = Decimal(str(tax_required or 0))
    warnings: List[str] = []
    delta = tax_required - book_capitalized
    if delta < 0:
        warnings.append(
            f"BOOK-EXCEEDS-TAX-REQUIRED [{label}]: book already capitalizes "
            f"${book_capitalized:,.2f} but the tax-required amount is only "
            f"${tax_required:,.2f} — no negative posting made; review the "
            f"book/tax convention difference (${-delta:,.2f}).")
        return Decimal("0"), warnings
    if book_capitalized > 0 and delta > 0:
        warnings.append(
            f"BASIS-RECONCILED [{label}]: ${book_capitalized:,.2f} already on "
            f"the books; posting only the ${delta:,.2f} tax delta.")
    return delta, warnings
