"use strict";
const form = document.getElementById("calculator-form");
const unitSelect = document.getElementById("units");
const resultPanel = document.getElementById("results");
const emptyState = document.getElementById("empty-state");
const errors = document.getElementById("errors");
const output = {
  calculated: document.getElementById("calculated"),
  effective: document.getElementById("effective"),
  gap: document.getElementById("gap"),
  sodium: document.getElementById("sodium-part"),
  glucose: document.getElementById("glucose-part"),
  urea: document.getElementById("urea-part")
};

function changeUnits() {
  const si = unitSelect.value === "si";
  document.getElementById("glucose-unit").textContent = si ? "mmol/L" : "mg/dL";
  document.getElementById("nitrogen-label").textContent = si ? "Urea" : "Blood urea nitrogen (BUN)";
  document.getElementById("nitrogen-unit").textContent = si ? "mmol/L" : "mg/dL";
  document.getElementById("formula").textContent = si
    ? "2 × sodium + glucose + urea (all in mmol/L)"
    : "2 × sodium + glucose ÷ 18 + BUN ÷ 2.8";
  // Clear unit-dependent values rather than silently reinterpret a previous entry.
  document.getElementById("glucose").value = "";
  document.getElementById("nitrogen").value = "";
  clearResult();
}
function clearResult() {
  errors.textContent = "";
  resultPanel.hidden = true;
  emptyState.hidden = false;
}
function format(value) {
  return value === null ? "Not provided" : value.toFixed(2);
}
form.addEventListener("submit", (event) => {
  event.preventDefault();
  clearResult();
  if (!form.reportValidity()) return;
  const si = unitSelect.value === "si";
  const input = {
    unit_system: unitSelect.value,
    sodium: document.getElementById("sodium").value,
    glucose: document.getElementById("glucose").value,
    measured_osmolality: document.getElementById("measured").value
  };
  input[si ? "urea" : "bun"] = document.getElementById("nitrogen").value;
  try {
    const value = SerumCalculator.calculate(input);
    output.calculated.textContent = format(value.calculated_osmolality);
    output.effective.textContent = format(value.effective_osmolality);
    output.gap.textContent = format(value.osmolal_gap);
    output.sodium.textContent = format(value.components.sodium);
    output.glucose.textContent = format(value.components.glucose);
    output.urea.textContent = format(value.components.urea);
    resultPanel.hidden = false;
    emptyState.hidden = true;
  } catch (error) {
    errors.textContent = error.message;
  }
});
unitSelect.addEventListener("change", changeUnits);
form.addEventListener("reset", () => {
  // reset event fires before the inputs revert to their defaults
  window.requestAnimationFrame(() => {
    document.getElementById("glucose-unit").textContent = "mg/dL";
    document.getElementById("nitrogen-label").textContent = "Blood urea nitrogen (BUN)";
    document.getElementById("nitrogen-unit").textContent = "mg/dL";
    document.getElementById("formula").textContent = "2 × sodium + glucose ÷ 18 + BUN ÷ 2.8";
    clearResult();
  });
});
