"""Multimodal Feature Fusion Module.

Combines Stage-1 electrical fingerprint features with EMAT acoustic features.
Supports three run modes (as required by Section 5.5 of 01_project_details.md):
1. Electrical-only (6 features)
2. Acoustic-only (7 features)
3. Electrical + Acoustic (fused) — the primary mode (13 features)
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Union
import numpy as np

from backend.data.loaders import BatteryRecord
from backend.electrical.features import ElectricalFeatureExtractor
from backend.degradation.state_model import (
    DegradationState,
    sample_degradation_parameters
)
from backend.emat.physics_simulator import EMATPhysicsSimulator
from backend.emat.noise_model import EMATNoiseModel
from backend.emat.dsp_receiver import SoftwareDefinedAcousticReceiver


class RunMode(str, Enum):
    ELECTRICAL_ONLY = "electrical_only"
    ACOUSTIC_ONLY = "acoustic_only"
    FUSED = "fused"


# Fused feature schema specification
FUSED_FEATURE_SCHEMA = [
    # Electrical modality (Stage 1)
    {"field": "ocv_v", "modality": "electrical", "units": "V", "description": "Open-circuit voltage at rest"},
    {"field": "dcir_mohm", "modality": "electrical", "units": "mΩ", "description": "DC internal-resistance proxy (ΔV/ΔI)"},
    {"field": "relaxation_slope", "modality": "electrical", "units": "V/s", "description": "Voltage-relaxation slope after pulse"},
    {"field": "relaxation_curvature", "modality": "electrical", "units": "V/s²", "description": "Voltage-relaxation curvature after pulse"},
    {"field": "temperature_response_c", "modality": "electrical", "units": "°C", "description": "Surface temperature rise during pulse"},
    {"field": "cell_imbalance_mv", "modality": "electrical", "units": "mV", "description": "Cell voltage imbalance/spread"},
    # Acoustic modality (EMAT Software-Defined Receiver)
    {"field": "tof_us", "modality": "acoustic", "units": "μs", "description": "Ultrasonic Time-of-Flight arrival delay"},
    {"field": "peak_amplitude", "modality": "acoustic", "units": "V", "description": "Matched-filter envelope correlation peak amplitude"},
    {"field": "integrated_energy", "modality": "acoustic", "units": "V²·s", "description": "Integrated energy in echo correlation window"},
    {"field": "echo_width_us", "modality": "acoustic", "units": "μs", "description": "Echo pulse compression FWHM width"},
    {"field": "attenuation_db", "modality": "acoustic", "units": "dB", "description": "Acoustic signal attenuation relative to healthy reference"},
    {"field": "snr_db", "modality": "acoustic", "units": "dB", "description": "Post-processing Signal-to-Noise Ratio"},
    {"field": "repeatability", "modality": "acoustic", "units": "ratio", "description": "Cross-correlation repeatability across bursts"}
]


class MultimodalFusionEngine:
    """Extracts, couples, and fuses electrical and acoustic features per battery unit."""

    def __init__(self):
        self.elec_extractor = ElectricalFeatureExtractor()
        self.emat_sim = EMATPhysicsSimulator()
        self.noise_model = EMATNoiseModel()
        self.dsp_receiver = SoftwareDefinedAcousticReceiver(fs_hz=self.emat_sim.fs_hz)

    def map_unit_to_degradation_state(self, record: Union[BatteryRecord, Dict[str, Any]]) -> DegradationState:
        """Determines underlying physical degradation state for acoustic coupling."""
        fade = float(record.capacity_fade_pct if isinstance(record, BatteryRecord) else record.get("capacity_fade_pct", 15.0))
        usage = str(record.usage_history if isinstance(record, BatteryRecord) else record.get("usage_history", "commuter"))

        # High usage / aggressive fast charging biases toward lithium plating risk
        if usage in ["aggressive_fast_charge", "taxi"] and fade >= 22.0:
            return DegradationState.PLATING
        elif fade < 8.0:
            return DegradationState.HEALTHY
        elif fade < 16.0:
            return DegradationState.MILD
        elif fade < 24.0:
            return DegradationState.MODERATE
        elif fade < 32.0:
            return DegradationState.PLATING
        else:
            return DegradationState.SEVERE

    def extract_electrical(self, record: Union[BatteryRecord, Dict[str, Any]]) -> Dict[str, Any]:
        """Extracts Stage-1 electrical feature dictionary and vector."""
        res = self.elec_extractor.extract_features(record)
        return {
            "features": {k: res["features"][k] for k in [
                "ocv_v", "dcir_mohm", "relaxation_slope",
                "relaxation_curvature", "temperature_response_c", "cell_imbalance_mv"
            ]},
            "vector": res["vector"],
            "feature_names": [
                "ocv_v", "dcir_mohm", "relaxation_slope",
                "relaxation_curvature", "temperature_response_c", "cell_imbalance_mv"
            ]
        }

    def extract_acoustic(
        self,
        record: Union[BatteryRecord, Dict[str, Any]],
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """Simulates EMAT sensing and DSP receiver extraction for the unit."""
        unit_id = record.unit_id if isinstance(record, BatteryRecord) else record.get("unit_id", "U0")
        if seed is None:
            # Hash unit_id for reproducible determinism
            seed = int(abs(hash(unit_id)) % 100000)

        state = self.map_unit_to_degradation_state(record)
        deg_params = sample_degradation_parameters(state, seed=seed)
        prop = self.emat_sim.simulate_propagation(deg_params)
        clean_echo = np.array(prop["echo_signal"])
        tx_chirp = self.emat_sim.generate_chirp_tx()

        # Generate coherent bursts (12 pulses) at -14 dB SNR
        bursts = [
            self.noise_model.inject_noise(
                clean_echo, self.emat_sim.time_vector, target_snr_db=-14.0, seed=seed + b * 13
            )["noisy_signal"]
            for b in range(12)
        ]

        res = self.dsp_receiver.process(bursts, tx_chirp, self.emat_sim.time_vector)
        feats = res["features"]
        
        # Selected 7 core acoustic features
        acoustic_names = [
            "tof_us", "peak_amplitude", "integrated_energy",
            "echo_width_us", "attenuation_db", "snr_db", "repeatability"
        ]
        acoustic_feats = {k: feats[k] for k in acoustic_names}
        acoustic_vector = np.array([acoustic_feats[k] for k in acoustic_names], dtype=float)

        return {
            "features": acoustic_feats,
            "vector": acoustic_vector,
            "feature_names": acoustic_names,
            "raw_dsp": res,
            "degradation_state": state.value
        }

    def fuse(
        self,
        record: Union[BatteryRecord, Dict[str, Any]],
        mode: RunMode = RunMode.FUSED,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """Produces electrical-only, acoustic-only, or fused feature vectors on demand."""
        unit_id = record.unit_id if isinstance(record, BatteryRecord) else record.get("unit_id", "UNKNOWN")

        if mode == RunMode.ELECTRICAL_ONLY:
            elec = self.extract_electrical(record)
            return {
                "unit_id": unit_id,
                "mode": mode.value,
                "features": elec["features"],
                "vector": elec["vector"],
                "feature_names": elec["feature_names"],
                "dimension": len(elec["feature_names"])
            }
        elif mode == RunMode.ACOUSTIC_ONLY:
            acous = self.extract_acoustic(record, seed=seed)
            return {
                "unit_id": unit_id,
                "mode": mode.value,
                "features": acous["features"],
                "vector": acous["vector"],
                "feature_names": acous["feature_names"],
                "dimension": len(acous["feature_names"]),
                "degradation_state": acous["degradation_state"]
            }
        else:
            # RunMode.FUSED
            elec = self.extract_electrical(record)
            acous = self.extract_acoustic(record, seed=seed)

            fused_dict = {**elec["features"], **acous["features"]}
            fused_names = elec["feature_names"] + acous["feature_names"]
            fused_vector = np.concatenate([elec["vector"], acous["vector"]])

            return {
                "unit_id": unit_id,
                "mode": mode.value,
                "features": fused_dict,
                "vector": fused_vector,
                "feature_names": fused_names,
                "dimension": len(fused_names),
                "degradation_state": acous["degradation_state"]
            }
