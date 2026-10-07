"""Tests for LOTUS Statistical Calibration Engine (Gate 7)."""

import pytest
import math
import numpy as np

from backend.data.lot_simulator import LotSimulator
from backend.lotus.lot_definition import LotIntegrityEnforcer
from backend.lotus.sampling import (
    compute_reference_sample_size,
    REFERENCE_SAMPLE_SIZE_TABLE,
    draw_reference_sample
)
from backend.lotus.ltt_calibration import (
    LTTCalibrationEngine,
    compute_unconditional_joint_risk,
    APPLICATIONS
)


def test_sublot_splitting_on_mixed_batch():
    """Verify that a deliberately mixed batch (NMC + LFP) is automatically split into sub-lots."""
    sim = LotSimulator()
    mixed_lot = sim.create_mixed_chemistry_anomalous_lot(lot_id="BATCH-MIXED-200", size=200, seed=42)

    enforcer = LotIntegrityEnforcer()
    is_homo, sub_lots, audit = enforcer.audit_and_split(mixed_lot.lot_id, mixed_lot.units)

    # Must refuse single lot calibration and split
    assert is_homo is False
    assert len(sub_lots) > 1
    assert audit["action_taken"] == "refused_single_lot_split_into_sublots"
    assert sum(s.size for s in sub_lots) == 200

    # Ensure chemistries are segregated
    sublot_chems = [s.provenance["chemistry"] for s in sub_lots]
    assert "NMC" in sublot_chems
    assert "LFP" in sublot_chems


def test_sample_size_table_exact_verification():
    """Verify exact formula m = ceil( ln(delta) / ln(1 - epsilon) ) reproduces Section 5.6 table at 90% confidence."""
    delta = 0.10  # 90% confidence
    test_cases = [
        (0.10, 22),
        (0.05, 45),
        (0.02, 114),
        (0.01, 230)
    ]
    for eps, expected_m in test_cases:
        calculated_m = compute_reference_sample_size(epsilon=eps, delta=delta)
        assert calculated_m == expected_m, f"Sample size mismatch for eps={eps}: expected {expected_m}, got {calculated_m}"
        # Direct math check
        raw_val = math.log(delta) / math.log(1.0 - eps)
        assert math.ceil(raw_val) == expected_m


def test_risk_definition_unconditional_vs_conditional_divergence():
    """Prove that R(lambda, a) is an UNCONDITIONAL JOINT PROBABILITY and NOT P(fail | approve).
    
    Construct a synthetic low-approval-rate scenario:
    Total units = 100
    Approved = 10 units (out of which 2 would fail Stage 3)
    Escalated/Rejected = 90 units
    
    Unconditional joint risk R(lambda, a) = 2 / 100 = 0.02 (2%)
    Conditional fail rate P(fail | approve) = 2 / 10 = 0.20 (20%)
    
    The code must report the correct (joint) probability as R(lambda, a) and keep them separate.
    """
    decisions = ["approve"] * 10 + ["escalate"] * 50 + ["reject"] * 40
    # 2 of the approved units fail Stage 3; remaining 8 approved pass.
    # Among escalated/rejected, 30 fail and 60 pass.
    stage3_passes = ([False] * 2 + [True] * 8) + ([False] * 30 + [True] * 60)

    joint_risk, conditional_rate = compute_unconditional_joint_risk(decisions, stage3_passes)

    assert joint_risk == 0.02, f"Expected unconditional joint risk 0.02, got {joint_risk}"
    assert conditional_rate == 0.20, f"Expected conditional fail rate 0.20, got {conditional_rate}"
    assert joint_risk != conditional_rate, "R(lambda, a) and P(fail | approve) must diverge in low-approval scenarios"


def test_escalation_is_always_safe_property():
    """Verify that escalated units contribute zero error to R(lambda, a) by construction."""
    # Scenario: 50 units, ALL of which would fail Stage 3 if tested.
    # But all 50 units are escalated!
    decisions = ["escalate"] * 50
    stage3_passes = [False] * 50

    joint_risk, conditional_rate = compute_unconditional_joint_risk(decisions, stage3_passes)

    # Because zero units were early-approved, early-approval disagreement is exactly zero!
    assert joint_risk == 0.0
    assert conditional_rate == 0.0


def test_ltt_calibration_certifies_threshold_and_minimizes_test_time():
    """Verify LTT calibration certifies a valid policy on a reference sample and picks optimal policy."""
    sim = LotSimulator()
    lot = sim.create_same_source_lot(lot_id="LOT-NOMINAL-NMC-200", size=200, seed=42)

    # Draw reference sample of m = 45 (for eps = 0.05, delta = 0.10)
    ref_units, remaining_units = draw_reference_sample(lot.units, m=45, seed=42)
    assert len(ref_units) == 45
    assert len(remaining_units) == 155

    calibrator = LTTCalibrationEngine()
    policy = calibrator.calibrate_application(
        reference_units=ref_units,
        application_id="solar_backup",
        epsilon=0.05,
        delta=0.10
    )

    assert policy.is_certified is True
    assert policy.certified_risk_bound <= 0.05
    assert policy.expected_mean_test_time_s < 14400.0  # Much faster than full Stage 3 testing
    assert policy.lambda_approve_threshold > policy.lambda_reject_threshold
