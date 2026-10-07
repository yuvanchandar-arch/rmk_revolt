from fastapi.testclient import TestClient
from backend.api.main import app
import json

client = TestClient(app)

def record_responses():
    print("=== ENDPOINT SAMPLES ===")

    # 1. GET /api/health
    r1 = client.get("/api/health")
    print(f"1. GET /api/health -> HTTP {r1.status_code}")
    print(json.dumps(r1.json(), indent=2))

    # 2. POST /api/lots
    r2 = client.post("/api/lots", json={"lot_id": "LOT-DEMO-NMC-200", "lot_type": "same_source", "size": 200, "seed": 42})
    print(f"\n2. POST /api/lots -> HTTP {r2.status_code}")
    print(json.dumps(r2.json(), indent=2))

    # 3. GET /api/lots
    r3 = client.get("/api/lots")
    print(f"\n3. GET /api/lots -> HTTP {r3.status_code} (count: {len(r3.json()['lots'])})")

    # 4. POST /api/lots/{lot_id}/run
    r4 = client.post("/api/lots/LOT-DEMO-NMC-200/run", json={"epsilon": 0.05, "delta": 0.10, "target_application": "solar_backup"})
    print(f"\n4. POST /api/lots/LOT-DEMO-NMC-200/run -> HTTP {r4.status_code}")
    print(json.dumps(r4.json(), indent=2))

    # 5. GET /api/lots/{lot_id}/certificate
    r5 = client.get("/api/lots/LOT-DEMO-NMC-200/certificate")
    print(f"\n5. GET /api/lots/LOT-DEMO-NMC-200/certificate -> HTTP {r5.status_code}")
    cert_summary = {k: r5.json()[k] for k in ["lot_id", "lot_size_N", "reference_sample_size_m", "time_saved_vs_full_testing_pct", "dual_risk_metrics"]}
    print(json.dumps(cert_summary, indent=2))

    # 6. GET /api/lots/{lot_id}/units
    r6 = client.get("/api/lots/LOT-DEMO-NMC-200/units?limit=2")
    print(f"\n6. GET /api/lots/LOT-DEMO-NMC-200/units?limit=2 -> HTTP {r6.status_code}")
    print(json.dumps(r6.json(), indent=2))

    # 7. GET /api/units/{unit_id}/evidence
    u_id = r6.json()["units"][0]["unit_id"]
    r7 = client.get(f"/api/units/{u_id}/evidence")
    print(f"\n7. GET /api/units/{u_id}/evidence -> HTTP {r7.status_code}")
    print(json.dumps({k: r7.json()[k] for k in ["unit_id", "decision", "decision_path", "mean_test_time_s"]}, indent=2))

    # 8. POST /api/ingest/sensor-reading (Hardware Bridge)
    hw_payload = {
        "reading_id": "HW-TEST-RIG-001",
        "device_id": "ESP32-EMAT-STATION-1",
        "sensor_type": "voltage_current_pulse",
        "timestamp": "2026-10-06T18:25:00Z",
        "payload": {
            "v_ocv": 3.965,
            "v_pulse_peak": 3.895,
            "i_pulse_peak": 5.0,
            "dcir_mohm": 14.0,
            "surface_temp_c": 25.1,
            "emat_burst_rx_mv": 12.4
        }
    }
    r8 = client.post("/api/ingest/sensor-reading", json=hw_payload)
    print(f"\n8. POST /api/ingest/sensor-reading -> HTTP {r8.status_code}")
    print(json.dumps(r8.json(), indent=2))

    # 9. GET /api/emat/multiphysics/Healthy
    r9 = client.get("/api/emat/multiphysics/Healthy")
    print(f"\n9. GET /api/emat/multiphysics/Healthy -> HTTP {r9.status_code}")
    m_summary = {k: r9.json()[k] for k in ["state", "true_tof_us", "plating_thickness_um", "extracted_features"]}
    print(json.dumps(m_summary, indent=2))

if __name__ == '__main__':
    record_responses()
