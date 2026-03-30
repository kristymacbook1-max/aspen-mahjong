"""International tax technical authority database."""
from .international_tax_authorities import INTERNATIONAL_TAX_AUTHORITIES
from .base import TechnicalAuthority, AuthorityLookup


def get_international_tax_lookup() -> AuthorityLookup:
    return AuthorityLookup(list(INTERNATIONAL_TAX_AUTHORITIES))
