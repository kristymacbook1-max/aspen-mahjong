"""Fuzzy-matching classifier for cost-capitalization.

Reads each department/cost-center + account combination on a trial balance and
classifies the line as one of:
  - book_capitalized : already capitalized on the books (CIP, fixed assets, inventory)
  - mixed            : mixed service cost / partly production (needs an allocation %)
  - tax-capitalized  : under the right method/section (266, 263(a), 263A, other:SEC)
  - deductible       : period cost

The rule base encodes the §263A reg cost lists and the IRS LB&I Practice Unit
cost categories (purchasing/storage/handling, mixed service costs, capitalizable
indirect costs). Each classification carries the governing section / Practice
Unit as its `basis`, plus a `confidence`, so the knowledge is *used* on the
working line rather than parked on a reference tab.

Matching is heuristic (stdlib difflib + token overlap, no extra dependency) and
every suggestion is editable downstream.
"""

from dataclasses import dataclass
from decimal import Decimal
from difflib import SequenceMatcher
import re

# Provision tags (kept in sync with analyzer.PROVISION_TAGS + lean additions)
P_BOOK = "book_capitalized"
P_MIXED = "mixed"
P_DEDUCT = "deductible"
P_266 = "266"
P_263A_ACQ = "263(a)"
P_263A = "263A"


def bucket_for(provision: str) -> str:
    """Coarse classification bucket for a provision tag."""
    if provision == P_BOOK:
        return "book_capitalized"
    if provision == P_MIXED:
        return "mixed"
    if provision == P_DEDUCT:
        return "deductible"
    return "tax_capitalized"


@dataclass
class Classification:
    provision: str
    cap_pct: Decimal          # portion of the line capitalized to the tagged bucket
    basis: str                # governing section + Practice Unit
    confidence: str           # high / medium / low
    score: float

    @property
    def bucket(self) -> str:
        return bucket_for(self.provision)


