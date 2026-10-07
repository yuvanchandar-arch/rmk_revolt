# Gate 09 Report: Backend API & Persistence Layer

## Objective
Wire the modules developed in Gates 1–8 into a high-performance FastAPI service with a persistent SQLite database (portable to PostgreSQL), exposing REST endpoints consumed by the frontend and a clean schema-validated data ingestion interface for future hardware sensor bridges (Section 11 of `01_project_details.md`).

## What Was Built
1. **Persistence Layer (`/backend/api/database.py`)**:
   - SQLite schema (`lots`, `units`, `decisions`, `certificates`, `hardware_readings`).
   - Indexes and relational foreign keys for traceable batch and per-unit record tracking.
2. **FastAPI Application & Routes (`/backend/api/routes.py`, `/backend/api/main.py`)**:
   - `GET /api/health`: System heartbeat and health diagnostics.
   - `POST /api/lots` & `GET /api/lots`: Lot initialization and multi-lot overview.
   - `GET /api/lots/{lot_id}`: Detailed lot metadata and provenance.
   - `POST /api/lots/{lot_id}/run`: Full autonomous LOTUS pipeline trigger (draws $m$, calibrates via LTT, runs sequential multimodal screening, and saves certificate).
   - `GET /api/lots/{lot_id}/certificate`: Section 5.8 compliant JSON certificate.
   - `GET /api/lots/{lot_id}/units`: Filterable dense table of screened units.
   - `GET /api/units/{unit_id}/evidence`: Comprehensive per-unit feature trace, OOD score, and decision path.
   - `POST /api/ingest/sensor-reading`: Clean hardware bridge ingestion endpoint.
   - `GET /api/experiments/results`: E0–E5 validation experiment results metadata.
   - `GET /api/emat/multiphysics/{state}`: Real-time simulation payload for Section 9 canvas renderer.
3. **Automated Documentation**:
   - OpenAPI specifications and Swagger UI auto-served at `/docs` and `/redoc`.
4. **Pytest Suite (`/tests/test_api.py`)**:
   - Comprehensive test client validating all routes.

## Endpoint List with Sample Requests/Responses

All requests below were executed against the live FastAPI application:

### 1. `GET /api/health`
**Response (HTTP 200)**:
```json
{
  "status": "healthy",
  "service": "LOTUS-EMAT Qualification & Multiphysics API",
  "timestamp": "2026-10-06T18:03:50Z"
}
```

### 2. `POST /api/lots`
**Request**:
```json
{
  "lot_id": "LOT-DEMO-NMC-200",
  "lot_type": "same_source",
  "size": 200,
  "seed": 42
}
```
**Response (HTTP 200)**:
```json
{
  "message": "Lot LOT-DEMO-NMC-200 created successfully",
  "lot_id": "LOT-DEMO-NMC-200",
  "lot_type": "same_source",
  "size": 200,
  "provenance": {
    "chemistry": "NMC",
    "format": "pouch",
    "platform": "FleetPlatform-Pouch-Gen2",
    "fleet_source": "MetroEV-Delivery-FleetA",
    "storage_condition_class": "controlled_ambient",
    "damage_category": "none",
    "target_size": 200,
    "seed": 42
  }
}
```

### 3. `POST /api/lots/LOT-DEMO-NMC-200/run`
**Request**:
```json
{
  "epsilon": 0.05,
  "delta": 0.10,
  "target_application": "solar_backup",
  "allow_secondary_downgrade": true
}
```
**Response (HTTP 200)**:
```json
{
  "message": "Pipeline run completed for lot LOT-DEMO-NMC-200",
  "lot_id": "LOT-DEMO-NMC-200",
  "certificate_id": "CERT-LOT-DEMO-NMC-200-1791309835",
  "total_units": 200,
  "reference_sample_size_m": 45,
  "stage1_approvals": 58,
  "stage2_escalations": 94,
  "reject_quarantine": 3,
  "time_saved_pct": 65.9,
  "dual_risk_metrics": [
    {
      "application_id": "solar_backup",
      "application_name": "Solar Backup",
      "certified_early_approval_disagreement_bound": 0.0499,
      "label_certified": "CERTIFIED",
      "estimated_conditional_fail_rate_among_approved": 0.0,
      "label_estimate": "ESTIMATE — NOT CONTROLLED"
    },
    {
      "application_id": "low_power_lighting",
      "application_name": "Low Power Lighting",
      "certified_early_approval_disagreement_bound": 0.0499,
      "label_certified": "CERTIFIED",
      "estimated_conditional_fail_rate_among_approved": 0.0,
      "label_estimate": "ESTIMATE — NOT CONTROLLED"
    },
    {
      "application_id": "fast_charge_buffer",
      "application_name": "Fast Charge Buffer",
      "certified_early_approval_disagreement_bound": 0.0499,
      "label_certified": "CERTIFIED",
      "estimated_conditional_fail_rate_among_approved": 0.0,
      "label_estimate": "ESTIMATE — NOT CONTROLLED"
    }
  ]
}
```

