"""Single taxonomy exporter.

Writes the taxonomy to hidden workbook sheets and reconstructs it from them.
This is the ONE place taxonomy is materialized into Excel (the original tool had
seven inconsistent copies). The Python-in-Excel workbook reads these sheets via
xl() and rebuilds the identical Taxonomy, so the Excel deliverable and the CLI
produce the same classifications by construction.
"""

from .taxonomy import get_taxonomy, Taxonomy

_CAT_COLS = ["code", "tier1", "tier2", "tier3", "mspm", "resale", "self_const",
             "interest", "priority", "keywords", "cc_clues", "is_labor",
             "labor_type", "cap_vs_deduct", "allows_negative_adj",
             "designated_property", "election_required", "authority", "note"]


def _cat_row(c):
    t = c["treatment"]
    return [c["code"], c["tier1"], c.get("tier2", ""), c.get("tier3", ""),
            t["mspm"], t["resale"], t["self_const"], t["interest"],
            c.get("priority", 0), "|".join(c.get("keywords", [])),
            "|".join(c.get("cc_clues", [])), bool(c.get("is_labor")),
            c.get("labor_type", ""), c.get("cap_vs_deduct") or "",
            bool(c.get("allows_negative_adj")), bool(c.get("designated_property")),
            bool(c.get("election_required")), c.get("authority", ""),
            c.get("note", "")]


def _blank(v):
    """A blank cell reads back as None via openpyxl's iter_rows, but as
    float('nan') via the =PY() workbook's pandas `xl(...).values.tolist()`
    path. NaN is truthy AND `nan != nan`, so `str(v or "")` neutralizes None
    but NOT NaN — which reintroduced the ["None"]-class corruption as ['nan']
    (36 phantom keyword/clue entries) on the ONE path that actually runs in
    Excel. Treat both as empty."""
    return v is None or v != v          # v != v is True only for NaN


def _s(v):
    return "" if _blank(v) else str(v)


def _row_to_cat(row):
    d = dict(zip(_CAT_COLS, row))

    def _list(v):
        return [k for k in _s(v).split("|") if k]
    return {
        "code": d["code"], "tier1": d["tier1"],
        "tier2": _s(d["tier2"]), "tier3": _s(d["tier3"]),
        "treatment": {"mspm": d["mspm"], "resale": d["resale"],
                      "self_const": d["self_const"], "interest": d["interest"]},
        "priority": int(d["priority"]) if not _blank(d["priority"]) else 0,
        "keywords": _list(d["keywords"]),
        "cc_clues": _list(d["cc_clues"]),
        "is_labor": bool(d["is_labor"]) and not _blank(d["is_labor"]),
        "labor_type": _s(d["labor_type"]),
        "cap_vs_deduct": _s(d["cap_vs_deduct"]) or None,
        "allows_negative_adj": bool(d["allows_negative_adj"]) and not _blank(d["allows_negative_adj"]),
        "designated_property": bool(d["designated_property"]) and not _blank(d["designated_property"]),
        "election_required": bool(d["election_required"]) and not _blank(d["election_required"]),
        "authority": _s(d["authority"]),
        "note": _s(d.get("note")),
    }


def export_reference_sheets(wb, tax: Taxonomy = None, hidden=True):
    """Write _Categories / _CCZones / _CCReclass / _GenericMap / _Lexicon to wb."""
    tax = tax or get_taxonomy()

    def sheet(name, header, rows):
        ws = wb.create_sheet(name)
        ws.append(header)
        for r in rows:
            ws.append(r)
        if hidden:
            ws.sheet_state = "hidden"
        return ws

    sheet("_Categories", _CAT_COLS, [_cat_row(c) for c in tax.categories])
    sheet("_CCZones", ["keyword", "zone", "zone_tier1"],
          [[z["keyword"], z["zone"], z["zone_tier1"]] for z in tax.cc_zones])
    sheet("_CCReclass", ["zone", "expense_type", "target"],
          [[r["zone"], r["expense_type"], r["target"]] for r in tax.cc_reclass])
    sheet("_GenericMap", ["code", "expense_type"],
          [[k, v] for k, v in tax.generic_map.items()])
    lex_rows = ([["abbrev", k, v] for k, v in tax.abbreviations.items()]
                + [["acct_syn", k, v] for k, v in tax.account_synonyms.items()]
                + [["cc_syn", k, v] for k, v in tax.cc_synonyms.items()])
    sheet("_Lexicon", ["kind", "key", "value"], lex_rows)
    return wb


def reference_data_from_rows(cats, zones, reclass, gmap, lexicon_rows):
    """Rebuild the taxonomy data dict from row lists (what xl() yields)."""
    lex = {"abbreviations": {}, "account_synonyms": {}, "cc_synonyms": {}}
    keymap = {"abbrev": "abbreviations", "acct_syn": "account_synonyms",
              "cc_syn": "cc_synonyms"}
    for kind, k, v in lexicon_rows:
        lex[keymap[kind]][k] = v
    return dict(
        categories=[_row_to_cat(r) for r in cats],
        cc_zones=[dict(keyword=z[0], zone=z[1], zone_tier1=z[2]) for z in zones],
        cc_reclass=[dict(zone=r[0], expense_type=r[1], target=r[2]) for r in reclass],
        generic_map={g[0]: g[1] for g in gmap},
        lexicon=lex,
    )


def taxonomy_from_workbook(wb) -> Taxonomy:
    """Reconstruct a Taxonomy from an exported workbook (skips header rows)."""
    def body(name):
        ws = wb[name]
        return [list(r) for r in ws.iter_rows(min_row=2, values_only=True)]
    data = reference_data_from_rows(body("_Categories"), body("_CCZones"),
                                    body("_CCReclass"), body("_GenericMap"),
                                    body("_Lexicon"))
    return Taxonomy.from_data(**data)
