"""
Orchestration between the HTTP layer and the engine. This is the ONLY place API code calls
engine functions; routers stay declarative. Engine dataclasses are mapped into Pydantic
response models here.
"""
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db.models import Race
from app.engine.evaluator import EvaluatedStrategy, build_context, rank_strategies
from app.engine.monte_carlo import MonteCarloConfig, StrategyDistribution, robustness_analysis
from app.engine.persistence import (
    load_validation_report,
    race_validation_to_dict,
    save_validation_report,
)
from app.engine.strategy_generator import can_generate, generate_strategies
from app.engine.validation import total_laps_for, validate_all, validate_race
from app.models.safety_car import expected_sc_rate
from app.report.summary import confidence_note, executive_summary
from app.api import schemas

_BACKEND_ROOT = Path(__file__).parent.parent.parent
_REPORT_DIR = _BACKEND_ROOT / "data" / "validation"
_REPORT_JSON = _REPORT_DIR / "report.json"


# --- typed errors the routers translate to HTTP status codes ---------------

class UnknownCircuit(ValueError):
    """Circuit is not in the cache -> 404."""


class CannotGenerate(ValueError):
    """Circuit exists but has too little data to build strategies -> 422."""


def _race_row(session, circuit_key: str) -> Race | None:
    return session.query(Race).filter(Race.circuit_key == circuit_key.lower()).first()


def _require_generatable(session, circuit_key: str) -> None:
    """404 if the circuit isn't cached, 422 if it can't generate."""
    if _race_row(session, circuit_key) is None:
        raise UnknownCircuit(f"no cached race for circuit '{circuit_key}'")
    ok, reason = can_generate(circuit_key)
    if not ok:
        raise CannotGenerate(f"{circuit_key}: {reason}")


# --- discovery -------------------------------------------------------------

def list_races(session) -> list[schemas.RaceListItem]:
    races = session.query(Race).order_by(Race.round).all()
    out: list[schemas.RaceListItem] = []
    for race in races:
        ok, reason = can_generate(race.circuit_key)
        out.append(schemas.RaceListItem(
            id=race.id,
            year=race.year,
            round=race.round,
            circuit_key=race.circuit_key,
            can_generate=ok,
            reason=reason,
            total_laps=total_laps_for(race.circuit_key, session),
        ))
    return out


# --- mappers ---------------------------------------------------------------

def _breakdown(ev: EvaluatedStrategy) -> schemas.Breakdown:
    return schemas.Breakdown(
        base_s=ev.base_time_s,
        compound_offset_s=ev.compound_offset_time_s,
        degradation_s=ev.degradation_time_s,
        fuel_s=ev.fuel_time_s,
        pit_s=ev.pit_time_s,
        total_s=ev.total_time_s,
    )


def _distribution(d: StrategyDistribution) -> schemas.DistributionOut:
    return schemas.DistributionOut(
        mean_s=d.mean_s, std_s=d.std_s,
        p10_s=d.p10_s, p50_s=d.p50_s, p90_s=d.p90_s,
        best_s=d.best_s, worst_s=d.worst_s,
        sc_benefit_freq=d.sc_benefit_freq, n_sims=d.n_sims,
    )


N_HIST_BINS = 32


def _histogram(samples: tuple[float, ...], lo: float, hi: float) -> list[int]:
    if hi <= lo:
        return [0] * N_HIST_BINS
    counts, _ = np.histogram(samples, bins=N_HIST_BINS, range=(lo, hi))
    return [int(c) for c in counts]


def _strategy_out(
    d: StrategyDistribution, ev: EvaluatedStrategy, histogram: list[int]
) -> schemas.StrategyOut:
    return schemas.StrategyOut(
        key=d.strategy.key,
        n_stops=d.strategy.n_stops,
        pit_laps=list(d.strategy.pit_laps),
        compounds=[st.compound for st in d.strategy.stints],
        win_probability=d.win_probability,
        histogram=histogram,
        breakdown=_breakdown(ev),
        distribution=_distribution(d),
    )


# --- strategy evaluation ---------------------------------------------------

