"""Data-driven classification engine.

Keeps the valuable model from the original tool — layered keyword/rule scoring,
cost-center "zone" reclassification of generic accounts, confidence + review
flags — but rebuilt as a single deterministic scored pass over a data-driven
taxonomy (no hard-coded category literals, no three redundant full-catalog
rescans). Layer 2 (rapidfuzz) is optional; Layer 3 (semantic) is a separate
opt-in plugin.
"""

import re
from functools import lru_cache

from .taxonomy import get_taxonomy, IMMUNE_TIERS, _WORD_RE
from .model import Classification

try:
    from rapidfuzz import fuzz
    HAS_FUZZY = True
except Exception:                       # pragma: no cover
    HAS_FUZZY = False

_LEADING_ACCT = re.compile(r"^[\s]*[\d\-\.]+[\s:·\-]+")
_PARENS = re.compile(r"\([^)]*\)")
# IRC-section shorthand ("401(k)", "403(b)", "457(b)") is not a narrative aside —
# the blanket parens-stripper below was eating the "(k)"/"(b)" entirely, turning
# "401(k) contribution" into "401 contribution" and losing the "401k" keyword.
_IRC_PAREN = re.compile(r"(\d)\s*\(\s*([a-z]{1,3})\s*\)")


@lru_cache(maxsize=None)
def _pattern(phrase):
    # The taxonomy has ~1,000 distinct keyword/clue phrases; compiling per call
    # thrashed re's tiny internal cache and dominated runtime (~90% of a large
    # TB's classify time was re.compile). Cached, the set compiles once.
    # Phrases are canonicalized the same way normalize() canonicalizes text
    # (hyphens/slashes -> spaces) so "freight-in"/"a/r trade" keywords match.
    phrase = re.sub(r"\s+", " ", phrase.replace("-", " ").replace("/", " ")).strip()
    return re.compile(rf"\b{re.escape(phrase)}\b")


def _phrase_in(phrase, text):
    """Word-boundary containment, not raw substring: a bare `in` check let short
    keywords/clues like "it" match inside unrelated words ("credit", "capital"),
    silently mis-tagging unrelated cost centers/accounts."""
    return _pattern(phrase).search(text) is not None


