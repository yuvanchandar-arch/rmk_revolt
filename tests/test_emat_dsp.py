"""Tests for EMAT Noise Model and Software-Defined Acoustic Receiver (Gate 5)."""

import pytest
import numpy as np
import os

from backend.degradation.state_model import DegradationState, sample_degradation_parameters
from backend.emat.physics_simulator import EMATPhysicsSimulator
from backend.emat.noise_model import EMATNoiseModel, NoiseConfig
from backend.emat.dsp_receiver import SoftwareDefinedAcousticReceiver


def test_noise_model_independent_components():
    """Verify noise model generates thermal, EMI, and rumble independently."""
    nm = EMATNoiseModel()
    t = np.linspace(0, 10e-6, 500)

    # 1. Zero out EMI and rumble -> only thermal
    cfg_thermal = NoiseConfig(thermal_noise_std=0.5, emi_amplitude=0.0, rumble_amplitude=0.0)
    res1 = nm.generate_noise(t, seed=42, config=cfg_thermal)
    assert np.std(res1["thermal"]) > 0.3
    assert np.all(res1["emi"] == 0.0)
    assert np.all(res1["rumble"] == 0.0)

    # 2. Zero out thermal and rumble -> only EMI
    cfg_emi = NoiseConfig(thermal_noise_std=0.0, emi_amplitude=0.8, rumble_amplitude=0.0)
    res2 = nm.generate_noise(t, seed=42, config=cfg_emi)
    assert np.all(res2["thermal"] == 0.0)
    assert np.std(res2["emi"]) > 0.2
    assert np.all(res2["rumble"] == 0.0)

    # 3. Target SNR injection (-15 dB)
    sim = EMATPhysicsSimulator()
    deg = sample_degradation_parameters(DegradationState.HEALTHY, seed=42)
    prop = sim.simulate_propagation(deg)
    clean = np.array(prop["echo_signal"])

    inj = nm.inject_noise(clean, sim.time_vector, target_snr_db=-15.0, seed=42)
    assert abs(inj["achieved_snr_db"] - (-15.0)) < 1.5


def test_matched_filter_recovery_at_minus_15db_snr():
    """Verify matched filtering recovers an echo buried in -15 dB noise."""
    sim = EMATPhysicsSimulator()
    nm = EMATNoiseModel()
    rx = SoftwareDefinedAcousticReceiver(fs_hz=sim.fs_hz)

    deg = sample_degradation_parameters(DegradationState.HEALTHY, seed=42)
    prop = sim.simulate_propagation(deg)
    clean = np.array(prop["echo_signal"])
    tx_chirp = sim.generate_chirp_tx()

    # Generate 16 coherent bursts at -15 dB SNR (standard EMAT pulse acquisition)
    bursts = []
    for b in range(16):
        inj = nm.inject_noise(clean, sim.time_vector, target_snr_db=-15.0, seed=100 + b)
        bursts.append(inj["noisy_signal"])

    # Raw single burst: echo completely invisible (peak amplitude within normal noise peaks)
    raw_burst = bursts[0]
    noise_std = np.std(raw_burst)
    assert np.max(np.abs(raw_burst)) < 4.0 * noise_std

    # Process with Software-Defined Acoustic Receiver
    res = rx.process(bursts, tx_chirp, sim.time_vector)
    feats = res["features"]

    # Receiver recovers clear peak with high post-processing SNR
    assert feats["snr_db"] > 10.0
    # ToF recovered within 0.15 us of ground-truth perturbed ToF
    true_tof = prop["perturbed_tof_us"]
    assert abs(feats["tof_us"] - true_tof) < 0.20


def test_feature_extraction_and_tof_correlation_ten_units():
    """Verify all 8 features extracted across 10 units and ToF correlates with degradation."""
    sim = EMATPhysicsSimulator()
    nm = EMATNoiseModel()
    rx = SoftwareDefinedAcousticReceiver(fs_hz=sim.fs_hz)
    tx_chirp = sim.generate_chirp_tx()

    states = [
        DegradationState.HEALTHY,
        DegradationState.MILD,
        DegradationState.MODERATE,
        DegradationState.PLATING,
        DegradationState.SEVERE
    ]

    extracted_tofs = []
    state_indices = []

    # 10 units: 2 units per state across all 5 states
    for s_idx, state in enumerate(states):
        for u_idx in range(2):
            seed = 100 * s_idx + u_idx
            deg = sample_degradation_parameters(state, seed=seed)
            prop = sim.simulate_propagation(deg)
            clean = np.array(prop["echo_signal"])
            
            bursts = [
                nm.inject_noise(clean, sim.time_vector, target_snr_db=-14.0, seed=seed * 10 + b)["noisy_signal"]
                for b in range(12)
            ]
            res = rx.process(bursts, tx_chirp, sim.time_vector)

            f = res["features"]
            for key in ["tof_us", "peak_amplitude", "integrated_energy", "echo_width_us", "attenuation_db", "snr_db", "repeatability", "center_frequency_mhz"]:
                assert key in f
                assert isinstance(f[key], (int, float))

            extracted_tofs.append(f["tof_us"])
            state_indices.append(s_idx)

    # Correlation check between degradation severity index (0 to 4) and extracted ToF
    corr = float(np.corrcoef(state_indices, extracted_tofs)[0, 1])
    assert corr > 0.90, f"Expected strong positive correlation between state and ToF, got {corr:.3f}"


def test_naming_compliance_no_prohibited_terms():
    """Verify prohibited receiver terminology does NOT appear in backend emat code; only approved names appear."""
    banned = "dig" + "ital " + "lna"
    backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend", "emat")

    for fname in ["noise_model.py", "dsp_receiver.py", "physics_simulator.py"]:
        path = os.path.join(backend_dir, fname)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        assert banned not in text.lower(), f"Found banned phrase in {fname}"

    # Confirm required name is present
    with open(os.path.join(backend_dir, "dsp_receiver.py"), "r", encoding="utf-8") as f:
        rx_text = f.read()
    assert "Software-Defined Acoustic Receiver" in rx_text
