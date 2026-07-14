"""§263A farming engine (§263A(d)/(e); Reg. §1.263A-4) — every treatment
branch: the §263A(i) small-business early exit, the §447/§448(a)(3)
unknown-status conservative path, animal exempt vs §447-capitalize, plant
≤2-year exempt vs the flush-language carve-out, >2-year capitalize, the
period-unknown conservative capitalize, the §263A(d)(3) election out
(honored vs barred, both consequence warnings once per run), the negative
guard, and the totals tie. Golden figures hand-computed in each
docstring."""

from decimal import Decimal

from financial_tools.cap263a.analysis import EntityProfile
from financial_tools.cap263a.engines.farming_unicap import (
    FarmGroup, compute_farming_unicap)


def _p(**overrides):
    """A profile that is NOT small-business exempt (TY 2026 threshold is
    $32,000,000; $50,000,000 exceeds it) so the per-group logic runs."""
    kw = dict(avg_gross_receipts=Decimal("50000000"))
    kw.update(overrides)
    return EntityProfile(**kw)


def _plant(gid, amount, **overrides):
    kw = dict(group_id=gid, description=gid, kind="plant",
              preproductive_costs=Decimal(str(amount)))
    kw.update(overrides)
    return FarmGroup(**kw)


def _animal(gid, amount, **overrides):
    kw = dict(group_id=gid, description=gid, kind="animal",
              preproductive_costs=Decimal(str(amount)))
    kw.update(overrides)
    return FarmGroup(**kw)


# --- step 1a: §263A(i) small-business early exit ------------------------------

def test_small_business_early_exit():
    """$5M avg receipts <= the $32M TY-2026 §448(c) threshold and not a tax
    shelter -> exempt: everything deducts (10,000 + 4,000 = 14,000), zero
    capitalization, no items/questions, and the §263A(i) note — even
    though required_447_accrual is None and a group is a >2-year plant."""
    groups = [_plant("P1", 10000, preproductive_period_over_2yr=True),
              _animal("A1", 4000)]
    out = compute_farming_unicap(
        groups, _p(avg_gross_receipts=Decimal("5000000")))
    assert out["exempt"] is True
    assert "§263A(i)" in out["note"]
    assert "farming UNICAP off" in out["note"]
    assert out["items"] == []
    assert out["open_questions"] == []
    assert out["capitalized_total"] == Decimal("0")
    assert out["deductible_total"] == Decimal("14000")


def test_small_business_exit_threshold_estimate_warning():
    """A tax year with no published §448(c) figure on file draws the
    threshold-estimate warning on the exempt path (mirrors
    analysis.compute_unicap)."""
    out = compute_farming_unicap(
        [_animal("A1", 1000)],
        _p(avg_gross_receipts=Decimal("5000000"), tax_year=2030))
    assert out["exempt"] is True
    assert any("§448(c) threshold" in w for w in out["warnings"])


def test_tax_shelter_barred_from_small_business_exemption():
    """A tax shelter with $1M receipts is NOT small-business exempt
    (§1.263A-1(b)(1)/(j)); its animal group must capitalize even with
    required_447_accrual explicitly False (the §448(a)(3) shelter bar)."""
    out = compute_farming_unicap(
        [_animal("A1", 4000)],
        _p(avg_gross_receipts=Decimal("1000000"), is_tax_shelter=True),
        required_447_accrual=False)
    assert out["exempt"] is False
    assert out["items"][0]["treatment"] == "animal_capitalize_447"
    assert out["capitalized_total"] == Decimal("4000")


# --- step 1b: §447/§448(a)(3) status gate -------------------------------------

def test_447_none_conservative_question_and_flag():
    """required_447_accrual None (non-shelter): exactly one open question
    naming §447/required_447_accrual, and the animal group capitalizes
    CONSERVATIVELY with flag 447-STATUS-UNKNOWN."""
    out = compute_farming_unicap([_animal("A1", 6000)], _p())
    row = out["items"][0]
    assert row["treatment"] == "animal_capitalize_447"
    assert "447-STATUS-UNKNOWN" in row["flags"]
    assert out["capitalized_total"] == Decimal("6000")
    assert len(out["open_questions"]) == 1
    q = out["open_questions"][0]["question"]
    assert "§447" in q and "required_447_accrual" in q


