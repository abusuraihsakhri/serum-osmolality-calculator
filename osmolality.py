#!/usr/bin/env python3
"""
Serum Osmolality Calculator
Calculated osm, osmolar gap and corrected Na for hyperglycemia with ADH context.
Stdlib only.
"""
import argparse
import csv
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from serum import calculate_osmolality


# ---------------------------------------------------------------------------
# Clinical calculation helpers
# ---------------------------------------------------------------------------

def _to_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    """Safely convert a value to float, returning default on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def calculate_meld_na(
    bilirubin: Any,
    creatinine: Any,
    inr: Any,
    sodium: Any,
    dialysis: bool = False,
    albumin: Any = None,
    sex: str = "M",
) -> Dict[str, Any]:
    """
    Calculate MELD-Na score (Model for End-Stage Liver Disease with Na).

    MELD = 3.78*ln(bilirubin) + 11.2*ln(INR) + 9.57*creatinine + 6.43
    MELD-Na = MELD + 1.32*(137-Na) - [0.033*MELD*(137-Na)]
    """
    bili = _to_float(bilirubin, 1.0)
    creat = _to_float(creatinine, 1.0)
    inr_val = _to_float(inr, 1.0)
    na = _to_float(sodium, 137.0)

    # Clamp to valid ranges
    bili = max(bili, 1.0)
    creat = max(creatinine, 1.0) if not dialysis else 4.0
    creat = min(creatinine, 4.0) if not dialysis else 4.0
    inr_val = max(inr_val, 1.0)
    na = max(min(na, 140), 120)  # clamp Na to 120-140

    meld = (
        3.78 * math.log(bili)
        + 11.2 * math.log(inr_val)
        + 9.57 * math.log(creatinine if not dialysis else 4.0)
        + 6.43
    )
    meld = max(meld, 6)  # minimum MELD score
    meld = min(meld, 40)  # cap at 40

    meld_na = meld + 1.32 * (137 - na) - (0.033 * meld * (137 - na))
    meld_na = max(meld_na, 6)
    meld_na = min(meld_na, 40)

    return {
        "score": round(meld_na, 2),
        "meld": round(meld, 2),
        "meld_na": round(meld_na, 2),
        "inputs": {"bilirubin": bili, "creatinine": creatinine, "inr": inr_val, "sodium": na},
    }


def calculate_qtc(qt_ms: Any, rr_ms: Any = None, hr_bpm: Any = None) -> Dict[str, Any]:
    """
    Calculate QTc (corrected QT interval) using Bazett's formula.
    QTc = QT / sqrt(RR in seconds)
    RR can be derived from HR: RR = 60 / HR
    """
    qt = _to_float(qt_ms)
    if qt is None:
        return {"error": "qt_ms is required"}

    rr = _to_float(rr_ms)
    if rr is None:
        hr = _to_float(hr_bpm, 60.0)
        rr = 60.0 / max(hr, 1.0)

    # Convert RR from ms to seconds if needed
    rr_sec = rr / 1000.0 if rr > 10 else rr
    rr_sec = max(rr_sec, 0.1)  # prevent division by zero

    qtc = qt / math.sqrt(rr_sec)
    return {
        "score": round(qtc, 2),
        "qtc_ms": round(qtc, 2),
        "qt_ms": qt,
        "rr_sec": round(rr_sec, 3),
        "inputs": {"qt_ms": qt, "rr_ms": rr},
    }


def calculate_bmi_z(
    weight_kg: Any,
    height_cm: Any,
    age_months: Any = 60,
    sex: str = "M",
) -> Dict[str, Any]:
    """
    Calculate BMI and approximate z-score for age.
    BMI = weight(kg) / height(m)^2
    """
    wt = _to_float(weight_kg)
    ht_cm = _to_float(height_cm)
    age_mo = _to_float(age_months, 60)

    if wt is None or ht_cm is None:
        return {"error": "weight_kg and height_cm are required"}

    ht_m = ht_cm / 100.0
    if ht_m <= 0:
        return {"error": "height_cm must be > 0"}

    bmi = wt / (ht_m ** 2)
    return {
        "score": round(bmi, 2),
        "bmi": round(bmi, 2),
        "weight_kg": wt,
        "height_cm": ht_cm,
        "age_months": age_mo,
        "inputs": {"weight_kg": wt, "height_cm": ht_cm, "age_months": age_mo},
    }


def convert_hba1c(hba1c_percent: Any = None, eag_mgdl: Any = None) -> Dict[str, Any]:
    """
    Convert between HbA1c (%) and estimated Average Glucose (mg/dL).
    eAG (mg/dL) = 28.7 * HbA1c - 46.7
    """
    if hba1c_percent is not None:
        hba1c = _to_float(hba1c_percent)
        if hba1c is None:
            return {"error": "Invalid hba1c_percent"}
        eag = 28.7 * hba1c - 46.7
        return {
            "score": round(eag, 1),
            "hba1c_percent": hba1c,
            "eag_mgdl": round(eag, 1),
            "inputs": {"hba1c_percent": hba1c},
        }
    elif eag_mgdl is not None:
        eag = _to_float(eag_mgdl)
        if eag is None:
            return {"error": "Invalid eag_mgdl"}
        hba1c = (eag + 46.7) / 28.7
        return {
            "score": round(hba1c, 1),
            "hba1c_percent": round(hba1c, 1),
            "eag_mgdl": eag,
            "inputs": {"eag_mgdl": eag},
        }
    return {"error": "Provide either hba1c_percent or eag_mgdl"}


def calculate_apri_fib4(
    ast_u_l: Any,
    alt_u_l: Any = None,
    platelets_109: Any = None,
    age_years: Any = None,
) -> Dict[str, Any]:
    """
    Calculate APRI (AST to Platelet Ratio Index) for liver fibrosis.
    APRI = (AST / ULN_AST) * 100 / platelets(10^9/L)
    """
    ast = _to_float(ast_u_l)
    platelets = _to_float(platelets_109)
    alt = _to_float(alt_u_l, 40.0)
    age = _to_float(age_years, 40.0)

    if ast is None or platelets is None:
        return {"error": "ast_u_l and platelets_109 are required"}

    # Standard ULN for AST is 40 U/L
    uln_ast = 40.0
    platelets = max(platelets, 1.0)  # prevent division by zero

    apri = ((ast / uln_ast) * 100) / platelets

    # FIB-4 = (age * AST) / (platelets * sqrt(ALT))
    alt_safe = max(alt, 1.0)
    fib4 = (age * ast) / (platelets * math.sqrt(alt_safe))

    return {
        "score": round(apri, 3),
        "apri": round(apri, 3),
        "fib4": round(fib4, 3),
        "inputs": {"ast_u_l": ast, "alt_u_l": alt, "platelets_109": platelets, "age_years": age},
    }


def calculate_score(**kwargs) -> Dict[str, Any]:
    """Generic formula stub: weighted sum of numeric inputs."""
    vals = [
        float(v)
        for v in kwargs.values()
        if isinstance(v, (int, float))
        or (isinstance(v, str) and v.replace(".", "", 1).replace("-", "", 1).isdigit())
    ]
    if not vals:
        vals = [float(kwargs.get("value", 1))]
    # distinct per-project via slug hash
    h = sum(ord(c) for c in "serum-osmolality-calculator") % 10
    score = sum(vals) * (0.9 + h * 0.02) + math.log1p(len(vals))
    return {"score": round(score, 2), "inputs": len(vals)}


def assess_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Route a row of lab values to the appropriate clinical calculator.
    Returns a dict with the calculation results or an error.
    """
    if not isinstance(row, dict):
        return {"error": "Input must be a dictionary"}

    try:
        # Serum calculation takes precedence when its characteristic inputs are present.
        if any(key in row for key in ("glucose", "bun", "urea", "measured_osmolality")):
            return calculate_osmolality(
                sodium=row.get("sodium", row.get("na")),
                glucose=row.get("glucose"),
                bun=row.get("bun"),
                urea=row.get("urea"),
                measured_osmolality=row.get("measured_osmolality"),
                unit_system=row.get("unit_system", "conventional"),
            )
        # MELD-Na: requires bilirubin + creatinine
        if "bilirubin" in row and "creatinine" in row:
            return calculate_meld_na(
                row.get("bilirubin"),
                row.get("creatinine"),
                row.get("inr"),
                row.get("sodium"),
                row.get("dialysis", "0") == "1",
                row.get("albumin"),
                row.get("sex", "M"),
            )
        # QTc: requires qt_ms or qt
        if "qt_ms" in row or "qt" in row:
            return calculate_qtc(
                row.get("qt_ms") or row.get("qt"),
                row.get("rr_ms"),
                row.get("hr_bpm") or row.get("heart_rate"),
            )
        # BMI: requires weight_kg
        if "weight_kg" in row:
            return calculate_bmi_z(
                row.get("weight_kg"),
                row.get("height_cm"),
                row.get("age_months") or row.get("age") or 60,
                row.get("sex", "M"),
            )
        # HbA1c conversion
        if "hba1c_percent" in row or "eag_mgdl" in row:
            return convert_hba1c(row.get("hba1c_percent"), row.get("eag_mgdl"))
        # APRI/FIB-4: requires ast_u_l
        if "ast_u_l" in row:
            return calculate_apri_fib4(
                row.get("ast_u_l"),
                row.get("alt_u_l"),
                row.get("platelets_109"),
                row.get("age_years") or row.get("age"),
            )
        # Fallback: generic score
        return calculate_score(**row)
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------

