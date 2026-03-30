"""Aggregated technical authority database for revenue recognition.

Combines all topic-specific authority files into a single searchable database.
"""

from .authorities.base import TechnicalAuthority, AuthorityLookup
from .authorities.advance_payments import ADVANCE_PAYMENT_AUTHORITIES
from .authorities.deposits_and_slots import DEPOSIT_AUTHORITIES
from .authorities.long_term_contracts import LONG_TERM_CONTRACT_AUTHORITIES
from .authorities.method_changes import METHOD_CHANGE_AUTHORITIES
from .authorities.accrual_and_afs import ACCRUAL_AFS_AUTHORITIES


# Combined database of all authorities
AUTHORITY_DATABASE = (
    ADVANCE_PAYMENT_AUTHORITIES
    + DEPOSIT_AUTHORITIES
    + LONG_TERM_CONTRACT_AUTHORITIES
    + METHOD_CHANGE_AUTHORITIES
    + ACCRUAL_AFS_AUTHORITIES
)


def get_authority_lookup() -> AuthorityLookup:
    """Get a fully loaded AuthorityLookup instance."""
    return AuthorityLookup(list(AUTHORITY_DATABASE))
