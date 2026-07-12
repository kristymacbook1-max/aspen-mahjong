"""Assemble the standalone HTML calculator.

Inlines engines.js + selftest.js + app.js + goldens.json into template.html
and writes cap263a_calculator.html — one self-contained file that runs on any
computer with a browser (no server, no install, works from file://).

Run from the repo root:
    python financial_tools/cap263a/standalone/goldens.py   # refresh vectors
    python financial_tools/cap263a/standalone/build.py
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "cap263a_calculator.html")


def _read(name):
    with open(os.path.join(HERE, name), "r", encoding="utf-8") as fh:
        return fh.read()


def _js_safe(text):
    # a "</script>" inside inlined content would terminate the script block
    return text.replace("</script>", "<\\/script>").replace("<!--", "<\\!--")


def main():
    html = _read("template.html")
    replacements = {
        "<!--GOLDENS_JSON-->": _js_safe(_read("goldens.json")),
        "<!--ENGINES_JS-->": _js_safe(_read("engines.js")),
        "<!--SELFTEST_JS-->": _js_safe(_read("selftest.js")),
        "<!--APP_JS-->": _js_safe(_read("app.js")),
    }
    for token, content in replacements.items():
        assert token in html, f"template missing {token}"
        html = html.replace(token, content)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"wrote {OUT} ({os.path.getsize(OUT):,} bytes)")


if __name__ == "__main__":
    main()
