"""Phase B: MSPM (§1.263A-2(c)) and SRM (§1.263A-3(d)) inventory engines.

Golden fixtures are the regulation's own worked examples where they exist
(MSPM: §1.263A-2(c)(3)(vi) Example 1 / Taxpayer P; SSCM split: Examples 4-6);
the SRM golden is the BUILD_PLAN's independently re-verified hand-built
illustration (no regulation-sourced SRM example exists).

The `result` dicts are hand-constructed (no analyze() round-trip): the MSPM/
SRM formulas draw their pools from EntityProfile fields, and compute_sscm
only needs `rows` and `mixed_total`.
"""

from decimal import Decimal as D

from financial_tools.cap263a.analysis import EntityProfile
from financial_tools.cap263a.engines.inventory import compute_mspm, compute_srm


def _result(mixed_total=D("0"), deductible_total=D("0")):
    return {
        "rows": [],
        "bucket_totals": {"Inventory §471": D("0"), "§263A Additional": D("0")},
        "mixed_total": mixed_total,
        "deductible_total": deductible_total,
    }


def _mspm_profile(**kw):
    kw.setdefault("method", "MSPM")
    kw.setdefault("avg_gross_receipts", D("75000000"))
    return EntityProfile(**kw)


def _srm_profile(**kw):
    kw.setdefault("method", "SRM")
    kw.setdefault("avg_gross_receipts", D("75000000"))
    kw.setdefault("produces", False)
    kw.setdefault("acquires_for_resale", True)
    kw.setdefault("purchasing_costs", D("60000"))
    kw.setdefault("current_year_471_costs", D("2000000"))
    kw.setdefault("storage_handling_costs", D("105000"))
    kw.setdefault("beginning_inventory_471", D("400000"))
    kw.setdefault("ending_inventory_471", D("500000"))
    return EntityProfile(**kw)


# ---------------------------------------------------------------- MSPM golden

def test_mspm_regulation_example_1():
    """§1.263A-2(c)(3)(vi)(A) Example 1 (Taxpayer P) — every number IRS-sourced.

    pre_production_ratio        = 200,000 / 2,500,000               =  8.00%
    residual                    = 200,000 - 8.00% x 1,000,000       = 120,000
    direct_materials_adjustment = 400,000 + 1,900,000 - 800,000     = 1,500,000
    production_ratio            = (800,000 + 120,000) / (7,500,000 + 1,500,000)
                                = 920,000 / 9,000,000               = 10.22%
    add'l to inventory          = 8.00% x 1,000,000 + 10.22% x 2,000,000
                                = 80,000 + 204,400                  = 284,400
    total ending inventory      = 3,000,000 §471 on hand + 284,400  = 3,284,400
    """
    p = _mspm_profile(
        pre_production_471=D("2500000"),           # 1.9M DM + 0.6M resale
        production_471=D("7500000"),
        pre_production_additional_263A=D("200000"),
        production_additional_263A=D("800000"),
        pre_production_471_on_hand=D("1000000"),   # 0.8M DM + 0.2M resale
        production_471_on_hand=D("2000000"),
        beginning_DM_not_yet_in_production=D("400000"),
        ending_DM_not_yet_in_production=D("800000"),
        DM_purchased_during_year=D("1900000"),
    )
    u = compute_mspm(_result(), p)
    assert u["exempt"] is False
    assert u["pre_production_ratio"] == D("0.0800")
    assert u["residual_pre_production_263A"] == D("120000")
    assert u["direct_materials_adjustment"] == D("1500000")
    assert u["production_ratio"] == D("0.1022")
    # 0.1022 only falls out if the ratio is quantized to 0.0001 BEFORE the
    # multiply (raw is 0.10222...): assert the quantization actually happened.
    assert u["production_ratio"].as_tuple().exponent == -4
    assert u["additional_capitalized_to_inventory"] == D("284400.00")
    total_ending_inventory = (u["pre_production_471_on_hand"]
                              + u["production_471_on_hand"]
                              + u["additional_capitalized_to_inventory"])
    assert total_ending_inventory == D("3284400.00")
    assert u["warnings"] == []
    assert u["adjusted_deductible_post"] == D("0")