# ---------------------------------------------------------------------------
# Rule base — ordered; earlier rules win ties. Seeded from §1.263A-1(e), the
# §263(a) repair regs, §266, and the IRS §263A Practice Units.
# ---------------------------------------------------------------------------
CLASSIFICATION_RULES = [
    # --- Already capitalized for book ---
    dict(keywords=["construction in progress", "cip", "work in process", "wip",
                   "fixed asset", "capitalized", "leasehold improvement", "buildings",
                   "machinery", "equipment asset", "inventory", "finished goods",
                   "raw materials", "capital work"],
         cc_hints=[], provision=P_BOOK, cap_pct=Decimal("1"),
         basis="Already capitalized on books (§471 cost base); §263A additional-cost layer only",
         confidence="high"),

    # --- §266 carrying charges (land / development context) ---
    dict(keywords=["property tax", "real estate tax", "ad valorem", "mortgage interest",
                   "land interest", "carrying charge", "insurance - land", "land taxes"],
         cc_hints=["land", "development", "unimproved", "investment property", "held for development"],
         cc_required=True,  # property tax/interest only capitalize under §266 in a land/dev context
         provision=P_266, cap_pct=Decimal("1"),
         basis="§266 / Reg §1.266-1(b)(1)(i)-(ii) — elective carrying charges",
         confidence="high"),

    # --- §263(a) acquisition / transaction / improvement ---
    dict(keywords=["acquisition cost", "transaction cost", "broker", "appraisal",
                   "due diligence", "title", "facilitative", "success fee", "deal cost",
                   "closing cost", "install", "installation"],
         cc_hints=[], provision=P_263A_ACQ, cap_pct=Decimal("1"),
         basis="§263(a) / Reg §1.263(a)-2 & -5 — acquisition / inherently facilitative costs",
         confidence="high"),
    dict(keywords=["improvement", "betterment", "restoration", "renovation", "remodel",
                   "rebuild", "overhaul"],
         cc_hints=[], provision=P_263A_ACQ, cap_pct=Decimal("1"),
         basis="§263(a) / Reg §1.263(a)-3 — betterment/restoration/adaptation (BRA)",
         confidence="medium"),

    # --- Other capitalization regimes ---
    dict(keywords=["goodwill", "customer list", "covenant not to compete", "franchise",
                   "trademark", "trade name", "intangible asset", "acquired intangible"],
         cc_hints=[], provision="other:197", cap_pct=Decimal("1"),
         basis="§197 — acquired intangibles, 15-year amortization",
         confidence="high"),
    dict(keywords=["research", "experimental", "r&e", "r & e", "software development",
                   "r&d expense"],
         cc_hints=["r&d", "research", "development lab"],
         provision="other:174A", cap_pct=Decimal("1"),
         basis="§174A domestic R&E (current expensing default; foreign R&E §174 15-yr)",
         confidence="high"),
    dict(keywords=["start-up", "startup", "pre-opening", "preopening", "organizational",
                   "incorporation", "syndication"],
         cc_hints=[], provision="other:195", cap_pct=Decimal("1"),
         basis="§195 / §248 / §709 — start-up & organizational ($5k + 180-mo; syndication permanent)",
         confidence="medium"),
    dict(keywords=["intangible drilling", "idc", "well development"],
         cc_hints=["oil", "gas", "drilling"],
         provision="other:263(c)", cap_pct=Decimal("1"),
         basis="§263(c) / §59(e) — intangible drilling costs",
         confidence="medium"),
    dict(keywords=["prepaid interest", "points", "loan points"],
         cc_hints=[], provision="other:461(g)", cap_pct=Decimal("1"),
         basis="§461(g) — prepaid interest spread over loan term",
         confidence="medium"),
    dict(keywords=["straddle", "carrying charge - straddle"],
         cc_hints=[], provision="other:263(g)", cap_pct=Decimal("1"),
         basis="§263(g) — straddle interest/carrying charges into basis",
         confidence="low"),

    # --- §263A — reseller purchasing/storage/handling (Reg §1.263A-3 / Reseller unit) ---
    dict(keywords=["purchasing", "procurement", "buying", "merchandising"],
         cc_hints=["purchasing", "procurement"],
         provision=P_263A, cap_pct=Decimal("1"),
         basis="§263A / Reg §1.263A-3(c)(3) purchasing costs; IRS Reseller Practice Unit (SRM)",
         confidence="high"),
    dict(keywords=["storage", "warehouse", "warehousing", "handling", "freight-in",
                   "freight in", "inbound freight", "receiving", "stocking"],
         cc_hints=["warehouse", "storage", "distribution center", "dc"],
         provision=P_263A, cap_pct=Decimal("1"),
         basis="§263A / Reg §1.263A-3(c) storage & handling; IRS Reseller Practice Unit (SRM)",
         confidence="high"),

    # --- §263A — producer indirect production costs (Reg §1.263A-1(e)(3)) ---
    dict(keywords=["indirect labor", "factory overhead", "production overhead", "manufacturing overhead",
                   "depreciation - production", "depreciation - factory", "factory rent",
                   "factory utilities", "quality control", "repairs - production",
                   "production supplies", "tooling", "spoilage", "officer compensation - production"],
         cc_hints=["manufacturing", "production", "factory", "plant", "mill"],
         provision=P_263A, cap_pct=Decimal("1"),
         basis="§263A / Reg §1.263A-1(e)(3) capitalizable indirect production cost; Producer Practice Unit",
         confidence="high"),
    dict(keywords=["direct labor", "direct material", "direct materials"],
         cc_hints=["manufacturing", "production", "factory"],
         provision=P_263A, cap_pct=Decimal("1"),
         basis="§263A / Reg §1.263A-1(e)(2) direct production cost",
         confidence="high"),

    # --- Mixed service costs (Reg §1.263A-1(e)(4); SSCM) ---
    dict(keywords=["accounting", "payroll dept", "human resources", "hr dept", "legal",
                   "information technology", "it dept", "data processing", "security",
                   "general management", "administration", "personnel"],
         cc_hints=["g&a", "corporate", "admin", "shared services", "service department"],
         provision=P_MIXED, cap_pct=Decimal("0.5"),
         basis="Mixed service cost §1.263A-1(e)(4); allocate via Simplified Service Cost Method",
         confidence="medium"),

    # --- Clearly deductible period costs (Reg §1.263A-1(e)(3)(iii)) ---
    dict(keywords=["selling", "sales commission", "marketing", "advertising", "promotion",
                   "distribution", "freight-out", "freight out", "outbound freight",
                   "income tax", "interest expense - general", "warranty", "bad debt",
                   "donation", "lobbying", "entertainment"],
         cc_hints=["sales", "marketing"],
         provision=P_DEDUCT, cap_pct=Decimal("0"),
         basis="Non-capitalizable period cost §1.263A-1(e)(3)(iii)",
         confidence="high"),
]

