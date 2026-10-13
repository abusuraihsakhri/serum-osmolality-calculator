"""
Focused tests for core clinical calculation functions in osmolality.py.
"""
import sys
import math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import osmolality as m


# ---------------------------------------------------------------------------
# calculate_score
# ---------------------------------------------------------------------------

class TestCalculateScore:
    def test_basic_numeric_inputs(self):
        r = m.calculate_score(a=10, b=20)
        assert isinstance(r, dict)
        assert "score" in r
        assert "inputs" in r
        assert r["inputs"] == 2

    def test_empty_input_uses_default(self):
        r = m.calculate_score()
        assert r["inputs"] == 1
        assert r["score"] > 0

    def test_string_numeric_values(self):
        r = m.calculate_score(x="5.5", y="4.5")
        assert r["inputs"] == 2

    def test_mixed_types_ignores_non_numeric(self):
        r = m.calculate_score(a=10, b="hello", c=None, d=20.0)
        assert r["inputs"] == 2


# ---------------------------------------------------------------------------
# calculate_meld_na
# ---------------------------------------------------------------------------

class TestCalculateMeldNa:
    def test_basic_calculation(self):
        r = m.calculate_meld_na(bilirubin=2.0, creatinine=1.5, inr=1.2, sodium=135)
        assert "meld_na" in r
        assert "meld" in r
        assert 6 <= r["meld_na"] <= 40
        assert 6 <= r["meld"] <= 40

    def test_dialysis_pins_creatinine(self):
        r = m.calculate_meld_na(bilirubin=1.0, creatinine=1.0, inr=1.0, sodium=137, dialysis=True)
        assert r["meld_na"] >= 6

    def test_missing_values_use_defaults(self):
        r = m.calculate_meld_na(bilirubin=2.0, creatinine=1.5, inr=None, sodium=None)
        assert "meld_na" in r

    def test_clamps_extreme_values(self):
        r = m.calculate_meld_na(bilirubin=0.01, creatinine=0.1, inr=0.5, sodium=160)
        assert r["meld_na"] <= 40


# ---------------------------------------------------------------------------
# calculate_qtc
# ---------------------------------------------------------------------------

class TestCalculateQtc:
    def test_basic_bazett(self):
        r = m.calculate_qtc(qt_ms=400, hr_bpm=60)
        assert "qtc_ms" in r
        assert r["qtc_ms"] > 0

    def test_with_rr(self):
        r = m.calculate_qtc(qt_ms=400, rr_ms=1000)
        assert abs(r["qtc_ms"] - 400.0) < 1.0

    def test_missing_qt_returns_error(self):
        r = m.calculate_qtc(qt_ms=None, hr_bpm=60)
        assert "error" in r


# ---------------------------------------------------------------------------
# calculate_bmi_z
# ---------------------------------------------------------------------------

class TestCalculateBmiZ:
    def test_basic_bmi(self):
        r = m.calculate_bmi_z(weight_kg=70, height_cm=175)
        assert "bmi" in r
        assert 22.0 < r["bmi"] < 23.0

    def test_missing_required_returns_error(self):
        r = m.calculate_bmi_z(weight_kg=None, height_cm=175)
        assert "error" in r

    def test_zero_height_returns_error(self):
        r = m.calculate_bmi_z(weight_kg=70, height_cm=0)
        assert "error" in r


# ---------------------------------------------------------------------------
# convert_hba1c
# ---------------------------------------------------------------------------

class TestConvertHba1c:
    def test_hba1c_to_eag(self):
        r = m.convert_hba1c(hba1c_percent=7.0)
        assert "eag_mgdl" in r
        assert r["eag_mgdl"] > 0

    def test_eag_to_hba1c(self):
        r = m.convert_hba1c(eag_mgdl=154.0)
        assert "hba1c_percent" in r
        assert 5.0 < r["hba1c_percent"] < 8.0

    def test_no_input_returns_error(self):
        r = m.convert_hba1c()
        assert "error" in r


# ---------------------------------------------------------------------------
# calculate_apri_fib4
# ---------------------------------------------------------------------------

class TestCalculateApriFib4:
    def test_basic_apri(self):
        r = m.calculate_apri_fib4(ast_u_l=80, alt_u_l=40, platelets_109=200, age_years=45)
        assert "apri" in r
        assert "fib4" in r
        assert r["apri"] > 0

    def test_missing_required_returns_error(self):
        r = m.calculate_apri_fib4(ast_u_l=None, platelets_109=200)
        assert "error" in r

    def test_zero_platelets_safe(self):
        r = m.calculate_apri_fib4(ast_u_l=40, alt_u_l=40, platelets_109=0, age_years=40)
        assert r["apri"] > 0  # no crash


# ---------------------------------------------------------------------------
# assess_row routing
# ---------------------------------------------------------------------------

class TestAssessRow:
    def test_routes_to_meld_na(self):
        r = m.assess_row({"bilirubin": 2.0, "creatinine": 1.5, "inr": 1.2, "sodium": 135})
        assert "meld_na" in r

    def test_routes_to_qtc(self):
        r = m.assess_row({"qt_ms": 400, "hr_bpm": 60})
        assert "qtc_ms" in r

    def test_routes_to_bmi(self):
        r = m.assess_row({"weight_kg": 70, "height_cm": 175})
        assert "bmi" in r

    def test_routes_to_hba1c(self):
        r = m.assess_row({"hba1c_percent": 7.0})
        assert "eag_mgdl" in r

    def test_routes_to_apri(self):
        r = m.assess_row({"ast_u_l": 80, "platelets_109": 200})
        assert "apri" in r

    def test_unknown_fields_are_rejected(self):
        r = m.assess_row({"value": 10})
        assert "error" in r

    def test_non_dict_input_returns_error(self):
        r = m.assess_row("not a dict")  # type: ignore
        assert "error" in r


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------

class TestPathValidation:
    def test_rejects_traversal(self):
        with pytest.raises(ValueError):
            m._validate_safe_path("../../etc/passwd")

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            m._validate_safe_path("")

    def test_accepts_safe_relative(self):
        p = m._validate_safe_path("sample.csv", must_exist=True)
        assert p.exists()


# ---------------------------------------------------------------------------
# process_csv
# ---------------------------------------------------------------------------

class TestProcessCsv:
    def test_batch_processing(self, tmp_path):
        # create input CSV
        inp = tmp_path / "input.csv"
        inp.write_text("id,value,qty\nA,10,2\nB,20,3\n", encoding="utf-8")
        out = tmp_path / "output.csv"
        results = m.process_csv(str(inp), str(out))
        assert len(results) == 2
        assert out.exists()

    def test_traversal_rejected(self, tmp_path):
        inp = tmp_path / "input.csv"
        inp.write_text("id,value\nA,10\n", encoding="utf-8")
        with pytest.raises(ValueError):
            m.process_csv(str(inp), "../etc/output.csv")
