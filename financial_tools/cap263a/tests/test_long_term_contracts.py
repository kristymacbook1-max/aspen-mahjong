"""§460 long-term contract PCM engine — every treatment branch, the exact
election/exemption boundaries, the exact-factor arithmetic convention, and
the once-per-run warnings. Golden figures hand-computed in each docstring."""

from decimal import Decimal

from financial_tools.cap263a.analysis import EntityProfile
from financial_tools.cap263a.engines.long_term_contracts import (
    LongTermContract, compute_460)


def _p(**overrides):
    kw = dict(avg_gross_receipts=Decimal("5000000"))
    kw.update(overrides)
    return EntityProfile(**kw)


def _ltc(contract_id, **overrides):
    """A plain construction contract with a duration estimate long enough
    (3 years) to stay OUT of the §460(e)(1)(B) small-contract exemption."""
    kw = dict(contract_id=contract_id, description=contract_id,
              total_contract_price=Decimal("1000000"),
              estimated_total_allocable_costs=Decimal("800000"),
              cumulative_allocable_costs=Decimal("200000"),
              estimated_duration_years=Decimal("3"))
    kw.update(overrides)
    return LongTermContract(**kw)


# --- step 5: plain PCM ---------------------------------------------------------

def test_pcm_year1_plain():
    """Price 1,000,000, estimated total 800,000, cumulative 200,000:
    factor 200,000/800,000 = 0.25; cumulative income 0.25 x 1,000,000 =
    250,000.00; year 1 so current income 250,000.00 and costs deducted
    200,000.00."""
    out = compute_460([_ltc("C1")], _p())
    row = out["contracts"][0]
    assert row["treatment"] == "pcm"
    assert row["completion_factor"] == Decimal("0.2500")
    assert row["cumulative_income"] == Decimal("250000.00")
    assert row["current_year_income"] == Decimal("250000.00")
    assert row["current_year_costs_deducted"] == Decimal("200000.00")
    assert row["deferred_costs"] == Decimal("0.00")
    assert row["flags"] == []
    assert out["total_current_year_income"] == Decimal("250000.00")
    assert out["total_current_year_costs"] == Decimal("200000.00")


def test_pcm_year2_with_prior():
    """Year 2 of the same contract: cumulative 600,000 (prior 200,000),
    prior income 250,000. Factor 600,000/800,000 = 0.75; cumulative income
    750,000.00; current income 750,000 - 250,000 = 500,000.00; costs
    deducted 600,000 - 200,000 = 400,000.00."""
    out = compute_460(
        [_ltc("C1", cumulative_allocable_costs=Decimal("600000"),
              prior_cumulative_allocable_costs=Decimal("200000"),
              prior_income_recognized=Decimal("250000"))], _p())
    row = out["contracts"][0]
    assert row["completion_factor"] == Decimal("0.7500")
    assert row["cumulative_income"] == Decimal("750000.00")
    assert row["current_year_income"] == Decimal("500000.00")
    assert row["current_year_costs_deducted"] == Decimal("400000.00")
    assert not any("LOOKBACK-NOT-IMPLEMENTED" in w for w in out["warnings"])


def test_exact_factor_multiplies_not_the_reported_4dp():
    """Cumulative 200,000 / estimated 700,000 = 2/7 = 0.285714...; the
    REPORTED factor is 0.2857 (4dp HALF_EVEN) but income multiplies the
    EXACT factor: 2/7 x 1,000,000 = 285,714.2857... -> 285,714.29 (cents,
    HALF_EVEN). Multiplying the pre-rounded factor would give 285,700.00 —
    wrong."""
    out = compute_460(
        [_ltc("C1", estimated_total_allocable_costs=Decimal("700000"))], _p())
    row = out["contracts"][0]
    assert row["completion_factor"] == Decimal("0.2857")
    assert row["cumulative_income"] == Decimal("285714.29")


# --- step 5: estimate shift / negative current income ---------------------------

