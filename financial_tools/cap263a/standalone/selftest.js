/* Shared parity harness: runs a goldens.json scenario spec through the JS
 * engines and compares the serialized output against the Python-generated
 * expectation. Used by test_parity.js (Node) and the in-browser self-test.
 *
 * Comparison rules:
 *  - numeric strings/numbers compare as exact decimals (D.cmp === 0);
 *  - "warnings" arrays compare by count + multiset of 30-char prefixes
 *    (codes are identical between ports; long prose tails may differ in
 *    locale-independent formatting);
 *  - "flags" arrays compare as sorted string lists;
 *  - prose fields (notes/authority/description/…) are ignored;
 *  - enum-ish strings (treatment/method/convention/…) compare exactly;
 *  - both sides must have the same keys otherwise.
 */
"use strict";

(function (root, factory) {
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory(require("./engines.js"));
  } else {
    root.CAP263A_SELFTEST = factory(root.CAP263A);
  }
})(typeof self !== "undefined" ? self : this, function (E) {

  const D = E.D;

  function serialize(x) {
    if (x instanceof D) return x.toString();
    if (x === null || x === undefined) return null;
    if (Array.isArray(x)) return x.map(serialize);
    if (typeof x === "object") {
      const o = {};
      for (const [k, v] of Object.entries(x)) o[k] = serialize(v);
      return o;
    }
    return x;
  }

  function augmentAmortizable(result) {
    if (result && Array.isArray(result.amortizable_items)) {
      result = Object.assign({}, result, {
        amortizable_items: result.amortizable_items.map(it =>
          Object.assign({}, it,
            { first_year_amortization: E.firstYearAmortization(it) })),
      });
    }
    return result;
  }

  function runScenario(spec) {
    const inp = spec.input;
    switch (spec.engine) {
      case "unicap": {
        const p = E.makeProfile(inp.profile || {});
        const r = E.analyzeAssigned(inp.rows || [], p);
        return { bucket_totals: r.bucket_totals, is_total: r.is_total,
          capitalized_total: r.capitalized_total, mixed_total: r.mixed_total,
          deductible_total: r.deductible_total, tie_check: r.tie_check,
          bucket_warnings: r.bucket_warnings, unicap: r.unicap };
      }
      case "lifo_decrement":
        return E.computeLifoDecrementRelease(
          (inp.layers || []).map(l => Object.assign({}, l, {
            layer_471: D.from(l.layer_471),
            layer_additional_263a: D.from(l.layer_additional_263a) })),
          inp.decrement);
      case "interest":
        return E.compute263af(inp.projects || [], inp.debts || [], inp.opts || {});
      case "s174":
        return augmentAmortizable(E.compute174(inp.expenditures || [], inp.opts || {}));
      case "intangibles":
        return augmentAmortizable(E.compute263a45(
          inp.transaction_costs || [], inp.intangibles || [],
          inp.startup_pools || [], inp.opts || {}));
      case "demolition":
        return augmentAmortizable(E.routeDemolition(
          inp.demolition_cost, inp.remaining_structure_basis,
          { casualty: !!inp.casualty }));
      case "s59e":
        return augmentAmortizable(E.compute59e(inp.elections || [], inp.opts || {}));
      case "s1060":
        return E.compute1060Allocation(inp);
      case "sca":
        return E.computeSCA(inp.pools || [], inp.assets || [], inp.sscm_ratio,
          { book_capitalized_indirect: inp.book_capitalized_indirect || {} });
      case "taxtb": {
        const out = E.computeTaxBasisTB(inp.tb_lines || [], inp.btds || []);
        return { tax_lines: out.tax_lines.map(l => ({ acct_num: l.acct_num,
            acct_desc: l.acct_desc, cc_num: l.cc_num, amount: l.amount })),
          m1_reconciliation: out.m1_reconciliation,
          cc_rollup: out.cc_rollup, warnings: out.warnings };
      }
      default:
        throw new Error("unknown engine: " + spec.engine);
    }
  }

  const NUMERIC_RE = /^-?\d+(\.\d+)?([eE][+-]?\d+)?$/;
  const IGNORE_KEYS = new Set(["notes", "note", "authority", "description",
    "source", "acct_desc", "cc_desc", "profile", "rows", "row_index",
    "source_sheet", "btd", "target", "applied"]);

  function isNumericStr(v) {
    return (typeof v === "number") ||
      (typeof v === "string" && NUMERIC_RE.test(v.trim()));
  }

  function warnKey(w) { return String(w).slice(0, 30); }

  function compare(exp, act, path, diffs) {
    if (diffs.length > 40) return; // don't flood
    if (exp === null || exp === undefined) {
      if (!(act === null || act === undefined)) {
        diffs.push(path + ": expected null, got " + JSON.stringify(act));
      }
      return;
    }
    if (Array.isArray(exp)) {
      if (!Array.isArray(act)) { diffs.push(path + ": expected array"); return; }
      const isWarnings = /(^|\.)(warnings|bucket_warnings)$/.test(path);
      const isFlags = /(^|\.)flags$/.test(path);
      if (isWarnings) {
        if (exp.length !== act.length) {
          diffs.push(path + ": warning count " + act.length + " ≠ expected " + exp.length +
            "\n  expected: " + exp.map(warnKey).join(" | ") +
            "\n  actual:   " + act.map(warnKey).join(" | "));
          return;
        }
        const e = exp.map(warnKey).sort(), a = act.map(warnKey).sort();
        for (let i = 0; i < e.length; i++) {
          if (e[i] !== a[i]) {
            diffs.push(path + ": warning prefixes differ — expected " +
              JSON.stringify(e[i]) + ", got " + JSON.stringify(a[i]));
            return;
          }
        }
        return;
      }
      if (isFlags) {
        const e = exp.map(String).sort(), a = act.map(String).sort();
        if (JSON.stringify(e) !== JSON.stringify(a)) {
          diffs.push(path + ": flags " + JSON.stringify(a) + " ≠ " + JSON.stringify(e));
        }
        return;
      }
      if (exp.length !== act.length) {
        diffs.push(path + ": length " + act.length + " ≠ expected " + exp.length);
        return;
      }
      for (let i = 0; i < exp.length; i++) compare(exp[i], act[i], path + "[" + i + "]", diffs);
      return;
    }
    if (typeof exp === "object") {
      if (act === null || typeof act !== "object" || Array.isArray(act)) {
        diffs.push(path + ": expected object, got " + JSON.stringify(act));
        return;
      }
      for (const k of Object.keys(exp)) {
        if (IGNORE_KEYS.has(k)) continue;
        if (!(k in act)) { diffs.push(path + "." + k + ": missing in JS output"); continue; }
        compare(exp[k], act[k], path + "." + k, diffs);
      }
      for (const k of Object.keys(act)) {
        if (IGNORE_KEYS.has(k)) continue;
        if (!(k in exp)) diffs.push(path + "." + k + ": extra key in JS output");
      }
      return;
    }
    if (typeof exp === "boolean" || typeof act === "boolean") {
      if (exp !== act) diffs.push(path + ": " + JSON.stringify(act) + " ≠ " + JSON.stringify(exp));
      return;
    }
    if (isNumericStr(exp) && isNumericStr(act)) {
      try {
        if (D.from(String(exp)).cmp(D.from(String(act))) !== 0) {
          diffs.push(path + ": " + act + " ≠ expected " + exp);
        }
      } catch (e) {
        diffs.push(path + ": numeric compare failed (" + exp + " vs " + act + ")");
      }
      return;
    }
    if (String(exp) !== String(act)) {
      diffs.push(path + ": " + JSON.stringify(String(act)) + " ≠ expected " +
        JSON.stringify(String(exp)));
    }
  }

  function runAll(goldens) {
    const results = [];
    for (const spec of goldens) {
      let diffs = [];
      try {
        const actual = serialize(runScenario(spec));
        compare(spec.expected, actual, spec.name, diffs);
      } catch (err) {
        diffs = ["EXCEPTION: " + (err && err.stack || err)];
      }
      results.push({ name: spec.name, engine: spec.engine,
        pass: diffs.length === 0, diffs });
    }
    return results;
  }

  return { serialize, runScenario, compare, runAll };
});
