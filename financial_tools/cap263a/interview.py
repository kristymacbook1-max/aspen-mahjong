"""Phase E interview layer — the user-question decision tree.

Loads the declarative question graph in ``taxonomy/interview.yaml`` (one node
per numbered question in BUILD_PLAN.md Phase E Gates 0-10), validates it at
load time, and walks it against an answers dict to emit a populated
``EntityProfile``, the schedule-requirements list, the election/3115 summary,
and warnings.

ID convention: question ids contain dots (``Q1.1a``); inside ``ask_when``
expressions they are exposed with dots mapped to underscores (``Q1_1a``).
Unanswered / never-asked questions evaluate as ``None`` (falsy).

Derived names available to ``ask_when`` (computed by the runner, never asked):
``small_business_exempt``, ``under_448c_threshold``, ``srm_available``.
"""

from __future__ import annotations

import ast
import dataclasses
import os
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional

import yaml

from .analysis import EntityProfile

_DEFAULT_GRAPH_PATH = os.path.join(os.path.dirname(__file__), "taxonomy",
                                   "interview.yaml")

_ANSWER_TYPES = {"bool", "enum", "decimal", "int", "str", "per_item"}
_KINDS = {"FACT", "ELECTION", "METHOD-OF-ACCOUNTING"}
# Names computed by the runner that ask_when expressions may reference in
# addition to question ids (see module docstring).
_DERIVED_NAMES = {"small_business_exempt", "under_448c_threshold",
                  "srm_available"}
# Gates skipped entirely for a §448(c)-exempt small business: all of §263A —
# including (f) interest — is off. Gates 4/5/8/9/10 (§263(a)/§266/§174/
# §1060/§59(e)) are NOT §263A provisions and still run.
_EXEMPT_SKIPPED_GATES = (1, 2, 3, 6, 7)

_PROFILE_FIELDS = {f.name for f in dataclasses.fields(EntityProfile)}


def _uid(qid: str) -> str:
    """Q1.1a -> Q1_1a (the name exposed to ask_when expressions)."""
    return qid.replace(".", "_")


@dataclass
class Node:
    id: str
    gate: int
    question: str
    answer_type: str
    maps_to: str
    kind: str
    authority: str = ""
    ask_when: str = "True"
    choices: Optional[List[str]] = None
    consequence: str = ""
    warning_if_true: str = ""


@dataclass
class InterviewResult:
    profile: EntityProfile
    schedules_required: List[str]
    elections: List[dict]
    warnings: List[str]
    asked: List[str]
    skipped_gates: List[int]
    # Extras (not part of the plan's four outputs, but cheap and useful):
    flags: Dict[str, Any] = field(default_factory=dict)
    schedule_data: Dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------
# Loader + load-time validation
# --------------------------------------------------------------------------

