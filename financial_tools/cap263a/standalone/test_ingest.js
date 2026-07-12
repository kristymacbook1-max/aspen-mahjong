#!/usr/bin/env node
/* Tests for ingest.js — CSV/XLSX/JSON parsing, amount cleanup, header
 * detection. Plain Node asserts; run: node standalone/test_ingest.js */
"use strict";
const assert = require("assert");
const path = require("path");
const os = require("os");
const fs = require("fs");
const { execFileSync } = require("child_process");
const I = require("./ingest.js");

let failures = 0;
function test(name, fn) {
  try {
    const r = fn();
    if (r && typeof r.then === "function") {
      r.then(() => console.log("PASS  " + name))
        .catch(e => { failures++; console.log("FAIL  " + name + "\n      " + (e.stack || e)); });
      return r;
    }
    console.log("PASS  " + name);
  } catch (e) {
    failures++;
    console.log("FAIL  " + name + "\n      " + (e.stack || e));
  }
}

const asyncTests = [];
function atest(name, fn) { asyncTests.push([name, fn]); }

/* ---------------- CSV ---------------- */

test("csv: quoted commas + embedded newline + escaped quotes", () => {
  const text = 'a,b,c\n"1,2","he said ""hi""","line1\nline2"\n';
  const { rows, delimiter } = I.parseCSV(text);
  assert.strictEqual(delimiter, ",");
  assert.deepStrictEqual(rows, [
    ["a", "b", "c"],
    ["1,2", 'he said "hi"', "line1\nline2"],
  ]);
});

test("csv: BOM stripped", () => {
  const { rows } = I.parseCSV("﻿a,b\n1,2\n");
  assert.deepStrictEqual(rows, [["a", "b"], ["1", "2"]]);
});

test("csv: tab sniffing", () => {
  const { rows, delimiter } = I.parseCSV("a\tb\tc\n1\t2\t3\n4\t5\t6\n");
  assert.strictEqual(delimiter, "\t");
  assert.deepStrictEqual(rows, [["a", "b", "c"], ["1", "2", "3"], ["4", "5", "6"]]);
});

test("csv: semicolon sniffing", () => {
  const { rows, delimiter } = I.parseCSV("a;b\n1;2\n3;4\n");
  assert.strictEqual(delimiter, ";");
  assert.deepStrictEqual(rows, [["a", "b"], ["1", "2"], ["3", "4"]]);
});

test("csv: \\r\\n and bare \\r line endings", () => {
  const { rows } = I.parseCSV("a,b\r\n1,2\r3,4\r\n");
  assert.deepStrictEqual(rows, [["a", "b"], ["1", "2"], ["3", "4"]]);
});

/* ---------------- amounts ---------------- */

test("cleanAmount: currency, thousands, parens, signs, blanks", () => {
  const cases = [
    ["$1,234.56", "1234.56"],
    ["(500)", "-500"],
    ["1234.56", "1234.56"],
    ["-500", "-500"],
    ["+500", "500"],
    ["-", null],
    ["", null],
    [null, null],
    [undefined, null],
    ["$(1,000)", "-1000"],
    [".5", "0.5"],
    ["0", "0"],
    ["(0)", "0"],
    [1234.5, "1234.5"],
    [true, null],
    ["abc", null],
    ["1 234,56", null], // documented: European format not handled
  ];
  for (const [input, expected] of cases) {
    assert.strictEqual(I.cleanAmount(input), expected,
      `cleanAmount(${JSON.stringify(input)})`);
  }
});

/* ---------------- header detection ---------------- */

test("detectHeader: messy TB with title rows", () => {
  const rows = [
    ["Acme Manufacturing"],
    ["Trial Balance FY2026"],
    ["GL Acct", "Account Description", "Dept", "YTD Amount"],
    ["5000", "Direct labor", "100", "1,000,000"],
    ["7000", "Advertising", "400", "200,000"],
  ];
  const { headerIndex, mapping } = I.detectHeader(rows);
  assert.strictEqual(headerIndex, 2);
  assert.deepStrictEqual(mapping, {
    0: "acct_num", 1: "acct_desc", 2: "cc_num", 3: "amount",
  });
  const objs = I.rowsToObjects(rows, headerIndex, mapping);
  assert.strictEqual(objs.length, 2);
  assert.strictEqual(objs[0].acct_num, "5000");
  assert.strictEqual(objs[0].acct_desc, "Direct labor");
  assert.strictEqual(objs[0].cc_num, "100");
  assert.strictEqual(objs[0].amount, "1000000");
  assert.strictEqual(objs[1].amount, "200000");
});

