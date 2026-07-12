import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from app.api.main import app
from app.api.schemas import EvaluateResponse

client = TestClient(app)

V1 = "/api/v1"


# --- ops (no DB dependency for /version; /health pings DB) ------------------

@pytest.mark.integration
def test_health_reports_connected_db():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
    assert body["version"]


def test_version_route():
    r = client.get("/version")
    assert r.status_code == 200
    body = r.json()
    assert body["engine_version"]
    assert body["api_version"]
    assert "validation_report" in body   # string or null


# --- discovery -------------------------------------------------------------

@pytest.mark.integration
def test_races_lists_generatable_and_blocked():
    r = client.get(f"{V1}/races")
    assert r.status_code == 200
    by_key = {row["circuit_key"]: row for row in r.json()}
    assert by_key["bahrain"]["can_generate"] is True
    assert by_key["australian"]["can_generate"] is False
    assert by_key["australian"]["reason"]
    assert by_key["bahrain"]["total_laps"] == 57


# --- strategy evaluate -----------------------------------------------------

@pytest.mark.integration
def test_evaluate_bahrain_shape_and_invariants():
    r = client.post(f"{V1}/strategy/evaluate", json={"circuit_key": "bahrain", "n_sims": 500})
    assert r.status_code == 200
    body = r.json()

    assert 0 < len(body["strategies"]) <= 8
    assert body["deterministic_top_key"]
    assert body["robust_top_key"]
    assert body["runtime_ms"] >= 0
    assert body["n_strategies_generated"] > 1000

    # breakdown components sum to total for every returned strategy
    for s in body["strategies"]:
        b = s["breakdown"]
        parts = b["base_s"] + b["compound_offset_s"] + b["degradation_s"] + b["fuel_s"] + b["pit_s"]
        assert parts == pytest.approx(b["total_s"], abs=1e-6)

    # multiset dedup held: all returned shapes are distinct keys
    keys = [s["key"] for s in body["strategies"]]
    assert len(set(keys)) == len(keys)

    # win-probabilities are present, in [0,1], and sum to ~1 across the displayed set
    probs = [s["win_probability"] for s in body["strategies"]]
    assert all(0.0 <= p <= 1.0 for p in probs)
    assert sum(probs) == pytest.approx(1.0, abs=1e-6)

    # each strategy carries a 32-bin histogram whose counts sum to n_sims on the shared domain
    assert body["histogram_hi"] > body["histogram_lo"]
    for s in body["strategies"]:
        assert len(s["histogram"]) == 32
        assert sum(s["histogram"]) == 500  # n_sims for this request


@pytest.mark.integration
def test_evaluate_response_has_no_raw_samples_anywhere():
    """The 2000-element samples array must never cross the wire."""
    r = client.post(f"{V1}/strategy/evaluate", json={"circuit_key": "bahrain", "n_sims": 300})
    assert "samples" not in r.text


@pytest.mark.integration
def test_evaluate_response_validates_against_schema():
    r = client.post(f"{V1}/strategy/evaluate", json={"circuit_key": "bahrain", "n_sims": 300})
    assert r.status_code == 200
    EvaluateResponse.model_validate(r.json())   # raises if the shape drifts


@pytest.mark.integration
def test_evaluate_australian_is_unprocessable():
    r = client.post(f"{V1}/strategy/evaluate", json={"circuit_key": "australian"})
    assert r.status_code == 422
    assert "two-compound" in r.json()["detail"]


@pytest.mark.integration
def test_evaluate_unknown_circuit_is_not_found():
    r = client.post(f"{V1}/strategy/evaluate", json={"circuit_key": "monaco"})
    assert r.status_code == 404


# --- validation ------------------------------------------------------------

@pytest.mark.integration
def test_validation_all_has_aggregate():
    r = client.get(f"{V1}/validation")
    assert r.status_code == 200
    body = r.json()
    assert "races_validated" in body["aggregate"]
    assert "pit_lap_mae" in body["aggregate"]
    assert len(body["races"]) >= 4


@pytest.mark.integration
def test_validation_bahrain_matches_stage4():
    r = client.get(f"{V1}/validation/bahrain")
    assert r.status_code == 200
    body = r.json()
    assert body["circuit_key"] == "bahrain"
    assert body["actual"]["winner"] == "VER"
    assert body["metrics"]["first_stop_abs_error"] > 0


@pytest.mark.integration
def test_validation_unknown_circuit_is_not_found():
    r = client.get(f"{V1}/validation/monaco")
    assert r.status_code == 404


# --- report ----------------------------------------------------------------

@pytest.mark.integration
def test_report_generate_bahrain():
    r = client.post(f"{V1}/report/generate", json={"circuit_key": "bahrain", "n_sims": 300})
    assert r.status_code == 200
    body = r.json()
    assert body["circuit_key"] == "bahrain"
    assert body["recommendation"]["key"]
    assert body["validation"]["actual"]["winner"] == "VER"
    assert body["explanation"]
    assert "recommends" in body["executive_summary"]
    assert body["confidence_note"]


@pytest.mark.integration
def test_report_pdf_unknown_circuit_is_not_found():
    # 404/422 are raised in build_report, before any WeasyPrint call — no native stack needed.
    assert client.get(f"{V1}/report/pdf/monaco").status_code == 404


@pytest.mark.integration
def test_report_pdf_ungeneratable_is_unprocessable():
    assert client.get(f"{V1}/report/pdf/australian").status_code == 422


@pytest.mark.integration
def test_report_pdf_bahrain_when_weasyprint_available():
    pytest.importorskip("weasyprint")
    r = client.get(f"{V1}/report/pdf/bahrain?n_sims=300")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"


# --- insights (degradation) -----------------------------------------------

@pytest.mark.integration
def test_degradation_curves_monotonic_increasing():
    r = client.get(f"{V1}/degradation/bahrain")
    assert r.status_code == 200
    body = r.json()
    assert body["circuit_key"] == "bahrain"
    assert len(body["compounds"]) >= 2
    for comp in body["compounds"]:
        losses = [pt["loss_s"] for pt in comp["curve"]]
        assert losses == sorted(losses), f"{comp['compound']} loss should be non-decreasing"
        assert losses[-1] >= losses[0]


@pytest.mark.integration
def test_degradation_unknown_circuit_is_not_found():
    assert client.get(f"{V1}/degradation/monaco").status_code == 404
