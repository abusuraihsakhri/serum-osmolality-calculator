const test = require("node:test");
const assert = require("node:assert/strict");
const { calculate } = require("../web/calculator.js");

test("conventional calculation and tonicity", () => {
  assert.deepEqual(calculate({ sodium: 140, glucose: 90, bun: 14 }), {
    calculated_osmolality: 290, effective_osmolality: 285,
    osmolal_gap: null, components: { sodium: 280, glucose: 5, urea: 5 }
  });
});

test("SI calculation and measured osmolal gap", () => {
  const r = calculate({ unit_system: "si", sodium: 140, glucose: 5, urea: 5, measured_osmolality: 300 });
  assert.equal(r.calculated_osmolality, 290);
  assert.equal(r.osmolal_gap, 10);
});

test("omitted measurement differs from an actual zero measurement", () => {
  assert.equal(calculate({ sodium: 140, glucose: 90, bun: 14 }).osmolal_gap, null);
  assert.equal(calculate({ sodium: 140, glucose: 90, bun: 14, measured_osmolality: 0 }).osmolal_gap, -290);
});

test("invalid values and incorrect unit combinations are rejected", () => {
  const base = { sodium: 140, glucose: 90, bun: 14 };
  for (const input of [{ ...base, glucose: "" }, { ...base, glucose: "Infinity" },
    { ...base, sodium: 0 }, { ...base, bun: -1 }, { ...base, glucose: true },
    { ...base, urea: 3 }, { ...base, unit_system: "si" }]) {
    assert.throws(() => calculate(input));
  }
});

test("rounded gap is derived from unrounded osmolality", () => {
  const r = calculate({ sodium: 140, glucose: 91, bun: 13, measured_osmolality: 300 });
  assert.equal(r.osmolal_gap, Math.round((300 - 280 - 91 / 18 - 13 / 2.8) * 100) / 100);
});


test("decimal inputs are accepted and overflow or object coercion is rejected", () => {
  assert.equal(calculate({ sodium: "140.5", glucose: "90.1", bun: "14.2" }).calculated_osmolality, 291.08);
  assert.throws(() => calculate({ sodium: 1e308, glucose: 0, bun: 0 }));
  assert.throws(() => calculate({ sodium: [140], glucose: 90, bun: 14 }));
});
