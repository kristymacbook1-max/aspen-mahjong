"""Round 5 — deferred mechanics implemented: HAR (§1.263A-2(c)(4)),
MSPM+LIFO combined ratio ((c)(3)(iv)), the $200K producer de minimis
((b)(3)(iv)/(c)(3)(v)), and the last three §1.263A-9(a)(4) debt screens.
Golden figures from BUILD_PLAN.md (regulation-sourced where the reg gives
them — Example 3's 9.48%/$142,200)."""

from datetime import date
from decimal import Decimal

from financial_tools.cap263a.analysis import EntityProfile, analyze
from financial_tools.cap263a.engines.interest import compute_263af
from financial_tools.cap263a.engines.inventory import compute_mspm
from financial_tools.cap263a.model import (CIPProject, CIPSnapshot,
                                           DebtInstrument, TBLine)


def _res(mixed=Decimal("0"), ded=Decimal("0")):
    return {"rows": [], "bucket_totals": {"Inventory §471": Decimal("0"),
                                          "§263A Additional": Decimal("0")},
            "mixed_total": mixed, "deductible_total": ded}


def _taxpayer_p(**overrides):
    """The regulation's own Example 1 facts (non-LIFO ACI = 284,400)."""
    kw = dict(avg_gross_receipts=Decimal("75000000"), method="MSPM",
              pre_production_471=Decimal("2500000"),
              production_471=Decimal("7500000"),
              pre_production_additional_263A=Decimal("200000"),
              production_additional_263A=Decimal("800000"),
              pre_production_471_on_hand=Decimal("1000000"),
              production_471_on_hand=Decimal("2000000"),
              beginning_DM_not_yet_in_production=Decimal("400000"),
              ending_DM_not_yet_in_production=Decimal("800000"),
              DM_purchased_during_year=Decimal("1900000"))
    kw.update(overrides)
    return EntityProfile(**kw)


def test_mspm_lifo_combined_ratio_example_3():
    """§1.263A-2(c)(3)(iv) Example 3 on the Taxpayer P facts: combined =
    284,400 / 3,000,000 = 9.48%, applied to a $1,500,000 increment =
    $142,200 — NOT the two ratios applied separately."""
    p = _taxpayer_p(inventory_method="lifo_dollar_value",
                    lifo_current_year_increment_471=Decimal("1500000"))
    u = compute_mspm(_res(), p)
    assert u["lifo_combined_ratio"] == Decimal("0.0948")
    assert u["additional_capitalized_to_inventory"] == Decimal("142200.00")
    assert not any("NOT-IMPLEMENTED" in w for w in u["warnings"])


def test_mspm_lifo_missing_increment_warns_with_nonlifo_figure():
    p = _taxpayer_p(inventory_method="lifo_dollar_value")
    u = compute_mspm(_res(), p)
    assert any("MSPM-LIFO-INCREMENT-MISSING" in w for w in u["warnings"])
    assert u["additional_capitalized_to_inventory"] == Decimal("284400.00")


def test_mspm_lifo_decrement_flagged():
    p = _taxpayer_p(inventory_method="lifo_dollar_value",
                    lifo_current_year_increment_471=Decimal("-100000"))
    u = compute_mspm(_res(), p)
    assert any("LIFO-DECREMENT-NOT-IMPLEMENTED" in w for w in u["warnings"])


def test_har_frozen_ratios_apply():
    """HAR in a qualifying year: frozen ratios replace actuals. Frozen
    9.00%/11.00% on Taxpayer P's on-hand figures: 0.09x1,000,000 +
    0.11x2,000,000 = 90,000 + 220,000 = 310,000."""
    p = _taxpayer_p(har_election=True,
                    har_preprod_ratio=Decimal("0.09"),
                    har_production_ratio=Decimal("0.11"),
                    har_qualifying_year_index=2)
    u = compute_mspm(_res(), p)
    assert u["har_applied"] is True
    assert u["additional_capitalized_to_inventory"] == Decimal("310000.00")
    # actuals still reported for the audit trail
    assert u["actual_pre_production_ratio"] == Decimal("0.0800")


