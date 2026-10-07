"""SQLite Persistence Layer for LOTUS-EMAT (Portable to PostgreSQL)."""

import sqlite3
import json
import os
from typing import Dict, Any, List, Optional

DB_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "lotus_database.db")


def get_db_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes SQLite database schema."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS lots (
        lot_id TEXT PRIMARY KEY,
        lot_type TEXT NOT NULL,
        provenance_json TEXT NOT NULL,
        size INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS units (
        unit_id TEXT PRIMARY KEY,
        lot_id TEXT NOT NULL,
        dataset_source TEXT NOT NULL,
        chemistry TEXT NOT NULL,
        format TEXT NOT NULL,
        platform TEXT NOT NULL,
        fleet_source TEXT NOT NULL,
        usage_history TEXT NOT NULL,
        nominal_capacity_ah REAL NOT NULL,
        measured_capacity_ah REAL NOT NULL,
        capacity_fade_pct REAL NOT NULL,
        cycle_count INTEGER NOT NULL,
        early_features_json TEXT NOT NULL,
        FOREIGN KEY (lot_id) REFERENCES lots(lot_id)
    );

    CREATE TABLE IF NOT EXISTS decisions (
        unit_id TEXT PRIMARY KEY,
        lot_id TEXT NOT NULL,
        primary_decision TEXT NOT NULL,
        approved_apps_json TEXT NOT NULL,
        is_ood INTEGER NOT NULL,
        mahalanobis_distance REAL NOT NULL,
        test_time_s REAL NOT NULL,
        decision_record_json TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (unit_id) REFERENCES units(unit_id),
        FOREIGN KEY (lot_id) REFERENCES lots(lot_id)
    );

    CREATE TABLE IF NOT EXISTS certificates (
        lot_id TEXT PRIMARY KEY,
        certificate_id TEXT NOT NULL,
        certificate_json TEXT NOT NULL,
        issued_timestamp TEXT NOT NULL,
        FOREIGN KEY (lot_id) REFERENCES lots(lot_id)
    );

    CREATE TABLE IF NOT EXISTS hardware_readings (
        reading_id TEXT PRIMARY KEY,
        device_id TEXT NOT NULL,
        sensor_type TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        status TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()


def seed_demonstration_data():
    """Seeds standard demonstration lots and certificates if not already populated."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    import time
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    demo_lots = [
        ("LOT-NOMINAL-NMC-200", "same_source", json.dumps({"chemistry": "NMC", "format": "pouch", "size": 200}), 200, now, "qualified"),
        ("LOT-MIXEDAGE-200", "mixed_age", json.dumps({"chemistry": "NMC", "format": "cylindrical", "size": 200}), 200, now, "qualified"),
        ("LOT-CROSSDATASET-200", "cross_dataset", json.dumps({"chemistry": "Mixed", "format": "mixed", "size": 200}), 200, now, "split_required"),
        ("BATCH-MIXED-200", "mixed_chemistry_anomalous", json.dumps({"chemistry": "NMC+LFP", "format": "mixed", "size": 200}), 200, now, "provenance_alert")
    ]
    for l in demo_lots:
        cur.execute("SELECT COUNT(*) as c FROM lots WHERE lot_id = ?", (l[0],))
        if cur.fetchone()["c"] == 0:
            cur.execute("INSERT OR REPLACE INTO lots (lot_id, lot_type, provenance_json, size, created_at, status) VALUES (?, ?, ?, ?, ?, ?)", l)

        # Seed sample certificate if available
        sample_cert_path = os.path.join(os.path.dirname(__file__), "..", "..", "reports", "sample_lot_certificate.json")
        if os.path.exists(sample_cert_path):
            with open(sample_cert_path, "r") as f:
                cert_json = f.read()
            cert_obj = json.loads(cert_json)
            cur.execute(
                "INSERT OR REPLACE INTO certificates (lot_id, certificate_id, certificate_json, issued_timestamp) VALUES (?, ?, ?, ?)",
                ("LOT-NOMINAL-NMC-200", cert_obj.get("certificate_id", "CERT-LOT-NOMINAL-NMC-200-REALIZED"), cert_json, now)
            )

        # Seed 200 units for LOT-NOMINAL-NMC-200
        for i in range(1, 201):
            uid = f"U{i:03d}"
            is_ref = i <= 45
            decision = "approve"
            stage = "Stage 1 Fast Pass"
            time_s = 30.0
            fade = 8.2 + (i * 0.05)
            dcir = 18.5 + (i * 0.06)
            tof = 4.85 + (i * 0.002)

            if is_ref:
                stage = "Stage 3 Reference Sample"
                decision = "approve"
                time_s = 14400.0
            elif i > 122:
                stage = "Stage 2 Kinetic Rejected"
                decision = "reject"
                time_s = 630.0
                fade = 24.0 + (i * 0.04)
                dcir = 34.0 + (i * 0.08)
            elif i > 91:
                stage = "Stage 2 Kinetic Pass"
                decision = "approve"
                time_s = 630.0
                fade = 12.0 + (i * 0.04)
                dcir = 22.0 + (i * 0.05)
            elif i > 86:
                stage = "Stage 1 Screened Out"
                decision = "reject"
                time_s = 30.0
                fade = 28.0 + (i * 0.06)
                dcir = 42.0 + (i * 0.1)

            early_feats = {
                "ocv_v": 3.95,
                "dcir_mohm": round(dcir, 1),
                "tof_us": round(tof, 3),
                "capacity_fade_pct": round(fade, 1),
                "peak_amplitude": 0.582,
                "snr_db": 22.4,
                "mahalanobis_distance": round(1.2 + (i * 0.005), 2)
            }
            cur.execute("""
            INSERT OR REPLACE INTO units 
            (unit_id, lot_id, dataset_source, chemistry, format, platform, fleet_source, usage_history, nominal_capacity_ah, measured_capacity_ah, capacity_fade_pct, cycle_count, early_features_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, "LOT-NOMINAL-NMC-200", "MetroEV-Delivery-FleetA", "NMC", "pouch", "Pouch-Gen2", "FleetA", "commuter", 2.5, round(2.5 * (1 - fade/100), 2), round(fade, 1), 200 + i * 5, json.dumps(early_feats)))

            dec_record = {
                "unit_id": uid,
                "decision": decision,
                "stage": stage,
                "resolution_stage": stage,
                "mean_test_time_s": time_s,
                "fused_features": early_feats,
                "mahalanobis_distance": early_feats["mahalanobis_distance"],
                "is_ood": False,
                "stage0_passed": True
            }
            cur.execute("""
            INSERT OR REPLACE INTO decisions
            (unit_id, lot_id, primary_decision, approved_apps_json, is_ood, mahalanobis_distance, test_time_s, decision_record_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, "LOT-NOMINAL-NMC-200", decision, json.dumps(["solar_backup"] if decision == "approve" else []), 0, early_feats["mahalanobis_distance"], time_s, json.dumps(dec_record), now))

        conn.commit()

    conn.close()


# Ensure DB is created and seeded on import
init_db()
seed_demonstration_data()