test("rowsToObjects: skips blank + section-header rows", () => {
  const rows = [
    ["Account Description", "Amount"],
    ["Expenses"],           // section header, no amount
    [],                     // blank
    ["Direct labor", "5000"],
  ];
  const { headerIndex, mapping } = I.detectHeader(rows);
  const objs = I.rowsToObjects(rows, headerIndex, mapping);
  assert.strictEqual(objs.length, 1);
  assert.strictEqual(objs[0].acct_desc, "Direct labor");
});

/* ---------------- excelSerialToISO ---------------- */

test("excelSerialToISO: known dates + leap-year bug", () => {
  assert.strictEqual(I.excelSerialToISO(45658), "2025-01-01");
  assert.strictEqual(I.excelSerialToISO(60), null); // the nonexistent 1900-02-29
  assert.strictEqual(I.excelSerialToISO(59), "1900-02-28");
  assert.strictEqual(I.excelSerialToISO(61), "1900-03-01");
  assert.strictEqual(I.excelSerialToISO(1), "1900-01-01");
});

/* ---------------- sniffAndParse dispatch ---------------- */

atest("sniffAndParse: json by extension and by content", async () => {
  const r1 = await I.sniffAndParse("engagement.json", '{"a":1}');
  assert.strictEqual(r1.kind, "json");
  assert.deepStrictEqual(r1.data, { a: 1 });
  const r2 = await I.sniffAndParse("weird.txt", '[1,2,3]');
  assert.strictEqual(r2.kind, "json");
  assert.deepStrictEqual(r2.data, [1, 2, 3]);
});

atest("sniffAndParse: csv fallback", async () => {
  const r = await I.sniffAndParse("tb.csv", "a,b\n1,2\n");
  assert.strictEqual(r.kind, "csv");
  assert.strictEqual(r.sheets[0].name, "tb");
  assert.deepStrictEqual(r.sheets[0].rows, [["a", "b"], ["1", "2"]]);
});

atest("sniffAndParse: xlsx extension without PK magic throws", async () => {
  await assert.rejects(
    () => I.sniffAndParse("fake.xlsx", new Uint8Array([1, 2, 3, 4])),
    /not a ZIP container/);
});

/* ---------------- XLSX end-to-end (built via Python openpyxl) ---------------- */

atest("xlsx: real workbook round-trip (deflate, shared strings, 2 sheets, gaps)", async () => {
  const tmp = path.join(os.tmpdir(), "cap263a_ingest_test_" + process.pid + ".xlsx");
  const py = `
import openpyxl
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "TB"
ws.append(["Account Description", None, "Amount"])  # gap column B
ws.append(["Direct labor & materials", None, 1000000])
for i in range(40):
    ws.append([f"Row {i}", None, i])
ws2 = wb.create_sheet("Notes")
ws2["A1"] = "Special chars: caf\\u00e9 & <tag> \\"quoted\\""
wb.save(r"${tmp}")
`;
  execFileSync("python3", ["-c", py]);
  try {
    const buf = fs.readFileSync(tmp);
    const { sheets } = await I.parseXLSX(buf);
    assert.deepStrictEqual(sheets.map(s => s.name), ["TB", "Notes"]);
    const tb = sheets[0].rows;
    assert.strictEqual(tb.length, 42);
    assert.strictEqual(tb[0][0], "Account Description");
    assert.strictEqual(tb[0][1], ""); // gap column filled
    assert.strictEqual(tb[0][2], "Amount");
    assert.strictEqual(tb[1][0], "Direct labor & materials");
    assert.strictEqual(tb[1][2], 1000000);
    assert.strictEqual(tb[41][0], "Row 39");
    assert.strictEqual(tb[41][2], 39);
    assert.strictEqual(sheets[1].rows[0][0], 'Special chars: café & <tag> "quoted"');
  } finally {
    fs.unlinkSync(tmp);
  }
});

/* Minimal STORED (method 0, no compression) ZIP built by hand, containing one
 * worksheet part — covers the uncompressed-entry code path deflate-based
 * fixtures never exercise (openpyxl always deflates). */
