"""Partnership tax technical authority database."""
from .partnership_tax_authorities import PARTNERSHIP_TAX_AUTHORITIES
from .base import TechnicalAuthority, AuthorityLookup


def get_partnership_tax_lookup() -> AuthorityLookup:
    return AuthorityLookup(list(PARTNERSHIP_TAX_AUTHORITIES))
