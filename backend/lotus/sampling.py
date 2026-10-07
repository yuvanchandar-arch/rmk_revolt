"""Random Reference Sampling and Finite-Sample Size Determination.

Implements the zero-violation reference sample size formula from Section 5.6:
m ≈ ceil( ln(δ) / ln(1 − ε) )

Reference table at confidence 1 - δ = 90% (δ = 0.10):
- ε = 10% -> m ≈ 22
- ε = 5%  -> m ≈ 45
- ε = 2%  -> m ≈ 114
- ε = 1%  -> m ≈ 230
"""

import math
from typing import List, Tuple, Optional, Union
import numpy as np
from backend.data.loaders import BatteryRecord


# Precomputed reference sample size verification table at delta = 0.10 (90% confidence)
REFERENCE_SAMPLE_SIZE_TABLE = {
    0.10: 22,
    0.05: 45,
    0.02: 114,
    0.01: 230
}


def compute_reference_sample_size(epsilon: float, delta: float = 0.10) -> int:
    """Computes reference sample size m based on the zero-violation risk bound:
    
    m = ceil( ln(delta) / ln(1 - epsilon) )
    """
    if epsilon <= 0.0 or epsilon >= 1.0:
        raise ValueError(f"Epsilon must be in (0, 1), got {epsilon}")
    if delta <= 0.0 or delta >= 1.0:
        raise ValueError(f"Delta must be in (0, 1), got {delta}")

    m_float = math.log(delta) / math.log(1.0 - epsilon)
    return int(math.ceil(m_float))


def draw_reference_sample(
    units: List[Union[BatteryRecord, dict]],
    m: Optional[int] = None,
    epsilon: float = 0.05,
    delta: float = 0.10,
    seed: int = 42
) -> Tuple[List[Any], List[Any]]:
    """Draws m units uniformly at random from the lot for full Stage-3 qualification.
    
    Returns:
        reference_units (List): m units for Stage-3 testing
        remaining_units (List): N - m units for fast sequential screening
    """
    n_total = len(units)
    if m is None:
        m = compute_reference_sample_size(epsilon=epsilon, delta=delta)

    # Cannot draw more reference units than available in the lot
    m_clamped = min(m, n_total)
    
    rng = np.random.default_rng(seed)
    shuffled_indices = rng.permutation(n_total)

    ref_indices = set(shuffled_indices[:m_clamped])
    
    ref_units = [units[i] for i in range(n_total) if i in ref_indices]
    remaining_units = [units[i] for i in range(n_total) if i not in ref_indices]

    return ref_units, remaining_units
