"""Fixed asset / depreciation technical authority database."""
from .depreciation_authorities import DEPRECIATION_AUTHORITIES
from .repair_regulations import REPAIR_REGULATION_AUTHORITIES
from .intangibles_197 import INTANGIBLES_197_AUTHORITIES
from .base import TechnicalAuthority, AuthorityLookup

ALL_FIXED_ASSET_AUTHORITIES = (
    list(DEPRECIATION_AUTHORITIES)
    + list(REPAIR_REGULATION_AUTHORITIES)
    + list(INTANGIBLES_197_AUTHORITIES)
)

def get_depreciation_lookup() -> AuthorityLookup:
    return AuthorityLookup(list(DEPRECIATION_AUTHORITIES))

def get_repair_regulation_lookup() -> AuthorityLookup:
    return AuthorityLookup(list(REPAIR_REGULATION_AUTHORITIES))

def get_intangibles_lookup() -> AuthorityLookup:
    return AuthorityLookup(list(INTANGIBLES_197_AUTHORITIES))

def get_all_fixed_asset_lookup() -> AuthorityLookup:
    return AuthorityLookup(ALL_FIXED_ASSET_AUTHORITIES)
