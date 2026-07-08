"""Phase 2: dollars-through-the-hierarchy + waterfall bucketing."""

from decimal import Decimal
from financial_tools.cap263a.model import TBLine
from financial_tools.cap263a.analysis import analyze, EntityProfile


def _tb():
    return [
        TBLine("5000", "Direct labor", "100", "Production", amount=Decimal("1000000")),
        TBLine("5100", "Factory depreciation", "100", "Plant", amount=Decimal("500000")),
        TBLine("6000", "Warehouse storage and handling", "200", "Warehouse", amount=Decimal("300000")),
        TBLine("7000", "Advertising", "400", "Marketing", amount=Decimal("200000")),
        TBLine("8000", "Officer compensation", "400", "Executive", amount=Decimal("400000")),
        TBLine("1000", "Accounts receivable", "", "", amount=Decimal("999")),
    ]


def test_amounts_carry_through_and_tie():
    r = analyze(_tb(), EntityProfile(avg_gross_receipts=Decimal("75000000")))
    assert r["tie_check"] == Decimal("0")
    # AR is a balance-sheet line, excluded from the IS total
    assert r["is_total"] == Decimal("2400000")


def test_bucketing():
    r = analyze(_tb(), EntityProfile(avg_gross_receipts=Decimal("75000000")))
    b = r["bucket_totals"]
    assert b["Inventory §471"] == Decimal("1500000")      # labor + factory dep
    assert b["§263A Additional"] == Decimal("300000")     # warehouse storage
    assert b["Deductible"] == Decimal("200000")           # advertising
    assert b["Mixed (allocable)"] == Decimal("400000")    # officer comp (allocable)


def test_small_business_exemption_turns_off_unicap():
    r = analyze(_tb(), EntityProfile(avg_gross_receipts=Decimal("1000000")))
    b = r["bucket_totals"]
    # under the §448(c) threshold: §471 / additional / mixed all fall to deductible
    assert b["Inventory §471"] == Decimal("0")
    assert b["§263A Additional"] == Decimal("0")
    assert b["Deductible"] >= Decimal("1800000")


def test_tax_shelter_barred_from_small_business_exemption():
    """§1.263A-1(b)(1)/(j): a §448(a)(3) tax shelter cannot use the small-
    business exemption regardless of gross receipts (added 2026-07-09 —
    the receipts-only gate silently exempted ineligible taxpayers)."""
    p = EntityProfile(avg_gross_receipts=Decimal("1000000"), is_tax_shelter=True)
    assert not p.small_business_exempt
    r = analyze(_tb(), p)
    assert not r["unicap"]["exempt"]
    assert r["bucket_totals"]["Inventory §471"] > Decimal("0")


def test_unicap_absorption_and_sscm():
    from decimal import Decimal as D
    lines = _tb()
    p = EntityProfile(avg_gross_receipts=D("75000000"), ending_inventory_471=D("1000000"))
    r = analyze(lines, p)
    u = r["unicap"]
    assert not u["exempt"]
    # SSCM ratio = production labor / total labor; officer comp is mixed (not labor)
    assert D("0") < u["mixed_alloc_ratio"] <= D("1")
    # absorption ratio = additional pool / §471 pool; capitalized = ending inv * ratio
    expected = (u["ending_inventory_471"] * u["absorption_ratio"]).quantize(D("0.01"))
    assert u["additional_capitalized_to_inventory"] == expected


def test_unicap_exempt_when_small():
    from decimal import Decimal as D
    r = analyze(_tb(), EntityProfile(avg_gross_receipts=D("1000000")))
    assert r["unicap"]["exempt"] is True
    assert r["unicap"]["additional_capitalized_to_inventory"] == D("0")