# --------------------------------------------- MSPM SSCM split (Examples 4-6)

def test_mspm_sscm_split_direct_material():
    """Example 4: $200,000 capitalizable MSC, direct-material method —
    $2,000,000 DM / $8,000,000 total §471 = 25% -> $50,000 pre / $150,000 prod."""
    p = _mspm_profile(
        mixed_alloc_ratio=D("1"),                  # 100% of the pool capitalizable
        mspm_mixed_split_method="direct_material",
        pre_production_471=D("2000000"),
        production_471=D("6000000"),               # total §471 = 8,000,000
        DM_purchased_during_year=D("2000000"),
    )
    u = compute_mspm(_result(mixed_total=D("200000")), p)
    assert u["mixed_capitalized"] == D("200000.00")
    assert u["mixed_split_method"] == "direct_material"
    assert u["mixed_split_proportion_pre"] == D("0.25")
    assert u["mixed_pre_production_share"] == D("50000.00")
    assert u["mixed_production_share"] == D("150000.00")
    # shares land in the pools BEFORE the ratios are computed
    assert u["pre_production_pool"] == D("50000.00")
    assert u["production_pool"] == D("150000.00")


def test_mspm_sscm_split_labor():
    """Example 5: labor method — $1,000,000 pre-production labor / $10,000,000
    total labor = 10% -> $20,000 pre / $180,000 production. The proportion is
    supplied via mspm_labor_split_proportion (both labor figures already
    exclude mixed-service labor per (c)(3)(iii)(B))."""
    p = _mspm_profile(
        mixed_alloc_ratio=D("1"),
        mspm_mixed_split_method="labor",
        pre_production_471=D("2000000"),
        production_471=D("6000000"),
    )
    p.mspm_labor_split_proportion = D("0.10")
    u = compute_mspm(_result(mixed_total=D("200000")), p)
    assert u["mixed_split_method"] == "labor"
    assert u["mixed_pre_production_share"] == D("20000.00")
    assert u["mixed_production_share"] == D("180000.00")
    assert not any("MSPM-SPLIT-INPUT-MISSING" in w for w in u["warnings"])


def test_mspm_sscm_split_90pct_election():
    """Example 6: 90%+ of MSC allocate to production (labor proportion 5% to
    pre-production -> 95% production) and the (c)(3)(iii)(C) election is made
    -> 100% to production."""
    p = _mspm_profile(
        mixed_alloc_ratio=D("1"),
        mspm_mixed_split_method="labor",
        mspm_90pct_split_election=True,
        pre_production_471=D("2000000"),
        production_471=D("6000000"),
    )
    p.mspm_labor_split_proportion = D("0.05")
    u = compute_mspm(_result(mixed_total=D("200000")), p)
    assert u["mspm_90pct_applied"] is True
    assert u["mixed_pre_production_share"] == D("0.00")
    assert u["mixed_production_share"] == D("200000.00")


def test_mspm_labor_split_missing_falls_back_to_direct_material():
    p = _mspm_profile(
        mixed_alloc_ratio=D("1"),
        mspm_mixed_split_method="labor",       # but no proportion supplied
        pre_production_471=D("2000000"),
        production_471=D("6000000"),
        DM_purchased_during_year=D("2000000"),
    )
    u = compute_mspm(_result(mixed_total=D("200000")), p)
    assert any("MSPM-SPLIT-INPUT-MISSING" in w for w in u["warnings"])
    assert u["mixed_split_method"] == "direct_material"
    assert u["mixed_pre_production_share"] == D("50000.00")


# ----------------------------------------------------------------- SRM golden

