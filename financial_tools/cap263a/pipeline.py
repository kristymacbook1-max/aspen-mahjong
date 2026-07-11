"""Pipeline: trial balance in → classified + FTA workbook out.

run() is the original TB-only path. run_engagement() is the full Runtime
Pipeline (BUILD_PLAN.md): ingest any-format uploads → tax-basis TB →
classify/UNICAP (SPM/MSPM/SRM dispatch) → SCA → §263A(f) → §174 →
§1.263(a)-4/-5 + start-up → §59(e) → §1060 — every engine's output and the
consolidated Basis & Amortization Schedule in one result dict.
"""

import os
import re
import warnings as _warnings
from datetime import datetime
from decimal import Decimal

from .reader import read_trial_balance
from .analysis import analyze, EntityProfile
from .report import CapitalizationReport

_UNSAFE_TAG_CHARS = re.compile(r"[^\w\-]+")


class CapitalizationPipeline:
    def __init__(self, output_dir: str = "output/cap263a"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def run(self, tb_path: str, profile: EntityProfile = None,
            company_tag: str = None, timestamp: str = None, sheet: str = None) -> dict:
        # Reader warnings (missing columns etc.) are data-quality caveats the
        # workpaper should document, not just ephemeral stderr text — capture
        # them into the result so the Summary tab renders them.
        with _warnings.catch_warnings(record=True) as caught:
            _warnings.simplefilter("always")
            lines = read_trial_balance(tb_path, sheet=sheet)
        result = analyze(lines, profile)
        result["data_quality"] = [str(w.message) for w in caught]
        tag = company_tag or (profile.entity_name if profile else None) or "entity"
        # An unsanitized entity name (e.g. "Acme/Sub LLC" or "../../etc") could
        # otherwise create unintended subdirectories or write outside output_dir
        # via os.path.join — collapse anything that isn't a word char/hyphen.
        # Cap the length too: a very long client name would blow past the OS's
        # 255-char filename limit and raise OSError.
        tag = (_UNSAFE_TAG_CHARS.sub("_", tag).strip("_") or "entity")[:100]
        ts = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
        out = os.path.join(self.output_dir, f"{tag}_cap263a_{ts}.xlsx")
        CapitalizationReport().generate(result, out)
        result["_output_path"] = out
        return result

    def run_engagement(self, source=None, profile: EntityProfile = None, *,
                       answers: dict = None,
                       sca_pools=None, sca_assets=None,
                       afr_highest: Decimal = None,
                       guaranteed_payments: Decimal = Decimal("0"),
                       below_afr_interest: Decimal = Decimal("0"),
                       re_options: dict = None,
                       success_fee_elections=frozenset(),
                       individual_amt_exposure: bool = False,
                       generate_workbook: bool = True,
                       company_tag: str = None, timestamp: str = None,
                       **reader_kwargs) -> dict:
        """The full Runtime Pipeline over an engagement.

        `source` is anything readers.read_engagement accepts (xlsx workbook,
        json engagement, directory of schedule files) — or an EngagementData
        instance directly. `answers` (a Phase E interview answers dict) builds
        the EntityProfile when no explicit `profile` is given. Engines only
        run when their schedules are present; every engine's warnings roll up
        into result["all_warnings"] and its AmortizableItem rows into
        result["basis_amortization"].
        """
        from .model import EngagementData
        from .readers import read_engagement
        from .engines.tax_basis_tb import compute_tax_basis_tb
        from .engines.interest import compute_263af
        from .engines.re_capitalization import compute_174
        from .engines.intangibles import compute_263a4_5
        from .engines.qualified_expenditures import compute_59e
        from .engines.purchase_price_allocation import compute_1060_allocation

        data = source if isinstance(source, EngagementData) else \
            read_engagement(source, **reader_kwargs)

        # Step 0 (Phase E): interview answers -> EntityProfile
        interview_result = None
        if profile is None and answers is not None:
            from .interview import run_interview
            interview_result = run_interview(answers)
            profile = interview_result.profile
        profile = profile or EntityProfile()

        # Step 2: tax-basis TB (materialized; downstream classifies THIS)
        tax_tb = None
        lines = data.tb_lines
        if data.btds:
            tax_tb = compute_tax_basis_tb(data.tb_lines, data.btds)
            lines = tax_tb["tax_lines"]

        # Step 3a: classify + UNICAP (SPM/MSPM/SRM dispatch inside analyze)
        result = analyze(lines, profile)
        result["engagement_validation"] = data.validation
        result["tax_basis_tb"] = tax_tb
        result["interview"] = interview_result

        basis_items = []
        all_warnings = list(result.get("bucket_warnings", []))
        all_warnings += result.get("unicap", {}).get("warnings", [])
        if tax_tb:
            all_warnings += tax_tb["warnings"]

        # Phase C — SCA (pools/assets are computed inputs, passed explicitly).
        # §263A(i) exempts a small business from ALL of §263A — SCA included,
        # same gate as Phase D below (found in red-team: SCA previously ran
        # for exempt taxpayers, and the exempt unicap dict has no
        # mixed_alloc_ratio key, silently allocating at ratio 0).
        if sca_pools and sca_assets and not profile.small_business_exempt:
            from .engines.sca import compute_sca
            sscm_ratio = result["unicap"].get("mixed_alloc_ratio", Decimal("0"))
            result["sca"] = compute_sca(sca_pools, sca_assets, sscm_ratio)
            all_warnings += result["sca"]["warnings"]
        elif sca_pools and sca_assets:
            all_warnings.append(
                "SCA skipped: §263A(i)/§448(c) small-business exemption covers "
                "self-constructed assets too — no §263A capitalization to them.")

        # Phase D — §263A(f); exempt entities skip ALL of §263A including (f)
        if data.cip_projects and data.debts and not profile.small_business_exempt:
            result["interest_263af"] = compute_263af(
                data.cip_projects, data.debts, afr_highest=afr_highest,
                below_afr_interest=below_afr_interest,
                guaranteed_payments=guaranteed_payments)
            all_warnings += result["interest_263af"]["warnings"]

        # Phase F — §174/§174A (NOT gated on the §263A exemption)
        if data.re_expenditures:
            result["re_174"] = compute_174(
                data.re_expenditures, current_tax_year=profile.tax_year,
                **(re_options or {}))
            basis_items += result["re_174"]["amortizable_items"]
            all_warnings += result["re_174"]["warnings"]

        # Phase G — §1.263(a)-4/-5 + §195/§248/§709
        if data.transaction_costs or data.intangibles or data.startup_pools:
            result["intangibles_263a45"] = compute_263a4_5(
                data.transaction_costs, data.intangibles, data.startup_pools,
                success_fee_elections=frozenset(success_fee_elections),
                current_tax_year=profile.tax_year)
            basis_items += result["intangibles_263a45"]["amortizable_items"]
            all_warnings += result["intangibles_263a45"]["warnings"]

        # Phase H — §59(e), gated on entity type / individual AMT exposure
        if data.qualified_expenditures:
            result["qualified_59e"] = compute_59e(
                data.qualified_expenditures, entity_type=profile.entity_type,
                individual_amt_exposure=individual_amt_exposure)
            basis_items += result["qualified_59e"]["amortizable_items"]
            all_warnings += result["qualified_59e"]["warnings"]

        # §1060 purchase price allocation (seeds acquired-asset basis)
        if data.purchase_price_allocations:
            result["ppa_1060"] = [compute_1060_allocation(p)
                                  for p in data.purchase_price_allocations]
            for ppa in result["ppa_1060"]:
                all_warnings += ppa["warnings"]

        # prepend blocking errors BEFORE publishing the list — the previous
        # order depended on list aliasing (a refactor to list(all_warnings)
        # would have silently dropped the blocking prefix; red-team finding).
        if data.validation.errors:
            all_warnings[:0] = [f"INGESTION ERROR (blocking): {e}"
                                for e in data.validation.errors]
        result["basis_amortization"] = basis_items
        result["all_warnings"] = all_warnings

        if generate_workbook:
            tag = company_tag or (profile.entity_name if profile else None) or "entity"
            tag = (_UNSAFE_TAG_CHARS.sub("_", tag).strip("_") or "entity")[:100]
            ts = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
            out = os.path.join(self.output_dir, f"{tag}_cap263a_{ts}.xlsx")
            CapitalizationReport().generate(result, out)
            result["_output_path"] = out
        return result
