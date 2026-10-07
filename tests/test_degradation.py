"""Tests for Degradation State Model (Gate 3)."""

import pytest
from backend.degradation.state_model import (
    DegradationState,
    STATE_DEFINITIONS,
    sample_degradation_parameters
)


def test_all_five_states_defined_with_ranges():
    """Verify that all five states exist with defined numeric ranges and rationales."""
    expected_states = [
        DegradationState.HEALTHY,
        DegradationState.MILD,
        DegradationState.MODERATE,
        DegradationState.PLATING,
        DegradationState.SEVERE
    ]
    assert len(STATE_DEFINITIONS) == 5
    for state in expected_states:
        assert state in STATE_DEFINITIONS
        defn = STATE_DEFINITIONS[state]
        assert defn.capacity_fade_pct_range[0] <= defn.capacity_fade_pct_range[1]
        assert defn.dcir_mohm_range[0] <= defn.dcir_mohm_range[1]
        assert defn.tof_shift_us_range[0] <= defn.tof_shift_us_range[1]
        assert defn.amp_attenuation_db_range[0] <= defn.amp_attenuation_db_range[1]
        assert defn.energy_attenuation_db_range[0] <= defn.energy_attenuation_db_range[1]
        assert defn.plating_thickness_um_range[0] <= defn.plating_thickness_um_range[1]
        assert len(defn.rationale) > 20


def test_determinism_same_seed_identical_output():
    """Prove that same state + same seed yields identical outputs across multiple runs."""
    for state in DegradationState:
        run1 = sample_degradation_parameters(state, seed=12345)
        run2 = sample_degradation_parameters(state, seed=12345)

        assert run1.to_dict() == run2.to_dict(), f"Determinism failure for {state}"
        assert run1.capacity_fade_pct == run2.capacity_fade_pct
        assert run1.dcir_mohm == run2.dcir_mohm
        assert run1.tof_shift_us == run2.tof_shift_us
        assert run1.amp_attenuation_db == run2.amp_attenuation_db
        assert run1.energy_attenuation_db == run2.energy_attenuation_db
        assert run1.plating_thickness_um == run2.plating_thickness_um


def test_range_compliance_over_100_seeds():
    """Verify across 100 seeds per state that all values lie strictly within documented bounds."""
    for state in DegradationState:
        defn = STATE_DEFINITIONS[state]
        for seed_idx in range(100):
            p = sample_degradation_parameters(state, seed=seed_idx)

            # Capacity fade
            assert defn.capacity_fade_pct_range[0] <= p.capacity_fade_pct <= defn.capacity_fade_pct_range[1], \
                f"Capacity fade {p.capacity_fade_pct} out of range for {state}"

            # DCIR
            assert defn.dcir_mohm_range[0] <= p.dcir_mohm <= defn.dcir_mohm_range[1], \
                f"DCIR {p.dcir_mohm} out of range for {state}"

            # ToF shift
            assert defn.tof_shift_us_range[0] <= p.tof_shift_us <= defn.tof_shift_us_range[1], \
                f"ToF shift {p.tof_shift_us} out of range for {state}"

            # Amp attenuation
            assert defn.amp_attenuation_db_range[0] <= p.amp_attenuation_db <= defn.amp_attenuation_db_range[1], \
                f"Amp attenuation {p.amp_attenuation_db} out of range for {state}"

            # Energy attenuation
            assert defn.energy_attenuation_db_range[0] <= p.energy_attenuation_db <= defn.energy_attenuation_db_range[1], \
                f"Energy attenuation {p.energy_attenuation_db} out of range for {state}"

            # Plating thickness
            assert defn.plating_thickness_um_range[0] <= p.plating_thickness_um <= defn.plating_thickness_um_range[1], \
                f"Plating thickness {p.plating_thickness_um} out of range for {state}"
