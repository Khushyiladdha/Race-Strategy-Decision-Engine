import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db.models import Race, Lap

_GLOBAL_DEFAULT_SC_PROB = 0.10  # fallback: ~10% of laps behind SC historically
_MIN_RACES_FOR_ESTIMATE = 2     # need at least 2 cached races to trust the estimate
_SC_LAP_TIME_MULTIPLIER = 1.30  # a lap ≥ 130% of that driver's median flags as SC/VSC

# Published historical SC rates per circuit. ASSUMPTION, not a fit.
# Source: approximate historical SC/VSC deployment frequency (FIA race reports, 2018-2023).
# expected_sc_rate() prefers the empirical estimator once >= _MIN_RACES_FOR_ESTIMATE
# races are cached; these constants are the honest fallback when the DB is too thin.
# Stage 2 established this pattern for compound_offset and pit_loss; we follow it here.
SC_RATE_PER_LAP: dict[str, float] = {
    "singapore": 0.28,   # street circuit, highest incident frequency on calendar
    "australian": 0.20,  # 2023 had 3 red flags; historically disrupted
    "japanese": 0.12,    # moderate SC history at Suzuka
    "austrian": 0.10,    # Red Bull Ring, moderate
    "bahrain": 0.08,     # relatively clean desert circuit
    "spanish": 0.06,     # Barcelona, historically low incident rate
}


def sc_probability_per_lap(circuit_key: str, session) -> float:
    """
    Estimate P(any given lap is under SC/VSC) for this circuit from cached race data.

    Method: for each driver in each cached race at this circuit, flag laps where
    lap_time_s >= 130% of that driver's median as safety-car-affected.
    Returns fraction of total valid laps that are flagged.
    Falls back to _GLOBAL_DEFAULT_SC_PROB if fewer than _MIN_RACES_FOR_ESTIMATE races.
    """
    races = (
        session.query(Race)
        .filter(Race.circuit_key == circuit_key.lower())
        .all()
    )

    if len(races) < _MIN_RACES_FOR_ESTIMATE:
        return _GLOBAL_DEFAULT_SC_PROB

    total_laps = 0
    sc_laps = 0

    for race in races:
        laps = (
            session.query(Lap)
            .filter(
                Lap.race_id == race.id,
                Lap.lap_time_s.isnot(None),
                Lap.is_valid == True,
            )
            .all()
        )

        # group by driver
        by_driver: dict[str, list[float]] = {}
        for lap in laps:
            by_driver.setdefault(lap.driver, []).append(lap.lap_time_s)

        for driver, times in by_driver.items():
            if len(times) < 3:
                continue
            median = float(np.median(times))
            threshold = median * _SC_LAP_TIME_MULTIPLIER
            for t in times:
                total_laps += 1
                if t >= threshold:
                    sc_laps += 1

    if total_laps == 0:
        return _GLOBAL_DEFAULT_SC_PROB

    return sc_laps / total_laps


def expected_sc_rate(circuit_key: str, session) -> float:
    """
    Best available SC-per-lap rate for this circuit.

    Priority:
    1. Empirical estimate from cached DB races (if >= _MIN_RACES_FOR_ESTIMATE)
    2. Published constant from SC_RATE_PER_LAP assumption table
    3. Global default (0.10)

    Stage 3 calls this instead of sc_probability_per_lap directly so that every
    circuit gets a meaningful rate even when the DB has only one race cached.
    """
    key = circuit_key.lower()
    n_races = (
        session.query(Race).filter(Race.circuit_key == key).count()
    )
    if n_races >= _MIN_RACES_FOR_ESTIMATE:
        return sc_probability_per_lap(circuit_key, session)
    rate = SC_RATE_PER_LAP.get(key)
    return rate if rate is not None else _GLOBAL_DEFAULT_SC_PROB
