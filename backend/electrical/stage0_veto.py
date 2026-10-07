"""Stage 0 Safety and Identity Veto Module.

Provides early non-negotiable quarantine veto before statistical screening.
Any battery failing physical plausibility, sensor integrity, or thermal/voltage safety
is immediately quarantined without consuming qualification time.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Union
from backend.data.loaders import BatteryRecord
from backend.electrical.features import ElectricalFeatureExtractor


@dataclass
class Stage0VetoResult:
    unit_id: str
    passed: bool
    veto_triggered: bool
    reasons: List[str]
    disposition: str  # "proceed_to_stage1" or "quarantine"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Stage0VetoEngine:
    def __init__(
        self,
        min_ocv_v: float = 2.50,
        max_ocv_v: float = 4.35,
        max_dcir_mohm: float = 400.0,
        max_temp_rise_c: float = 35.0,
        max_imbalance_mv: float = 120.0
    ):
        self.min_ocv_v = min_ocv_v
        self.max_ocv_v = max_ocv_v
        self.max_dcir_mohm = max_dcir_mohm
        self.max_temp_rise_c = max_temp_rise_c
        self.max_imbalance_mv = max_imbalance_mv
        self.extractor = ElectricalFeatureExtractor()

    def evaluate(self, record: Union[BatteryRecord, Dict[str, Any]]) -> Stage0VetoResult:
        """Evaluates a unit against Stage 0 physical and sensor veto criteria."""
        if isinstance(record, dict):
            unit_id = record.get("unit_id", "UNKNOWN")
            damage = record.get("damage_category", "none")
        else:
            unit_id = record.unit_id
            damage = record.damage_category

        feat_res = self.extractor.extract_features(record)
        feats = feat_res["features"]

        reasons = []

        # 1. Sensor quality check
        if feats["sensor_quality_flag"] == 0:
            reasons.append("Sensor quality check failed: missing, corrupt, or dropped sensor telemetry")

        # 2. OCV physical electrochemical window
        ocv = feats["ocv_v"]
        if ocv < self.min_ocv_v:
            reasons.append(f"Severe under-voltage: OCV {ocv:.3f}V below safety cutoff {self.min_ocv_v}V (copper dissolution risk)")
        elif ocv > self.max_ocv_v:
            reasons.append(f"Over-voltage anomaly: OCV {ocv:.3f}V exceeds electrochemical stability limit {self.max_ocv_v}V")

        # 3. DCIR plausibility
        dcir = feats["dcir_mohm"]
        if dcir <= 0:
            reasons.append(f"Non-physical internal resistance: DCIR {dcir:.2f} mΩ is non-positive")
        elif dcir > self.max_dcir_mohm:
            reasons.append(f"Excessive internal resistance: DCIR {dcir:.2f} mΩ exceeds safety limit {self.max_dcir_mohm} mΩ")

        # 4. Temperature rise / thermal safety
        temp_rise = feats["temperature_response_c"]
        if temp_rise > self.max_temp_rise_c:
            reasons.append(f"Thermal anomaly: Pulse temperature rise {temp_rise:.2f}°C exceeds threshold {self.max_temp_rise_c}°C")

        # 5. Cell imbalance
        imbalance = feats["cell_imbalance_mv"]
        if imbalance > self.max_imbalance_mv:
            reasons.append(f"Critical cell imbalance: {imbalance:.2f} mV exceeds veto ceiling {self.max_imbalance_mv} mV")

        # 6. Physical structural damage
        if damage in ["severe_dent", "casing_rupture", "electrolyte_leak"]:
            reasons.append(f"Physical damage veto: cell casing flagged with {damage}")

        veto_triggered = len(reasons) > 0
        passed = not veto_triggered
        disposition = "proceed_to_stage1" if passed else "quarantine"

        return Stage0VetoResult(
            unit_id=unit_id,
            passed=passed,
            veto_triggered=veto_triggered,
            reasons=reasons,
            disposition=disposition
        )
