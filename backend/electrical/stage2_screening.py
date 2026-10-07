"""Stage 2 Extended Electrical Screening Pipeline.

Activated when a unit escalates from Stage 1. Computes a distinct, richer set of
higher-order electrochemical and kinetic features from extended pulse and relaxation dynamics:
1. Fast relaxation time constant (tau_fast)
2. Slow diffusion time constant (tau_slow)
3. Ohmic resistance (R_ohmic)
4. Charge-transfer polarization resistance (R_charge_transfer)
5. Diffusion polarization resistance (R_diffusion)
6. Polarization index (ratio of polarization resistance to ohmic resistance)
7. Normalized Joule heating rate (W / A^2)
8. Overpotential recovery ratio
"""

from typing import Dict, Any, Union
import numpy as np
from backend.data.loaders import BatteryRecord


class Stage2ScreeningPipeline:
    """Extracts extended multi-timescale electrical features for escalated units."""

    def extract_extended_features(self, record: Union[BatteryRecord, Dict[str, Any]]) -> Dict[str, Any]:
        if isinstance(record, dict):
            unit_id = record.get("unit_id", "UNKNOWN")
            early_feats = record.get("early_features", {})
            time_series = record.get("time_series", {})
            nom_cap = float(record.get("nominal_capacity_ah", 2.0))
        else:
            unit_id = record.unit_id
            early_feats = record.early_features
            time_series = record.time_series
            nom_cap = record.nominal_capacity_ah

        # Base DCIR and relaxation from Stage 1
        dcir = max(0.1, float(early_feats.get("dcir_mohm", 20.0)))
        rel_slope = abs(float(early_feats.get("relaxation_slope", 0.05)))
        rel_curv = abs(float(early_feats.get("relaxation_curvature", 0.01)))
        temp_rise = float(early_feats.get("temp_rise_c", 0.5))

        # Kinetic decomposition into multi-timescale impedance components
        # R_ohmic is approximately 55-65% of total high-rate DCIR
        r_ohmic = dcir * 0.60
        # R_charge_transfer reflects double-layer activation kinetics (~25-30%)
        r_ct = dcir * 0.28 * (1.0 + min(rel_slope * 2.0, 1.5))
        # R_diffusion reflects solid-state Li+ diffusion in electrode particles (~10-15%)
        r_diff = dcir * 0.12 * (1.0 + min(rel_curv * 10.0, 2.0))

        # Time constants (seconds)
        tau_fast = float(np.clip(0.4 + 0.05 * (dcir / 10.0), 0.2, 3.0))
        tau_slow = float(np.clip(5.0 + 0.8 * (dcir / 10.0), 3.0, 25.0))

        # Dimensionless kinetic ratios
        polarization_index = float((r_ct + r_diff) / max(0.1, r_ohmic))
        joule_rate = float((temp_rise) / max(0.01, (nom_cap * 2.0) ** 2))
        overpotential_recovery_ratio = float(np.clip(0.65 + 0.25 * np.exp(-rel_slope), 0.4, 0.98))

        # Refine if full time-series is available
        if time_series and "voltage_v" in time_series and len(time_series["voltage_v"]) > 200:
            voltages = np.array(time_series["voltage_v"])
            times = np.array(time_series["time_s"])
            currents = np.array(time_series["current_a"])
            
            # Post-pulse relaxation window (e.g. t >= 15.0s)
            relax_idx = np.where(times >= 15.0)[0]
            if len(relax_idx) > 20:
                t_rel = times[relax_idx] - times[relax_idx[0]]
                v_rel = voltages[relax_idx]
                v_inf = v_rel[-1]
                v_delta = np.maximum(1e-5, np.abs(v_inf - v_rel))
                
                # Fit two exponential decay rates if possible
                log_vd = np.log(v_delta)
                # Early slope (0.1s to 2s)
                early_w = np.where((t_rel >= 0.1) & (t_rel <= 2.0))[0]
                if len(early_w) > 3:
                    p_early = np.polyfit(t_rel[early_w], log_vd[early_w], 1)
                    if p_early[0] < 0:
                        tau_fast = float(np.clip(-1.0 / p_early[0], 0.1, 5.0))
                
                # Late slope (5s to 14s)
                late_w = np.where(t_rel >= 4.0)[0]
                if len(late_w) > 5:
                    p_late = np.polyfit(t_rel[late_w], log_vd[late_w], 1)
                    if p_late[0] < 0:
                        tau_slow = float(np.clip(-1.0 / p_late[0], 2.0, 30.0))

        extended_dict = {
            "unit_id": unit_id,
            "tau_fast_s": round(tau_fast, 3),
            "tau_slow_s": round(tau_slow, 2),
            "r_ohmic_mohm": round(r_ohmic, 2),
            "r_charge_transfer_mohm": round(r_ct, 2),
            "r_diffusion_mohm": round(r_diff, 2),
            "polarization_index": round(polarization_index, 3),
            "normalized_joule_rate": round(joule_rate, 5),
            "overpotential_recovery_ratio": round(overpotential_recovery_ratio, 3),
        }

        extended_vector = np.array([
            extended_dict["tau_fast_s"],
            extended_dict["tau_slow_s"],
            extended_dict["r_ohmic_mohm"],
            extended_dict["r_charge_transfer_mohm"],
            extended_dict["r_diffusion_mohm"],
            extended_dict["polarization_index"],
            extended_dict["normalized_joule_rate"],
            extended_dict["overpotential_recovery_ratio"]
        ], dtype=float)

        return {
            "extended_features": extended_dict,
            "vector": extended_vector,
            "feature_names": [
                "tau_fast_s", "tau_slow_s", "r_ohmic_mohm",
                "r_charge_transfer_mohm", "r_diffusion_mohm",
                "polarization_index", "normalized_joule_rate",
                "overpotential_recovery_ratio"
            ]
        }
