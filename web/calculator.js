/* Dependency-free serum osmolality calculation shared by the browser and Node tests. */
(function (root) {
  "use strict";
  function numeric(name, value, positive) {
    if (value === "" || value === null || value === undefined || (typeof value !== "number" && typeof value !== "string")) {
      throw new Error(name + " is required.");
    }
    if (typeof value === "string" && !/^[+-]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)(?:e[+-]?[0-9]+)?$/i.test(value.trim())) {
      throw new Error(name + " must be a decimal number.");
    }
    const number = Number(value);
    if (!Number.isFinite(number)) throw new Error(name + " must be a finite number.");
    if (number < 0 || (positive && number === 0)) {
      throw new Error(name + " must be " + (positive ? "greater than zero." : "non-negative."));
    }
    return number;
  }
  const round2 = x => Math.round((x + Number.EPSILON) * 100) / 100;
  function calculate(input) {
    const units = input.unit_system || "conventional";
    if (units !== "conventional" && units !== "si") throw new Error("Invalid unit system.");
    const sodium = numeric("Sodium", input.sodium, true);
    const glucose = numeric("Glucose", input.glucose, false);
    let glucosePart, ureaPart;
    if (units === "si") {
      if (input.bun !== undefined && input.bun !== null) throw new Error("Use urea for SI units.");
      glucosePart = glucose;
      ureaPart = numeric("Urea", input.urea, false);
    } else {
      if (input.urea !== undefined && input.urea !== null) throw new Error("Use BUN for conventional units.");
      glucosePart = glucose / 18;
      ureaPart = numeric("BUN", input.bun, false) / 2.8;
    }
    const effective = 2 * sodium + glucosePart;
    const calculated = effective + ureaPart;
    if (!Number.isFinite(calculated)) throw new Error("Computed osmolality is outside the supported numeric range.");
    const measured = input.measured_osmolality === undefined || input.measured_osmolality === null ||
      input.measured_osmolality === "" ? null : numeric("Measured osmolality", input.measured_osmolality, false);
    return {
      calculated_osmolality: round2(calculated),
      effective_osmolality: round2(effective),
      osmolal_gap: measured === null ? null : round2(measured - calculated),
      components: { sodium: round2(2 * sodium), glucose: round2(glucosePart), urea: round2(ureaPart) }
    };
  }
  const api = { calculate };
  root.SerumCalculator = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