def load_graph(path: Optional[str] = None) -> List[Node]:
    """Load and validate the question graph. Raises ValueError on any
    violation of the plan's validate-at-load discipline."""
    path = path or _DEFAULT_GRAPH_PATH
    with open(path, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    if not isinstance(doc, dict) or "questions" not in doc:
        raise ValueError(f"interview graph {path!r}: expected a mapping with "
                         "a 'questions' key")
    raw = doc["questions"]
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"interview graph {path!r}: 'questions' must be a "
                         "non-empty list")

    nodes: List[Node] = []
    for i, item in enumerate(raw):
        try:
            nodes.append(Node(
                id=item["id"], gate=int(item["gate"]),
                question=item["question"],
                answer_type=item["answer_type"], maps_to=item["maps_to"],
                kind=item["kind"], authority=item.get("authority", ""),
                ask_when=str(item.get("ask_when", "True")),
                choices=item.get("choices"),
                consequence=item.get("consequence", ""),
                warning_if_true=item.get("warning_if_true", ""),
            ))
        except KeyError as e:
            raise ValueError(f"interview graph node #{i} "
                             f"({item.get('id', '?')}): missing field {e}")

    # 1. unique ids
    seen = set()
    for n in nodes:
        if n.id in seen:
            raise ValueError(f"interview graph: duplicate question id {n.id!r}")
        seen.add(n.id)

    # 2. every gate 0-10 present
    gates = {n.gate for n in nodes}
    missing = sorted(set(range(11)) - gates)
    if missing:
        raise ValueError(f"interview graph: missing gate(s) {missing} — "
                         "every gate 0-10 must be present")

    allowed_names = {_uid(n.id) for n in nodes} | _DERIVED_NAMES
    for n in nodes:
        # 3. answer_type / kind / choices sanity
        if n.answer_type not in _ANSWER_TYPES:
            raise ValueError(f"{n.id}: unknown answer_type {n.answer_type!r} "
                             f"(allowed: {sorted(_ANSWER_TYPES)})")
        if n.kind not in _KINDS:
            raise ValueError(f"{n.id}: unknown kind {n.kind!r} "
                             f"(allowed: {sorted(_KINDS)})")
        if n.answer_type == "enum" and not n.choices:
            raise ValueError(f"{n.id}: answer_type 'enum' requires 'choices'")

        # 4. ask_when references only defined question ids / derived names
        try:
            tree = ast.parse(n.ask_when, mode="eval")
        except SyntaxError as e:
            raise ValueError(f"{n.id}: ask_when {n.ask_when!r} is not a valid "
                             f"expression: {e}")
        for sub in ast.walk(tree):
            if isinstance(sub, ast.Name) and sub.id not in allowed_names \
                    and sub.id not in ("True", "False", "None"):
                raise ValueError(
                    f"{n.id}: ask_when references undefined name {sub.id!r} "
                    "(not a question id or derived name)")

        # 5. maps_to targets: profile.<field> must be a real EntityProfile
        #    field; otherwise schedule.<name> / flag.<NAME> / none.
        mt = n.maps_to
        if mt.startswith("profile."):
            fname = mt[len("profile."):]
            if fname not in _PROFILE_FIELDS:
                raise ValueError(
                    f"{n.id}: maps_to {mt!r} — {fname!r} is not a field on "
                    "EntityProfile")
        elif mt != "none" and not mt.startswith(("schedule.", "flag.")):
            raise ValueError(f"{n.id}: maps_to {mt!r} must be 'none' or start "
                             "with 'profile.'/'schedule.'/'flag.'")
    return nodes


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

_BOOL_TRUE = {"true", "yes", "y", "1", "x", "t"}
_BOOL_FALSE = {"false", "no", "n", "0", "", "f", "none"}


def _coerce(node: Node, value: Any) -> Any:
    """Answer coercion with the question id in every failure.

    bool answers use a truthy/falsy STRING table — Python's bool("no") is
    True, which turned a dictated "no" to the tax-shelter question into
    is_tax_shelter=True and switched all of UNICAP on (red-team, confirmed).
    """
    if value is None:
        return None
    try:
        if node.answer_type == "decimal":
            if isinstance(value, bool):
                raise ValueError(f"expected a number, got bool {value!r}")
            d = Decimal(str(value))
            # NaN receipts crashed the derived-exemption comparison with a
            # raw InvalidOperation; -Infinity GRANTED the exemption
            # (round-3 fuzz, both confirmed)
            if not d.is_finite():
                raise ValueError(f"non-finite amount {value!r} rejected")
            return d
        if node.answer_type == "int":
            if isinstance(value, bool):
                raise ValueError(f"expected an integer, got bool {value!r}")
            return int(value)
        if node.answer_type == "bool":
            if isinstance(value, bool):
                return value
            s = str(value).strip().lower()
            if s in _BOOL_TRUE:
                return True
            if s in _BOOL_FALSE:
                return False
            raise ValueError(
                f"ambiguous yes/no answer {value!r} — use yes/no/true/false")
        if node.answer_type == "per_item":
            if isinstance(value, (str, bytes)) or not hasattr(value, "__iter__"):
                # list("abc") silently exploded a scalar into characters
                raise ValueError(
                    f"per-item answer must be a LIST of item dicts, got {value!r}")
            return list(value)
        return value
    except (ValueError, ArithmeticError, TypeError) as e:
        raise ValueError(f"{node.id}: cannot coerce answer {value!r} "
                         f"({node.answer_type}): {e}") from None


def _sec448_threshold(env: Dict[str, Any]) -> Decimal:
    """§448(c) threshold for Q0.2's year — reuses EntityProfile.THRESHOLDS
    via a temp profile (the plan's own instruction)."""
    year = env.get("Q0_2")
    return EntityProfile(tax_year=int(year) if year else 2026).sec448_threshold


