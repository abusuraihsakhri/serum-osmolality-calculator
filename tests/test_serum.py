"""Clinical calculation regression and numerical safety tests."""
import math
import pytest
from serum import calculate_osmolality
from osmolality import assess_row


def test_conventional_and_tonicity():
    result = calculate_osmolality(sodium=140, glucose=90, bun=14)
    assert result == {
        "calculated_osmolality": 290.0,
        "effective_osmolality": 285.0,
        "osmolal_gap": None,
    }


def test_measured_gap_can_be_negative_or_positive():
    assert calculate_osmolality(140, 90, 14, 300)["osmolal_gap"] == 10
    assert calculate_osmolality(140, 90, 14, 280)["osmolal_gap"] == -10


def test_si_units():
    result = calculate_osmolality(140, 5, unit_system="si", urea=5)
    assert result["calculated_osmolality"] == 290
    assert result["effective_osmolality"] == 285


def test_osmolal_gap_uses_unrounded_internal_value():
    value = calculate_osmolality(140, 91, 13, 300)
    expected = round(300 - (280 + 91 / 18 + 13 / 2.8), 2)
    assert value["osmolal_gap"] == expected


@pytest.mark.parametrize("data", [
    {"sodium": 140, "glucose": 90},
    {"sodium": None, "glucose": 90, "bun": 14},
    {"sodium": "NaN", "glucose": 90, "bun": 14},
    {"sodium": 140, "glucose": float("inf"), "bun": 14},
    {"sodium": 0, "glucose": 90, "bun": 14},
    {"sodium": 140, "glucose": -1, "bun": 14},
    {"sodium": 140, "glucose": 90, "bun": -1},
    {"sodium": True, "glucose": 90, "bun": 14},
    {"sodium": 140, "glucose": 90, "bun": 14, "urea": 5},
    {"sodium": 140, "glucose": 90, "bun": 14, "unit_system": "si"},
    {"sodium": 140, "glucose": 90, "bun": 14, "unit_system": "unsupported"},
])
def test_rejects_invalid_inputs(data):
    with pytest.raises(ValueError):
        calculate_osmolality(**data)


def test_row_routes_to_serum_first():
    r = assess_row({"sodium": "140", "glucose": "90", "bun": "14", "measured_osmolality": "300"})
    assert r["calculated_osmolality"] == 290
    assert r["osmolal_gap"] == 10


def test_row_reports_errors_instead_of_fabricated_values():
    r = assess_row({"sodium": "140", "glucose": "NaN", "bun": "14"})
    assert "error" in r


def test_api_calculate_schema():
    from fastapi.testclient import TestClient
    from agents.api import app
    client = TestClient(app)
    response = client.post("/api/osmolality", json={"sodium": 140, "glucose": 90, "bun": 14})
    assert response.status_code == 200
    assert response.json()["calculated_osmolality"] == 290
    assert client.post("/api/osmolality", json={"sodium": 140, "glucose": 90, "bun": 14, "unit_system": "si"}).status_code == 422
    assert client.get("/").status_code == 200
    assert client.get("/calculator.js").status_code == 200

def test_legacy_meld_uses_log_creatinine():
    from osmolality import calculate_meld_na
    value = calculate_meld_na(bilirubin=1, creatinine=4, inr=1, sodium=137)
    assert value["meld"] == pytest.approx(round(9.57 * math.log(4) + 6.43, 2))


def test_low_meld_not_adjusted_for_sodium():
    from osmolality import calculate_meld_na
    value = calculate_meld_na(bilirubin=1, creatinine=1, inr=1, sodium=125)
    assert value["meld_na"] == value["meld"]


def test_hmac_audit_detects_tampering():
    from agents.base import AuditTrail
    log = AuditTrail(secret_key="test-secret")
    log.log("actor", "system", "test", {"status": "ok"})
    assert log.verify_integrity()
    log.logs[0]["event_type"] = "tampered"
    assert not log.verify_integrity()


def test_extreme_inputs_reject_overflow():
    with pytest.raises(ValueError):
        calculate_osmolality(1e308, 0, 0)


def test_hmac_uses_unambiguous_serialization():
    from agents.base import AuditTrail
    log = AuditTrail(secret_key="test-secret")
    log.log("a|b", "c", "test", {"status": "ok"})
    log.logs[0]["actor"] = "a"
    log.logs[0]["actor_tier"] = "b|c"
    assert not log.verify_integrity()
