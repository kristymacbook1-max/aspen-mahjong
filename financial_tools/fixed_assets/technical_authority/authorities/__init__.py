"""Fixed asset / depreciation technical authority database."""
from .depreciation_authorities import DEPRECIATION_AUTHORITIES
from .base import TechnicalAuthority, AuthorityLookup

def get_depreciation_lookup() -> AuthorityLookup:
    return AuthorityLookup(list(DEPRECIATION_AUTHORITIES))