def _derived(env: Dict[str, Any]) -> Dict[str, Any]:
    """Runner-computed names exposed to ask_when (and used for warnings)."""
    receipts = env.get("Q0_4")
    under = (receipts is not None
             and Decimal(str(receipts)) <= _sec448_threshold(env))
    exempt = under and not env.get("Q0_3")

    # Gate 1 consequence matrix (computed, not asked): SRM available only for
    # a pure reseller, de-minimis production incident to resale, or
    # private-label goods (§1.263A-3(a)(4)).
    produces = env.get("Q1_1a")
    if produces is None:
        srm_available: Optional[bool] = None   # Gate 1 not (yet) answered
    elif not produces or env.get("Q1_4"):
        srm_available = True          # pure reseller / private-label route
    elif env.get("Q1_2") is None:
        # a producer whose de minimis determination was never established:
        # UNKNOWN, not unavailable — the prior False here asserted "above de
        # minimis" for a question never asked (round-3 fuzz, confirmed)
        srm_available = None
    else:
        srm_available = (env.get("Q1_2") == "de_minimis"
                         and bool(env.get("Q1_3")))
    return {"small_business_exempt": exempt,
            "under_448c_threshold": under,
            "srm_available": srm_available}


def _eval_ask_when(expr: str, env: Dict[str, Any]) -> bool:
    # SAFETY NOTE: eval() is acceptable here because the YAML graph SHIPS WITH
    # THE TOOL (same trust level as this .py file) — it is not user input.
    # Builtins are stripped anyway, and load_graph() has already restricted
    # every referenced name to defined question ids / derived names.
    scope = dict(env)
    scope.update(_derived(env))
    try:
        return bool(eval(expr, {"__builtins__": {}}, scope))  # noqa: S307
    except TypeError:
        # An ordered comparison against a still-unanswered (None) prerequisite
        # (e.g. "Q0_2 <= 2025" before Q0.2 is answered): not askable yet.
        return False


