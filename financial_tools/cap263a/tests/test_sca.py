"""Phase C SCA engine — golden worked test (BUILD_PLAN.md Phase C, RESTATED
2026-07-09 in the ADOPTED Option-(B) ordering), the mixed-eligibility gate,
driver guardrails, degenerate denominator, penny-plug conservation, and the
CIP double-count review-queue route."""

from decimal import Decimal

import pytest

from financial_tools.cap263a.engines.sca import (
    compute_sca, load_drivers, DriverTaxonomyError)
from financial_tools.cap263a.model import CostPool, SelfConstructedAsset


D = Decimal


def _assets(a2_eligible=True):
    return [
        SelfConstructedAsset(asset_id="A1", description="Warehouse expansion",
                             book_cost=D("200000"), sscm_eligible=True),
        SelfConstructedAsset(asset_id="A2", description="Packaging line",
                             book_cost=D("300000"), sscm_eligible=a2_eligible),
    ]


def _hr_pool(driver="headcount"):
    return CostPool(pool_id="HR", description="HR shared services",
                    amount=D("100000"), driver=driver, is_mixed_service=True,
                    targets={"A1": D("75"), "A2": D("25"),
                             "NON_PRODUCTION": D("0")})


def _building_pool():
    return CostPool(pool_id="BLDG-DEP", description="Depreciation - Building",
                    amount=D("50000"), driver="square_footage",
                    is_mixed_service=False,
                    targets={"A1": D("2000"), "A2": D("8000")})


def test_golden_worked_option_b():
    """BUILD_PLAN.md Phase C worked test, Option-(B) ordering.

    HR mixed pool $100,000 by headcount across the FULL target set
    {A1: 75, A2: 25, NON_PRODUCTION: 0}:
      driver split FIRST: A1 100,000×75/100 = 75,000; A2 25,000; NP 0
      THEN gate (both eligible) and apply SSCM 0.60 per share:
        A1 mixed = 75,000×0.60 = 45,000 (30,000 deductible)
        A2 mixed = 25,000×0.60 = 15,000 (10,000 deductible)
      conservation on capitalizable: 45,000+15,000 = 60,000 = 100,000×0.60
    Building-dep pool $50,000 by sq ft {A1: 2,000, A2: 8,000} — plain
    indirect, NOT mixed-service, so no SSCM step:
      A1 = 50,000×20% = 10,000; A2 = 50,000×80% = 40,000
    Per asset: additional §263A = 45,000+10,000 = 55,000 (A1) and
    15,000+40,000 = 55,000 (A2); adjusted basis pre-interest =
    200,000+55,000 = 255,000 (A1), 300,000+55,000 = 355,000 (A2).
    Deductible = 30,000+10,000+0 (NP) = 40,000."""
    out = compute_sca([_hr_pool(), _building_pool()], _assets(),
                      sscm_ratio=D("0.60"))
    a1, a2 = out["per_asset"]["A1"], out["per_asset"]["A2"]
    assert a1["mixed_263a"] == D("45000.00")
    assert a2["mixed_263a"] == D("15000.00")
    assert a1["indirect_263a"] == D("10000.00")
    assert a2["indirect_263a"] == D("40000.00")
    assert a1["additional_263a"] == D("55000.00")
    assert a2["additional_263a"] == D("55000.00")
    assert a1["adjusted_basis_pre_interest"] == D("255000.00")
    assert a2["adjusted_basis_pre_interest"] == D("355000.00")
    # bucket C is Phase D's — APE emitted, no interest computed
    assert a1["ape_for_interest"] == a1["adjusted_basis_pre_interest"]
    assert out["ape_by_asset"]["A2"] == D("355000.00")
    assert a1["mixed_263a"] + a2["mixed_263a"] == D("100000") * D("0.60")
    assert out["deductible_total"] == D("40000.00")
    assert out["not_booked_total"] == D("0")
    assert out["warnings"] == []
    assert all(c["ok"] for c in out["conservation_checks"])
    assert len(out["conservation_checks"]) == 2


def test_mixed_eligibility_gate_full_share_not_booked():
    """Option-(B) DECISION 2026-07-08 (TAX_DECISIONS.md §8c): A2 is
    SSCM-ineligible, sharing the same HR pool.

    Driver split is unchanged: A1 75,000 / A2 25,000 / NP 0. A2's share is
    computed and stays in the audit trail, but the FULL 25,000 is tracked as
    not booked — NOT 25,000×0.60 = 15,000. Reading adopted here: the plan
    says the ineligible share is "NOT booked to bucket B" pending the
    general §1.263A-1(g)(4) method; applying the SSCM ratio to it would
    presume the very SSCM applicability that the (h)(2) eligibility test
    failed, so the entire unresolved share (25,000) is carried in
    not_booked_total, with no capitalizable/deductible split. A1 is
    unaffected: mixed = 75,000×0.60 = 45,000."""
    out = compute_sca([_hr_pool()], _assets(a2_eligible=False),
                      sscm_ratio=D("0.60"))
    assert out["per_asset"]["A1"]["mixed_263a"] == D("45000.00")
    assert out["per_asset"]["A2"]["mixed_263a"] == D("0")
    assert out["per_asset"]["A2"]["additional_263a"] == D("0")
    assert out["not_booked_total"] == D("25000.00")
    assert any("SSCM-INELIGIBLE-NO-FALLBACK" in w for w in out["warnings"])
    a2_row = [r for r in out["audit_trail"]
              if r["pool_id"] == "HR" and r["target"] == "A2"][0]
    assert a2_row["allocated"] == D("25000.00")     # visible in the trail
    assert a2_row["not_booked"] == D("25000.00")
    assert a2_row["capitalized"] == D("0")
    assert "SSCM-INELIGIBLE-NO-FALLBACK" in a2_row["flags"]
    # the eligible asset's share is NOT inflated by the gated share
    assert all(c["ok"] for c in out["conservation_checks"])


