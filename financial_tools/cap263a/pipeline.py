"""Pipeline: trial balance in → classified + FTA workbook out."""

import os
from datetime import datetime

from .reader import read_trial_balance
from .analysis import analyze, EntityProfile
from .report import CapitalizationReport


class CapitalizationPipeline:
    def __init__(self, output_dir: str = "output/cap263a"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def run(self, tb_path: str, profile: EntityProfile = None,
            company_tag: str = None, timestamp: str = None) -> dict:
        lines = read_trial_balance(tb_path)
        result = analyze(lines, profile)
        tag = company_tag or (profile.entity_name if profile else None) or "entity"
        tag = tag.replace(" ", "_")
        ts = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
        out = os.path.join(self.output_dir, f"{tag}_cap263a_{ts}.xlsx")
        CapitalizationReport().generate(result, out)
        result["_output_path"] = out
        return result