def run_interview(answers: Dict[str, Any],
                  graph: Optional[List[Node]] = None) -> InterviewResult:
    """Walk the graph in document order against ``answers``
    (question id -> answer; per_item questions -> list of per-item dicts).

    Optional non-question key in ``answers``:
      * ``prior_elections``: {question_id: established prior-year answer} for
        METHOD-OF-ACCOUNTING sub-elections (Q0.6's "established sub-elections")
        — a differing current answer in a non-first year emits
        METHOD-CHANGE-3115-481A-REQUIRED naming that question id.
    """
    graph = graph if graph is not None else load_graph()
    prior_elections = answers.get("prior_elections") or {}
    if not isinstance(prior_elections, dict):
        # a truthy non-dict crashed (int) or silently compared against
        # nothing (str) — round-3 fuzz, confirmed
        raise ValueError("prior_elections must be a dict of "
                         "{question_id: established prior-year answer}, got "
                         f"{type(prior_elections).__name__}")

    env: Dict[str, Any] = {_uid(n.id): None for n in graph}
    # A typo'd answer key silently un-answers its question (red-team) —
    # surface every key that matches no question id.
    known_ids = {n.id for n in graph} | {"prior_elections"}
    unknown_keys = [k for k in answers if k not in known_ids]
    warnings_head = [f"UNRECOGNIZED-ANSWER-KEY: {k!r} matches no question id "
                     f"— that answer was IGNORED (check for typos/spacing)."
                     for k in unknown_keys]
    asked: List[str] = []
    warnings: List[str] = list(warnings_head)
    elections: List[dict] = []
    flags: Dict[str, Any] = {}
    schedule_data: Dict[str, Any] = {}
    profile_kwargs: Dict[str, Any] = {}
    skipped: set = set()

    for node in graph:
        # Gate 0 exemption short-circuit: §263A (including (f)) is entirely
        # off — Gates 1, 2, 3, 6, 7 never asked. Gates 4/5/8/9/10 still run.
        if node.gate in _EXEMPT_SKIPPED_GATES \
                and _derived(env)["small_business_exempt"]:
            skipped.add(node.gate)
            continue

        if not _eval_ask_when(node.ask_when, env):
            continue

        asked.append(node.id)
        answer = _coerce(node, answers.get(node.id))
        if answer is None:
            continue                     # asked but unanswered: nothing to map
        env[_uid(node.id)] = answer

        if node.answer_type == "enum" and node.choices \
                and answer not in node.choices:
            # Warn AND refuse to route — the bogus value previously flowed
            # straight into the profile (entity_type='TOTALLY_BOGUS' reached
            # compute_59e's gating; red-team, confirmed).
            warnings.append(f"ANSWER-OUT-OF-MENU: {node.id} answer "
                            f"{answer!r} not in {node.choices} — NOT applied; "
                            f"the question remains effectively unanswered.")
            env[_uid(node.id)] = None
            continue

        # Route the answer
        mt = node.maps_to
        if mt.startswith("profile."):
            profile_kwargs[mt[len("profile."):]] = answer
        elif mt.startswith("flag."):
            flags[mt[len("flag."):]] = answer
        elif mt.startswith("schedule."):
            schedule_data[mt[len("schedule."):]] = answer

        if node.kind in ("ELECTION", "METHOD-OF-ACCOUNTING"):
            # an empty per-item list is "no items elected" — recording it
            # put content-free elections on the workpaper summary (fuzz)
            if not (node.answer_type == "per_item" and not answer):
                elections.append({"id": node.id, "kind": node.kind,
                                  "answer": answer})

        if node.warning_if_true and answer:
            warnings.append(f"{node.warning_if_true}: {node.id} — "
                            f"{node.consequence or node.question}")

    derived = _derived(env)
    exempt = derived["small_business_exempt"]
    srm_available = derived["srm_available"]
    first_year = bool(env.get("Q0_5"))
    prior_method = env.get("Q0_6")
    this_method = env.get("Q2_2")

    # The exemption walk vs the returned profile: with Q0.4 unanswered, the
    # gates all ran but EntityProfile's receipts default (0) reports exempt —
    # downstream UNICAP silently switches OFF for a fully-interviewed
    # taxpayer (round-3 fuzz, confirmed). Warn loudly; nothing can invent
    # the missing receipts figure.
    if "Q0.4" in asked and env.get("Q0_4") is None:
        warnings.append(
            "EXEMPTION-UNDETERMINED: Q0.4 (aggregated 3-yr average gross "
            "receipts) was not answered — the §448(c) exemption CANNOT be "
            "determined. The returned profile's receipts default to $0, "
            "which downstream reads as EXEMPT (all §263A off); supply Q0.4 "
            "before relying on any computation.")

    # Answers supplied for questions the graph decided NOT to ask are never
    # applied (verified) — but silence hid real contradictions (Q0.5=first
    # year AND Q0.6=prior method both answered; fuzz). Warn per key.
    answered_ids = {k for k in answers if k != "prior_elections"}
    for qid in sorted(answered_ids - set(asked)):
        if qid in known_ids:
            warnings.append(
                f"ANSWER-FOR-UNASKED-QUESTION: {qid} was answered but the "
                f"graph never asked it (skipped gate or unmet ask_when) — "
                f"the answer was NOT applied. If you expected it to count, "
                f"check the controlling answers upstream of it.")

    # Gate 2 menu constraint / Gate 1 consequence matrix: SRM chosen while the
    # matrix says it was never available.
    if this_method == "SRM" and srm_available is False:
        warnings.append(
            "SRM-METHOD-CONFLICT: Q2.2 = SRM but Gate 1's consequence matrix "
            "makes SRM unavailable (producer above de minimis, no "
            "incident-to-resale route, no private-label goods) — SPM/MSPM "
            "only (§1.263A-3(a)(4)).")
    elif this_method == "SRM" and srm_available is None \
            and env.get("Q1_1a"):
        warnings.append(
            "SRM-AVAILABILITY-UNKNOWN: Q2.2 = SRM but the de minimis "
            "determination (Q1.2) was never established for this producer — "
            "the §1.263A-3(a)(4) availability gate cannot be evaluated. "
            "Resolve Gate 1 before relying on SRM figures.")

    # §1.263A-1(h)(3)(ii): a reseller must use the labor-based SSCM ratio.
    if env.get("Q2_8b") == "production_cost" and env.get("Q1_1b") \
            and not env.get("Q1_1a"):
        warnings.append(
            "SSCM-RATIO-RESELLER: the production-cost allocation ratio is a "
            "producer-only formula (§1.263A-1(h)(3)(ii)) — a reseller "
            "electing it is a regulation violation; use the labor-based "
            "ratio.")

    # Q0.6a reconciliation (runner-computed; never asked). First-§263A-year
    # taxpayers ADOPT methods — Q0.6 was never asked, no 3115 posture at all.
    if not first_year and prior_method is not None:
        if prior_method == "none_noncompliant" or (
                prior_method == "SRM" and srm_available is False):
            warnings.append(
                "PRIOR-METHOD-IMPERMISSIBLE: Q0.6 prior_year_method "
                f"{prior_method!r} was never legally available for this "
                "activity profile — discovered impermissible method, an "
                "error-correction event under §446(e) (3115 with a different "
                "DCN/§481(a) posture than an elective switch).")
        elif this_method is not None and this_method != prior_method:
            warnings.append(
                "METHOD-CHANGE-3115-481A-REQUIRED: Q2.2 method "
                f"{this_method!r} differs from established prior-year method "
                f"{prior_method!r} — Form 3115, §481(a) adjustment, and "
                "§1.263A-7 revalued beginning-inventory inputs required.")

    # Established prior-year sub-elections (Q0.6's "established
    # sub-elections") vs this year's METHOD-OF-ACCOUNTING answers.
    if not first_year:
        for e in elections:
            if e["kind"] != "METHOD-OF-ACCOUNTING" or e["id"] == "Q2.2":
                continue
            if e["id"] in prior_elections \
                    and e["answer"] != prior_elections[e["id"]]:
                warnings.append(
                    f"METHOD-CHANGE-3115-481A-REQUIRED: {e['id']} answer "
                    f"{e['answer']!r} differs from established prior-year "
                    f"answer {prior_elections[e['id']]!r} — Form 3115 / "
                    "§481(a) required.")

    # Schedules Phase A must ingest for this taxpayer (only what the answers
    # require). MSPM/SRM need nothing beyond the profile scalars.
    schedules: List[str] = []
    if env.get("Q6_0"):                       # self-constructed assets
        schedules += ["fixed_assets", "cip"]
    if env.get("Q7_0"):                       # §263A(f) candidates
        schedules += ["cip", "debt"]
    if env.get("Q8_0"):
        schedules += ["re"]
    if env.get("Q9_0"):
        schedules += ["transaction_costs", "intangibles", "startup"]
    if env.get("Q9_7a"):
        schedules += ["startup"]
    if env.get("Q9_9a"):
        schedules += ["ppa"]
    if env.get("Q10_2"):                      # non-empty §59(e) elections
        schedules += ["qualified_expenditures"]
    schedules += ["btd"]                      # BTDs always recommended
    seen: set = set()
    schedules_required = [s for s in schedules
                          if not (s in seen or seen.add(s))]

    if exempt:
        skipped |= set(_EXEMPT_SKIPPED_GATES)

    profile = EntityProfile(**profile_kwargs)
    return InterviewResult(
        profile=profile,
        schedules_required=schedules_required,
        elections=elections,
        warnings=warnings,
        asked=asked,
        skipped_gates=sorted(skipped),
        flags=flags,
        schedule_data=schedule_data,
    )


