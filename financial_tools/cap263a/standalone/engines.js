/* cap263a standalone engines — faithful JavaScript ports of the Python
 * engines in financial_tools/cap263a (analysis.py, engines/*.py).
 *
 * Arithmetic is exact decimal (BigInt coefficient + base-10 exponent),
 * mirroring Python's Decimal: division rounds to 28 significant digits
 * (ROUND_HALF_EVEN, the default context), quantize() supports HALF_EVEN
 * (Python default) and HALF_UP (used by the interest/SCA engines).
 * Parity with the Python engines is pinned by goldens.json (generated from
 * the Python side) via test_parity.js / the in-browser self-test panel.
 *
 * Usable both in the browser (window.CAP263A) and Node (module.exports).
 */
"use strict";

/* ================================ Decimal ================================ */

const DIV_PREC = 28; // Python decimal default context precision

class D {
  constructor(coef, exp) { this.c = coef; this.e = exp; }

  static from(v) {
    if (v instanceof D) return v;
    if (v === null || v === undefined || v === "") return new D(0n, 0);
    if (typeof v === "boolean") throw new Error("expected a dollar amount, got bool " + v);
    if (typeof v === "bigint") return new D(v, 0);
    let s = String(v).trim().replace(/,/g, "");
    const m = s.match(/^([+-]?)(\d*)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/);
    if (!m || (m[2] === "" && (m[3] === undefined || m[3] === "")))
      throw new Error("not a dollar amount: " + JSON.stringify(v));
    const sign = m[1] === "-" ? -1n : 1n;
    const intp = m[2] || "0", frac = m[3] || "";
    const exp = (m[4] ? parseInt(m[4], 10) : 0) - frac.length;
    return new D(sign * BigInt(intp + (frac || "")), exp);
  }

  static zero() { return new D(0n, 0); }

  _align(o) {
    if (this.e === o.e) return [this.c, o.c, this.e];
    if (this.e > o.e) return [this.c * 10n ** BigInt(this.e - o.e), o.c, o.e];
    return [this.c, o.c * 10n ** BigInt(o.e - this.e), this.e];
  }
  plus(o)  { o = D.from(o); const [a, b, e] = this._align(o); return new D(a + b, e); }
  minus(o) { o = D.from(o); const [a, b, e] = this._align(o); return new D(a - b, e); }
  times(o) { o = D.from(o); return new D(this.c * o.c, this.e + o.e); }
  neg()    { return new D(-this.c, this.e); }
  abs()    { return this.c < 0n ? this.neg() : this; }
  isZero() { return this.c === 0n; }
  sign()   { return this.c === 0n ? 0 : (this.c < 0n ? -1 : 1); }
  cmp(o)   { o = D.from(o); const [a, b] = this._align(o); return a === b ? 0 : (a < b ? -1 : 1); }
  lt(o)  { return this.cmp(o) < 0; }
  le(o)  { return this.cmp(o) <= 0; }
  gt(o)  { return this.cmp(o) > 0; }
  ge(o)  { return this.cmp(o) >= 0; }
  eq(o)  { return this.cmp(o) === 0; }

  static max(...xs) { return xs.reduce((a, b) => (D.from(a).ge(b) ? D.from(a) : D.from(b))); }
  static min(...xs) { return xs.reduce((a, b) => (D.from(a).le(b) ? D.from(a) : D.from(b))); }
  static sum(arr, init) { let t = init ? D.from(init) : D.zero(); for (const x of arr) t = t.plus(x); return t; }

  /** digits in |coef| */
  _ndigits() { const s = (this.c < 0n ? -this.c : this.c).toString(); return this.c === 0n ? 1 : s.length; }

  /** divide, rounding to `prec` significant digits HALF_EVEN (Python ctx). */
  div(o, prec) {
    o = D.from(o);
    if (o.c === 0n) throw new Error("division by zero");
    prec = prec || DIV_PREC;
    const negA = this.c < 0n, negB = o.c < 0n;
    let a = negA ? -this.c : this.c, b = negB ? -o.c : o.c;
    if (a === 0n) return new D(0n, 0);
    // scale a so the integer quotient has (prec + guard) digits
    const guard = 5;
    const need = prec + guard + b.toString().length - a.toString().length;
    let shift = need > 0 ? need : 0;
    a = a * 10n ** BigInt(shift);
    let q = a / b;
    const r = a % b;
    // exact remainder marker: bump last guard digit odd-ness via sticky bit
    let exp = this.e - o.e - shift;
    // round q HALF_EVEN to prec significant digits, sticky = (r != 0)
    const qs = q.toString();
    if (qs.length > prec) {
      const drop = qs.length - prec;
      const scale = 10n ** BigInt(drop);
      let head = q / scale;
      const tail = q % scale;
      const half = scale / 2n;
      const sticky = r !== 0n || (tail % 1n !== 0n /*never*/);
      if (tail > half || (tail === half && (sticky || head % 2n === 1n))) head += 1n;
      else if (tail === half && !sticky && head % 2n === 0n) { /* stay */ }
      q = head;
      exp += drop;
    } else if (r !== 0n) {
      // fewer digits than prec but inexact: extend? (can't happen given shift)
    }
    const sign = (negA !== negB) ? -1n : 1n;
    return new D(sign * q, exp);
  }

  /** quantize to 10^qexp (e.g. -2 = cents). mode: "HE" half-even (default), "HU" half-up. */
  q(qexp, mode) {
    mode = mode || "HE";
    if (this.e >= qexp) return new D(this.c * 10n ** BigInt(this.e - qexp), qexp);
    const drop = qexp - this.e;
    const scale = 10n ** BigInt(drop);
    const neg = this.c < 0n;
    const a = neg ? -this.c : this.c;
    let head = a / scale;
    const tail = a % scale;
    const half = scale / 2n;
    if (mode === "HU") {
      if (tail >= half) head += 1n;
    } else { // HALF_EVEN
      if (tail > half || (tail === half && head % 2n === 1n)) head += 1n;
    }
    return new D(neg ? -head : head, qexp);
  }

  isFinite() { return true; }

  toString() {
    const neg = this.c < 0n;
    let digits = (neg ? -this.c : this.c).toString();
    let e = this.e;
    let s;
    if (e >= 0) {
      s = digits + "0".repeat(e);
    } else {
      const point = digits.length + e;
      if (point > 0) s = digits.slice(0, point) + "." + digits.slice(point);
      else s = "0." + "0".repeat(-point) + digits;
    }
    return (neg ? "-" : "") + s;
  }

  toNumber() { return parseFloat(this.toString()); }
}

/** model._dec parity: coerce; reject bool, non-finite, |x| > 1e15. */
function dec(v) {
  if (typeof v === "number" && !Number.isFinite(v))
    throw new Error("non-finite dollar amount rejected: " + v);
  const d = D.from(v);
  if (d.abs().gt(D.from("1e15")))
    throw new Error("implausible dollar magnitude rejected: " + v);
  return d;
}

/* money formatting ≈ Python f"{x:,.2f}" */
function fmt(x, dp) {
  const d = D.from(x).q(-(dp === undefined ? 2 : dp), "HE");
  let s = d.toString();
  let neg = s.startsWith("-");
  if (neg) s = s.slice(1);
  let [i, f] = s.split(".");
  i = i.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return (neg ? "-" : "") + i + (f ? "." + f : (dp ? "." + "0".repeat(dp) : ""));
}
function money(x, dp) { return "$" + fmt(x, dp === undefined ? 2 : dp); }
function money0(x) { return "$" + fmt(x, 0); }
/* Python repr() parity for warning-text stability: 'x', not "x". */
function pyrepr(s) { return "'" + String(s) + "'"; }
function safeRepr(x) {
  // Python-ish repr for objects embedded in warning text (dict -> {'k': v})
  if (x instanceof D) return "Decimal('" + x.toString() + "')";
  if (typeof x === "bigint") return x.toString();
  if (x === null || x === undefined) return "None";
  if (typeof x === "string") return pyrepr(x);
  if (Array.isArray(x)) return "[" + x.map(safeRepr).join(", ") + "]";
  if (typeof x === "object") {
    return "{" + Object.entries(x).map(function (kv) {
      return pyrepr(kv[0]) + ": " + safeRepr(kv[1]);
    }).join(", ") + "}";
  }
  return String(x);
}

const CENT = -2, RATIO4 = -4, RATIO6 = -6;

/* widened-context quantize to cents (analysis._q / inventory._q) */
function q2(x) { return D.from(x).q(CENT, "HE"); }

/* ============================= EntityProfile ============================= */

const THRESHOLDS = { 2018: "25000000", 2019: "26000000", 2020: "26000000",
  2021: "26000000", 2022: "27000000", 2023: "29000000",
  2024: "30000000", 2025: "31000000", 2026: "32000000" };
const LARGE_PRODUCER_THRESHOLD = D.from("50000000");

const PROFILE_DECIMAL_FIELDS = [
  "avg_gross_receipts", "ending_inventory_471",
  "accumulated_production_expenditures", "avoided_cost_rate",
  "pre_production_471", "production_471",
  "pre_production_additional_263A", "production_additional_263A",
  "pre_production_471_on_hand", "production_471_on_hand",
  "beginning_DM_not_yet_in_production", "ending_DM_not_yet_in_production",
  "DM_purchased_during_year",
  "purchasing_costs", "current_year_471_costs",
  "storage_handling_costs", "beginning_inventory_471",
  "ending_inventory_471_total_lifo", "lifo_current_year_increment_471",
];
const PROFILE_RATIO_FIELDS = ["mixed_alloc_ratio", "mspm_labor_split_proportion",
  "har_preprod_ratio", "har_production_ratio", "har_combined_ratio"];

function makeProfile(spec) {
  const p = Object.assign({
    entity_name: "", entity_type: "c_corp", tax_year: 2026,
    avg_gross_receipts: "0", is_tax_shelter: false, has_afs: true,
    industry: "", produces: true, acquires_for_resale: false,
    method: "SPM", ending_inventory_471: "0", mixed_alloc_ratio: null,
    accumulated_production_expenditures: "0", avoided_cost_rate: "0",
    has_designated_property: false,
    inventory_method: "FIFO", is_first_263a_year: false, prior_year_method: "",
    production_activity_level: "", production_incident_to_resale: false,
    private_label_goods: false, sscm_ratio_method: "labor",
    msc_90_10_election: false, include_negative_263a: false,
    pre_production_471: "0", production_471: "0",
    pre_production_additional_263A: "0", production_additional_263A: "0",
    pre_production_471_on_hand: "0", production_471_on_hand: "0",
    beginning_DM_not_yet_in_production: "0", ending_DM_not_yet_in_production: "0",
    DM_purchased_during_year: "0",
    producer_de_minimis_200k: false,
    har_election: false, har_preprod_ratio: null, har_production_ratio: null,
    har_combined_ratio: null, har_qualifying_year_index: 0,
    lifo_current_year_increment_471: "0",
    mspm_mixed_split_method: "direct_material",
    mspm_labor_split_proportion: null, mspm_90pct_split_election: false,
    purchasing_costs: "0", current_year_471_costs: "0",
    storage_handling_costs: "0", beginning_inventory_471: "0",
    srm_variation_a: false, srm_variation_b: false,
    ending_inventory_471_total_lifo: "0",
  }, spec || {});
  for (const f of PROFILE_DECIMAL_FIELDS) {
    if (typeof p[f] === "boolean") throw new Error("EntityProfile." + f + " expects a dollar amount, got bool");
    p[f] = dec(p[f]);
  }
  for (const f of PROFILE_RATIO_FIELDS) {
    if (p[f] !== null && p[f] !== undefined && p[f] !== "") p[f] = D.from(p[f]);
    else p[f] = null;
  }
  return p;
}

function sec448Threshold(p) {
  return D.from(THRESHOLDS[p.tax_year] || "32000000");
}
function thresholdIsEstimate(p) { return !(p.tax_year in THRESHOLDS); }
function sec448PreTcja(p) { return p.tax_year < 2018; }
function smallBusinessExempt(p) {
  if (p.is_tax_shelter) return false;
  return p.avg_gross_receipts.le(sec448Threshold(p));
}
function deMinimisCeiling(p) { return D.from(p.has_afs ? "5000" : "2500"); }

/* ======================= analyze (assigned tiers) ======================== */

const BUCKETS = ["Inventory §471", "§263A Additional", "§263(a) Mandatory",
  "§263(a) Elective", "§263A(f) Interest", "§266 Carrying",
  "Mixed (allocable)", "Deductible", "Non-Operating"];
const CAPITALIZED_BUCKETS = ["Inventory §471", "§263A Additional", "§263(a) Mandatory",
  "§263(a) Elective", "§263A(f) Interest", "§266 Carrying"];
const NON_IS_TIERS = new Set(["Balance Sheet", "Revenue"]);

const TIER1_CHOICES = ["§471 Cost", "Additional §263A", "Capitalizable (MSPM)",
  "§263(a) Tangible", "§263(a) Transaction/Intangible", "§263A(f) Interest",
  "§266 Carrying Charges", "Mixed Service", "Excluded", "Non-Operating",
  "Balance Sheet", "Revenue"];

function bucketOf(cls, profile) {
  const t = cls.tier1;
  const exempt = smallBusinessExempt(profile);
  if (t === "§471 Cost") return exempt ? "Deductible" : "Inventory §471";
  if (t === "Additional §263A" || t === "Capitalizable (MSPM)")
    return exempt ? "Deductible" : "§263A Additional";
  if (t === "§263(a) Tangible") {
    if (cls.cap_vs_deduct === "capitalize") return "§263(a) Mandatory";
    if (cls.cap_vs_deduct === "elective") return "§263(a) Elective";
    return "Deductible";
  }
  if (t === "§263(a) Transaction/Intangible") return "§263(a) Mandatory";
  if (t === "§263A(f) Interest") return exempt ? "Deductible" : "§263A(f) Interest";
  if (t === "§266 Carrying Charges") return "§266 Carrying";
  if (t === "Mixed Service") return exempt ? "Deductible" : "Mixed (allocable)";
  if (t === "Non-Operating") return "Non-Operating";
  return "Deductible";
}

/**
 * analyzeAssigned: the standalone counterpart of analysis.analyze(), taking
 * MANUALLY-ASSIGNED classifications (the keyword classifier is not embedded —
 * the analyst assigns each line's tier, exactly the review step the desktop
 * tool routes low-confidence lines to anyway).
 * lines: [{acct_num, acct_desc, cc_num, cc_desc, amount, tier1,
 *          cap_vs_deduct, is_labor, code}]
 */
function analyzeAssigned(lines, profile) {
  const totals = {};
  for (const b of BUCKETS) totals[b] = D.zero();
  let isTotal = D.zero();
  const rows = [];
  const btdWarnings = [];

  for (const ln of lines) {
    const amount = dec(ln.amount);
    const cls = {
      code: ln.code || "", tier1: ln.tier1 || "Excluded",
      cap_vs_deduct: ln.cap_vs_deduct || null,
      is_labor: !!ln.is_labor, flags: (ln.flags || []).slice(),
    };
    const isIS = !NON_IS_TIERS.has(cls.tier1);
    let bucket = isIS ? bucketOf(cls, profile) : "";
    if ((ln.acct_desc || "").startsWith("[BTD]")) {
      if (isIS && bucket !== "Deductible") {
        btdWarnings.push(
          "UNMATCHED-BTD-HELD-DEDUCTIBLE: " + pyrepr(ln.acct_desc) +
          " (" + money0(amount) + ") would have classified into " +
          pyrepr(bucket) + " on keywords alone — held in Deductible " +
          "pending the account mapping fix; do not leave unmatched BTDs in " +
          "a filing workpaper.");
      }
      bucket = isIS ? "Deductible" : "";
      if (!cls.flags.includes("REVIEW")) cls.flags.push("REVIEW");
    }
    if (isIS) {
      totals[bucket] = totals[bucket].plus(amount);
      isTotal = isTotal.plus(amount);
    }
    rows.push({ line: { ...ln, amount }, cls, bucket, is_income_statement: isIS });
  }

  const capitalized = D.sum(CAPITALIZED_BUCKETS.map(b => totals[b]));
  const mixed = totals["Mixed (allocable)"];
  const deductible = totals["Deductible"].plus(totals["Non-Operating"]);

  const bucketWarnings = btdWarnings.slice();
  for (const b of CAPITALIZED_BUCKETS) {
    if (totals[b].lt(0)) {
      bucketWarnings.push(
        "NEGATIVE '" + b + "' BUCKET (" + money0(totals[b]) + "): capitalization cannot be " +
        "negative — contra/reversal lines classified here need review.");
    }
  }
  if (capitalized.lt(0)) {
    bucketWarnings.push(
      "TOTAL CAPITALIZED IS NEGATIVE (" + money0(capitalized) + ") — the workbook would " +
      "show a negative addition to basis. Review the contributing lines.");
  }

  const result = {
    profile, rows, bucket_totals: totals, is_total: isTotal,
    capitalized_total: capitalized, mixed_total: mixed,
    deductible_total: deductible,
    bucket_warnings: bucketWarnings,
    tie_check: isTotal.minus(capitalized.plus(mixed).plus(deductible)),
  };
  result.unicap = computeUnicap(result, profile);
  return result;
}

