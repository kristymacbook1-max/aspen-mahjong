/* cap263a standalone calculator — UI layer over engines.js.
 * All computation happens in engines.js (parity-tested vs the Python
 * engines); this file only builds forms, feeds them to the engines, and
 * renders results + warnings. State persists to localStorage and can be
 * exported/imported as JSON. */
"use strict";
(function () {
  const E = window.CAP263A;
  const SELFTEST = window.CAP263A_SELFTEST;
  const D = E.D;

  /* ---------------- state ---------------- */
  const STORAGE_KEY = "cap263a_standalone_v1";
  const state = {
    profile: {},
    tb_lines: [],
    btds: [],
    lifo: { layers: [], decrement: "" },
    interest: { projects: [], snapshots: [], debts: [],
      opts: { afr_highest: "", below_afr_interest: "", guaranteed_payments: "" } },
    sca: { assets: [], pools: [], sscm_ratio: "", book_capitalized_indirect: "" },
    s174: { expenditures: [], opts: {} },
    intang: { transaction_costs: [], intangibles: [], startup_pools: [],
      success_fee_elections: "", demolition: { cost: "", basis: "", casualty: false } },
    s59e: { elections: [], opts: { entity_type: "c_corp",
      individual_amt_exposure: false, overlapping: "" } },
    s1060: { transaction_id: "", aggregate_consideration: "",
      class_fmv: { I: "", II: "", III: "", IV: "", V: "", VI: "" } },
    tangible: { items: [], opts: { de_minimis_election: false,
      small_taxpayer_building_election: false,
      capitalize_repairs_following_books: false,
      total_building_repairs_maintenance_improvements: "" } },
    interview_answers: {},
  };
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    if (saved && typeof saved === "object") deepMerge(state, saved);
  } catch (e) { /* fresh start */ }

  function deepMerge(dst, src) {
    for (const [k, v] of Object.entries(src)) {
      if (v && typeof v === "object" && !Array.isArray(v)
          && dst[k] && typeof dst[k] === "object" && !Array.isArray(dst[k])) {
        deepMerge(dst[k], v);
      } else dst[k] = v;
    }
  }
  function save() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
    catch (e) { /* storage may be unavailable on file:// in some browsers */ }
  }

  /* ---------------- tiny DOM helpers ---------------- */
  function el(tag, attrs, ...children) {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === "class") n.className = v;
      else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
      else if (k === "checked") n.checked = !!v;
      else if (k === "value") n.value = v == null ? "" : v;
      else n.setAttribute(k, v);
    }
    for (const c of children.flat()) {
      if (c == null) continue;
      n.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    }
    return n;
  }
  function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }

  /* value formatting for result tables */
  function fmtVal(v, kind) {
    if (v instanceof D) {
      if (kind === "ratio") return v.toString();
      if (kind === "pct") return v.times(100).q(-2, "HE").toString() + "%";
      return "$" + E.fmt(v, 2);
    }
    if (v === null || v === undefined) return "—";
    return String(v);
  }

  function kvTable(rows) {
    const t = el("table", { class: "kv" });
    for (const r of rows) {
      const [label, value, kindOrOpts] = r;
      const opts = typeof kindOrOpts === "object" ? kindOrOpts : { kind: kindOrOpts };
      const tr = el("tr", opts.hl ? { class: "hl" } : {},
        el("td", {}, label), el("td", {}, fmtVal(value, opts.kind)));
      t.appendChild(tr);
    }
    return t;
  }

  function warnList(warnings) {
    const box = el("div", {});
    for (const w of warnings || []) box.appendChild(el("div", { class: "warn" }, "⚠ " + w));
    if (!warnings || !warnings.length)
      box.appendChild(el("p", { class: "note" }, "No warnings."));
    return box;
  }

  function rawDetails(obj) {
    return el("details", { class: "raw" },
      el("summary", {}, "Full result (JSON)"),
      el("pre", {}, JSON.stringify(SELFTEST.serialize(obj), null, 2)));
  }

  /* ---------------- generic editable table ---------------- */
  /* cols: [{key, label, type: text|money|int|check|select|date|textarea,
   *         options?, width?, placeholder?}] */
  function ioTable(rows, cols, onChange, blankRow) {
    const wrap = el("div", { class: "tblwrap" });
    const table = el("table", { class: "io" });
    const thead = el("tr", {});
    for (const c of cols) thead.appendChild(el("th", c.width ? { style: "width:" + c.width } : {}, c.label));
    thead.appendChild(el("th", { style: "width:30px" }, ""));
    table.appendChild(thead);

    function render() {
      while (table.rows.length > 1) table.deleteRow(1);
      rows.forEach((row, i) => {
        const tr = el("tr", {});
        for (const c of cols) {
          const td = el("td", { class: (c.type === "money" || c.type === "int") ? "num" : "" });
          let inp;
          if (c.type === "check") {
            inp = el("input", { type: "checkbox", checked: !!row[c.key],
              onchange: e => { row[c.key] = e.target.checked; onChange && onChange(); save(); } });
          } else if (c.type === "select") {
            inp = el("select", {
              onchange: e => { row[c.key] = e.target.value; onChange && onChange(); save(); } },
              c.options.map(o => {
                const [val, lbl] = Array.isArray(o) ? o : [o, o];
                const opt = el("option", { value: val }, lbl);
                if (String(row[c.key] ?? "") === String(val)) opt.selected = true;
                return opt;
              }));
          } else if (c.type === "textarea") {
            inp = el("textarea", { rows: 2, placeholder: c.placeholder || "",
              oninput: e => { row[c.key] = e.target.value; save(); },
              onchange: () => { onChange && onChange(); } });
            inp.value = row[c.key] || "";
          } else {
            inp = el("input", { type: c.type === "date" ? "date" : "text",
              placeholder: c.placeholder || "",
              value: row[c.key] == null ? "" : row[c.key],
              oninput: e => { row[c.key] = e.target.value; save(); },
              onchange: () => { onChange && onChange(); } });
          }
          td.appendChild(inp);
          tr.appendChild(td);
        }
        tr.appendChild(el("td", {},
          el("button", { class: "mini", title: "Delete row",
            onclick: () => { rows.splice(i, 1); render(); onChange && onChange(); save(); } },
            "✕")));
        table.appendChild(tr);
      });
    }
    render();
    wrap.appendChild(table);
    wrap.appendChild(el("button", { class: "mini",
      onclick: () => { rows.push(Object.assign({}, blankRow || {})); render(); save(); } },
      "+ Add row"));
    return wrap;
  }

  /* parse "key=value" lines into an object */
  function parseKV(text) {
    const out = {};
    for (const line of String(text || "").split(/\n+/)) {
      const s = line.trim();
      if (!s) continue;
      const i = s.indexOf("=");
      if (i < 0) continue;
      out[s.slice(0, i).trim()] = s.slice(i + 1).trim();
    }
    return out;
  }
  function parseList(text) {
    return String(text || "").split(/[,\n]+/).map(s => s.trim()).filter(Boolean);
  }
  function numOrBlank(v) { return String(v == null ? "" : v).trim(); }
  function orZero(v) { const s = numOrBlank(v); return s === "" ? "0" : s; }

  /* ---------------- panels ---------------- */
  const panels = [];
  function panel(id, title, build) { panels.push({ id, title, build }); }

  function currentProfile() {
    const p = {};
    for (const [k, v] of Object.entries(state.profile)) {
      if (v === "" || v === null || v === undefined) continue;
      p[k] = v;
    }
    // numeric coercions for ints
    if (p.tax_year) p.tax_year = parseInt(p.tax_year, 10) || 2026;
    if (p.har_qualifying_year_index)
      p.har_qualifying_year_index = parseInt(p.har_qualifying_year_index, 10) || 0;
    return E.makeProfile(p);
  }

  /* ---- Entity Profile ---- */
  panel("profile", "Entity Profile", function (root) {
    root.appendChild(el("h2", {}, "Entity Profile"));
    root.appendChild(el("p", { class: "note" },
      "Everything downstream (§448(c) exemption gate, UNICAP method dispatch, " +
      "MSPM/SRM balances, HAR/LIFO elections) reads from this profile. Dollar " +
      "fields accept plain numbers (commas OK)."));

    const P = state.profile;
    function field(key, label, opts) {
      opts = opts || {};
      if (opts.type === "check") {
        return el("label", { class: "chk" },
          el("input", { type: "checkbox", checked: !!P[key],
            onchange: e => { P[key] = e.target.checked; save(); refreshDerived(); } }),
          label);
      }
      if (opts.type === "select") {
        return el("label", { class: "f" }, label,
          el("select", { onchange: e => { P[key] = e.target.value; save(); refreshDerived(); } },
            opts.options.map(o => {
              const [val, lbl] = Array.isArray(o) ? o : [o, o];
              const n = el("option", { value: val }, lbl);
              if (String(P[key] ?? opts.dflt ?? "") === String(val)) n.selected = true;
              return n;
            })));
      }
      return el("label", { class: "f" }, label,
        el("input", { type: "text", value: P[key] == null ? "" : P[key],
          placeholder: opts.placeholder || "",
          oninput: e => { P[key] = e.target.value; save(); },
          onchange: refreshDerived }));
    }

    root.appendChild(el("fieldset", {}, el("legend", {}, "Entity & exemption (§263A(i)/§448(c))"),
      el("div", { class: "grid" },
        field("entity_name", "Entity name"),
        field("entity_type", "Entity type", { type: "select",
          options: ["c_corp", "s_corp", "partnership", "sole_prop"], dflt: "c_corp" }),
        field("tax_year", "Tax year", { placeholder: "2026" }),
        field("avg_gross_receipts", "3-yr avg gross receipts (§448(c), aggregated)"),
        field("industry", "Industry")),
      el("div", { class: "grid", style: "margin-top:8px" },
        field("is_tax_shelter", "Tax shelter under §448(a)(3) (bars the exemption)", { type: "check" }),
        field("has_afs", "Has applicable financial statement (de minimis $5,000 vs $2,500)", { type: "check" }),
        field("produces", "Produces property (§263A producer)", { type: "check" }),
        field("acquires_for_resale", "Acquires property for resale", { type: "check" }))));

    root.appendChild(el("fieldset", {}, el("legend", {}, "UNICAP method & SSCM"),
      el("div", { class: "grid" },
        field("method", "Simplified method", { type: "select",
          options: ["SPM", "MSPM", "SRM"], dflt: "SPM" }),
        field("inventory_method", "Inventory method", { type: "select",
          options: ["FIFO", "lifo_specific", "lifo_dollar_value"], dflt: "FIFO" }),
        field("ending_inventory_471", "Ending §471 costs on hand (SPM/SRM multiplicand)"),
        field("sscm_ratio_method", "SSCM ratio method", { type: "select",
          options: [["labor", "labor-based (§1.263A-1(h)(4))"],
                    ["production_cost", "production-cost (§1.263A-1(h)(5), producers)"]],
          dflt: "labor" }),
        field("mixed_alloc_ratio", "SSCM ratio override (blank = computed)"),
        field("production_activity_level", "Production activity level (SRM gate)", { type: "select",
          options: [["", "— not established —"], ["de_minimis", "de minimis"],
                    ["more_than_de_minimis", "more than de minimis"]] })),
      el("div", { class: "grid", style: "margin-top:8px" },
        field("producer_de_minimis_200k", "$200K producer de minimis (§1.263A-2(b)(3)(iv)) — additional §263A deemed zero", { type: "check" }),
        field("msc_90_10_election", "(g)(4)(ii) 90/10 all-departments election (warns: not implemented)", { type: "check" }),
        field("production_incident_to_resale", "Production incident to resale (SRM (a)(4)(ii))", { type: "check" }),
        field("private_label_goods", "Private-label producer ((a)(4)(iii))", { type: "check" }))));

    root.appendChild(el("fieldset", {}, el("legend", {}, "MSPM balances (§1.263A-2(c)) — used when method = MSPM"),
      el("div", { class: "grid" },
        field("pre_production_471", "Pre-production §471 incurred"),
        field("production_471", "Production §471 incurred"),
        field("pre_production_additional_263A", "Pre-production additional §263A"),
        field("production_additional_263A", "Production additional §263A"),
        field("pre_production_471_on_hand", "Pre-production §471 on hand (current-year, (c)(3)(ii)(C))"),
        field("production_471_on_hand", "Production §471 on hand (current-year, (c)(3)(ii)(E))"),
        field("beginning_DM_not_yet_in_production", "Beginning DM not yet in production"),
        field("DM_purchased_during_year", "DM purchased during year"),
        field("ending_DM_not_yet_in_production", "Ending DM not yet in production"),
        field("lifo_current_year_increment_471", "LIFO current-year increment (§471) — combined-ratio multiplicand"),
        field("mspm_mixed_split_method", "Mixed split method ((c)(3)(iii)(B))", { type: "select",
          options: ["direct_material", "labor"], dflt: "direct_material" }),
        field("mspm_labor_split_proportion", "Labor split proportion (pre-production share, 0–1)")),
      el("div", { class: "grid", style: "margin-top:8px" },
        field("mspm_90pct_split_election", "(c)(3)(iii)(C) 90% split election", { type: "check" }))));

    root.appendChild(el("fieldset", {}, el("legend", {}, "HAR election (§1.263A-2(c)(4))"),
      el("div", { class: "grid" },
        field("har_preprod_ratio", "Frozen pre-production ratio"),
        field("har_production_ratio", "Frozen production ratio"),
        field("har_combined_ratio", "Frozen combined ratio (LIFO, (c)(4)(iii))"),
        field("har_qualifying_year_index", "Qualifying-year index (1–5; 6 = recomputation)")),
      el("div", { class: "grid", style: "margin-top:8px" },
        field("har_election", "HAR election in effect", { type: "check" }))));

    root.appendChild(el("fieldset", {}, el("legend", {}, "SRM balances (§1.263A-3(d)) — used when method = SRM"),
      el("div", { class: "grid" },
        field("purchasing_costs", "Purchasing costs (incl. (F) mixed-service share)"),
        field("current_year_471_costs", "Current year's purchases (§471)"),
        field("storage_handling_costs", "Storage & handling costs (incl. (F) share)"),
        field("beginning_inventory_471", "Beginning inventory §471 (LIFO carrying value if LIFO)"),
        field("ending_inventory_471_total_lifo", "TOTAL ending §471 at LIFO value (variation B multiplicand)")),
      el("div", { class: "grid", style: "margin-top:8px" },
        field("srm_variation_a", "Variation (A): exclude beginning inventory from S&H denominator", { type: "check" }),
        field("srm_variation_b", "Variation (B): S&H ratio × total ending §471 (LIFO)", { type: "check" }))));

    const derived = el("div", { class: "results" });
    root.appendChild(derived);
    function refreshDerived() {
      clear(derived);
      try {
        const p = currentProfile();
        derived.appendChild(el("h3", {}, "Derived"));
        derived.appendChild(kvTable([
          ["§448(c) threshold (TY " + p.tax_year + ")", E.sec448Threshold(p)],
          ["Threshold is an estimate (year not on file)", String(E.thresholdIsEstimate(p))],
          ["Small-business exempt — UNICAP off", String(E.smallBusinessExempt(p)), { hl: true }],
          ["De minimis safe-harbor ceiling (§1.263(a)-1(f))", E.deMinimisCeiling(p)],
        ]));
      } catch (err) {
        derived.appendChild(el("div", { class: "warn err" }, String(err)));
      }
    }
    refreshDerived();
  });

  /* ---- Import Files ---- */
  const I = window.CAP263A_INGEST;

  /** Generic header/column detector parameterized by a field->aliases map
   *  (mirrors ingest.js's own detectHeader, which is hardcoded to the TB
   *  fields) — lets every schedule in the app use the SAME alias-scoring
   *  algorithm, not just the trial balance. */
  function genericDetectHeader(rows, aliasMap) {
    const lookup = new Map();
    for (const field of Object.keys(aliasMap)) {
      for (const a of aliasMap[field]) {
        const n = I.normHeader(a);
        if (!lookup.has(n)) lookup.set(n, field);
      }
    }
    let best = { headerIndex: 0, mapping: {} }, bestScore = 0;
    const limit = Math.min(rows.length, 10);
    for (let r = 0; r < limit; r++) {
      const row = rows[r] || [];
      const mapping = {}, taken = new Set();
      let score = 0;
      for (let c = 0; c < row.length; c++) {
        const field = lookup.get(I.normHeader(row[c]));
        if (field && !taken.has(field)) { mapping[c] = field; taken.add(field); score++; }
      }
      if (score > bestScore) { best = { headerIndex: r, mapping }; bestScore = score; }
    }
    return best;
  }

  function genericRowsToObjects(rows, headerIndex, mapping) {
    const out = [];
    for (let r = headerIndex + 1; r < rows.length; r++) {
      const row = rows[r] || [];
      const nonEmpty = row.filter(c => c !== null && c !== undefined && String(c).trim() !== "").length;
      if (nonEmpty === 0) continue;
      const obj = {};
      for (const [ci, field] of Object.entries(mapping)) {
        const raw = row[Number(ci)];
        obj[field] = raw === null || raw === undefined ? "" : String(raw).trim();
      }
      if (Object.values(obj).every(v => v === "")) continue;
      out.push(obj);
    }
    return out;
  }

  function toBoolStr(v, dflt) {
    if (v === undefined || v === "") return dflt;
    const s = String(v).trim().toLowerCase();
    return ["true", "1", "yes", "y", "x"].includes(s);
  }

  /* Import destinations: every schedule the app models. Each entry's
   * `aliases` reuses the Python-derived alias tables from ingest.js where
   * one exists (btd/re/transaction_costs/intangibles/startup/
   * qualified_expenditures/debt/cip — ported verbatim from reader.py/
   * readers.py); the rest (lifo, sca pools/assets, tangible items) are new
   * schedules this UI introduces, given a matching alias table here. */
  const TANGIBLE_ALIASES = {
    item_id: ["item id", "id"], description: ["description"],
    amount: ["amount", "cost"],
    invoice_or_item_cost: ["invoice cost", "invoice or item cost", "per-item cost"],
    unit_of_property: ["unit of property", "uop"],
    is_building: ["is building", "building"],
    building_unadjusted_basis: ["building unadjusted basis", "building basis"],
    is_material_or_supply: ["materials and supplies", "materials & supplies", "m&s"],
    betterment: ["betterment"], adaptation: ["adaptation"],
    restoration: ["restoration"],
  };
  const LIFO_ALIASES = {
    year: ["year", "layer year"],
    layer_471: ["layer 471", "layer §471", "471 costs"],
    layer_additional_263a: ["layer additional 263a", "additional §263a"],
  };
  const SCA_POOL_ALIASES = {
    pool_id: ["pool id", "id"], description: ["description"],
    amount: ["amount"], driver: ["driver"],
    is_mixed_service: ["is mixed service", "mixed service"],
  };
  const SCA_ASSET_ALIASES = {
    asset_id: ["asset id", "id"], book_cost: ["book cost", "cost"],
    sscm_eligible: ["sscm eligible", "eligible"],
  };

  const IMPORT_TARGETS = [
    { key: "tb", label: "Trial Balance", aliases: I.TB_ALIASES,
      get: () => state.tb_lines,
      map: o => ({ acct_num: o.acct_num || "", acct_desc: o.acct_desc || "",
        cc_num: o.cc_num || "", cc_desc: o.cc_desc || "", amount: o.amount || "0",
        tier1: "Excluded", cap_vs_deduct: "", is_labor: false }) },
    { key: "btd", label: "Book-Tax Differences", aliases: I.SCHEDULE_ALIASES.btd,
      get: () => state.btds,
      map: o => ({ btd_id: o.btd_id || "", acct_num: o.acct_num || "",
        cc_num: o.cc_num || "", description: o.description || "",
        adjustment: o.adjustment || "0" }) },
    { key: "re", label: "§174 R&E Expenditures", aliases: I.SCHEDULE_ALIASES.re,
      get: () => state.s174.expenditures,
      map: o => ({ re_id: o.re_id || "", description: o.description || "",
        amount: o.amount || "0", domestic: toBoolStr(o.domestic, true),
        tax_year: o.tax_year || "", book_capitalized_amount: o.book_capitalized_amount || "0" }) },
    { key: "transaction_costs", label: "§1.263(a)-5 Transaction Costs",
      aliases: I.SCHEDULE_ALIASES.transaction_costs,
      get: () => state.intang.transaction_costs,
      map: o => ({ item_id: o.item_id || "", transaction_id: o.transaction_id || "",
        description: o.description || "", amount: o.amount || "0",
        covered_transaction: toBoolStr(o.covered_transaction, false),
        inherently_facilitative: toBoolStr(o.inherently_facilitative, false),
        success_based: toBoolStr(o.success_based, false),
        transaction_abandoned: toBoolStr(o.transaction_abandoned, false),
        incurred_date: o.incurred_date || "", bright_line_date: o.bright_line_date || "" }) },
    { key: "intangibles", label: "§1.263(a)-4 Intangibles",
      aliases: I.SCHEDULE_ALIASES.intangibles,
      get: () => state.intang.intangibles,
      map: o => ({ item_id: o.item_id || "", description: o.description || "",
        amount: o.amount || "0",
        acquired_with_business: toBoolStr(o.acquired_with_business, false),
        benefit_start: o.benefit_start || "", benefit_end: o.benefit_end || "",
        payment_year: o.payment_year || "",
        facilitative_costs: o.facilitative_costs || "0",
        prior_capitalized_basis: o.prior_capitalized_basis || "0" }) },
    { key: "startup", label: "§195/§248/§709 Start-up Pools",
      aliases: I.SCHEDULE_ALIASES.startup,
      get: () => state.intang.startup_pools,
      map: o => ({ pool_id: o.pool_id || "", kind: o.kind || "startup",
        total: o.total || "0", business_commencement: o.business_commencement || "" }) },
    { key: "qualified_expenditures", label: "§59(e) Elections",
      aliases: I.SCHEDULE_ALIASES.qualified_expenditures,
      get: () => state.s59e.elections,
      map: o => ({ item_id: o.item_id || "", category: o.category || "idc",
        amount: o.amount || "0", elected: toBoolStr(o.elected, true),
        election_year: o.election_year || "" }) },
    { key: "debt", label: "§263A(f) Debt Schedule", aliases: I.SCHEDULE_ALIASES.debt,
      get: () => state.interest.debts,
      map: o => {
        const screenKeys = ["related_party_below_afr", "non_interest_bearing",
          "personal_or_qualified_residence", "tax_exempt_org_nonbusiness",
          "disallowed_163_8T", "reserve_or_deferred_tax",
          "tax_liability_453a_460b", "sale_leaseback_purchase_money"];
        let screen = "";
        for (const k of screenKeys) if (toBoolStr(o[k], false)) { screen = k; break; }
        return { debt_id: o.debt_id || "", principal: o.principal || "0",
          interest_incurred: o.interest_incurred || "0",
          traced_to: o.traced_to || "", screen, outstanding_by_date: "" };
      } },
    { key: "cip", label: "§263A(f) Designated-Property Units", aliases: I.SCHEDULE_ALIASES.cip,
      get: () => state.interest.projects,
      map: o => ({ project_id: o.project_id || "",
        book_capitalized_interest: o.book_capitalized_interest || "0",
        is_common_feature: toBoolStr(o.is_common_feature, false) }) },
    { key: "lifo", label: "LIFO Layers", aliases: LIFO_ALIASES,
      get: () => state.lifo.layers,
      map: o => ({ year: o.year || "", layer_471: o.layer_471 || "0",
        layer_additional_263a: o.layer_additional_263a || "0" }) },
    { key: "sca_pools", label: "SCA Cost Pools", aliases: SCA_POOL_ALIASES,
      get: () => state.sca.pools,
      map: o => ({ pool_id: o.pool_id || "", description: o.description || "",
        amount: o.amount || "0", driver: o.driver || "",
        is_mixed_service: toBoolStr(o.is_mixed_service, false), targets: "" }) },
    { key: "sca_assets", label: "SCA Assets", aliases: SCA_ASSET_ALIASES,
      get: () => state.sca.assets,
      map: o => ({ asset_id: o.asset_id || "", book_cost: o.book_cost || "0",
        sscm_eligible: toBoolStr(o.sscm_eligible, false) }) },
    { key: "tangible", label: "§263(a) Tangible-Property Items", aliases: TANGIBLE_ALIASES,
      get: () => state.tangible.items,
      map: o => ({ item_id: o.item_id || "", description: o.description || "",
        amount: o.amount || "0",
        invoice_or_item_cost: o.invoice_or_item_cost || "",
        unit_of_property: o.unit_of_property || "",
        is_building: toBoolStr(o.is_building, false),
        building_unadjusted_basis: o.building_unadjusted_basis || "0",
        is_material_or_supply: toBoolStr(o.is_material_or_supply, false),
        betterment: "", adaptation: "", restoration: "" }) },
  ];

  panel("import", "Import Files", function (root) {
    root.appendChild(el("h2", {}, "Import Files — CSV / XLSX / JSON, any schedule"));
    root.appendChild(el("p", { class: "note" },
      "Fully offline: XLSX is parsed with a native ZIP/OOXML reader, CSV with " +
      "delimiter sniffing (comma/tab/semicolon/pipe), both reusing the SAME " +
      "column-alias tables as the Python reader (financial_tools/cap263a/" +
      "reader.py, readers.py) — so a real ERP export TB or schedule export " +
      "maps onto the right fields automatically. Preview the detected mapping " +
      "before appending; nothing imports silently. Not every schedule has a " +
      "dedicated tab yet — Fixed Assets uploads parse but currently have no " +
      "destination in this app (they seed the desktop tool's Asset Basis " +
      "Schedule / SCA targets, not modeled standalone)."));

    const destSel = el("select", {},
      IMPORT_TARGETS.map(t => el("option", { value: t.key }, t.label)));
    root.appendChild(el("label", { class: "f", style: "max-width:360px" },
      "Import into", destSel));
    const fileInput = el("input", { type: "file", multiple: "multiple",
      accept: ".csv,.tsv,.txt,.xlsx,.xlsm,.json" });
    root.appendChild(el("div", { style: "margin:8px 0" }, fileInput));
    const out = el("div", { class: "results" });
    root.appendChild(out);

    fileInput.addEventListener("change", async () => {
      clear(out);
      const target = IMPORT_TARGETS.find(t => t.key === destSel.value);
      for (const file of Array.from(fileInput.files)) {
        const box = el("div", {}, el("h3", {}, file.name));
        out.appendChild(box);
        try {
          const buf = await file.arrayBuffer();
          const ext = (file.name.split(".").pop() || "").toLowerCase();
          const isTextFmt = ["csv", "tsv", "txt", "json"].includes(ext);
          const data = isTextFmt ? new TextDecoder("utf-8").decode(buf) : buf;
          const parsed = await I.sniffAndParse(file.name, data);
          if (parsed.kind === "json") {
            box.appendChild(el("p", { class: "note" },
              "Parsed as a JSON engagement file. Full-engagement JSON import " +
              "(the multi-schedule format the Python CLI accepts) isn't wired " +
              "into this UI yet — showing the raw structure for reference."));
            box.appendChild(el("details", { class: "raw" },
              el("summary", {}, "Parsed JSON"),
              el("pre", {}, JSON.stringify(parsed.data, null, 2).slice(0, 20000))));
            continue;
          }
          for (const sheet of parsed.sheets) {
            const sheetBox = el("div", {},
              el("h4", { style: "margin:8px 0 2px" },
                parsed.sheets.length > 1 ? "Sheet: " + sheet.name : "Preview"));
            box.appendChild(sheetBox);
            const { headerIndex, mapping } = genericDetectHeader(sheet.rows, target.aliases);
            const fieldNames = Object.keys(target.aliases);
            const mappedCount = Object.keys(mapping).length;
            sheetBox.appendChild(el("p", { class: "note" },
              "Detected header row " + (headerIndex + 1) + "; matched " +
              mappedCount + " of " + fieldNames.length + " target fields (" +
              fieldNames.join(", ") + ")."));
            const objs = genericRowsToObjects(sheet.rows, headerIndex, mapping);
            const prev = el("table", { class: "io" });
            const headerRow = sheet.rows[headerIndex] || [];
            prev.appendChild(el("tr", {}, headerRow.map((h, ci) =>
              el("th", {}, String(h == null ? "" : h) +
                (mapping[ci] ? " → " + mapping[ci] : "")))));
            for (const row of sheet.rows.slice(headerIndex + 1, headerIndex + 6)) {
              prev.appendChild(el("tr", {}, headerRow.map((_, ci) =>
                el("td", {}, String(row[ci] == null ? "" : row[ci])))));
            }
            sheetBox.appendChild(el("div", { class: "tblwrap" }, prev));
            sheetBox.appendChild(el("button", { class: "act", onclick: () => {
              const arr = target.get();
              for (const o of objs) arr.push(target.map(o));
              save();
              alert("Imported " + objs.length + " row(s) into " + target.label +
                ". Open that tab to review/edit.");
            } }, "Import " + objs.length + " row(s) into " + target.label));
          }
        } catch (err) {
          box.appendChild(el("div", { class: "warn err" }, String(err)));
        }
      }
    });
  });

  /* ---- Interview ---- */
  const INTERVIEW_SPEC = JSON.parse(
    document.getElementById("interview-spec-data").textContent);

  function evalCond(c, answers) {
    if (c.any) return c.any.some(sub => evalCond(sub, answers));
    if (c.all) return c.all.every(sub => evalCond(sub, answers));
    if (c.derived) return derivedValue(c.derived, answers) === c.equals;
    const v = answers[c.question];
    if ("in" in c) return c.in.includes(v);
    return v === c.equals;
  }
  function derivedValue(name, answers) {
    const receipts = answers["Q0.4"];
    const taxYear = answers["Q0.2"] || 2026;
    const threshold = E.THRESHOLDS[taxYear] ? Number(E.THRESHOLDS[taxYear]) : 32000000;
    const under = receipts !== undefined && receipts !== "" && Number(receipts) <= threshold;
    if (name === "under_448c_threshold") return under;
    if (name === "small_business_exempt") return under && !answers["Q0.3"];
    if (name === "srm_available")
      return answers["Q1.2"] === "de_minimis" && !!answers["Q1.3"];
    return undefined;
  }
  function questionVisible(q, answers) {
    if (!q.show_if) return true;
    return q.show_if.every(c => evalCond(c, answers));
  }

  panel("interview", "Interview", function (root) {
    root.appendChild(el("h2", {}, "Guided Interview — every fact the calculations need"));
    root.appendChild(el("p", { class: "note" },
      "Mirrors the desktop tool's Phase E interview graph (" +
      INTERVIEW_SPEC.gates.reduce((n, g) => n + g.questions.length, 0) +
      " questions across " + INTERVIEW_SPEC.gates.length + " gates), plus a " +
      "new tangible-property gate. Questions appear only when relevant to " +
      "your prior answers. \"Apply to Profile\" copies mapped answers onto " +
      "the Entity Profile; \"Check completeness\" re-runs the same missing-" +
      "input checks the engines would otherwise only surface as a warning " +
      "AFTER computing."));

    const body = el("div", {});
    root.appendChild(body);

    function fieldFor(q) {
      const answers = state.interview_answers;
      const val = answers[q.id];
      let input;
      if (q.type === "bool") {
        input = el("select", { onchange: e => {
          answers[q.id] = e.target.value === "" ? undefined
            : e.target.value === "true"; save(); render(); } },
          [["", "— unanswered —"], ["true", "Yes"], ["false", "No"]].map(([v, l]) => {
            const o = el("option", { value: v }, l);
            const cur = val === undefined ? "" : String(val);
            if (cur === v) o.selected = true;
            return o;
          }));
      } else if (q.type === "choice") {
        input = el("select", { onchange: e => {
          answers[q.id] = e.target.value || undefined; save(); render(); } },
          [["", "— unanswered —"]].concat(q.choices.map(c => [c.value, c.label]))
            .map(([v, l]) => {
              const o = el("option", { value: v }, l);
              if ((val || "") === v) o.selected = true;
              return o;
            }));
      } else {
        input = el("input", { type: "text", value: val == null ? "" : val,
          oninput: e => { answers[q.id] = e.target.value; save(); },
          onchange: render });
      }
      return input;
    }

    function render() {
      clear(body);
      for (const g of INTERVIEW_SPEC.gates) {
        const visible = g.questions.filter(q => questionVisible(q, state.interview_answers));
        if (!visible.length) continue;
        const fs = el("fieldset", {}, el("legend", {}, g.title || g.id));
        for (const q of visible) {
          const row = el("div", { style: "margin-bottom:10px" },
            el("label", { class: "f" }, q.id + ". " + q.text, fieldFor(q)),
            q.help ? el("p", { class: "note", style: "margin:2px 0 0" }, q.help) : null);
          fs.appendChild(row);
        }
        body.appendChild(fs);
      }
      const actions = el("div", {});
      actions.appendChild(el("button", { class: "act", onclick: applyToProfile },
        "Apply answers to Profile"));
      actions.appendChild(el("button", { class: "act", onclick: () => {
        clear(checkOut);
        checkOut.appendChild(runCompletenessCheck());
      } }, "Check completeness"));
      body.appendChild(actions);
      body.appendChild(checkOut);
    }

    function applyToProfile() {
      let applied = 0;
      for (const g of INTERVIEW_SPEC.gates) {
        for (const q of g.questions) {
          const val = state.interview_answers[q.id];
          if (val === undefined || val === "") continue;
          const mt = q.maps_to || {};
          if (mt.profile_field) { state.profile[mt.profile_field] = val; applied++; }
        }
      }
      save();
      alert("Applied " + applied + " answer(s) to the Entity Profile.");
    }

    function runCompletenessCheck() {
      const box = el("div", {});
      box.appendChild(el("h3", {}, "Completeness"));
      let profile;
      try { profile = currentProfile(); }
      catch (err) {
        box.appendChild(el("div", { class: "warn err" }, String(err)));
        return box;
      }
      const fires = [];
      for (const c of INTERVIEW_SPEC.completeness || []) {
        const w = c.when || {};
        let matches = true;
        if ("profile_field" in w) matches = String(profile[w.profile_field]) === String(w.equals);
        if (!matches) continue;
        const missing = (c.then_required || []).filter(f => {
          const v = profile[f];
          return v === null || v === undefined || v === "" ||
            (v instanceof D && v.isZero());
        });
        if (missing.length) fires.push(c.question || ("Missing: " + missing.join(", ")));
      }
      if (!fires.length) {
        box.appendChild(el("p", { class: "note ok" },
          "No missing-input gaps detected for the current profile."));
      } else {
        for (const f of fires) box.appendChild(el("div", { class: "warn" }, "⚠ " + f));
      }
      return box;
    }

    const checkOut = el("div", { class: "results" });
    render();
  });

  /* ---- Trial balance & UNICAP ---- */
  panel("tb", "Trial Balance & UNICAP", function (root) {
    root.appendChild(el("h2", {}, "Trial Balance → Waterfall → §263A UNICAP"));
    root.appendChild(el("p", { class: "note" },
      "Assign each income-statement line a tier (the desktop tool's keyword " +
      "classifier does this automatically; here the analyst assigns — the same " +
      "review step every low-confidence line goes through anyway). Compute runs " +
      "the exact analyze() → SSCM → SPM/MSPM/SRM chain, gated on the profile's " +
      "§448(c) exemption."));

    const TIERS = E.TIER1_CHOICES.map(t => [t, t]);
    root.appendChild(ioTable(state.tb_lines, [
      { key: "acct_num", label: "Acct #", width: "70px" },
      { key: "acct_desc", label: "Description", width: "220px" },
      { key: "cc_desc", label: "Cost center", width: "120px" },
      { key: "amount", label: "Amount", type: "money", width: "110px" },
      { key: "tier1", label: "Tier", type: "select", options: TIERS, width: "190px" },
      { key: "cap_vs_deduct", label: "§263(a) tangible route", type: "select",
        options: [["", "—"], ["capitalize", "capitalize (BAR)"],
                  ["elective", "elective safe harbor"], ["deduct", "deduct"]],
        width: "150px" },
      { key: "is_labor", label: "Labor", type: "check", width: "50px" },
      { key: "is_income_tax", label: "Income-based tax", type: "check", width: "60px" },
    ], null, { tier1: "Excluded" }));

    const out = el("div", { class: "results" });
    root.appendChild(el("button", { class: "act", onclick: compute }, "Compute"));
    root.appendChild(out);

    function compute() {
      clear(out);
      try {
        const profile = currentProfile();
        const lines = state.tb_lines.map(l => ({
          acct_num: l.acct_num || "", acct_desc: l.acct_desc || "",
          cc_num: l.cc_num || "", cc_desc: l.cc_desc || "",
          amount: orZero(l.amount), tier1: l.tier1 || "Excluded",
          cap_vs_deduct: l.cap_vs_deduct || null, is_labor: !!l.is_labor,
          code: l.is_income_tax ? "NO-INCTAX" : "",
        }));
        const r = E.analyzeAssigned(lines, profile);
        const u = r.unicap;

        out.appendChild(el("h3", {}, "Capitalization waterfall"));
        const rows = [["Starting income-statement total", r.is_total, { hl: true }]];
        for (const b of E.CAPITALIZED_BUCKETS)
          rows.push(["  less: " + b, r.bucket_totals[b]]);
        rows.push(["  less: Mixed service — SSCM capitalized share",
          u.mixed_capitalized || D.zero()]);
        const totalCap = r.capitalized_total.plus(u.mixed_capitalized || D.zero());
        rows.push(["Total capitalized", totalCap, { hl: true }]);
        rows.push(["Mixed service — SSCM remaining deductible", u.mixed_deductible || D.zero()]);
        rows.push(["Deductible + Non-Operating (as classified)",
          r.deductible_total]);
        rows.push(["Adjusted currently-deductible",
          r.is_total.minus(totalCap), { hl: true }]);
        out.appendChild(kvTable(rows));

        out.appendChild(el("h3", {}, "§263A UNICAP (" + (u.exempt ? "exempt" : u.method) + ")"));
        if (u.exempt) {
          out.appendChild(el("p", { class: "note" }, u.note));
        } else {
          const kv = [
            ["SSCM allocation ratio (" + (u.method || "") + ")", u.mixed_alloc_ratio, "ratio"],
            ["Mixed capitalized to §263A", u.mixed_capitalized],
            ["Mixed remaining deductible", u.mixed_deductible],
          ];
          if (u.method === "MSPM") {
            kv.push(["Pre-production pool", u.pre_production_pool],
              ["Pre-production absorption ratio", u.pre_production_ratio, "ratio"],
              ["Residual pre-production §263A (rolls to production)", u.residual_pre_production_263A],
              ["Direct-materials adjustment", u.direct_materials_adjustment],
              ["Production pool", u.production_pool],
              ["Production absorption ratio", u.production_ratio, "ratio"],
              ["HAR applied", String(u.har_applied)]);
            if (u.lifo_combined_ratio !== null && u.lifo_combined_ratio !== undefined)
              kv.push(["LIFO combined absorption ratio", u.lifo_combined_ratio, "ratio"]);
          } else if (u.method === "SRM") {
            kv.push(["Purchasing ratio", u.purchasing_ratio, "ratio"],
              ["Storage & handling ratio", u.storage_handling_ratio, "ratio"],
              ["Combined ratio", u.combined_ratio, "ratio"],
              ["Method conflict (not a permissible position)", String(u.method_conflict)]);
          } else {
            kv.push(["§471 cost pool", u.sec471_pool],
              ["Additional §263A pool (incl. mixed)", u.additional_263a_pool],
              ["SPM absorption ratio", u.absorption_ratio, "ratio"]);
          }
          kv.push(["Additional §263A capitalized to ending inventory",
            u.additional_capitalized_to_inventory, { hl: true }]);
          kv.push(["Adjusted deductible after mixed allocation",
            u.adjusted_deductible_post]);
          out.appendChild(kvTable(kv));
        }

        out.appendChild(el("h3", {}, "Warnings"));
        out.appendChild(warnList([...(r.bucket_warnings || []), ...((u.warnings) || [])]));
        out.appendChild(rawDetails({ bucket_totals: r.bucket_totals, unicap: u }));
      } catch (err) {
        out.appendChild(el("div", { class: "warn err" }, String(err)));
      }
      save();
    }
  });

  /* ---- Tangible §263(a) ---- */
  panel("tangible", "§263(a) Tangible Property", function (root) {
    root.appendChild(el("h2", {}, "§263(a) Tangible Property — Capitalize vs. Deduct"));
    root.appendChild(el("p", { class: "note" },
      "Repair regulations decision order: negative-amount guard → de minimis " +
      "safe harbor (§1.263(a)-1(f)) → materials & supplies (§1.162-3) → small " +
      "taxpayer building safe harbor (§1.263(a)-3(h)) → betterment/adaptation/" +
      "restoration (BAR) tests (§1.263(a)-3(j)/(l)/(k)) → routine maintenance " +
      "safe harbor (§1.263(a)-3(i)) → repair (§162) or the §1.263(a)-3(n) " +
      "capitalize-per-books election. Leave a BAR/safe-harbor cell blank when " +
      "the fact is unknown — the engine capitalizes CONSERVATIVELY and asks " +
      "an explicit question rather than guessing; it never silently deducts " +
      "on a missing fact."));

    const TRI = [["", "— unknown —"], ["true", "Yes"], ["false", "No"]];
    root.appendChild(ioTable(state.tangible.items, [
      { key: "item_id", label: "Id", width: "70px" },
      { key: "description", label: "Description", width: "180px" },
      { key: "amount", label: "Amount", type: "money", width: "100px" },
      { key: "invoice_or_item_cost", label: "Invoice/item cost (de minimis)", type: "money", width: "110px" },
      { key: "unit_of_property", label: "Unit of property", width: "100px" },
      { key: "is_building", label: "Building", type: "check", width: "55px" },
      { key: "building_unadjusted_basis", label: "Building unadj. basis", type: "money", width: "110px" },
      { key: "is_material_or_supply", label: "M&S candidate", type: "check", width: "60px" },
      { key: "ms_unit_cost_200_or_less", label: "M&S: unit cost ≤$200?", type: "select", options: TRI, width: "110px" },
      { key: "ms_economic_life_12mo_or_less", label: "M&S: life ≤12mo?", type: "select", options: TRI, width: "100px" },
      { key: "betterment", label: "Betterment?", type: "select", options: TRI, width: "100px" },
      { key: "adaptation", label: "Adaptation?", type: "select", options: TRI, width: "100px" },
      { key: "restoration", label: "Restoration?", type: "select", options: TRI, width: "100px" },
      { key: "routine_maintenance_expected_more_than_once", label: "Routine maint. >1x?",
        type: "select", options: TRI, width: "110px" },
      { key: "book_capitalized", label: "Book capitalized", type: "check", width: "60px" },
    ]));

    const O = state.tangible.opts;
    root.appendChild(el("div", { class: "grid", style: "max-width:1000px" },
      el("label", { class: "chk" },
        el("input", { type: "checkbox", checked: !!O.de_minimis_election,
          onchange: e => { O.de_minimis_election = e.target.checked; save(); } }),
        "§1.263(a)-1(f) de minimis safe harbor election (annual, irrevocable)"),
      el("label", { class: "chk" },
        el("input", { type: "checkbox", checked: !!O.small_taxpayer_building_election,
          onchange: e => { O.small_taxpayer_building_election = e.target.checked; save(); } }),
        "§1.263(a)-3(h) small taxpayer building safe harbor election"),
      el("label", { class: "chk" },
        el("input", { type: "checkbox", checked: !!O.capitalize_repairs_following_books,
          onchange: e => { O.capitalize_repairs_following_books = e.target.checked; save(); } }),
        "§1.263(a)-3(n) capitalize repairs per books election"),
      el("label", { class: "f" },
        "Per-building TRUE aggregate override (unit_of_property=total, one per line — overrides the schedule-only fallback)",
        el("textarea", { rows: 2,
          value: O.total_building_repairs_maintenance_improvements || "",
          oninput: e => { O.total_building_repairs_maintenance_improvements = e.target.value; save(); } }))));

    const out = el("div", { class: "results" });
    root.appendChild(el("button", { class: "act", onclick: () => {
      clear(out);
      try {
        const profile = currentProfile();
        const items = state.tangible.items.map(it => ({
          item_id: it.item_id || "", description: it.description || "",
          amount: orZero(it.amount),
          invoice_or_item_cost: it.invoice_or_item_cost === "" || it.invoice_or_item_cost == null
            ? null : it.invoice_or_item_cost,
          unit_of_property: it.unit_of_property || "",
          is_building: !!it.is_building,
          building_unadjusted_basis: orZero(it.building_unadjusted_basis),
          is_material_or_supply: !!it.is_material_or_supply,
          ms_unit_cost_200_or_less: it.ms_unit_cost_200_or_less === "" || it.ms_unit_cost_200_or_less == null
            ? null : it.ms_unit_cost_200_or_less === "true" || it.ms_unit_cost_200_or_less === true,
          ms_economic_life_12mo_or_less: it.ms_economic_life_12mo_or_less === "" || it.ms_economic_life_12mo_or_less == null
            ? null : it.ms_economic_life_12mo_or_less === "true" || it.ms_economic_life_12mo_or_less === true,
          routine_maintenance_expected_more_than_once:
            it.routine_maintenance_expected_more_than_once === "" || it.routine_maintenance_expected_more_than_once == null
              ? null : it.routine_maintenance_expected_more_than_once === "true" || it.routine_maintenance_expected_more_than_once === true,
          betterment: it.betterment === "" || it.betterment == null
            ? null : it.betterment === "true" || it.betterment === true,
          adaptation: it.adaptation === "" || it.adaptation == null
            ? null : it.adaptation === "true" || it.adaptation === true,
          restoration: it.restoration === "" || it.restoration == null
            ? null : it.restoration === "true" || it.restoration === true,
          book_capitalized: !!it.book_capitalized,
        }));
        const tbrmi = parseKV(O.total_building_repairs_maintenance_improvements);
        const r = E.computeTangible263a(items, profile, {
          de_minimis_election: !!O.de_minimis_election,
          small_taxpayer_building_election: !!O.small_taxpayer_building_election,
          capitalize_repairs_following_books: !!O.capitalize_repairs_following_books,
          total_building_repairs_maintenance_improvements:
            Object.keys(tbrmi).length ? tbrmi : null });

        out.appendChild(kvTable([
          ["Deductible total", r.deductible_total, { hl: true }],
          ["Capitalized total (mandatory improvements + pending)", r.capitalized_total, { hl: true }],
          ["Elective capitalized total ((n) election)", r.elective_capitalized_total],
        ]));

        if (r.open_questions.length) {
          out.appendChild(el("h3", {}, "Open questions — answer these to finalize the treatment"));
          for (const q of r.open_questions) {
            out.appendChild(el("div", { class: "warn" },
              "❓ " + q.question, el("div", { class: "note", style: "margin-top:4px" }, q.why)));
          }
        }

        out.appendChild(el("h3", {}, "Items"));
        const t = el("table", { class: "io" });
        t.appendChild(el("tr", {}, el("th", {}, "Item"), el("th", {}, "Amount"),
          el("th", {}, "Treatment"), el("th", {}, "Authority"),
          el("th", {}, "Deductible"), el("th", {}, "Capitalized"), el("th", {}, "Flags")));
        for (const row of r.items) {
          t.appendChild(el("tr", {},
            el("td", {}, (row.item_id || "") + " " + (row.description || "")),
            el("td", { class: "num" }, "$" + E.fmt(row.amount, 2)),
            el("td", {}, row.treatment),
            el("td", {}, row.authority),
            el("td", { class: "num" }, "$" + E.fmt(row.deductible, 2)),
            el("td", { class: "num" }, "$" + E.fmt(row.capitalized, 2)),
            el("td", {}, (row.flags || []).join(", "))));
        }
        out.appendChild(el("div", { class: "tblwrap" }, t));
        out.appendChild(el("h3", {}, "Warnings"));
        out.appendChild(warnList(r.warnings));
        out.appendChild(rawDetails(r));
      } catch (err) {
        out.appendChild(el("div", { class: "warn err" }, String(err)));
      }
    } }, "Compute"));
    root.appendChild(out);
  });

  /* ---- Tax-basis TB ---- */
  panel("taxtb", "Tax-Basis TB (BTDs)", function (root) {
    root.appendChild(el("h2", {}, "Book-Tax Differences → Tax-Basis Trial Balance"));
    root.appendChild(el("p", { class: "note" },
      "Applies each signed TAX-minus-BOOK adjustment to its matching TB line " +
      "(exact acct+cc match first, then acct-only when unambiguous). Unmatched " +
      "BTDs become standalone [BTD] tax-only lines — the classifier holds those " +
      "in Deductible with a REVIEW flag."));

    root.appendChild(el("h3", {}, "Book-tax differences"));
    root.appendChild(ioTable(state.btds, [
      { key: "btd_id", label: "BTD id", width: "70px" },
      { key: "acct_num", label: "Acct #", width: "80px" },
      { key: "cc_num", label: "CC # (blank = acct-only match)", width: "110px" },
      { key: "description", label: "Description" },
      { key: "adjustment", label: "Adjustment (tax − book)", type: "money", width: "130px" },
    ]));

    const out = el("div", { class: "results" });
    root.appendChild(el("button", { class: "act", onclick: compute },
      "Compute tax-basis TB"));
    root.appendChild(el("button", { class: "act", onclick: adopt },
      "Adopt tax lines into Trial Balance tab"));
    root.appendChild(out);

    let lastResult = null;
    function tbInput() {
      return state.tb_lines.map(l => ({ acct_num: l.acct_num || "",
        acct_desc: l.acct_desc || "", cc_num: l.cc_num || "",
        cc_desc: l.cc_desc || "", amount: orZero(l.amount),
        tier1: l.tier1, cap_vs_deduct: l.cap_vs_deduct, is_labor: l.is_labor,
        code: l.is_income_tax ? "NO-INCTAX" : "" }));
    }
    function compute() {
      clear(out);
      try {
        lastResult = E.computeTaxBasisTB(tbInput(), state.btds.map(b => ({
          btd_id: b.btd_id || "", acct_num: b.acct_num || "",
          cc_num: b.cc_num || "", description: b.description || "",
          adjustment: orZero(b.adjustment) })));
        const m1 = lastResult.m1_reconciliation;
        out.appendChild(el("h3", {}, "M-1 reconciliation"));
        out.appendChild(kvTable([
          ["Book total", m1.book_total],
          ["Σ BTD adjustments", m1.btd_total],
          ["Tax-basis total", m1.tax_total, { hl: true }],
          ["Tie check (must be 0)", m1.tie_check,
            { hl: !m1.tie_check.isZero() }],
        ]));
        out.appendChild(el("h3", {}, "Tax-basis lines"));
        const t = el("table", { class: "io" });
        t.appendChild(el("tr", {}, el("th", {}, "Acct #"), el("th", {}, "Description"),
          el("th", {}, "CC"), el("th", {}, "Tax amount")));
        for (const l of lastResult.tax_lines) {
          t.appendChild(el("tr", {}, el("td", {}, l.acct_num),
            el("td", {}, l.acct_desc), el("td", {}, l.cc_num),
            el("td", { class: "num" }, "$" + E.fmt(l.amount, 2))));
        }
        out.appendChild(el("div", { class: "tblwrap" }, t));
        out.appendChild(el("h3", {}, "Warnings"));
        out.appendChild(warnList(lastResult.warnings));
      } catch (err) {
        out.appendChild(el("div", { class: "warn err" }, String(err)));
      }
    }
    function adopt() {
      if (!lastResult) compute();
      if (!lastResult) return;
      state.tb_lines = lastResult.tax_lines.map(l => ({
        acct_num: l.acct_num, acct_desc: l.acct_desc, cc_num: l.cc_num,
        cc_desc: "", amount: l.amount.toString(),
        tier1: (l.tier1 || (String(l.acct_desc).startsWith("[BTD]") ? "Excluded" : "Excluded")),
        cap_vs_deduct: l.cap_vs_deduct || "", is_labor: !!l.is_labor,
        is_income_tax: l.code === "NO-INCTAX" }));
      save();
      alert("Tax-basis lines copied to the Trial Balance tab (" +
        state.tb_lines.length + " lines). Re-assign tiers for any new [BTD] lines.");
      show("tb");
    }
  });

  /* ---- LIFO decrement ---- */
  panel("lifo", "LIFO Decrement Release", function (root) {
    root.appendChild(el("h2", {}, "LIFO Decrement — §263A Release to COGS"));
    root.appendChild(el("p", { class: "note" },
      "§1.263A-2(b)(3)(iii)(C): layers liquidate LAST-first; released = layer's " +
      "additional §263A × (liquidated §471 ÷ layer §471). List layers oldest " +
      "first — the calculator consumes from the bottom of the list."));
    root.appendChild(ioTable(state.lifo.layers, [
      { key: "year", label: "Layer year", width: "90px" },
      { key: "layer_471", label: "Layer §471 costs", type: "money" },
      { key: "layer_additional_263a", label: "Layer additional §263A", type: "money" },
    ]));
    const dec = el("input", { type: "text", value: state.lifo.decrement || "",
      oninput: e => { state.lifo.decrement = e.target.value; save(); } });
    root.appendChild(el("label", { class: "f", style: "max-width:260px" },
      "Decrement (positive §471 dollars)", dec));
    const out = el("div", { class: "results" });
    root.appendChild(el("button", { class: "act", onclick: () => {
      clear(out);
      try {
        const r = E.computeLifoDecrementRelease(
          state.lifo.layers.map(l => ({ year: l.year,
            layer_471: D.from(orZero(l.layer_471)),
            layer_additional_263a: D.from(orZero(l.layer_additional_263a)) })),
          orZero(state.lifo.decrement));
        out.appendChild(kvTable([
          ["Released §263A to COGS", r.released_263a_to_cogs, { hl: true }],
          ["Unabsorbed decrement", r.unabsorbed_decrement],
        ]));
        out.appendChild(el("h3", {}, "Layer detail (LIFO order)"));
        const t = el("table", { class: "io" });
        t.appendChild(el("tr", {}, el("th", {}, "Year"), el("th", {}, "Liquidated §471"),
          el("th", {}, "Released §263A")));
        for (const l of r.layers) {
          t.appendChild(el("tr", {}, el("td", {}, String(l.year ?? "")),
            el("td", { class: "num" }, "$" + E.fmt(l.liquidated_471, 2)),
            el("td", { class: "num" }, "$" + E.fmt(l.released_263a, 2))));
        }
        out.appendChild(el("div", { class: "tblwrap" }, t));
        out.appendChild(el("h3", {}, "Warnings"));
        out.appendChild(warnList(r.warnings));
      } catch (err) {
        out.appendChild(el("div", { class: "warn err" }, String(err)));
      }
    } }, "Compute"));
    root.appendChild(out);
  });

  /* ---- §263A(f) interest ---- */
  panel("interest", "§263A(f) Interest", function (root) {
    root.appendChild(el("h2", {}, "§263A(f) Avoided-Cost Interest (§§1.263A-8/-9)"));
    root.appendChild(el("p", { class: "note" },
      "Snapshot-then-average: excess_d = max(0, APE_d − traced debt_d) at each " +
      "measurement date; average excess × WAIR = excess expenditure amount. " +
      "Traced interest always capitalizes in full; the (c)(7) cap prorates only " +
      "the excess pool. Note: the §263A(i) small-business exemption covers ALL " +
      "of §263A including (f) — check the Entity Profile before relying on this."));

    root.appendChild(el("h3", {}, "Designated-property units"));
    root.appendChild(ioTable(state.interest.projects, [
      { key: "project_id", label: "Unit id", width: "110px" },
      { key: "book_capitalized_interest", label: "Book (ASC 835-20) capitalized interest", type: "money" },
      { key: "is_common_feature", label: "Common feature (§1.263A-10, flag only)", type: "check", width: "80px" },
    ]));
    root.appendChild(el("h3", {}, "APE snapshots (one row per unit × measurement date)"));
    root.appendChild(ioTable(state.interest.snapshots, [
      { key: "project_id", label: "Unit id", width: "110px" },
      { key: "measurement_date", label: "Measurement date", type: "date", width: "150px" },
      { key: "cumulative_ape", label: "Cumulative APE at that date", type: "money" },
    ]));
    root.appendChild(el("h3", {}, "Debt schedule"));
    root.appendChild(ioTable(state.interest.debts, [
      { key: "debt_id", label: "Debt id", width: "80px" },
      { key: "principal", label: "Principal (avg-outstanding fallback)", type: "money" },
      { key: "interest_incurred", label: "Interest incurred", type: "money" },
      { key: "traced_to", label: "Traced to unit (§1.163-8T)", width: "110px" },
      { key: "screen", label: "§1.263A-9(a)(4) exclusion screen", type: "select", width: "230px",
        options: [["", "— eligible —"],
          ["disallowed_163_8T", "§1.163-8T(m)(7)(ii) disallowed"],
          ["related_party_below_afr", "related-party below-AFR"],
          ["personal_or_qualified_residence", "personal / qualified residence"],
          ["tax_exempt_org_nonbusiness", "tax-exempt org non-business"],
          ["reserve_or_deferred_tax", "reserve / deferred-tax liability"],
          ["tax_liability_453a_460b", "tax liability / §453A / §460(b)"],
          ["sale_leaseback_purchase_money", "sale-leaseback purchase-money"],
          ["non_interest_bearing", "non-interest-bearing (A/P etc.)"]] },
      { key: "outstanding_by_date", label: "Dated balances (date=amount per line)",
        type: "textarea", placeholder: "2026-03-31=600000\n2026-06-30=800000" },
    ]));
    const O = state.interest.opts;
    root.appendChild(el("div", { class: "grid", style: "max-width:760px" },
      el("label", { class: "f" }, "Highest AFR (fallback rate, e.g. 0.06)",
        el("input", { type: "text", value: O.afr_highest || "",
          oninput: e => { O.afr_highest = e.target.value; save(); } })),
      el("label", { class: "f" }, "Below-AFR related-party interest available",
        el("input", { type: "text", value: O.below_afr_interest || "",
          oninput: e => { O.below_afr_interest = e.target.value; save(); } })),
      el("label", { class: "f" }, "§707(c) guaranteed payments available",
        el("input", { type: "text", value: O.guaranteed_payments || "",
          oninput: e => { O.guaranteed_payments = e.target.value; save(); } }))));

    const out = el("div", { class: "results" });
    root.appendChild(el("button", { class: "act", onclick: () => {
      clear(out);
      try {
        const projects = state.interest.projects.map(p => ({
          project_id: p.project_id || "",
          is_common_feature: !!p.is_common_feature,
          book_capitalized_interest: orZero(p.book_capitalized_interest),
          snapshots: state.interest.snapshots
            .filter(s => (s.project_id || "") === (p.project_id || ""))
            .map(s => ({ measurement_date: s.measurement_date || null,
              cumulative_ape: orZero(s.cumulative_ape) })) }));
        const debts = state.interest.debts.map(d => {
          const nd = { debt_id: d.debt_id || "", description: d.debt_id || "",
            principal: orZero(d.principal),
            interest_incurred: orZero(d.interest_incurred),
            traced_to: d.traced_to || "",
            outstanding_by_date: parseKV(d.outstanding_by_date) };
          if (d.screen) nd[d.screen] = true;
          return nd;
        });
        const r = E.compute263af(projects, debts, {
          afr_highest: O.afr_highest || null,
          below_afr_interest: orZero(O.below_afr_interest),
          guaranteed_payments: orZero(O.guaranteed_payments) });
        out.appendChild(kvTable([
          ["WAIR (" + r.wair_source + ")", r.wair, "ratio"],
          ["Total traced interest capitalized", r.total_traced],
          ["Total excess expenditure amount", r.total_excess],
          ["TOTAL §263A(f) capitalized", r.total_capitalized, { hl: true }],
          ["Prorated under the (c)(7) cap", String(r.prorated)],
        ]));
        out.appendChild(el("h3", {}, "Per unit"));
        const t = el("table", { class: "io" });
        t.appendChild(el("tr", {}, el("th", {}, "Unit"), el("th", {}, "Avg excess"),
          el("th", {}, "Excess amount"), el("th", {}, "Traced interest"),
          el("th", {}, "Total capitalized"), el("th", {}, "Tax delta to post")));
        for (const [pid, u] of Object.entries(r.per_unit)) {
          t.appendChild(el("tr", {}, el("td", {}, pid),
            el("td", { class: "num" }, "$" + E.fmt(u.average_excess, 2)),
            el("td", { class: "num" }, "$" + E.fmt(u.excess_expenditure_amount, 2)),
            el("td", { class: "num" }, "$" + E.fmt(u.traced_interest, 2)),
            el("td", { class: "num" }, "$" + E.fmt(u.total_capitalized, 2)),
            el("td", { class: "num" }, "$" + E.fmt(u.tax_delta_to_post, 2))));
        }
        out.appendChild(el("div", { class: "tblwrap" }, t));
        out.appendChild(el("h3", {}, "Per-source consumption (informational)"));
        const c = r.consumption;
        out.appendChild(kvTable([
          ["Nontraced interest consumed", c.nontraced_consumed],
          ["Below-AFR consumed", c.below_afr_consumed],
          ["Guaranteed payments consumed", c.guaranteed_payments_consumed],
          ["Nontraced remaining deductible", c.nontraced_remaining_deductible],
          ["Unsourced excess (tie check)", c.unsourced_excess],
        ]));
        out.appendChild(el("h3", {}, "Warnings"));
        out.appendChild(warnList(r.warnings));
        out.appendChild(rawDetails(r));
      } catch (err) {
        out.appendChild(el("div", { class: "warn err" }, String(err)));
      }
    } }, "Compute"));
    root.appendChild(out);
  });

  /* ---- SCA ---- */
  panel("sca", "Self-Constructed Assets", function (root) {
    root.appendChild(el("h2", {}, "Self-Constructed Assets — Additional §263A Allocation (bucket B)"));
    root.appendChild(el("p", { class: "note" },
      "Driver-splits each indirect/mixed-service pool across its declared " +
      "targets, then gates mixed-service shares through §1.263A-1(h)(2) SSCM " +
      "eligibility. Ineligible shares are computed but NOT booked " +
      "(SSCM-INELIGIBLE-NO-FALLBACK). Targets: one 'target=driver value' per " +
      "line; use NON_PRODUCTION for the non-production share."));
    root.appendChild(el("h3", {}, "Assets"));
    root.appendChild(ioTable(state.sca.assets, [
      { key: "asset_id", label: "Asset id", width: "110px" },
      { key: "book_cost", label: "Book/CIP cost (bucket A)", type: "money" },
      { key: "sscm_eligible", label: "SSCM eligible (§1.263A-1(h)(2) route C/D)", type: "check", width: "90px" },
    ]));
    root.appendChild(el("h3", {}, "Cost pools"));
    root.appendChild(ioTable(state.sca.pools, [
      { key: "pool_id", label: "Pool id", width: "80px" },
      { key: "description", label: "Description", width: "200px" },
      { key: "amount", label: "Amount", type: "money", width: "110px" },
      { key: "driver", label: "Driver", type: "select", width: "140px",
        options: E.SCA_DRIVERS.drivers.map(d => [d, d]) },
      { key: "is_mixed_service", label: "Mixed service", type: "check", width: "60px" },
      { key: "targets", label: "Targets (target=value per line)", type: "textarea",
        placeholder: "A1=6000\nNON_PRODUCTION=1000" },
    ]));
    const rat = el("input", { type: "text", value: state.sca.sscm_ratio || "",
      oninput: e => { state.sca.sscm_ratio = e.target.value; save(); } });
    root.appendChild(el("label", { class: "f", style: "max-width:260px" },
      "SSCM ratio (from the UNICAP tab's computation)", rat));
    const out = el("div", { class: "results" });
    root.appendChild(el("button", { class: "act", onclick: () => {
      clear(out);
      try {
        const pools = state.sca.pools.map(p => ({ pool_id: p.pool_id || "",
          description: p.description || "", amount: orZero(p.amount),
          driver: p.driver || "", is_mixed_service: !!p.is_mixed_service,
          targets: parseKV(p.targets) }));
        const assets = state.sca.assets.map(a => ({ asset_id: a.asset_id || "",
          book_cost: orZero(a.book_cost), sscm_eligible: !!a.sscm_eligible }));
        const r = E.computeSCA(pools, assets, orZero(state.sca.sscm_ratio), {});
        out.appendChild(el("h3", {}, "Per asset"));
        const t = el("table", { class: "io" });
        t.appendChild(el("tr", {}, el("th", {}, "Asset"), el("th", {}, "Book cost (A)"),
          el("th", {}, "Indirect §263A"), el("th", {}, "Mixed §263A"),
          el("th", {}, "Additional §263A (B)"), el("th", {}, "Adjusted basis pre-interest / APE")));
        for (const [aid, a] of Object.entries(r.per_asset)) {
          t.appendChild(el("tr", {}, el("td", {}, aid),
            el("td", { class: "num" }, "$" + E.fmt(a.book_cost, 2)),
            el("td", { class: "num" }, "$" + E.fmt(a.indirect_263a, 2)),
            el("td", { class: "num" }, "$" + E.fmt(a.mixed_263a, 2)),
            el("td", { class: "num" }, "$" + E.fmt(a.additional_263a, 2)),
            el("td", { class: "num" }, "$" + E.fmt(a.adjusted_basis_pre_interest, 2))));
        }
        out.appendChild(el("div", { class: "tblwrap" }, t));
        out.appendChild(kvTable([
          ["Deductible (NON_PRODUCTION + mixed remainder)", r.deductible_total],
          ["Not booked (ineligible / unknown targets)", r.not_booked_total],
          ["Conservation checks all tie", String(r.conservation_checks.every(c => c.ok))],
        ]));
        out.appendChild(el("h3", {}, "Warnings"));
        out.appendChild(warnList(r.warnings));
        out.appendChild(rawDetails(r));
      } catch (err) {
        out.appendChild(el("div", { class: "warn err" }, String(err)));
      }
    } }, "Compute"));
    root.appendChild(out);
  });

  /* ---- §174 ---- */
  panel("s174", "§174 / §174A R&E", function (root) {
    root.appendChild(el("h2", {}, "§174/§174A Research & Experimental (post-OBBBA)"));
    root.appendChild(el("p", { class: "note" },
      "Foreign research: mandatory 180-month capitalization. Domestic: default " +
      "expensing under §174A(a), or the elective §174A(c) ≥60-month " +
      "capitalization (a method of accounting). Includes the 2022-2024 " +
      "remaining-basis catch-up and the §448(c) retroactive-election conflict " +
      "guard."));
    root.appendChild(ioTable(state.s174.expenditures, [
      { key: "re_id", label: "Id", width: "70px" },
      { key: "description", label: "Description" },
      { key: "amount", label: "Amount", type: "money", width: "120px" },
      { key: "domestic", label: "Domestic", type: "check", width: "60px" },
      { key: "tax_year", label: "Year incurred", width: "90px" },
      { key: "book_capitalized_amount", label: "Book capitalized", type: "money", width: "120px" },
    ], null, { domestic: true }));
    const O = state.s174.opts;
    root.appendChild(el("div", { class: "grid", style: "max-width:900px" },
      el("label", { class: "chk" },
        el("input", { type: "checkbox", checked: !!O.domestic_capitalization_election,
          onchange: e => { O.domestic_capitalization_election = e.target.checked; save(); } }),
        "§174A(c) domestic capitalization election"),
      el("label", { class: "f" }, "Elected period (months, ≥60)",
        el("input", { type: "text", value: O.elected_period_months || "",
          oninput: e => { O.elected_period_months = e.target.value; save(); } })),
      el("label", { class: "f" }, "2022-24 catch-up method",
        el("select", { onchange: e => { O.catchup_method = e.target.value; save(); } },
          [["", "— none —"], ["one_year", "one year"], ["two_year", "two years (50/50)"]]
            .map(([v, l]) => { const o = el("option", { value: v }, l);
              if ((O.catchup_method || "") === v) o.selected = true; return o; }))),
      el("label", { class: "f" }, "Remaining 2022-24 domestic basis",
        el("input", { type: "text", value: O.remaining_2022_2024_basis || "",
          oninput: e => { O.remaining_2022_2024_basis = e.target.value; save(); } })),
      el("label", { class: "chk" },
        el("input", { type: "checkbox", checked: !!O.small_business_retroactive,
          onchange: e => { O.small_business_retroactive = e.target.checked; save(); } }),
        "§448(c) small-business retroactive election (amend 2022-24)"),
      el("label", { class: "f" }, "Disposal events (R&E ids, comma-separated)",
        el("input", { type: "text", value: O.disposal_events || "",
          oninput: e => { O.disposal_events = e.target.value; save(); } }))));
    const out = el("div", { class: "results" });
    root.appendChild(el("button", { class: "act", onclick: () => {
      clear(out);
      try {
        const r = E.compute174(state.s174.expenditures.map(x => ({
          re_id: x.re_id || "", description: x.description || "",
          amount: orZero(x.amount), domestic: !!x.domestic,
          tax_year: parseInt(x.tax_year, 10) || 0,
          book_capitalized_amount: orZero(x.book_capitalized_amount) })), {
          current_tax_year: (currentProfile().tax_year || 2026),
          domestic_capitalization_election: !!O.domestic_capitalization_election,
          elected_period_months: parseInt(O.elected_period_months, 10) || 60,
          catchup_method: O.catchup_method || null,
          remaining_2022_2024_basis: orZero(O.remaining_2022_2024_basis),
          small_business_retroactive: !!O.small_business_retroactive,
          disposal_events: parseList(O.disposal_events) });
        out.appendChild(kvTable([
          ["Current-year deduction (expensing + catch-up)", r.current_year_deduction, { hl: true }],
          ["Capitalized basis posted (post-reconciliation)", r.capitalized_total, { hl: true }],
          ["Catch-up — current year", r.catchup.current_year_deduction],
          ["Catch-up — following year", r.catchup.following_year_deduction],
        ]));
        out.appendChild(renderAmortTable(r.amortizable_items));
        out.appendChild(el("h3", {}, "Warnings"));
        out.appendChild(warnList(r.warnings));
        out.appendChild(rawDetails(r));
      } catch (err) {
        out.appendChild(el("div", { class: "warn err" }, String(err)));
      }
    } }, "Compute"));
    root.appendChild(out);
  });

  function renderAmortTable(items) {
    const box = el("div", {});
    box.appendChild(el("h3", {}, "Basis & amortization schedule"));
    if (!items.length) {
      box.appendChild(el("p", { class: "note" }, "No amortizable items posted."));
      return box;
    }
    const t = el("table", { class: "io" });
    t.appendChild(el("tr", {}, el("th", {}, "Item"), el("th", {}, "Category"),
      el("th", {}, "Basis"), el("th", {}, "Months"), el("th", {}, "Convention"),
      el("th", {}, "Year-1 amortization"), el("th", {}, "Flags")));
    for (const it of items) {
      t.appendChild(el("tr", {},
        el("td", {}, (it.item_id || "") + " " + (it.description || "")),
        el("td", {}, it.category || ""),
        el("td", { class: "num" }, "$" + E.fmt(it.basis, 2)),
        el("td", { class: "num" }, it.recovery_months == null ? "—" : String(it.recovery_months)),
        el("td", {}, it.convention || ""),
        el("td", { class: "num" }, "$" + E.fmt(E.firstYearAmortization(it), 2)),
        el("td", {}, (it.flags || []).join(", "))));
    }
    box.appendChild(el("div", { class: "tblwrap" }, t));
    return box;
  }

  /* ---- Intangibles / transaction costs / start-up / §280B ---- */
  panel("intang", "§263(a)-4/-5 & Start-up", function (root) {
    root.appendChild(el("h2", {}, "Transaction Costs, Intangibles, Start-up/Org, §280B"));
    root.appendChild(el("p", { class: "note" },
      "§1.263(a)-5 bright-line/facilitative routing (incl. the Rev. Proc. " +
      "2011-29 70/30 success-fee election and abandoned-transaction losses); " +
      "§1.263(a)-4 12-month rule and the $5,000 facilitative cliff (commissions " +
      "always capitalize); §195/§248/§709 pools with the $50,000 phase-out; " +
      "§280B demolition routing."));

    root.appendChild(el("h3", {}, "§1.263(a)-5 transaction costs"));
    root.appendChild(ioTable(state.intang.transaction_costs, [
      { key: "item_id", label: "Id", width: "60px" },
      { key: "transaction_id", label: "Deal", width: "80px" },
      { key: "description", label: "Description" },
      { key: "amount", label: "Amount", type: "money", width: "110px" },
      { key: "covered_transaction", label: "Covered", type: "check", width: "55px" },
      { key: "inherently_facilitative", label: "Inherently facilitative", type: "check", width: "60px" },
      { key: "success_based", label: "Success-based", type: "check", width: "60px" },
      { key: "transaction_abandoned", label: "Abandoned", type: "check", width: "60px" },
      { key: "incurred_date", label: "Incurred", type: "date", width: "135px" },
      { key: "bright_line_date", label: "Bright-line", type: "date", width: "135px" },
    ]));
    const sf = el("input", { type: "text",
      value: state.intang.success_fee_elections || "",
      oninput: e => { state.intang.success_fee_elections = e.target.value; save(); } });
    root.appendChild(el("label", { class: "f", style: "max-width:420px" },
      "Rev. Proc. 2011-29 elections (deal ids, comma-separated — IRREVOCABLE)", sf));

    root.appendChild(el("h3", {}, "§1.263(a)-4 intangibles"));
    root.appendChild(ioTable(state.intang.intangibles, [
      { key: "item_id", label: "Id", width: "60px" },
      { key: "description", label: "Description" },
      { key: "amount", label: "Amount", type: "money", width: "110px" },
      { key: "acquired_with_business", label: "§197 (with business)", type: "check", width: "60px" },
      { key: "benefit_start", label: "Benefit start", type: "date", width: "135px" },
      { key: "benefit_end", label: "Benefit end", type: "date", width: "135px" },
      { key: "payment_year", label: "Payment yr", width: "80px" },
      { key: "facilitative_costs", label: "Facilitative (non-commission)", type: "money", width: "110px" },
      { key: "facilitative_commissions", label: "Commissions", type: "money", width: "100px" },
      { key: "prior_capitalized_basis", label: "Prior capitalized", type: "money", width: "110px" },
    ]));

    root.appendChild(el("h3", {}, "§195/§248/§709 start-up & organizational pools"));
    root.appendChild(ioTable(state.intang.startup_pools, [
      { key: "pool_id", label: "Pool", width: "70px" },
      { key: "kind", label: "Kind", type: "select", width: "150px",
        options: ["startup", "org_corp", "org_partnership", "syndication"] },
      { key: "total", label: "Total costs", type: "money", width: "120px" },
      { key: "business_commencement", label: "Business commencement", type: "date", width: "160px" },
    ], null, { kind: "startup" }));

    const out = el("div", { class: "results" });
    root.appendChild(el("button", { class: "act", onclick: () => {
      clear(out);
      try {
        const r = E.compute263a45(
          state.intang.transaction_costs.map(t => ({ item_id: t.item_id || "",
            transaction_id: t.transaction_id || "", description: t.description || "",
            amount: orZero(t.amount), covered_transaction: !!t.covered_transaction,
            inherently_facilitative: !!t.inherently_facilitative,
            success_based: !!t.success_based,
            transaction_abandoned: !!t.transaction_abandoned,
            incurred_date: t.incurred_date || null,
            bright_line_date: t.bright_line_date || null })),
          state.intang.intangibles.map(i => ({ item_id: i.item_id || "",
            description: i.description || "", amount: orZero(i.amount),
            acquired_with_business: !!i.acquired_with_business,
            benefit_start: i.benefit_start || null, benefit_end: i.benefit_end || null,
            payment_year: parseInt(i.payment_year, 10) || 0,
            facilitative_costs: orZero(i.facilitative_costs),
            facilitative_commissions: orZero(i.facilitative_commissions),
            prior_capitalized_basis: orZero(i.prior_capitalized_basis) })),
          state.intang.startup_pools.map(p => ({ pool_id: p.pool_id || "",
            kind: p.kind || "startup", total: orZero(p.total),
            business_commencement: p.business_commencement || null })),
          { success_fee_elections: parseList(state.intang.success_fee_elections),
            current_tax_year: currentProfile().tax_year || 2026 });
        out.appendChild(kvTable([
          ["Capitalized basis posted", r.capitalized_total, { hl: true }],
          ["Currently deductible", r.deductible_total, { hl: true }],
        ]));
        out.appendChild(renderAmortTable(r.amortizable_items));
        out.appendChild(el("h3", {}, "Warnings"));
        out.appendChild(warnList(r.warnings));
        out.appendChild(rawDetails(r));
      } catch (err) {
        out.appendChild(el("div", { class: "warn err" }, String(err)));
      }
    } }, "Compute"));

    root.appendChild(el("h3", {}, "§280B demolition router"));
    const dm = state.intang.demolition;
    const dOut = el("div", { class: "results" });
    root.appendChild(el("div", { class: "grid", style: "max-width:760px" },
      el("label", { class: "f" }, "Demolition cost",
        el("input", { type: "text", value: dm.cost || "",
          oninput: e => { dm.cost = e.target.value; save(); } })),
      el("label", { class: "f" }, "Remaining structure basis",
        el("input", { type: "text", value: dm.basis || "",
          oninput: e => { dm.basis = e.target.value; save(); } })),
      el("label", { class: "chk" },
        el("input", { type: "checkbox", checked: !!dm.casualty,
          onchange: e => { dm.casualty = e.target.checked; save(); } }),
        "Casualty-triggered (Notice 90-21 — routes to SME, nothing auto-applied)")));
    root.appendChild(el("button", { class: "act", onclick: () => {
      clear(dOut);
      try {
        const r = E.routeDemolition(orZero(dm.cost), orZero(dm.basis),
          { casualty: !!dm.casualty });
        dOut.appendChild(renderAmortTable(r.amortizable_items));
        dOut.appendChild(warnList(r.warnings));
      } catch (err) {
        dOut.appendChild(el("div", { class: "warn err" }, String(err)));
      }
    } }, "Route demolition"));
    root.appendChild(dOut);
    root.appendChild(out);
  });

  /* ---- §59(e) ---- */
  panel("s59e", "§59(e) Elections", function (root) {
    root.appendChild(el("h2", {}, "§59(e) Qualified-Expenditure Amortization Elections"));
    root.appendChild(el("p", { class: "note" },
      "Item-by-item, irrevocable except by IRS consent. Gated FIRST on entity " +
      "type / individual-AMT exposure: a C corp (or a pass-through without " +
      "stated owner exposure) has no current-law use for §59(e)."));
    root.appendChild(ioTable(state.s59e.elections, [
      { key: "item_id", label: "Id", width: "70px" },
      { key: "category", label: "Category", type: "select", width: "190px",
        options: Object.keys(E.QE_PERIODS).map(k => [k, k]) },
      { key: "amount", label: "Amount", type: "money", width: "130px" },
      { key: "elected", label: "Elected", type: "check", width: "60px" },
      { key: "election_year", label: "Election year", width: "100px" },
    ], null, { category: "idc", elected: true }));
    const O = state.s59e.opts;
    root.appendChild(el("div", { class: "grid", style: "max-width:760px" },
      el("label", { class: "f" }, "Entity type",
        el("select", { onchange: e => { O.entity_type = e.target.value; save(); } },
          ["c_corp", "s_corp", "partnership", "sole_prop"].map(v => {
            const o = el("option", { value: v }, v);
            if ((O.entity_type || "c_corp") === v) o.selected = true; return o; }))),
      el("label", { class: "chk" },
        el("input", { type: "checkbox", checked: !!O.individual_amt_exposure,
          onchange: e => { O.individual_amt_exposure = e.target.checked; save(); } }),
        "Individual owners with AMT exposure"),
      el("label", { class: "f" }, "Items also under a §174A(c) election (ids)",
        el("input", { type: "text", value: O.overlapping || "",
          oninput: e => { O.overlapping = e.target.value; save(); } }))));
    const out = el("div", { class: "results" });
    root.appendChild(el("button", { class: "act", onclick: () => {
      clear(out);
      try {
        const r = E.compute59e(state.s59e.elections.map(x => ({
          item_id: x.item_id || "", category: x.category || "",
          amount: orZero(x.amount), elected: !!x.elected,
          election_year: parseInt(x.election_year, 10) || 0 })), {
          entity_type: O.entity_type || "c_corp",
          individual_amt_exposure: !!O.individual_amt_exposure,
          overlapping_174A_items: parseList(O.overlapping) });
        out.appendChild(renderAmortTable(r.amortizable_items));
        out.appendChild(el("h3", {}, "Warnings"));
        out.appendChild(warnList(r.warnings));
        out.appendChild(rawDetails(r));
      } catch (err) {
        out.appendChild(el("div", { class: "warn err" }, String(err)));
      }
    } }, "Compute"));
    root.appendChild(out);
  });

  /* ---- §1060 ---- */
  panel("s1060", "§1060 Allocation", function (root) {
    root.appendChild(el("h2", {}, "§1060 / Form 8594 Residual Purchase-Price Allocation"));
    root.appendChild(el("p", { class: "note" },
      "Consideration fills Classes I→VI in order, each capped at aggregate FMV; " +
      "Class VII (goodwill/going concern) is the residual. A shortfall inside a " +
      "class is a data/valuation red flag, not a silent outcome."));
    const S = state.s1060;
    const grid = el("div", { class: "grid", style: "max-width:900px" });
    grid.appendChild(el("label", { class: "f" }, "Transaction id",
      el("input", { type: "text", value: S.transaction_id || "",
        oninput: e => { S.transaction_id = e.target.value; save(); } })));
    grid.appendChild(el("label", { class: "f" }, "Aggregate consideration",
      el("input", { type: "text", value: S.aggregate_consideration || "",
        oninput: e => { S.aggregate_consideration = e.target.value; save(); } })));
    const CLS_LABELS = { I: "I — cash & equivalents", II: "II — marketable securities",
      III: "III — receivables/MTM", IV: "IV — inventory", V: "V — fixed assets",
      VI: "VI — §197 ex-goodwill" };
    for (const c of ["I", "II", "III", "IV", "V", "VI"]) {
      grid.appendChild(el("label", { class: "f" }, "Class " + CLS_LABELS[c] + " FMV",
        el("input", { type: "text", value: S.class_fmv[c] || "",
          oninput: e => { S.class_fmv[c] = e.target.value; save(); } })));
    }
    root.appendChild(grid);
    const out = el("div", { class: "results" });
    root.appendChild(el("button", { class: "act", onclick: () => {
      clear(out);
      try {
        const fmv = {};
        for (const [k, v] of Object.entries(S.class_fmv))
          if (String(v).trim() !== "") fmv[k] = orZero(v);
        const r = E.compute1060Allocation({ transaction_id: S.transaction_id || "",
          aggregate_consideration: orZero(S.aggregate_consideration), class_fmv: fmv });
        const rows = [];
        for (const c of ["I", "II", "III", "IV", "V", "VI"])
          if (c in r.by_class) rows.push(["Class " + c, r.by_class[c]]);
        rows.push(["Class VII residual (goodwill/going concern)",
          r.class_vii_residual, { hl: true }]);
        out.appendChild(kvTable(rows));
        out.appendChild(el("h3", {}, "Warnings"));
        out.appendChild(warnList(r.warnings));
      } catch (err) {
        out.appendChild(el("div", { class: "warn err" }, String(err)));
      }
    } }, "Compute"));
    root.appendChild(out);
  });

  /* ---- Save / Load ---- */
  panel("io", "Save / Load", function (root) {
    root.appendChild(el("h2", {}, "Save / Load Engagement"));
    root.appendChild(el("p", { class: "note" },
      "Inputs auto-save to this browser's local storage. Export a portable JSON " +
      "snapshot to move an engagement to another machine (this file runs " +
      "anywhere — no server, no install)."));
    root.appendChild(el("button", { class: "act", onclick: () => {
      const blob = new Blob([JSON.stringify(state, null, 2)],
        { type: "application/json" });
      const a = el("a", { href: URL.createObjectURL(blob),
        download: "cap263a_engagement.json" });
      document.body.appendChild(a); a.click(); a.remove();
    } }, "Export engagement JSON"));
    const file = el("input", { type: "file", accept: ".json,application/json",
      onchange: e => {
        const f = e.target.files[0];
        if (!f) return;
        const reader = new FileReader();
        reader.onload = () => {
          try {
            const data = JSON.parse(reader.result);
            deepMerge(state, data);
            save();
            location.reload();
          } catch (err) { alert("Import failed: " + err); }
        };
        reader.readAsText(f);
      } });
    root.appendChild(el("label", { class: "f", style: "max-width:320px" },
      "Import engagement JSON", file));
    root.appendChild(el("button", { class: "act",
      style: "background:var(--bad)", onclick: () => {
        if (confirm("Clear ALL inputs?")) {
          localStorage.removeItem(STORAGE_KEY); location.reload();
        }
      } }, "Clear everything"));
  });

  /* ---- Self-tests ---- */
  panel("selftest", "Self-Tests", function (root) {
    root.appendChild(el("h2", {}, "Engine Self-Tests (parity vs the Python engines)"));
    root.appendChild(el("p", { class: "note" },
      "Every scenario below was computed by the authoritative Python engines " +
      "(financial_tools/cap263a) and embedded in this file; the JavaScript " +
      "engines recompute each one on load. All green = the numbers this file " +
      "produces match the Python tool exactly."));
    const box = el("div", {});
    root.appendChild(box);
    renderSelfTests(box);
  });

  let selftestResults = null;
  function runSelfTests() {
    if (selftestResults) return selftestResults;
    const goldens = JSON.parse(document.getElementById("goldens-data").textContent);
    selftestResults = SELFTEST.runAll(goldens);
    return selftestResults;
  }
  function renderSelfTests(box) {
    const results = runSelfTests();
    const passed = results.filter(r => r.pass).length;
    box.appendChild(el("p", {},
      el("span", { class: "pill " + (passed === results.length ? "ok" : "bad") },
        passed + " / " + results.length + " pass")));
    for (const r of results) {
      const row = el("div", { class: "selftest-row" },
        el("span", { class: r.pass ? "ok" : "err" }, r.pass ? "PASS " : "FAIL "),
        r.name + "  (" + r.engine + ")");
      for (const d of r.diffs) row.appendChild(el("div", { class: "diff" }, d));
      box.appendChild(row);
    }
  }

  /* ---------------- shell ---------------- */
  const nav = document.getElementById("nav");
  const main = document.getElementById("main");
  const sections = {};
  const buttons = {};
  for (const p of panels) {
    const sec = el("section", { class: "panel", id: "panel-" + p.id });
    main.appendChild(sec);
    sections[p.id] = { sec, built: false, build: p.build };
    const btn = el("button", { onclick: () => show(p.id) }, p.title);
    buttons[p.id] = btn;
    nav.appendChild(btn);
  }
  function show(id) {
    for (const [pid, s] of Object.entries(sections)) {
      s.sec.classList.toggle("active", pid === id);
      buttons[pid].classList.toggle("active", pid === id);
    }
    const s = sections[id];
    if (!s.built) { s.build(s.sec); s.built = true; }
  }

  /* self-test badge (also machine-readable for headless verification) */
  (function () {
    const results = runSelfTests();
    const passed = results.filter(r => r.pass).length;
    const ok = passed === results.length;
    const badge = document.getElementById("selftest-badge");
    badge.appendChild(el("span", { class: "pill " + (ok ? "ok" : "bad"),
      id: "selftest-status",
      "data-status": (ok ? "PASS" : "FAIL") + " " + passed + "/" + results.length },
      "self-tests: " + passed + "/" + results.length));
    badge.parentNode.style.cursor = "pointer";
  })();

  /* test hook: #buildall forces every panel to build (surfaces DOM errors
   * in lazily-built tabs during headless verification) */
  if (location.hash === "#buildall") {
    let failures = [];
    for (const p of panels) {
      try { show(p.id); } catch (err) { failures.push(p.id + ": " + err); }
    }
    const n = el("div", { id: "buildall-status",
      "data-status": failures.length ? "FAIL " + failures.join(" | ") : "PASS all-panels" });
    document.body.appendChild(n);

    /* end-to-end smoke: feed a known TB through the real UI compute path and
     * check the rendered UNICAP figure (expected: $94,000.00 to inventory) */
    try {
      state.profile.avg_gross_receipts = "75000000";
      state.profile.ending_inventory_471 = "200000";
      state.profile.method = "SPM";
      state.tb_lines.length = 0;
      state.tb_lines.push(
        { acct_desc: "Direct labor", amount: "1000000", tier1: "§471 Cost", is_labor: true },
        { acct_desc: "Direct materials", amount: "500000", tier1: "§471 Cost" },
        { acct_desc: "Purchasing salaries", amount: "300000", tier1: "Additional §263A", is_labor: true },
        { acct_desc: "HR - plant", amount: "400000", tier1: "Mixed Service", is_labor: true },
        { acct_desc: "Advertising", amount: "200000", tier1: "Excluded" });
      show("tb");
      const btn = Array.from(sections.tb.sec.querySelectorAll("button.act"))
        .find(b => b.textContent === "Compute");
      btn.click();
      const txt = sections.tb.sec.textContent;
      const ok = txt.indexOf("$94,000.00") !== -1 && txt.indexOf("Total capitalized") !== -1;
      document.body.appendChild(el("div", { id: "smoke-status",
        "data-status": ok ? "PASS ui-smoke" : "FAIL ui-smoke (94,000 not rendered)" }));
    } catch (err) {
      document.body.appendChild(el("div", { id: "smoke-status",
        "data-status": "FAIL ui-smoke " + err }));
    }

    /* import-pipeline smoke: run a real CSV through I.sniffAndParse +
     * genericDetectHeader/genericRowsToObjects for the "re" (§174) target,
     * exercising the exact code path the Import Files tab's file handler
     * uses, without needing to simulate a <input type=file> change event. */
    (async () => {
      try {
        const csv = "RE Id,Description,Amount,Domestic,Year Incurred\n" +
          "F1,Foreign lab,900000,No,2026\nD1,US bench,150000,Yes,2026\n";
        const parsed = await I.sniffAndParse("re.csv", csv);
        const target = IMPORT_TARGETS.find(t => t.key === "re");
        const { headerIndex, mapping } = genericDetectHeader(parsed.sheets[0].rows, target.aliases);
        const objs = genericRowsToObjects(parsed.sheets[0].rows, headerIndex, mapping);
        const mapped = objs.map(target.map);
        const ok = parsed.kind === "csv" && objs.length === 2 &&
          mapped[0].re_id === "F1" && mapped[0].amount === "900000" &&
          mapped[1].re_id === "D1";
        document.body.appendChild(el("div", { id: "import-smoke-status",
          "data-status": ok ? "PASS import-smoke"
            : "FAIL import-smoke " + JSON.stringify(mapped) }));
      } catch (err) {
        document.body.appendChild(el("div", { id: "import-smoke-status",
          "data-status": "FAIL import-smoke " + err }));
      }
    })();

    /* tangible engine smoke: a conservative-capitalize case (missing BAR
     * facts) must produce an open question and NOT silently deduct. */
    try {
      state.tangible.items.length = 0;
      state.tangible.items.push({ item_id: "P1", description: "Roof work",
        amount: "4000", betterment: "", adaptation: "false", restoration: "" });
      show("tangible");
      const tbtn = Array.from(sections.tangible.sec.querySelectorAll("button.act"))
        .find(b => b.textContent === "Compute");
      tbtn.click();
      const ttxt = sections.tangible.sec.textContent;
      const tok = ttxt.indexOf("open_question_capitalize_pending") !== -1 &&
        ttxt.indexOf("Open questions") !== -1;
      document.body.appendChild(el("div", { id: "tangible-smoke-status",
        "data-status": tok ? "PASS tangible-smoke" : "FAIL tangible-smoke" }));
    } catch (err) {
      document.body.appendChild(el("div", { id: "tangible-smoke-status",
        "data-status": "FAIL tangible-smoke " + err }));
    }
  }

  show("profile");
})();
