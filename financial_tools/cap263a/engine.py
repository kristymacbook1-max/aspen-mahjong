"""Data-driven classification engine.

Keeps the valuable model from the original tool — layered keyword/rule scoring,
cost-center "zone" reclassification of generic accounts, confidence + review
flags — but rebuilt as a single deterministic scored pass over a data-driven
taxonomy (no hard-coded category literals, no three redundant full-catalog
rescans). Layer 2 (rapidfuzz) is optional; Layer 3 (semantic) is a separate
opt-in plugin.
"""

import re
from .taxonomy import get_taxonomy, IMMUNE_TIERS, _WORD_RE
from .model import Classification

try:
    from rapidfuzz import fuzz
    HAS_FUZZY = True
except Exception:                       # pragma: no cover
    HAS_FUZZY = False

_LEADING_ACCT = re.compile(r"^[\s]*[\d\-\.]+[\s:·\-]+")
_PARENS = re.compile(r"\([^)]*\)")


def normalize(text: str) -> str:
    t = (text or "").lower().strip()
    t = _LEADING_ACCT.sub("", t)        # strip "6100-20 · " style prefixes
    t = _PARENS.sub(" ", t)
    t = re.sub(r"[^a-z0-9&\s\-/]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _expand(text, abbreviations):
    return " ".join(abbreviations.get(w, w) for w in text.split())


def _apply_synonyms(text, syn):
    words = text.split()
    return " ".join(syn.get(w, w) for w in words)


def _prep(text, tax, syn):
    return _apply_synonyms(_expand(normalize(text), tax.abbreviations), syn)


def detect_cc_zone(cc_text, tax):
    """Return (zone, zone_tier1) from the longest matching cost-center keyword."""
    if not cc_text:
        return "", ""
    for rule in tax.zone_rules():
        if rule["keyword"] and rule["keyword"] in cc_text:
            return rule["zone"], rule["zone_tier1"]
    return "", ""


def _confidence(score):
    if score >= 70: return 85
    if score >= 50: return 70
    if score >= 35: return 55
    if score >= 20: return 40
    if score >= 10: return 25
    return 10


def classify(acct_num="", acct_desc="", cc_num="", cc_desc="", tax=None):
    tax = tax or get_taxonomy()
    desc = _prep(acct_desc, tax, tax.account_synonyms)
    cc = _prep(f"{cc_desc} {cc_num}", tax, tax.cc_synonyms)
    combined = f"{desc} {cc}".strip()
    desc_words = set(_WORD_RE.findall(desc))
    cc_words = set(_WORD_RE.findall(cc))

    zone, zone_tier1 = detect_cc_zone(cc, tax)

    # --- candidate set ---
    cand = set()
    for w in desc_words | cc_words:
        cand |= tax.word_to_codes.get(w, set())
    for w in cc_words:
        cand |= tax.cc_clue_to_codes.get(w, set())
    cand |= tax.generic_codes
    if zone_tier1:
        cand |= tax.codes_by_tier1.get(zone_tier1, set())
    if not cand:
        cand = set(tax.by_code)

    best = None; best_score = -1; best_method = ""; best_kw_hit = False
    runner = None; runner_score = -1
    gen_kw_code = None; gen_kw_score = -1     # best generic code with a keyword hit

    for code in sorted(cand):                       # deterministic order
        c = tax.by_code[code]
        score = 0
        method = []

        # Layer 1: keyword
        kw_hit = False
        kws = c.get("keywords", [])
        if any(k.lower() in desc for k in kws):
            score += 50; method.append("kw:desc"); kw_hit = True
        elif any(k.lower() in combined for k in kws):
            score += 35; method.append("kw:comb"); kw_hit = True

        # cost-center clues
        clue_hits = sum(1 for clue in c.get("cc_clues", [])
                        if clue.lower() in cc)
        if clue_hits:
            score += min(20 + (clue_hits - 1) * 10, 40); method.append("cc")

        # zone alignment (not for generic / immune tiers)
        if (zone_tier1 and c["tier1"] == zone_tier1
                and code not in tax.generic_codes
                and c["tier1"] not in IMMUNE_TIERS):
            score += 25; method.append("zone")

        # Layer 2: fuzzy (only when no exact keyword hit and still weak)
        if HAS_FUZZY and not kw_hit and score < 40 and kws:
            top = max((fuzz.partial_ratio(k.lower(), combined) for k in kws),
                      default=0)
            if top >= 85:
                score += 30; method.append(f"fuzzy:{int(top)}")
            elif top >= 75:
                score += 20; method.append(f"fuzzy:{int(top)}")

        score += int(c.get("priority", 0))

        if kw_hit and code in tax.generic_codes and score > gen_kw_score:
            gen_kw_code, gen_kw_score = code, score

        if score > best_score:
            runner, runner_score = best, best_score
            best, best_score, best_method, best_kw_hit = code, score, "+".join(method), kw_hit
        elif score > runner_score:
            runner, runner_score = code, score

    if best is None:
        best, best_score, best_method = "VAGUE-OTHER", 0, "no-match"

    # --- generic reclassification by cost-center zone ---
    # Fire when the winner is itself generic, OR when a generic code had a keyword
    # hit but a zone-only specific code edged it out (the -10 generic priority
    # penalty must not defeat a valid account keyword + department reclass).
    reclassed = False
    suspense = False
    best_had_specific_kw = best_kw_hit and best not in tax.generic_codes
    if (gen_kw_code and not best_had_specific_kw
            and tax.generic_map.get(gen_kw_code) == "suspense"
            and best not in tax.generic_codes):
        # a "variance/clearing/suspense" keyword must beat a zone-only specific guess
        best = gen_kw_code
        best_method += "+suspense"
        suspense = True
    else:
        gen_source = (best if best in tax.generic_codes
                      else (gen_kw_code if not best_had_specific_kw else None))
        if zone and gen_source:
            exp = tax.generic_map.get(gen_source)
            if exp and exp != "suspense":
                target = tax.reclass_target(zone, exp)
                if target and target in tax.by_code and target != best:
                    best = target
                    best_method += "+cc-reclass"
                    best_score = max(best_score, 60)
                    reclassed = True

    c = tax.by_code[best]
    conf = _confidence(best_score)
    flags = []
    if suspense:
        flags.append("REVIEW")
    if reclassed:
        flags.append("CC-RECLASSED")
    if (runner is not None and runner_score >= 0
            and (best_score - runner_score) < 10 and best_score < 60):
        rc = tax.by_code.get(runner)
        if rc and rc["tier1"] != c["tier1"]:
            flags.append("AMBIGUOUS")
    if (zone_tier1 and c["tier1"] != zone_tier1
            and c["tier1"] not in IMMUNE_TIERS and c["tier1"] != "Mixed Service"):
        flags.append("CC-CONFLICT")
    if conf < 40:
        flags.append("REVIEW")
    elif conf < 70:
        flags.append("LOW-CONF")

    return Classification(
        code=c["code"], tier1=c["tier1"], tier2=c.get("tier2", ""),
        tier3=c.get("tier3", ""), treatment=dict(c["treatment"]),
        cap_vs_deduct=c.get("cap_vs_deduct"),
        allows_negative_adj=bool(c.get("allows_negative_adj")),
        designated_property=bool(c.get("designated_property")),
        election_required=bool(c.get("election_required")),
        is_labor=bool(c.get("is_labor")), labor_type=c.get("labor_type", ""),
        authority=c.get("authority", ""),
        confidence=conf, flags=flags, method=best_method,
        notes=("zone=" + zone if zone else ""),
    )
