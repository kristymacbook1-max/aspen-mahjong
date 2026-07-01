"""Taxonomy integrity + tax-fix regression tests."""

from financial_tools.cap263a import get_taxonomy


def test_taxonomy_loads_and_validates():
    t = get_taxonomy()
    assert len(t.categories) >= 130
    assert t.validate() is True


def test_all_reclass_targets_resolve():
    # The bug class the original tool shipped: MSC-RENT/MSC-DEP/... dangling targets.
    t = get_taxonomy()
    for (zone, exp), target in t._reclass_index.items():
        assert target in t.by_code, f"reclass ({zone},{exp}) -> missing {target}"


def test_all_generic_map_keys_are_categories():
    t = get_taxonomy()
    for gcode in t.generic_map:
        assert gcode in t.by_code, f"generic_map key {gcode} not a category"


def test_vague_codes_never_map_to_compensation():
    # Original bug: VAGUE-* -> compensation -> DL-PROD (variances tagged direct labor).
    t = get_taxonomy()
    for gcode, exp in t.generic_map.items():
        if gcode.startswith("VAGUE-"):
            assert exp == "suspense"


def test_corporate_reclass_targets_fixed():
    t = get_taxonomy()
    assert t.reclass_target("corporate", "rent") == "MSC-CORPRENT"
    assert t.reclass_target("corporate", "utilities") == "MSC-CORPUTIL"
    assert t.reclass_target("corporate", "depreciation") == "MSC-CORPDEP"


def test_tax_fixes_applied():
    t = get_taxonomy()
    # FO-PTAX is not labor (was mislabeled labor/benefits)
    assert t.by_code["FO-PTAX"]["is_labor"] is False
    # Officer comp re-tiered to mixed service (allocable), not Non-Operating
    assert t.by_code["NO-OFFICER"]["tier1"] == "Mixed Service"
    # Capitalizable interest re-tiered to §263A(f)
    assert t.by_code["NO-INTCAP"]["tier1"] == "§263A(f) Interest"


def test_missing_regimes_added():
    t = get_taxonomy()
    tiers = {c["tier1"] for c in t.categories}
    assert "§266 Carrying Charges" in tiers
    assert "§263(a) Transaction/Intangible" in tiers
    assert "§263(a) Tangible" in tiers
    assert "§263A(f) Interest" in tiers
    # §266 codes present
    assert "SEC266-TAX" in t.by_code
