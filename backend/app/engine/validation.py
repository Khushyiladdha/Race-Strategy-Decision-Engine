"""
Stage 4 — historical validation.

For each cached race, run the full engine on the real conditions and compare its top
recommendation to what the winner actually did. The point is NOT that the engine should
match reality — it optimizes free-air pace and ignores track position, traffic and undercut
dynamics. The disagreements, and their explanations, are the deliverable.

Validation axes:
  1. Stop count      — did the engine pick the right number of stops?
  2. Pit laps (MAE)  — how far off are the stop laps, when counts match?
  3. Compound match  — same compound sequence?
  4. Timing model    — predicted total vs a free-air reconstruction of the winner's time.
                       Independent of the strategy choice; validates the pace/deg model itself.

Ground-truth notes established by probing the cache:
  - PitStop double-counts (in-lap + out-lap): a real 2-stop reads [14,15,36,37]. So actual
    pit laps come from Lap stint boundaries, with de-duplicated PitStop as a cross-check.
  - Finishing positions are not stored, so winner IDENTITY is a documented constant
    (RACE_ACTUALS) sourced from official 2023 results — same honesty pattern as pit_loss /
    compound_offset / SC_RATE_PER_LAP. Winner laps/compounds are DB-derived, not typed.
"""
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db.models import Lap, Race
from app.engine.evaluator import build_context, rank_strategies
from app.engine.monte_carlo import (
    MonteCarloConfig,
    StrategyDistribution,
    run_monte_carlo,
    robustness_analysis,
    sample_sc_scenarios,
)
from app.engine.strategy_generator import can_generate, generate_strategies
from app.models.pit_loss import pit_loss
from app.models.safety_car import expected_sc_rate
from app.models.tyre_degradation import available_compounds

# Documented official 2023 race winners. ASSUMPTION (identity only) — laps are DB-derived.
# Australian is listed for completeness but the engine cannot generate there (Stage 2 gate).
RACE_ACTUALS: dict[str, dict] = {
    "bahrain":    {"winner": "VER"},
    "spanish":    {"winner": "VER"},
    "austrian":   {"winner": "VER"},
    "japanese":   {"winner": "VER"},
    "singapore":  {"winner": "SAI"},   # the one race VER didn't win in 2023
    "australian": {"winner": "VER"},
}

_SC_LAP_TIME_MULTIPLIER = 1.30   # a lap >= 130% of that driver's median flags as SC-affected
_SC_FIELD_FRACTION = 0.50        # a lap is an SC lap if >= this fraction of the field is slow
_MIN_DRIVERS_FOR_SC_LAP = 5      # need a quorum before calling a lap an SC lap
_MIN_REAL_STINT_LAPS = 3         # stints shorter than this are red-flag/in-out artifacts,
                                 # not strategic stints (e.g. 2023 Austria's phantom lap-2 "stop")


@dataclass(frozen=True)
class ActualStrategy:
    driver: str
    stints: tuple[tuple[str, int], ...]   # (compound, length) in race order
    pit_laps: tuple[int, ...]
    n_stops: int

    @property
    def compounds(self) -> tuple[str, ...]:
        return tuple(c for c, _ in self.stints)


@dataclass(frozen=True)
class TimingAxis:
    predicted_total_s: float
    actual_total_est_s: float     # free-air reconstruction (green median x N + pit loss)
    time_error_s: float           # predicted - actual (positive: engine slower than reality)
    green_lap_median_s: float
    lap_coverage: float           # fraction of race laps with a usable green time


@dataclass(frozen=True)
class RaceValidation:
    circuit_key: str
    total_laps: int
    predicted: StrategyDistribution       # headline: deterministic top-1, MC-annotated
    robust_pick_key: str                  # Stage 3 top-1 (may differ from headline)
    actual: ActualStrategy
    field_median_first_stop: float
    stop_count_match: bool
    pit_lap_mae: float | None             # None when stop counts differ
    first_stop_abs_error: int
    compound_match: str                   # "exact" | "partial" | "mismatch"
    timing: TimingAxis
    flags: tuple[str, ...]
    candidate_explanation: str


def _race_for(circuit_key: str, session) -> Race | None:
    return session.query(Race).filter(Race.circuit_key == circuit_key.lower()).first()