def test_har_missing_ratios_warns_and_uses_actuals():
    p = _taxpayer_p(har_election=True)
    u = compute_mspm(_res(), p)
    assert u["har_applied"] is False
    assert any("HAR-RATIOS-MISSING" in w for w in u["warnings"])
    assert u["additional_capitalized_to_inventory"] == Decimal("284400.00")


def test_har_recomputation_pass_and_fail():
    """Recomputation year (index 6): BOTH ratios within ±0.5pp of actuals
    (0.0800/0.1022) -> extension; either outside -> actuals + resumption
    warning. 0.0790/0.1050 both inside; 0.0730 outside."""
    passing = _taxpayer_p(har_election=True, har_qualifying_year_index=6,
                          har_preprod_ratio=Decimal("0.0790"),
                          har_production_ratio=Decimal("0.1050"))
    u = compute_mspm(_res(), passing)
    assert u["har_applied"] is True
    assert any("HAR-RECOMPUTATION-PASSED" in w for w in u["warnings"])

    failing = _taxpayer_p(har_election=True, har_qualifying_year_index=6,
                          har_preprod_ratio=Decimal("0.0730"),
                          har_production_ratio=Decimal("0.1050"))
    u2 = compute_mspm(_res(), failing)
    assert u2["har_applied"] is False
    assert any("HAR-RECOMPUTATION-FAILED" in w for w in u2["warnings"])
    assert u2["additional_capitalized_to_inventory"] == Decimal("284400.00")


def test_200k_de_minimis_deems_zero_and_bars_har():
    p = _taxpayer_p(producer_de_minimis_200k=True, har_election=True)
    u = compute_mspm(_res(mixed=Decimal("50000"), ded=Decimal("10000")), p)
    assert u["additional_capitalized_to_inventory"] == Decimal("0")
    assert any("HAR-BARRED-200K" in w for w in u["warnings"])
    assert u["adjusted_deductible_post"] == Decimal("60000")


def test_200k_de_minimis_spm_path():
    lines = [TBLine("5000", "Direct labor", "100", "Production",
                    amount=Decimal("100000"))]
    p = EntityProfile(avg_gross_receipts=Decimal("75000000"),
                      producer_de_minimis_200k=True,
                      ending_inventory_471=Decimal("500000"))
    r = analyze(lines, p)
    assert r["unicap"]["additional_capitalized_to_inventory"] == Decimal("0")
    assert "de minimis" in r["unicap"]["note"]


def test_remaining_a4_debt_screens_excluded_and_named():
    unit = CIPProject(project_id="U", snapshots=[
        CIPSnapshot(measurement_date=date(2026, 3, 31),
                    cumulative_ape=Decimal("1000000"))])
    debts = [
        DebtInstrument(debt_id="DTL", principal=Decimal("100"),
                       interest_incurred=Decimal("5"),
                       reserve_or_deferred_tax=True),
        DebtInstrument(debt_id="453A", principal=Decimal("100"),
                       interest_incurred=Decimal("5"),
                       tax_liability_453a_460b=True),
        DebtInstrument(debt_id="SLB", principal=Decimal("100"),
                       interest_incurred=Decimal("5"),
                       sale_leaseback_purchase_money=True),
        DebtInstrument(debt_id="OK", principal=Decimal("1000000"),
                       interest_incurred=Decimal("50000")),
    ]
    out = compute_263af([unit], debts)
    joined = " ".join(out["warnings"])
    assert "DTL" in joined and "deferred-tax" in joined
    assert "453A" in joined and "§453A" in joined
    assert "SLB" in joined and "sale-leaseback" in joined
    # only the clean debt feeds WAIR: 50,000 / 1,000,000 = 5%
    assert out["wair"] == Decimal("50000") / Decimal("1000000")