_DEFAULT = Classification(
    provision=P_DEDUCT, cap_pct=Decimal("0"),
    basis="No rule matched — defaulted to deductible; review",
    confidence="low", score=0.0,
)

_THRESHOLD = 0.58
_WORD_RE = re.compile(r"[a-z0-9&]+")


def _tokens(text: str):
    return _WORD_RE.findall((text or "").lower())


_TOKEN_GATE = 0.82  # ignore weak single-token fuzzy matches (kills false positives)


def _phrase_score(phrase: str, text_lc: str, tokens) -> float:
    """Best match score of a keyword phrase against the line text."""
    phrase = phrase.lower()
    if phrase in text_lc:
        return 1.0
    pwords = phrase.split()
    if len(pwords) > 1:
        # multiword: fraction of phrase-words that hit a token
        hits = sum(1 for pw in pwords if any(
            pw == tok or SequenceMatcher(None, pw, tok).ratio() >= 0.85 for tok in tokens))
        return hits / len(pwords)
    # single word: best token ratio, but only if it clears the gate
    best = 0.0
    for tok in tokens:
        r = SequenceMatcher(None, phrase, tok).ratio()
        if r >= _TOKEN_GATE:
            best = max(best, r)
    return best


def _bump(confidence: str, up: bool) -> str:
    order = ["low", "medium", "high"]
    i = order.index(confidence) if confidence in order else 1
    i = min(2, i + 1) if up else max(0, i - 1)
    return order[i]


def classify(account_name: str, cost_center_name: str = "",
             cost_center_type: str = "", book_category: str = "") -> Classification:
    """Classify a department/cost-center + account combo. Heuristic; editable."""
    text_lc = " ".join([account_name or "", cost_center_name or "",
                        cost_center_type or "", book_category or ""]).lower()
    tokens = _tokens(text_lc)
    cc_text = " ".join([cost_center_name or "", cost_center_type or ""]).lower()

    best_rule = None
    best_score = 0.0
    for rule in CLASSIFICATION_RULES:
        kw_score = max((_phrase_score(kw, text_lc, tokens) for kw in rule["keywords"]),
                       default=0.0)
        cc_hit = 0.0
        if rule["cc_hints"]:
            cc_hit = max((_phrase_score(h, cc_text, _tokens(cc_text)) for h in rule["cc_hints"]),
                         default=0.0)
        # Rules that require cost-center context (e.g. §266 land) only fire on a hit
        if rule.get("cc_required") and cc_hit < 0.85:
            continue
        cc_boost = 0.12 if cc_hit >= 0.85 else 0.0
        score = min(1.0, kw_score + cc_boost)
        if score > best_score:
            best_score, best_rule = score, dict(rule, _cc_boost=cc_boost)

    if not best_rule or best_score < _THRESHOLD:
        return Classification(**{**_DEFAULT.__dict__})

    conf = best_rule["confidence"]
    if best_rule.get("_cc_boost", 0.0) > 0 and best_score >= 0.95:
        conf = _bump(conf, up=True)
    elif best_score < 0.7:
        conf = _bump(conf, up=False)

    return Classification(
        provision=best_rule["provision"],
        cap_pct=best_rule["cap_pct"],
        basis=best_rule["basis"],
        confidence=conf,
        score=round(best_score, 3),
    )