/* ================================ SSCM =================================== */

function computeSSCM(result, profile) {
  const rows = result.rows;
  const CAP_TIERS = new Set(["§471 Cost", "Additional §263A"]);
  const DENOM_EXCL = new Set(["Mixed Service", "Non-Operating", "Balance Sheet", "Revenue"]);
  const prodLabor = D.sum(rows.filter(r => r.cls.is_labor && CAP_TIERS.has(r.cls.tier1))
    .map(r => r.line.amount));
  const totalLabor = D.sum(rows.filter(r => r.cls.is_labor && !DENOM_EXCL.has(r.cls.tier1))
    .map(r => r.line.amount));
  let ratioWarn = null;
  let ratioMethodUsed = "labor";
  let ratio;
  if (profile.mixed_alloc_ratio !== null) {
    ratio = profile.mixed_alloc_ratio;
    ratioMethodUsed = "override";
    if (!(ratio.ge(0) && ratio.le(1))) {
      ratioWarn = "SSCM ALLOCATION RATIO OVERRIDE = " + ratio + " is outside [0,1] — a " +
        "service-cost allocation ratio is a fraction; clamped to [0,1] for the " +
        "computation. Check the input.";
    }
  } else if (profile.sscm_ratio_method === "production_cost" && !profile.acquires_for_resale) {
    const b = result.bucket_totals;
    const incomeTax = D.sum(rows.filter(r => r.cls.code === "NO-INCTAX").map(r => r.line.amount));
    const numerator = b["Inventory §471"].plus(b["§263A Additional"]);
    const denominator = result.is_total.minus(result.mixed_total)
      .minus(b["§263A(f) Interest"]).minus(incomeTax);
    if (denominator.gt(0)) {
      ratio = numerator.div(denominator);
      ratioMethodUsed = "production_cost";
      if (!(ratio.ge(0) && ratio.le(1))) {
        ratioWarn = "SSCM PRODUCTION-COST RATIO = " + ratio.q(RATIO4, "HE") +
          " is outside [0,1] — review the §263A pools vs total costs; clamped.";
      }
    } else {
      ratio = D.zero();
      ratioWarn = "SSCM PRODUCTION-COST RATIO: total costs (excl. mixed service, " +
        "interest, income-based taxes) is zero or negative — ratio set to 0; " +
        "labor method may be the better election on these facts.";
    }
  } else {
    if (profile.sscm_ratio_method === "production_cost") {
      ratioWarn = "SSCM-PRODUCTION-COST-RESELLER: the production-cost allocation " +
        "ratio is a producer-only formula (§1.263A-1(h)(3)(ii)) — labor-based " +
        "ratio used instead.";
    }
    ratio = totalLabor.isZero() ? D.zero() : prodLabor.div(totalLabor);
    if (!(ratio.ge(0) && ratio.le(1))) {
      ratioWarn = "SSCM LABOR RATIO = " + ratio.q(RATIO4, "HE") + " is outside [0,1] " +
        "(production labor " + fmt(prodLabor, 0) + " / UNICAP labor " + fmt(totalLabor, 0) +
        ") — likely a negative/contra labor line; clamped to [0,1]. Review.";
    }
  }
  if (ratio.lt(0)) ratio = D.zero();
  else if (ratio.gt(1)) ratio = D.from(1);
  ratio = ratio.q(RATIO6, "HE");
  const mixed = result.mixed_total;
  const mixedCap = q2(mixed.times(ratio));
  const mixedDed = mixed.minus(mixedCap);
  if (profile.msc_90_10_election && !mixed.isZero() && ratioWarn === null) {
    ratioWarn = "MSC-90-10-NOT-IMPLEMENTED: the (g)(4)(ii) all-departments 90% " +
      "election is set, but the department-level carve-out mechanics are not " +
      "built — the SSCM ratio was applied UNIFORMLY across all mixed service " +
      "costs. A department ≥90% capitalizable must be allocated 100% under " +
      "the election (mandatory side); review before filing.";
  }
  return { mixed_alloc_ratio: ratio, production_labor: prodLabor,
    total_labor: totalLabor, mixed_capitalized: mixedCap,
    mixed_deductible: mixedDed, ratio_warning: ratioWarn,
    ratio_method_used: ratioMethodUsed };
}

/* ================================= SPM =================================== */

function computeUnicap(result, profile) {
  if (smallBusinessExempt(profile)) {
    const w = [];
    if (sec448PreTcja(profile)) {
      w.push("PRE-TCJA-YEAR: TY " + profile.tax_year + " begins before 2018 — the " +
        "§263A(i)/§448(c) small-business exemption DID NOT EXIST for that " +
        "year (old law: former §263A(b)(2)(B) $10M reseller exception only; " +
        "producers had no exemption). This exempt determination is NOT " +
        "valid for TY " + profile.tax_year + "; apply pre-TCJA law.");
    }
    if (thresholdIsEstimate(profile)) {
      w.push("§448(c) threshold for TY " + profile.tax_year + " is not on file — the " +
        "2026 figure (" + money0(sec448Threshold(profile)) + ") was used to determine " +
        "the exemption. VERIFY: a higher indexed threshold cannot change this " +
        "result, but relying on it should be documented.");
    }
    return { exempt: true,
      note: "§263A(i)/§448(c) small-business exception — UNICAP off.",
      warnings: w, mixed_capitalized: D.zero(),
      mixed_deductible: result.mixed_total,
      absorption_ratio: D.zero(),
      additional_capitalized_to_inventory: D.zero() };
  }
  if (profile.method === "MSPM") return computeMSPM(result, profile);
  if (profile.method === "SRM") return computeSRM(result, profile);
  return computeSPM(result, profile);
}

function computeSPM(result, profile) {
  if (profile.producer_de_minimis_200k) {
    return { exempt: false, method: "SPM",
      note: "§1.263A-2(b)(3)(iv) $200K producer de minimis — additional §263A costs deemed zero.",
      warnings: [], mixed_alloc_ratio: D.zero(),
      production_labor: D.zero(), total_labor: D.zero(),
      mixed_capitalized: D.zero(), mixed_deductible: result.mixed_total,
      sec471_pool: result.bucket_totals["Inventory §471"],
      additional_263a_pool: D.zero(), absorption_ratio: D.zero(),
      ending_inventory_471: profile.ending_inventory_471,
      additional_capitalized_to_inventory: D.zero(),
      adjusted_deductible_post: result.deductible_total.plus(result.mixed_total) };
  }
  const sscm = computeSSCM(result, profile);
  const ratio = sscm.mixed_alloc_ratio;
  const mixedCap = sscm.mixed_capitalized, mixedDed = sscm.mixed_deductible;
  const ratioWarn = sscm.ratio_warning;

  const sec471Pool = result.bucket_totals["Inventory §471"];
  const additionalPool = result.bucket_totals["§263A Additional"].plus(mixedCap);
  const absorption = sec471Pool.isZero() ? D.zero() : q2(additionalPool.div(sec471Pool));
  const addToInv = q2(profile.ending_inventory_471.times(absorption));

  const warnings = [];
  if (ratioWarn) warnings.push(ratioWarn);
  if (profile.method !== "SPM") {
    warnings.push("METHOD: profile.method=" + pyrepr(profile.method) +
      " is not implemented — this computation is SPM. Do not sign an " +
      profile.method + " workpaper off these numbers (MSPM/SRM are Phase B " +
      "of the build plan).");
  }
  if (absorption.gt(1)) {
    warnings.push("ABSORPTION RATIO = " + absorption + " (>100%): the additional §263A pool (" +
      money0(additionalPool) + ") exceeds the entire §471 base (" + money0(sec471Pool) +
      "). Verify the §471 classifications — this is almost always a data error.");
  }
  if (profile.ending_inventory_471.lt(0)) {
    warnings.push("NEGATIVE ENDING §471 INVENTORY (" + money0(profile.ending_inventory_471) +
      "): a §471-costs-on-hand figure cannot be negative — the capitalized-to-" +
      "inventory amount is meaningless until the input is fixed.");
  }
  if (profile.ending_inventory_471.gt(sec471Pool) && sec471Pool.gt(0)) {
    warnings.push("ENDING §471 INVENTORY (" + money0(profile.ending_inventory_471) +
      ") EXCEEDS THE §471 COST POOL (" + money0(sec471Pool) + "): the amount capitalized " +
      "to inventory scales off an input inconsistent with the trial balance — " +
      "verify the ending-inventory figure.");
  }
  if (additionalPool.lt(0)) {
    warnings.push("NEGATIVE ADDITIONAL §263A POOL: the absorption ratio and the amount " +
      "capitalized to ending inventory are negative. Verify the negative " +
      "adjustments driving this are permissible in the pool.");
    if (profile.method === "SPM" && profile.avg_gross_receipts.gt(LARGE_PRODUCER_THRESHOLD)) {
      warnings.push("Reg §1.263A-1(d)(3)(ii)(B)(1) (verified vs primary source; T.D. number " +
        "unconfirmed): a producer with >$50M average gross receipts may NOT include " +
        "negative adjustments in additional §263A costs under the SPM — use the MSPM.");
    }
  }
  if (sec471Pool.le(0) && !additionalPool.isZero()) {
    warnings.push("§471 POOL IS " + (sec471Pool.isZero() ? "ZERO" : "NEGATIVE") +
      " while the additional §263A pool is nonzero — the absorption ratio is not " +
      "meaningful; check classification of §471 lines.");
  }
  if (sec448PreTcja(profile)) {
    warnings.push("PRE-TCJA-YEAR: TY " + profile.tax_year + " begins before 2018 — §448(c)/" +
      "§263A(i) do not apply to that year; the small-business gate ran on " +
      "post-TCJA law. Apply former §263A(b)(2)(B) instead.");
  }
  if (thresholdIsEstimate(profile)) {
    warnings.push("§448(c) threshold for TY " + profile.tax_year + " is not on file — the 2026 " +
      "figure (" + money0(sec448Threshold(profile)) + ") was used. The threshold is " +
      "inflation-indexed; VERIFY before relying on the small-business exemption " +
      "determination.");
  }

  return { exempt: false, method: "SPM", warnings,
    mixed_alloc_ratio: ratio,
    production_labor: sscm.production_labor, total_labor: sscm.total_labor,
    mixed_capitalized: mixedCap, mixed_deductible: mixedDed,
    sec471_pool: sec471Pool, additional_263a_pool: additionalPool,
    absorption_ratio: absorption,
    ending_inventory_471: profile.ending_inventory_471,
    additional_capitalized_to_inventory: addToInv,
    adjusted_deductible_post: result.deductible_total.plus(mixedDed) };
}

/* ================================= MSPM ================================== */

const NINETY = D.from("0.9");

function ratioSanity(warnings, label, ratio) {
  if (ratio.gt(1)) {
    warnings.push("ABSORPTION RATIO " + label + " = " + ratio + " (>100%): the numerator pool " +
      "exceeds its entire base — almost always a data error; verify the inputs " +
      "before relying on this figure.");
  } else if (ratio.lt(0)) {
    warnings.push("ABSORPTION RATIO " + label + " = " + ratio + " (<0): a negative ratio means " +
      "a negative pool or denominator — review the negative inputs.");
  }
}

