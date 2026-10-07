"""Tests for Multimodal Feature Fusion (Gate 6)."""

import pytest
import numpy as np

from backend.data.lot_simulator import LotSimulator
from backend.fusion.feature_fusion import (
    MultimodalFusionEngine,
    RunMode,
    FUSED_FEATURE_SCHEMA
)


def test_three_run_modes_from_same_unit():
    """Verify electrical-only, acoustic-only, and fused modes producible on demand from the same unit."""
    sim = LotSimulator()
    lot = sim.create_same_source_lot(lot_id="LOT-TEST", size=5, seed=42)
    unit = lot.units[0]

    engine = MultimodalFusionEngine()

    # 1. Electrical-only
    res_elec = engine.fuse(unit, mode=RunMode.ELECTRICAL_ONLY)
    assert res_elec["mode"] == "electrical_only"
    assert res_elec["dimension"] == 6
    assert res_elec["vector"].shape == (6,)
    assert "ocv_v" in res_elec["features"]
    assert "tof_us" not in res_elec["features"]

    # 2. Acoustic-only
    res_acous = engine.fuse(unit, mode=RunMode.ACOUSTIC_ONLY, seed=123)
    assert res_acous["mode"] == "acoustic_only"
    assert res_acous["dimension"] == 7
    assert res_acous["vector"].shape == (7,)
    assert "tof_us" in res_acous["features"]
    assert "ocv_v" not in res_acous["features"]

    # 3. Fused
    res_fused = engine.fuse(unit, mode=RunMode.FUSED, seed=123)
    assert res_fused["mode"] == "fused"
    assert res_fused["dimension"] == 13
    assert res_fused["vector"].shape == (13,)
    assert "ocv_v" in res_fused["features"]
    assert "tof_us" in res_fused["features"]

    # Vector concatenation consistency
    np.testing.assert_array_equal(
        res_fused["vector"],
        np.concatenate([res_elec["vector"], res_acous["vector"]])
    )


def test_fused_feature_schema_documentation():
    """Verify fused feature schema is documented with field, modality, units, and description."""
    assert len(FUSED_FEATURE_SCHEMA) == 13
    elec_fields = [f for f in FUSED_FEATURE_SCHEMA if f["modality"] == "electrical"]
    acous_fields = [f for f in FUSED_FEATURE_SCHEMA if f["modality"] == "acoustic"]

    assert len(elec_fields) == 6
    assert len(acous_fields) == 7

    for entry in FUSED_FEATURE_SCHEMA:
        assert "field" in entry
        assert "modality" in entry
        assert "units" in entry
        assert "description" in entry
        assert len(entry["description"]) > 5


def test_twenty_unit_demonstration_from_lot_simulator():
    """Demonstrate fusion across 20 units drawn from Gate 1's lot simulator."""
    sim = LotSimulator()
    lot = sim.create_same_source_lot(lot_id="LOT-DEMO-20", size=20, seed=42)
    assert lot.size == 20

    engine = MultimodalFusionEngine()

    for idx, unit in enumerate(lot.units):
        fused = engine.fuse(unit, mode=RunMode.FUSED)
        assert fused["dimension"] == 13
        assert not np.any(np.isnan(fused["vector"]))
        # Verify physical sanity of fused values
        feats = fused["features"]
        assert 2.5 <= feats["ocv_v"] <= 4.4
        assert feats["dcir_mohm"] > 0
        assert 2.5 <= feats["tof_us"] <= 8.5
        assert feats["snr_db"] > 5.0
        assert 0.0 <= feats["repeatability"] <= 1.0
