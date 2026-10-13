"""Deterministic serum osmolality estimates (not a measured laboratory result).

Conventional: 2*Na (mmol/L) + glucose (mg/dL)/18 + BUN (mg/dL)/2.8.
SI:           2*Na (mmol/L) + glucose (mmol/L) + urea (mmol/L).
Tonicity excludes urea; osmolal gap is measured minus calculated.
"""
import math
from typing import Any, Dict, Optional


def _number(name: str, value: Any, *, strictly_positive: bool = False) -> float:
    if isinstance(value, bool) or value is None or isinstance(value, (list, dict)):
        raise ValueError(f"{name} must be a finite numeric value")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{name} must be a finite numeric value") from None
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite numeric value")
    if number < 0 or (strictly_positive and number == 0):
        raise ValueError(f"{name} must be {'greater than zero' if strictly_positive else 'non-negative'}")
    return number


def calculate_osmolality(
    sodium: Any,
    glucose: Any,
    bun: Any = None,
    measured_osmolality: Any = None,
    *,
    unit_system: str = "conventional",
    urea: Any = None,
) -> Dict[str, Optional[float]]:
    """Calculate serum osmolality and effective osmolality (mOsm/kg, approximate).

    For conventional units, sodium is mmol/L, glucose and BUN are mg/dL.
    For SI, sodium, glucose and urea are mmol/L. Do not enter BUN as urea.
    """
    if unit_system not in ("conventional", "si"):
        raise ValueError("unit_system must be 'conventional' or 'si'")
    na = _number("sodium", sodium, strictly_positive=True)
    glu = _number("glucose", glucose)
    if unit_system == "conventional":
        if urea is not None:
            raise ValueError("Use bun (mg/dL), not urea, for conventional units")
        nitrogen = _number("bun", bun)
        glucose_component = glu / 18.0
        urea_component = nitrogen / 2.8
    else:
        if bun is not None:
            raise ValueError("Use urea (mmol/L), not bun, for SI units")
        nitrogen = _number("urea", urea)
        glucose_component = glu
        urea_component = nitrogen
    effective = 2.0 * na + glucose_component
    calculated = effective + urea_component
    measured = None if measured_osmolality is None or measured_osmolality == "" else _number(
        "measured_osmolality", measured_osmolality
    )
    return {
        "calculated_osmolality": round(calculated, 2),
        "effective_osmolality": round(effective, 2),
        "osmolal_gap": round(measured - calculated, 2) if measured is not None else None,
    }
