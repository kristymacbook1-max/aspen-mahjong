"""Runtime Pipeline Step 2 — the materialized tax-basis trial balance.

Applies every BookTaxDifference (signed TAX-minus-BOOK) to its matching book
TB line and returns a second, tax-basis TB structurally identical to the input
(so the same classifier consumes it), plus an M-1-style reconciliation and
cost-center rollups. BTDs that match no TB line become standalone tax-only
lines AND a warning — a silent drop would break book = tax - Σ(BTD).
"""

from decimal import Decimal
from typing import Dict, List, Tuple

from ..model import BookTaxDifference, TBLine


def compute_tax_basis_tb(tb_lines: List[TBLine],
                         btds: List[BookTaxDifference]) -> dict:
    """Returns {tax_lines, m1_reconciliation, cc_rollup, warnings,
    unmatched_btds}. Matching: (acct_num, cc_num) exact first, then acct_num
    alone when the BTD carries no cost center."""
    by_key: Dict[Tuple[str, str], TBLine] = {}
    by_acct: Dict[str, List[TBLine]] = {}
    tax_lines: List[TBLine] = []
    warnings: List[str] = []
    for ln in tb_lines:
        copy = TBLine(acct_num=ln.acct_num, acct_desc=ln.acct_desc,
                      cc_num=ln.cc_num, cc_desc=ln.cc_desc,
                      amount=ln.amount, statement_type=ln.statement_type,
                      row_index=ln.row_index)
        tax_lines.append(copy)
        key = (copy.acct_num, copy.cc_num)
        if key in by_key and copy.acct_num:
            # both lines' dollars survive in tax_lines, but WHICH line a BTD
            # adjusts becomes insertion-order luck — surface it (red-team).
            warnings.append(
                f"DUPLICATE-TB-KEY (acct={copy.acct_num!r}, cc={copy.cc_num!r}): "
                f"multiple TB lines share this key — a BTD matching it applies "
                f"to the LAST line only ({copy.acct_desc!r}). Split the BTD or "
                f"disambiguate the accounts if that's not the intended target.")
        by_key[key] = copy
        by_acct.setdefault(copy.acct_num, []).append(copy)
    unmatched: List[BookTaxDifference] = []
    applied: List[dict] = []

    for btd in btds:
        target = by_key.get((btd.acct_num, btd.cc_num))
        if target is None and btd.acct_num and not btd.cc_num:
            candidates = by_acct.get(btd.acct_num, [])
            if len(candidates) == 1:
                target = candidates[0]
            elif len(candidates) > 1:
                warnings.append(
                    f"BTD {btd.btd_id or btd.description!r} matches account "
                    f"{btd.acct_num!r} in {len(candidates)} cost centers — no "
                    f"cc_num given; applied to none. Split the BTD by cost center.")
                unmatched.append(btd)
                continue
        if target is None:
            # tax-only line: keep the total reconciliation intact
            tax_lines.append(TBLine(
                acct_num=btd.acct_num, acct_desc=f"[BTD] {btd.description}",
                cc_num=btd.cc_num, cc_desc="", amount=btd.adjustment))
            warnings.append(
                f"BTD {btd.btd_id or btd.description!r} matched no TB line "
                f"(acct={btd.acct_num!r}, cc={btd.cc_num!r}) — carried as a "
                f"standalone tax-only line; verify the account mapping.")
            unmatched.append(btd)
            applied.append({"btd": btd, "target": None})
            continue
        target.amount = target.amount + btd.adjustment
        applied.append({"btd": btd, "target": target})

    book_total = sum((l.amount for l in tb_lines), Decimal("0"))
    tax_total = sum((l.amount for l in tax_lines), Decimal("0"))
    btd_total = sum((b.adjustment for b in btds), Decimal("0"))

    cc_rollup: Dict[str, Decimal] = {}
    for ln in tax_lines:
        cc_rollup[ln.cc_num] = cc_rollup.get(ln.cc_num, Decimal("0")) + ln.amount

    m1 = {"book_total": book_total, "btd_total": btd_total,
          "tax_total": tax_total,
          # ties by construction: tax = book + Σ(applied or carried BTDs)
          "tie_check": tax_total - (book_total + btd_total)}
    if m1["tie_check"] != 0:
        warnings.append(f"TAX-BASIS TB TIE-CHECK FAILED: {m1['tie_check']} — "
                        f"a BTD was dropped or double-applied. Do not proceed.")
    return {"tax_lines": tax_lines, "m1_reconciliation": m1,
            "cc_rollup": cc_rollup, "warnings": warnings,
            "unmatched_btds": unmatched, "applied": applied}