def test_absorption_over_100pct_and_bad_ending_inventory_warn():
    """A tiny §471 pool with a large additional pool gives an absorption ratio
    >100%, and a free-typed ending inventory inconsistent with the pool makes
    the capitalized-to-inventory figure meaningless — both must warn."""
    lines = [TBLine("5000", "Raw materials", "100", "Production", amount=Decimal("100")),
             TBLine("6000", "Purchasing dept salaries", "200", "Procurement", amount=Decimal("500000"))]
    r = analyze(lines, EntityProfile(avg_gross_receipts=Decimal("100000000"),
                                     ending_inventory_471=Decimal("10000000")))
    joined = " ".join(r["unicap"]["warnings"])
    assert "ABSORPTION RATIO" in joined and ">100%" in joined
    assert "EXCEEDS THE" in joined


def test_sscm_ratio_override_and_labor_are_clamped_to_unit_interval():
    """A mixed_alloc_ratio override > 1 (or a negative labor-derived ratio)
    must be clamped to [0,1] and warned — a service-cost ratio is a fraction."""
    lines = [TBLine("1", "Officer compensation", "", "Executive", amount=Decimal("300000")),
             TBLine("2", "Raw materials", "", "Production", amount=Decimal("1000000"))]
    r = analyze(lines, EntityProfile(avg_gross_receipts=Decimal("100000000"),
                                     mixed_alloc_ratio=Decimal("3.5")))
    assert r["unicap"]["mixed_alloc_ratio"] == Decimal("1.000000")
    assert r["unicap"]["mixed_capitalized"] == Decimal("300000.00")   # not 1,050,000
    assert any("OVERRIDE" in w for w in r["unicap"]["warnings"])


def test_negative_capitalized_buckets_are_flagged():
    """A contra/reversal line driving §263(a) Mandatory (or any capitalized
    bucket) negative is economically invalid and must be surfaced — the
    original negative-pool guard only saw the §263A pools."""
    lines = [TBLine("1", "Facilitative transaction cost", "", "", amount=Decimal("100000")),
             TBLine("2", "Trademark cost refund", "", "", amount=Decimal("-900000")),
             TBLine("3", "Raw materials", "", "Production", amount=Decimal("1000000"))]
    r = analyze(lines, EntityProfile(avg_gross_receipts=Decimal("100000000")))
    assert r["bucket_totals"]["§263(a) Mandatory"] < 0
    assert any("NEGATIVE" in w and "263(a) Mandatory" in w for w in r["bucket_warnings"])


def test_small_business_exemption_covers_263af_interest():
    """§263A(i) exempts from ALL of §263A including (f) — a §263A(f)-coded
    interest line must fall to Deductible for an exempt entity, not stay in
    the capitalized bucket while the Summary says 'UNICAP off'. §266 (a
    non-§263A provision) is deliberately NOT gated."""
    lines = [TBLine("7100", "Construction period interest", "300", "Plant Construction",
                    amount=Decimal("12000"))]
    exempt = analyze(lines, EntityProfile(avg_gross_receipts=Decimal("1000000")))
    assert exempt["bucket_totals"]["§263A(f) Interest"] == Decimal("0")
    assert exempt["bucket_totals"]["Deductible"] == Decimal("12000")
    large = analyze(lines, EntityProfile(avg_gross_receipts=Decimal("75000000")))
    assert large["bucket_totals"]["§263A(f) Interest"] == Decimal("12000")


def test_negative_additional_pool_is_warned_with_large_producer_rule():
    """A negative additional §263A pool used to flow silently into a negative
    absorption ratio and a negative 'capitalized' amount. It must carry
    warnings — including the large-producer (>$50M) negative-adjustment rule
    when method=SPM. Citation §1.263A-1(d)(3)(ii)(B)(1) VERIFIED 2026-07-08
    against primary-source regulation text (26 CFR 1.263A-1) — corrected from
    two earlier wrong guesses ((C), then an unverified T.D. number); (B) lists
    the three taxpayer types (SPM<=$50M / MSPM / SRM) permitted negative
    adjustments, (C) is the unrelated cash/trade-discount rule."""
    lines = [
        TBLine("5000", "Raw materials", "100", "Production", amount=Decimal("1000000")),
        TBLine("6000", "Warehouse rent", "200", "Warehouse", amount=Decimal("60000")),
        TBLine("6100", "Excess book depreciation", "200", "Warehouse", amount=Decimal("-400000")),
    ]
    p = EntityProfile(avg_gross_receipts=Decimal("75000000"),
                      ending_inventory_471=Decimal("500000"), method="SPM")
    u = analyze(lines, p)["unicap"]
    assert u["additional_263a_pool"] < 0
    joined = " ".join(u["warnings"])
    assert "NEGATIVE ADDITIONAL" in joined
    assert "§1.263A-1(d)(3)(ii)(B)(1)" in joined
    assert ">$50M" in joined