def test_srm_golden():
    """purchasing 60,000 / 2,000,000                      = 0.030000
    storage & handling 105,000 / (400,000 + 2,000,000)    = 0.043750
    combined                                              = 0.073750
    add'l to inventory 0.073750 x 500,000                 = 36,875.00"""
    u = compute_srm(_result(), _srm_profile())
    assert u["exempt"] is False
    assert u["method_conflict"] is False
    assert u["purchasing_ratio"] == D("0.030000")
    assert u["storage_handling_ratio"] == D("0.043750")
    assert u["storage_handling_ratio"].as_tuple().exponent == -6
    assert u["combined_ratio"] == D("0.073750")
    assert u["additional_capitalized_to_inventory"] == D("36875.00")
    assert u["warnings"] == []


def test_srm_variation_a_excludes_beginning_inventory():
    """Permissible variation §1.263A-3(d)(3)(iii)(A): beginning inventory out
    of the S&H denominator.

    storage & handling 105,000 / 2,000,000  = 0.052500
    combined 0.030000 + 0.052500            = 0.082500
    add'l to inventory 0.082500 x 500,000   = 41,250.00"""
    u = compute_srm(_result(), _srm_profile(srm_variation_a=True))
    assert u["purchasing_ratio"] == D("0.030000")
    assert u["storage_handling_ratio"] == D("0.052500")
    assert u["storage_handling_denominator"] == D("2000000")
    assert u["combined_ratio"] == D("0.082500")
    assert u["additional_capitalized_to_inventory"] == D("41250.00")


# --------------------------------------------------- SRM method-availability

def test_srm_method_conflict_more_than_de_minimis_producer():
    """§1.263A-3(a)(4)(i): a more-than-de-minimis producer may not elect SRM.
    Hard conflict — warning leads the list, but the numbers still compute."""
    u = compute_srm(_result(), _srm_profile(
        produces=True,
        production_activity_level="more_than_de_minimis",
        private_label_goods=False))
    assert u["method_conflict"] is True
    assert u["warnings"][0].startswith("SRM-METHOD-CONFLICT")
    assert "NOT a permissible filing position" in u["warnings"][0]
    # visibility beats a crash: figures still returned
    assert u["additional_capitalized_to_inventory"] == D("36875.00")


def test_srm_no_conflict_for_private_label_producer():
    """(a)(4)(iii) private-label carve-out re-opens SRM for the producer."""
    u = compute_srm(_result(), _srm_profile(
        produces=True,
        production_activity_level="more_than_de_minimis",
        private_label_goods=True))
    assert u["method_conflict"] is False
    assert not any("SRM-METHOD-CONFLICT" in w for w in u["warnings"])


def test_srm_reseller_production_cost_sscm_ratio_warns():
    """(Updated round 5: the warning moved into compute_sscm itself — the
    production-cost ratio is now IMPLEMENTED for producers, and a reseller
    electing it falls back to labor with SSCM-PRODUCTION-COST-RESELLER.)"""
    u = compute_srm(_result(), _srm_profile(sscm_ratio_method="production_cost"))
    assert any("SSCM-PRODUCTION-COST-RESELLER" in w for w in u["warnings"])


# ------------------------------------------------ guardrails / degenerate data

def test_mspm_negative_residual_floored_with_warning():
    """pre_production_471_on_hand > pre_production_471 is definitionally an
    input-contract breach ((c)(3)(ii)(C)/(E): on-hand = current-year-incurred
    costs on hand): ratio 10.00% x 2,000 on-hand > 100 pool -> raw residual
    -100, floored at 0 with the input-contract warning."""
    p = _mspm_profile(
        pre_production_471=D("1000"),
        pre_production_additional_263A=D("100"),
        pre_production_471_on_hand=D("2000"),
    )
    u = compute_mspm(_result(), p)
    assert u["residual_pre_production_263A"] == D("0.00")
    flagged = [w for w in u["warnings"] if "MSPM-NEGATIVE-RESIDUAL-FLOORED" in w]
    assert flagged and "current-year-incurred" in flagged[0]