def total_laps_for(circuit_key: str, session) -> int:
    """Race distance = max lap number across the field (the winner runs full distance)."""
    race = _race_for(circuit_key, session)
    if race is None:
        raise ValueError(f"no cached race for {circuit_key}")
    m = (
        session.query(Lap.lap_number)
        .filter(Lap.race_id == race.id)
        .order_by(Lap.lap_number.desc())
        .first()
    )
    if m is None:
        raise ValueError(f"{circuit_key}: no laps cached")
    return int(m[0])


def dedup_pit_laps(raw: list[int]) -> list[int]:
    """
    Collapse the in-lap/out-lap double-count in PitStop: consecutive lap numbers are one
    stop. [14, 15, 36, 37] -> [14, 36]. Keeps the earlier lap of each consecutive run.
    """
    out: list[int] = []
    prev: int | None = None
    for lap in sorted(raw):
        if prev is not None and lap - prev <= 1:   # part of the current consecutive run
            prev = lap
            continue
        out.append(lap)
        prev = lap
    return out


def extract_actual_strategy(circuit_key: str, driver: str, session) -> ActualStrategy | None:
    """
    Reconstruct a driver's real strategy from Lap stint boundaries.

    Groups the driver's laps by stint_number; each stint contributes (compound, length),
    and pit laps are the last lap of every stint except the final one. Returns None if the
    driver has no usable stint data (e.g. absent from this race).
    """
    race = _race_for(circuit_key, session)
    if race is None:
        return None

    laps = (
        session.query(Lap)
        .filter(Lap.race_id == race.id, Lap.driver == driver)
        .order_by(Lap.lap_number)
        .all()
    )
    if not laps:
        return None

    # group by stint, remembering compound (mode of non-null) and last lap
    stint_laps: dict[int, list[Lap]] = {}
    for lap in laps:
        if lap.stint_number is None:
            continue
        stint_laps.setdefault(lap.stint_number, []).append(lap)

    if not stint_laps:
        return None

    stints: list[tuple[str, int]] = []
    stint_ends: list[int] = []
    for stint_no in sorted(stint_laps):
        group = stint_laps[stint_no]
        compounds = [g.compound for g in group if g.compound]
        if not compounds:
            continue
        length = len(group)
        if length < _MIN_REAL_STINT_LAPS:   # red-flag / in-out lap artifact, not a real stint
            continue
        compound = statistics.mode(compounds)
        stints.append((compound, length))
        stint_ends.append(max(g.lap_number for g in group))

    if len(stints) < 1:
        return None

    pit_laps = tuple(stint_ends[:-1])   # every stint end but the last
    return ActualStrategy(
        driver=driver,
        stints=tuple(stints),
        pit_laps=pit_laps,
        n_stops=len(stints) - 1,
    )


def detect_sc_laps(circuit_key: str, session) -> set[int]:
    """
    Lap numbers where the field was under safety car, inferred from pace.

    A lap is flagged when at least _SC_FIELD_FRACTION of the drivers present on that lap
    ran >= 130% of their own median — i.e. the whole field slowed together, which is the
    signature of a neutralization rather than one driver's bad lap.
    """
    race = _race_for(circuit_key, session)
    if race is None:
        return set()

    laps = (
        session.query(Lap)
        .filter(Lap.race_id == race.id, Lap.lap_time_s.isnot(None), Lap.is_valid == True)
        .all()
    )

    by_driver: dict[str, list[float]] = {}
    for lap in laps:
        by_driver.setdefault(lap.driver, []).append(lap.lap_time_s)
    driver_median = {
        d: float(np.median(t)) for d, t in by_driver.items() if len(t) >= 3
    }

    slow_by_lap: dict[int, int] = {}
    present_by_lap: dict[int, int] = {}
    for lap in laps:
        med = driver_median.get(lap.driver)
        if med is None:
            continue
        present_by_lap[lap.lap_number] = present_by_lap.get(lap.lap_number, 0) + 1
        if lap.lap_time_s >= med * _SC_LAP_TIME_MULTIPLIER:
            slow_by_lap[lap.lap_number] = slow_by_lap.get(lap.lap_number, 0) + 1

    sc_laps: set[int] = set()
    for lap_no, present in present_by_lap.items():
        if present < _MIN_DRIVERS_FOR_SC_LAP:
            continue
        if slow_by_lap.get(lap_no, 0) / present >= _SC_FIELD_FRACTION:
            sc_laps.add(lap_no)
    return sc_laps


