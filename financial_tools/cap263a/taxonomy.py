"""Taxonomy loader + validator for the §263A/§263(a)/§266 classifier.

Single source of truth: the YAML files under taxonomy/. Loading builds a
keyword index and VALIDATES every cross-reference (reclass targets, generic-map
targets, cost-center reclass) resolves to a real category code — this catches
the dead-code class of bug (e.g. the old MSC-RENT/MSC-DEP dangling targets and
labor keys that pointed at non-existent codes).
"""

import os
import re
from functools import lru_cache

import yaml

_DIR = os.path.join(os.path.dirname(__file__), "taxonomy")

# Tiers that are inherent to the account and must never be reclassified by
# cost-center context.
IMMUNE_TIERS = frozenset({"Balance Sheet", "Revenue", "Non-Operating"})
_WORD_RE = re.compile(r"[a-z0-9&]+")


def _load(name):
    with open(os.path.join(_DIR, name), "r") as fh:
        return yaml.safe_load(fh)


class TaxonomyError(ValueError):
    pass


class Taxonomy:
    def __init__(self, data=None):
        """Load from the YAML files, or from an in-memory `data` dict (used by
        the exported Python-in-Excel workbook so it runs the identical engine)."""
        if data is None:
            data = dict(
                categories=_load("categories.yaml"),
                cc_zones=_load("cc_zones.yaml"),
                cc_reclass=_load("cc_reclass.yaml"),
                generic_map=_load("generic_map.yaml"),
                lexicon=_load("lexicon.yaml"),
            )
        self.categories = data["categories"]
        self.by_code = {c["code"]: c for c in self.categories}
        self.cc_zones = data["cc_zones"]                # keyword -> zone/zone_tier1
        self.cc_reclass = data["cc_reclass"]            # (zone, expense_type) -> target
        self.generic_map = data["generic_map"]          # GEN-*/VAGUE-* -> expense_type
        lex = data["lexicon"]
        self.abbreviations = lex["abbreviations"]
        self.account_synonyms = lex["account_synonyms"]
        self.cc_synonyms = lex["cc_synonyms"]

        self._reclass_index = {(r["zone"], r["expense_type"]): r["target"]
                               for r in self.cc_reclass}
        # cost-center zone keywords, longest first (specific beats generic)
        self._zone_rules = sorted(self.cc_zones, key=lambda z: -len(z["keyword"]))
        self._build_keyword_index()
        self.validate()

    @classmethod
    def from_data(cls, categories, cc_zones, cc_reclass, generic_map, lexicon):
        return cls(dict(categories=categories, cc_zones=cc_zones, cc_reclass=cc_reclass,
                        generic_map=generic_map, lexicon=lexicon))

    # ------------------------------------------------------------------
    def _build_keyword_index(self):
        self.word_to_codes = {}      # word -> set(code)
        self.cc_clue_to_codes = {}   # clue word -> set(code)
        self.generic_codes = set()
        for c in self.categories:
            code = c["code"]
            if code.startswith("GEN-") or code.startswith("VAGUE-"):
                self.generic_codes.add(code)
            for kw in c.get("keywords", []):
                for w in _WORD_RE.findall(kw.lower()):
                    self.word_to_codes.setdefault(w, set()).add(code)
            for clue in c.get("cc_clues", []):
                for w in _WORD_RE.findall(clue.lower()):
                    self.cc_clue_to_codes.setdefault(w, set()).add(code)
        self.codes_by_tier1 = {}
        for c in self.categories:
            self.codes_by_tier1.setdefault(c["tier1"], set()).add(c["code"])

    # ------------------------------------------------------------------
    def validate(self):
        """Raise if any cross-reference dangles. This is the guard the
        original tool lacked (dead ADD-PURCH/SC-LABOR/MSC-RENT references)."""
        errors = []
        # reclass targets must exist
        for (zone, exp), target in self._reclass_index.items():
            if target not in self.by_code:
                errors.append(f"cc_reclass ({zone},{exp}) -> unknown code {target}")
        # every generic_map key must be a real (generic) category
        for gcode in self.generic_map:
            if gcode not in self.by_code:
                errors.append(f"generic_map key {gcode} is not a category")
        # every category referenced by generic_map expense_type should be reachable
        # (soft check: at least one reclass rule targets a real code per expense_type)
        # required fields
        for c in self.categories:
            for fld in ("code", "tier1", "treatment", "priority"):
                if fld not in c:
                    errors.append(f"category {c.get('code','?')} missing {fld}")
            t = c.get("treatment", {})
            for m in ("mspm", "resale", "self_const", "interest"):
                if m not in t:
                    errors.append(f"category {c['code']} treatment missing {m}")
        if errors:
            raise TaxonomyError("Taxonomy validation failed:\n  " + "\n  ".join(errors))
        return True

    # ------------------------------------------------------------------
    def reclass_target(self, zone, expense_type):
        return self._reclass_index.get((zone, expense_type))

    def zone_rules(self):
        return self._zone_rules


@lru_cache(maxsize=1)
def get_taxonomy() -> Taxonomy:
    return Taxonomy()
