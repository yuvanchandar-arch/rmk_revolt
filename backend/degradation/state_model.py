"""Degradation State Model (Shared by Electrical & Acoustic Modalities).

Defines the single ground-truth degradation generator that provably couples
electrical feature shifts and EMAT physics-layer perturbations.

States:
1. Healthy
2. Mild degradation
3. Moderate degradation
4. Plating-associated degradation
5. Severe degradation
"""

from enum import Enum
from dataclasses import dataclass, asdict
from typing import Dict, Any, Tuple
import numpy as np


class DegradationState(str, Enum):
    HEALTHY = "Healthy"
    MILD = "Mild degradation"
    MODERATE = "Moderate degradation"
    PLATING = "Plating-associated degradation"
    SEVERE = "Severe degradation"


@dataclass(frozen=True)
class StateDefinition:
    state: DegradationState
    capacity_fade_pct_range: Tuple[float, float]
    dcir_mohm_range: Tuple[float, float]
    tof_shift_us_range: Tuple[float, float]
    amp_attenuation_db_range: Tuple[float, float]
    energy_attenuation_db_range: Tuple[float, float]
    plating_thickness_um_range: Tuple[float, float]
    rationale: str


STATE_DEFINITIONS: Dict[DegradationState, StateDefinition] = {
    DegradationState.HEALTHY: StateDefinition(
        state=DegradationState.HEALTHY,
        capacity_fade_pct_range=(0.0, 8.0),
        dcir_mohm_range=(15.0, 22.0),
        tof_shift_us_range=(0.00, 0.25),
        amp_attenuation_db_range=(-1.5, 0.0),
        energy_attenuation_db_range=(-2.0, 0.0),
        plating_thickness_um_range=(0.0, 0.0),
        rationale="Pristine electrode active material and uniform electrolyte wetting; negligible SEI impedance; high acoustic transmission with minimal scattering."
    ),
    DegradationState.MILD: StateDefinition(
        state=DegradationState.MILD,
        capacity_fade_pct_range=(8.0, 16.0),
        dcir_mohm_range=(22.0, 28.0),
        tof_shift_us_range=(0.25, 0.60),
        amp_attenuation_db_range=(-4.0, -1.5),
        energy_attenuation_db_range=(-5.0, -2.0),
        plating_thickness_um_range=(0.0, 0.5),
        rationale="Early SEI formation consuming cyclable lithium; slight rise in charge transfer resistance; minor acoustic boundary mismatch at separator interface."
    ),
    DegradationState.MODERATE: StateDefinition(
        state=DegradationState.MODERATE,
        capacity_fade_pct_range=(16.0, 24.0),
        dcir_mohm_range=(28.0, 38.0),
        tof_shift_us_range=(0.60, 1.10),
        amp_attenuation_db_range=(-7.5, -4.0),
        energy_attenuation_db_range=(-9.0, -5.0),
        plating_thickness_um_range=(0.5, 1.5),
        rationale="Thickening passivation layers and micro-cracking of active cathode particles; increased interfacial resistance; moderate wave dispersion and velocity reduction."
    ),
    DegradationState.PLATING: StateDefinition(
        state=DegradationState.PLATING,
        capacity_fade_pct_range=(24.0, 32.0),
        dcir_mohm_range=(38.0, 52.0),
        tof_shift_us_range=(1.10, 1.80),
        amp_attenuation_db_range=(-12.0, -7.5),
        energy_attenuation_db_range=(-14.0, -9.0),
        plating_thickness_um_range=(2.0, 8.0),
        rationale="Metallic lithium plating deposits at graphite anode boundary, perturbing acoustic boundary conditions and causing pronounced ultrasonic wave delay and interfacial acoustic scattering."
    ),
    DegradationState.SEVERE: StateDefinition(
        state=DegradationState.SEVERE,
        capacity_fade_pct_range=(32.0, 48.0),
        dcir_mohm_range=(52.0, 85.0),
        tof_shift_us_range=(1.80, 2.80),
        amp_attenuation_db_range=(-18.0, -12.0),
        energy_attenuation_db_range=(-22.0, -14.0),
        plating_thickness_um_range=(8.0, 20.0),
        rationale="Extensive active material loss, severe electrolyte dry-out, and heavy dead lithium deposits; dramatic impedance surge and massive acoustic signal damping."
    ),
}


@dataclass
class DegradationParameters:
    state: str
    capacity_fade_pct: float
    dcir_mohm: float
    tof_shift_us: float
    amp_attenuation_db: float
    energy_attenuation_db: float
    plating_thickness_um: float
    seed: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def sample_degradation_parameters(
    state: DegradationState,
    seed: int
) -> DegradationParameters:
    """Sample degradation parameters deterministically within the state's defined ranges."""
    defn = STATE_DEFINITIONS[state]
    rng = np.random.default_rng(seed)

    def _sample_range(r: Tuple[float, float]) -> float:
        low, high = r
        if low == high:
            return low
        val = low + float(rng.uniform(0.0, 1.0)) * (high - low)
        return float(np.clip(val, low, high))

    fade = _sample_range(defn.capacity_fade_pct_range)
    dcir = _sample_range(defn.dcir_mohm_range)
    tof = _sample_range(defn.tof_shift_us_range)
    amp_att = _sample_range(defn.amp_attenuation_db_range)
    eng_att = _sample_range(defn.energy_attenuation_db_range)
    plating = _sample_range(defn.plating_thickness_um_range)

    return DegradationParameters(
        state=state.value,
        capacity_fade_pct=round(fade, 2),
        dcir_mohm=round(dcir, 2),
        tof_shift_us=round(tof, 3),
        amp_attenuation_db=round(amp_att, 2),
        energy_attenuation_db=round(eng_att, 2),
        plating_thickness_um=round(plating, 2),
        seed=seed
    )
