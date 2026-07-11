"""Phase E interview layer: graph validation, decision-tree paths, warnings,
and the golden MSPM full path (regulation Example 1, §1.263A-2(c)(3)(vi)(A))."""

from decimal import Decimal

import pytest
import yaml

from financial_tools.cap263a.interview import load_graph, run_interview


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _minimal_graph_doc():
    """Smallest structurally-valid graph: one node per gate 0-10."""
    return {"questions": [
        {"id": f"Q{g}.1", "gate": g, "question": f"gate {g} question?",
         "answer_type": "bool", "maps_to": "none", "kind": "FACT",
         "ask_when": "True"}
        for g in range(11)
    ]}


def _write(tmp_path, doc):
    p = tmp_path / "graph.yaml"
    p.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
    return str(p)


def _base_answers(**overrides):
    """A non-exempt first-year producer baseline; tests override as needed."""
    a = {
        "Q0.1": "c_corp", "Q0.2": 2026, "Q0.3": False,
        "Q0.4": Decimal("40000000"),      # above the 2026 $32M threshold
        "Q0.5": True,                     # first §263A year -> adoption
        "Q1.1a": True, "Q1.1b": False, "Q1.4": False,
        "Q2.1": "FIFO", "Q2.2": "MSPM", "Q2.4": False, "Q2.5": False,
        "Q2.6a": False, "Q2.7a": "direct_material", "Q2.7b": False,
        "Q2.8a": False, "Q2.9": True,
        "Q4.1a": True, "Q4.1b": False, "Q4.2a": False,
        "Q4.4a": False, "Q5.1": False, "Q5.2": False,
        "Q6.0": False, "Q7.0": False, "Q8.0": False,
        "Q9.0": False, "Q9.7a": False, "Q9.9a": False, "Q9.10": [],
        "Q10.1": False,
    }
    a.update(overrides)
    return a


MSPM_QIDS = [f"Q3.{i}" for i in range(2, 11)]   # Q3.2 .. Q3.10


# --------------------------------------------------------------------------
# 1. Graph validation
# --------------------------------------------------------------------------

def test_shipped_graph_loads_and_covers_all_gates():
    nodes = load_graph()
    gates = {n.gate for n in nodes}
    assert gates == set(range(11))
    ids = [n.id for n in nodes]
    assert len(ids) == len(set(ids))
    # spot-check the plan's numbered questions (incl. 2026-07-09 additions)
    for qid in ["Q0.6a", "Q1.4", "Q2.6b", "Q3.10", "Q3.12", "Q3.15", "Q3.22",
                "Q4.1b", "Q5.3", "Q6.5", "Q7.10", "Q7.19", "Q7.23", "Q8.4",
                "Q9.9b", "Q9.10", "Q10.4"]:
        assert qid in ids, f"missing plan question {qid}"
    # per-item sub-trees are typed per_item
    by_id = {n.id: n for n in nodes}
    for qid in ["Q3.19", "Q3.20", "Q3.21", "Q3.22", "Q6.1", "Q7.1", "Q7.20",
                "Q8.6", "Q9.1", "Q10.2"]:
        assert by_id[qid].answer_type == "per_item"


def test_broken_graph_undefined_ask_when_reference(tmp_path):
    doc = _minimal_graph_doc()
    doc["questions"][3]["ask_when"] = "Q99_9 and Q0_1"
    with pytest.raises(ValueError, match="undefined name 'Q99_9'"):
        load_graph(_write(tmp_path, doc))


def test_broken_graph_nonexistent_profile_field(tmp_path):
    doc = _minimal_graph_doc()
    doc["questions"][5]["maps_to"] = "profile.not_a_real_field"
    with pytest.raises(ValueError, match="not_a_real_field.*not a field"):
        load_graph(_write(tmp_path, doc))


def test_broken_graph_missing_gate(tmp_path):
    doc = _minimal_graph_doc()
    doc["questions"] = [q for q in doc["questions"] if q["gate"] != 7]
    with pytest.raises(ValueError, match=r"missing gate\(s\) \[7\]"):
        load_graph(_write(tmp_path, doc))


def test_broken_graph_duplicate_id(tmp_path):
    doc = _minimal_graph_doc()
    doc["questions"].append(dict(doc["questions"][0]))
    with pytest.raises(ValueError, match="duplicate question id"):
        load_graph(_write(tmp_path, doc))


# --------------------------------------------------------------------------
# 2. Exempt path: small taxpayer short-circuit
# --------------------------------------------------------------------------

