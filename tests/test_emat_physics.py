"""Tests for EMAT Multilayer Acoustic Physics Simulator (Gate 4)."""

import pytest
import numpy as np
import os

from backend.degradation.state_model import DegradationState, sample_degradation_parameters
from backend.emat.physics_simulator import (
    AcousticLayer,
    get_default_layer_stack,
    EMATPhysicsSimulator
)


def test_multilayer_model_all_five_layers():
    """Verify all five layers from Section 5.3(a) are implemented with physical acoustic properties."""
    layers = get_default_layer_stack(plating_thickness_um=3.5)
    layer_names = [l.name for l in layers]

    expected_layers = [
        "aluminum_casing",
        "electrode_stack",
        "separator_electrolyte",
        "graphite_anode_region",
        "degradation_plating_proxy_layer"
    ]
    assert layer_names == expected_layers
    assert len(layers) == 5

    for l in layers:
        assert l.thickness_mm > 0
        assert l.velocity_m_s > 0
        assert l.density_kg_m3 > 0
        assert l.impedance_mrayl > 0
        assert l.attenuation_db_mm >= 0


def test_chirp_transmit_waveform_properties():
    """Chirp transmit pulse must be windowed, bandlimited, and have expected duration."""
    sim = EMATPhysicsSimulator(fs_hz=20e6, chirp_duration_s=2.5e-6)
    chirp = sim.generate_chirp_tx()

    expected_len = int(2.5e-6 * 20e6)
    assert len(chirp) == expected_len
    # Peak amplitude within [0.9, 1.0]
    assert 0.9 <= np.max(np.abs(chirp)) <= 1.01
    # Smooth start and end (tapered)
    assert abs(chirp[0]) < 0.05
    assert abs(chirp[-1]) < 0.05


def test_echo_delay_and_amplitude_change_across_states():
    """Echo delay and amplitude must demonstrably change across all 5 degradation states."""
    sim = EMATPhysicsSimulator()
    states = [
        DegradationState.HEALTHY,
        DegradationState.MILD,
        DegradationState.MODERATE,
        DegradationState.PLATING,
        DegradationState.SEVERE
    ]

    tofs = []
    amps = []

    for s in states:
        deg = sample_degradation_parameters(s, seed=42)
        res = sim.simulate_propagation(deg)

        tof = res["perturbed_tof_us"]
        amp = res["peak_amplitude"]
        tofs.append(tof)
        amps.append(amp)

    # ToF must monotonically increase as degradation severity increases
    for i in range(len(tofs) - 1):
        assert tofs[i + 1] > tofs[i], f"ToF did not increase from {states[i]} to {states[i+1]}"

    # Amplitude must monotonically decrease (attenuation increases)
    for i in range(len(amps) - 1):
        assert amps[i + 1] < amps[i], f"Amplitude did not decrease from {states[i]} to {states[i+1]}"


def test_framing_language_compliance():
    """Verify that docstrings and code use the required physical framing and ban prohibited phrases."""
    file_path = os.path.join(os.path.dirname(__file__), "..", "backend", "emat", "physics_simulator.py")
    with open(file_path, "r", encoding="utf-8") as f:
        code_text = f.read()

    # Banned phrasing
    banned_framing = "clean reflection " + "off a plating slab"
    assert banned_framing not in code_text.lower()

    # Mandatory phrasing
    assert "perturbs acoustic propagation characteristics" in code_text or \
           "perturb the acoustic propagation characteristics" in code_text
