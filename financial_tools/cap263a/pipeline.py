"""Pipeline: trial balance in → classified + FTA workbook out."""

import os
import re
import warnings as _warnings
from datetime import datetime

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
        tag = _UNSAFE_TAG_CHARS.sub("_", tag).strip("_") or "entity"
        ts = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
        out = os.path.join(self.output_dir, f"{tag}_cap263a_{ts}.xlsx")
        CapitalizationReport().generate(result, out)
        result["_output_path"] = out
        return result