def test_447_none_moot_for_tax_shelter():
    """required_447_accrual None but is_tax_shelter True: the §447 answer
    cannot change any treatment (the flush-language bar applies
    regardless), so NO question and NO 447-STATUS-UNKNOWN flag — the
    animal still capitalizes under the shelter bar."""
    out = compute_farming_unicap(
        [_animal("A1", 6000)], _p(is_tax_shelter=True))
    row = out["items"][0]
    assert row["treatment"] == "animal_capitalize_447"
    assert "447-STATUS-UNKNOWN" not in row["flags"]
    assert out["open_questions"] == []


# --- step 2b: animals (§263A(d)(1)(A)(ii)) ------------------------------------

def test_animal_exempt_deduct():
    """Not §447-required, not a shelter -> animals are exempt: 8,000
    deducts under §263A(d)(1)(A)(ii), nothing capitalized, no flags."""
    out = compute_farming_unicap([_animal("A1", 8000)], _p(),
                                 required_447_accrual=False)
    row = out["items"][0]
    assert row["treatment"] == "animal_exempt_deduct"
    assert "(d)(1)(A)(ii)" in row["authority"]
    assert row["flags"] == []
    assert out["deductible_total"] == Decimal("8000")
    assert out["capitalized_total"] == Decimal("0")
    assert out["open_questions"] == []


def test_animal_capitalize_447_explicit():
    """required_447_accrual True: the animal exception is unavailable
    (§263A(d)(1) flush language) — 8,000 capitalizes; the status is
    KNOWN, so no 447-STATUS-UNKNOWN flag and no open question."""
    out = compute_farming_unicap([_animal("A1", 8000)], _p(),
                                 required_447_accrual=True)
    row = out["items"][0]
    assert row["treatment"] == "animal_capitalize_447"
    assert "flush language" in row["authority"]
    assert "447-STATUS-UNKNOWN" not in row["flags"]
    assert out["capitalized_total"] == Decimal("8000")
    assert out["open_questions"] == []


# --- step 2c: plants ----------------------------------------------------------

def test_plant_short_period_exempt():
    """preproductive_period_over_2yr False, no §447 bar: 2,500 deducts
    under §263A(d)(1)(A)(i)."""
    out = compute_farming_unicap(
        [_plant("P1", 2500, preproductive_period_over_2yr=False)], _p(),
        required_447_accrual=False)
    row = out["items"][0]
    assert row["treatment"] == "plant_exempt_deduct"
    assert "(d)(1)(A)(i)" in row["authority"]
    assert out["deductible_total"] == Decimal("2500")


def test_plant_short_period_447_flush_carveout():
    """preproductive_period_over_2yr False but required_447_accrual True:
    the flush language of §263A(d)(1) denies the exception for BOTH
    prongs — the short-period plant STILL capitalizes (conservative
    reading), flagged 263AD1-FLUSH-READING."""
    out = compute_farming_unicap(
        [_plant("P1", 2500, preproductive_period_over_2yr=False)], _p(),
        required_447_accrual=True)
    row = out["items"][0]
    assert row["treatment"] == "plant_capitalize_447"
    assert "263AD1-FLUSH-READING" in row["flags"]
    assert "flush language" in row["authority"]
    assert out["capitalized_total"] == Decimal("2500")
    assert out["deductible_total"] == Decimal("0")


def test_plant_over_2yr_capitalize():
    """preproductive_period_over_2yr True: 12,000 of preproductive costs
    capitalize (§263A(d)/(e)(3)) regardless of §447 status; recovery is
    out of scope (the amount attaches to the plant's basis)."""
    out = compute_farming_unicap(
        [_plant("P1", 12000, preproductive_period_over_2yr=True)], _p(),
        required_447_accrual=False)
    row = out["items"][0]
    assert row["treatment"] == "preproductive_capitalize"
    assert "§263A(e)(3)" in row["authority"]
    assert row["flags"] == []
    assert out["capitalized_total"] == Decimal("12000")
    assert out["open_questions"] == []


def test_plant_period_none_conservative():
    """preproductive_period_over_2yr None: open question (is the crop on
    the IRS >2-year nationwide-weighted-average list?) and the 9,000
    capitalizes CONSERVATIVELY with flag PREPRODUCTIVE-PERIOD-UNKNOWN —
    never silently deducted on missing facts."""
    out = compute_farming_unicap([_plant("P1", 9000)], _p(),
                                 required_447_accrual=False)
    row = out["items"][0]
    assert row["treatment"] == "open_question_capitalize_pending"
    assert "PREPRODUCTIVE-PERIOD-UNKNOWN" in row["flags"]
    assert out["capitalized_total"] == Decimal("9000")
    q = out["open_questions"][0]["question"]
    assert "preproductive_period_over_2yr" in q
    assert "§263A(e)(3)(B)" in q