def test_estimate_shift_negative_current_income_not_floored():
    """Prior year recognized 500,000 (factor 0.5 on an 800,000 estimate at
    cumulative 400,000). This year the estimate is revised UP to 1,600,000
    with cumulative 600,000: factor 0.375, cumulative income 375,000.00,
    current income 375,000 - 500,000 = -125,000.00 — permitted, NOT
    floored. Draws NEGATIVE-CURRENT-INCOME and LOOKBACK-NOT-IMPLEMENTED."""
    out = compute_460(
        [_ltc("C1", estimated_total_allocable_costs=Decimal("1600000"),
              cumulative_allocable_costs=Decimal("600000"),
              prior_cumulative_allocable_costs=Decimal("400000"),
              prior_income_recognized=Decimal("500000"))], _p())
    row = out["contracts"][0]
    assert row["completion_factor"] == Decimal("0.3750")
    assert row["current_year_income"] == Decimal("-125000.00")
    assert "NEGATIVE-CURRENT-INCOME" in row["flags"]
    assert any("NEGATIVE-CURRENT-INCOME" in w for w in out["warnings"])
    assert any("LOOKBACK-NOT-IMPLEMENTED" in w for w in out["warnings"])
    assert out["total_current_year_income"] == Decimal("-125000.00")


def test_negative_current_income_warned_once_per_run():
    """Two contracts both go negative: each row is flagged, but the
    NEGATIVE-CURRENT-INCOME warning fires ONCE for the run."""
    def neg(cid):
        return _ltc(cid, estimated_total_allocable_costs=Decimal("1600000"),
                    cumulative_allocable_costs=Decimal("600000"),
                    prior_cumulative_allocable_costs=Decimal("400000"),
                    prior_income_recognized=Decimal("500000"))
    out = compute_460([neg("C1"), neg("C2")], _p())
    assert all("NEGATIVE-CURRENT-INCOME" in r["flags"]
               for r in out["contracts"])
    assert sum(1 for w in out["warnings"]
               if w.startswith("NEGATIVE-CURRENT-INCOME")) == 1


# --- step 5: over-100% clamp / zero estimate -------------------------------------

def test_completion_over_100pct_clamps_to_1():
    """Cumulative 550,000 on an estimated total 500,000: raw factor 1.1
    clamps to 1.0000; cumulative income = the full price 1,000,000.00.
    COMPLETION-OVER-100PCT warns (stale estimate) and triggers
    LOOKBACK-NOT-IMPLEMENTED."""
    out = compute_460(
        [_ltc("C1", estimated_total_allocable_costs=Decimal("500000"),
              cumulative_allocable_costs=Decimal("550000"))], _p())
    row = out["contracts"][0]
    assert row["completion_factor"] == Decimal("1.0000")
    assert row["cumulative_income"] == Decimal("1000000.00")
    assert "COMPLETION-OVER-100PCT" in row["flags"]
    assert any("COMPLETION-OVER-100PCT" in w for w in out["warnings"])
    assert any("LOOKBACK-NOT-IMPLEMENTED" in w for w in out["warnings"])


def test_zero_estimate_factor_zero_costs_still_deducted():
    """Estimated total 0 with cumulative 50,000: ZERO-ESTIMATE warning,
    factor 0.0000, no income — but PCM still deducts the 50,000.00 of
    costs incurred."""
    out = compute_460(
        [_ltc("C1", estimated_total_allocable_costs=Decimal("0"),
              cumulative_allocable_costs=Decimal("50000"))], _p())
    row = out["contracts"][0]
    assert any("ZERO-ESTIMATE" in w for w in out["warnings"])
    assert row["completion_factor"] == Decimal("0.0000")
    assert row["cumulative_income"] == Decimal("0.00")
    assert row["current_year_income"] == Decimal("0.00")
    assert row["current_year_costs_deducted"] == Decimal("50000.00")