def field_median_first_stop(circuit_key: str, session) -> float:
    """Median first-stop lap across every driver who made at least one stop."""
    race = _race_for(circuit_key, session)
    if race is None:
        return float("nan")

    drivers = [d[0] for d in session.query(Lap.driver).filter(Lap.race_id == race.id).distinct()]
    first_stops: list[int] = []
    for drv in drivers:
        actual = extract_actual_strategy(circuit_key, drv, session)
        if actual and actual.pit_laps:
            first_stops.append(actual.pit_laps[0])
    return float(statistics.median(first_stops)) if first_stops else float("nan")


def _compound_match(predicted: tuple[str, ...], actual: tuple[str, ...]) -> str:
    """exact = same ordered sequence; partial = same set; mismatch = different set."""
    if predicted == actual:
        return "exact"
    if set(predicted) == set(actual):
        return "partial"
    return "mismatch"


def _pit_lap_error(predicted: tuple[int, ...], actual: tuple[int, ...]) -> tuple[float | None, int]:
    """Returns (MAE when stop counts match else None, first-stop absolute error)."""
    first_err = (
        abs(predicted[0] - actual[0]) if predicted and actual else 0
    )
    if len(predicted) != len(actual):
        return None, first_err
    if not predicted:
        return 0.0, 0
    mae = float(np.mean([abs(p - a) for p, a in zip(sorted(predicted), sorted(actual))]))
    return mae, first_err


def _timing_axis(
    circuit_key: str,
    winner: str,
    total_laps: int,
    n_stops: int,
    predicted_total_s: float,
    session,
) -> TimingAxis:
    """
    Free-air reconstruction of the winner's race time, comparable to the engine's prediction.

    In/out laps are NULL in the cache, so we can't sum lap times directly. Instead:
        actual_total_est = median(winner green laps) * total_laps + n_stops * pit_loss
    Both sides are free-air (no SC/traffic), so the delta isolates the pace/deg model.
    """
    race = _race_for(circuit_key, session)
    times = [
        l.lap_time_s
        for l in session.query(Lap)
        .filter(
            Lap.race_id == race.id,
            Lap.driver == winner,
            Lap.lap_time_s.isnot(None),
            Lap.is_valid == True,
        )
        .all()
    ]
    if not times:
        return TimingAxis(predicted_total_s, float("nan"), float("nan"), float("nan"), 0.0)

    green_median = float(np.median(times))
    actual_total_est = green_median * total_laps + n_stops * pit_loss(circuit_key)
    return TimingAxis(
        predicted_total_s=predicted_total_s,
        actual_total_est_s=actual_total_est,
        time_error_s=predicted_total_s - actual_total_est,
        green_lap_median_s=green_median,
        lap_coverage=len(times) / total_laps,
    )


def _build_flags_and_explanation(
    circuit_key: str,
    predicted_pits: tuple[int, ...],
    actual: ActualStrategy,
    sc_laps: set[int],
    compound_match: str,
    session,
) -> tuple[tuple[str, ...], str]:
    flags: list[str] = []

    # 1. SC-induced stop: an actual pit lap lands on (or next to) a detected SC lap
    sc_hit_laps = [p for p in actual.pit_laps if p in sc_laps or (p - 1) in sc_laps]
    if sc_hit_laps:
        flags.append(f"sc-coincidence: actual stop(s) at {sc_hit_laps} land under detected SC")

    # 2. Compound-gate exclusion: winner used a compound the engine excludes
    avail = set(available_compounds(circuit_key))
    excluded_used = sorted(set(actual.compounds) - avail)
    if excluded_used:
        flags.append(
            f"compound-gate: winner used {excluded_used} which the data gate excludes; "
            f"engine structurally cannot recommend this shape"
        )

    # 3. Undercut / early-stop signature: actual first stop materially earlier, no SC cause
    if predicted_pits and actual.pit_laps:
        gap = predicted_pits[0] - actual.pit_laps[0]
        if gap >= 3 and actual.pit_laps[0] not in sc_laps and (actual.pit_laps[0] - 1) not in sc_laps:
            flags.append(
                f"undercut-signature: actual first stop {gap} laps earlier than predicted "
                f"with no SC coincidence (free-air model ignores track position)"
            )

    # Craft a one-line candidate explanation from the strongest signal.
    # first_gap > 0: engine wanted to pit later than reality (undercut by the team).
    # first_gap < 0: engine wanted to pit earlier than reality (team ran long / overcut).
    first_gap = (predicted_pits[0] - actual.pit_laps[0]) if (predicted_pits and actual.pit_laps) else 0
    if excluded_used:
        explanation = "Compound unavailable"
    elif sc_hit_laps:
        explanation = "Safety Car overlap"
    elif first_gap >= 3:
        explanation = "Early undercut"
    elif first_gap <= -3:
        explanation = "Team ran long (overcut)"
    elif compound_match == "mismatch":
        explanation = "Compound mismatch"
    elif compound_match == "partial":
        explanation = "Same compounds, reordered"
    else:
        explanation = "Close agreement"

    return tuple(flags), explanation


