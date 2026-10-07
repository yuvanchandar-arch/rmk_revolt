"""Lot construction simulator for LOTUS-EMAT.

Constructs traceable battery lots across nominal and shifted scenarios:
1. Same-source lots (nominal case, e.g. 200-unit NMC fleet)
2. Mixed-age lots (wide cycle count & degradation variance)
3. Cross-dataset lots (distribution shift across NASA, CALCE, Oxford, PulseBat)
4. Mixed-chemistry/anomalous lots (mixed chemistries & corrupted/outlier units for abstention/splitting)
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import numpy as np

from backend.data.loaders import (
    BatteryRecord,
    load_nasa_pcoe,
    load_calce,
    load_oxford,
    load_pulsebat,
    _generate_pulse_timeseries
)


@dataclass
class Lot:
    lot_id: str
    lot_type: str
    provenance: Dict[str, Any]
    units: List[BatteryRecord]

    @property
    def size(self) -> int:
        return len(self.units)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lot_id": self.lot_id,
            "lot_type": self.lot_type,
            "provenance": self.provenance,
            "size": self.size,
            "units": [u.to_dict() for u in self.units]
        }


class LotSimulator:
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir
        self._nasa = None
        self._calce = None
        self._oxford = None
        self._pulsebat = None

    @property
    def nasa_records(self) -> List[BatteryRecord]:
        if self._nasa is None:
            self._nasa = load_nasa_pcoe(self.data_dir)
        return self._nasa

    @property
    def calce_records(self) -> List[BatteryRecord]:
        if self._calce is None:
            self._calce = load_calce(self.data_dir)
        return self._calce

    @property
    def oxford_records(self) -> List[BatteryRecord]:
        if self._oxford is None:
            self._oxford = load_oxford(self.data_dir)
        return self._oxford

    @property
    def pulsebat_records(self) -> List[BatteryRecord]:
        if self._pulsebat is None:
            self._pulsebat = load_pulsebat(self.data_dir)
        return self._pulsebat

    def create_same_source_lot(
        self,
        lot_id: str = "LOT-NOMINAL-NMC-200",
        size: int = 200,
        seed: int = 42
    ) -> Lot:
        """Constructs a nominal same-source lot (e.g. worked example from Section 6:
        Single fleet, NMC, same platform, similar storage history).
        """
        rng = np.random.default_rng(seed)
        units: List[BatteryRecord] = []
        
        # Nominal parameters
        chemistry = "NMC"
        fmt = "pouch"
        platform = "FleetPlatform-Pouch-Gen2"
        fleet = "MetroEV-Delivery-FleetA"
        storage = "controlled_ambient"
        damage = "none"
        nom_cap = 2.5

        for i in range(size):
            unit_seed = int(seed * 1000 + i)
            unit_rng = np.random.default_rng(unit_seed)
            
            # Realistic degradation distribution for 2nd-life retired fleet:
            # Mean capacity fade ~ 19%, standard deviation ~ 4%
            fade = float(np.clip(unit_rng.normal(19.0, 4.0), 8.0, 34.0))
            meas_cap = nom_cap * (1.0 - fade / 100.0)
            cycles = int(unit_rng.integers(600, 950))
            soh_frac = meas_cap / nom_cap

            ts, feats = _generate_pulse_timeseries(
                nominal_cap=nom_cap,
                soh_fraction=soh_frac,
                temp_ambient=24.0,
                seed=unit_seed,
                dcir_mult=1.0
            )

            record = BatteryRecord(
                unit_id=f"{lot_id}-U{i+1:03d}",
                dataset_source="PulseBat",
                chemistry=chemistry,
                format=fmt,
                platform=platform,
                fleet_source=fleet,
                usage_history="delivery",
                nominal_capacity_ah=nom_cap,
                measured_capacity_ah=round(meas_cap, 3),
                capacity_fade_pct=round(fade, 2),
                cycle_count=cycles,
                storage_condition_class=storage,
                damage_category=damage,
                time_series=ts,
                early_features=feats
            )
            units.append(record)

        provenance = {
            "chemistry": chemistry,
            "format": fmt,
            "platform": platform,
            "fleet_source": fleet,
            "storage_condition_class": storage,
            "damage_category": damage,
            "target_size": size,
            "seed": seed
        }

        return Lot(
            lot_id=lot_id,
            lot_type="same_source",
            provenance=provenance,
            units=units
        )

    def create_mixed_age_lot(
        self,
        lot_id: str = "LOT-MIXEDAGE-200",
        size: int = 200,
        seed: int = 42
    ) -> Lot:
        """Constructs a lot with the same chemistry/platform but widely varying cycle counts and ages."""
        rng = np.random.default_rng(seed)
        units: List[BatteryRecord] = []

        chemistry = "NMC"
        fmt = "cylindrical_18650"
        platform = "FleetPlatform-18650"
        fleet = "MixedCommuter-Fleet"
        storage = "controlled_ambient"
        damage = "none"
        nom_cap = 3.0

        for i in range(size):
            unit_seed = int(seed * 2000 + i)
            unit_rng = np.random.default_rng(unit_seed)

            # Broad bimodal or uniform age spectrum from near-new (50 cycles) to highly degraded (1800 cycles)
            cycles = int(unit_rng.integers(100, 1800))
            fade = float(np.clip(5.0 + (cycles / 1800.0) * 32.0 + unit_rng.normal(0, 3.0), 5.0, 42.0))
            meas_cap = nom_cap * (1.0 - fade / 100.0)
            soh_frac = meas_cap / nom_cap

            ts, feats = _generate_pulse_timeseries(
                nominal_cap=nom_cap,
                soh_fraction=soh_frac,
                temp_ambient=23.0,
                seed=unit_seed,
                dcir_mult=1.0 + (cycles / 2000.0)
            )

            record = BatteryRecord(
                unit_id=f"{lot_id}-U{i+1:03d}",
                dataset_source="PulseBat",
                chemistry=chemistry,
                format=fmt,
                platform=platform,
                fleet_source=fleet,
                usage_history="commuter",
                nominal_capacity_ah=nom_cap,
                measured_capacity_ah=round(meas_cap, 3),
                capacity_fade_pct=round(fade, 2),
                cycle_count=cycles,
                storage_condition_class=storage,
                damage_category=damage,
                time_series=ts,
                early_features=feats
            )
            units.append(record)

        provenance = {
            "chemistry": chemistry,
            "format": fmt,
            "platform": platform,
            "fleet_source": fleet,
            "storage_condition_class": storage,
            "damage_category": damage,
            "target_size": size,
            "seed": seed
        }

        return Lot(
            lot_id=lot_id,
            lot_type="mixed_age",
            provenance=provenance,
            units=units
        )

    def create_cross_dataset_lot(
        self,
        lot_id: str = "LOT-CROSSDATASET-200",
        size: int = 200,
        seed: int = 42
    ) -> Lot:
        """Constructs a lot spanning multiple public datasets (NASA, CALCE, Oxford, PulseBat)."""
        rng = np.random.default_rng(seed)
        units: List[BatteryRecord] = []

        pool = []
        pool.extend(self.nasa_records)
        pool.extend(self.calce_records)
        pool.extend(self.oxford_records)
        # Add subset of PulseBat to fill
        pool.extend(self.pulsebat_records)

        indices = rng.choice(len(pool), size=size, replace=True)
        for i, idx in enumerate(indices):
            base_rec = pool[idx]
            # Copy and give unique unit_id
            rec = BatteryRecord(
                unit_id=f"{lot_id}-U{i+1:03d}-{base_rec.unit_id}",
                dataset_source=base_rec.dataset_source,
                chemistry=base_rec.chemistry,
                format=base_rec.format,
                platform=base_rec.platform,
                fleet_source=base_rec.fleet_source,
                usage_history=base_rec.usage_history,
                nominal_capacity_ah=base_rec.nominal_capacity_ah,
                measured_capacity_ah=base_rec.measured_capacity_ah,
                capacity_fade_pct=base_rec.capacity_fade_pct,
                cycle_count=base_rec.cycle_count,
                storage_condition_class=base_rec.storage_condition_class,
                damage_category=base_rec.damage_category,
                time_series=base_rec.time_series,
                early_features=base_rec.early_features
            )
            units.append(rec)

        provenance = {
            "chemistry": "mixed (cross-dataset)",
            "format": "mixed",
            "platform": "cross-dataset",
            "fleet_source": "multi-lab",
            "storage_condition_class": "mixed",
            "damage_category": "mixed",
            "target_size": size,
            "seed": seed
        }

        return Lot(
            lot_id=lot_id,
            lot_type="cross_dataset",
            provenance=provenance,
            units=units
        )

    def create_mixed_chemistry_anomalous_lot(
        self,
        lot_id: str = "LOT-ANOMALOUS-200",
        size: int = 200,
        seed: int = 42
    ) -> Lot:
        """Constructs a lot containing mixed chemistries (e.g. NMC + LFP) and anomalous units
        specifically designed for testing lot-splitting, abstention, and veto.
        """
        rng = np.random.default_rng(seed)
        units: List[BatteryRecord] = []

        # 70% NMC units, 30% LFP units
        n_nmc = int(size * 0.7)
        n_lfp = size - n_nmc

        for i in range(size):
            unit_seed = int(seed * 3000 + i)
            unit_rng = np.random.default_rng(unit_seed)

            is_lfp = (i >= n_nmc)
            chem = "LFP" if is_lfp else "NMC"
            fmt = "prismatic" if is_lfp else "pouch"
            platform = "Platform-LFP-Prismatic" if is_lfp else "Platform-NMC-Pouch"
            fleet = "Fleet-Transit-Mixed"
            storage = "elevated_temp" if (i % 4 == 0) else "controlled_ambient"
            damage = "minor_casing_scratch" if (i % 12 == 0) else "none"
            nom_cap = 40.0 if is_lfp else 2.5

            fade = float(np.clip(unit_rng.normal(21.0, 5.0), 8.0, 38.0))
            meas_cap = nom_cap * (1.0 - fade / 100.0)
            cycles = int(unit_rng.integers(400, 1200))
            soh_frac = meas_cap / nom_cap

            # Corrupt sensor for unit index 42 deliberately
            corrupt = (i == 42)

            ts, feats = _generate_pulse_timeseries(
                nominal_cap=nom_cap,
                soh_fraction=soh_frac,
                temp_ambient=25.0,
                seed=unit_seed,
                corrupt_sensor=corrupt
            )

            record = BatteryRecord(
                unit_id=f"{lot_id}-U{i+1:03d}",
                dataset_source="PulseBat",
                chemistry=chem,
                format=fmt,
                platform=platform,
                fleet_source=fleet,
                usage_history="taxi" if is_lfp else "commuter",
                nominal_capacity_ah=nom_cap,
                measured_capacity_ah=round(meas_cap, 3),
                capacity_fade_pct=round(fade, 2),
                cycle_count=cycles,
                storage_condition_class=storage,
                damage_category=damage,
                time_series=ts,
                early_features=feats
            )
            units.append(record)

        provenance = {
            "chemistry": "mixed (NMC + LFP)",
            "format": "mixed (pouch + prismatic)",
            "platform": "mixed",
            "fleet_source": "Fleet-Transit-Mixed",
            "storage_condition_class": "mixed",
            "damage_category": "mixed",
            "target_size": size,
            "seed": seed
        }

        return Lot(
            lot_id=lot_id,
            lot_type="mixed_chemistry_anomalous",
            provenance=provenance,
            units=units
        )
