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


# Ensure DB is created on import
init_db()