# --------------------------------------------------------------------------
# Optional CLI prompt mode (nice-to-have; the answers-dict API is the
# required deliverable): python -m financial_tools.cap263a.interview
# --------------------------------------------------------------------------

def _prompt(node: Node) -> Any:
    label = f"[{node.id}] {node.question}"
    if node.answer_type == "bool":
        raw = input(f"{label} [y/n/enter=skip] ").strip().lower()
        return None if not raw else raw in ("y", "yes", "true", "1")
    if node.answer_type == "enum":
        raw = input(f"{label} {node.choices} ").strip()
        return raw or None
    if node.answer_type == "per_item":
        print(f"{label} (per-item sub-tree — enter item count, 0/enter=none)")
        raw = input("  count: ").strip()
        n = int(raw) if raw.isdigit() else 0
        items = []
        for i in range(n):
            items.append({"note": input(f"  item {i + 1} notes: ").strip()})
        return items
    raw = input(f"{label} ").strip()
    return raw or None


def main() -> None:                                   # pragma: no cover
    graph = load_graph()
    answers: Dict[str, Any] = {}
    env: Dict[str, Any] = {_uid(n.id): None for n in graph}
    for node in graph:
        if node.gate in _EXEMPT_SKIPPED_GATES \
                and _derived(env)["small_business_exempt"]:
            continue
        if not _eval_ask_when(node.ask_when, env):
            continue
        val = _prompt(node)
        if val is not None:
            answers[node.id] = val
            env[_uid(node.id)] = _coerce(node, val)
    result = run_interview(answers, graph)
    print("\n--- InterviewResult ---")
    print("asked:", len(result.asked), "questions")
    print("skipped gates:", result.skipped_gates)
    print("schedules required:", result.schedules_required)
    print("elections:", *result.elections, sep="\n  ")
    print("warnings:", *result.warnings, sep="\n  ")
    print("profile:", result.profile)


if __name__ == "__main__":                            # pragma: no cover
    main()
