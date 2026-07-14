/* Zero-dependency file ingestion for the standalone §263A calculator.
 *
 * Parses spreadsheet uploads (CSV / XLSX / JSON) into row objects entirely
 * offline — no third-party code, no DOM, no DOMParser. Runs in the browser
 * (attached as window.CAP263A_INGEST) and under Node 22 (CommonJS module,
 * exercised by test_ingest.js).
 *
 * Format limitations (documented for the UI):
 *  - Amounts: US formatting only. "$1,234.56", "(500)", "1234.56", "-500"
 *    are handled; European "1 234,56" / "1.234,56" are NOT (they return null
 *    or misparse-safe null — internal spaces and comma decimals are rejected).
 *  - XLSX dates are returned as raw Excel serial numbers; styles.xml is not
 *    consulted. Callers that know a column is a date can convert with
 *    excelSerialToISO(n) (1900 date system, incl. the Lotus leap-year bug:
 *    serial 60 = the nonexistent 1900-02-29 -> null).
 *  - XLSX: only .xlsx/.xlsm ZIP containers (stored or deflate entries);
 *    legacy .xls (BIFF) and encrypted workbooks are not supported. Formula
 *    cells yield their cached values only. Phonetic (rPh) runs are ignored.
 *  - ZIP64 archives (>4 GB / >65535 entries) are not supported.
 */
"use strict";