def test_small_business_exempt_short_circuit():
    answers = {
        "Q0.1": "s_corp", "Q0.2": 2026, "Q0.3": False,
        "Q0.4": Decimal("1000000"), "Q0.5": True,
        "Q4.1a": False, "Q5.1": False, "Q5.2": False,
        "Q8.0": False, "Q9.0": False, "Q9.7a": False, "Q9.9a": False,
        "Q10.1": False,
    }
    r = run_interview(answers)
    assert r.skipped_gates == [1, 2, 3, 6, 7]
    # no §263A gate question ever asked
    assert not any(q.startswith(("Q1.", "Q2.", "Q3.", "Q6.", "Q7."))
                   for q in r.asked)
    # Gates 4 and 5 (§263(a)/§266 — not §263A provisions) still run
    assert "Q4.1a" in r.asked and "Q5.1" in r.asked
    assert r.profile.avg_gross_receipts == Decimal("1000000")
    assert r.profile.small_business_exempt
    assert len(r.asked) <= 25          # "exempt taxpayer ... and is done"
    assert r.warnings == []


# --------------------------------------------------------------------------
# 3. Pure reseller path: SRM available, no MSPM questions
# --------------------------------------------------------------------------

def test_pure_reseller_never_sees_mspm_questions():
    answers = _base_answers(
        **{"Q1.1a": False, "Q1.1b": True, "Q2.2": "SRM",
           "Q3.11": Decimal("2100000"), "Q3.12": Decimal("260000"),
           "Q3.13": Decimal("190000"), "Q3.14": Decimal("400000"),
           "Q3.15": Decimal("500000"), "Q3.16": False,
           "Q3.17": "none", "Q3.18a": False,
           "Q3.19": [], "Q3.20": [], "Q3.21": [], "Q3.22": []})
    r = run_interview(answers)
    assert "Q2.7a" not in r.asked and "Q2.7b" not in r.asked
    assert not any(q in r.asked for q in MSPM_QIDS)
    # Q1.2 needs BOTH produce and resale; a pure reseller is never asked it
    assert "Q1.2" not in r.asked
    # producer-only $200k de minimis not asked either
    assert "Q2.5" not in r.asked
    # SRM questions asked, SRM accepted without conflict
    for qid in ["Q3.11", "Q3.12", "Q3.13", "Q3.14", "Q3.15"]:
        assert qid in r.asked
    assert r.profile.method == "SRM"
    assert not any(w.startswith("SRM-METHOD-CONFLICT") for w in r.warnings)
    assert r.profile.purchasing_costs == Decimal("260000")


# --------------------------------------------------------------------------
# 4. Method-conflict path: SRM chosen but never available
# --------------------------------------------------------------------------

def test_srm_method_conflict_warning():
    answers = _base_answers(
        **{"Q1.1a": True, "Q1.1b": True, "Q1.2": "more_than_de_minimis",
           "Q1.4": False, "Q2.2": "SRM"})
    r = run_interview(answers)
    assert any(w.startswith("SRM-METHOD-CONFLICT") for w in r.warnings)


def test_private_label_reopens_srm_for_big_producer():
    # (a)(4)(iii): private-label is the carve-out that can qualify a
    # MORE-than-de-minimis producer for SRM — Q1.4 asked always.
    answers = _base_answers(
        **{"Q1.1a": True, "Q1.1b": True, "Q1.2": "more_than_de_minimis",
           "Q1.4": True, "Q2.2": "SRM"})
    r = run_interview(answers)
    assert not any(w.startswith("SRM-METHOD-CONFLICT") for w in r.warnings)


# --------------------------------------------------------------------------
# 5. 3115 trigger vs first-year adoption
# --------------------------------------------------------------------------

def test_method_change_emits_3115_warning():
    answers = _base_answers(**{"Q0.5": False, "Q0.6": "SPM", "Q2.2": "MSPM"})
    r = run_interview(answers)
    hits = [w for w in r.warnings
            if w.startswith("METHOD-CHANGE-3115-481A-REQUIRED")]
    assert hits and "Q2.2" in hits[0]
    assert r.profile.prior_year_method == "SPM"


def test_first_year_adoption_emits_no_3115_warning():
    answers = _base_answers(**{"Q0.5": True, "Q2.2": "MSPM"})
    r = run_interview(answers)
    assert "Q0.6" not in r.asked            # adoption: prior method not asked
    assert not any("METHOD-CHANGE-3115-481A-REQUIRED" in w
                   for w in r.warnings)
    assert not any("PRIOR-METHOD-IMPERMISSIBLE" in w for w in r.warnings)


