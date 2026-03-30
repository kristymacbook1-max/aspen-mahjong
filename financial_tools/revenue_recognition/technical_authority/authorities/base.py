"""Base dataclass and lookup utilities for technical authorities."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class TechnicalAuthority:
    """A single tax technical authority (statute, regulation, case, ruling, etc.)."""
    citation: str
    authority_type: str  # statute, regulation, case_law, rev_proc, rev_rul, plr, cca, tam, notice
    title: str
    year: int
    relevance: str  # which rev rec method/issue this relates to
    key_holding: str
    facts_summary: str = ""
    taxpayer_favorable: bool = True
    weight: str = "substantial"  # primary, substantial, some, limited
    topics: List[str] = field(default_factory=list)
    related_citations: List[str] = field(default_factory=list)
    url: str = ""
    notes: str = ""


class AuthorityLookup:
    """Search and filter technical authorities."""

    def __init__(self, authorities: List[TechnicalAuthority] = None):
        self.authorities = authorities or []

    def add(self, authorities: List[TechnicalAuthority]):
        """Add authorities to the database."""
        self.authorities.extend(authorities)

    def by_topic(self, topic: str) -> List[TechnicalAuthority]:
        topic_lower = topic.lower()
        return [a for a in self.authorities if any(topic_lower in t.lower() for t in a.topics)]

    def by_type(self, authority_type: str) -> List[TechnicalAuthority]:
        return [a for a in self.authorities if a.authority_type == authority_type]

    def by_relevance(self, method: str) -> List[TechnicalAuthority]:
        method_lower = method.lower()
        return [a for a in self.authorities if method_lower in a.relevance.lower()]

    def favorable(self, topic: str = None) -> List[TechnicalAuthority]:
        results = self.authorities if not topic else self.by_topic(topic)
        return [a for a in results if a.taxpayer_favorable]

    def adverse(self, topic: str = None) -> List[TechnicalAuthority]:
        results = self.authorities if not topic else self.by_topic(topic)
        return [a for a in results if not a.taxpayer_favorable]

    def primary(self, topic: str = None) -> List[TechnicalAuthority]:
        results = self.authorities if not topic else self.by_topic(topic)
        return [a for a in results if a.weight == "primary"]

    def search(self, query: str) -> List[TechnicalAuthority]:
        q = query.lower()
        return [a for a in self.authorities if (
            q in a.citation.lower() or
            q in a.title.lower() or
            q in a.key_holding.lower() or
            q in a.facts_summary.lower() or
            q in a.relevance.lower()
        )]

    def for_position(self, topics: List[str]) -> dict:
        """Get supporting and adverse authorities for a set of topics."""
        all_relevant = []
        for topic in topics:
            all_relevant.extend(self.by_topic(topic))
        # Deduplicate
        seen = set()
        unique = []
        for a in all_relevant:
            if a.citation not in seen:
                seen.add(a.citation)
                unique.append(a)
        return {
            "supporting": [a for a in unique if a.taxpayer_favorable],
            "adverse": [a for a in unique if not a.taxpayer_favorable],
            "primary": [a for a in unique if a.weight == "primary"],
            "all": unique,
        }
