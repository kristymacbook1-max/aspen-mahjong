"""Pipeline: output-path sanitization for the entity-name tag."""

import os

from openpyxl import Workbook

from financial_tools.cap263a.pipeline import CapitalizationPipeline


def _make_tb(path):
    wb = Workbook(); ws = wb.active; ws.title = "TB"
    ws.append(["Account Number", "Account Description", "Amount"])
    ws.append(["5000", "Direct labor", 300000])
    wb.save(path)


def test_entity_tag_with_slash_does_not_escape_output_dir(tmp_path):
    """An unsanitized entity name like "Acme/Sub LLC" used to create an
    unintended subdirectory via os.path.join; a crafted "../../etc" could
    write outside output_dir entirely."""
    tb = tmp_path / "tb.xlsx"; _make_tb(tb)
    out_dir = tmp_path / "out"
    result = CapitalizationPipeline(str(out_dir)).run(str(tb), company_tag="Acme/Sub LLC")
    out_path = os.path.abspath(result["_output_path"])
    assert os.path.commonpath([os.path.abspath(str(out_dir)), out_path]) == os.path.abspath(str(out_dir))
    assert os.path.dirname(out_path) == os.path.abspath(str(out_dir))  # no nested subdir created


def test_entity_tag_path_traversal_does_not_escape_output_dir(tmp_path):
    tb = tmp_path / "tb.xlsx"; _make_tb(tb)
    out_dir = tmp_path / "out"
    result = CapitalizationPipeline(str(out_dir)).run(str(tb), company_tag="../../etc")
    out_path = os.path.abspath(result["_output_path"])
    assert os.path.commonpath([os.path.abspath(str(out_dir)), out_path]) == os.path.abspath(str(out_dir))