(function (root, factory) {
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.CAP263A_INGEST = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {

  // ------------------------------------------------------------------
  // Column alias tables
  //
  // Ported from financial_tools/cap263a/reader.py (_ALIASES — the trial-
  // balance reader) and financial_tools/cap263a/readers.py (_SPECS — the
  // per-schedule engagement readers). A few extra real-world synonyms are
  // appended and marked "// added": common ERP export headers ("GL Acct",
  // "YTD Amount") that the Python tables matched only via their broader
  // openpyxl pipeline.
  // ------------------------------------------------------------------

  const TB_ALIASES = {
    acct_num: ["account number", "acct number", "acct #", "acct no",
      "account no", "gl account", "account #", "gl #", "account",
      "gl acct", "gl account number", "account num", "acct"], // added
    acct_desc: ["account description", "acct desc", "acct description",
      "account desc", "gl description", "gl desc", "description",
      "account name"], // added
    cc_num: ["cost center number", "cc number", "cc #", "cc", "dept number",
      "dept. number", "dept #", "dept no", "department number",
      "cost center", "cost center #",
      "dept"], // added (readers.py uses "dept" for cc_num on BTD schedules)
    cc_desc: ["cost center description", "cc description", "cc desc",
      "department description", "dept description", "dept desc",
      "department", "dept name", "cost center name"],
    // A single net/amount column is preferred (see reader.py: "debit" alone
    // would zero credit balances on a two-column TB).
    amount: ["amount", "net balance", "net", "total book amount", "balance",
      "net amount", "ending balance", "amount (debit / <credit>)",
      "ytd amount", "ytd balance", "period amount", "current balance"], // added
    debit: ["debit", "debit amount", "dr"],
    credit: ["credit", "credit amount", "cr"],
  };

  // Schedule-specific header synonyms, verbatim from readers.py _SPECS
  // (field name -> lowercase alias list, keyed by schedule kind).
  const SCHEDULE_ALIASES = {
    btd: {
      btd_id: ["btd id", "btd #", "id"],
      acct_num: ["account number", "acct number", "acct #", "account", "gl account"],
      cc_num: ["cost center", "cc", "cc #", "dept", "department", "cost center number"],
      description: ["description", "btd description", "difference description"],
      adjustment: ["adjustment", "tax minus book", "btd amount", "amount",
        "tax-book difference", "difference"],
      category: ["category", "type", "btd type"],
      affects_471: ["affects 471", "affects §471", "in 471 costs", "embedded in 471"],
    },
    fixed_assets: {
      asset_id: ["asset id", "asset #", "asset number", "id"],
      description: ["description", "asset description", "asset name"],
      asset_type: ["asset type", "type", "property type", "category"],
      class_life: ["class life", "macrs life", "recovery period", "life"],
      cost: ["cost", "book cost", "gross book value", "basis", "original cost"],
      placed_in_service: ["placed in service", "pis date", "pis",
        "in service date", "placed in service date"],
      cc_num: ["cost center", "cc", "cc #", "dept", "department"],
      book_capitalized_interest: ["book capitalized interest",
        "capitalized interest", "book cap interest"],
      is_improvement: ["is improvement", "improvement"],
      demolition_event: ["demolition", "demolition event", "demolished"],
    },
    cip: {
      project_id: ["project id", "project #", "cip id", "id", "project"],
      description: ["description", "project description", "project name"],
      linked_asset_id: ["linked asset id", "asset id", "target asset", "asset"],
      is_real_property: ["is real property", "real property", "real"],
      class_life: ["class life", "recovery period", "life"],
      total_estimated_cost: ["total estimated cost", "estimated cost", "budget"],
      production_start: ["production start", "start date", "construction start"],
      production_complete: ["production complete", "completion date", "complete date"],
      is_improvement: ["is improvement", "improvement"],
      mid_production_purchase_price: ["mid production purchase price", "purchase price"],
      unit_id: ["unit id", "unit"],
      is_common_feature: ["is common feature", "common feature"],
      contract_role: ["contract role", "role"],
      book_capitalized_interest: ["book capitalized interest", "capitalized interest"],
    },
    debt: {
      debt_id: ["debt id", "loan id", "debt #", "loan #", "id", "loan"],
      description: ["description", "loan description", "lender"],
      principal: ["principal", "average outstanding", "avg outstanding",
        "outstanding", "balance"],
      rate: ["rate", "interest rate", "annual rate"],
      interest_incurred: ["interest incurred", "interest", "interest expense"],
      traced_to: ["traced to", "traced project", "project id", "traced"],
      related_party_below_afr: ["related party below afr", "below afr"],
      non_interest_bearing: ["non interest bearing", "non-interest bearing"],
      personal_or_qualified_residence: ["personal", "qualified residence"],
      tax_exempt_org_nonbusiness: ["tax exempt", "tax-exempt nonbusiness"],
      disallowed_163_8T: ["disallowed 163-8t", "disallowed"],
      reserve_or_deferred_tax: ["reserve", "deferred tax", "dtl"],
      tax_liability_453a_460b: ["tax liability", "453a", "460b"],
      sale_leaseback_purchase_money: ["sale leaseback", "sale-leaseback",
        "purchase money"],
    },
    re: {
      re_id: ["re id", "project id", "id", "project"],
      description: ["description", "project description"],
      amount: ["amount", "expenditure", "cost"],
      domestic: ["domestic", "is domestic", "us"],
      tax_year: ["tax year", "year", "year incurred"],
      software_development: ["software development", "software", "software dev"],
      book_capitalized_amount: ["book capitalized amount", "book capitalized"],
    },
    transaction_costs: {
      item_id: ["item id", "id"],
      transaction_id: ["transaction id", "transaction", "deal id", "deal"],
      description: ["description", "cost description"],
      amount: ["amount", "cost", "fee"],
      cost_type: ["cost type", "type"],
      covered_transaction: ["covered transaction", "covered"],
      inherently_facilitative: ["inherently facilitative", "facilitative"],
      incurred_date: ["incurred date", "date incurred", "date"],
      bright_line_date: ["bright line date", "bright-line date"],
      success_based: ["success based", "success-based", "success fee"],
      transaction_abandoned: ["abandoned", "transaction abandoned"],
    },
    intangibles: {
      item_id: ["item id", "intangible id", "id"],
      description: ["description", "intangible description"],
      amount: ["amount", "cost"],
      category: ["category", "intangible category", "type"],
      acquired_with_business: ["acquired with business", "with business",
        "197 eligible", "§197"],
      benefit_start: ["benefit start", "start date", "rights start"],
      benefit_end: ["benefit end", "end date", "rights end"],
      payment_year: ["payment year", "year paid", "year"],
      facilitative_costs: ["facilitative costs", "facilitative"],
      facilitative_commissions: ["facilitative commissions", "commissions",
        "commission"],
      prior_capitalized_basis: ["prior capitalized basis", "prior basis"],
    },
    startup: {
      pool_id: ["pool id", "id"],
      kind: ["kind", "type", "pool type"],
      total: ["total", "amount", "total costs"],
      business_commencement: ["business commencement", "commencement date",
        "business start", "start date"],
    },
    qualified_expenditures: {
      item_id: ["item id", "id"],
      category: ["category", "type"],
      amount: ["amount", "expenditure"],
      elected: ["elected", "59e election", "elect"],
      election_year: ["election year", "year"],
    },
  };

  // Section headers to skip on a TB (reader.py _SECTION_HEADERS).
  const SECTION_HEADERS = new Set(["assets", "liabilities", "equity",
    "revenue", "expenses", "income", "cost of goods sold", "cogs"]);

  // ------------------------------------------------------------------
  // Normalization + alias lookup
  // ------------------------------------------------------------------

  /** Case/space/punctuation-insensitive header form: lowercase, every run of
   *  non-alphanumerics collapses to a single space ("Acct. #" -> "acct",
   *  "YTD  Amount" -> "ytd amount"). */
  function normHeader(s) {
    return String(s == null ? "" : s)
      .toLowerCase()
      .replace(/[^a-z0-9§&]+/g, " ")
      .trim();
  }

  // Precompute normalized alias -> field lookups for the TB target fields.
  const TB_FIELDS = ["acct_num", "acct_desc", "cc_num", "cc_desc", "amount"];
  const TB_LOOKUP = (function () {
    const m = new Map();
    for (const field of TB_FIELDS) {
      for (const a of TB_ALIASES[field]) {
        const n = normHeader(a);
        if (!m.has(n)) m.set(n, field); // first field (in TB_FIELDS order) wins
      }
    }
    return m;
  })();

  // ------------------------------------------------------------------
  // 1. parseCSV
  // ------------------------------------------------------------------

  const CSV_DELIMS = [",", "\t", ";", "|"];

  /** RFC-4180-ish record parser for one known delimiter. Handles quoted
   *  fields containing delimiters/newlines, "" escapes, \r\n and bare \r. */
  function csvRecords(text, delim) {
    const rows = [];
    let row = [], field = "", inQ = false, i = 0;
    const n = text.length;
    while (i < n) {
      const ch = text[i];
      if (inQ) {
        if (ch === '"') {
          if (text[i + 1] === '"') { field += '"'; i += 2; continue; }
          inQ = false; i++; continue;
        }
        field += ch; i++; continue;
      }
      if (ch === '"') { inQ = true; i++; continue; }
      if (ch === delim) { row.push(field); field = ""; i++; continue; }
      if (ch === "\n" || ch === "\r") {
        if (ch === "\r" && text[i + 1] === "\n") i++;
        row.push(field); rows.push(row); row = []; field = ""; i++;
        continue;
      }
      field += ch; i++;
    }
    if (field !== "" || row.length) { row.push(field); rows.push(row); }
    // Drop a trailing fully-empty record (text ending in a newline).
    while (rows.length && rows[rows.length - 1].every(c => c === "")) rows.pop();
    return rows;
  }

  /** Pick the delimiter whose column count is most consistent (and > 1)
   *  over the first non-empty records of a sample. */
  function sniffDelimiter(text) {
    const sample = text.slice(0, 65536);
    let best = ",", bestScore = -1;
    for (const d of CSV_DELIMS) {
      const recs = csvRecords(sample, d)
        .filter(r => r.some(c => c.trim() !== ""))
        .slice(0, 10);
      if (!recs.length) continue;
      const counts = {};
      for (const r of recs) counts[r.length] = (counts[r.length] || 0) + 1;
      let modeCount = 0, modeFreq = 0;
      for (const k of Object.keys(counts)) {
        if (counts[k] > modeFreq ||
            (counts[k] === modeFreq && Number(k) > modeCount)) {
          modeFreq = counts[k]; modeCount = Number(k);
        }
      }
      if (modeCount <= 1) continue; // a non-occurring delimiter always "wins" with 1 col
      const score = (modeFreq / recs.length) * 1000 + modeCount;
      if (score > bestScore) { bestScore = score; best = d; }
    }
    return best;
  }

  /** parseCSV(text) -> {rows: string[][], delimiter} */
  function parseCSV(text) {
    let t = String(text);
    if (t.charCodeAt(0) === 0xFEFF) t = t.slice(1); // BOM
    const delimiter = sniffDelimiter(t);
    return { rows: csvRecords(t, delimiter), delimiter };
  }

  // ------------------------------------------------------------------
  // 3. cleanAmount
  // ------------------------------------------------------------------

  const NUM_RE = /^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$/;

  /** cleanAmount(v) -> canonical numeric string, or null when not numeric.
   *  "$1,234.56" -> "1234.56"; "(500)" -> "-500"; "-" -> null; "" -> null.
   *  US formats only: "1 234,56" (space thousands / comma decimals) is NOT
   *  handled and returns null. */
  function cleanAmount(v) {
    if (v === null || v === undefined) return null;
    if (typeof v === "number") {
      return Number.isFinite(v) ? String(v) : null;
    }
    if (typeof v === "boolean") return null;
    let s = String(v).trim();
    if (s === "" || s === "-" || s === "–" || s === "—") return null;
    // currency + thousands separators (US only)
    s = s.replace(/[$,]/g, "").trim();
    // accounting negatives: (500) -> -500
    let neg = false;
    if (/^\(.*\)$/.test(s)) { neg = true; s = s.slice(1, -1).trim(); }
    if (s.startsWith("-")) { neg = !neg; s = s.slice(1).trim(); }
    else if (s.startsWith("+")) { s = s.slice(1).trim(); }
    if (s === "" || !NUM_RE.test(s)) return null;
    if (s.startsWith(".")) s = "0" + s;
    if (Number(s) === 0) neg = false; // no "-0"
    return (neg ? "-" : "") + s;
  }

  // ------------------------------------------------------------------
  // 4. detectHeader
  // ------------------------------------------------------------------

  const HEADER_SCAN_ROWS = 10;

  /** detectHeader(rows) -> {headerIndex, mapping}
   *  Scans the first 10 rows for the row matching the most TB aliases
   *  (case/space/punct-insensitive). mapping = {colIndex: fieldName} for
   *  acct_num / acct_desc / cc_num / cc_desc / amount. Blank rows and
   *  section headers score 0 and are skipped naturally. */
  function detectHeader(rows) {
    let best = { headerIndex: 0, mapping: {} }, bestScore = 0;
    const limit = Math.min(rows.length, HEADER_SCAN_ROWS);
    for (let r = 0; r < limit; r++) {
      const row = rows[r] || [];
      const mapping = {}, taken = new Set();
      let score = 0;
      for (let c = 0; c < row.length; c++) {
        const field = TB_LOOKUP.get(normHeader(row[c]));
        if (field && !taken.has(field)) {
          mapping[c] = field; taken.add(field); score++;
        }
      }
      if (score > bestScore) { best = { headerIndex: r, mapping }; bestScore = score; }
    }
    return best;
  }

  // ------------------------------------------------------------------
  // 5. rowsToObjects
  // ------------------------------------------------------------------

  function cellText(v) {
    if (v === null || v === undefined) return "";
    return String(v).trim();
  }

  /** rowsToObjects(rows, headerIndex, mapping) -> objects[]
   *  One object per data row below the header, with keys acct_num,
   *  acct_desc, cc_num, cc_desc (strings, "" when unmapped) and amount
   *  (cleanAmount string or null), plus row_index (0-based index into rows).
   *  Skips: rows with no amount AND no description; section-header rows
   *  (a single non-empty cell and no amount). */
  function rowsToObjects(rows, headerIndex, mapping) {
    const out = [];
    for (let r = headerIndex + 1; r < rows.length; r++) {
      const row = rows[r] || [];
      const obj = { acct_num: "", acct_desc: "", cc_num: "", cc_desc: "",
        amount: null, row_index: r };
      for (const [ci, field] of Object.entries(mapping)) {
        const raw = row[Number(ci)];
        if (field === "amount") obj.amount = cleanAmount(raw);
        else obj[field] = cellText(raw);
      }
      const nonEmpty = row.filter(c => cellText(c) !== "").length;
      if (nonEmpty === 0) continue;                       // blank row
      if (obj.amount === null && obj.acct_desc === "") continue;
      if (nonEmpty === 1 && obj.amount === null) continue; // section header
      if (obj.amount === null &&
          SECTION_HEADERS.has(obj.acct_desc.toLowerCase()) &&
          obj.acct_num === "") continue;                  // "Assets" etc.
      out.push(obj);
    }
    return out;
  }

  // ------------------------------------------------------------------
  // 2. parseXLSX — minimal ZIP + OOXML reader, no third-party code
  // ------------------------------------------------------------------

  function utf8Decode(u8) {
    return new TextDecoder("utf-8").decode(u8);
  }

  /** Inflate a raw-deflate stream. Uses DecompressionStream("deflate-raw")
   *  (global in browsers and Node 22); in Node, feature-test and fall back
   *  to zlib.inflateRawSync so tests never flake. */
  async function inflateRaw(u8) {
    if (typeof DecompressionStream === "function") {
      try {
        const ds = new DecompressionStream("deflate-raw");
        const stream = new Blob([u8]).stream().pipeThrough(ds);
        const ab = await new Response(stream).arrayBuffer();
        return new Uint8Array(ab);
      } catch (e) {
        // fall through to zlib in Node
        if (typeof require !== "function") throw e;
      }
    }
    if (typeof require === "function") {
      return new Uint8Array(require("zlib").inflateRawSync(Buffer.from(u8)));
    }
    throw new Error("No deflate-raw decompressor available");
  }

  /** Parse a ZIP archive: EOCD -> central directory -> entries.
   *  Returns Map<name, {method, dataStart, compSize}> plus the byte array. */
  function zipDirectory(u8) {
    const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
    // End Of Central Directory: scan backwards (max 64K comment).
    let eocd = -1;
    const lo = Math.max(0, u8.length - 22 - 65535);
    for (let i = u8.length - 22; i >= lo; i--) {
      if (dv.getUint32(i, true) === 0x06054b50) { eocd = i; break; }
    }
    if (eocd < 0) throw new Error("Not a ZIP file (no end-of-central-directory)");
    const count = dv.getUint16(eocd + 10, true);
    let p = dv.getUint32(eocd + 16, true);
    const entries = new Map();
    for (let e = 0; e < count; e++) {
      if (dv.getUint32(p, true) !== 0x02014b50) {
        throw new Error("Corrupt ZIP central directory");
      }
      const method = dv.getUint16(p + 10, true);
      const compSize = dv.getUint32(p + 20, true);
      const nameLen = dv.getUint16(p + 28, true);
      const extraLen = dv.getUint16(p + 30, true);
      const commentLen = dv.getUint16(p + 32, true);
      const localOff = dv.getUint32(p + 42, true);
      const name = utf8Decode(u8.subarray(p + 46, p + 46 + nameLen));
      // Local header gives the actual data start (its own name/extra lengths
      // may differ from the central directory's).
      if (dv.getUint32(localOff, true) !== 0x04034b50) {
        throw new Error("Corrupt ZIP local header for " + name);
      }
      const lNameLen = dv.getUint16(localOff + 26, true);
      const lExtraLen = dv.getUint16(localOff + 28, true);
      entries.set(name, {
        method, compSize,
        dataStart: localOff + 30 + lNameLen + lExtraLen,
      });
      p += 46 + nameLen + extraLen + commentLen;
    }
    return entries;
  }

  async function zipExtract(u8, entries, name) {
    const ent = entries.get(name);
    if (!ent) return null;
    const comp = u8.subarray(ent.dataStart, ent.dataStart + ent.compSize);
    if (ent.method === 0) return comp.slice();       // stored
    if (ent.method === 8) return inflateRaw(comp);   // deflate
    throw new Error("Unsupported ZIP compression method " + ent.method +
      " for " + name);
  }

  // ---- tiny XML helpers (xlsx-produced XML only: standard attribute
  // quoting, well-formed, no CDATA in the parts we read) ----

  function decodeXML(s) {
    return String(s)
      .replace(/&#x([0-9A-Fa-f]+);/g, (_, h) => String.fromCodePoint(parseInt(h, 16)))
      .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(parseInt(d, 10)))
      .replace(/&lt;/g, "<").replace(/&gt;/g, ">")
      .replace(/&quot;/g, '"').replace(/&apos;/g, "'")
      .replace(/&amp;/g, "&");
  }

  function xmlAttr(tag, name) {
    const re = new RegExp("(?:^|\\s)" +
      name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") +
      "\\s*=\\s*(?:\"([^\"]*)\"|'([^']*)')");
    const m = re.exec(tag);
    if (!m) return null;
    return decodeXML(m[1] !== undefined ? m[1] : m[2]);
  }

  /** Concatenate the text of every <t> descendant (rich-text runs), ignoring
   *  phonetic <rPh> blocks. Handles <t/> and <t xml:space="preserve">. */
  function textRuns(xml) {
    const cleaned = xml.replace(/<rPh\b[\s\S]*?<\/rPh>/g, "");
    let out = "";
    const re = /<t(?:\s[^>]*)?>([\s\S]*?)<\/t>|<t(?:\s[^>]*)?\/>/g;
    let m;
    while ((m = re.exec(cleaned)) !== null) {
      if (m[1] !== undefined) out += decodeXML(m[1]);
    }
    return out;
  }

  /** "BC" -> 54 (0-based column index). */
  function colIndex(ref) {
    let n = 0;
    for (let i = 0; i < ref.length; i++) {
      const c = ref.charCodeAt(i);
      if (c < 65 || c > 90) break;
      n = n * 26 + (c - 64);
    }
    return n - 1;
  }

  function parseSharedStrings(xml) {
    if (!xml) return [];
    const out = [];
    const re = /<si(?:\s[^>]*)?>([\s\S]*?)<\/si>|<si(?:\s[^>]*)?\/>/g;
    let m;
    while ((m = re.exec(xml)) !== null) {
      out.push(m[1] !== undefined ? textRuns(m[1]) : "");
    }
    return out;
  }

  const MAX_SHEET_ROWS = 262144; // guard: a stray cell at row ~1M must not OOM

  function parseWorksheet(xml, shared) {
    const sparse = []; // sparse array of sparse rows
    let maxCol = -1, maxRow = -1, autoRow = -1;
    const rowRe = /<row\b([^>]*)>([\s\S]*?)<\/row>|<row\b([^>]*)\/>/g;
    let rm;
    while ((rm = rowRe.exec(xml)) !== null) {
      const attrs = rm[1] !== undefined ? rm[1] : rm[3];
      const inner = rm[2];
      const rAttr = xmlAttr("<row " + attrs + ">", "r");
      let rIdx = rAttr ? parseInt(rAttr, 10) - 1 : autoRow + 1;
      if (!(rIdx >= 0)) rIdx = autoRow + 1;
      autoRow = rIdx;
      if (rIdx >= MAX_SHEET_ROWS) continue;
      if (inner === undefined) { if (rIdx > maxRow) maxRow = rIdx; continue; }
      const cells = [];
      let autoCol = -1;
      const cellRe = /<c\b([^>]*)\/>|<c\b([^>]*)>([\s\S]*?)<\/c>/g;
      let cm;
      while ((cm = cellRe.exec(inner)) !== null) {
        const cAttrs = cm[1] !== undefined ? cm[1] : cm[2];
        const body = cm[3];
        const tag = "<c " + cAttrs + ">";
        const ref = xmlAttr(tag, "r");
        let cIdx = ref ? colIndex(ref) : autoCol + 1;
        if (!(cIdx >= 0)) cIdx = autoCol + 1;
        autoCol = cIdx;
        const t = xmlAttr(tag, "t") || "";
        let val = "";
        if (body !== undefined) {
          if (t === "inlineStr") {
            const is = /<is(?:\s[^>]*)?>([\s\S]*?)<\/is>/.exec(body);
            val = is ? textRuns(is[1]) : "";
          } else {
            const vm = /<v(?:\s[^>]*)?>([\s\S]*?)<\/v>/.exec(body);
            const raw = vm ? decodeXML(vm[1]) : "";
            if (t === "s") {
              const si = parseInt(raw, 10);
              val = Number.isInteger(si) && shared[si] !== undefined ? shared[si] : "";
            } else if (t === "str" || t === "e" || t === "d") {
              val = raw;
            } else if (t === "b") {
              val = raw === "1" ? "TRUE" : "FALSE";
            } else { // n / default: numeric
              if (raw === "") val = "";
              else {
                const num = Number(raw);
                val = Number.isFinite(num) ? num : raw;
              }
            }
          }
        }
        cells[cIdx] = val;
        if (cIdx > maxCol) maxCol = cIdx;
      }
      sparse[rIdx] = cells;
      if (rIdx > maxRow) maxRow = rIdx;
    }
    // Densify: every row is an array of length maxCol+1; gaps are "".
    const rows = [];
    for (let r = 0; r <= maxRow; r++) {
      const src = sparse[r] || [];
      const row = new Array(Math.max(maxCol + 1, 0)).fill("");
      for (let c = 0; c <= maxCol; c++) {
        if (src[c] !== undefined) row[c] = src[c];
      }
      rows.push(row);
    }
    return rows;
  }

  function resolveTarget(target) {
    let t = String(target || "");
    if (t.startsWith("/")) return t.slice(1);
    while (t.startsWith("../")) t = t.slice(3); // "../foo" from xl/ -> "foo"
    return "xl/" + t;
  }

  /** parseXLSX(arrayBuffer) -> Promise<{sheets: [{name, rows}]}>
   *  rows: dense (string|number)[][]; dates stay as raw serial numbers
   *  (convert with excelSerialToISO). */
  async function parseXLSX(arrayBuffer) {
    const u8 = arrayBuffer instanceof Uint8Array
      ? arrayBuffer
      : new Uint8Array(arrayBuffer);
    const entries = zipDirectory(u8);

    async function xmlOf(name) {
      const bytes = await zipExtract(u8, entries, name);
      if (bytes === null) return null;
      let s = utf8Decode(bytes);
      if (s.charCodeAt(0) === 0xFEFF) s = s.slice(1);
      return s;
    }

    const wbXml = await xmlOf("xl/workbook.xml");
    if (wbXml === null) throw new Error("Not an XLSX workbook (missing xl/workbook.xml)");
    const relsXml = await xmlOf("xl/_rels/workbook.xml.rels");
    const ssXml = await xmlOf("xl/sharedStrings.xml");
    const shared = parseSharedStrings(ssXml || "");

    // rId -> target from the rels part
    const rels = new Map();
    if (relsXml) {
      const rre = /<Relationship\b[^>]*\/?>/g;
      let m;
      while ((m = rre.exec(relsXml)) !== null) {
        const id = xmlAttr(m[0], "Id");
        const target = xmlAttr(m[0], "Target");
        if (id && target) rels.set(id, resolveTarget(target));
      }
    }

    // sheets in workbook order
    const sheets = [];
    const sre = /<sheet\b[^>]*\/?>/g;
    let sm, fallback = 0;
    while ((sm = sre.exec(wbXml)) !== null) {
      const name = xmlAttr(sm[0], "name") || ("Sheet" + (sheets.length + 1));
      const rid = xmlAttr(sm[0], "r:id") || xmlAttr(sm[0], "id");
      fallback++;
      let target = rid ? rels.get(rid) : null;
      if (!target) target = "xl/worksheets/sheet" + fallback + ".xml";
      const wsXml = await xmlOf(target);
      sheets.push({ name, rows: wsXml === null ? [] : parseWorksheet(wsXml, shared) });
    }
    return { sheets };
  }

  // ------------------------------------------------------------------
  // excelSerialToISO
  // ------------------------------------------------------------------

  const DAY_MS = 86400000;

  /** Excel 1900-system serial -> "YYYY-MM-DD". Serial 1 = 1900-01-01.
   *  Preserves the Lotus leap-year bug: serial 60 pretends 1900-02-29
   *  existed — it did not, so 60 returns null (as do serials < 1 and
   *  non-finite input). Fractions (time of day) are truncated. */
  function excelSerialToISO(n) {
    const s = Math.floor(Number(n));
    if (!Number.isFinite(s) || s < 1 || s === 60) return null;
    // For serials >= 61 the effective epoch is 1899-12-30 (the phantom
    // Feb 29 already counted); for 1..59 it is 1899-12-31.
    const days = s <= 59 ? s + 1 : s;
    const d = new Date(Date.UTC(1899, 11, 30) + days * DAY_MS);
    return d.toISOString().slice(0, 10);
  }

  // ------------------------------------------------------------------
  // 6. sniffAndParse
  // ------------------------------------------------------------------

  function extOf(filename) {
    const m = /\.([A-Za-z0-9]+)$/.exec(String(filename || ""));
    return m ? m[1].toLowerCase() : "";
  }

  function stripExt(filename) {
    const base = String(filename || "").replace(/^.*[\\/]/, "");
    return base.replace(/\.[A-Za-z0-9]+$/, "") || base || "Sheet1";
  }

  /** sniffAndParse(filename, data) -> Promise<{kind, ...}>
   *  data: string | ArrayBuffer | Uint8Array. Dispatches on extension AND
   *  magic bytes: PK\x03\x04 -> xlsx, leading "{"/"[" (or .json) -> json,
   *  otherwise csv.
   *    xlsx -> {kind:"xlsx", sheets}
   *    csv  -> {kind:"csv",  sheets:[{name, rows}], delimiter}
   *    json -> {kind:"json", data} (JSON.parse verbatim) */
  async function sniffAndParse(filename, data) {
    const ext = extOf(filename);
    let text = null, bytes = null;
    if (typeof data === "string") {
      text = data;
    } else {
      bytes = data instanceof Uint8Array ? data : new Uint8Array(data);
      const isPK = bytes.length >= 4 && bytes[0] === 0x50 && bytes[1] === 0x4B &&
        bytes[2] === 0x03 && bytes[3] === 0x04;
      if (isPK || ext === "xlsx" || ext === "xlsm") {
        if (!isPK) {
          throw new Error(filename + ": has an Excel extension but is not a " +
            "ZIP container (legacy .xls and encrypted workbooks are not supported)");
        }
        const parsed = await parseXLSX(bytes);
        return { kind: "xlsx", sheets: parsed.sheets };
      }
      text = utf8Decode(bytes);
    }
    if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);
    const head = text.replace(/^\s+/, "");
    if (ext === "json" || head.startsWith("{") || head.startsWith("[")) {
      try {
        return { kind: "json", data: JSON.parse(text) };
      } catch (e) {
        if (ext === "json") {
          throw new Error(filename + ": invalid JSON — " + e.message);
        }
        // fall through: treat as CSV
      }
    }
    const { rows, delimiter } = parseCSV(text);
    return { kind: "csv", sheets: [{ name: stripExt(filename), rows }], delimiter };
  }

  // ------------------------------------------------------------------

  return {
    TB_ALIASES, SCHEDULE_ALIASES, SECTION_HEADERS,
    normHeader,
    parseCSV, sniffDelimiter,
    cleanAmount,
    detectHeader, rowsToObjects,
    parseXLSX, excelSerialToISO,
    sniffAndParse,
  };
});