# --- step 7: completion true-up ---------------------------------------------------

def test_completion_true_up_recognizes_full_price():
    """completed_this_year with cumulative 750,000 on an estimated total
    800,000 (raw factor 0.9375 < 1): the factor is forced to 1.0000 with
    COMPLETION-TRUE-UP, cumulative income = the full price 1,000,000.00;
    prior income 600,000 -> current income 400,000.00.
    LOOKBACK-NOT-IMPLEMENTED fires once."""
    out = compute_460(
        [_ltc("C1", cumulative_allocable_costs=Decimal("750000"),
              prior_cumulative_allocable_costs=Decimal("480000"),
              prior_income_recognized=Decimal("600000"),
              completed_this_year=True)], _p())
    row = out["contracts"][0]
    assert row["completion_factor"] == Decimal("1.0000")
    assert "COMPLETION-TRUE-UP" in row["flags"]
    assert row["cumulative_income"] == Decimal("1000000.00")
    assert row["current_year_income"] == Decimal("400000.00")
    assert sum(1 for w in out["warnings"]
               if "LOOKBACK-NOT-IMPLEMENTED" in w) == 1


def test_completed_at_exact_estimate_no_true_up_but_lookback_warns():
    """completed_this_year with cumulative == estimated total: factor is
    already 1, no COMPLETION-TRUE-UP — but completion alone still draws
    LOOKBACK-NOT-IMPLEMENTED."""
    out = compute_460(
        [_ltc("C1", cumulative_allocable_costs=Decimal("800000"),
              completed_this_year=True)], _p())
    row = out["contracts"][0]
    assert row["completion_factor"] == Decimal("1.0000")
    assert "COMPLETION-TRUE-UP" not in row["flags"]
    assert row["cumulative_income"] == Decimal("1000000.00")
    assert any("LOOKBACK-NOT-IMPLEMENTED" in w for w in out["warnings"])


# --- step 6: 10% election (§460(b)(5)) --------------------------------------------

def test_ten_percent_election_defers_below_the_line():
    """Election on, cumulative 99,900 on estimated total 1,000,000: factor
    0.0999 < 10% -> contract disregarded for the year: current income 0.00,
    costs NOT deducted — 99,900.00 reported as deferred_costs, flag
    TEN-PCT-DEFERRED. cumulative_income keeps the PCM formula figure
    0.0999 x 1,000,000 = 99,900.00 (informational)."""
    out = compute_460(
        [_ltc("C1", estimated_total_allocable_costs=Decimal("1000000"),
              cumulative_allocable_costs=Decimal("99900"),
              ten_percent_election=True)], _p())
    row = out["contracts"][0]
    assert row["completion_factor"] == Decimal("0.0999")
    assert "TEN-PCT-DEFERRED" in row["flags"]
    assert row["current_year_income"] == Decimal("0.00")
    assert row["current_year_costs_deducted"] == Decimal("0.00")
    assert row["deferred_costs"] == Decimal("99900.00")
    assert row["cumulative_income"] == Decimal("99900.00")
    assert out["total_current_year_income"] == Decimal("0.00")
    assert out["total_current_year_costs"] == Decimal("0.00")


def test_ten_percent_election_at_exactly_ten_percent_recognizes():
    """Election on, cumulative 100,000 on estimated total 1,000,000: factor
    exactly 0.10 is NOT < 10% -> normal PCM: income 100,000.00, costs
    100,000.00, no deferral flag."""
    out = compute_460(
        [_ltc("C1", estimated_total_allocable_costs=Decimal("1000000"),
              cumulative_allocable_costs=Decimal("100000"),
              ten_percent_election=True)], _p())
    row = out["contracts"][0]
    assert row["completion_factor"] == Decimal("0.1000")
    assert "TEN-PCT-DEFERRED" not in row["flags"]
    assert row["current_year_income"] == Decimal("100000.00")
    assert row["current_year_costs_deducted"] == Decimal("100000.00")
    assert row["deferred_costs"] == Decimal("0.00")