def test_mspm_negative_on_hand_floored_with_warning():
    p = _mspm_profile(
        pre_production_471=D("1000"),
        pre_production_additional_263A=D("100"),
        production_471_on_hand=D("-500"),
    )
    u = compute_mspm(_result(), p)
    assert u["production_471_on_hand"] == D("0")
    assert any("MSPM-NEGATIVE-ON-HAND-BALANCE" in w for w in u["warnings"])


def test_mspm_zero_denominators_safe():
    """All-zero inputs: no division fault, ratios 0, warnings surfaced."""
    u = compute_mspm(_result(), _mspm_profile())
    assert u["pre_production_ratio"] == D("0")
    assert u["production_ratio"] == D("0")
    assert u["additional_capitalized_to_inventory"] == D("0.00")
    assert any("MSPM-ZERO-DENOMINATOR" in w for w in u["warnings"])


def test_srm_zero_denominators_safe():
    u = compute_srm(_result(), _srm_profile(
        purchasing_costs=D("0"), current_year_471_costs=D("0"),
        storage_handling_costs=D("0"), beginning_inventory_471=D("0"),
        ending_inventory_471=D("0")))
    assert u["purchasing_ratio"] == D("0")
    assert u["storage_handling_ratio"] == D("0")
    assert u["additional_capitalized_to_inventory"] == D("0.00")
    assert any("SRM-ZERO-DENOMINATOR" in w for w in u["warnings"])


def test_mspm_negative_pool_permitted_no_50m_bar():
    """§1.263A-1(d)(3)(ii)(B)(2): MSPM permits negative additional §263A
    amounts with NO gross-receipts cap — warning for visibility only, and no
    SPM-style $50M message even for a large producer."""
    p = _mspm_profile(
        avg_gross_receipts=D("75000000"),          # over the SPM-only cap
        pre_production_471=D("1000000"),
        pre_production_additional_263A=D("-50000"),
        pre_production_471_on_hand=D("400000"),
        production_471=D("2000000"),
        production_additional_263A=D("100000"),
        production_471_on_hand=D("500000"),
        DM_purchased_during_year=D("1000000"),
    )
    u = compute_mspm(_result(), p)
    assert u["pre_production_ratio"] == D("-0.0500")
    assert any("MSPM-NEGATIVE-POOL" in w for w in u["warnings"])
    joined = " ".join(u["warnings"])
    assert "50M" not in joined and "50,000,000" not in joined


def test_srm_negative_pool_permitted_no_50m_bar():
    """§1.263A-1(d)(3)(ii)(B)(3): same for SRM — negative purchasing pool
    flows through (combined = -0.030000 + 0.043750 = 0.013750)."""
    u = compute_srm(_result(), _srm_profile(
        purchasing_costs=D("-60000")))
    assert u["purchasing_ratio"] == D("-0.030000")
    assert u["combined_ratio"] == D("0.013750")
    assert u["additional_capitalized_to_inventory"] == D("6875.00")
    assert any("SRM-NEGATIVE-POOL" in w for w in u["warnings"])
    joined = " ".join(u["warnings"])
    assert "50M" not in joined and "50,000,000" not in joined


# ------------------------------------------------------------- dispatcher wire

def test_dispatcher_routes_mspm_and_srm():
    """compute_unicap dispatches on profile.method and the engines return the
    SPM-superset shape (contract keys present)."""
    from financial_tools.cap263a.analysis import compute_unicap
    res = _result(deductible_total=D("10"))
    for method, key in (("MSPM", "production_ratio"), ("SRM", "combined_ratio")):
        p = _mspm_profile(method=method) if method == "MSPM" else _srm_profile()
        u = compute_unicap(res, p)
        for k in ("exempt", "warnings", "mixed_alloc_ratio", "mixed_capitalized",
                  "mixed_deductible", "additional_capitalized_to_inventory",
                  "adjusted_deductible_post", key):
            assert k in u, (method, k)
        assert u["adjusted_deductible_post"] == D("10")
