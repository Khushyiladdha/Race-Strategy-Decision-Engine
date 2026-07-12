"""
Monte Carlo robustness layer for strategy evaluation.

Takes Stage 2's deterministic ranked strategies and stress-tests the strongest
candidates against safety cars and degradation noise, producing a distribution
per strategy instead of a point estimate.

Design decisions:
- SC events are discrete Poisson windows (not per-lap Bernoulli): real cautions
  are multi-lap; isolated per-lap coin flips are unphysical.
- Common random numbers: SC windows are sampled once and shared across all
  candidate strategies, so every strategy faces the *same* race. Cross-strategy
  variance drops; the pit-timing signal rises.
- Degradation noise scales with extrapolation_laps: a strategy that runs a stint
  10 laps past anything observed carries wider uncertainty — exactly where we
  should be least confident.
- Raw simulation samples preserved so callers can build histograms and violin
  plots without re-running the simulation.
"""
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.engine.evaluator import EvaluatedStrategy, RaceContext
from app.engine.strategy_generator import Strategy
from app.models.safety_car import expected_sc_rate


@dataclass(frozen=True)
class MonteCarloConfig:
    n_sims: int = 2000
    seed: int = 0
    # degradation noise (multiplicative on slope coefficients)
    deg_cv: float = 0.12                  # base coefficient of variation
    extrap_cv_per_lap: float = 0.004      # extra CV per lap beyond max_observed
    # safety car
    mean_sc_duration_laps: float = 4.0   # expected length of one SC event
    sc_pit_discount_frac: float = 0.50   # a stop under SC costs this fraction of normal
    sc_lap_penalty_s: float = 12.0       # seconds added per lap run under SC
    # candidate selection and display
    time_window_s: float = 2.0           # pool = strategies within this of best
    max_candidates: int = 200            # hard cap on pool size
    display_k: int = 8                   # distinct shapes returned
    robust_metric: str = "mean_s"        # "mean_s" or "p90_s"


@dataclass(frozen=True)
class StrategyDistribution:
    strategy: Strategy
    deterministic_time_s: float
    mean_s: float
    std_s: float
    p10_s: float
    p50_s: float
    p90_s: float
    best_s: float
    worst_s: float
    sc_benefit_freq: float        # fraction of sims where >= 1 pit caught an SC window
    samples: tuple[float, ...]   # raw simulation totals for histogram/violin/win-prob
    n_sims: int
    win_probability: float = 0.0  # set by robustness_analysis across the displayed set

    def summary(self, seed: int) -> dict:
        """
        Persist-friendly summary — the fields worth saving, without the 2000-sample
        array. Stage 4 embeds this in the validation report; Stages 5/8 read it back.
        """
        return {
            "strategy_key": self.strategy.key,
            "deterministic_time_s": round(self.deterministic_time_s, 2),
            "mean_s": round(self.mean_s, 2),
            "std_s": round(self.std_s, 2),
            "p10_s": round(self.p10_s, 2),
            "p50_s": round(self.p50_s, 2),
            "p90_s": round(self.p90_s, 2),
            "sc_benefit_freq": round(self.sc_benefit_freq, 4),
            "seed": seed,
            "n_simulations": self.n_sims,
        }


def _multiset_key(strategy: Strategy) -> tuple:
    """
    Canonical (compound, length) multiset — the equivalence class Stage 2 can't separate.

    Two strategies in the same class differ only in pit timing. Stage 2 treats them
    identically; Monte Carlo gives them different SC exposure and separates them.
    Using sorted tuple (not frozenset) so two stints of equal compound+length aren't lost.
    """
    pairs = [(st.compound, st.length) for st in strategy.stints]
    return tuple(sorted(pairs))


