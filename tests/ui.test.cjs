const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

test("form renders results and handles SI units and validation without a server", () => {
  const ids = [
    "calculator-form", "units", "results", "empty-state", "errors",
    "calculated", "effective", "gap", "sodium-part", "glucose-part", "urea-part",
    "sodium", "glucose", "nitrogen", "measured", "glucose-unit", "nitrogen-label",
    "nitrogen-unit", "formula"
  ];
  const html = fs.readFileSync(path.join(__dirname, "../web/index.html"), "utf8");
  for (const id of ids) assert.ok(html.includes('id="' + id + '"'), "Missing form element " + id);
  const elements = Object.fromEntries(ids.map(id => [id, {
    value: "", textContent: "", hidden: false, handlers: {},
    addEventListener(event, cb) { this.handlers[event] = cb; },
    reportValidity() { return true; }
  }]));
  elements.units.value = "conventional";
  elements.results.hidden = true;
  global.document = { getElementById: id => elements[id] };
  global.window = { requestAnimationFrame: callback => callback() };
  global.SerumCalculator = require("../web/calculator.js");
  require("../web/app.js");
  elements.sodium.value = "140";
  elements.glucose.value = "90";
  elements.nitrogen.value = "14";
  elements.measured.value = "300";
  elements["calculator-form"].handlers.submit({ preventDefault() {} });
  assert.equal(elements.calculated.textContent, "290.00");
  assert.equal(elements.effective.textContent, "285.00");
  assert.equal(elements.gap.textContent, "10.00");
  assert.equal(elements.results.hidden, false);
  assert.equal(elements["empty-state"].hidden, true);
  elements.units.value = "si";
  elements.units.handlers.change();
  assert.equal(elements.glucose.value, "");
  assert.equal(elements.nitrogen.value, "");
  assert.equal(elements["glucose-unit"].textContent, "mmol/L");
  elements.glucose.value = "5";
  elements.nitrogen.value = "5";
  elements["calculator-form"].handlers.submit({ preventDefault() {} });
  assert.equal(elements.calculated.textContent, "290.00");
  elements.glucose.value = "-5";
  elements["calculator-form"].handlers.submit({ preventDefault() {} });
  assert.match(elements.errors.textContent, /non-negative/);
  assert.equal(elements.results.hidden, true);
  elements.units.value = "conventional";
  elements["calculator-form"].handlers.reset();
  assert.equal(elements["glucose-unit"].textContent, "mg/dL");
});
