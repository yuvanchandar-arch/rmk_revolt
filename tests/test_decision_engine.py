"""Tests for Sequential Decision Policy Engine & Certificate Generator (Gate 8)."""

import pytest
import numpy as np
import json

from backend.data.lot_simulator import LotSimulator
from backend.data.loaders import BatteryRecord
from backend.lotus.sampling import draw_reference_sample
from backend.lotus.ltt_calibration import LTTCalibrationEngine, CertifiedThresholdPolicy
from backend.lotus.decision_engine import (
    SequentialDecisionEngine,
    DecisionOutcome,
    MahalanobisOODDetector
)
from backend.lotus.certificate import LotCertificateGenerator, LotCertificate


@pytest.fixture
def calibrated_system():
    sim = LotSimulator()
    lot = sim.create_same_source_lot("LOT-NOMINAL-NMC-200", size=200, seed=42)
    ref_units, remaining = draw_reference_sample(lot.units, m=45, seed=42)

    calibrator = LTTCalibrationEngine()
    policies = {
        app_id: calibrator.calibrate_application(ref_units, app_id, epsilon=0.05, delta=0.10)
        for app_id in ["solar_backup", "low_power_lighting", "fast_charge_buffer"]
    }

    engine = SequentialDecisionEngine(policies=policies)
    engine.fit_calibration_population(ref_units)

    return {
        "engine": engine,
        "lot": lot,
        "ref_units": ref_units,
        "remaining_units": remaining,
        "policies": policies
    }


def test_four_decisions_demonstrated(calibrated_system):
    """Verify approve, reject, escalate (intermediate), and abstain decisions can all be produced,
    and verify Stage-2-resolved and Stage-3-fallback units are produced.
    """
    engine = calibrated_system["engine"]
    units = calibrated_system["remaining_units"]

    decisions_seen = set()
    stage2_resolved_count = 0
    stage3_fallback_count = 0

    for u in units:
        # Full resolution evaluation
        res_solar = engine.evaluate_unit(u, target_application="solar_backup")
        decisions_seen.add(res_solar.decision)
        if res_solar.resolution_stage == "stage2":
            stage2_resolved_count += 1
        elif res_solar.resolution_stage == "stage3":
            stage3_fallback_count += 1

        # Intermediate escalation without running Stage 3 fallback
        res_esc = engine.evaluate_unit(u, target_application="solar_backup", execute_stage3_fallback=False)
        decisions_seen.add(res_esc.decision)

    # Corrupted unit -> Abstain
    corrupt_unit = BatteryRecord(
        unit_id="UNIT-CORRUPT",
        dataset_source="Synthetic",
        chemistry="NMC",
        format="pouch",
        platform="Platform-NMC-Pouch",
        fleet_source="MetroEV-Delivery-FleetA",
        usage_history="delivery",
        nominal_capacity_ah=2.5,
        measured_capacity_ah=2.0,
        capacity_fade_pct=20.0,
        cycle_count=700,
        storage_condition_class="controlled_ambient",
        damage_category="none",
        time_series={},
        early_features={"ocv_v": 0.0, "dcir_mohm": -999.0, "sensor_quality_flag": 0}
    )
    res_corrupt = engine.evaluate_unit(corrupt_unit)
    decisions_seen.add(res_corrupt.decision)

    # Severely degraded unit with zero valid applications -> Reject
    severely_degraded_unit = BatteryRecord(
        unit_id="UNIT-SEVERE-REJECT",
        dataset_source="PulseBat",
        chemistry="NMC",
        format="pouch",
        platform="Platform-NMC-Pouch",
        fleet_source="MetroEV-Delivery-FleetA",
        usage_history="delivery",
        nominal_capacity_ah=2.5,
        measured_capacity_ah=1.2,
        capacity_fade_pct=52.0,
        cycle_count=2200,
        storage_condition_class="controlled_ambient",
        damage_category="none",
        time_series={},
        early_features={"ocv_v": 3.75, "dcir_mohm": 110.0, "sensor_quality_flag": 1}
    )
    res_reject = engine.evaluate_unit(severely_degraded_unit, target_application="solar_backup")
    decisions_seen.add(res_reject.decision)

    # All four outcomes represented
    assert DecisionOutcome.APPROVE in decisions_seen
    assert DecisionOutcome.ESCALATE in decisions_seen
    assert DecisionOutcome.REJECT in decisions_seen
    assert DecisionOutcome.ABSTAIN in decisions_seen
    # Verify real Stage 2 resolution or Stage 3 fallback occurred
    assert (stage2_resolved_count + stage3_fallback_count) > 0


def test_deliberate_ood_abstention(calibrated_system):
    """A unit with an out-of-distribution feature vector must trigger OOD abstention."""
    engine = calibrated_system["engine"]
    base_unit = calibrated_system["remaining_units"][0]

    # Create synthetic OOD unit with physically anomalous features (e.g. 5x DCIR and 4x ToF)
    ood_unit = BatteryRecord(
        unit_id="UNIT-OOD-OUTLIER-999",
        dataset_source="PulseBat",
        chemistry="NMC",
        format="pouch",
        platform="Platform-NMC-Pouch",
        fleet_source="MetroEV-Delivery-FleetA",
        usage_history="delivery",
        nominal_capacity_ah=base_unit.nominal_capacity_ah,
        measured_capacity_ah=base_unit.measured_capacity_ah,
        capacity_fade_pct=base_unit.capacity_fade_pct,
        cycle_count=base_unit.cycle_count,
        storage_condition_class=base_unit.storage_condition_class,
        damage_category=base_unit.damage_category,
        time_series=base_unit.time_series,
        early_features={
            **base_unit.early_features,
            "dcir_mohm": 180.0,
            "cell_imbalance_mv": 95.0
        }
    )

    res = engine.evaluate_unit(ood_unit)
    assert res.decision == DecisionOutcome.ABSTAIN
    assert res.is_ood is True
    assert res.mahalanobis_distance > engine.ood_detector.threshold_distance
    assert any("OOD Anomaly Detected" in step for step in res.decision_path)