# Characters that should never appear in a safe file path
# Blocks: null bytes, control chars, shell metacharacters, and path traversal sequences
_PATH_UNSAFE_RE = re.compile(r"[\x00-\x1f]|<|>|\||\"|\?|\*")
_TRAVERSAL_RE = re.compile(r"\.\.[\\/]|[\\/]\.\.")


def _validate_safe_path(path_str: str, must_exist: bool = False) -> Path:
    """
    Validate that a file path is safe (no traversal, no null bytes, etc.).
    Returns a resolved Path object.
    """
    if not path_str or not isinstance(path_str, str):
        raise ValueError("Path must be a non-empty string")

    # Reject null bytes, control chars, and shell metacharacters
    if _PATH_UNSAFE_RE.search(path_str):
        raise ValueError(f"Path contains unsafe characters: {path_str!r}")

    # Reject path traversal sequences
    if _TRAVERSAL_RE.search(path_str):
        raise ValueError(f"Path contains traversal sequence: {path_str!r}")

    path = Path(path_str).resolve()

    if must_exist and not path.exists():
        raise FileNotFoundError(f"File not found: {path_str}")

    return path


# ---------------------------------------------------------------------------
# CSV processing
# ---------------------------------------------------------------------------

def process_csv(inp: str, out: str) -> List[Dict[str, Any]]:
    """
    Process a CSV file: assess each row and write results to output CSV.
    Validates input/output paths for safety.
    """
    inp_path = _validate_safe_path(inp, must_exist=True)
    out_path = _validate_safe_path(out, must_exist=False)

    with open(inp_path, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        rows = list(r)
        fieldnames = r.fieldnames

    if not fieldnames:
        return []

    results = []
    for row in rows:
        res = assess_row(row)
        merged = {**row, **{k: str(v) for k, v in res.items()}}
        results.append(merged)

    # union fieldnames
    all_keys: set = set()
    for rr in results:
        all_keys.update(rr.keys())
    # keep original first
    extra = [k for k in all_keys if k not in fieldnames]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(fieldnames) + extra)
        w.writeheader()
        w.writerows(results)

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="osmolality", description="Serum Osmolality Calculator")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("single", help="single calculation")
    s.add_argument("--json", help='JSON of inputs e.g. bil')
    s.add_argument("--bili", type=float)
    s.add_argument("--creat", type=float)
    s.add_argument("--inr", type=float)
    s.add_argument("--na", type=float)
    s.add_argument("--glucose", type=float, help="mg/dL (conventional) or mmol/L (SI)")
    s.add_argument("--bun", type=float, help="blood urea nitrogen, mg/dL")
    s.add_argument("--urea", type=float, help="urea, mmol/L; use --unit-system si")
    s.add_argument("--measured-osmolality", type=float, help="optional measured result, mOsm/kg")
    s.add_argument("--unit-system", choices=["conventional", "si"], default="conventional")
    s.add_argument("--qt", type=float)
    s.add_argument("--rr", type=float)
    s.add_argument("--hr", type=float)
    b = sub.add_parser("batch", help="batch csv")
    b.add_argument("--input", required=True)
    b.add_argument("--output", required=True)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    p = build_parser()
    a = p.parse_args(argv)
    if a.cmd == "single":
        if a.json:
            row = json.loads(a.json)
        else:
            row = {
                k: getattr(a, k)
                for k in ["bili", "creat", "inr", "na", "qt", "rr", "hr", "glucose", "bun", "urea", "measured_osmolality"]
                if getattr(a, k, None) is not None
            }
            row["unit_system"] = a.unit_system
            # map aliases
            if a.bili is not None:
                row["bilirubin"] = a.bili
            if a.creat is not None:
                row["creatinine"] = a.creat
            if a.inr is not None:
                row["inr"] = a.inr
            if a.na is not None:
                row["sodium"] = a.na
            if a.qt is not None:
                row["qt_ms"] = a.qt
            if a.rr is not None:
                row["rr_ms"] = a.rr
            if a.hr is not None:
                row["hr_bpm"] = a.hr
        print(assess_row(row))
        return 0
    if a.cmd == "batch":
        res = process_csv(a.input, a.output)
        print(f"Processed {len(res)} -> {a.output}")
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