function computeMSPM(result, profile) {
  const warnings = [];
  if (profile.producer_de_minimis_200k) {
    if (profile.har_election) {
      warnings.push("HAR-BARRED-200K: the HAR election is not available to a taxpayer " +
        "deemed to have zero additional §263A costs under the $200K de minimis " +
        "(§1.263A-2(c)(4) refinement (4)) — election ignored.");
    }
    return { exempt: false, method: "MSPM",
      note: "§1.263A-2(c)(3)(v) $200K producer de minimis — additional §263A costs deemed zero.",
      warnings, mixed_alloc_ratio: D.zero(),
      production_labor: D.zero(), total_labor: D.zero(),
      mixed_capitalized: D.zero(), mixed_deductible: result.mixed_total,
      pre_production_ratio: D.zero(), production_ratio: D.zero(),
      pre_production_pool: D.zero(), production_pool: D.zero(),
      residual_pre_production_263A: D.zero(),
      direct_materials_adjustment: D.zero(),
      pre_production_471: profile.pre_production_471,
      production_471: profile.production_471,
      pre_production_471_on_hand: profile.pre_production_471_on_hand,
      production_471_on_hand: profile.production_471_on_hand,
      additional_capitalized_to_inventory: D.zero(),
      adjusted_deductible_post: result.deductible_total.plus(result.mixed_total) };
  }

  const sscm = computeSSCM(result, profile);
  if (sscm.ratio_warning) warnings.push(sscm.ratio_warning);
  const mixedCap = sscm.mixed_capitalized;
  const mixedDed = sscm.mixed_deductible;

  const splitDenom = profile.pre_production_471.plus(profile.production_471);
  const dmProp = splitDenom.isZero() ? D.zero()
    : profile.DM_purchased_during_year.div(splitDenom);
  let splitMethodUsed = "direct_material";
  let preProp = dmProp;
  if (profile.mspm_mixed_split_method === "labor") {
    const raw = profile.mspm_labor_split_proportion;
    if (raw === null) {
      if (!mixedCap.isZero()) {
        warnings.push("MSPM-SPLIT-INPUT-MISSING: mspm_mixed_split_method='labor' but no " +
          "mspm_labor_split_proportion (pre-production labor / total labor, both " +
          "excluding mixed-service labor, §1.263A-2(c)(3)(iii)(B)) was supplied — " +
          "fell back to the direct-material proportion. Supply the labor " +
          "proportion or change the split method.");
      }
    } else {
      preProp = raw;
      splitMethodUsed = "labor";
      if (!(preProp.ge(0) && preProp.le(1))) {
        warnings.push("MSPM-SPLIT-PROPORTION-INVALID: mspm_labor_split_proportion=" + preProp +
          " is outside [0,1] — a split proportion is a fraction; clamped. Check the input.");
        preProp = D.min(D.max(preProp, D.zero()), D.from(1));
      }
    }
  }
  if (!mixedCap.isZero() && splitMethodUsed === "direct_material" && splitDenom.isZero()) {
    warnings.push("MSPM-SPLIT-ZERO-DENOMINATOR: total §471 costs incurred " +
      "(pre_production_471 + production_471) is zero — the direct-material split " +
      "proportion defaulted to 0 (all mixed service costs to production). Review.");
  }

  let ninetyApplied = false;
  if (profile.mspm_90pct_split_election) {
    if (preProp.ge(NINETY)) { preProp = D.from(1); ninetyApplied = true; }
    else if (D.from(1).minus(preProp).ge(NINETY)) { preProp = D.zero(); ninetyApplied = true; }
  }
  const mixedPre = mixedCap.times(preProp);
  const mixedProd = mixedCap.minus(mixedPre);

  const prePool = profile.pre_production_additional_263A.plus(mixedPre);
  const prodPool = profile.production_additional_263A.plus(mixedProd);
  for (const [name, pool] of [["pre-production", prePool], ["production", prodPool]]) {
    if (pool.lt(0)) {
      warnings.push("MSPM-NEGATIVE-POOL: the " + name + " additional §263A pool is negative (" +
        money(pool) + "). Negative adjustments are permitted under the MSPM with " +
        "no gross-receipts restriction (§1.263A-1(d)(3)(ii)(B)(2), unlike the SPM), " +
        "but verify none derive from cash/trade discounts or §162(c)/(e)/(f)/(g)-type " +
        "amounts (§1.263A-1(d)(3)(ii)(C)-(E)).");
    }
  }

  let preOnHand = profile.pre_production_471_on_hand;
  let prodOnHand = profile.production_471_on_hand;
  if (preOnHand.lt(0)) {
    warnings.push("MSPM-NEGATIVE-ON-HAND-BALANCE: pre_production_471_on_hand (" +
      money(preOnHand) + ") is negative — input inconsistent with " +
      "§1.263A-2(c)(3)(ii)(C)/(E): on-hand figures must be current-year-incurred " +
      "costs remaining on hand, not raw inventory balances. Floored at 0.");
    preOnHand = D.zero();
  }
  if (prodOnHand.lt(0)) {
    warnings.push("MSPM-NEGATIVE-ON-HAND-BALANCE: production_471_on_hand (" +
      money(prodOnHand) + ") is negative — input inconsistent with " +
      "§1.263A-2(c)(3)(ii)(C)/(E): on-hand figures must be current-year-incurred " +
      "costs remaining on hand, not raw inventory balances. Floored at 0.");
    prodOnHand = D.zero();
  }

  let preRatio;
  if (!profile.pre_production_471.isZero()) {
    preRatio = prePool.div(profile.pre_production_471).q(RATIO4, "HE");
  } else {
    preRatio = D.zero();
    warnings.push("MSPM-ZERO-DENOMINATOR: pre_production_471 is zero — the pre-production " +
      "absorption ratio was set to 0. Verify the §471 direct-material/resale cost inputs.");
  }

  let residual = prePool.minus(preRatio.times(preOnHand));
  if (residual.lt(0)) {
    warnings.push("MSPM-NEGATIVE-RESIDUAL-FLOORED: residual pre-production §263A computed " +
      "negative (" + money(residual) + ") — input inconsistent with " +
      "§1.263A-2(c)(3)(ii)(C)/(E): on-hand figures must be current-year-incurred " +
      "costs remaining on hand, not raw inventory balances (a compliant " +
      "pre_production_471_on_hand cannot exceed pre_production_471). Floored at 0.");
    residual = D.zero();
  }

  const dmAdjustment = profile.beginning_DM_not_yet_in_production
    .plus(profile.DM_purchased_during_year)
    .minus(profile.ending_DM_not_yet_in_production);

  const prodDenom = profile.production_471.plus(dmAdjustment);
  let productionRatio;
  if (prodDenom.lt(0)) {
    productionRatio = D.zero();
    warnings.push("MSPM-NEGATIVE-DENOMINATOR: production_471 + direct_materials_adjustment " +
      "is negative (" + money(prodDenom) + ") — ending DM-not-yet-in-production " +
      "exceeds beginning + purchases, an impossible materials flow. Ratio set to 0; " +
      "fix the DM inputs.");
  } else if (!prodDenom.isZero()) {
    productionRatio = prodPool.plus(residual).div(prodDenom).q(RATIO4, "HE");
  } else {
    productionRatio = D.zero();
    warnings.push("MSPM-ZERO-DENOMINATOR: production_471 + direct_materials_adjustment is " +
      "zero — the production absorption ratio was set to 0. Verify the production " +
      "§471 and direct-material flow inputs.");
  }

  ratioSanity(warnings, "(MSPM pre-production)", preRatio);
  ratioSanity(warnings, "(MSPM production)", productionRatio);
  const actualPre = preRatio, actualProd = productionRatio;

  const isLifo = profile.inventory_method === "lifo_specific"
    || profile.inventory_method === "lifo_dollar_value";
  let harApplied = false;
  if (profile.har_election && !isLifo) {
    if (profile.har_preprod_ratio === null || profile.har_production_ratio === null) {
      warnings.push("HAR-RATIOS-MISSING: har_election set but the frozen " +
        "pre-production/production historic ratios were not supplied — ACTUAL " +
        "ratios used; supply har_preprod_ratio and har_production_ratio.");
    } else if (profile.har_qualifying_year_index === 6) {
      const band = D.from("0.005");
      const passes = profile.har_preprod_ratio.minus(actualPre).abs().le(band)
        && profile.har_production_ratio.minus(actualProd).abs().le(band);
      if (passes) {
        preRatio = profile.har_preprod_ratio.q(RATIO4, "HE");
        productionRatio = profile.har_production_ratio.q(RATIO4, "HE");
        harApplied = true;
        warnings.push("HAR-RECOMPUTATION-PASSED: both historic ratios within ±0.5pp of " +
          "actuals — HAR extends through the recomputation year and the five " +
          "following taxable years (§1.263A-2(c)(4)).");
      } else {
        warnings.push("HAR-RECOMPUTATION-FAILED: a historic ratio fell outside ±0.5pp of " +
          "the actual ratio (conjunctive test) — ACTUAL ratios applied this year; " +
          "HAR must RESUME on the updated test period in the third taxable year " +
          "following the recomputation year (§1.263A-2(c)(4)).");
      }
    } else {
      preRatio = profile.har_preprod_ratio.q(RATIO4, "HE");
      productionRatio = profile.har_production_ratio.q(RATIO4, "HE");
      harApplied = true;
    }
  }

  const nonlifoAdd = q2(preRatio.times(preOnHand).plus(productionRatio.times(prodOnHand)));

  let combinedRatio = null;
  let addToInv;
  if (isLifo) {
    const totalOnHand = preOnHand.plus(prodOnHand);
    if (profile.har_election) {
      if (profile.har_combined_ratio !== null) {
        combinedRatio = profile.har_combined_ratio.q(RATIO4, "HE");
        harApplied = true;
      } else {
        warnings.push("HAR-RATIOS-MISSING: har_election under LIFO needs the COMBINED " +
          "historic absorption ratio ((c)(4)(iii)) — har_combined_ratio not " +
          "supplied; the actual combined ratio was used.");
      }
    }
    if (combinedRatio === null) {
      combinedRatio = totalOnHand.isZero() ? D.zero()
        : nonlifoAdd.div(totalOnHand).q(RATIO4, "HE");
      if (totalOnHand.isZero()) {
        warnings.push("MSPM-LIFO-ZERO-ON-HAND: no §471 costs on hand — the combined " +
          "absorption ratio was set to 0.");
      }
    }
    const increment = profile.lifo_current_year_increment_471;
    if (increment.gt(0)) {
      addToInv = q2(combinedRatio.times(increment));
    } else if (increment.lt(0)) {
      addToInv = nonlifoAdd;
      warnings.push("LIFO-DECREMENT-NOT-IMPLEMENTED: a negative increment is a LIFO " +
        "decrement year — the released-§263A computation (§1.263A-2(b)(3)(iii)(C)) " +
        "needs per-layer data this engine does not carry; the NON-LIFO figure " +
        "below is a placeholder, NOT the LIFO-correct answer.");
    } else {
      addToInv = nonlifoAdd;
      warnings.push("MSPM-LIFO-INCREMENT-MISSING: inventory_method is LIFO but " +
        "lifo_current_year_increment_471 was not supplied — the figure below is " +
        "the NON-LIFO computation, not the combined-ratio × increment answer " +
        "(§1.263A-2(c)(3)(iv)). Supply the increment.");
    }
  } else {
    addToInv = nonlifoAdd;
  }

  return { exempt: false, method: "MSPM", warnings,
    mixed_alloc_ratio: sscm.mixed_alloc_ratio,
    production_labor: sscm.production_labor, total_labor: sscm.total_labor,
    mixed_capitalized: mixedCap, mixed_deductible: mixedDed,
    mixed_split_method: splitMethodUsed,
    mixed_split_proportion_pre: preProp,
    mixed_pre_production_share: q2(mixedPre),
    mixed_production_share: q2(mixedProd),
    mspm_90pct_applied: ninetyApplied,
    pre_production_pool: q2(prePool),
    production_pool: q2(prodPool),
    pre_production_471: profile.pre_production_471,
    pre_production_ratio: preRatio,
    pre_production_471_on_hand: preOnHand,
    residual_pre_production_263A: q2(residual),
    direct_materials_adjustment: q2(dmAdjustment),
    production_471: profile.production_471,
    production_ratio: productionRatio,
    production_471_on_hand: prodOnHand,
    actual_pre_production_ratio: actualPre,
    actual_production_ratio: actualProd,
    har_applied: harApplied,
    lifo_combined_ratio: combinedRatio,
    additional_capitalized_to_inventory: addToInv,
    adjusted_deductible_post: result.deductible_total.plus(mixedDed) };
}

/* ====================== LIFO decrement release =========================== */

function computeLifoDecrementRelease(layers, decrement) {
  decrement = D.from(decrement);
  if (decrement.le(0)) throw new Error("decrement must be positive, got " + decrement);
  const warnings = [];
  let released = D.zero();
  let remaining = decrement;
  const detail = [];
  for (let i = layers.length - 1; i >= 0; i--) {
    if (remaining.le(0)) break;
    const layer = layers[i];
    const layer471 = D.from(layer.layer_471);
    const layerAdd = D.from(layer.layer_additional_263a);
    if (layer471.le(0)) {
      warnings.push("LIFO-LAYER-INVALID: layer " + safeRepr(layer) +
        " has non-positive §471 costs — skipped; fix the layer schedule.");
      continue;
    }
    const liquidated = D.min(remaining, layer471);
    const share = layerAdd.times(liquidated).div(layer471);
    released = released.plus(share);
    remaining = remaining.minus(liquidated);
    detail.push(Object.assign({}, layer,
      { liquidated_471: liquidated, released_263a: q2(share) }));
  }
  if (remaining.gt(0)) {
    warnings.push("LIFO-DECREMENT-EXCEEDS-LAYERS: " + money(remaining) + " of the " +
      "decrement exceeds the supplied layers' total §471 costs — the layer " +
      "schedule is incomplete; released §263A is understated until it is.");
  }
  return { released_263a_to_cogs: q2(released), layers: detail,
    unabsorbed_decrement: q2(remaining), warnings };
}

/* ================================= SRM =================================== */

function computeSRM(result, profile) {
  const warnings = [];
  let methodConflict = false;
  if (profile.produces && profile.private_label_goods) {
    warnings.push("PRIVATE-LABEL-CONDITIONS: SRM availability rests on the (a)(4)(iii) " +
      "private-label carve-out — confirm its three conditions hold (production " +
      "under contract with an UNRELATED person; incident to resale; property " +
      "sold to customers). Neither this engine nor the interview verifies them.");
  }
  if (profile.produces && !profile.private_label_goods) {
    if (profile.production_activity_level === "more_than_de_minimis") {
      methodConflict = true;
      warnings.push("SRM-METHOD-CONFLICT: §1.263A-3(a)(4)(i) bars the simplified resale " +
        "method for a producer above the de minimis threshold (SPM/MSPM required) " +
        "— these SRM figures are NOT a permissible filing position.");
    } else if (profile.production_activity_level === "de_minimis"
        && !profile.production_incident_to_resale) {
      methodConflict = true;
      warnings.push("SRM-METHOD-CONFLICT: §1.263A-3(a)(4)(ii) permits SRM for a de-minimis " +
        "producer only when production is INCIDENT TO RESALE of §1221(1) property — " +
        "production_incident_to_resale is False, so SRM is not available. These " +
        "figures are NOT a permissible filing position.");
    } else if (!profile.production_activity_level) {
      warnings.push("SRM-PRODUCTION-LEVEL-UNKNOWN: the taxpayer produces but " +
        "production_activity_level was never established (Gate 1 Q1.2) — the " +
        "§1.263A-3(a)(4) availability gate CANNOT be evaluated. Resolve the de " +
        "minimis determination before relying on these SRM figures.");
    }
  } else if (!profile.produces && profile.production_activity_level === "more_than_de_minimis") {
    warnings.push("SRM-INPUTS-INCONSISTENT: produces=False but production_activity_level=" +
      "'more_than_de_minimis' — the availability gate cannot be evaluated on " +
      "contradictory inputs. Fix the activity profile.");
  }

  const sscm = computeSSCM(result, profile);
  if (sscm.ratio_warning) warnings.push(sscm.ratio_warning);

  for (const [name, pool] of [["purchasing_costs", profile.purchasing_costs],
                              ["storage_handling_costs", profile.storage_handling_costs]]) {
    if (pool.lt(0)) {
      warnings.push("SRM-NEGATIVE-POOL: " + name + " is negative (" + money(pool) + "). " +
        "Negative adjustments are permitted under the SRM with no gross-receipts " +
        "restriction (§1.263A-1(d)(3)(ii)(B)(3), unlike the SPM), but verify none " +
        "derive from cash/trade discounts or §162(c)/(e)/(f)/(g)-type amounts " +
        "(§1.263A-1(d)(3)(ii)(C)-(E)).");
    }
  }

  let purchasingRatio;
  if (!profile.current_year_471_costs.isZero()) {
    purchasingRatio = profile.purchasing_costs.div(profile.current_year_471_costs).q(RATIO6, "HE");
  } else {
    purchasingRatio = D.zero();
    warnings.push("SRM-ZERO-DENOMINATOR: current_year_471_costs (the current year's " +
      "purchases, §1.263A-3(d)(3)(i)(D)(2)/(E)) is zero — the purchasing ratio " +
      "was set to 0. Verify the purchases input.");
  }

  let shDenom = profile.current_year_471_costs;
  if (!profile.srm_variation_a) shDenom = shDenom.plus(profile.beginning_inventory_471);
  let storageHandlingRatio;
  if (!shDenom.isZero()) {
    storageHandlingRatio = profile.storage_handling_costs.div(shDenom).q(RATIO6, "HE");
  } else {
    storageHandlingRatio = D.zero();
    warnings.push("SRM-ZERO-DENOMINATOR: the storage & handling denominator " +
      "(beginning_inventory_471 + current_year_471_costs" +
      (profile.srm_variation_a
        ? ", beginning inventory excluded per the (d)(3)(iii)(A) variation" : "") +
      ") is zero — the storage & handling ratio was set to 0. Verify the " +
      "inventory and purchases inputs.");
  }

  const combinedRatio = purchasingRatio.plus(storageHandlingRatio);
  ratioSanity(warnings, "(SRM purchasing)", purchasingRatio);
  ratioSanity(warnings, "(SRM storage & handling)", storageHandlingRatio);
  if (profile.ending_inventory_471.lt(0)) {
    warnings.push("SRM-NEGATIVE-ENDING-INVENTORY: ending_inventory_471 is negative (" +
      money(profile.ending_inventory_471) + ") — a §471-costs-on-hand figure " +
      "cannot be negative; the capitalized amount below is meaningless until " +
      "the input is fixed.");
  }
  if (profile.srm_variation_a && profile.srm_variation_b) {
    warnings.push("SRM-VARIATION-A-PLUS-B: both (d)(3)(iii) variations elected — A's " +
      "current-year-only S&H denominator is being applied to B's all-layer total " +
      "multiplicand, an internally inconsistent combination the regulation text " +
      "presents as independent options without addressing. SME must confirm " +
      "before filing.");
  }
  let addToInv;
  if (profile.srm_variation_b) {
    const totalLifo = profile.ending_inventory_471_total_lifo;
    if (totalLifo.le(0)) {
      warnings.push("SRM-VARIATION-B-INPUT-MISSING: srm_variation_b elected but " +
        "ending_inventory_471_total_lifo (TOTAL ending-inventory §471 at LIFO " +
        "carrying value — the S&H ratio's multiplicand under (d)(3)(iii)(B)) was " +
        "not supplied; computed WITHOUT the variation.");
      addToInv = q2(combinedRatio.times(profile.ending_inventory_471));
    } else {
      addToInv = q2(purchasingRatio.times(profile.ending_inventory_471)
        .plus(storageHandlingRatio.times(totalLifo)));
    }
  } else {
    addToInv = q2(combinedRatio.times(profile.ending_inventory_471));
  }

  if (!result.mixed_total.isZero()) {
    warnings.push("SRM-MSC-INPUT-CONTRACT: " + money0(result.mixed_total) + " of mixed-service " +
      "costs are on the classified TB. Under the SRM their capitalizable share " +
      "belongs INSIDE the purchasing/storage-handling pool inputs per the " +
      "§1.263A-3(d)(3)(i)(F) one-step sub-split — confirm the pool figures " +
      "already include it; the full TB mixed total is otherwise reported as " +
      "currently deductible here (informational SSCM ratio: " +
      sscm.mixed_alloc_ratio + ").");
  }

  return { exempt: false, method: "SRM", method_conflict: methodConflict, warnings,
    mixed_alloc_ratio: sscm.mixed_alloc_ratio,
    production_labor: sscm.production_labor, total_labor: sscm.total_labor,
    mixed_capitalized: D.zero(), mixed_deductible: result.mixed_total,
    purchasing_costs: profile.purchasing_costs,
    current_year_471_costs: profile.current_year_471_costs,
    purchasing_ratio: purchasingRatio,
    storage_handling_costs: profile.storage_handling_costs,
    storage_handling_denominator: shDenom,
    storage_handling_ratio: storageHandlingRatio,
    combined_ratio: combinedRatio,
    srm_variation_a: profile.srm_variation_a,
    srm_variation_b: profile.srm_variation_b,
    ending_inventory_471: profile.ending_inventory_471,
    additional_capitalized_to_inventory: addToInv,
    adjusted_deductible_post: result.deductible_total.plus(result.mixed_total) };
}

