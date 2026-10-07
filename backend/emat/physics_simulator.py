"""EMAT Multilayer Acoustic Physics Simulator ("The Encoder").

Scientific Framing Requirement:
In this module, degradation and plating perturb the acoustic propagation characteristics
of the cell — modifying wave speed, interfacial impedance mismatch, scattering, and attenuation
through the layered cell structure. Metallic deposits and SEI growth act as inhomogeneous,
dissipative acoustic perturbations at the electrode-separator interface.

Multilayer Acoustic Propagation Path:
EMAT transducer -> aluminum casing -> electrode stack -> separator/electrolyte ->
graphite anode region -> degradation/plating proxy layer.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

from backend.degradation.state_model import DegradationState, DegradationParameters, sample_degradation_parameters


@dataclass
class AcousticLayer:
    """Represents a discrete medium in the multilayer acoustic propagation path."""
    name: str
    thickness_mm: float
    velocity_m_s: float
    density_kg_m3: float
    impedance_mrayl: float
    attenuation_db_mm: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def get_default_layer_stack(plating_thickness_um: float = 0.0) -> List[AcousticLayer]:
    """Builds the 5-layer acoustic propagation medium.
    
    Layers:
    1. Aluminum outer casing
    2. Electrode stack (anode/cathode composite)
    3. Separator / electrolyte
    4. Graphite anode region
    5. Degradation / plating proxy layer (perturbed thickness and acoustic characteristics)
    """
    # Degradation and plating perturb the acoustic propagation characteristics of the cell
    proxy_thick_mm = max(0.0001, plating_thickness_um / 1000.0)
    
    return [
        AcousticLayer(
            name="aluminum_casing",
            thickness_mm=0.8,
            velocity_m_s=6320.0,
            density_kg_m3=2700.0,
            impedance_mrayl=17.06,  # 2.7 * 6320 / 1000
            attenuation_db_mm=0.05
        ),
        AcousticLayer(
            name="electrode_stack",
            thickness_mm=3.2,
            velocity_m_s=2250.0,
            density_kg_m3=2200.0,
            impedance_mrayl=4.95,
            attenuation_db_mm=0.45
        ),
        AcousticLayer(
            name="separator_electrolyte",
            thickness_mm=0.025,
            velocity_m_s=1480.0,
            density_kg_m3=1200.0,
            impedance_mrayl=1.77,
            attenuation_db_mm=0.80
        ),
        AcousticLayer(
            name="graphite_anode_region",
            thickness_mm=0.15,
            velocity_m_s=1850.0,
            density_kg_m3=1950.0,
            impedance_mrayl=3.61,
            attenuation_db_mm=0.60
        ),
        AcousticLayer(
            name="degradation_plating_proxy_layer",
            thickness_mm=proxy_thick_mm,
            velocity_m_s=1350.0,  # Lower wave velocity in porous/plated perturbation zone
            density_kg_m3=1400.0,
            impedance_mrayl=1.89,
            attenuation_db_mm=1.50
        )
    ]


class EMATPhysicsSimulator:
    """Simulates chirp transmission and multilayer acoustic echo generation.
    
    Degradation and plating perturb the acoustic propagation characteristics of the cell,
    producing measurable Time-of-Flight (ToF) delays and amplitude/energy attenuation.
    """

    def __init__(
        self,
        fs_hz: float = 20e6,           # 20 MHz sampling frequency
        chirp_duration_s: float = 2.5e-6, # 2.5 microseconds chirp
        f0_hz: float = 1.0e6,          # Start frequency: 1.0 MHz
        f1_hz: float = 4.0e6,          # End frequency: 4.0 MHz
        total_time_s: float = 12.0e-6  # 12 microseconds recording window
    ):
        self.fs_hz = fs_hz
        self.chirp_duration_s = chirp_duration_s
        self.f0_hz = f0_hz
        self.f1_hz = f1_hz
        self.total_time_s = total_time_s
        self.dt = 1.0 / fs_hz
        self.time_vector = np.arange(0, total_time_s, self.dt)

    def generate_chirp_tx(self) -> np.ndarray:
        """Generates a linear frequency-modulated (LFM) chirp pulse."""
        n_chirp = int(self.chirp_duration_s * self.fs_hz)
        t_chirp = np.arange(n_chirp) * self.dt
        k = (self.f1_hz - self.f0_hz) / self.chirp_duration_s
        # Windowed chirp with Tukey / cosine taper to prevent spectral leakage
        window = np.hanning(n_chirp)
        phase = 2.0 * np.pi * (self.f0_hz * t_chirp + 0.5 * k * (t_chirp ** 2))
        chirp = window * np.sin(phase)
        return chirp

    def simulate_propagation(
        self,
        degradation: DegradationParameters,
        layers: Optional[List[AcousticLayer]] = None
    ) -> Dict[str, Any]:
        """Propagates transmit chirp through the multilayer cell medium.
        
        Degradation and plating perturb the acoustic propagation characteristics of the cell,
        producing state-dependent round-trip delay (ToF) and attenuation.
        """
        if layers is None:
            layers = get_default_layer_stack(degradation.plating_thickness_um)

        chirp_tx = self.generate_chirp_tx()
        n_total = len(self.time_vector)
        tx_signal = np.zeros(n_total)
        tx_signal[:len(chirp_tx)] = chirp_tx

        # Calculate nominal two-way round-trip travel time across all layers
        # Base round trip time: 2 * sum(d_i / v_i)
        base_tof_s = 2.0 * sum((l.thickness_mm * 1e-3) / l.velocity_m_s for l in layers)
        
        # Additional perturbed delay from degradation state (ToF shift in microseconds)
        perturbed_tof_s = base_tof_s + (degradation.tof_shift_us * 1e-6)

        # Attenuation factor in linear amplitude scale (from dB)
        attenuation_lin = float(10.0 ** (degradation.amp_attenuation_db / 20.0))
        
        # Calculate echo arrival sample index
        echo_delay_samples = int(np.round(perturbed_tof_s * self.fs_hz))

        # Generate received echo waveform with slight dispersion spreading
        echo_signal = np.zeros(n_total)
        # Dispersion filter modeling frequency-dependent absorption in degraded layers
        dispersion_sigma = 1.0 + (degradation.capacity_fade_pct / 30.0)
        filt_pts = int(3 * dispersion_sigma)
        filt_kernel = np.exp(-0.5 * (np.arange(-filt_pts, filt_pts + 1) / max(0.5, dispersion_sigma)) ** 2)
        filt_kernel = filt_kernel / np.sum(filt_kernel)
        
        dispersed_chirp = np.convolve(chirp_tx, filt_kernel, mode="same")
        
        if echo_delay_samples < n_total:
            end_idx = min(n_total, echo_delay_samples + len(dispersed_chirp))
            len_copy = end_idx - echo_delay_samples
            echo_signal[echo_delay_samples:end_idx] = dispersed_chirp[:len_copy] * attenuation_lin

        # Peak amplitude and energy of clean echo
        peak_amp = float(np.max(np.abs(echo_signal))) if len(echo_signal) > 0 else 0.0
        echo_energy = float(np.sum(echo_signal ** 2) * self.dt)

        return {
            "time_us": (self.time_vector * 1e6).tolist(),
            "tx_signal": tx_signal.tolist(),
            "echo_signal": echo_signal.tolist(),
            "base_tof_us": round(base_tof_s * 1e6, 3),
            "perturbed_tof_us": round(perturbed_tof_s * 1e6, 3),
            "tof_shift_us": round(degradation.tof_shift_us, 3),
            "peak_amplitude": round(peak_amp, 5),
            "echo_energy": round(echo_energy, 9),
            "amp_attenuation_db": round(degradation.amp_attenuation_db, 2),
            "plating_thickness_um": round(degradation.plating_thickness_um, 2),
            "state": degradation.state,
            "layers": [l.to_dict() for l in layers]
        }