def normalize(text: str) -> str:
    t = (text or "").lower().strip()
    t = _LEADING_ACCT.sub("", t)        # strip "6100-20 · " style prefixes
    t = _IRC_PAREN.sub(r"\1\2", t)       # "401(k)" -> "401k" before the parens strip below
    t = _PARENS.sub(" ", t)
    # Hyphens/slashes become spaces so "Deprec-Mfg" tokenizes as two words the
    # lexicon can expand and "A/R trade" matches the "a/r trade"-style keywords
    # (which _pattern canonicalizes the same way).
    t = re.sub(r"[^a-z0-9&\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _prep(text, expand, apply_syn):
    """normalize -> abbreviation expansion -> synonym mapping, all phrase-level
    (longest-first, word-boundary). The original word-by-word substitution made
    every multi-word lexicon key silently dead (76 of 425 entries) and let
    2-letter abbreviations ("or", "oh", "pr") corrupt ordinary text."""
    return apply_syn(expand(normalize(text)))


def detect_cc_zone(cc_text, tax):
    """Return (zone, zone_tier1) from the longest matching cost-center keyword.

    Word-boundary match, not raw substring: a bare `in` check let short zone
    keywords like "it" match inside unrelated words ("capital", "credit",
    "waiting"), silently mis-zoning ordinary cost centers as corporate IT.
    """
    if not cc_text:
        return "", ""
    for rule in tax.zone_rules():
        kw = rule["keyword"]
        if kw and _pattern(kw).search(cc_text):
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
    desc = _prep(acct_desc, tax.expand_abbrev, tax.apply_account_syn)
    cc = _prep(f"{cc_desc} {cc_num}", tax.expand_abbrev, tax.apply_cc_syn)
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

    # Pre-pass: does any specialized code have a direct description-keyword
    # hit? Specialized = the capitalization-regime tiers (§263A(f) interest /
    # §266 carrying charges) plus negative-adjustment scaffold codes
    # (allows_negative_adj, e.g. NEG-263A for inventory shrinkage/write-off/
    # variance charges). The immune-tier bonus below protects BS/Revenue/
    # Non-Operating accounts from *department* pull — it must not outvote an
    # explicit regime keyword ("construction loan" interest must not lose to
    # plain "interest expense" + immune, and an "inventory shrinkage" IS
    # charge must not vanish into the Balance Sheet tier).
    _SPECIALIZED_TIERS = ("§263A(f) Interest", "§266 Carrying Charges",
                          "§263(a) Transaction/Intangible")
    specialized_codes = set()
    for t1 in _SPECIALIZED_TIERS:
        specialized_codes |= tax.codes_by_tier1.get(t1, set())
    specialized_codes |= {c["code"] for c in tax.categories if c.get("allows_negative_adj")}
    specialized_desc_hit = any(
        any(_phrase_in(k.lower(), desc) for k in tax.by_code[sc].get("keywords", []))
        for sc in (specialized_codes & cand))

    for code in sorted(cand):                       # deterministic order
        c = tax.by_code[code]
        score = 0
        method = []

        # Layer 1: keyword
        kw_hit = False; desc_hit = False
        kws = c.get("keywords", [])
        if any(_phrase_in(k.lower(), desc) for k in kws):
            score += 50; method.append("kw:desc"); kw_hit = True; desc_hit = True
        elif any(_phrase_in(k.lower(), combined) for k in kws):
            score += 35; method.append("kw:comb"); kw_hit = True

        # Balance-Sheet / Revenue / Non-Operating accounts are inherent to the
        # account, not the department: a direct description hit beats any
        # cost-center reclassification (prevents AR/AP/accrued/etc. being pulled
        # into a department's Mixed-Service default).
        if desc_hit and c["tier1"] in IMMUNE_TIERS and not specialized_desc_hit:
            score += 25; method.append("immune")

        # cost-center clues
        clue_hits = sum(1 for clue in c.get("cc_clues", [])
                        if _phrase_in(clue.lower(), cc))
        if clue_hits:
            score += min(20 + (clue_hits - 1) * 10, 40); method.append("cc")

        # zone alignment (not for generic / immune tiers). Requires a direct
        # signal (keyword or cost-center clue) so a bare in-zone code cannot win
        # on department membership alone — that phantom-win pulled balance-sheet
        # and specific accounts into a department's Mixed-Service default.
        if (zone_tier1 and c["tier1"] == zone_tier1
                and (kw_hit or clue_hits)
                and code not in tax.generic_codes
                and c["tier1"] not in IMMUNE_TIERS):
            score += 20; method.append("zone")

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
    elif not best_method:
        # Won with an empty method list — i.e. purely on a nonnegative `priority`
        # default with ZERO real signal (no keyword/clue/zone/fuzzy hit at all).
        # A code only reaches the candidate pool via incidental single-word
        # overlap in the keyword index (e.g. "contribution" pulling in
        # NO-CHARITY for a "401(k) ... contribution" line that never actually
        # phrase-matched); priority alone must never pick a specific tier1 out
        # of thin air — fall back to the safe, flagged default instead.
        best, best_score, best_method, best_kw_hit = "VAGUE-OTHER", 0, "no-match", False

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
    # Calibration: a win with no direct account-description keyword hit is a weaker
    # signal than the raw score implies. Zone-only / cost-center-only matches must
    # not report high confidence (so the review queue is meaningful).
    has_desc_kw = "kw:desc" in best_method
    if not has_desc_kw and not suspense:
        # 35, not 40: the review flag fires at conf < 40, so capping exactly AT
        # the threshold left every clue/zone-only guess sitting one point above
        # the review queue — flagged LOW-CONF but never REVIEW-counted.
        conf = min(conf, 55 if "kw" in best_method else 35)

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