def test_multi_application_approval_on_single_unit(calibrated_system):
    """Verify a single battery holds approvals for two distinct applications simultaneously."""
    engine = calibrated_system["engine"]
    units = calibrated_system["remaining_units"]

    multi_approved_unit = None
    for u in units:
        res = engine.evaluate_unit(u, target_application="solar_backup")
        app_ids = [a.application_id for a in res.approved_applications]
        if "solar_backup" in app_ids and "low_power_lighting" in app_ids:
            multi_approved_unit = res
            break

    assert multi_approved_unit is not None, "Failed to find unit holding multiple applications"
    app_ids = [a.application_id for a in multi_approved_unit.approved_applications]
    assert "solar_backup" in app_ids
    assert "low_power_lighting" in app_ids

    # Each approval holds its own certified risk bound
    for app in multi_approved_unit.approved_applications:
        assert app.certified_risk_bound <= 0.05
        assert app.label_certified == "CERTIFIED"
        assert "ESTIMATE" in app.label_estimate


def test_certificate_fields_and_dual_risk_contract(calibrated_system):
    """Verify certificate contains every Section 5.8 field and distinctly separates CERTIFIED vs ESTIMATE."""
    engine = calibrated_system["engine"]
    lot = calibrated_system["lot"]
    ref_units = calibrated_system["ref_units"]
    remaining = calibrated_system["remaining_units"]
    policies = calibrated_system["policies"]

    decisions = [engine.evaluate_unit(u, target_application="solar_backup") for u in remaining]

    cert_gen = LotCertificateGenerator()
    cert = cert_gen.generate_certificate(
        lot_id=lot.lot_id,
        provenance=lot.provenance,
        lot_size=lot.size,
        ref_sample_size=len(ref_units),
        policies=policies,
        decisions=decisions
    )

    cert_dict = cert.to_dict()

    # Exact field checklist from Section 5.8
    required_fields = [
        "lot_id", "lot_definition_provenance", "lot_size_N", "reference_sample_size_m",
        "confidence_one_minus_delta", "risk_target_epsilon_per_application",
        "stage1_approval_count", "stage2_escalation_count", "stage3_full_test_count",
        "reject_quarantine_count", "mean_test_time_per_unit_s", "time_saved_vs_full_testing_pct",
        "dual_risk_metrics", "data_quality_score", "out_of_distribution_flags_count",
        "application_recommendations_and_limits", "per_unit_evidence_records"
    ]
    for rf in required_fields:
        assert rf in cert_dict, f"Missing required Section 5.8 field: {rf}"

    # Verify Dual-Risk records: CERTIFIED vs ESTIMATE distinction
    for dr in cert.dual_risk_metrics:
        assert dr.label_certified == "CERTIFIED"
        assert "ESTIMATE" in dr.label_estimate
        assert "NOT CONTROLLED" in dr.label_estimate
        assert dr.certified_early_approval_disagreement_bound <= 0.05
        assert isinstance(dr.estimated_conditional_fail_rate_among_approved, float)

    # Verify JSON export
    cert_json = cert.to_json()
    loaded = json.loads(cert_json)
    assert loaded["lot_id"] == lot.lot_id
    assert "CERTIFIED" in cert_json
    assert "ESTIMATE" in cert_json


def test_no_unit_terminates_at_escalate_in_certificate(calibrated_system):
    """Assert that no unit in a completed lot certificate has ESCALATE as its final recorded state."""
    engine = calibrated_system["engine"]
    lot = calibrated_system["lot"]
    ref_units = calibrated_system["ref_units"]
    remaining = calibrated_system["remaining_units"]
    policies = calibrated_system["policies"]

    # Fully evaluate remaining units
    decisions = [engine.evaluate_unit(u, target_application="solar_backup") for u in remaining]

    # Verify no unit terminates at ESCALATE in decisions
    for d in decisions:
        assert d.decision != DecisionOutcome.ESCALATE, f"Unit {d.unit_id} terminated at ESCALATE!"
        assert d.decision in [DecisionOutcome.APPROVE, DecisionOutcome.REJECT, DecisionOutcome.ABSTAIN]

    cert_gen = LotCertificateGenerator()
    cert = cert_gen.generate_certificate(
        lot_id=lot.lot_id,
        provenance=lot.provenance,
        lot_size=lot.size,
        ref_sample_size=len(ref_units),
        policies=policies,
        decisions=decisions
    )

    # Verify no unit in certificate per-unit evidence records has 'escalate'
    for rec in cert.per_unit_evidence_records:
        assert rec["primary_decision"] != "escalate", f"Unit {rec['unit_id']} recorded as escalate in certificate!"
        assert rec["primary_decision"] in ["approve", "reject", "abstain"]

    # Verify real Stage 3 count: reference sample m + realized Stage 3 fallback units
    n_fallback = sum(1 for d in decisions if getattr(d, "resolution_stage", "") == "stage3" or getattr(d, "stage3_tested", False))
    assert cert.stage3_full_test_count == len(ref_units) + n_fallback
