"""
Compound base pace.

This module exists because compound pace is NOT identifiable from race data.

Compound choice is nearly collinear with race phase: softs run at the start on a
green track with heavy fuel and dirty air, hards run late on a rubbered-in circuit.
Fitting an intercept per compound -- even with driver fixed effects -- ranks softs
SLOWER than hards at bahrain, spanish and japanese alike. Track evolution and dirty
air are both unmodeled (see README Limitations), and they bias exactly this quantity.

So the offsets below are an ASSUMPTION, not a fit. They are published Pirelli step
deltas. Degradation (a, b in tyre_degradation.py) IS fitted from data, because it is
estimated within a stint where race phase is roughly constant.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db.models import Race, Lap
from app.models.fuel_model import fuel_correction

# Seconds slower than the softest compound, at equal fuel and tyre age.
# Assumption, not a fit -- see module docstring.
COMPOUND_OFFSET_S: dict[str, float] = {
    "SOFT": 0.00,
    "MEDIUM": 0.55,
    "HARD": 1.15,
}

_FASTEST_LAP_PERCENTILE = 5.0  # reference pace = median of the fastest 5% of laps


def compound_offset(compound: str) -> float:
    """Pace penalty in seconds relative to SOFT. Raises on unknown compound."""
    try:
        return COMPOUND_OFFSET_S[compound.upper()]
    except KeyError:
        raise ValueError(f"Unknown compound {compound!r}") from None


def circuit_base_lap_s(circuit_key: str, session) -> float:
    """
    Reference full-fuel pace for a circuit, in seconds.

    Median of the fastest 5% of fuel-corrected valid laps across all cached races.
    A percentile rather than the outright minimum: min() is biased low by sample
    size, which is what corrupted the per-compound base_lap_s in the first place.

    This is a single circuit-level number. Per-compound pace comes from adding
    compound_offset(); it is never fitted.
    """
    races = session.query(Race).filter(Race.circuit_key == circuit_key.lower()).all()
    if not races:
        raise ValueError(f"No cached races for circuit {circuit_key!r}")

    corrected: list[float] = []
    for race in races:
        laps = (
            session.query(Lap)
            .filter(
                Lap.race_id == race.id,
                Lap.is_valid == True,
                Lap.lap_time_s.isnot(None),
            )
            .all()
        )
        # normalise to a full-fuel car: raw + k*L  (prediction is the inverse)
        corrected.extend(l.lap_time_s + fuel_correction(l.lap_number) for l in laps)

    if not corrected:
        raise ValueError(f"No valid laps for circuit {circuit_key!r}")

    arr = np.array(corrected)
    cutoff = np.percentile(arr, _FASTEST_LAP_PERCENTILE)
    return float(np.median(arr[arr <= cutoff]))