def test_no_ten_percent_election_below_ten_percent_recognizes():
    """Same 9.99% facts WITHOUT the election: ordinary PCM recognition —
    income 99,900.00, costs 99,900.00."""
    out = compute_460(
        [_ltc("C1", estimated_total_allocable_costs=Decimal("1000000"),
              cumulative_allocable_costs=Decimal("99900"))], _p())
    row = out["contracts"][0]
    assert "TEN-PCT-DEFERRED" not in row["flags"]
    assert row["current_year_income"] == Decimal("99900.00")
    assert row["current_year_costs_deducted"] == Decimal("99900.00")


# --- step 3: home construction exemption (§460(e)(1)(A)) --------------------------

def test_home_construction_exempt_no_pcm_routes_to_unicap():
    out = compute_460([_ltc("H1", is_home_construction=True)], _p())
    row = out["contracts"][0]
    assert row["treatment"] == "home_construction_exempt"
    assert row["completion_factor"] is None
    assert row["cumulative_income"] == Decimal("0")
    assert row["current_year_income"] == Decimal("0")
    assert row["current_year_costs_deducted"] == Decimal("0")
    w = next(w for w in out["warnings"] if "HOME-CONSTRUCTION-EXEMPT" in w)
    assert "263A" in w and "UNICAP" in w
    assert out["total_current_year_income"] == Decimal("0")


# --- step 4: small construction exemption (§460(e)(1)(B)) --------------------------

def test_small_construction_exempt_at_exact_receipts_threshold():
    """Receipts EXACTLY at profile.sec448_threshold with a 2-year duration:
    exempt (the §448(c) test is <=). One cent over the threshold: PCM."""
    profile = _p()
    at = _p(avg_gross_receipts=profile.sec448_threshold)
    out = compute_460(
        [_ltc("S1", estimated_duration_years=Decimal("2"))], at)
    assert out["contracts"][0]["treatment"] == "small_construction_exempt"
    w = next(w for w in out["warnings"] if "SMALL-CONSTRUCTION-EXEMPT" in w)
    assert "448(c)" in w

    over = _p(avg_gross_receipts=profile.sec448_threshold + Decimal("0.01"))
    out2 = compute_460(
        [_ltc("S1", estimated_duration_years=Decimal("2"))], over)
    assert out2["contracts"][0]["treatment"] == "pcm"
    assert out2["contracts"][0]["current_year_income"] == Decimal("250000.00")


def test_small_construction_duration_boundary():
    """Duration exactly 2 years is exempt (§460(e)(1)(B)(i) 'within
    2 years'); 2.5 years is not — PCM computes."""
    out = compute_460([_ltc("S2", estimated_duration_years=Decimal("2"))],
                      _p())
    assert out["contracts"][0]["treatment"] == "small_construction_exempt"

    out2 = compute_460([_ltc("S2", estimated_duration_years=Decimal("2.5"))],
                       _p())
    assert out2["contracts"][0]["treatment"] == "pcm"
    assert out2["contracts"][0]["completion_factor"] == Decimal("0.2500")


def test_construction_duration_unknown_asks_and_computes_pcm():
    """estimated_duration_years None on a construction contract: an open
    question about the at-commencement 2-year estimate, flag
    460E-DURATION-UNKNOWN, and PCM computed conservatively."""
    out = compute_460([_ltc("S3", estimated_duration_years=None)], _p())
    row = out["contracts"][0]
    assert row["treatment"] == "pcm"
    assert "460E-DURATION-UNKNOWN" in row["flags"]
    assert row["current_year_income"] == Decimal("250000.00")
    q = next(q for q in out["open_questions"] if q["contract_id"] == "S3")
    assert "460(e)(1)(B)" in q["question"]
    assert "estimated_duration_years" in q["question"]