def sample_sc_scenarios(
    total_laps: int,
    p_per_lap: float,
    cfg: MonteCarloConfig,
    rng: np.random.Generator,
) -> list[list[tuple[int, int]]]:
    """
    Generate n_sims SC scenarios as lists of (start, end) lap windows (inclusive, 1-based).

    Calibration: the expected SC-lap fraction matches p_per_lap * total_laps by construction.
        λ = p_per_lap * total_laps / mean_sc_duration
        K ~ Poisson(λ) events per race; each event has duration ~ Uniform[3, 6] laps.
    Overlapping or adjacent windows are merged so lap counts are never double-counted.
    """
    if p_per_lap <= 0.0:
        return [[] for _ in range(cfg.n_sims)]

    lam = p_per_lap * total_laps / cfg.mean_sc_duration_laps
    scenarios: list[list[tuple[int, int]]] = []

    for _ in range(cfg.n_sims):
        n_events = int(rng.poisson(lam))
        windows: list[tuple[int, int]] = []

        for _ in range(n_events):
            dur = int(rng.integers(3, 7))  # 3..6 inclusive
            max_start = max(1, total_laps - dur + 1)
            start = int(rng.integers(1, max_start + 1))
            end = min(start + dur - 1, total_laps)
            windows.append((start, end))

        if windows:
            windows.sort()
            merged: list[tuple[int, int]] = [windows[0]]
            for s, e in windows[1:]:
                ps, pe = merged[-1]
                if s <= pe + 1:       # overlapping or adjacent
                    merged[-1] = (ps, max(pe, e))
                else:
                    merged.append((s, e))
            windows = merged

        scenarios.append(windows)

    return scenarios


def _under_sc(lap: int, windows: list[tuple[int, int]]) -> bool:
    """True if this lap falls inside any SC window."""
    for start, end in windows:
        if start <= lap <= end:
            return True
    return False


def sc_laps_count(windows: list[tuple[int, int]], total_laps: int) -> int:
    """Total laps under SC, clamped to race length. Exposed for calibration tests."""
    return sum(min(end, total_laps) - start + 1 for start, end in windows)


