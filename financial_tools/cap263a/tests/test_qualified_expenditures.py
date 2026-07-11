"""Phase H golden tests — compute_59e (§59(e)) + the periods YAML.

Every expected figure is hand-derived in the test docstrings.
"""

from decimal import Decimal

from financial_tools.cap263a.engines.qualified_expenditures import (
    C_CORP_GATE_WARNING, compute_59e, load_periods)
from financial_tools.cap263a.model import QualifiedExpenditureElection


def _el(item_id="Q1", category="idc", amount="120000", **kw):
    return QualifiedExpenditureElection(item_id=item_id, category=category,
                                        amount=Decimal(amount), elected=True,
                                        election_year=2026, **kw)


def test_c_corp_no_exposure_gated_out():
    """GATE FIRST: a C corp with no individual-AMT-exposed owners has no
    current-law §59(e) use (corporate AMT repealed by TCJA; CAMT §55/§56A
    does not use §57/§59(e) preference items) — no items, no schedule,
    just the CAMT warning."""
    out = compute_59e([_el()], entity_type="c_corp",
                      individual_amt_exposure=False)
    assert out["items"] == []
    assert out["amortizable_items"] == []
    assert out["warnings"] == [C_CORP_GATE_WARNING]
    assert "CAMT" in out["warnings"][0]


def test_individual_idc_120000_over_60_months():
    """Individual electing §59(e) on IDC 120,000: 60-month straight-line
    (§59(e)(4)/§263(c)); year-1 = 120,000 × 12/60 / 2 = 12,000 under the
    documented mid-year-start proxy (no month data in the schedule)."""
    out = compute_59e([_el()], entity_type="individual",
                      individual_amt_exposure=True)
    [row] = out["items"]
    assert row["recovery_months"] == 60
    assert row["first_year_amortization"] == Decimal("12000")
    [item] = out["amortizable_items"]
    assert item.category == "qualified_expenditure"
    assert item.convention == "mid-year"
    assert item.start_year == 2026


def test_mining_item_flags_57_cite_unverified():
    """Mining exploration election → §57-MINING-CITE-UNVERIFIED (exact
    §57(a) subparagraph unconfirmed against primary text); schedule still
    computed: 120-month period, 50,000 × 12/120 / 2 = 2,500 year-1."""
    out = compute_59e([_el(item_id="M1", category="mining_exploration",
                           amount="50000")],
                      entity_type="individual", individual_amt_exposure=True)
    [row] = out["items"]
    assert row["recovery_months"] == 120
    assert row["first_year_amortization"] == Decimal("2500")
    assert "§57-MINING-CITE-UNVERIFIED" in row["flags"]
    assert any("§57-MINING-CITE-UNVERIFIED" in w for w in out["warnings"])


def test_overlap_with_174a_election_flags_conflict():
    """re_domestic item also carrying a §174A(c) election →
    §59E-174A-ELECTION-CONFLICT, routed to SME; still computed (120 months)
    with the flag leading."""
    out = compute_59e([_el(item_id="R1", category="re_domestic",
                           amount="60000")],
                      entity_type="s_corp", individual_amt_exposure=True,
                      overlapping_174A_items=frozenset({"R1"}))
    [row] = out["items"]
    assert "§59E-174A-ELECTION-CONFLICT" in row["flags"]
    assert row["recovery_months"] == 120       # still computed, flag leads
    assert any("§59E-174A-ELECTION-CONFLICT" in w for w in out["warnings"])


def test_non_elected_items_skipped():
    el = QualifiedExpenditureElection(item_id="X1", category="idc",
                                      amount=Decimal("10000"), elected=False,
                                      election_year=2026)
    out = compute_59e([el], entity_type="individual",
                      individual_amt_exposure=True)
    assert out["items"] == []
    assert out["amortizable_items"] == []


def test_periods_yaml_table():
    """The YAML carries exactly the §59(e)(2)(A)-(E) table: circulation 36 /
    re_domestic 120 / idc 60 / mining_exploration 120 /
    mining_development 120, each with an authority string; the R&E entry
    notes the OBBBA re-pointing to §174A(a)."""
    periods = load_periods()
    assert {k: v["months"] for k, v in periods.items()} == {
        "circulation": 36, "re_domestic": 120, "idc": 60,
        "mining_exploration": 120, "mining_development": 120}
    assert all(v.get("authority") for v in periods.values())
    assert "174A(a)" in periods["re_domestic"]["authority"]
