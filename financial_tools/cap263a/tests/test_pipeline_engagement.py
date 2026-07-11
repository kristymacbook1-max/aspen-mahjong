"""End-to-end Runtime Pipeline: uploads in -> every engine -> one result."""

import json
from decimal import Decimal

from financial_tools.cap263a.analysis import EntityProfile
from financial_tools.cap263a.pipeline import CapitalizationPipeline


def _engagement_json(tmp_path):
    doc = {
        "trial_balance": [
            {"acct_num": "5000", "acct_desc": "Direct labor", "cc_num": "100",
             "cc_desc": "Production", "amount": "1000000"},
            {"acct_num": "6000", "acct_desc": "Warehouse storage and handling",
             "cc_num": "200", "cc_desc": "Warehouse", "amount": "300000"},
            {"acct_num": "7000", "acct_desc": "Advertising", "cc_num": "400",
             "cc_desc": "Marketing", "amount": "200000"},
        ],
        "btd": [
            {"acct_num": "5000", "cc_num": "100", "description": "Comp accrual",
             "adjustment": "-40000"},
        ],
        "fixed_assets": [
            {"asset_id": "FA1", "description": "Plant", "asset_type": "real",
             "cost": "2500000"},
        ],
        "cip": [
            {"project_id": "P1", "description": "Expansion",
             "linked_asset_id": "FA1", "is_real_property": "yes"},
        ],
        "cip_snapshots": [
            {"project_id": "P1", "measurement_date": "2026-03-31", "cumulative_ape": "3500000"},
            {"project_id": "P1", "measurement_date": "2026-06-30", "cumulative_ape": "5000000"},
            {"project_id": "P1", "measurement_date": "2026-09-30", "cumulative_ape": "6500000"},
            {"project_id": "P1", "measurement_date": "2026-12-31", "cumulative_ape": "8000000"},
        ],
        "debt": [
            {"debt_id": "L1", "principal": "3000000", "rate": "0.06",
             "interest_incurred": "180000", "traced_to": "P1"},
            {"debt_id": "L2", "principal": "2800000", "interest_incurred": "200000"},
        ],
        "re": [
            {"re_id": "R1", "description": "Foreign lab", "amount": "150000",
             "domestic": "no", "tax_year": "2026"},
            {"re_id": "R2", "description": "US software dev", "amount": "500000",
             "domestic": "yes", "tax_year": "2026"},
        ],
        "startup": [
            {"pool_id": "S1", "kind": "startup", "total": "52000",
             "business_commencement": "2026-01-01"},
        ],
        "qualified_expenditures": [
            {"item_id": "Q1", "category": "idc", "amount": "120000",
             "elected": "yes", "election_year": "2026"},
        ],
        "ppa": [
            {"transaction id": "T1", "aggregate consideration": "1000000",
             "class": "IV", "fmv": "300000"},
            {"transaction id": "T1", "class": "V", "fmv": "500000"},
        ],
    }
    p = tmp_path / "engagement.json"
    p.write_text(json.dumps(doc))
    return p


def test_full_pipeline_runs_every_engine(tmp_path):
    """One engagement upload drives every engine: tax-basis TB applied before
    classification (labor 1,000,000 - 40,000 = 960,000 in the §471 bucket),
    §263A(f) hits the golden 376,428.57, foreign R&E amortizes, the startup
    pool computes 3,000 first-year deduction, the §59(e) item is gated OUT
    for a C-corp with no individual AMT exposure, and §1060 leaves a 200,000
    Class VII residual."""
    pipe = CapitalizationPipeline(output_dir=str(tmp_path / "out"))
    profile = EntityProfile(entity_name="E2E Test Co",
                            avg_gross_receipts=Decimal("75000000"),
                            ending_inventory_471=Decimal("500000"))
    r = pipe.run_engagement(_engagement_json(tmp_path), profile)

    # Step 2: tax-basis TB materialized and used downstream
    assert r["tax_basis_tb"]["m1_reconciliation"]["tie_check"] == Decimal("0")
    assert r["bucket_totals"]["Inventory §471"] == Decimal("960000")

    # Phase D golden (the plan's corrected fixture)
    interest = r["interest_263af"]
    assert interest["total_capitalized"] == Decimal("376428.57")
    assert interest["per_unit"]["P1"]["traced_interest"] == Decimal("180000")

    # Phase F: foreign capitalized (mid-year 15-yr), domestic expensed
    re_out = r["re_174"]
    assert re_out["capitalized_total"] == Decimal("150000")
    foreign_items = [i for i in re_out["amortizable_items"]]
    assert foreign_items and foreign_items[0].first_year_amortization() == Decimal("5000.00")

    # Phase G: startup 52,000 -> 3,000 first-year deduction, remainder amortizes
    su = r["intangibles_263a45"]["startup_items"][0]
    assert su["first_year_deduction"] == Decimal("3000")

    # Phase H: gated out for a C-corp with no individual-AMT exposure
    assert r["qualified_59e"]["items"] == []
    assert any("C corp" in w or "CAMT" in w for w in r["qualified_59e"]["warnings"])

    # §1060: 1,000,000 - 300,000 (IV) - 500,000 (V) = 200,000 Class VII
    ppa = r["ppa_1060"][0]
    assert ppa["class_vii_residual"] == Decimal("200000")

    # consolidated outputs
    assert r["basis_amortization"], "AmortizableItem rows must roll up"
    assert isinstance(r["all_warnings"], list)
    assert r["_output_path"].endswith(".xlsx")


def test_exempt_entity_skips_263af_but_not_174(tmp_path):
    """§263A(i) exemption turns off §263A(f) but NOT §174 (a non-§263A
    provision) — the pipeline must gate them differently."""
    pipe = CapitalizationPipeline(output_dir=str(tmp_path / "out"))
    profile = EntityProfile(avg_gross_receipts=Decimal("1000000"))
    r = pipe.run_engagement(_engagement_json(tmp_path), profile,
                            generate_workbook=False)
    assert "interest_263af" not in r
    assert r["re_174"]["capitalized_total"] == Decimal("150000")


def test_59e_runs_for_individual_amt_exposure(tmp_path):
    pipe = CapitalizationPipeline(output_dir=str(tmp_path / "out"))
    profile = EntityProfile(entity_type="partnership",
                            avg_gross_receipts=Decimal("75000000"))
    r = pipe.run_engagement(_engagement_json(tmp_path), profile,
                            individual_amt_exposure=True,
                            generate_workbook=False)
    items = r["qualified_59e"]["items"]
    assert items and items[0]["category"] == "idc"