def simulate_strategy(
    evaluated: EvaluatedStrategy,
    ctx: RaceContext,
    sc_scenarios: list[list[tuple[int, int]]],
    cfg: MonteCarloConfig,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Simulate n_sims races for this strategy. Returns (totals, sc_benefited).

    Three perturbations on top of the deterministic baseline T0:
    1. Degradation noise: per-stint multiplicative factor m ~ N(1, sigma) on slope.
       sigma grows with extrapolation_laps to model higher uncertainty past observed data.
    2. SC cheap-stop: pits inside an SC window cost (1 - discount) * pit_loss.
    3. SC lap penalty: common-mode time added for each lap run under caution.

    SC windows are shared across strategies (common random numbers) — rng is used
    only for per-strategy idiosyncratic degradation noise.

    All three perturbations are fully vectorised over the n_sims dimension so there
    is no Python-level loop over simulations.
    """
    n = cfg.n_sims
    T0 = evaluated.total_time_s
    totals = np.full(n, T0, dtype=np.float64)
    sc_benefited = np.zeros(n, dtype=bool)

    # Pre-compute per-stint values
    pit_laps = evaluated.strategy.pit_laps
    stint_data: list[tuple[float, float]] = []   # (base_deg, sigma)
    for st in evaluated.strategy.stints:
        a, b = ctx.deg[st.compound]
        nl = st.length
        base_deg = a * nl * (nl + 1) / 2 + b * nl * (nl + 1) * (2 * nl + 1) / 6
        beyond = max(0, nl - ctx.max_observed[st.compound])
        sigma = cfg.deg_cv + cfg.extrap_cv_per_lap * beyond
        stint_data.append((base_deg, sigma))

    # 1. Vectorised degradation noise: one draw of size n per stint
    for base_deg, sigma in stint_data:
        if sigma > 0.0:
            m = rng.normal(1.0, sigma, size=n)    # shape (n,)
            totals += base_deg * (m - 1.0)

    # 2. Build SC coverage matrix (n × (total_laps+1), 1-indexed, lap 0 unused)
    max_lap = ctx.total_laps
    sc_coverage = np.zeros((n, max_lap + 1), dtype=bool)
    for sim_idx, windows in enumerate(sc_scenarios):
        for start, end in windows:
            sc_coverage[sim_idx, start: end + 1] = True

    # 3. Vectorised cheap-stop discount
    for pit_lap in pit_laps:
        under = sc_coverage[:, pit_lap]           # shape (n,)
        totals -= cfg.sc_pit_discount_frac * ctx.pit_loss_s * under
        sc_benefited |= under

    # 4. Vectorised SC lap penalty
    sc_laps_per_sim = sc_coverage[:, 1: max_lap + 1].sum(axis=1)   # shape (n,)
    totals += cfg.sc_lap_penalty_s * sc_laps_per_sim

    return totals, sc_benefited


def run_monte_carlo(
    evaluated: EvaluatedStrategy,
    ctx: RaceContext,
    sc_scenarios: list[list[tuple[int, int]]],
    cfg: MonteCarloConfig,
    rng: np.random.Generator,
) -> StrategyDistribution:
    """Run simulation and package results into a StrategyDistribution."""
    totals, sc_benefited = simulate_strategy(evaluated, ctx, sc_scenarios, cfg, rng)
    return StrategyDistribution(
        strategy=evaluated.strategy,
        deterministic_time_s=evaluated.total_time_s,
        mean_s=float(np.mean(totals)),
        std_s=float(np.std(totals)),
        p10_s=float(np.percentile(totals, 10)),
        p50_s=float(np.percentile(totals, 50)),
        p90_s=float(np.percentile(totals, 90)),
        best_s=float(np.min(totals)),
        worst_s=float(np.max(totals)),
        sc_benefit_freq=float(np.mean(sc_benefited)),
        samples=tuple(float(x) for x in totals),
        n_sims=cfg.n_sims,
    )


def robustness_analysis(
    ranked: list[EvaluatedStrategy],
    ctx: RaceContext,
    cfg: MonteCarloConfig,
    session,
) -> list[StrategyDistribution]:
    """
    Orchestrator: pool → simulate → dedup by multiset → top display_k.

    Resolves Stage 2 Limitations A and B with a single mechanism:
    A (5.5x redundancy): after simulation, group by (compound, length) multiset
      and keep the best representative per group. Stage 2 ties are now broken.
    B (pit laps inert): SC windows make pit-lap placement load-bearing before
      the dedup step discards redundant variants.

    The dedup deliberately runs AFTER simulation — throwing away pit-timing variety
      before sampling would discard exactly the signal we need to evaluate.
    """
    if not ranked:
        return []

    # 1. Pool: strategies within time_window_s of the best, capped
    best_time = ranked[0].total_time_s
    pool = [e for e in ranked if e.total_time_s - best_time <= cfg.time_window_s]
    pool = pool[: cfg.max_candidates]

    # 2. Sample SC scenarios once — shared (common random numbers)
    p_sc = expected_sc_rate(ctx.circuit_key, session)
    rng_sc = np.random.default_rng(cfg.seed)
    sc_scenarios = sample_sc_scenarios(ctx.total_laps, p_sc, cfg, rng_sc)

    # 3. Simulate each candidate with its own reproducible degradation RNG
    distributions: list[StrategyDistribution] = []
    for i, ev in enumerate(pool):
        rng_deg = np.random.default_rng(cfg.seed + i + 1)  # +1 avoids SC seed collision
        dist = run_monte_carlo(ev, ctx, sc_scenarios, cfg, rng_deg)
        distributions.append(dist)

    # 4. Dedup: within each multiset class keep the best-metric representative
    if cfg.robust_metric == "p90_s":
        metric_fn = lambda d: d.p90_s
    else:
        metric_fn = lambda d: d.mean_s

    best_per_class: dict[tuple, StrategyDistribution] = {}
    for dist in distributions:
        mk = _multiset_key(dist.strategy)
        if mk not in best_per_class or metric_fn(dist) < metric_fn(best_per_class[mk]):
            best_per_class[mk] = dist

    # 5. Sort representatives and return top display_k
    representatives = sorted(best_per_class.values(), key=metric_fn)[: cfg.display_k]

    # 6. Win-probability across the displayed set. SC scenarios are shared (CRN), so column i
    #    is the SAME race for every strategy — argmin per column is a fair head-to-head. This is
    #    the intended payoff of Stage 3's common random numbers. Sums to 1 across the set.
    if representatives:
        matrix = np.array([r.samples for r in representatives])   # (k, n_sims)
        winners = np.argmin(matrix, axis=0)                       # winning row per sim
        counts = np.bincount(winners, minlength=len(representatives))
        win_probs = counts / matrix.shape[1]
        representatives = [
            replace(r, win_probability=float(wp)) for r, wp in zip(representatives, win_probs)
        ]

    return representatives
