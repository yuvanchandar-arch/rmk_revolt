"""Lot Definition Enforcement and Automatic Sub-Lot Splitting.

As mandated by Section 5.6 of 01_project_details.md:
A lot is a traceable group sharing:
- chemistry
- format
- platform
- fleet/source
- storage condition class
- damage category

If an incoming batch mixes these attributes, the engine must refuse to calibrate
it as one monolithic lot and split it into sub-lots automatically.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple, Union
from collections import defaultdict

from backend.data.loaders import BatteryRecord


@dataclass(frozen=True)
class LotProvenanceKey:
    chemistry: str
    format: str
    platform: str
    fleet_source: str
    storage_condition_class: str
    damage_category: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SubLot:
    sublot_id: str
    parent_lot_id: str
    provenance: Dict[str, Any]
    units: List[BatteryRecord]

    @property
    def size(self) -> int:
        return len(self.units)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sublot_id": self.sublot_id,
            "parent_lot_id": self.parent_lot_id,
            "provenance": self.provenance,
            "size": self.size,
            "unit_ids": [u.unit_id for u in self.units]
        }


class LotIntegrityEnforcer:
    """Enforces lot homogeneity and performs automatic sub-lot splitting."""

    def extract_key(self, record: Union[BatteryRecord, Dict[str, Any]]) -> LotProvenanceKey:
        if isinstance(record, BatteryRecord):
            return LotProvenanceKey(
                chemistry=record.chemistry,
                format=record.format,
                platform=record.platform,
                fleet_source=record.fleet_source,
                storage_condition_class=record.storage_condition_class,
                damage_category=record.damage_category
            )
        else:
            return LotProvenanceKey(
                chemistry=record.get("chemistry", "UNKNOWN"),
                format=record.get("format", "UNKNOWN"),
                platform=record.get("platform", "UNKNOWN"),
                fleet_source=record.get("fleet_source", "UNKNOWN"),
                storage_condition_class=record.get("storage_condition_class", "UNKNOWN"),
                damage_category=record.get("damage_category", "none")
            )

    def audit_and_split(
        self,
        batch_id: str,
        units: List[Union[BatteryRecord, Dict[str, Any]]]
    ) -> Tuple[bool, List[SubLot], Dict[str, Any]]:
        """Audits a batch for provenance homogeneity.
        
        Returns:
            is_homogeneous (bool): True if single traceable lot; False if split.
            sub_lots (List[SubLot]): List of sub-lots (length 1 if homogeneous, >1 if split).
            audit_report (dict): Traceability statistics and audit details.
        """
        groups: Dict[LotProvenanceKey, List[BatteryRecord]] = defaultdict(list)
        for u in units:
            key = self.extract_key(u)
            groups[key].append(u)

        is_homogeneous = len(groups) == 1
        sub_lots: List[SubLot] = []

        sublot_labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for idx, (key, grp_units) in enumerate(groups.items()):
            label = sublot_labels[idx % len(sublot_labels)] if not is_homogeneous else "0"
            sublot_id = f"{batch_id}-SUBLOT-{label}" if not is_homogeneous else batch_id
            sub_lot = SubLot(
                sublot_id=sublot_id,
                parent_lot_id=batch_id,
                provenance=key.to_dict(),
                units=grp_units
            )
            sub_lots.append(sub_lot)

        # Audit breakdown
        audit_report = {
            "batch_id": batch_id,
            "total_units": len(units),
            "is_homogeneous": is_homogeneous,
            "distinct_groups_count": len(groups),
            "action_taken": "calibrated_as_single_lot" if is_homogeneous else "refused_single_lot_split_into_sublots",
            "sublot_breakdown": [
                {
                    "sublot_id": s.sublot_id,
                    "size": s.size,
                    "chemistry": s.provenance["chemistry"],
                    "format": s.provenance["format"],
                    "platform": s.provenance["platform"],
                    "fleet_source": s.provenance["fleet_source"],
                }
                for s in sub_lots
            ]
        }

        return is_homogeneous, sub_lots, audit_report
