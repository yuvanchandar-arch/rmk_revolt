"""Tests for FastAPI backend routes and persistence layer (Gate 9)."""

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_create_and_list_lots():
    # 1. Create a nominal lot
    payload = {
        "lot_id": "LOT-API-TEST-200",
        "lot_type": "same_source",
        "size": 50,
        "seed": 42
    }
    create_res = client.post("/api/lots", json=payload)
    assert create_res.status_code == 200
    create_data = create_res.json()
    assert create_data["lot_id"] == "LOT-API-TEST-200"
    assert create_data["size"] == 50

    # 2. List lots
    list_res = client.get("/api/lots")
    assert list_res.status_code == 200
    lots = list_res.json()["lots"]
    assert any(l["lot_id"] == "LOT-API-TEST-200" for l in lots)

    # 3. Get single lot details
    detail_res = client.get("/api/lots/LOT-API-TEST-200")
    assert detail_res.status_code == 200
    assert detail_res.json()["lot_id"] == "LOT-API-TEST-200"


def test_run_lot_pipeline_and_get_certificate():
    # Run the pipeline for the lot
    run_payload = {
        "epsilon": 0.05,
        "delta": 0.10,
        "target_application": "solar_backup",
        "allow_secondary_downgrade": True
    }
    run_res = client.post("/api/lots/LOT-API-TEST-200/run", json=run_payload)
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert run_data["lot_id"] == "LOT-API-TEST-200"
    assert run_data["reference_sample_size_m"] == 45
    assert "dual_risk_metrics" in run_data

    # Fetch certificate
    cert_res = client.get("/api/lots/LOT-API-TEST-200/certificate")
    assert cert_res.status_code == 200
    cert = cert_res.json()
    assert cert["lot_id"] == "LOT-API-TEST-200"
    assert cert["reference_sample_size_m"] == 45
    assert len(cert["dual_risk_metrics"]) == 3

    # Verify dual-risk labels
    for dr in cert["dual_risk_metrics"]:
        assert dr["label_certified"] == "CERTIFIED"
        assert "ESTIMATE" in dr["label_estimate"]


def test_list_units_with_filters_and_get_evidence():
    # List units
    units_res = client.get("/api/lots/LOT-API-TEST-200/units?limit=10")
    assert units_res.status_code == 200
    units_data = units_res.json()
    assert len(units_data["units"]) > 0

    first_unit_id = units_data["units"][0]["unit_id"]

    # Filter by chemistry
    chem_res = client.get("/api/lots/LOT-API-TEST-200/units?chemistry=NMC")
    assert chem_res.status_code == 200
    assert all(u["chemistry"] == "NMC" for u in chem_res.json()["units"])

    # Get single unit evidence
    # Look for a screened unit that has evidence
    for u in units_data["units"]:
        if u["decision"] != "reference_full_tested":
            ev_res = client.get(f"/api/units/{u['unit_id']}/evidence")
            assert ev_res.status_code == 200
            ev_data = ev_res.json()
            assert ev_data["unit_id"] == u["unit_id"]
            assert "decision_path" in ev_data
            break


def test_hardware_sensor_reading_ingestion_endpoint():
    """Verify hardware bridge endpoint accepts valid telemetry without modifying statistical engine."""
    sensor_payload = {
        "reading_id": "HW-SENS-READING-9001",
        "device_id": "ESP32-EMAT-RIG-ALPHA",
        "sensor_type": "voltage_current_pulse",
        "timestamp": "2026-10-06T18:15:00Z",
        "payload": {
            "v_pre_pulse": 3.962,
            "v_pulse": 3.891,
            "i_pulse": 5.02,
            "calculated_dcir_mohm": 14.14,
            "temp_c": 24.8,
            "emat_tof_us": 3.52,
            "emat_snr_db": 18.5
        }
    }

    ingest_res = client.post("/api/ingest/sensor-reading", json=sensor_payload)
    assert ingest_res.status_code == 200
    ingest_data = ingest_res.json()
    assert ingest_data["status"] == "success"
    assert ingest_data["reading_id"] == "HW-SENS-READING-9001"
    assert "hardware telemetry successfully ingested" in ingest_data["message"].lower()


def test_experiments_and_multiphysics_endpoints():
    # Experiments endpoint
    exp_res = client.get("/api/experiments/results")
    assert exp_res.status_code == 200
    assert len(exp_res.json()["experiments"]) == 6

    # EMAT multiphysics endpoint
    multi_res = client.get("/api/emat/multiphysics/Healthy")
    assert multi_res.status_code == 200
    m_data = multi_res.json()
    assert m_data["state"] == "Healthy"
    assert "layers" in m_data
    assert "tx_signal" in m_data
    assert "raw_noisy_signal" in m_data
    assert "recovered_envelope" in m_data
    assert "extracted_features" in m_data
