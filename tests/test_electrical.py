"""Tests for Electrical Stage 0 veto, Stage 1 features, and Stage 2 screening (Gate 2)."""

import pytest
import numpy as np

from backend.data.loaders import (
    load_nasa_pcoe,
    load_calce,
    load_oxford,
    load_pulsebat,
    BatteryRecord
)
from backend.electrical.features import ElectricalFeatureExtractor
from backend.electrical.stage0_veto import Stage0VetoEngine
from backend.electrical.stage2_screening import Stage2ScreeningPipeline


def test_stage1_six_features_across_all_datasets():
    """Verify all six Stage-1 features are computed with real numeric values across all datasets."""
    extractor = ElectricalFeatureExtractor()
    datasets = {
        "NASA": load_nasa_pcoe()[0],
        "CALCE": load_calce()[0],
        "Oxford": load_oxford()[0],
        "PulseBat": load_pulsebat()[0],
    }

    required_keys = [
        "ocv_v", "dcir_mohm", "relaxation_slope",
        "relaxation_curvature", "temperature_response_c", "cell_imbalance_mv"
    ]

    for name, unit in datasets.items():
        res = extractor.extract_features(unit)
        feats = res["features"]
        vec = res["vector"]

        assert vec.shape == (6,), f"Feature vector for {name} must have shape (6,), got {vec.shape}"
        assert not np.any(np.isnan(vec)), f"NaN in feature vector for {name}"

        for key in required_keys:
            val = feats[key]
            assert isinstance(val, (int, float)), f"{key} in {name} is not numeric: {type(val)}"
            # Plausibility checks on real numbers
            if key == "ocv_v":
                assert 2.5 <= val <= 4.4, f"OCV out of bounds in {name}: {val}"
            elif key == "dcir_mohm":
                assert val > 0, f"DCIR must be positive in {name}: {val}"
            elif key == "cell_imbalance_mv":
                assert val >= 0, f"Imbalance must be non-negative in {name}: {val}"


def test_stage0_veto_quarantines_corrupted_records():
    """Stage 0 veto must quarantine corrupted records with explicit reasons."""
    veto_engine = Stage0VetoEngine()

    # 1. Valid nominal record should pass Stage 0
    valid_unit = load_pulsebat()[0]
    res_valid = veto_engine.evaluate(valid_unit)
    assert res_valid.passed is True
    assert res_valid.veto_triggered is False
    assert res_valid.disposition == "proceed_to_stage1"
    assert len(res_valid.reasons) == 0

    # 2. Corrupted sensor record
    corrupt_sensor_record = BatteryRecord(
        unit_id="CORRUPT-SENSOR-001",
        dataset_source="Synthetic",
        chemistry="NMC",
        format="pouch",
        platform="Platform-Test",
        fleet_source="Fleet-Test",
        usage_history="commuter",
        nominal_capacity_ah=2.5,
        measured_capacity_ah=2.0,
        capacity_fade_pct=20.0,
        cycle_count=500,
        storage_condition_class="controlled_ambient",
        damage_category="none",
        time_series={"time_s": [0, 1], "voltage_v": [0, 0], "current_a": [0, 0], "temperature_c": [25, 25]},
        early_features={
            "ocv_v": 0.0,
            "dcir_mohm": -999.0,
            "relaxation_slope": 0.0,
            "relaxation_curvature": 0.0,
            "temp_rise_c": 0.0,
            "cell_imbalance_mv": 0.0,
            "sensor_quality_flag": 0
        }
    )
    res_sensor = veto_engine.evaluate(corrupt_sensor_record)
    assert res_sensor.passed is False
    assert res_sensor.veto_triggered is True
    assert res_sensor.disposition == "quarantine"
    assert any("Sensor quality check failed" in r for r in res_sensor.reasons)

    # 3. Severe under-voltage record
    undervoltage_record = BatteryRecord(
        unit_id="UNDERVOLT-001",
        dataset_source="Synthetic",
        chemistry="NMC",
        format="pouch",
        platform="Platform-Test",
        fleet_source="Fleet-Test",
        usage_history="commuter",
        nominal_capacity_ah=2.5,
        measured_capacity_ah=1.0,
        capacity_fade_pct=60.0,
        cycle_count=1800,
        storage_condition_class="controlled_ambient",
        damage_category="none",
        time_series={"time_s": [0, 1], "voltage_v": [1.4, 1.4], "current_a": [0, 0], "temperature_c": [25, 25]},
        early_features={
            "ocv_v": 1.40,
            "dcir_mohm": 85.0,
            "relaxation_slope": 0.01,
            "relaxation_curvature": 0.001,
            "temp_rise_c": 1.2,
            "cell_imbalance_mv": 12.0,
            "sensor_quality_flag": 1
        }
    )
    res_undervolt = veto_engine.evaluate(undervoltage_record)
    assert res_undervolt.passed is False
    assert res_undervolt.disposition == "quarantine"
    assert any("under-voltage" in r.lower() for r in res_undervolt.reasons)


def test_stage2_extended_features_richer_than_stage1():
    """Stage 2 must produce a distinct, richer set of features than Stage 1."""
    extractor_s1 = ElectricalFeatureExtractor()
    pipeline_s2 = Stage2ScreeningPipeline()

    unit = load_pulsebat()[0]
    s1_res = extractor_s1.extract_features(unit)
    s2_res = pipeline_s2.extract_extended_features(unit)

    s1_feats = set(s1_res["features"].keys()) - {"unit_id", "sensor_quality_flag"}
    s2_feats = set(s2_res["extended_features"].keys()) - {"unit_id"}

    # Distinct feature sets
    assert len(s1_feats.intersection(s2_feats)) == 0, "Stage 1 and Stage 2 must have distinct feature sets"
    # Stage 2 is richer (8 features vs 6)
    assert len(s2_feats) > len(s1_feats)
    assert s2_res["vector"].shape == (8,)
    assert not np.any(np.isnan(s2_res["vector"]))
    assert s2_res["extended_features"]["tau_fast_s"] > 0
    assert s2_res["extended_features"]["tau_slow_s"] > s2_res["extended_features"]["tau_fast_s"]
    assert s2_res["extended_features"]["polarization_index"] > 0