def test_hard_blocked_driver_hr_by_machine_hours():
    """Guardrail: an HR pool driven by machine_hours is a nonsensical
    pairing (sca_drivers.yaml category 1 blocks it) → HARD-BLOCKED-DRIVER,
    pool NOT allocated: every target allocated 0, per-asset totals 0,
    but the pool stays visible in the audit trail."""
    out = compute_sca([_hr_pool(driver="machine_hours")], _assets(),
                      sscm_ratio=D("0.60"))
    assert any("HARD-BLOCKED-DRIVER" in w for w in out["warnings"])
    assert out["per_asset"]["A1"]["additional_263a"] == D("0")
    assert out["per_asset"]["A2"]["additional_263a"] == D("0")
    rows = [r for r in out["audit_trail"] if r["pool_id"] == "HR"]
    assert len(rows) == 3 and all(r["allocated"] == 0 for r in rows)
    assert out["conservation_checks"][0]["ok"]      # expected 0, allocated 0


def test_degenerate_denominator():
    """Σ driver values == 0 → allocate 0, flag POOL-DEGENERATE-DENOMINATOR
    (BUILD_PLAN.md guardrails bullet). 40,000/0 is not a share — nothing
    books, nothing errors."""
    pool = CostPool(pool_id="UTIL", description="Utilities pool",
                    amount=D("40000"), driver="machine_hours",
                    is_mixed_service=False,
                    targets={"A1": D("0"), "A2": D("0")})
    out = compute_sca([pool], _assets(), sscm_ratio=D("0.60"))
    assert any("POOL-DEGENERATE-DENOMINATOR" in w for w in out["warnings"])
    assert out["per_asset"]["A1"]["indirect_263a"] == D("0")
    assert out["per_asset"]["A2"]["indirect_263a"] == D("0")
    assert all(r["allocated"] == 0 for r in out["audit_trail"])


def test_penny_plug_conservation():
    """$100 across 3 equal-driver targets: each raw share 100/3 =
    33.333... → round2 = 33.33 each, Σ = 99.99, one cent short. The largest
    driver-value target (tie → first declared, A1) is penny-plugged to
    33.34 so Σ allocated == 100.00 == pool.amount EXACTLY."""
    assets = _assets() + [SelfConstructedAsset(
        asset_id="A3", description="Third asset", book_cost=D("0"),
        sscm_eligible=True)]
    pool = CostPool(pool_id="SUP", description="Supervision pool",
                    amount=D("100"), driver="direct_labor",
                    is_mixed_service=False,
                    targets={"A1": D("1"), "A2": D("1"), "A3": D("1")})
    out = compute_sca([pool], assets, sscm_ratio=D("0.60"))
    alloc = {r["target"]: r["allocated"] for r in out["audit_trail"]}
    assert alloc["A1"] == D("33.34")
    assert alloc["A2"] == D("33.33") and alloc["A3"] == D("33.33")
    assert sum(alloc.values()) == D("100.00")
    check = out["conservation_checks"][0]
    assert check["ok"] and check["allocated_sum"] == pool.amount


def test_book_capitalized_indirect_routes_to_review_queue():
    """Bucket A/B double-count rule is UNRESOLVED (BUILD_PLAN.md Basis
    Reconciliation §(2), Gate 6 Q6.3): a nonzero book-capitalized-indirect
    amount emits CIP-DOUBLE-COUNT-REVIEW naming the $5,000.00, and the
    computation is IDENTICAL to the golden test — no adjustment invented."""
    out = compute_sca([_hr_pool(), _building_pool()], _assets(),
                      sscm_ratio=D("0.60"),
                      book_capitalized_indirect={"A1": D("5000")})
    review = [w for w in out["warnings"] if "CIP-DOUBLE-COUNT-REVIEW" in w]
    assert len(review) == 1
    assert "A1" in review[0] and "5,000.00" in review[0]
    # amounts unchanged vs. the golden fixture
    assert out["per_asset"]["A1"]["additional_263a"] == D("55000.00")
    assert out["per_asset"]["A2"]["additional_263a"] == D("55000.00")
    assert out["not_booked_total"] == D("0")


def test_drivers_yaml_unknown_driver_errors(tmp_path):
    """Loader dead-entry guard: a driver named in a category but absent from
    the `drivers` list is a typo/dead entry and must error at load."""
    bad = tmp_path / "bad_drivers.yaml"
    bad.write_text(
        "drivers: [headcount]\n"
        "categories:\n"
        "  - match_keywords: [hr]\n"
        "    preferred: [head_count]\n"    # typo — not declared
        "    blocked: []\n"
        "default:\n  allowed: [headcount]\n")
    with pytest.raises(DriverTaxonomyError):
        load_drivers(str(bad))


def test_shipped_drivers_yaml_loads_clean():
    """The shipped taxonomy/sca_drivers.yaml passes its own validation."""
    data = load_drivers()
    assert "categories" in data and "default" in data