function crc32(buf) {
  let table = crc32._table;
  if (!table) {
    table = crc32._table = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
      table[n] = c >>> 0;
    }
  }
  let crc = 0xFFFFFFFF;
  for (let i = 0; i < buf.length; i++) crc = table[(crc ^ buf[i]) & 0xFF] ^ (crc >>> 8);
  return (crc ^ 0xFFFFFFFF) >>> 0;
}

function buildStoredZip(files) {
  // files: [{name, data: Buffer}]
  const localParts = [];
  const centralParts = [];
  let offset = 0;
  for (const f of files) {
    const nameBuf = Buffer.from(f.name, "utf-8");
    const crc = crc32(f.data);
    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);   // version needed
    local.writeUInt16LE(0, 6);    // flags
    local.writeUInt16LE(0, 8);    // method: 0 = stored
    local.writeUInt16LE(0, 10);   // mod time
    local.writeUInt16LE(0, 12);   // mod date
    local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(f.data.length, 18); // comp size
    local.writeUInt32LE(f.data.length, 22); // uncomp size
    local.writeUInt16LE(nameBuf.length, 26);
    local.writeUInt16LE(0, 28);
    const localEntry = Buffer.concat([local, nameBuf, f.data]);
    localParts.push(localEntry);

    const central = Buffer.alloc(46);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE(20, 4);  // version made by
    central.writeUInt16LE(20, 6);  // version needed
    central.writeUInt16LE(0, 8);
    central.writeUInt16LE(0, 10);
    central.writeUInt16LE(0, 12);
    central.writeUInt16LE(0, 14);
    central.writeUInt32LE(crc, 16);
    central.writeUInt32LE(f.data.length, 20);
    central.writeUInt32LE(f.data.length, 24);
    central.writeUInt16LE(nameBuf.length, 28);
    central.writeUInt16LE(0, 30);
    central.writeUInt16LE(0, 32);
    central.writeUInt16LE(0, 34);
    central.writeUInt16LE(0, 36);
    central.writeUInt32LE(0, 38);
    central.writeUInt32LE(offset, 42);
    centralParts.push(Buffer.concat([central, nameBuf]));
    offset += localEntry.length;
  }
  const localBuf = Buffer.concat(localParts);
  const centralBuf = Buffer.concat(centralParts);
  const eocd = Buffer.alloc(22);
  eocd.writeUInt32LE(0x06054b50, 0);
  eocd.writeUInt16LE(0, 4);
  eocd.writeUInt16LE(0, 6);
  eocd.writeUInt16LE(files.length, 8);
  eocd.writeUInt16LE(files.length, 10);
  eocd.writeUInt32LE(centralBuf.length, 12);
  eocd.writeUInt32LE(localBuf.length, 16);
  eocd.writeUInt16LE(0, 20);
  return Buffer.concat([localBuf, centralBuf, eocd]);
}

atest("xlsx: hand-built STORED (uncompressed) zip entry", async () => {
  const workbookXml = '<?xml version="1.0"?><workbook><sheets>' +
    '<sheet name="Sheet1" r:id="rId1"/></sheets></workbook>';
  const relsXml = '<?xml version="1.0"?><Relationships>' +
    '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>';
  const sheetXml = '<?xml version="1.0"?><worksheet><sheetData>' +
    '<row r="1"><c r="A1" t="str"><v>hello</v></c>' +
    '<c r="B1"><v>42</v></c></row>' +
    '</sheetData></worksheet>';
  const zipBuf = buildStoredZip([
    { name: "xl/workbook.xml", data: Buffer.from(workbookXml, "utf-8") },
    { name: "xl/_rels/workbook.xml.rels", data: Buffer.from(relsXml, "utf-8") },
    { name: "xl/worksheets/sheet1.xml", data: Buffer.from(sheetXml, "utf-8") },
  ]);
  const { sheets } = await I.parseXLSX(new Uint8Array(zipBuf));
  assert.strictEqual(sheets.length, 1);
  assert.strictEqual(sheets[0].name, "Sheet1");
  assert.deepStrictEqual(sheets[0].rows, [["hello", 42]]);
});

/* ---------------- run ---------------- */

Promise.all(asyncTests.map(([name, fn]) => {
  const p = Promise.resolve().then(fn);
  return p.then(() => console.log("PASS  " + name))
    .catch(e => { failures++; console.log("FAIL  " + name + "\n      " + (e.stack || e)); });
})).then(() => {
  console.log("\n" + (failures ? failures + " failure(s)" : "all tests passed"));
  process.exit(failures ? 1 : 0);
});
