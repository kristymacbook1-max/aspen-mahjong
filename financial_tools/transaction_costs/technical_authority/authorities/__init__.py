"""Transaction cost technical authority database."""
from .transaction_cost_authorities import TRANSACTION_COST_AUTHORITIES
from .base import TechnicalAuthority, AuthorityLookup

def get_transaction_cost_lookup() -> AuthorityLookup:
    return AuthorityLookup(list(TRANSACTION_COST_AUTHORITIES))
