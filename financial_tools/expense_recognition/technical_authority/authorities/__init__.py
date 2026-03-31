"""Expense recognition technical authority databases."""

from .economic_performance import ECONOMIC_PERFORMANCE_AUTHORITIES
from .prepaid_expenses import PREPAID_EXPENSE_AUTHORITIES
from .recurring_item import RECURRING_ITEM_AUTHORITIES
from .compensation import COMPENSATION_AUTHORITIES
from .interest_limitation import INTEREST_LIMITATION_AUTHORITIES
from .research_development import RESEARCH_DEVELOPMENT_AUTHORITIES
from .related_party import RELATED_PARTY_AUTHORITIES
from .base import TechnicalAuthority, AuthorityLookup

ALL_EXPENSE_AUTHORITIES = (
    ECONOMIC_PERFORMANCE_AUTHORITIES
    + PREPAID_EXPENSE_AUTHORITIES
    + RECURRING_ITEM_AUTHORITIES
    + COMPENSATION_AUTHORITIES
    + INTEREST_LIMITATION_AUTHORITIES
    + RESEARCH_DEVELOPMENT_AUTHORITIES
    + RELATED_PARTY_AUTHORITIES
)


def get_expense_authority_lookup() -> AuthorityLookup:
    """Return an AuthorityLookup loaded with all expense recognition authorities."""
    return AuthorityLookup(list(ALL_EXPENSE_AUTHORITIES))