def evaluate_circuit(session, req: schemas.EvaluateRequest) -> schemas.EvaluateResponse:
    _require_generatable(session, req.circuit_key)

    t0 = time.perf_counter()
    total_laps = req.total_laps or total_laps_for(req.circuit_key, session)
    cfg = MonteCarloConfig(
        n_sims=req.n_sims, seed=req.seed,
        robust_metric=req.robust_metric, display_k=req.top_k,
    )

    ctx = build_context(req.circuit_key, total_laps, session)
    strategies = generate_strategies(req.circuit_key, total_laps)
    ranked = rank_strategies(strategies, ctx)          # list[EvaluatedStrategy], ascending
    by_key = {ev.strategy.key: ev for ev in ranked}

    distributions = robustness_analysis(ranked, ctx, cfg, session)   # top-k, deduped

    # Shared histogram domain so every strategy's bars line up on one axis.
    hist_lo = min((d.best_s for d in distributions), default=0.0)
    hist_hi = max((d.worst_s for d in distributions), default=0.0)
    strategy_out = [
        _strategy_out(d, by_key[d.strategy.key], _histogram(d.samples, hist_lo, hist_hi))
        for d in distributions
    ]

    deterministic_top_key = ranked[0].strategy.key
    robust_top_key = distributions[0].strategy.key if distributions else deterministic_top_key
    runtime_ms = int((time.perf_counter() - t0) * 1000)

    return schemas.EvaluateResponse(
        circuit_key=req.circuit_key.lower(),
        total_laps=total_laps,
        sc_rate_per_lap=expected_sc_rate(req.circuit_key, session),
        n_strategies_generated=len(strategies),
        deterministic_top_key=deterministic_top_key,
        robust_top_key=robust_top_key,
        strategies=strategy_out,
        histogram_lo=hist_lo,
        histogram_hi=hist_hi,
        runtime_ms=runtime_ms,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


# --- model insights --------------------------------------------------------

def get_degradation(session, circuit_key: str) -> schemas.DegradationResponse:
    """Fitted deg(n) = a*n + b*n^2 per available compound, sampled into a curve for plotting."""
    _require_generatable(session, circuit_key)
    from app.models.tyre_degradation import available_compounds, load_params

    compounds: list[schemas.DegradationCurve] = []
    for compound in available_compounds(circuit_key):
        p = load_params(circuit_key, compound)
        a, b = p["a"], p["b"]
        max_obs = int(p["max_stint_lap_observed"])
        curve = [
            schemas.DegradationPoint(lap=n, loss_s=round(a * n + b * n * n, 4))
            for n in range(1, max_obs + 1)
        ]
        compounds.append(
            schemas.DegradationCurve(
                compound=compound, a=a, b=b, max_observed=max_obs, curve=curve
            )
        )
    return schemas.DegradationResponse(circuit_key=circuit_key.lower(), compounds=compounds)


# --- validation ------------------------------------------------------------

def _load_or_build_report(session, refresh: bool) -> dict:
    if refresh or not _REPORT_JSON.exists():
        cfg = MonteCarloConfig()   # defaults: n_sims=2000, seed=0
        results = validate_all(session, cfg)
        save_validation_report(results, _REPORT_DIR, seed=cfg.seed)
    return load_validation_report(_REPORT_JSON)


def get_validation_all(session, refresh: bool = False) -> schemas.ValidationAllResponse:
    data = _load_or_build_report(session, refresh)
    return schemas.ValidationAllResponse(
        aggregate=data["aggregate"],
        races=[schemas.ValidationDetailOut.model_validate(r) for r in data["races"]],
    )


def get_validation_one(session, circuit_key: str, refresh: bool = False) -> schemas.ValidationDetailOut:
    _require_generatable(session, circuit_key)
    key = circuit_key.lower()

    data = _load_or_build_report(session, refresh)
    for r in data["races"]:
        if r["circuit_key"] == key:
            return schemas.ValidationDetailOut.model_validate(r)

    # Generatable but absent from a stale report -> force one rebuild.
    data = _load_or_build_report(session, refresh=True)
    for r in data["races"]:
        if r["circuit_key"] == key:
            return schemas.ValidationDetailOut.model_validate(r)

    raise UnknownCircuit(f"no validation available for circuit '{circuit_key}'")


# --- report ----------------------------------------------------------------

def build_report(session, req: schemas.ReportRequest) -> schemas.ReportResponse:
    _require_generatable(session, req.circuit_key)

    eval_req = schemas.EvaluateRequest(
        circuit_key=req.circuit_key, n_sims=req.n_sims, seed=req.seed, top_k=8,
    )
    evaluated = evaluate_circuit(session, eval_req)
    recommendation = evaluated.strategies[0]   # robust top-1

    # Single-race validation, computed fresh so the report reflects this run's config.
    cfg = MonteCarloConfig(n_sims=req.n_sims, seed=req.seed)
    rv = validate_race(req.circuit_key, session, cfg)
    if rv is None:
        raise CannotGenerate(f"{req.circuit_key}: validation unavailable")
    validation = schemas.ValidationDetailOut.model_validate(
        race_validation_to_dict(rv, req.seed)
    )

    return schemas.ReportResponse(
        circuit_key=req.circuit_key.lower(),
        recommendation=recommendation,
        validation=validation,
        explanation=validation.explanation,
        executive_summary=executive_summary(recommendation, validation),
        confidence_note=confidence_note(evaluated.strategies),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


# --- ops -------------------------------------------------------------------

def validation_report_mtime() -> str | None:
    if not _REPORT_JSON.exists():
        return None
    ts = _REPORT_JSON.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