def test_prior_method_impermissible_reconciliation():
    # Q0.6a: prior year on SRM, but Gate 1's matrix says SRM was NEVER
    # available -> discovered impermissible method, not an elective switch.
    answers = _base_answers(
        **{"Q0.5": False, "Q0.6": "SRM", "Q2.2": "MSPM",
           "Q1.1a": True, "Q1.1b": True, "Q1.2": "more_than_de_minimis",
           "Q1.4": False})
    r = run_interview(answers)
    assert any(w.startswith("PRIOR-METHOD-IMPERMISSIBLE") for w in r.warnings)


# --------------------------------------------------------------------------
# 6. Golden MSPM full path — regulation Example 1 (Taxpayer P) figures
# --------------------------------------------------------------------------

def test_golden_mspm_full_path():
    answers = _base_answers(
        **{"Q2.2": "MSPM", "Q2.7a": "direct_material", "Q2.7b": False,
           "Q2.8a": True, "Q2.8b": "labor", "Q2.8c": False, "Q2.8d": False,
           "Q3.2": Decimal("2500000"),    # pre-production §471 incurred
           "Q3.3": Decimal("7500000"),    # production §471 incurred
           "Q3.4": Decimal("200000"),     # pre-production additional §263A
           "Q3.5": Decimal("800000"),     # production additional §263A
           "Q3.6": Decimal("1000000"),    # pre-production §471 on hand
           "Q3.7": Decimal("2000000"),    # production §471 on hand
           "Q3.8": Decimal("400000"),     # beginning DM not yet in production
           "Q3.9": Decimal("800000"),     # ending DM not yet in production
           "Q3.10": Decimal("1900000")})  # DM purchased during the year
    r = run_interview(answers)
    p = r.profile
    assert p.method == "MSPM"
    assert p.pre_production_471 == Decimal("2500000")
    assert p.production_471 == Decimal("7500000")
    assert p.pre_production_additional_263A == Decimal("200000")
    assert p.production_additional_263A == Decimal("800000")
    assert p.pre_production_471_on_hand == Decimal("1000000")
    assert p.production_471_on_hand == Decimal("2000000")
    assert p.beginning_DM_not_yet_in_production == Decimal("400000")
    assert p.ending_DM_not_yet_in_production == Decimal("800000")
    assert p.DM_purchased_during_year == Decimal("1900000")
    assert p.mspm_mixed_split_method == "direct_material"
    assert p.mspm_90pct_split_election is False
    assert p.sscm_ratio_method == "labor"
    # SPM/SRM balance questions never asked on the MSPM path
    assert "Q3.1" not in r.asked and "Q3.11" not in r.asked
    # every MSPM balance question was actually asked
    for qid in MSPM_QIDS:
        assert qid in r.asked
    # MSPM needs nothing beyond profile scalars; BTDs always recommended
    assert r.schedules_required == ["btd"]
    # method + sub-elections recorded in the election summary
    election_ids = {e["id"] for e in r.elections}
    assert {"Q2.2", "Q2.7a", "Q2.8a", "Q2.8b"} <= election_ids
    assert r.warnings == []


def test_producer_200k_de_minimis_skips_ratio_inputs():
    answers = _base_answers(**{"Q2.5": True})
    r = run_interview(answers)
    assert "Q2.5" in r.asked
    # Q2.6-Q2.8 and Gate 3 ratio inputs skipped
    for qid in ["Q2.6a", "Q2.7a", "Q2.8a"] + MSPM_QIDS:
        assert qid not in r.asked


# --------------------------------------------------------------------------
# 7. Gate 10 gating
# --------------------------------------------------------------------------

def test_gate10_skipped_for_pure_c_corp():
    answers = _base_answers(**{"Q0.1": "c_corp", "Q10.1": False})
    r = run_interview(answers)
    assert "Q10.1" in r.asked
    for qid in ["Q10.2", "Q10.3", "Q10.4"]:
        assert qid not in r.asked


def test_gate10_asked_for_amt_exposed_passthrough():
    answers = _base_answers(
        **{"Q0.1": "partnership", "Q10.1": True,
           "Q10.2": [{"category": "idc", "amount": "100000",
                      "elect": True}],
           "Q10.4": False})
    r = run_interview(answers)
    assert "Q10.2" in r.asked and "Q10.4" in r.asked
    assert "qualified_expenditures" in r.schedules_required
