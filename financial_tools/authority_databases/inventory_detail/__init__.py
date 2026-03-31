"""Inventory authority detail modules — expanded coverage of UNICAP, LIFO, and industry-specific rules."""

from .lifo_authorities import LIFO_AUTHORITIES
from .unicap_authorities import UNICAP_AUTHORITIES
from .inventory_valuation_authorities import INVENTORY_VALUATION_AUTHORITIES
from .capitalizable_costs_authorities import CAPITALIZABLE_COSTS_AUTHORITIES
from .inventory_case_law import INVENTORY_CASE_LAW
from .inventory_admin_guidance import INVENTORY_ADMIN_GUIDANCE

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from revenue_recognition.technical_authority.authorities.base import AuthorityLookup

ALL_INVENTORY_DETAIL_AUTHORITIES = (
    list(LIFO_AUTHORITIES)
    + list(UNICAP_AUTHORITIES)
    + list(INVENTORY_VALUATION_AUTHORITIES)
    + list(CAPITALIZABLE_COSTS_AUTHORITIES)
    + list(INVENTORY_CASE_LAW)
    + list(INVENTORY_ADMIN_GUIDANCE)
)


def get_all_inventory_detail_lookup() -> AuthorityLookup:
    return AuthorityLookup(ALL_INVENTORY_DETAIL_AUTHORITIES)