# --- step 2: manufacturing PCM applicability (§460(f)(2)) ---------------------------

def test_manufacturing_both_prongs_false_not_long_term():
    """Both §460(f)(2) prongs explicitly False: not a long-term contract —
    treatment not_long_term_exempt, nothing computed, no open question."""
    out = compute_460(
        [_ltc("M1", contract_type="manufacturing", unique_item=False,
              normal_production_period_over_12mo=False)], _p())
    row = out["contracts"][0]
    assert row["treatment"] == "not_long_term_exempt"
    assert row["completion_factor"] is None
    assert row["current_year_income"] == Decimal("0")
    assert any("NOT-LONG-TERM" in w for w in out["warnings"])
    assert out["open_questions"] == []
    assert out["total_current_year_income"] == Decimal("0")


def test_manufacturing_prong_none_asks_and_computes_conservative_pcm():
    """unique_item None with the other prong False: OPEN QUESTION naming
    ONLY the missing fact, flag 460F2-FACTS-INCOMPLETE, and PCM computed
    conservatively (0.25 -> 250,000.00)."""
    out = compute_460(
        [_ltc("M2", contract_type="manufacturing", unique_item=None,
              normal_production_period_over_12mo=False)], _p())
    row = out["contracts"][0]
    assert row["treatment"] == "pcm"
    assert "460F2-FACTS-INCOMPLETE" in row["flags"]
    assert row["current_year_income"] == Decimal("250000.00")
    q = next(q for q in out["open_questions"] if q["contract_id"] == "M2")
    assert "unique_item" in q["question"]
    assert "460(f)(2)(A)" in q["question"]
    assert "normal_production_period_over_12mo" not in q["question"]


def test_manufacturing_prong_true_plain_pcm_no_small_construction_exemption():
    """Either prong True -> PCM with no flag and no question; a
    manufacturing contract never gets the §460(e)(1)(B) CONSTRUCTION
    exemption even with a short duration and small receipts."""
    out = compute_460(
        [_ltc("M3", contract_type="manufacturing", unique_item=True,
              estimated_duration_years=Decimal("1"))], _p())
    row = out["contracts"][0]
    assert row["treatment"] == "pcm"
    assert row["flags"] == []
    assert row["current_year_income"] == Decimal("250000.00")
    assert out["open_questions"] == []


# --- step 1: guards -----------------------------------------------------------------

def test_negative_price_sme_review_excluded_from_totals():
    out = compute_460(
        [_ltc("N1", total_contract_price=Decimal("-1000000")),
         _ltc("C1")], _p())
    row = out["contracts"][0]
    assert row["treatment"] == "sme_review"
    assert "NEGATIVE-AMOUNT" in row["flags"]
    assert any("NEGATIVE-AMOUNT" in w for w in out["warnings"])
    # only the good contract reaches the totals
    assert out["total_current_year_income"] == Decimal("250000.00")
    assert out["total_current_year_costs"] == Decimal("200000.00")


def test_costs_decreased_warns_but_still_computes_on_cumulative():
    """Cumulative 100,000 below the prior cumulative 150,000: a data error
    — COSTS-DECREASED warns, but PCM still computes on the cumulative as
    given: factor 0.125, income 125,000.00, costs deducted 100,000 -
    150,000 = -50,000.00."""
    out = compute_460(
        [_ltc("D1", cumulative_allocable_costs=Decimal("100000"),
              prior_cumulative_allocable_costs=Decimal("150000"),
              prior_income_recognized=Decimal("0"))], _p())
    row = out["contracts"][0]
    assert "COSTS-DECREASED" in row["flags"]
    assert any("COSTS-DECREASED" in w for w in out["warnings"])
    assert row["treatment"] == "pcm"
    assert row["completion_factor"] == Decimal("0.1250")
    assert row["current_year_income"] == Decimal("125000.00")
    assert row["current_year_costs_deducted"] == Decimal("-50000.00")