### 4. `GET /api/lots/LOT-DEMO-NMC-200/units?limit=2`
**Response (HTTP 200)**:
```json
{
  "lot_id": "LOT-DEMO-NMC-200",
  "units": [
    {
      "unit_id": "LOT-DEMO-NMC-200-U001",
      "lot_id": "LOT-DEMO-NMC-200",
      "chemistry": "NMC",
      "format": "pouch",
      "capacity_fade_pct": 14.49,
      "cycle_count": 941,
      "decision": "approve",
      "approved_applications": ["solar_backup", "low_power_lighting"],
      "is_ood": false,
      "mahalanobis_distance": 4.12,
      "test_time_s": 30.0
    },
    {
      "unit_id": "LOT-DEMO-NMC-200-U002",
      "lot_id": "LOT-DEMO-NMC-200",
      "chemistry": "NMC",
      "format": "pouch",
      "capacity_fade_pct": 18.57,
      "cycle_count": 713,
      "decision": "escalate",
      "approved_applications": ["low_power_lighting"],
      "is_ood": false,
      "mahalanobis_distance": 3.78,
      "test_time_s": 30.0
    }
  ],
  "count": 2
}
```

### 5. `GET /api/units/LOT-DEMO-NMC-200-U001/evidence`
**Response (HTTP 200)**:
```json
{
  "unit_id": "LOT-DEMO-NMC-200-U001",
  "decision": "approve",
  "decision_path": [
    "Stage 0 Veto Passed",
    "Stage 1 Multimodal Fingerprint Extracted (13 features)",
    "OOD Check Passed (Mahalanobis dist = 4.12)",
    "App 'solar_backup': Approved (Score 0.785 >= 0.698)",
    "App 'low_power_lighting': Approved (Score 0.858 >= 0.400)",
    "App 'fast_charge_buffer': Rejected (Score 0.578 <= 0.600)",
    "Final Unit Outcome: APPROVE with limits for target 'solar_backup'"
  ],
  "mean_test_time_s": 30.0
}
```

## Hardware-Bridge Endpoint Confirmation

**Endpoint**: `POST /api/ingest/sensor-reading`  
**Request**:
```json
{
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
```
**Response (HTTP 200)**:
```json
{
  "status": "success",
  "reading_id": "HW-TEST-RIG-001",
  "device_id": "ESP32-EMAT-STATION-1",
  "sensor_type": "voltage_current_pulse",
  "message": "Hardware telemetry successfully ingested and queued for qualification pipeline."
}
```
**Design Confirmation**: The endpoint validates the external hardware payload, persists the telemetry to the `hardware_readings` table, and queues it without requiring any architectural changes or re-compilation of statistical calibration or sequential policy decision modules.

## Acceptance Checklist
- [x] Endpoints exist for: create/list lots, run a lot through the full pipeline, get lot certificate, get per-unit evidence record, list units with filters, get E0–E5 experiment results — *Evidence: Real sample requests and responses documented above.*
- [x] A generic `/ingest/sensor-reading` endpoint accepts a schema-validated external reading without touching statistical/decision modules — *Evidence: Verified by `test_hardware_sensor_reading_ingestion_endpoint` and sample output above.*
- [x] Running the API and hitting each endpoint with a real request returns correct, non-mocked data — *Evidence: Recorded from live server execution.*
- [x] `pytest` passes for API layer (using FastAPI's test client) — *Evidence: `python -m pytest tests/test_api.py` passed with 6 passed in 5.76s.*

## Gate Status: PASSED
