"""Standalone HTML calculator: the JS engines must stay in lockstep with the
Python engines. Three gates:

1. goldens.json regenerates byte-identically — an engine change without a
   vector refresh (single-source-of-truth drift) fails here;
2. the committed cap263a_calculator.html is the current build of its inputs —
   a stale dist file fails here;
3. node test_parity.js — the JS ports reproduce every golden scenario
   (skipped when node isn't installed; CI environments with node run it).
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
STANDALONE = os.path.join(HERE, "..", "standalone")
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def test_goldens_json_is_current():
    sys.path.insert(0, STANDALONE)
    try:
        import goldens as goldens_mod
    finally:
        sys.path.pop(0)
    regenerated = []
    for sc in goldens_mod.SCENARIOS:
        result = goldens_mod.RUNNERS[sc["engine"]](sc["input"])
        regenerated.append({"name": sc["name"], "engine": sc["engine"],
                            "input": sc["input"],
                            "expected": goldens_mod.serialize(result)})
    with open(os.path.join(STANDALONE, "goldens.json"), encoding="utf-8") as fh:
        committed = json.load(fh)
    assert regenerated == committed, (
        "goldens.json is stale — an engine changed. Regenerate: "
        "python financial_tools/cap263a/standalone/goldens.py && "
        "python financial_tools/cap263a/standalone/build.py")


def test_built_html_is_current(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "cap263a_standalone_build", os.path.join(STANDALONE, "build.py"))
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    out = tmp_path / "built.html"
    orig_out = build.OUT
    build.OUT = str(out)
    try:
        build.main()
    finally:
        build.OUT = orig_out
    committed = open(os.path.join(STANDALONE, "cap263a_calculator.html"),
                     encoding="utf-8").read()
    assert out.read_text(encoding="utf-8") == committed, (
        "cap263a_calculator.html is stale — rebuild: "
        "python financial_tools/cap263a/standalone/build.py")


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_engines_match_python_goldens():
    proc = subprocess.run(
        ["node", os.path.join(STANDALONE, "test_parity.js")],
        capture_output=True, text=True, cwd=REPO_ROOT)
    assert proc.returncode == 0, (
        "JS/Python parity failure:\n" + proc.stdout[-4000:] + proc.stderr[-2000:])