# --- step 8: cost-allocation input contract ------------------------------------------

def test_cost_allocation_input_warning_once_per_run_by_regime():
    """Default regime: one COST-ALLOCATION-INPUT-CONTRACT warning citing
    §1.460-5(b); simplified_cost_to_cost=True cites §1.460-5(c) instead —
    always once per run, never per contract."""
    out = compute_460([_ltc("C1"), _ltc("C2")], _p())
    ws = [w for w in out["warnings"]
          if "COST-ALLOCATION-INPUT-CONTRACT" in w]
    assert len(ws) == 1
    assert "1.460-5(b)" in ws[0]

    out2 = compute_460([_ltc("C1"), _ltc("C2")], _p(),
                       simplified_cost_to_cost=True)
    ws2 = [w for w in out2["warnings"]
           if "COST-ALLOCATION-INPUT-CONTRACT" in w]
    assert len(ws2) == 1
    assert "1.460-5(c)" in ws2[0]


def test_no_contracts_no_warnings():
    out = compute_460([], _p())
    assert out["contracts"] == []
    assert out["warnings"] == []
    assert out["total_current_year_income"] == Decimal("0")
    assert out["total_current_year_costs"] == Decimal("0")


# --- totals tie -----------------------------------------------------------------------

def test_totals_tie_across_every_branch():
    """One contract per branch. Hand arithmetic (quantized per-row figures):
      C1 plain PCM year 1:    income  250,000.00  costs  200,000.00
      C2 negative shift:      income -125,000.00  costs  200,000.00
      T1 10%-deferred:        income        0.00  costs        0.00
                              (deferred_costs 99,900.00 — not in totals)
      X1 completed true-up:   income  400,000.00  costs  270,000.00
      H1 home construction, S1 small construction, M1 not-long-term,
      N1 negative guard:      all excluded (0.00 / 0.00)
      totals: income 250,000 - 125,000 + 0 + 400,000 = 525,000.00
              costs  200,000 + 200,000 + 0 + 270,000 = 670,000.00
      and each total equals the exact sum of its per-row quantized figures."""
    contracts = [
        _ltc("C1"),
        _ltc("C2", estimated_total_allocable_costs=Decimal("1600000"),
             cumulative_allocable_costs=Decimal("600000"),
             prior_cumulative_allocable_costs=Decimal("400000"),
             prior_income_recognized=Decimal("500000")),
        _ltc("T1", estimated_total_allocable_costs=Decimal("1000000"),
             cumulative_allocable_costs=Decimal("99900"),
             ten_percent_election=True),
        _ltc("X1", cumulative_allocable_costs=Decimal("750000"),
             prior_cumulative_allocable_costs=Decimal("480000"),
             prior_income_recognized=Decimal("600000"),
             completed_this_year=True),
        _ltc("H1", is_home_construction=True),
        _ltc("S1", estimated_duration_years=Decimal("2")),
        _ltc("M1", contract_type="manufacturing", unique_item=False,
             normal_production_period_over_12mo=False),
        _ltc("N1", total_contract_price=Decimal("-5")),
    ]
    out = compute_460(contracts, _p())
    assert out["total_current_year_income"] == Decimal("525000.00")
    assert out["total_current_year_costs"] == Decimal("670000.00")
    assert out["total_current_year_income"] == sum(
        (r["current_year_income"] for r in out["contracts"]), Decimal("0"))
    assert out["total_current_year_costs"] == sum(
        (r["current_year_costs_deducted"] for r in out["contracts"]),
        Decimal("0"))
    # the deferral kept T1's costs out of the totals but reported them
    t1 = next(r for r in out["contracts"] if r["contract_id"] == "T1")
    assert t1["deferred_costs"] == Decimal("99900.00")
    # look-back warned once (X1 completed + C2 negative shift)
    assert sum(1 for w in out["warnings"]
               if "LOOKBACK-NOT-IMPLEMENTED" in w) == 1
