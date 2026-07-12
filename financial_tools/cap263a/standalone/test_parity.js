#!/usr/bin/env node
/* Node parity harness: engines.js vs Python goldens.json.
 * Run: node financial_tools/cap263a/standalone/test_parity.js */
"use strict";
const fs = require("fs");
const path = require("path");
const SELFTEST = require("./selftest.js");

const goldens = JSON.parse(
  fs.readFileSync(path.join(__dirname, "goldens.json"), "utf-8"));
const results = SELFTEST.runAll(goldens);

let failed = 0;
for (const r of results) {
  if (r.pass) {
    console.log("PASS  " + r.name);
  } else {
    failed++;
    console.log("FAIL  " + r.name);
    for (const d of r.diffs) console.log("      " + d.split("\n").join("\n      "));
  }
}
console.log("\n" + (results.length - failed) + "/" + results.length + " scenarios pass");
process.exit(failed ? 1 : 0);
