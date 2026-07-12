"""
Score and rank strategies by predicted total race time.

Sign convention (this has bitten us once already):
    fitting     observed -> model:   corrected = raw + k*L
    prediction  model -> observed:   raw       = model - k*L
They are inverses. fuel_time_s below is therefore NEGATIVE -- time gained.
"""
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.engine.strategy_generator import Strategy
from app.models.compound_pace import circuit_base_lap_s, compound_offset
from app.models.fuel_model import FUEL_BURN_S_PER_LAP
from app.models.pit_loss import pit_loss
from app.models.tyre_degradation import load_params


@dataclass(frozen=True)
class RaceContext:
    """
    Per-circuit lookups resolved once. 45k strategies x 3 stints must never
    hit the database or reparse JSON.
    """
    circuit_key: str
    total_laps: int
    base_lap_s: float
    pit_loss_s: float
    fuel_k: float
    deg: dict[str, tuple[float, float]]   # compound -> (a, b)
    max_observed: dict[str, int]          # compound -> max_stint_lap_observed


def build_context(
    circuit_key: str,
    total_laps: int,
    session,
    *,
    fuel_k: float = FUEL_BURN_S_PER_LAP,
) -> RaceContext:
    from app.models.tyre_degradation import available_compounds

    deg: dict[str, tuple[float, float]] = {}
    max_observed: dict[str, int] = {}
    for c in available_compounds(circuit_key):
        p = load_params(circuit_key, c)
        deg[c] = (p["a"], p["b"])
        max_observed[c] = p["max_stint_lap_observed"]

    return RaceContext(
        circuit_key=circuit_key,
        total_laps=total_laps,
        base_lap_s=circuit_base_lap_s(circuit_key, session),
        pit_loss_s=pit_loss(circuit_key),
        fuel_k=fuel_k,
        deg=deg,
        max_observed=max_observed,
    )


@dataclass(frozen=True)
class EvaluatedStrategy:
    strategy: Strategy
    total_time_s: float
    # additive breakdown -- these five sum to total_time_s
    base_time_s: float
    compound_offset_time_s: float
    degradation_time_s: float
    fuel_time_s: float            # negative: fuel burn-off makes the car faster
    pit_time_s: float
    extrapolation_laps: int       # laps beyond max_stint_lap_observed; Stage 3 uses this


def _deg_sum(n: int, a: float, b: float) -> float:
    """Sum of a*i + b*i^2 for i in 1..n, in closed form."""
    return a * n * (n + 1) / 2 + b * n * (n + 1) * (2 * n + 1) / 6


def _fuel_sum(start_lap: int, end_lap: int, k: float) -> float:
    """Sum of k*L for L in start_lap..end_lap, in closed form."""
    s, e = start_lap, end_lap
    return k * (e * (e + 1) - s * (s - 1)) / 2


def evaluate(strategy: Strategy, ctx: RaceContext) -> EvaluatedStrategy:
    compound_offset_time = 0.0
    degradation_time = 0.0
    fuel_time = 0.0
    extrapolation = 0

    for stint in strategy.stints:
        a, b = ctx.deg[stint.compound]
        n = stint.length

        compound_offset_time += compound_offset(stint.compound) * n
        degradation_time += _deg_sum(n, a, b)
        # subtract: projecting the full-fuel model back onto real race laps
        fuel_time -= _fuel_sum(stint.start_lap, stint.end_lap, ctx.fuel_k)

        beyond = n - ctx.max_observed[stint.compound]
        if beyond > 0:
            extrapolation += beyond

    base_time = ctx.base_lap_s * ctx.total_laps
    pit_time = strategy.n_stops * ctx.pit_loss_s
    total = base_time + compound_offset_time + degradation_time + fuel_time + pit_time

    return EvaluatedStrategy(
        strategy=strategy,
        total_time_s=total,
        base_time_s=base_time,
        compound_offset_time_s=compound_offset_time,
        degradation_time_s=degradation_time,
        fuel_time_s=fuel_time,
        pit_time_s=pit_time,
        extrapolation_laps=extrapolation,
    )


def rank_strategies(strategies: list[Strategy], ctx: RaceContext) -> list[EvaluatedStrategy]:
    """Ascending by predicted total time. Ties broken by key for stable ordering."""
    evaluated = [evaluate(s, ctx) for s in strategies]
    evaluated.sort(key=lambda e: (e.total_time_s, e.strategy.key))
    return evaluated
