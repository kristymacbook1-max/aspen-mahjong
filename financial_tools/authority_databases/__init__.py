"""Standalone technical authority databases for accounting methods, inventory, and credits."""

from .accounting_methods import ACCOUNTING_METHOD_AUTHORITIES, get_accounting_methods_lookup
from .inventory import INVENTORY_AUTHORITIES, get_inventory_lookup
from .credits import CREDIT_AUTHORITIES, get_credits_lookup
