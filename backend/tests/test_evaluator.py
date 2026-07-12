import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.engine.evaluator import (
    EvaluatedStrategy,
    RaceContext,
    _deg_sum,
    _fuel_sum,
    evaluate,
    rank_strategies,
)
from app.engine.strategy_generator import Stint, Strategy


def _ctx(**overrides) -> RaceContext:
    defaults = dict(
        circuit_key="bahrain",
        total_laps=57,
        base_lap_s=95.0,
        pit_loss_s=22.0,
        fuel_k=0.03,
        deg={"SOFT": (0.12, 0.001), "MEDIUM": (0.08, 0.0005), "HARD": (0.05, 0.0)},
        max_observed={"SOFT": 18, "MEDIUM": 30, "HARD": 24},
    )
    defaults.update(overrides)
    return RaceContext(**defaults)


def _one_stop(p=25, c1="SOFT", c2="HARD", total=57) -> Strategy:
    return Strategy(stints=(
        Stint(c1, 1, p),
        Stint(c2, p + 1, total),
    ))


def _two_stop(p1=18, p2=38, total=57) -> Strategy:
    return Strategy(stints=(
        Stint("SOFT", 1, p1),
        Stint("MEDIUM", p1 + 1, p2),
        Stint("HARD", p2 + 1, total),
    ))


# --- closed forms must equal the naive loops they replace -------------------

@pytest.mark.parametrize("n", [1, 2, 5, 17, 40])
@pytest.mark.parametrize("a,b", [(0.12, 0.001), (0.05, 0.0), (0.0, 0.004)])
def test_deg_closed_form_matches_naive_loop(n, a, b):
    naive = sum(a * i + b * i ** 2 for i in range(1, n + 1))
    assert _deg_sum(n, a, b) == pytest.approx(naive, abs=1e-9)


@pytest.mark.parametrize("start,end", [(1, 1), (1, 57), (19, 38), (39, 57)])
def test_fuel_closed_form_matches_naive_loop(start, end):
    k = 0.03
    naive = sum(k * L for L in range(start, end + 1))
    assert _fuel_sum(start, end, k) == pytest.approx(naive, abs=1e-9)


# --- the additive breakdown ------------------------------------------------

def test_breakdown_components_sum_to_total():
    e = evaluate(_two_stop(), _ctx())
    parts = (
        e.base_time_s
        + e.compound_offset_time_s
        + e.degradation_time_s
        + e.fuel_time_s
        + e.pit_time_s
    )
    assert parts == pytest.approx(e.total_time_s, abs=1e-9)


def test_fuel_is_time_gained_and_pit_is_time_lost():
    e = evaluate(_one_stop(), _ctx())
    assert e.fuel_time_s < 0, "fuel burn-off makes the car faster"
    assert e.pit_time_s > 0


def test_fuel_time_covers_every_race_lap_exactly_once():
    """Stints tile 1..N, so summed fuel must equal a single whole-race sum."""
    ctx = _ctx()
    e = evaluate(_two_stop(), ctx)
    whole_race = -_fuel_sum(1, ctx.total_laps, ctx.fuel_k)
    assert e.fuel_time_s == pytest.approx(whole_race, abs=1e-9)


# --- physical sanity -------------------------------------------------------

def test_longer_stint_costs_more_degradation():
    ctx = _ctx()
    short = evaluate(_one_stop(p=15), ctx).degradation_time_s
    long_ = evaluate(_one_stop(p=40), ctx).degradation_time_s
    assert long_ > short


def test_two_stop_pays_exactly_one_extra_pit_loss():
    ctx = _ctx()
    one = evaluate(_one_stop(), ctx)
    two = evaluate(_two_stop(), ctx)
    assert two.pit_time_s - one.pit_time_s == pytest.approx(ctx.pit_loss_s, abs=1e-9)


def test_extrapolation_accumulates_across_every_stint():
    """SOFT observed to 18, HARD to 24. A lap-30 stop overruns both."""
    ctx = _ctx()
    e = evaluate(_one_stop(p=30, c1="SOFT", c2="HARD"), ctx)
    soft_over = 30 - 18   # stint laps 1..30
    hard_over = 27 - 24   # stint laps 31..57
    assert e.extrapolation_laps == soft_over + hard_over


def test_no_extrapolation_when_every_stint_is_within_observed_range():
    ctx = _ctx(max_observed={"SOFT": 30, "MEDIUM": 30, "HARD": 30})
    e = evaluate(_two_stop(p1=18, p2=38), ctx)  # stints of 18, 20, 19 laps
    assert e.extrapolation_laps == 0


# --- the cancellation property, pinned ------------------------------------

def test_base_and_fuel_are_strategy_independent():
    """
    Fuel and base pace cancel out of the ranking today because every strategy
    covers the same laps. Stage 3's safety cars will break this. When they do,
    this test must fail loudly rather than the assumption rotting unnoticed.
    """
    ctx = _ctx()
    a = evaluate(_one_stop(p=25), ctx)
    b = evaluate(_two_stop(p1=18, p2=38), ctx)
    assert a.base_time_s == pytest.approx(b.base_time_s, abs=1e-9)
    assert a.fuel_time_s == pytest.approx(b.fuel_time_s, abs=1e-9)


# --- ranking ---------------------------------------------------------------

def test_ranking_is_ascending_and_deterministic():
    ctx = _ctx()
    strategies = [_one_stop(p) for p in range(10, 45)] + [_two_stop()]
    ranked = rank_strategies(strategies, ctx)
    times = [e.total_time_s for e in ranked]
    assert times == sorted(times)
    again = rank_strategies(list(reversed(strategies)), ctx)
    assert [e.strategy.key for e in ranked] == [e.strategy.key for e in again]


def test_evaluate_returns_evaluated_strategy():
    assert isinstance(evaluate(_one_stop(), _ctx()), EvaluatedStrategy)
