"""Re-export base authority classes."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from revenue_recognition.technical_authority.authorities.base import TechnicalAuthority, AuthorityLookup
__all__ = ["TechnicalAuthority", "AuthorityLookup"]