# --- step 2d: §263A(d)(3) election out ----------------------------------------

def test_election_out_honored_and_consequences_fire_once():
    """Two >2-year plant groups covered by the election, no §447 bar: both
    deduct (7,000 + 3,000 = 10,000) as election_out_deduct, and EACH
    consequence warning (ADS §263A(e)(2); §1245 recharacterization
    §263A(e)(1)) fires exactly ONCE for the run, not per group."""
    groups = [_plant("P1", 7000, preproductive_period_over_2yr=True,
                     in_election_out_year=True),
              _plant("P2", 3000, preproductive_period_over_2yr=True,
                     in_election_out_year=True)]
    out = compute_farming_unicap(groups, _p(), required_447_accrual=False,
                                 election_out_263Ad3=True)
    assert all(r["treatment"] == "election_out_deduct" for r in out["items"])
    assert out["deductible_total"] == Decimal("10000")
    assert out["capitalized_total"] == Decimal("0")
    assert sum(1 for w in out["warnings"]
               if w.startswith("ELECTION-OUT-ADS-REQUIRED")) == 1
    assert sum(1 for w in out["warnings"]
               if w.startswith("ELECTION-OUT-1245-RECHARACTERIZATION")) == 1


def test_election_out_barred_for_447_taxpayer():
    """required_447_accrual True: the §263A(d)(3) election is unavailable —
    ELECTION-OUT-UNAVAILABLE (flag + warning), the election is IGNORED,
    the 7,000 stays capitalized, and NO consequence warnings fire."""
    out = compute_farming_unicap(
        [_plant("P1", 7000, preproductive_period_over_2yr=True,
                in_election_out_year=True)],
        _p(), required_447_accrual=True, election_out_263Ad3=True)
    row = out["items"][0]
    assert row["treatment"] == "preproductive_capitalize"
    assert "ELECTION-OUT-UNAVAILABLE" in row["flags"]
    assert any("ELECTION-OUT-UNAVAILABLE" in w for w in out["warnings"])
    assert out["capitalized_total"] == Decimal("7000")
    assert not any("ELECTION-OUT-ADS-REQUIRED" in w for w in out["warnings"])
    assert not any("ELECTION-OUT-1245-RECHARACTERIZATION" in w
                   for w in out["warnings"])


def test_election_out_barred_when_447_unknown_carries_flag():
    """required_447_accrual None + election: barred under the CONSERVATIVE
    assumption, so the row carries BOTH ELECTION-OUT-UNAVAILABLE and
    447-STATUS-UNKNOWN (the bar itself rests on the unanswered fact)."""
    out = compute_farming_unicap(
        [_plant("P1", 7000, preproductive_period_over_2yr=True,
                in_election_out_year=True)],
        _p(), election_out_263Ad3=True)
    row = out["items"][0]
    assert "ELECTION-OUT-UNAVAILABLE" in row["flags"]
    assert "447-STATUS-UNKNOWN" in row["flags"]
    assert out["capitalized_total"] == Decimal("7000")


def test_election_out_requires_both_run_switch_and_group_year():
    """The election applies only when election_out_263Ad3 AND the group's
    in_election_out_year are BOTH set — either alone leaves the >2-year
    plant capitalized with no election warnings."""
    # run switch on, group not covered
    out = compute_farming_unicap(
        [_plant("P1", 5000, preproductive_period_over_2yr=True)],
        _p(), required_447_accrual=False, election_out_263Ad3=True)
    assert out["items"][0]["treatment"] == "preproductive_capitalize"
    assert out["warnings"] == []
    # group covered, run switch off
    out = compute_farming_unicap(
        [_plant("P1", 5000, preproductive_period_over_2yr=True,
                in_election_out_year=True)],
        _p(), required_447_accrual=False)
    assert out["items"][0]["treatment"] == "preproductive_capitalize"
    assert out["warnings"] == []