/* ======================= basis reconciliation ============================ */

function reconcile(bookCapitalized, taxRequired, label) {
  bookCapitalized = D.from(bookCapitalized || 0);
  taxRequired = D.from(taxRequired || 0);
  const warnings = [];
  const delta = taxRequired.minus(bookCapitalized);
  if (delta.lt(0)) {
    warnings.push("BOOK-EXCEEDS-TAX-REQUIRED [" + label + "]: book already capitalizes " +
      money(bookCapitalized) + " but the tax-required amount is only " +
      money(taxRequired) + " — no negative posting made; review the book/tax " +
      "convention difference (" + money(delta.neg()) + ").");
    return [D.zero(), warnings];
  }
  if (bookCapitalized.gt(0) && delta.gt(0)) {
    warnings.push("BASIS-RECONCILED [" + label + "]: " + money(bookCapitalized) +
      " already on the books; posting only the " + money(delta) + " tax delta.");
  }
  return [delta, warnings];
}

/* ========================== §263A(f) interest ============================ */

function q2up(x) { return D.from(x).q(CENT, "HU"); }

function isEligibleDebt(debt) {
  if (debt.disallowed_163_8T || debt.related_party_below_afr) return false;
  if (debt.personal_or_qualified_residence || debt.tax_exempt_org_nonbusiness) return false;
  if (debt.reserve_or_deferred_tax || debt.tax_liability_453a_460b
      || debt.sale_leaseback_purchase_money) return false;
  if (debt.non_interest_bearing && !debt.traced_to) return false;
  return true;
}

function exclusionScreen(debt) {
  if (debt.disallowed_163_8T)
    return "§1.263A-9(a)(4) — interest disallowed under §1.163-8T(m)(7)(ii)";
  if (debt.related_party_below_afr)
    return "§1.263A-9(a)(4)(iii) — related-person debt at a below-AFR rate at issuance";
  if (debt.personal_or_qualified_residence)
    return "§1.263A-9(a)(4) — personal interest (§163(h)(2)) / qualified residence interest (§163(h)(3))";
  if (debt.tax_exempt_org_nonbusiness)
    return "§1.263A-9(a)(4) — tax-exempt organization debt outside an unrelated trade or business";
  if (debt.reserve_or_deferred_tax)
    return "§1.263A-9(a)(4) — reserve/deferred-tax liability not treated as debt for federal income tax purposes";
  if (debt.tax_liability_453a_460b)
    return "§1.263A-9(a)(4) — income tax liability / §453A deferred tax / §460(b) look-back hypothetical liability";
  if (debt.sale_leaseback_purchase_money)
    return "§1.263A-9(a)(4) — sale-leaseback purchase-money obligation";
  if (debt.non_interest_bearing && !debt.traced_to)
    return "§1.263A-9(a)(4) — non-interest-bearing debt (accounts payable etc.) that is not itself traced debt";
  return "§1.263A-9(a)(4) — excluded (unspecified screen)";
}

