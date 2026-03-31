"""Re-export base authority classes from revenue_recognition shared module."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from revenue_recognition.technical_authority.authorities.base import (
    TechnicalAuthority,
    AuthorityLookup,
)

__all__ = ["TechnicalAuthority", "AuthorityLookup"]