def test_election_out_does_not_touch_exempt_animal():
    """An exempt animal group deducts on its OWN authority
    (animal_exempt_deduct) — the election overlay only applies to groups
    that would otherwise capitalize, so no consequence warnings fire."""
    out = compute_farming_unicap(
        [_animal("A1", 3000, in_election_out_year=True)],
        _p(), required_447_accrual=False, election_out_263Ad3=True)
    assert out["items"][0]["treatment"] == "animal_exempt_deduct"
    assert out["warnings"] == []


def test_election_out_period_unknown_deducts_but_keeps_question():
    """Period-unknown plant under a valid election: deduct is the outcome
    under either answer, so it deducts as election_out_deduct — but the
    PREPRODUCTIVE-PERIOD-UNKNOWN flag and open question are KEPT (the
    answer still scopes the §263A(e) consequences), and the consequence
    warnings fire."""
    out = compute_farming_unicap(
        [_plant("P1", 4000, in_election_out_year=True)],
        _p(), required_447_accrual=False, election_out_263Ad3=True)
    row = out["items"][0]
    assert row["treatment"] == "election_out_deduct"
    assert "PREPRODUCTIVE-PERIOD-UNKNOWN" in row["flags"]
    assert any("preproductive_period_over_2yr" in q["question"]
               for q in out["open_questions"])
    assert out["deductible_total"] == Decimal("4000")
    assert any("ELECTION-OUT-ADS-REQUIRED" in w for w in out["warnings"])


# --- step 2a + totals ---------------------------------------------------------

def test_negative_amount_guard():
    """-500 -> sme_review with NEGATIVE-AMOUNT (flag + warning), excluded
    from BOTH totals; the sibling 1,000 animal group still deducts."""
    out = compute_farming_unicap(
        [_animal("N1", -500), _animal("A1", 1000)],
        _p(), required_447_accrual=False)
    row = out["items"][0]
    assert row["treatment"] == "sme_review"
    assert "NEGATIVE-AMOUNT" in row["flags"]
    assert row["capitalized"] == Decimal("0")
    assert row["deductible"] == Decimal("0")
    assert any("NEGATIVE-AMOUNT" in w for w in out["warnings"])
    assert out["capitalized_total"] == Decimal("0")
    assert out["deductible_total"] == Decimal("1000")


def test_totals_tie_mixed_schedule():
    """Golden, hand-computed. required_447_accrual False, election on:
      A1 animal 1,000            -> deduct  (animal_exempt_deduct)
      P1 plant >2yr 5,000        -> capitalize (preproductive_capitalize)
      P2 plant ≤2yr 2,000        -> deduct  (plant_exempt_deduct)
      P3 plant >2yr elected 4,000-> deduct  (election_out_deduct)
      P4 plant period-None 3,000 -> capitalize (conservative)
      N1 plant -100              -> sme_review (excluded)
    capitalized 5,000 + 3,000 = 8,000; deductible 1,000 + 2,000 + 4,000 =
    7,000; tie: 8,000 + 7,000 == 15,000 == sum of non-sme amounts."""
    groups = [_animal("A1", 1000),
              _plant("P1", 5000, preproductive_period_over_2yr=True),
              _plant("P2", 2000, preproductive_period_over_2yr=False),
              _plant("P3", 4000, preproductive_period_over_2yr=True,
                     in_election_out_year=True),
              _plant("P4", 3000),
              _plant("N1", -100)]
    out = compute_farming_unicap(groups, _p(), required_447_accrual=False,
                                 election_out_263Ad3=True)
    assert out["exempt"] is False
    assert out["capitalized_total"] == Decimal("8000")
    assert out["deductible_total"] == Decimal("7000")
    non_sme = sum((r["amount"] for r in out["items"]
                   if r["treatment"] != "sme_review"), Decimal("0"))
    assert out["capitalized_total"] + out["deductible_total"] == non_sme \
        == Decimal("15000")
    # every non-sme row carries its dollars in exactly one column
    for r in out["items"]:
        if r["treatment"] != "sme_review":
            assert r["deductible"] + r["capitalized"] == r["amount"]


def test_farmgroup_coerces_money_to_decimal():
    """FarmGroup routes preproductive_costs through model._dec: a str
    coerces to Decimal exactly (no float drift)."""
    g = FarmGroup(group_id="G1", preproductive_costs="1000.50")
    assert g.preproductive_costs == Decimal("1000.50")
    assert isinstance(g.preproductive_costs, Decimal)