def test_unimplemented_method_and_stale_threshold_are_warned():
    """--method MSPM/SRM silently computed SPM with no indication; a tax year
    with no published §448(c) threshold silently used the 2026 figure. Both
    must surface as warnings."""
    lines = [TBLine("5000", "Direct labor", "100", "Production", amount=Decimal("100000"))]
    p = EntityProfile(avg_gross_receipts=Decimal("75000000"), method="MSPM", tax_year=2027)
    assert p.sec448_threshold_is_estimate
    u = analyze(lines, p)["unicap"]
    joined = " ".join(u["warnings"])
    assert "MSPM" in joined and "not implemented" in joined
    assert "2027" in joined and "VERIFY" in joined


def test_sscm_labor_ratio_excludes_msc_labor_and_includes_all_other_tob_labor():
    """Reg §1.263A-1(h)(4), CORRECTED 2026-07-09 (docs/TAX_DECISIONS.md §9):
    the labor-based allocation ratio's denominator is TOTAL trade-or-business
    labor EXCLUDING labor included in mixed service costs. A prior version of
    this test asserted the opposite rule on both counts (mixed-service officer
    comp IN the denominator, sales-commission labor OUT), citing the same
    regulation — the code and this test were wrong together. Under (h)(4):
    numerator = §263A labor (production 100k); denominator = production 100k +
    sales 850k = 950k (officer comp is mixed-service labor, excluded from
    BOTH)."""
    lines = [
        TBLine("5000", "Direct labor", "100", "Production", amount=Decimal("100000")),
        TBLine("8000", "Officer compensation", "400", "Executive", amount=Decimal("50000")),
        TBLine("9000", "Sales commissions", "500", "Sales", amount=Decimal("850000")),
    ]
    p = EntityProfile(avg_gross_receipts=Decimal("75000000"), ending_inventory_471=Decimal("0"))
    r = analyze(lines, p)
    u = r["unicap"]
    assert u["production_labor"] == Decimal("100000"), f"got {u['production_labor']}"
    assert u["total_labor"] == Decimal("950000"), f"got {u['total_labor']}"
    assert u["mixed_alloc_ratio"] == Decimal("0.105263")


def test_sscm_labor_ratio_includes_additional_263a_tier_labor():
    """SME decision (docs/TAX_DECISIONS.md §3 item 5, resolved; ratio values
    re-derived 2026-07-09 under the corrected §1.263A-1(h)(4) denominator —
    see §9): purchasing and warehouse labor (Additional §263A tier — already
    100% capitalized in its own right) belongs in BOTH the numerator and
    denominator of the SSCM ratio, not excluded entirely. Under the corrected
    denominator rule: §471 $200k / Mixed $50k / Additional §263A $80k /
    Excluded $300k -> numerator = 200k+80k = 280k; denominator = 200k+80k+300k
    = 580k (mixed-service officer comp excluded); ratio = 0.482759."""
    lines = [
        TBLine("1", "Direct labor", "100", "Production", amount=Decimal("200000")),
        TBLine("2", "Officer compensation", "400", "Executive", amount=Decimal("50000")),
        TBLine("3", "Purchasing dept salaries", "200", "Procurement", amount=Decimal("80000")),
        TBLine("4", "Sales commissions", "500", "Sales", amount=Decimal("300000")),
    ]
    p = EntityProfile(avg_gross_receipts=Decimal("75000000"))
    u = analyze(lines, p)["unicap"]
    assert u["production_labor"] == Decimal("280000"), f"got {u['production_labor']}"
    assert u["total_labor"] == Decimal("580000"), f"got {u['total_labor']}"
    assert u["mixed_alloc_ratio"] == Decimal("0.482759")