def validate_race(circuit_key: str, session, cfg: MonteCarloConfig) -> RaceValidation | None:
    """
    Run the full engine on one race and compare to the winner. Returns None if the circuit
    cannot generate strategies or the winner's data is missing.
    """
    ok, _ = can_generate(circuit_key)
    if not ok:
        return None

    winner = RACE_ACTUALS.get(circuit_key.lower(), {}).get("winner")
    if winner is None:
        return None
    actual = extract_actual_strategy(circuit_key, winner, session)
    if actual is None:
        return None

    total_laps = total_laps_for(circuit_key, session)
    ctx = build_context(circuit_key, total_laps, session)
    ranked = rank_strategies(generate_strategies(circuit_key, total_laps), ctx)
    headline = ranked[0]

    # Monte Carlo distribution for the headline (deterministic top-1)
    p_sc = expected_sc_rate(circuit_key, session)
    rng_sc = np.random.default_rng(cfg.seed)
    sc_scenarios = sample_sc_scenarios(total_laps, p_sc, cfg, rng_sc)
    predicted_dist = run_monte_carlo(
        headline, ctx, sc_scenarios, cfg, np.random.default_rng(cfg.seed + 1)
    )

    # Stage 3 robust pick (may differ from the deterministic headline)
    robust = robustness_analysis(ranked, ctx, cfg, session)
    robust_pick_key = robust[0].strategy.key if robust else headline.strategy.key

    predicted_pits = headline.strategy.pit_laps
    predicted_compounds = tuple(st.compound for st in headline.strategy.stints)

    pit_mae, first_err = _pit_lap_error(predicted_pits, actual.pit_laps)
    compound_match = _compound_match(predicted_compounds, actual.compounds)
    sc_laps = detect_sc_laps(circuit_key, session)
    flags, explanation = _build_flags_and_explanation(
        circuit_key, predicted_pits, actual, sc_laps, compound_match, session
    )
    timing = _timing_axis(
        circuit_key, winner, total_laps, actual.n_stops, headline.total_time_s, session
    )

    return RaceValidation(
        circuit_key=circuit_key,
        total_laps=total_laps,
        predicted=predicted_dist,
        robust_pick_key=robust_pick_key,
        actual=actual,
        field_median_first_stop=field_median_first_stop(circuit_key, session),
        stop_count_match=(headline.strategy.n_stops == actual.n_stops),
        pit_lap_mae=pit_mae,
        first_stop_abs_error=first_err,
        compound_match=compound_match,
        timing=timing,
        flags=flags,
        candidate_explanation=explanation,
    )


def validate_all(session, cfg: MonteCarloConfig) -> list[RaceValidation]:
    """Validate every cached race the engine can handle, in round order."""
    races = session.query(Race).order_by(Race.round).all()
    results: list[RaceValidation] = []
    for race in races:
        rv = validate_race(race.circuit_key, session, cfg)
        if rv is not None:
            results.append(rv)
    return results


def aggregate(results: list[RaceValidation]) -> dict:
    """Headline numbers across the validated races."""
    matched = [r for r in results if r.pit_lap_mae is not None]
    pit_maes = [r.pit_lap_mae for r in matched]
    time_errors = [r.timing.time_error_s for r in results if r.timing.time_error_s == r.timing.time_error_s]

    return {
        "races_validated": len(results),
        "pit_lap_mae": round(float(np.mean(pit_maes)), 2) if pit_maes else None,
        "first_stop_mae": round(float(np.mean([r.first_stop_abs_error for r in results])), 2)
        if results else None,
        "stop_count_mismatches": sum(1 for r in results if not r.stop_count_match),
        "compound_mismatches": sum(1 for r in results if r.compound_match == "mismatch"),
        "compound_exact_matches": sum(1 for r in results if r.compound_match == "exact"),
        "mean_abs_time_error_s": round(float(np.mean([abs(e) for e in time_errors])), 2)
        if time_errors else None,
        "mean_signed_time_error_s": round(float(np.mean(time_errors)), 2) if time_errors else None,
    }