function normalizeDateKey(k) {
  const s = String(k).trim();
  let m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (m) return isoDate(+m[1], +m[2], +m[3]);
  m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (m) return isoDate(+m[3], +m[1], +m[2]);
  m = s.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})$/);
  if (m) return isoDate(+m[1], +m[2], +m[3]);
  m = s.match(/^(\d{1,2})-(\d{1,2})-(\d{4})$/);
  if (m) return isoDate(+m[3], +m[1], +m[2]);
  return s;
}
function isoDate(y, mo, d) {
  if (mo < 1 || mo > 12 || d < 1 || d > daysInMonth(y, mo)) return null;
  return String(y).padStart(4, "0") + "-" + String(mo).padStart(2, "0") + "-" +
    String(d).padStart(2, "0");
}
function daysInMonth(y, m) {
  return [31, (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0 ? 29 : 28,
    31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1];
}

function normalizeDateKeyOrKeep(k) {
  const n = normalizeDateKey(k);
  return n === null ? String(k).trim() : n;
}

function outstandingAt(debt, isoD, misses) {
  const obd = debt.outstanding_by_date;
  if (!obd || Object.keys(obd).length === 0) return debt.principal;
  if (!(isoD in obd)) {
    if (misses) misses.push((debt.debt_id || debt.description) + "@" + isoD);
    return debt.principal;
  }
  return obd[isoD];
}

/**
 * cipProjects: [{project_id, is_common_feature, book_capitalized_interest,
 *   snapshots: [{measurement_date: "YYYY-MM-DD", cumulative_ape}]}]
 * debts: [{debt_id, description, principal, interest_incurred, traced_to,
 *   outstanding_by_date: {date: amt}, ...screen flags}]
 */
function compute263af(cipProjects, debts, opts) {
  opts = opts || {};
  const belowAfrInterest = D.from(opts.below_afr_interest || 0);
  const guaranteedPayments = D.from(opts.guaranteed_payments || 0);
  const afrHighest = (opts.afr_highest === undefined || opts.afr_highest === null
    || opts.afr_highest === "") ? null : D.from(opts.afr_highest);

  const warnings = [];

  // normalize debt inputs
  debts = debts.map(d => {
    const nd = Object.assign({}, d);
    nd.principal = D.from(d.principal || 0);
    nd.interest_incurred = D.from(d.interest_incurred || 0);
    nd.traced_to = d.traced_to || "";
    const obd = {};
    for (const [k, v] of Object.entries(d.outstanding_by_date || {}))
      obd[normalizeDateKeyOrKeep(k)] = D.from(v);
    nd.outstanding_by_date = obd;
    return nd;
  });
  cipProjects = cipProjects.map(p => {
    const np = Object.assign({}, p);
    np.book_capitalized_interest = D.from(p.book_capitalized_interest || 0);
    np.snapshots = (p.snapshots || []).map(s => ({
      measurement_date: s.measurement_date || null,
      cumulative_ape: D.from(s.cumulative_ape || 0) }));
    return np;
  });

  const eligible = [];
  for (const debt of debts) {
    if (debt.interest_incurred.lt(0)) {
      warnings.push("NEGATIVE-INTEREST-INCURRED [" + (debt.debt_id || debt.description) + "]: " +
        money(debt.interest_incurred) + " floored to 0 — interest incurred cannot " +
        "be negative; route rebates/adjustments through the schedule, not a " +
        "negative figure.");
      debt.interest_incurred = D.zero();
    }
    if (isEligibleDebt(debt)) eligible.push(debt);
    else warnings.push("INELIGIBLE-DEBT [" + (debt.debt_id || debt.description) + "]: " +
      "excluded from tracing and the WAIR pool — " + exclusionScreen(debt) + ".");
  }

  const projectIds = new Set(cipProjects.map(p => p.project_id));
  const tracedByUnit = {};
  const nontraced = [];
  for (const debt of eligible) {
    if (debt.traced_to) {
      if (!projectIds.has(debt.traced_to)) {
        warnings.push("TRACED-TO-UNKNOWN-UNIT [" + (debt.debt_id || debt.description) + "]: " +
          "traced_to=" + pyrepr(debt.traced_to) + " matches no unit given " +
          "to this computation — interest neither traced nor in the WAIR pool; " +
          "review the tracing schedule.");
        continue;
      }
      (tracedByUnit[debt.traced_to] = tracedByUnit[debt.traced_to] || []).push(debt);
    } else nontraced.push(debt);
  }

  const perUnitDates = cipProjects
    .filter(p => p.snapshots.length)
    .map(p => new Set(p.snapshots.filter(s => s.measurement_date !== null)
      .map(s => s.measurement_date)));
  let unionDates = new Set();
  for (const ds of perUnitDates) for (const d of ds) unionDates.add(d);
  let largest = new Set();
  for (const ds of perUnitDates) if (ds.size > largest.size) largest = ds;
  const setLe = (a, b) => { for (const x of a) if (!b.has(x)) return false; return true; };
  const gridsNested = perUnitDates.length > 0 && largest.size === unionDates.size
    && setLe(largest, unionDates) && perUnitDates.every(ds => setLe(ds, largest));
  if (perUnitDates.length && !gridsNested) {
    warnings.push("MIXED-MEASUREMENT-GRID: units carry snapshot dates on different " +
      "conventions (their date sets do not nest) — §1.263A-9(f) uses ONE " +
      "taxpayer-level measurement-date convention. Each unit was averaged over " +
      "ITS OWN dates (no zero-padding); align the CIP snapshot schedules to one " +
      "grid before relying on this computation.");
  }
  const allDates = gridsNested ? Array.from(unionDates).sort() : [];

  const nontracedInterest = D.sum(nontraced.map(d => d.interest_incurred));
  let avgNontracedOutstanding = D.zero();
  const balanceMisses = [];
  if (nontraced.length) {
    if (allDates.length && nontraced.some(d => Object.keys(d.outstanding_by_date).length)) {
      let total = D.zero();
      for (const isoD of allDates)
        for (const debt of nontraced)
          total = total.plus(outstandingAt(debt, isoD, balanceMisses));
      avgNontracedOutstanding = total.div(D.from(allDates.length));
    } else {
      avgNontracedOutstanding = D.sum(nontraced.map(d => d.principal));
    }
  }

  let wair, wairSource;
  if (avgNontracedOutstanding.gt(0)) {
    wair = nontracedInterest.div(avgNontracedOutstanding);
    wairSource = "nontraced";
  } else if (nontracedInterest.gt(0)) {
    wair = D.zero();
    wairSource = "unavailable";
    warnings.push("WAIR-DATA-INCONSISTENT: " + money(nontracedInterest) + " nontraced " +
      "interest incurred but zero nontraced principal outstanding on every " +
      "measurement date — WAIR cannot be computed and the AFR fallback does not " +
      "apply (debt existed). Excess amounts computed as ZERO; fix the debt " +
      "schedule's dated balances.");
  } else if (afrHighest !== null) {
    wair = afrHighest;
    wairSource = "afr_fallback";
    warnings.push("WAIR-AFR-FALLBACK: no eligible nontraced debt outstanding during the " +
      "computation period — WAIR set to the highest applicable Federal rate per " +
      "§1.263A-9(c)(5)(iii)(D).");
  } else {
    wair = D.zero();
    wairSource = "unavailable";
    warnings.push("WAIR-UNAVAILABLE: no eligible nontraced debt outstanding AND no " +
      "highest AFR supplied — §1.263A-9(c)(5)(iii)(D) fallback cannot run; excess " +
      "expenditure amounts computed as ZERO. Supply afr_highest before relying " +
      "on this computation.");
  }

  const perUnit = {};
  const rawExcess = {};
  for (const project of cipProjects) {
    const pid = project.project_id;
    if (project.is_common_feature) {
      warnings.push("COMMON-FEATURE-OUT-OF-SCOPE [" + pid + "]: §1.263A-10(b) " +
        "common-feature/unit-of-property mechanics are not implemented — treated " +
        "as a standalone designated-property unit.");
    }
    const unitDebts = tracedByUnit[pid] || [];
    const tracedInterest = D.sum(unitDebts.map(d => d.interest_incurred));

    const snaps = project.snapshots.filter(s => s.measurement_date !== null)
      .slice().sort((a, b) => a.measurement_date < b.measurement_date ? -1
        : (a.measurement_date > b.measurement_date ? 1 : 0));
    const ape = {}, tracedByDate = {}, excessByDate = {};
    for (const s of snaps) {
      const iso = s.measurement_date;
      if (iso in ape) {
        warnings.push("DUPLICATE-MEASUREMENT-DATE [" + pid + "] " + iso + ": two APE " +
          "snapshots on the same date — the later row overwrote the earlier (" +
          money(ape[iso]) + "). Fix the CIP schedule.");
      }
      if (s.cumulative_ape.lt(0)) {
        warnings.push("NEGATIVE-APE [" + pid + "] " + iso + ": cumulative APE " +
          money(s.cumulative_ape) + " — accumulated production expenditures " +
          "cannot be negative; the per-date excess floors at 0, but fix the CIP " +
          "schedule.");
      }
      ape[iso] = s.cumulative_ape;
      const tracedD = D.sum(unitDebts.map(d => outstandingAt(d, iso, balanceMisses)));
      tracedByDate[iso] = tracedD;
      excessByDate[iso] = D.max(D.zero(), s.cumulative_ape.minus(tracedD));
    }

    let averageExcess;
    const excessCount = Object.keys(excessByDate).length;
    if (excessCount) {
      const denominator = allDates.length ? D.from(allDates.length) : D.from(excessCount);
      averageExcess = D.sum(Object.values(excessByDate)).div(denominator);
      if (allDates.length && excessCount < allDates.length) {
        warnings.push("PARTIAL-PERIOD-UNIT [" + pid + "]: " + excessCount + " APE snapshots " +
          "over a " + allDates.length + "-date computation period — missing dates " +
          "treated as zero excess per the §1.263A-9(f)(2)(iii) snapshot convention. " +
          "Confirm the unit's production period actually excludes those dates (a " +
          "missing data row would UNDERSTATE capitalization).");
      }
    } else {
      averageExcess = D.zero();
      warnings.push("NO-MEASUREMENT-DATES [" + pid + "]: unit has no dated APE snapshots — " +
        "average excess expenditures computed as ZERO; only traced interest " +
        "capitalized. Supply the CIP snapshot schedule.");
    }

    rawExcess[pid] = averageExcess.times(wair);
    perUnit[pid] = {
      measurement_dates: Object.keys(ape).sort(),
      ape_snapshots: ape,
      traced_debt_by_date: tracedByDate,
      excess_by_date: excessByDate,
      average_excess: averageExcess,
      traced_interest: q2up(tracedInterest),
    };
  }

  if (balanceMisses.length) {
    const shown = balanceMisses.slice(0, 6).join(", ");
    const more = balanceMisses.length > 6 ? " (+" + (balanceMisses.length - 6) + " more)" : "";
    warnings.push("DATED-BALANCE-MISSING: debts with dated balance schedules lack a " +
      "balance on these measurement dates — principal was substituted, which can " +
      "distort WAIR and traced-debt snapshots: " + shown + more +
      ". Complete the debt balance schedule.");
  }

  const totalAvailable = nontracedInterest.plus(belowAfrInterest).plus(guaranteedPayments);
  let sumRaw = D.sum(Object.values(rawExcess));
  let prorated = false;
  if (sumRaw.gt(totalAvailable)) {
    const factor = totalAvailable.div(sumRaw);
    for (const pid of Object.keys(rawExcess)) rawExcess[pid] = rawExcess[pid].times(factor);
    prorated = true;
    warnings.push("PRORATED: aggregate excess expenditure amounts (" +
      "$" + fmt(q2up(sumRaw)) + ") exceed total interest available for capitalization (" +
      "$" + fmt(q2up(totalAvailable)) + ") — each unit's excess amount scaled pro rata " +
      "per §1.263A-9(c)(7); traced interest is never prorated.");
  }

  const quantized = {};
  for (const pid of Object.keys(rawExcess)) quantized[pid] = q2up(rawExcess[pid]);
  const qKeys = Object.keys(quantized);
  if (prorated && qKeys.length) {
    const drift = D.sum(Object.values(quantized)).minus(q2up(totalAvailable));
    if (!drift.isZero()) {
      let largestPid = qKeys[0];
      for (const pid of qKeys)
        if (quantized[pid].gt(quantized[largestPid])) largestPid = pid;
      quantized[largestPid] = quantized[largestPid].minus(drift);
    }
  }

  let totalTraced = D.zero(), totalExcess = D.zero();
  const projectsById = {};
  for (const p of cipProjects) projectsById[p.project_id] = p;
  for (const pid of Object.keys(perUnit)) {
    const unit = perUnit[pid];
    const excessAmount = quantized[pid];
    unit.excess_expenditure_amount = excessAmount;
    unit.total_capitalized = unit.traced_interest.plus(excessAmount);
    totalTraced = totalTraced.plus(unit.traced_interest);
    totalExcess = totalExcess.plus(excessAmount);
    const book = projectsById[pid].book_capitalized_interest;
    unit.book_capitalized_interest = book;
    const [delta, recWarnings] = reconcile(book, unit.total_capitalized,
      "§263A(f) interest — " + pid);
    unit.tax_delta_to_post = delta;
    warnings.push(...recWarnings);
  }

  let remaining = totalExcess;
  const consumedNontraced = D.min(nontracedInterest, remaining);
  remaining = remaining.minus(consumedNontraced);
  const consumedBelowAfr = D.min(belowAfrInterest, remaining);
  remaining = remaining.minus(consumedBelowAfr);
  const consumedGuaranteed = D.min(guaranteedPayments, remaining);
  remaining = remaining.minus(consumedGuaranteed);
  const consumption = {
    nontraced_consumed: q2up(consumedNontraced),
    below_afr_consumed: q2up(consumedBelowAfr),
    guaranteed_payments_consumed: q2up(consumedGuaranteed),
    nontraced_remaining_deductible: q2up(nontracedInterest.minus(consumedNontraced)),
    below_afr_remaining_deductible: q2up(belowAfrInterest.minus(consumedBelowAfr)),
    guaranteed_payments_remaining_deductible: q2up(guaranteedPayments.minus(consumedGuaranteed)),
    unsourced_excess: q2up(remaining),
  };

  return { per_unit: perUnit, wair, wair_source: wairSource,
    total_traced: totalTraced, total_excess: totalExcess,
    total_capitalized: totalTraced.plus(totalExcess),
    prorated, consumption, warnings };
}

/* ============================ §174 / §174A =============================== */

const FOREIGN_RECOVERY_MONTHS = 180;
const MIN_ELECTED_MONTHS = 60;
const NOTE_174A = "§174A(c) amortization runs ratably from the month the taxpayer first " +
  "realizes benefits; that month is not in the input schedule (DATA GAP) — " +
  "mid-year convention applied as a documented proxy.";

function firstYearAmortization(item) {
  if (!item.recovery_months || D.from(item.basis).isZero()) return D.zero();
  let annual = D.from(item.basis).times(12).div(D.from(item.recovery_months));
  if (item.convention === "mid-year") annual = annual.div(D.from(2));
  return annual.q(CENT, "HE");
}

function compute174(reExpenditures, opts) {
  opts = opts || {};
  const currentTaxYear = opts.current_tax_year || 2026;
  const domesticElection = !!opts.domestic_capitalization_election;
  let electedPeriodMonths = opts.elected_period_months || 60;
  let catchupMethod = opts.catchup_method || null;
  const remainingBasis = D.from(opts.remaining_2022_2024_basis || 0);
  const smallBusinessRetroactive = !!opts.small_business_retroactive;
  const disposalIds = new Set(opts.disposal_events || []);

  const warnings = [];
  const items = [];
  const amortizable = [];
  let currentYearDeduction = D.zero();
  let capitalizedTotal = D.zero();

  if (domesticElection) {
    if (electedPeriodMonths < MIN_ELECTED_MONTHS) {
      warnings.push("ELECTED-PERIOD-BELOW-60: §174A(c) requires a period of not less than " +
        "60 months; " + electedPeriodMonths + " requested — floored to 60.");
      electedPeriodMonths = MIN_ELECTED_MONTHS;
    }
    warnings.push("§174A(c) domestic-capitalization election is a METHOD OF ACCOUNTING — " +
      "consistency/3115 discipline applies.");
  }

  const seenIds = new Set();
  for (const exp of reExpenditures) {
    const amount = D.from(exp.amount || 0);
    const bookCap = D.from(exp.book_capitalized_amount || 0);
    seenIds.add(exp.re_id);
    const disposed = disposalIds.has(exp.re_id);
    const row = { re_id: exp.re_id, description: exp.description, amount,
      domestic: !!exp.domestic, treatment: "",
      tax_required_capitalized: D.zero(), posted_basis: D.zero(),
      current_year_deduction: D.zero(), flags: [] };

    if (!exp.domestic) {
      row.treatment = "foreign_mandatory_capitalize";
      row.tax_required_capitalized = amount;
      const [delta, rw] = reconcile(bookCap, amount,
        "§174 foreign R&E " + (exp.re_id || exp.description));
      warnings.push(...rw);
      row.posted_basis = delta;
      const item = { item_id: exp.re_id, description: exp.description,
        category: "re_pool", basis: delta,
        recovery_months: FOREIGN_RECOVERY_MONTHS, convention: "mid-year",
        start_year: exp.tax_year || currentTaxYear, source: "Phase F compute_174",
        authority: "§174(a)(2): foreign research, 15-year straight-line, " +
          "midpoint (mid-year) convention", flags: [], notes: "" };
      if (disposed) {
        row.flags.push("DISPOSAL-NO-LOSS-174D");
        item.flags.push("DISPOSAL-NO-LOSS-174D");
        warnings.push("§174(d) [" + exp.re_id + "]: disposal/retirement/abandonment of " +
          "property with capitalized foreign R&E basis — NO loss deduction; " +
          "amortization continues as if the disposition never occurred.");
      }
      amortizable.push(item);
      capitalizedTotal = capitalizedTotal.plus(delta);
    } else if (domesticElection) {
      row.treatment = "domestic_elected_capitalize";
      row.tax_required_capitalized = amount;
      const [delta, rw] = reconcile(bookCap, amount,
        "§174A(c) elected domestic R&E " + (exp.re_id || exp.description));
      warnings.push(...rw);
      row.posted_basis = delta;
      const item = { item_id: exp.re_id, description: exp.description,
        category: "re_pool", basis: delta,
        recovery_months: electedPeriodMonths, convention: "mid-year",
        start_year: exp.tax_year || currentTaxYear, source: "Phase F compute_174",
        authority: "§174A(c): elective domestic capitalization, " +
          electedPeriodMonths + "-month straight-line",
        flags: [], notes: NOTE_174A };
      if (disposed) {
        row.flags.push("DISPOSAL-NO-LOSS-174D", "§174D-DOMESTIC-ELECTIVE-UNVERIFIED");
        item.flags.push("DISPOSAL-NO-LOSS-174D", "§174D-DOMESTIC-ELECTIVE-UNVERIFIED");
        warnings.push("§174(d) [" + exp.re_id + "]: disposal touching ELECTED-capitalization " +
          "domestic R&E basis — no loss taken and amortization continued " +
          "(conservative reading); whether post-OBBBA §174(d) reaches " +
          "§174A(c)-elected domestic basis is UNVERIFIED — " +
          "§174D-DOMESTIC-ELECTIVE-UNVERIFIED, SME review.");
      }
      amortizable.push(item);
      capitalizedTotal = capitalizedTotal.plus(delta);
    } else {
      row.treatment = "domestic_default_expense";
      row.current_year_deduction = amount;
      currentYearDeduction = currentYearDeduction.plus(amount);
      if (bookCap.gt(0)) {
        warnings.push("BOOK-TAX-DIVERGENCE [" + exp.re_id + "]: books capitalize " +
          money(bookCap) + " of domestic R&E the §174A(a) default currently " +
          "expenses — book/tax difference, review (no tax capitalization posted).");
      }
      if (disposed) row.flags.push("DISPOSAL-MOOT-EXPENSED");
    }
    items.push(row);
  }

  for (const unknown of Array.from(disposalIds).filter(x => !seenIds.has(x)).sort()) {
    warnings.push("DISPOSAL-UNKNOWN-RE-ID: " + pyrepr(unknown) +
      " matches no R&E expenditure in the schedule.");
  }

  const catchup = { method: catchupMethod,
    current_year_deduction: D.zero(), following_year_deduction: D.zero() };
  if (smallBusinessRetroactive && catchupMethod) {
    warnings.push("CATCHUP-RETROACTIVE-MUTUALLY-EXCLUSIVE: the §448(c) small-business " +
      "retroactive election and a catch-up method were BOTH selected — mutually " +
      "exclusive. NO catch-up deduction was booked; resolve which election " +
      "applies before relying on this output.");
    catchup.conflicted_amount_not_deducted = remainingBasis;
    catchupMethod = null;
  }
  if (smallBusinessRetroactive) {
    warnings.push("SMALL-BUSINESS-RETROACTIVE-DEADLINE: the Rev. Proc. 2025-28 retroactive " +
      "election requires AMENDED 2022-2024 returns by July 6, 2026 — a lapsing " +
      "hard deadline; the amended-return computation itself is out of scope for " +
      "this engine.");
  }
  if (catchupMethod === "one_year") {
    catchup.current_year_deduction = remainingBasis;
    currentYearDeduction = currentYearDeduction.plus(remainingBasis);
  } else if (catchupMethod === "two_year") {
    const half = remainingBasis.div(D.from(2)).q(CENT, "HE");
    catchup.current_year_deduction = half;
    catchup.following_year_deduction = remainingBasis.minus(half);
    currentYearDeduction = currentYearDeduction.plus(half);
    warnings.push("CATCHUP-SPLIT-UNVERIFIED: two-year catch-up assumed 50/50 across the " +
      "two years — the exact ratable split needs a Rev. Proc. 2025-28 primary " +
      "read before filing use.");
  } else if (catchupMethod !== null && catchupMethod !== "one_year" && catchupMethod !== "two_year") {
    warnings.push("CATCHUP-METHOD-UNKNOWN: " + pyrepr(catchupMethod) +
      " — no catch-up computed (expected one_year/two_year).");
  }

  return { items, amortizable_items: amortizable,
    current_year_deduction: currentYearDeduction,
    capitalized_total: capitalizedTotal, catchup, warnings };
}

/* =================== §1.263(a)-4/-5 + start-up + §280B =================== */

const FACILITATIVE_DE_MINIMIS = D.from("5000");
const STARTUP_FIRST_YEAR_CAP = D.from("5000");
const STARTUP_PHASEOUT_START = D.from("50000");
const STARTUP_RECOVERY_MONTHS = 180;
const SEC197_RECOVERY_MONTHS = 180;

function parseDate(s) {
  if (!s) return null;
  const m = String(s).match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (!m) return null;
  return { y: +m[1], m: +m[2], d: +m[3] };
}
function dateCmp(a, b) {
  if (a.y !== b.y) return a.y - b.y;
  if (a.m !== b.m) return a.m - b.m;
  return a.d - b.d;
}
function addMonths(d, months) {
  const t = d.y * 12 + (d.m - 1) + months;
  const y = Math.floor(t / 12), m = (t % 12 + 12) % 12 + 1;
  return { y, m, d: Math.min(d.d, daysInMonth(y, m)) };
}
function monthsBetween(start, end) {
  let months = (end.y - start.y) * 12 + (end.m - start.m);
  if (end.d > start.d) months += 1;
  return months;
}

function twelveMonthRulePasses(it) {
  if (!it.benefit_start || !it.benefit_end || !it.payment_year) return null;
  const prongA = addMonths(it.benefit_start, 12);
  const prongB = { y: it.payment_year + 1, m: 12, d: 31 };
  const earlier = dateCmp(prongA, prongB) <= 0 ? prongA : prongB;
  return dateCmp(it.benefit_end, earlier) <= 0;
}

function compute263a45(transactionCosts, intangibles, startupPools, opts) {
  opts = opts || {};
  const successFeeElections = new Set(opts.success_fee_elections || []);
  const currentTaxYear = opts.current_tax_year || 2026;
  const warnings = [];
  const amortizable = [];
  let capitalizedTotal = D.zero();
  let deductibleTotal = D.zero();

  const transactionItems = [];
  for (const tcRaw of transactionCosts) {
    const tc = Object.assign({}, tcRaw);
    tc.amount = D.from(tc.amount || 0);
    tc.incurred_date = parseDate(tc.incurred_date);
    tc.bright_line_date = parseDate(tc.bright_line_date);
    const row = { item_id: tc.item_id, transaction_id: tc.transaction_id,
      description: tc.description, amount: tc.amount, treatment: "",
      deductible: D.zero(), capitalized: D.zero(), flags: [] };
    if (tc.amount.lt(0)) {
      row.treatment = "sme_review";
      row.flags.push("NEGATIVE-AMOUNT");
      warnings.push("NEGATIVE-AMOUNT [txn cost " + (tc.item_id || tc.description) + "]: " +
        money(tc.amount) + " — nothing computed; route credits/refunds through " +
        "the schedule, not a negative fee.");
      transactionItems.push(row);
      continue;
    }
    let cap = D.zero(), ded = D.zero();
    if (tc.success_based && tc.covered_transaction
        && successFeeElections.has(tc.transaction_id)) {
      ded = tc.amount.times(D.from("0.70")).q(CENT, "HE");
      cap = tc.amount.minus(ded);
      row.treatment = "success_fee_70_30";
      row.flags.push("REV-PROC-2011-29-IRREVOCABLE");
    } else if (tc.inherently_facilitative) {
      cap = tc.amount;
      row.treatment = "inherently_facilitative_capitalize";
    } else if (tc.covered_transaction && tc.bright_line_date && tc.incurred_date
        && dateCmp(tc.incurred_date, tc.bright_line_date) < 0) {
      ded = tc.amount;
      row.treatment = "investigatory_pre_bright_line_deduct";
    } else if (tc.covered_transaction) {
      cap = tc.amount;
      row.treatment = "facilitative_capitalize";
      if (!(tc.bright_line_date && tc.incurred_date)) {
        row.flags.push("BRIGHT-LINE-DATES-MISSING");
        warnings.push("BRIGHT-LINE-DATES-MISSING [" + tc.item_id + "]: covered-transaction " +
          "cost lacks incurred/bright-line dates — capitalized conservatively; " +
          "supply dates to test the investigatory carve-out.");
      }
    } else {
      ded = tc.amount;
      row.treatment = "deductible_162";
    }

    if (tc.transaction_abandoned && cap.gt(0)) {
      row.flags.push("ABANDONED-TRANSACTION-LOSS-73-580");
      warnings.push("ABANDONED-TRANSACTION [" + tc.item_id + "]: transaction " +
        pyrepr(tc.transaction_id) + " abandoned — " + money(cap) +
        " of capitalized transaction costs becomes a deductible loss " +
        "(Rev. Rul. 73-580).");
      ded = ded.plus(cap);
      cap = D.zero();
      row.treatment += "+abandoned_loss";
    }

    if (cap.gt(0)) {
      amortizable.push({ item_id: tc.item_id, description: tc.description,
        category: "intangible", basis: cap, recovery_months: null,
        convention: "none", start_year: currentTaxYear,
        source: "Phase G compute_263a4_5",
        authority: "§1.263(a)-5 facilitative transaction cost",
        flags: [], notes: "Attach to the facilitated asset's basis (seed for " +
          "downstream routing — asset basis / §197 / §1.446-5)." });
    }
    row.deductible = ded; row.capitalized = cap;
    deductibleTotal = deductibleTotal.plus(ded);
    capitalizedTotal = capitalizedTotal.plus(cap);
    transactionItems.push(row);
  }

  const intangibleItems = [];
  for (const itRaw of intangibles) {
    const it = Object.assign({}, itRaw);
    it.amount = D.from(it.amount || 0);
    it.facilitative_costs = D.from(it.facilitative_costs || 0);
    it.facilitative_commissions = D.from(it.facilitative_commissions || 0);
    it.prior_capitalized_basis = D.from(it.prior_capitalized_basis || 0);
    it.benefit_start = parseDate(it.benefit_start);
    it.benefit_end = parseDate(it.benefit_end);
    it.payment_year = it.payment_year || 0;
    const row = { item_id: it.item_id, description: it.description,
      amount: it.amount, facilitative_costs: it.facilitative_costs,
      treatment: "", deductible: D.zero(), capitalized: D.zero(),
      posted_basis: D.zero(), flags: [] };
    if (it.benefit_start && it.benefit_end && dateCmp(it.benefit_end, it.benefit_start) < 0) {
      row.flags.push("BENEFIT-DATES-REVERSED");
      row.treatment = "sme_review";
      warnings.push("BENEFIT-DATES-REVERSED [" + it.item_id + "]: benefit_end precedes " +
        "benefit_start — no treatment computed; fix the schedule dates.");
      intangibleItems.push(row);
      continue;
    }
    if (it.payment_year && !(it.payment_year >= 1900 && it.payment_year <= 9998)) {
      row.flags.push("PAYMENT-YEAR-INVALID");
      row.treatment = "sme_review";
      warnings.push("PAYMENT-YEAR-INVALID [" + it.item_id + "]: payment_year=" +
        it.payment_year + " is not a plausible tax year — no treatment computed.");
      intangibleItems.push(row);
      continue;
    }
    const passes12mo = twelveMonthRulePasses(it);
    if (passes12mo) {
      row.treatment = "twelve_month_rule_deduct";
      row.deductible = it.amount.plus(it.facilitative_costs);
      deductibleTotal = deductibleTotal.plus(row.deductible);
      if (it.facilitative_commissions.gt(0)) {
        row.flags.push("E4-COMMISSIONS-ALWAYS-CAPITALIZED");
        row.capitalized = it.facilitative_commissions;
        const [delta, rw] = reconcile(D.zero(), it.facilitative_commissions,
          "12-month-rule item commissions " + (it.item_id || it.description));
        warnings.push(...rw);
        amortizable.push({ item_id: it.item_id,
          description: it.description + " (commissions)",
          category: "intangible", basis: delta, recovery_months: null,
          convention: "none", start_year: currentTaxYear,
          source: "Phase G compute_263a4_5",
          authority: "§1.263(a)-4(e)(4): commissions always facilitative",
          flags: ["E4-COMMISSIONS-ALWAYS-CAPITALIZED", "INDEFINITE-LIFE-SME-REVIEW"],
          notes: "" });
        row.posted_basis = delta;
        capitalizedTotal = capitalizedTotal.plus(delta);
      }
      intangibleItems.push(row);
      continue;
    }
    if (passes12mo === null && (it.benefit_start || it.benefit_end)) {
      row.flags.push("TWELVE-MONTH-DATES-INCOMPLETE");
    }

    let cap = it.amount.plus(it.facilitative_commissions);
    if (it.facilitative_commissions.gt(0)) row.flags.push("E4-COMMISSIONS-ALWAYS-CAPITALIZED");
    let ded = D.zero();
    if (it.facilitative_costs.gt(0)) {
      if (it.facilitative_costs.le(FACILITATIVE_DE_MINIMIS)) {
        ded = ded.plus(it.facilitative_costs);
        row.flags.push("E4-DE-MINIMIS-DEDUCTED");
      } else {
        cap = cap.plus(it.facilitative_costs);
        row.flags.push("E4-CLIFF-ALL-CAPITALIZED");
      }
    }
    row.treatment = "capitalize_263a4";

    let recovery, convention, authority;
    if (it.acquired_with_business) {
      recovery = SEC197_RECOVERY_MONTHS;
      convention = "full-month";
      authority = "§197(a): acquired-with-business intangible, 15-year";
    } else if (it.benefit_start && it.benefit_end) {
      recovery = monthsBetween(it.benefit_start, it.benefit_end);
      if (recovery < 1) {
        recovery = 1;
        row.flags.push("RECOVERY-FLOORED-ONE-MONTH");
      }
      convention = "full-month";
      authority = "§1.263(a)-4: amortized over the benefit term (" + recovery +
        " months, benefit_end − benefit_start)";
    } else {
      recovery = null;
      convention = "none";
      authority = "§1.263(a)-4: no ascertainable life in schedule";
      row.flags.push("INDEFINITE-LIFE-SME-REVIEW");
      warnings.push("INDEFINITE-LIFE-SME-REVIEW [" + it.item_id + "]: capitalized " +
        "intangible with no §197 route and no benefit dates — recovery period " +
        "is a per-item SME determination, not defaulted.");
    }

    const [delta, rw] = reconcile(it.prior_capitalized_basis, cap,
      "§1.263(a)-4 intangible " + (it.item_id || it.description));
    warnings.push(...rw);
    amortizable.push({ item_id: it.item_id, description: it.description,
      category: "intangible", basis: delta, recovery_months: recovery,
      convention, start_year: currentTaxYear,
      source: "Phase G compute_263a4_5", authority,
      flags: row.flags.slice(), notes: "" });
    row.deductible = ded; row.capitalized = cap; row.posted_basis = delta;
    deductibleTotal = deductibleTotal.plus(ded);
    capitalizedTotal = capitalizedTotal.plus(delta);
    intangibleItems.push(row);
  }

  const startupItems = [];
  for (const poolRaw of startupPools) {
    const pool = Object.assign({}, poolRaw);
    pool.total = D.from(pool.total || 0);
    pool.business_commencement = parseDate(pool.business_commencement);
    const row = { pool_id: pool.pool_id, kind: pool.kind, total: pool.total,
      first_year_deduction: D.zero(), amortizable_remainder: D.zero(),
      first_year_amortization: D.zero(), flags: [] };
    if (pool.total.lt(0)) {
      row.flags.push("NEGATIVE-POOL-TOTAL");
      warnings.push("NEGATIVE-POOL-TOTAL [startup " + pool.pool_id + "]: total " +
        money(pool.total) + " — nothing computed; fix the schedule.");
      startupItems.push(row);
      continue;
    }
    if (pool.kind === "syndication") {
      row.flags.push("SYNDICATION-PERMANENTLY-CAPITALIZED");
      warnings.push("SYNDICATION-PERMANENTLY-CAPITALIZED [" + pool.pool_id + "]: §709(b) " +
        "syndication costs — no first-year deduction, no amortization; " +
        "deductible only on complete liquidation.");
      amortizable.push({ item_id: pool.pool_id, description: "Syndication costs",
        category: "startup_org", basis: pool.total, recovery_months: null,
        convention: "none", start_year: currentTaxYear,
        source: "Phase G compute_263a4_5",
        authority: "§709(b): syndication costs, permanent capitalization",
        flags: ["SYNDICATION-PERMANENTLY-CAPITALIZED"], notes: "" });
      capitalizedTotal = capitalizedTotal.plus(pool.total);
      startupItems.push(row);
      continue;
    }

    const phaseout = D.max(D.zero(), pool.total.minus(STARTUP_PHASEOUT_START));
    const firstYear = D.min(pool.total,
      D.max(D.zero(), STARTUP_FIRST_YEAR_CAP.minus(phaseout)));
    const remainder = pool.total.minus(firstYear);
    let monthsInService, startYear;
    if (pool.business_commencement) {
      monthsInService = 12 - pool.business_commencement.m + 1;
      startYear = pool.business_commencement.y;
    } else {
      monthsInService = 12;
      startYear = currentTaxYear;
      row.flags.push("BUSINESS-COMMENCEMENT-DATE-MISSING");
      warnings.push("BUSINESS-COMMENCEMENT-DATE-MISSING [" + pool.pool_id + "]: " +
        "amortization must begin with the month the active trade or business " +
        "begins — January assumed pending the date.");
    }
    let firstYearAmort = D.zero();
    if (remainder.gt(0)) {
      firstYearAmort = remainder.times(D.from(monthsInService))
        .div(D.from(STARTUP_RECOVERY_MONTHS)).q(CENT, "HE");
      amortizable.push({ item_id: pool.pool_id,
        description: pool.kind + " cost pool",
        category: "startup_org", basis: remainder,
        recovery_months: STARTUP_RECOVERY_MONTHS,
        convention: "full-month", start_year: startYear,
        source: "Phase G compute_263a4_5",
        authority: "§195(b)/§248(a)/§709(b)(1): 180-month straight-line from " +
          "business commencement",
        flags: [], notes: "Year-1 amortization " + monthsInService + "/180 " +
          "(months in service, calendar-year assumption)." });
      capitalizedTotal = capitalizedTotal.plus(remainder);
    }
    row.first_year_deduction = firstYear;
    row.amortizable_remainder = remainder;
    row.first_year_amortization = firstYearAmort;
    deductibleTotal = deductibleTotal.plus(firstYear);
    startupItems.push(row);
  }

  return { transaction_items: transactionItems,
    intangible_items: intangibleItems, startup_items: startupItems,
    amortizable_items: amortizable, capitalized_total: capitalizedTotal,
    deductible_total: deductibleTotal, warnings };
}

function routeDemolition(demolitionCost, remainingStructureBasis, opts) {
  opts = opts || {};
  demolitionCost = D.from(demolitionCost || 0);
  remainingStructureBasis = D.from(remainingStructureBasis || 0);
  const warnings = [];
  const items = [];
  if (opts.casualty) {
    warnings.push("CASUALTY-EXCEPTION-SME-REVIEW: casualty-triggered demolition — " +
      "Notice 90-21 carve-out may apply; §280B land capitalization NOT " +
      "auto-applied, route to SME.");
    return { amortizable_items: items, warnings };
  }
  const total = demolitionCost.plus(remainingStructureBasis);
  warnings.push("§280B-CAPITALIZED-TO-LAND: demolition cost " + money(demolitionCost) +
    " + remaining structure basis " + money(remainingStructureBasis) +
    " capitalized to land — no loss, no depreciation (Reg. §1.280B-1).");
  items.push({ item_id: "", description: "§280B demolition — capitalized to land",
    category: "land", basis: total, recovery_months: null, convention: "none",
    start_year: 0, source: "Phase G route_demolition",
    authority: "§280B / Reg. §1.280B-1",
    flags: ["§280B-CAPITALIZED-TO-LAND"], notes: "" });
  return { amortizable_items: items, warnings };
}

/* ================================ §59(e) ================================= */

const QE_PERIODS = {
  circulation: { months: 36,
    authority: "§59(e)(2)(A) — §173 circulation expenditures; 3-taxable-year period per §59(e)(4)(A)" },
  re_domestic: { months: 120,
    authority: "§59(e)(2)(B) — domestic research & experimental expenditures under §174A(a) (cite re-pointed from old §174(a) by OBBBA/P.L. 119-21 §70302); 10-year period per §59(e)(1)" },
  idc: { months: 60,
    authority: "§59(e)(2)(C) — intangible drilling and development costs under §263(c); 60-month period per §59(e)(4) (§57(a)(2) preference)" },
  mining_exploration: { months: 120,
    authority: "§59(e)(2)(E) — mining exploration expenditures under §617(a); 10-year period per §59(e)(1) (§57(a) subparagraph UNVERIFIED — §57-MINING-CITE-UNVERIFIED)" },
  mining_development: { months: 120,
    authority: "§59(e)(2)(D) — mining development expenditures under §616(a); 10-year period per §59(e)(1) (§57(a) subparagraph UNVERIFIED — §57-MINING-CITE-UNVERIFIED)" },
};

const C_CORP_GATE_WARNING = "§59(e) has no current-law use for a C corp with no " +
  "individual-AMT-exposed owners (corporate AMT repealed by TCJA; CAMT §55/§56A " +
  "does not use §57/§59(e) preference items)";

function compute59e(elections, opts) {
  opts = opts || {};
  const entityType = opts.entity_type || "c_corp";
  const individualAmtExposure = !!opts.individual_amt_exposure;
  const overlapping = new Set(opts.overlapping_174A_items || []);
  const warnings = [];
  const items = [];
  const amortizable = [];

  if (!individualAmtExposure && entityType !== "sole_prop") {
    if (entityType === "c_corp") {
      return { items, amortizable_items: amortizable, warnings: [C_CORP_GATE_WARNING] };
    }
    return { items, amortizable_items: amortizable, warnings: [
      "§59E-NO-AMT-EXPOSURE: entity_type=" + pyrepr(entityType) + " with " +
      "individual_amt_exposure=False — §59(e) matters only when an individual " +
      "owner could face §55/§56/§57 preference items (Gate 10 Q10.1). No " +
      "election scheduled; re-run with individual_amt_exposure=True if owners " +
      "are exposed."] };
  }

  for (const elRaw of elections) {
    const el = Object.assign({}, elRaw);
    el.amount = D.from(el.amount || 0);
    if (!el.elected) continue;
    if (el.amount.lt(0)) {
      warnings.push("NEGATIVE-AMOUNT [§59(e) " + el.item_id + "]: " + money(el.amount) +
        " — no schedule built; fix the expenditure figure.");
      continue;
    }
    const row = { item_id: el.item_id, category: el.category, amount: el.amount,
      recovery_months: null, first_year_amortization: D.zero(), flags: [] };
    const spec = QE_PERIODS[el.category];
    if (!spec) {
      warnings.push("§59E-CATEGORY-UNKNOWN [" + el.item_id + "]: " +
        pyrepr(el.category) + " is not a §59(e)(2) qualified-expenditure " +
        "category — no schedule built.");
      row.flags.push("§59E-CATEGORY-UNKNOWN");
      items.push(row);
      continue;
    }
    if (String(el.category).startsWith("mining_")) {
      row.flags.push("§57-MINING-CITE-UNVERIFIED");
      warnings.push("§57-MINING-CITE-UNVERIFIED [" + el.item_id + "]: the exact §57(a) " +
        "subparagraph for the mining exploration/development AMT preference is " +
        "unconfirmed against primary text.");
    }
    if (overlapping.has(el.item_id)) {
      row.flags.push("§59E-174A-ELECTION-CONFLICT");
      warnings.push("§59E-174A-ELECTION-CONFLICT [" + el.item_id + "]: §174A(c) " +
        "capitalization was also elected on these dollars — which period governs " +
        "(10-year §59(e) vs. the elected ≥60-month §174A(c)) is unresolved; " +
        "routed to SME review.");
    }
    const months = spec.months;
    const item = { item_id: el.item_id,
      description: "§59(e) election — " + el.category,
      category: "qualified_expenditure", basis: el.amount,
      recovery_months: months, convention: "mid-year",
      start_year: el.election_year || 0,
      source: "Phase H compute_59e", authority: spec.authority,
      flags: row.flags.slice(),
      notes: "Mid-year start is a documented proxy — the schedule carries no " +
        "month data (see module docstring). Election is item-by-item and " +
        "irrevocable except by IRS consent." };
    row.recovery_months = months;
    row.first_year_amortization = firstYearAmortization(item);
    amortizable.push(item);
    items.push(row);
  }

  return { items, amortizable_items: amortizable, warnings };
}

/* ================================ §1060 ================================== */

const CLASS_ORDER = ["I", "II", "III", "IV", "V", "VI"];

function compute1060Allocation(ppa) {
  const warnings = [];
  const byClass = {};
  const consideration = D.from(ppa.aggregate_consideration || 0);
  const classFmv = {};
  for (const [k, v] of Object.entries(ppa.class_fmv || {})) classFmv[k] = D.from(v);

  if (consideration.lt(0)) {
    warnings.push("NEGATIVE-CONSIDERATION [" + ppa.transaction_id + "]: aggregate " +
      "consideration " + money(consideration) + " is negative — no allocation " +
      "computed; correct the input.");
    return { by_class: {}, class_vii_residual: D.zero(), warnings };
  }

  const unknown = Object.keys(classFmv).filter(k => !CLASS_ORDER.includes(k)).sort();
  if (unknown.length) {
    warnings.push("UNKNOWN-CLASS-KEYS [" + ppa.transaction_id + "]: [" +
      unknown.map(u => "'" + u + "'").join(", ") + "] ignored — class_fmv keys " +
      "must be 'I'..'VI' (Class VII is the residual, never an input).");
  }

  let remaining = consideration;
  let shortfallHit = false;
  for (const cls of CLASS_ORDER) {
    const fmv = classFmv[cls] || D.zero();
    if (fmv.lt(0)) {
      warnings.push("NEGATIVE-CLASS-FMV [" + ppa.transaction_id + "]: Class " + cls +
        " FMV " + money(fmv) + " is invalid — treated as $0; fix the valuation.");
      byClass[cls] = D.zero();
      continue;
    }
    if (shortfallHit) { byClass[cls] = D.zero(); continue; }
    if (remaining.ge(fmv)) {
      byClass[cls] = fmv;
      remaining = remaining.minus(fmv);
    } else {
      byClass[cls] = remaining;
      remaining = D.zero();
      shortfallHit = true;
      warnings.push("CONSIDERATION-BELOW-CLASS-FMV [" + ppa.transaction_id + "]: " +
        "consideration exhausted within Class " + cls + " (FMV " + money(fmv) +
        ", only " + money(byClass[cls]) + " available) — allocated proportionally " +
        "to FMV within the class per §1.338-6(b), zero to later classes; " +
        "consideration below the sum of Class I-VI FMVs signals a data or " +
        "valuation error.");
    }
  }
  byClass["VII"] = remaining;
  return { by_class: byClass, class_vii_residual: remaining, warnings };
}

/* ================================= SCA =================================== */

const SCA_DRIVERS = {
  drivers: ["headcount", "square_footage", "direct_labor", "machine_hours",
    "book_cost", "direct_material"],
  categories: [
    { match_keywords: ["hr", "human resources", "personnel", "payroll"],
      preferred: ["headcount", "direct_labor"],
      blocked: ["machine_hours", "square_footage"] },
    { match_keywords: ["property tax", "building", "rent",
        "depreciation - building", "facilities"],
      preferred: ["square_footage", "book_cost"], blocked: ["headcount"] },
    { match_keywords: ["it", "information technology"],
      preferred: ["headcount"], blocked: ["machine_hours"] },
  ],
  default: { allowed: ["headcount", "square_footage", "direct_labor",
    "machine_hours", "book_cost", "direct_material"] },
};

const NON_PRODUCTION = "NON_PRODUCTION";

function canon(s) {
  return String(s).toLowerCase().replace(/-/g, " ").replace(/\//g, " ")
    .replace(/\s+/g, " ").trim();
}
function escapeRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }
function matchCategory(description, taxonomy) {
  const desc = canon(description);
  for (const cat of taxonomy.categories || []) {
    for (const kw of cat.match_keywords) {
      const re = new RegExp("\\b" + escapeRe(canon(kw)) + "\\b");
      if (re.test(desc)) return cat;
    }
  }
  return null;
}

function validateDriver(pool, taxonomy) {
  const warnings = [];
  const known = new Set(taxonomy.drivers || []);
  const label = "pool " + pool.pool_id + " ('" + pool.description + "')";
  if (!known.has(pool.driver)) {
    warnings.push("HARD-BLOCKED-DRIVER [" + label + "]: driver '" + pool.driver +
      "' is not a recognized allocation driver — pool not allocated");
    return warnings;
  }
  const cat = matchCategory(pool.description, taxonomy);
  if (cat !== null) {
    if ((cat.blocked || []).includes(pool.driver)) {
      warnings.push("HARD-BLOCKED-DRIVER [" + label + "]: '" + pool.driver + "' is a " +
        "nonsensical driver for this pool category (keywords " +
        JSON.stringify(cat.match_keywords) + ") — pool not allocated");
    } else if ((cat.preferred || []).length && !cat.preferred.includes(pool.driver)) {
      warnings.push("SOFT-DRIVER-MISMATCH [" + label + "]: '" + pool.driver + "' is not " +
        "a preferred driver for this pool category (preferred " +
        JSON.stringify(cat.preferred) + ") — allocated anyway; review");
    }
  } else {
    const allowed = (taxonomy.default && taxonomy.default.allowed) || Array.from(known);
    if (!allowed.includes(pool.driver)) {
      warnings.push("SOFT-DRIVER-MISMATCH [" + label + "]: '" + pool.driver + "' is " +
        "outside the default allowed driver set — allocated anyway; review");
    }
  }
  return warnings;
}

function splitPool(pool) {
  const keys = Object.keys(pool.targets);
  const total = D.sum(keys.map(k => pool.targets[k]));
  const allocated = {};
  for (const t of keys) allocated[t] = pool.amount.times(pool.targets[t]).div(total).q(CENT, "HU");
  const plug = pool.amount.minus(D.sum(keys.map(k => allocated[k])));
  if (!plug.isZero()) {
    let largestKey = keys[0];
    for (const t of keys) if (pool.targets[t].gt(pool.targets[largestKey])) largestKey = t;
    allocated[largestKey] = allocated[largestKey].plus(plug);
  }
  return allocated;
}

function computeSCA(pools, assets, sscmRatio, opts) {
  opts = opts || {};
  const taxonomy = opts.drivers || SCA_DRIVERS;
  const bookCapitalizedIndirect = opts.book_capitalized_indirect || {};
  const warnings = [];
  const auditTrail = [];
  const conservationChecks = [];
  let notBookedTotal = D.zero();
  let deductibleTotal = D.zero();

  sscmRatio = D.from(sscmRatio);
  if (!(sscmRatio.ge(0) && sscmRatio.le(1))) {
    warnings.push("SSCM RATIO = " + sscmRatio + " is outside [0,1] — clamped. Review.");
    sscmRatio = D.max(D.zero(), D.min(D.from(1), sscmRatio));
  }

  pools = pools.map(p => {
    const np = Object.assign({}, p);
    np.amount = D.from(p.amount || 0);
    const t = {};
    for (const [k, v] of Object.entries(p.targets || {})) t[k] = D.from(v);
    np.targets = t;
    return np;
  });
  assets = assets.map(a => {
    const na = Object.assign({}, a);
    na.book_cost = D.from(a.book_cost || 0);
    return na;
  });

  const byId = {};
  for (const a of assets) byId[a.asset_id] = a;
  const perAsset = {};
  for (const a of assets) {
    perAsset[a.asset_id] = { book_cost: a.book_cost,
      indirect_263a: D.zero(), mixed_263a: D.zero() };
  }

  for (const pool of pools) {
    const poolWarnings = validateDriver(pool, taxonomy);
    warnings.push(...poolWarnings);
    let blocked = poolWarnings.some(w => w.startsWith("HARD-BLOCKED-DRIVER"));
    const targetKeys = Object.keys(pool.targets);
    const driverTotal = D.sum(targetKeys.map(k => pool.targets[k]));
    let blockFlag = "HARD-BLOCKED-DRIVER";
    if (pool.amount.lt(0) && !blocked) {
      blocked = true;
      blockFlag = "NEGATIVE-POOL-AMOUNT";
      warnings.push("NEGATIVE-POOL-AMOUNT [pool " + pool.pool_id + "]: pool amount is " +
        money(pool.amount) + " — a cost pool cannot be negative; pool NOT " +
        "allocated. Route credits/reversals through the classifier, not a " +
        "negative pool.");
    }
    const negativeDrivers = targetKeys.filter(t => pool.targets[t].lt(0));
    if (negativeDrivers.length && !blocked) {
      blocked = true;
      blockFlag = "NEGATIVE-DRIVER-VALUE";
      warnings.push("NEGATIVE-DRIVER-VALUE [pool " + pool.pool_id + "]: driver values for [" +
        negativeDrivers.map(t => "'" + t + "'").join(", ") + "] are negative — a " +
        "driver share is a fraction of a physical quantity; pool NOT allocated. " +
        "Fix the driver data.");
    }
    const degenerate = driverTotal.isZero();
    if (degenerate && !blocked) {
      warnings.push("POOL-DEGENERATE-DENOMINATOR [pool " + pool.pool_id + "]: Σ driver " +
        "values == 0 — nothing allocated; supply real driver data");
    }

    if (blocked || degenerate) {
      for (const target of targetKeys) {
        auditTrail.push({ pool_id: pool.pool_id, target, driver: pool.driver,
          driver_value: pool.targets[target], share: D.zero(),
          allocated: D.zero(), capitalized: D.zero(), deductible: D.zero(),
          not_booked: D.zero(),
          flags: [blocked ? blockFlag : "POOL-DEGENERATE-DENOMINATOR"] });
      }
      conservationChecks.push({ pool_id: pool.pool_id, pool_amount: pool.amount,
        allocated_sum: D.zero(), expected: D.zero(), ok: true,
        note: "pool not allocated (blocked/degenerate driver)" });
      continue;
    }

    const allocated = splitPool(pool);
    for (const target of targetKeys) {
      const dv = pool.targets[target];
      const amt = allocated[target];
      const share = dv.div(driverTotal);
      const flags = [];
      let capitalized = D.zero(), deductible = D.zero(), notBooked = D.zero();
      const asset = byId[target];

      if (target === NON_PRODUCTION) {
        deductible = amt;
      } else if (!asset) {
        flags.push("POOL-TARGET-UNKNOWN");
        notBooked = amt;
        warnings.push("POOL-TARGET-UNKNOWN [pool " + pool.pool_id + "]: target '" + target +
          "' matches no asset — share " + money(amt) + " not booked");
      } else if (pool.is_mixed_service) {
        if (asset.sscm_eligible) {
          capitalized = amt.times(sscmRatio).q(CENT, "HU");
          deductible = amt.minus(capitalized);
          perAsset[target].mixed_263a = perAsset[target].mixed_263a.plus(capitalized);
        } else {
          flags.push("SSCM-INELIGIBLE-NO-FALLBACK");
          notBooked = amt;
          warnings.push("SSCM-INELIGIBLE-NO-FALLBACK [pool " + pool.pool_id + " → " + target +
            "]: asset fails §1.263A-1(h)(2) routes (C)/(D); driver share " +
            money(amt) + " computed but NOT booked to bucket B — general " +
            "§1.263A-1(g)(4) method required");
        }
      } else {
        capitalized = amt;
        perAsset[target].indirect_263a = perAsset[target].indirect_263a.plus(capitalized);
      }

      notBookedTotal = notBookedTotal.plus(notBooked);
      deductibleTotal = deductibleTotal.plus(deductible);
      auditTrail.push({ pool_id: pool.pool_id, target, driver: pool.driver,
        driver_value: dv, share, allocated: amt, capitalized, deductible,
        not_booked: notBooked, flags });
    }

    const allocatedSum = D.sum(targetKeys.map(k => allocated[k]));
    conservationChecks.push({ pool_id: pool.pool_id, pool_amount: pool.amount,
      allocated_sum: allocatedSum, expected: pool.amount,
      ok: allocatedSum.eq(pool.amount), note: "" });
    if (!allocatedSum.eq(pool.amount)) {
      warnings.push("POOL-CONSERVATION-FAILED [pool " + pool.pool_id + "]: allocated " +
        allocatedSum + " != pool amount " + pool.amount + ". Do not proceed.");
    }
  }

  for (const [assetId, amountRaw] of Object.entries(bookCapitalizedIndirect)) {
    const amount = D.from(amountRaw || 0);
    if (!amount.isZero()) {
      warnings.push("CIP-DOUBLE-COUNT-REVIEW [" + assetId + "]: " + money(amount) +
        " of indirect cost is already book-capitalized in CIP (bucket A); " +
        "bucket B may re-add some or all of it. No adjustment made — routed to " +
        "review queue pending the bucket A/B double-count rule");
    }
  }

  for (const assetId of Object.keys(perAsset)) {
    const row = perAsset[assetId];
    row.additional_263a = row.indirect_263a.plus(row.mixed_263a);
    row.adjusted_basis_pre_interest = row.book_cost.plus(row.additional_263a);
    row.ape_for_interest = row.adjusted_basis_pre_interest;
  }

  const apeByAsset = {};
  for (const [aid, r] of Object.entries(perAsset)) apeByAsset[aid] = r.ape_for_interest;

  return { per_asset: perAsset, ape_by_asset: apeByAsset,
    audit_trail: auditTrail, warnings, not_booked_total: notBookedTotal,
    deductible_total: deductibleTotal, conservation_checks: conservationChecks };
}

/* ============================ tax-basis TB =============================== */

function computeTaxBasisTB(tbLines, btds) {
  const byKey = {};
  const byAcct = {};
  const taxLines = [];
  const warnings = [];
  for (const ln of tbLines) {
    const copy = { acct_num: ln.acct_num || "", acct_desc: ln.acct_desc || "",
      cc_num: ln.cc_num || "", cc_desc: ln.cc_desc || "",
      amount: D.from(ln.amount || 0), statement_type: ln.statement_type || "",
      tier1: ln.tier1, cap_vs_deduct: ln.cap_vs_deduct, is_labor: ln.is_labor,
      code: ln.code };
    taxLines.push(copy);
    const key = copy.acct_num + " " + copy.cc_num;
    if (key in byKey && copy.acct_num) {
      warnings.push("DUPLICATE-TB-KEY (acct='" + copy.acct_num + "', cc='" + copy.cc_num +
        "'): multiple TB lines share this key — a BTD matching it applies to the " +
        "LAST line only ('" + copy.acct_desc + "'). Split the BTD or disambiguate " +
        "the accounts if that's not the intended target.");
    }
    byKey[key] = copy;
    (byAcct[copy.acct_num] = byAcct[copy.acct_num] || []).push(copy);
  }
  const unmatched = [];
  const applied = [];
  for (const btdRaw of btds) {
    const btd = Object.assign({}, btdRaw);
    btd.adjustment = D.from(btd.adjustment || 0);
    let target = byKey[(btd.acct_num || "") + " " + (btd.cc_num || "")] || null;
    if (target === null && btd.acct_num && !btd.cc_num) {
      const candidates = byAcct[btd.acct_num] || [];
      if (candidates.length === 1) target = candidates[0];
      else if (candidates.length > 1) {
        warnings.push("BTD '" + (btd.btd_id || btd.description) + "' matches account '" +
          btd.acct_num + "' in " + candidates.length + " cost centers — no cc_num " +
          "given; applied to none. Split the BTD by cost center.");
        unmatched.push(btd);
        continue;
      }
    }
    if (target === null) {
      taxLines.push({ acct_num: btd.acct_num || "",
        acct_desc: "[BTD] " + (btd.description || ""), cc_num: btd.cc_num || "",
        cc_desc: "", amount: btd.adjustment });
      warnings.push("BTD '" + (btd.btd_id || btd.description) + "' matched no TB line " +
        "(acct='" + (btd.acct_num || "") + "', cc='" + (btd.cc_num || "") + "') — " +
        "carried as a standalone tax-only line; verify the account mapping.");
      unmatched.push(btd);
      applied.push({ btd, target: null });
      continue;
    }
    target.amount = target.amount.plus(btd.adjustment);
    applied.push({ btd, target });
  }

  const bookTotal = D.sum(tbLines.map(l => D.from(l.amount || 0)));
  const taxTotal = D.sum(taxLines.map(l => l.amount));
  const btdTotal = D.sum(btds.map(b => D.from(b.adjustment || 0)));

  const ccRollup = {};
  for (const ln of taxLines) {
    const k = ln.cc_num || "";
    ccRollup[k] = (ccRollup[k] || D.zero()).plus(ln.amount);
  }

  const m1 = { book_total: bookTotal, btd_total: btdTotal, tax_total: taxTotal,
    tie_check: taxTotal.minus(bookTotal.plus(btdTotal)) };
  if (!m1.tie_check.isZero()) {
    warnings.push("TAX-BASIS TB TIE-CHECK FAILED: " + m1.tie_check + " — a BTD was " +
      "dropped or double-applied. Do not proceed.");
  }
  return { tax_lines: taxLines, m1_reconciliation: m1, cc_rollup: ccRollup,
    warnings, unmatched_btds: unmatched, applied };
}

/* ============ §263(a) tangible property — capitalize vs deduct ============ */
/* Port of engines/tangible_263a.py — decision order verbatim (see that
 * module's docstring for the full citation-by-citation walkthrough):
 * 1. negative amount -> sme_review.
 * 2. de minimis safe harbor (§1.263(a)-1(f)) if elected.
 * 3. materials & supplies (§1.162-3) if flagged.
 * 4. small taxpayer building safe harbor (§1.263(a)-3(h)) if elected + building.
 * 5. BAR improvement tests (betterment/adaptation/restoration, §1.263(a)-3(j)/(l)/(k)).
 * 6. routine maintenance safe harbor (§1.263(a)-3(i)).
 * 7. repair (§162; §1.263(a)-3(d)) or the (n) capitalize-per-books election.
 * Every step short-circuits to a `continue` in the Python; missing BAR facts
 * capitalize CONSERVATIVELY and emit an open question — never a silent deduct. */

const STSH_GROSS_RECEIPTS_CEILING = D.from("10000000");
const STSH_BASIS_CEILING = D.from("1000000");
const STSH_DOLLAR_CEILING = D.from("10000");
const STSH_BASIS_PCT = D.from("0.02");

function computeTangible263a(items, profile, opts) {
  opts = opts || {};
  const deMinimisElection = !!opts.de_minimis_election;
  const smallTaxpayerBuildingElection = !!opts.small_taxpayer_building_election;
  const capitalizeRepairsFollowingBooks = !!opts.capitalize_repairs_following_books;
  const explicitAgg = opts.total_building_repairs_maintenance_improvements || null;

  const warnings = [];
  const openQuestions = [];
  const seenQuestions = new Set();
  function ask(item, question, why) {
    if (seenQuestions.has(question)) return;
    seenQuestions.add(question);
    openQuestions.push({ item_id: item.item_id, question, why });
  }

  if (deMinimisElection && profile.has_afs) {
    warnings.push("DE-MINIMIS-POLICY-CONDITION: the §1.263(a)-1(f) de minimis safe " +
      "harbor is elected and the taxpayer has an AFS — a WRITTEN accounting " +
      "policy expensing amounts under the ceiling, in place as of the START " +
      "of the taxable year, is a condition of the election ((f)(1)(i)(B)). " +
      "Confirm it exists; the election is annual, irrevocable, and " +
      "all-or-nothing for qualifying items.");
  }
  if (smallTaxpayerBuildingElection
      && profile.avg_gross_receipts.gt(STSH_GROSS_RECEIPTS_CEILING)) {
    warnings.push("STSH-INELIGIBLE-RECEIPTS: the §1.263(a)-3(h) small-taxpayer " +
      "building safe harbor is elected but average annual gross receipts (" +
      money0(profile.avg_gross_receipts) + ") exceed the $10,000,000 ceiling " +
      "— the safe harbor is unavailable; no item was deducted under it.");
  }

  const uopSums = {};
  for (const it of items) {
    const amt = D.from(it.amount || 0);
    if (it.unit_of_property && amt.ge(0)) {
      uopSums[it.unit_of_property] = (uopSums[it.unit_of_property] || D.zero()).plus(amt);
    }
  }

  let msTimingWarned = false, stshScheduleAggWarned = false;
  let repairsBookCapitalized = 0, repairsBookExpensed = 0;

  const rows = [];
  let deductibleTotal = D.zero(), capitalizedTotal = D.zero(),
    electiveCapitalizedTotal = D.zero();

  for (const itRaw of items) {
    const it = Object.assign({}, itRaw);
    it.amount = D.from(it.amount || 0);
    it.building_unadjusted_basis = D.from(it.building_unadjusted_basis || 0);
    it.invoice_or_item_cost = (it.invoice_or_item_cost === null
      || it.invoice_or_item_cost === undefined || it.invoice_or_item_cost === "")
      ? null : D.from(it.invoice_or_item_cost);
    const label = it.item_id || it.description;
    const row = { item_id: it.item_id, description: it.description,
      amount: it.amount, treatment: "", authority: "", flags: [],
      deductible: D.zero(), capitalized: D.zero() };

    // 1. negative amount
    if (it.amount.lt(0)) {
      row.treatment = "sme_review";
      row.flags.push("NEGATIVE-AMOUNT");
      warnings.push("NEGATIVE-AMOUNT [tangible " + label + "]: " + money(it.amount) +
        " — nothing computed; route credits/refunds through the schedule, " +
        "not a negative expenditure.");
      rows.push(row);
      continue;
    }

    let fellThrough = false;

    // 2. de minimis safe harbor
    if (deMinimisElection) {
      if (it.invoice_or_item_cost !== null) {
        if (it.invoice_or_item_cost.le(deMinimisCeiling(profile))) {
          row.treatment = "de_minimis_deduct";
          row.authority = "Reg. §1.263(a)-1(f); Notice 2015-82";
          row.deductible = it.amount;
          deductibleTotal = deductibleTotal.plus(it.amount);
          rows.push(row);
          continue;
        }
      } else {
        row.flags.push("DE-MINIMIS-COST-UNKNOWN");
        const ceiling = deMinimisCeiling(profile);
        ask(it,
          "Item " + label + " '" + it.description + "': what is the " +
          "per-invoice (or per-item as substantiated on the invoice) cost " +
          "(Reg. §1.263(a)-1(f))? Supply invoice_or_item_cost to test it " +
          "against the " + money0(ceiling) + " de minimis ceiling.",
          "The de minimis election is on but the schedule does not carry " +
          "the per-invoice/per-item cost — the item continued down the " +
          "decision tree conservatively.");
      }
    }

    // 3. materials & supplies (§1.162-3)
    if (it.is_material_or_supply) {
      if (it.ms_unit_cost_200_or_less || it.ms_economic_life_12mo_or_less) {
        const prongs = [];
        if (it.ms_unit_cost_200_or_less) prongs.push("§1.162-3(c)(1)(iv) unit cost ≤ $200");
        if (it.ms_economic_life_12mo_or_less)
          prongs.push("§1.162-3(c)(1)(iii) economic life ≤ 12 months");
        row.treatment = "materials_supplies_deduct";
        row.authority = prongs.join("; ");
        row.flags.push("MS-TIMING-NOT-DETERMINED");
        if (!msTimingWarned) {
          msTimingWarned = true;
          warnings.push("MS-TIMING-NOT-DETERMINED: materials & supplies were " +
            "deducted under §1.162-3, but the incidental (deduct when " +
            "paid/incurred, (a)(2)) vs non-incidental (deduct when used or " +
            "consumed, (a)(1)) TIMING distinction is out of scope for this " +
            "engine — confirm the deduction year per item.");
        }
        row.deductible = it.amount;
        deductibleTotal = deductibleTotal.plus(it.amount);
        rows.push(row);
        continue;
      }
      if ((it.ms_unit_cost_200_or_less === null || it.ms_unit_cost_200_or_less === undefined)
          && (it.ms_economic_life_12mo_or_less === null || it.ms_economic_life_12mo_or_less === undefined)) {
        ask(it,
          "Item " + label + " '" + it.description + "': is the unit " +
          "acquisition/production cost $200 or less (§1.162-3(c)(1)(iv)), " +
          "or is the economic useful life 12 months or less " +
          "(§1.162-3(c)(1)(iii))? Answer ms_unit_cost_200_or_less and " +
          "ms_economic_life_12mo_or_less True/False.",
          "The item is marked as a materials & supplies candidate but " +
          "neither §1.162-3 prong is established — it continued down the " +
          "decision tree.");
      }
    }

    // 4. small taxpayer building safe harbor
    if (smallTaxpayerBuildingElection && it.is_building) {
      const eligible = profile.avg_gross_receipts.le(STSH_GROSS_RECEIPTS_CEILING)
        && it.building_unadjusted_basis.le(STSH_BASIS_CEILING);
      if (!eligible) {
        row.flags.push("STSH-NOT-ELIGIBLE");
      } else {
        const uop = it.unit_of_property;
        let aggregate;
        if (explicitAgg && uop in explicitAgg) {
          aggregate = D.from(explicitAgg[uop]);
        } else {
          aggregate = uop ? (uopSums[uop] || D.zero()) : it.amount;
          if (!stshScheduleAggWarned) {
            stshScheduleAggWarned = true;
            warnings.push("STSH-AGGREGATE-FROM-SCHEDULE-ONLY: the §1.263(a)-3(h) " +
              "per-building aggregate was summed from the items ON THIS " +
              "SCHEDULE only — the test requires ALL amounts paid during " +
              "the year for repairs, maintenance, and improvements on the " +
              "building, including amounts outside this schedule. Supply " +
              "total_building_repairs_maintenance_improvements to test the " +
              "true aggregate.");
          }
        }
        const ceiling = D.min(STSH_DOLLAR_CEILING,
          STSH_BASIS_PCT.times(it.building_unadjusted_basis));
        if (aggregate.le(ceiling)) {
          row.treatment = "small_taxpayer_sh_deduct";
          row.authority = "Reg. §1.263(a)-3(h) small taxpayer building safe harbor";
          row.deductible = it.amount;
          deductibleTotal = deductibleTotal.plus(it.amount);
          rows.push(row);
          continue;
        }
        row.flags.push("STSH-CEILING-EXCEEDED");
      }
    }

    // 5. BAR improvement tests
    const barTrue = [];
    if (it.betterment) barTrue.push("Reg. §1.263(a)-3(j) betterment");
    if (it.adaptation) barTrue.push("Reg. §1.263(a)-3(l) adaptation to a new/different use");
    if (it.restoration) barTrue.push("Reg. §1.263(a)-3(k) restoration");
    if (barTrue.length) {
      row.treatment = "improvement_capitalize";
      row.authority = barTrue.join("; ");
      row.capitalized = it.amount;
      capitalizedTotal = capitalizedTotal.plus(it.amount);
      rows.push(row);
      continue;
    }
    const prompts = {
      betterment: "betterment (§1.263(a)-3(j)) — does the work ameliorate a " +
        "pre-existing material condition or defect, or materially add to or " +
        "increase the capacity, productivity, efficiency, strength, or " +
        "quality of the unit of property?",
      adaptation: "adaptation (§1.263(a)-3(l)) — does the work adapt the " +
        "unit of property to a new or different use?",
      restoration: "restoration (§1.263(a)-3(k)) — does the work replace a " +
        "major component or substantial structural part, restore after a " +
        "basis-adjusted loss, or return the property to ordinary efficient " +
        "operating condition after deterioration to a state of disrepair " +
        "where it was no longer functional?",
    };
    const missing = ["betterment", "adaptation", "restoration"]
      .filter(p => it[p] === null || it[p] === undefined);
    if (missing.length) {
      row.treatment = "open_question_capitalize_pending";
      row.authority = "Reg. §1.263(a)-3(d)/(j)/(k)/(l) — improvement facts " +
        "pending; capitalized conservatively";
      row.flags.push("BAR-FACTS-INCOMPLETE");
      row.capitalized = it.amount;
      capitalizedTotal = capitalizedTotal.plus(it.amount);
      ask(it,
        "Item " + label + " '" + it.description + "': the following " +
        "improvement facts are not established: " + missing.join(", ") +
        ". Answer each True/False: " + missing.map(p => prompts[p]).join(" "),
        "Any single True prong requires capitalization as an improvement " +
        "(§1.263(a)-3(d)(2)); all-False opens the repair / " +
        "routine-maintenance path. The amount is capitalized CONSERVATIVELY " +
        "pending the answer — never silently deducted on missing facts.");
      rows.push(row);
      continue;
    }

    // 6. routine maintenance safe harbor
    if (it.routine_maintenance_expected_more_than_once) {
      row.treatment = "routine_maintenance_deduct";
      row.authority = "Reg. §1.263(a)-3(i) routine maintenance safe harbor";
      row.deductible = it.amount;
      deductibleTotal = deductibleTotal.plus(it.amount);
      rows.push(row);
      continue;
    }
    if (it.routine_maintenance_expected_more_than_once === null
        || it.routine_maintenance_expected_more_than_once === undefined) {
      ask(it,
        "Item " + label + " '" + it.description + "': at the time the unit " +
        "of property was placed in service, was this maintenance expected " +
        "to be performed more than once over the property's class life " +
        "(for a building: more than once in 10 years) (§1.263(a)-3(i))? " +
        "Answer routine_maintenance_expected_more_than_once True/False.",
        "All BAR prongs are False, so the amount is deductible either way " +
        "— the answer only settles whether the routine maintenance safe " +
        "harbor or the general repair rule is the cited authority.");
    }

    // 7. repair / (n) election
    if (capitalizeRepairsFollowingBooks && it.book_capitalized) {
      repairsBookCapitalized++;
      row.treatment = "elective_capitalize_books";
      row.authority = "Reg. §1.263(a)-3(n) election to capitalize repairs " +
        "capitalized on books";
      row.capitalized = it.amount;
      electiveCapitalizedTotal = electiveCapitalizedTotal.plus(it.amount);
      rows.push(row);
      continue;
    }
    if (capitalizeRepairsFollowingBooks) repairsBookExpensed++;
    row.treatment = "repair_deduct";
    row.authority = "§162; Reg. §1.263(a)-3(d)";
    row.deductible = it.amount;
    deductibleTotal = deductibleTotal.plus(it.amount);
    rows.push(row);
  }

  if (capitalizeRepairsFollowingBooks && repairsBookCapitalized && repairsBookExpensed) {
    warnings.push("N-ELECTION-CONSISTENCY: the §1.263(a)-3(n) election is on, but " +
      "some repair items are capitalized on books and others are not — the " +
      "election applies to ALL amounts paid for repair and maintenance " +
      "capitalized on the books and records for the year. Verify the book " +
      "treatment of every repair line is consistent with the election.");
  }

  return { items: rows, open_questions: openQuestions,
    deductible_total: deductibleTotal, capitalized_total: capitalizedTotal,
    elective_capitalized_total: electiveCapitalizedTotal, warnings };
}
/* ============================== exports ================================== */

const CAP263A = {
  D, dec, fmt, money, q2,
  THRESHOLDS, LARGE_PRODUCER_THRESHOLD,
  makeProfile, sec448Threshold, thresholdIsEstimate, sec448PreTcja, smallBusinessExempt,
  deMinimisCeiling,
  BUCKETS, CAPITALIZED_BUCKETS, TIER1_CHOICES, bucketOf, analyzeAssigned,
  computeSSCM, computeUnicap, computeSPM, computeMSPM, computeSRM,
  computeLifoDecrementRelease,
  reconcile, isEligibleDebt, compute263af,
  compute174, firstYearAmortization,
  compute263a45, routeDemolition,
  compute59e, QE_PERIODS,
  compute1060Allocation,
  computeSCA, SCA_DRIVERS,
  computeTaxBasisTB,
  computeTangible263a,
};

if (typeof module !== "undefined" && module.exports) module.exports = CAP263A;
if (typeof window !== "undefined") window.CAP263A = CAP263A;
