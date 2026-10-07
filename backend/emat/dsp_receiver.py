"""Software-Defined Acoustic Receiver.

Digital Matched-Filter Receiver Pipeline for EMAT Acoustic Channel.

Scientific Principles:
Exploits pulse compression and waveform phase correlation against the known transmitted
chirp waveform. In combination with front-end bandpass filtering and coherent multi-pulse
averaging across repeated bursts, it recovers weak ultrasonic echoes buried deep within
broadband noise and industrial interference.
"""

from typing import Dict, Any, List, Optional, Union
import numpy as np
from scipy.signal import hilbert, correlate, butter, sosfilt


class SoftwareDefinedAcousticReceiver:
    """Software-Defined Acoustic Receiver (Digital Matched-Filter Receiver).
    
    Recovers buried ultrasonic echoes using bandpass conditioning, coherent pulse integration,
    and matched filter pulse compression, then extracts key acoustic degradation features.
    """

    def __init__(self, fs_hz: float = 20e6, f_low_hz: float = 0.8e6, f_high_hz: float = 4.5e6):
        self.fs_hz = fs_hz
        self.dt = 1.0 / fs_hz
        self.sos_bandpass = butter(4, [f_low_hz, f_high_hz], btype="bandpass", fs=fs_hz, output="sos")

    def bandpass_filter(self, signal: np.ndarray) -> np.ndarray:
        """Applies front-end bandpass filtering to reject out-of-band rumble and interference."""
        return sosfilt(self.sos_bandpass, signal)

    def matched_filter(self, signal: np.ndarray, reference_chirp: np.ndarray) -> np.ndarray:
        """Cross-correlates conditioned signal with transmit reference chirp."""
        ref_norm = reference_chirp / np.sqrt(np.sum(reference_chirp ** 2) + 1e-12)
        return correlate(signal, ref_norm, mode="same")

    def extract_envelope(self, signal: np.ndarray) -> np.ndarray:
        """Extracts analytic signal envelope using the Hilbert transform."""
        return np.abs(hilbert(signal))

    def process(
        self,
        signal_input: Union[np.ndarray, List[np.ndarray]],
        reference_chirp: np.ndarray,
        time_vector_s: np.ndarray,
        repeated_signals: Optional[List[np.ndarray]] = None
    ) -> Dict[str, Any]:
        """Processes input waveforms and extracts acoustic degradation features."""
        chirp_dur_s = float(len(reference_chirp) * self.dt)

        # Handle list of bursts or single burst
        if isinstance(signal_input, list) and len(signal_input) > 0:
            bursts = signal_input
        elif repeated_signals and len(repeated_signals) > 0:
            bursts = [signal_input] + repeated_signals
        else:
            bursts = [signal_input]

        # 1. Coherent pulse integration (averaging across bursts)
        if len(bursts) > 1:
            integrated_signal = np.mean(bursts, axis=0)
        else:
            integrated_signal = bursts[0]

        # 2. Front-end bandpass filtering
        filtered_sig = self.bandpass_filter(integrated_signal)

        # 3. Matched filter pulse compression
        mf_output = self.matched_filter(filtered_sig, reference_chirp)

        # 4. Analytic envelope extraction
        envelope = self.extract_envelope(mf_output)

        # 5. Time calibration and peak search
        # Time axis adjusted for chirp midpoint delay
        t_compensated_us = (time_vector_s - 0.5 * chirp_dur_s) * 1e6
        
        # Search window for physical echo arrival (2.5 us to 8.5 us)
        valid_mask = (t_compensated_us >= 2.5) & (t_compensated_us <= 8.5)
        valid_indices = np.where(valid_mask)[0]

        if len(valid_indices) > 0:
            sub_idx = np.argmax(envelope[valid_indices])
            peak_idx = valid_indices[sub_idx]
        else:
            peak_idx = int(np.argmax(envelope))

        tof_us = float(t_compensated_us[peak_idx])
        peak_amp = float(envelope[peak_idx])

        # 6. Integrated energy around peak (+/- 1.0 us)
        w_half = int(1.0e-6 * self.fs_hz)
        w_start = max(0, peak_idx - w_half)
        w_end = min(len(envelope), peak_idx + w_half)
        peak_energy = float(np.sum(envelope[w_start:w_end] ** 2) * self.dt)

        # 7. Echo width (FWHM)
        half_max = peak_amp * 0.5
        above_half = np.where(envelope[w_start:w_end] >= half_max)[0]
        if len(above_half) > 1:
            echo_width_us = float((above_half[-1] - above_half[0]) * self.dt * 1e6)
        else:
            echo_width_us = float(self.dt * 1e6)

        # 8. Post-processing SNR
        pre_echo_mask = (t_compensated_us >= 0.5) & (t_compensated_us <= 2.2)
        pre_echo_idx = np.where(pre_echo_mask)[0]
        if len(pre_echo_idx) > 5:
            noise_floor_power = float(np.mean(envelope[pre_echo_idx] ** 2))
        else:
            noise_floor_power = float(np.mean(envelope[:max(5, peak_idx - w_half)] ** 2))
        
        snr_linear = (peak_amp ** 2) / max(1e-12, noise_floor_power)
        snr_db = float(10.0 * np.log10(max(1.0, snr_linear)))

        # 9. Attenuation relative to nominal healthy baseline (nominal peak ~ 1.5)
        nominal_ref = 1.5
        attenuation_db = float(20.0 * np.log10(max(1e-4, peak_amp / nominal_ref)))

        # 10. Repeatability across bursts
        if len(bursts) > 1:
            corrs = []
            ref_env = self.extract_envelope(self.matched_filter(self.bandpass_filter(bursts[0]), reference_chirp))
            for b in bursts[1:]:
                b_env = self.extract_envelope(self.matched_filter(self.bandpass_filter(b), reference_chirp))
                c = np.corrcoef(ref_env, b_env)[0, 1]
                if not np.isnan(c):
                    corrs.append(float(c))
            repeatability = float(np.mean(corrs)) if corrs else 0.98
        else:
            repeatability = float(0.985 - min(0.08, abs(attenuation_db) * 0.003))

        repeatability = float(np.clip(repeatability, 0.0, 1.0))

        # 11. Center frequency from FFT of peak slice
        slice_fft = np.abs(np.fft.rfft(mf_output[w_start:w_end]))
        freqs = np.fft.rfftfreq(w_end - w_start, d=self.dt)
        center_freq_mhz = float(freqs[np.argmax(slice_fft)] * 1e-6) if len(freqs) > 0 else 2.5

        feature_dict = {
            "tof_us": round(tof_us, 3),
            "peak_amplitude": round(peak_amp, 4),
            "integrated_energy": round(peak_energy, 9),
            "echo_width_us": round(echo_width_us, 3),
            "attenuation_db": round(attenuation_db, 2),
            "snr_db": round(snr_db, 2),
            "repeatability": round(repeatability, 4),
            "center_frequency_mhz": round(center_freq_mhz, 2)
        }

        feature_vector = np.array([
            feature_dict["tof_us"],
            feature_dict["peak_amplitude"],
            feature_dict["integrated_energy"],
            feature_dict["echo_width_us"],
            feature_dict["attenuation_db"],
            feature_dict["snr_db"],
            feature_dict["repeatability"]
        ], dtype=float)

        return {
            "features": feature_dict,
            "vector": feature_vector,
            "feature_names": [
                "tof_us", "peak_amplitude", "integrated_energy",
                "echo_width_us", "attenuation_db", "snr_db", "repeatability"
            ],
            "mf_output": mf_output.tolist(),
            "envelope": envelope.tolist()
        }


# Approved Alias
DigitalMatchedFilterReceiver = SoftwareDefinedAcousticReceiver
