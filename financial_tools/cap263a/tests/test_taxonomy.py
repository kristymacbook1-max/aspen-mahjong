"""Taxonomy integrity + tax-fix regression tests."""

import ast
import inspect

import pytest
from financial_tools.cap263a import get_taxonomy
from financial_tools.cap263a.taxonomy import Taxonomy, TaxonomyError


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


def test_no_dead_code_after_return():
    """The original bug class: __init__'s tail (_zone_rules/_build_keyword_index/
    validate) landed after a `return` in from_data() and never ran. Statically
    assert no function body in taxonomy.py has unreachable statements after an
    unconditional `return` at the same block level."""
    src = inspect.getsource(inspect.getmodule(Taxonomy))
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for i, stmt in enumerate(node.body[:-1]):
                if isinstance(stmt, ast.Return):
                    unreachable = node.body[i + 1]
                    pytest.fail(f"{node.name}: unreachable code after return at "
                                f"line {unreachable.lineno}")


def test_validate_actually_raises_on_bad_data():
    """validate() must really run and really catch a dangling reference —
    not just claim to via a docstring."""
    t = get_taxonomy()
    bad_categories = [dict(c) for c in t.categories]
    bad_cc_reclass = list(t.cc_reclass) + [
        {"zone": "production", "expense_type": "bogus", "target": "NOT-A-REAL-CODE"}]
    with pytest.raises(TaxonomyError):
        Taxonomy.from_data(
            categories=bad_categories, cc_zones=t.cc_zones, cc_reclass=bad_cc_reclass,
            generic_map=t.generic_map,
            lexicon={"abbreviations": t.abbreviations, "account_synonyms": t.account_synonyms,
                     "cc_synonyms": t.cc_synonyms})
