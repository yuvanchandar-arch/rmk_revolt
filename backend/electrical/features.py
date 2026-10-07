"""Stage 1 Electrical Fingerprint Feature Extraction Pipeline.

Extracts the six required electrical features per unit:
1. Open-circuit voltage (OCV)
2. DC internal-resistance proxy (ΔV/ΔI from pulse)
3. Voltage-relaxation slope after pulse
4. Voltage-relaxation curvature after pulse
5. Surface-temperature response
6. Module/cell imbalance or voltage spread
Plus the sensor-quality flag.
"""

from typing import Dict, Any, Union
import numpy as np
from backend.data.loaders import BatteryRecord


class ElectricalFeatureExtractor:
    """Extracts Stage-1 fast electrical fingerprint features from raw battery records."""

    def extract_features(self, record: Union[BatteryRecord, Dict[str, Any]]) -> Dict[str, Any]:
        """Extracts the 6 Stage-1 electrical features plus quality flag from a battery record."""
        if isinstance(record, dict):
            early_feats = record.get("early_features", {})
            time_series = record.get("time_series", {})
            unit_id = record.get("unit_id", "UNKNOWN")
        else:
            early_feats = record.early_features
            time_series = record.time_series
            unit_id = record.unit_id

        # Direct readout from recorded features if available
        ocv = float(early_feats.get("ocv_v", 0.0))
        dcir = float(early_feats.get("dcir_mohm", 0.0))
        rel_slope = float(early_feats.get("relaxation_slope", 0.0))
        rel_curv = float(early_feats.get("relaxation_curvature", 0.0))
        temp_resp = float(early_feats.get("temp_rise_c", 0.0))
        imbalance = float(early_feats.get("cell_imbalance_mv", 0.0))
        quality_flag = int(early_feats.get("sensor_quality_flag", 1))

        # Check raw time series if available to verify or refine
        if time_series and "voltage_v" in time_series and len(time_series["voltage_v"]) > 0:
            voltages = np.array(time_series["voltage_v"])
            currents = np.array(time_series.get("current_a", []))
            times = np.array(time_series.get("time_s", []))
            temps = np.array(time_series.get("temperature_c", []))

            # Quality check on raw arrays
            if np.any(np.isnan(voltages)) or np.any(np.isinf(voltages)) or len(voltages) < 10:
                quality_flag = 0

            # If OCV was 0 or unpopulated, derive from first resting window
            if ocv == 0.0 and len(voltages) > 0 and quality_flag == 1:
                ocv = float(np.mean(voltages[:min(40, len(voltages))]))

            # If DCIR was unpopulated and we have current
            if dcir == 0.0 and len(currents) == len(voltages) and quality_flag == 1:
                # Find max current pulse
                pulse_idx = np.where(np.abs(currents) > 0.5)[0]
                if len(pulse_idx) > 5:
                    v_rest = ocv
                    v_pulse = float(voltages[pulse_idx[2]])
                    i_pulse = float(currents[pulse_idx[2]])
                    if abs(i_pulse) > 1e-3:
                        dcir = float(abs(v_rest - v_pulse) / abs(i_pulse) * 1000.0)

            # Temperature response
            if temp_resp == 0.0 and len(temps) > 0 and quality_flag == 1:
                temp_resp = float(np.max(temps) - np.min(temps))

        feature_dict = {
            "unit_id": unit_id,
            "ocv_v": round(ocv, 4),
            "dcir_mohm": round(dcir, 2),
            "relaxation_slope": round(rel_slope, 5),
            "relaxation_curvature": round(rel_curv, 6),
            "temperature_response_c": round(temp_resp, 2),
            "cell_imbalance_mv": round(imbalance, 2),
            "sensor_quality_flag": quality_flag,
        }

        feature_vector = np.array([
            feature_dict["ocv_v"],
            feature_dict["dcir_mohm"],
            feature_dict["relaxation_slope"],
            feature_dict["relaxation_curvature"],
            feature_dict["temperature_response_c"],
            feature_dict["cell_imbalance_mv"]
        ], dtype=float)

        return {
            "features": feature_dict,
            "vector": feature_vector,
            "feature_names": [
                "ocv_v", "dcir_mohm", "relaxation_slope",
                "relaxation_curvature", "temperature_response_c", "cell_imbalance_mv"
            ]
        }
