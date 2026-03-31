"""CAMT technical authority database."""
from .camt_authorities import CAMT_AUTHORITIES
from .base import TechnicalAuthority, AuthorityLookup

def get_camt_authority_lookup() -> AuthorityLookup:
    return AuthorityLookup(list(CAMT_AUTHORITIES))
