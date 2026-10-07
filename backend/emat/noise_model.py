"""EMAT Acoustic Channel Noise Model ("The Attenuator").

Simulates realistic battery test-bench and operational acoustic noise:
1. White thermal noise (broadband Johnson-Nyquist thermal background)
2. Sinusoidal EMI (inverter / switching motor harmonics, e.g. 50 kHz, 250 kHz, 1.2 MHz)
3. Low-frequency rumble (conveyor / mechanical vibration < 40 kHz)

Allows independent configuration of noise sources or automatic calibration to a target SNR (e.g. -15 dB).
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
import numpy as np


@dataclass
class NoiseConfig:
    thermal_noise_std: float = 0.35
    emi_amplitude: float = 0.25
    emi_frequencies_hz: tuple = (60e3, 200e3, 1.2e6)
    rumble_amplitude: float = 0.20
    rumble_freq_hz: float = 15e3

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EMATNoiseModel:
    """Injects independently configurable thermal noise, sinusoidal EMI, and rumble."""

    def __init__(self, config: Optional[NoiseConfig] = None):
        self.config = config or NoiseConfig()

    def generate_noise(
        self,
        time_vector_s: np.ndarray,
        seed: int = 42,
        config: Optional[NoiseConfig] = None
    ) -> Dict[str, np.ndarray]:
        """Generates the three independent noise components."""
        cfg = config or self.config
        rng = np.random.default_rng(seed)
        n_pts = len(time_vector_s)

        # 1. White thermal noise
        thermal = rng.normal(0.0, cfg.thermal_noise_std, n_pts)

        # 2. Sinusoidal EMI
        emi = np.zeros(n_pts)
        for freq in cfg.emi_frequencies_hz:
            phase = rng.uniform(0, 2.0 * np.pi)
            emi += (cfg.emi_amplitude / len(cfg.emi_frequencies_hz)) * np.sin(2.0 * np.pi * freq * time_vector_s + phase)

        # 3. Low-frequency mechanical rumble
        rumble_phase = rng.uniform(0, 2.0 * np.pi)
        rumble = cfg.rumble_amplitude * np.sin(2.0 * np.pi * cfg.rumble_freq_hz * time_vector_s + rumble_phase)

        total_noise = thermal + emi + rumble

        return {
            "thermal": thermal,
            "emi": emi,
            "rumble": rumble,
            "total_noise": total_noise
        }

    def inject_noise(
        self,
        clean_signal: np.ndarray,
        time_vector_s: np.ndarray,
        target_snr_db: Optional[float] = None,
        seed: int = 42
    ) -> Dict[str, Any]:
        """Injects noise into clean echo signal, optionally scaling to exact target SNR."""
        noise_dict = self.generate_noise(time_vector_s, seed=seed)
        total_noise = noise_dict["total_noise"]

        # Calculate signal and noise powers
        sig_power = float(np.mean(clean_signal ** 2))
        raw_noise_power = float(np.mean(total_noise ** 2))

        if target_snr_db is not None:
            # Desired SNR = 10 * log10(sig_power / noise_power)
            # noise_power = sig_power / 10^(target_snr / 10)
            if sig_power > 1e-12:
                desired_noise_power = sig_power / (10.0 ** (target_snr_db / 10.0))
                scaling = np.sqrt(desired_noise_power / max(1e-12, raw_noise_power))
                total_noise = total_noise * scaling
                for k in ["thermal", "emi", "rumble"]:
                    noise_dict[k] = noise_dict[k] * scaling

        noisy_signal = clean_signal + total_noise

        actual_snr_db = 10.0 * np.log10(max(1e-12, sig_power) / max(1e-12, float(np.mean(total_noise ** 2))))

        return {
            "noisy_signal": noisy_signal,
            "total_noise": total_noise,
            "thermal": noise_dict["thermal"],
            "emi": noise_dict["emi"],
            "rumble": noise_dict["rumble"],
            "achieved_snr_db": round(float(actual_snr_db), 2)
        }
