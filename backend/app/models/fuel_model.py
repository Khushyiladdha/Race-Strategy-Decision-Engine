# Seconds per lap the car gains as fuel burns off.
# ~1.5 kg/lap x ~0.02 s/kg. Shifts absolute predicted time but cancels out of the
# strategy ranking (every strategy covers the same laps), so it is not urgent to
# refine. Stage 4's absolute-time comparison is what can actually identify it.
FUEL_BURN_S_PER_LAP = 0.03


def fuel_correction(lap_number: int, k: float = FUEL_BURN_S_PER_LAP) -> float:
    """
    Seconds gained on this lap relative to lap 0 due to fuel burn-off.
    Positive = car is faster on this lap than at race start.
    k=0.03 s/lap ~ 1.5 kg/lap × 0.02 s/kg, a standard F1 approximation.
    """
    if lap_number < 0:
        raise ValueError(f"lap_number must be >= 0, got {lap_number}")
    return k * lap_number
