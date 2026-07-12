import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.engine.evaluator import RaceContext, evaluate
from app.engine.monte_carlo import (
    MonteCarloConfig,
    StrategyDistribution,
    _multiset_key,
    run_monte_carlo,
    robustness_analysis,
    sample_sc_scenarios,
    sc_laps_count,
    simulate_strategy,
)
from app.engine.strategy_generator import Stint, Strategy


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

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


def _one_stop(p: int = 25, c1: str = "SOFT", c2: str = "HARD", total: int = 57) -> Strategy:
    return Strategy(stints=(Stint(c1, 1, p), Stint(c2, p + 1, total)))


def _cfg_zero_noise(**overrides) -> MonteCarloConfig:
    """Config with all perturbation disabled — sim should collapse to deterministic."""
    base = dict(
        n_sims=200,
        seed=0,
        deg_cv=0.0,
        extrap_cv_per_lap=0.0,
        sc_pit_discount_frac=0.0,
        sc_lap_penalty_s=0.0,
    )
    base.update(overrides)
    return MonteCarloConfig(**base)


# Two-stop strategies that share the same (compound, length) multiset.
# H-S-S@16,36 and S-S-H@20,41 for 57 laps both map to {(HARD,16),(SOFT,20),(SOFT,21)}.
_HSS = Strategy(stints=(
    Stint("HARD",  1, 16),
    Stint("SOFT", 17, 36),
    Stint("SOFT", 37, 57),
))
_SSH = Strategy(stints=(
    Stint("SOFT",  1, 20),
    Stint("SOFT", 21, 41),
    Stint("HARD", 42, 57),
))


# ---------------------------------------------------------------------------
# Correctness anchors
# ---------------------------------------------------------------------------

def test_zero_noise_zero_sc_collapses_to_deterministic():
    """With every perturbation disabled, mean == T0 and std == 0."""
    cfg = _cfg_zero_noise(n_sims=500)
    ctx = _ctx()
    ev = evaluate(_one_stop(), ctx)
    rng_sc = np.random.default_rng(0)
    sc_scenarios = sample_sc_scenarios(ctx.total_laps, 0.0, cfg, rng_sc)
    dist = run_monte_carlo(ev, ctx, sc_scenarios, cfg, np.random.default_rng(1))
    assert dist.mean_s == pytest.approx(dist.deterministic_time_s, abs=1e-9)
    assert dist.std_s == pytest.approx(0.0, abs=1e-9)


def test_seed_determinism():
    """Same seed produces identical distributions; different seeds differ."""
    cfg = MonteCarloConfig(n_sims=500, seed=42)
    ctx = _ctx()
    ev = evaluate(_one_stop(), ctx)
    rng_sc = np.random.default_rng(cfg.seed)
    sc = sample_sc_scenarios(ctx.total_laps, 0.10, cfg, rng_sc)

    d1 = run_monte_carlo(ev, ctx, sc, cfg, np.random.default_rng(cfg.seed + 1))
    d2 = run_monte_carlo(ev, ctx, sc, cfg, np.random.default_rng(cfg.seed + 1))
    d3 = run_monte_carlo(ev, ctx, sc, cfg, np.random.default_rng(cfg.seed + 99))

    assert d1.mean_s == pytest.approx(d2.mean_s, abs=1e-12)
    assert d1.std_s == pytest.approx(d2.std_s, abs=1e-12)
    # Different seed should produce different draws (astronomically unlikely to collide)
    assert abs(d1.mean_s - d3.mean_s) > 1e-6 or abs(d1.std_s - d3.std_s) > 1e-6


def test_sc_lap_fraction_calibration():
    """
    Empirical SC-lap fraction over many scenarios should match p_per_lap.
    Guards the λ = p*N/mean_dur derivation.
    """
    cfg = MonteCarloConfig(n_sims=5000, seed=7)
    rng = np.random.default_rng(7)
    total_laps = 57
    p = 0.20
    scenarios = sample_sc_scenarios(total_laps, p, cfg, rng)
    total_sc = sum(sc_laps_count(w, total_laps) for w in scenarios)
    empirical_p = total_sc / (total_laps * len(scenarios))
    assert abs(empirical_p - p) < 0.03   # within 3 pp; 5000 sims should be well within


def test_percentile_ordering():
    """best <= p10 <= p50 <= p90 <= worst for every distribution."""
    cfg = MonteCarloConfig(n_sims=500, seed=0)
    ctx = _ctx()
    ev = evaluate(_one_stop(), ctx)
    rng_sc = np.random.default_rng(0)
    sc = sample_sc_scenarios(ctx.total_laps, 0.15, cfg, rng_sc)
    dist = run_monte_carlo(ev, ctx, sc, cfg, np.random.default_rng(1))
    assert dist.best_s <= dist.p10_s
    assert dist.p10_s <= dist.p50_s
    assert dist.p50_s <= dist.p90_s
    assert dist.p90_s <= dist.worst_s


def test_samples_length_matches_n_sims():
    cfg = MonteCarloConfig(n_sims=123, seed=0)
    ctx = _ctx()
    ev = evaluate(_one_stop(), ctx)
    sc = sample_sc_scenarios(ctx.total_laps, 0.0, cfg, np.random.default_rng(0))
    dist = run_monte_carlo(ev, ctx, sc, cfg, np.random.default_rng(1))
    assert len(dist.samples) == 123
    assert dist.n_sims == 123


# ---------------------------------------------------------------------------
# Sum-to-total: a single sim's total equals T0 + Δdeg + Δpit + Δsc
# ---------------------------------------------------------------------------

def test_sum_to_total_single_sim():
    """
    White-box: with zero noise and a controlled SC scenario, the perturbation
    formula is verifiable analytically.

    Strategy pits at lap 25. SC window [23, 27] → pit lap 25 is inside.
    Expected: total = T0 - discount*pit_loss + sc_penalty * 5 (5 laps in window).
    """
    cfg = MonteCarloConfig(
        n_sims=1,
        seed=0,
        deg_cv=0.0,
        extrap_cv_per_lap=0.0,
        sc_pit_discount_frac=0.5,
        sc_lap_penalty_s=10.0,
    )
    ctx = _ctx()
    strategy = _one_stop(p=25)
    ev = evaluate(strategy, ctx)

    sc_scenarios = [[(23, 27)]]   # 5 SC laps; pit at 25 inside [23,27]
    totals, _ = simulate_strategy(ev, ctx, sc_scenarios, cfg, np.random.default_rng(0))

    expected_delta = (
        -cfg.sc_pit_discount_frac * ctx.pit_loss_s   # cheap stop
        + cfg.sc_lap_penalty_s * 5                    # 5 SC laps: 23,24,25,26,27
    )
    assert totals[0] == pytest.approx(ev.total_time_s + expected_delta, abs=1e-9)


# ---------------------------------------------------------------------------
# SC effect tests
# ---------------------------------------------------------------------------

def test_cheap_stop_reduces_mean_time():
    """If every sim has a pit under SC and sc_lap_penalty = 0, mean < T0."""
    cfg = MonteCarloConfig(
        n_sims=200,
        seed=0,
        deg_cv=0.0,
        extrap_cv_per_lap=0.0,
        sc_lap_penalty_s=0.0,
        sc_pit_discount_frac=0.5,
    )
    ctx = _ctx()
    ev = evaluate(_one_stop(p=25), ctx)

    # Every sim: SC covers lap 25 (pit lap)
    sc_scenarios = [[(23, 27)]] * cfg.n_sims
    dist = run_monte_carlo(ev, ctx, sc_scenarios, cfg, np.random.default_rng(0))

    assert dist.mean_s < dist.deterministic_time_s
    assert dist.sc_benefit_freq == pytest.approx(1.0, abs=1e-9)


def test_no_sc_means_no_benefit():
    """With p = 0, no scenarios are generated, sc_benefit_freq == 0."""
    cfg = MonteCarloConfig(n_sims=200, seed=0, deg_cv=0.0, extrap_cv_per_lap=0.0)
    ctx = _ctx()
    ev = evaluate(_one_stop(), ctx)
    sc = sample_sc_scenarios(ctx.total_laps, 0.0, cfg, np.random.default_rng(0))
    dist = run_monte_carlo(ev, ctx, sc, cfg, np.random.default_rng(1))
    assert dist.sc_benefit_freq == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Extrapolation widens uncertainty
# ---------------------------------------------------------------------------

def test_extrapolation_widens_std():
    """
    Strategy A: all stints within max_observed. Strategy B: one stint well past it.
    B must have strictly larger std_s (more uncertainty, not just equal).

    We use zero SC so only degradation noise drives the spread.
    """
    # max_observed SOFT=25, HARD=40 — comfortable headroom for the "within" strategy
    ctx = _ctx(max_observed={"SOFT": 25, "MEDIUM": 30, "HARD": 40})

    # A: SOFT 20 laps (within 25), HARD 37 laps (within 40)
    strat_a = _one_stop(p=20, c1="SOFT", c2="HARD")
    # B: SOFT 30 laps (5 past max=25), HARD 27 laps (within 40)
    strat_b = _one_stop(p=30, c1="SOFT", c2="HARD")

    cfg = MonteCarloConfig(n_sims=2000, seed=0, sc_lap_penalty_s=0.0, sc_pit_discount_frac=0.0)
    sc = sample_sc_scenarios(ctx.total_laps, 0.0, cfg, np.random.default_rng(0))

    ev_a = evaluate(strat_a, ctx)
    ev_b = evaluate(strat_b, ctx)
    dist_a = run_monte_carlo(ev_a, ctx, sc, cfg, np.random.default_rng(1))
    dist_b = run_monte_carlo(ev_b, ctx, sc, cfg, np.random.default_rng(2))

    assert dist_b.std_s > dist_a.std_s, (
        f"Extrapolating strategy should have wider std: "
        f"std_a={dist_a.std_s:.4f}, std_b={dist_b.std_s:.4f}"
    )


# ---------------------------------------------------------------------------
# Limitation-resolution tests
# ---------------------------------------------------------------------------

def test_multiset_key_groups_same_class():
    """H-S-S@16,36 and S-S-H@20,41 must hash to the same multiset key."""
    assert _multiset_key(_HSS) == _multiset_key(_SSH)


def test_multiset_key_separates_different_class():
    """A one-stop and a two-stop must not share a multiset key."""
    assert _multiset_key(_one_stop(p=20)) != _multiset_key(_HSS)


def test_mc_breaks_stage2_tie():
    """
    H-S-S@16,36 and S-S-H@20,41 have identical deterministic times (Limitation B).
    With a SC window [17,20] in every sim, only S-S-H's lap-20 pit is inside — it
    benefits from the cheap-stop discount, so mean_s differs between the two.
    """
    cfg = MonteCarloConfig(
        n_sims=500,
        seed=0,
        deg_cv=0.0,
        extrap_cv_per_lap=0.0,
        sc_lap_penalty_s=0.0,       # isolate the cheap-stop signal
        sc_pit_discount_frac=0.5,
    )
    ctx = _ctx()
    ev_hss = evaluate(_HSS, ctx)
    ev_ssh = evaluate(_SSH, ctx)

    # Verify Stage 2 treats them identically
    assert ev_hss.total_time_s == pytest.approx(ev_ssh.total_time_s, abs=1e-9), (
        "Precondition failed: strategies are not Stage 2 ties"
    )

    # SC window at laps 17-20: S-S-H pits at lap 20 (inside), H-S-S pits at 16 and 36 (outside)
    sc_scenarios = [[(17, 20)]] * cfg.n_sims

    dist_hss = run_monte_carlo(ev_hss, ctx, sc_scenarios, cfg, np.random.default_rng(1))
    dist_ssh = run_monte_carlo(ev_ssh, ctx, sc_scenarios, cfg, np.random.default_rng(2))

    # S-S-H catches the cheap stop; H-S-S does not
    assert dist_ssh.mean_s < dist_hss.mean_s, (
        f"MC should break the tie: mean_ssh={dist_ssh.mean_s:.3f}, mean_hss={dist_hss.mean_s:.3f}"
    )
    assert dist_ssh.sc_benefit_freq == pytest.approx(1.0, abs=1e-9)
    assert dist_hss.sc_benefit_freq == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Integration tests (require populated Postgres)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_robustness_analysis_returns_distinct_multisets():
    """
    Resolves Limitation A: every returned distribution must be from a distinct
    (compound, length) multiset class. No two entries should share the same class.
    """
    from db.session import SessionLocal
    from app.engine.evaluator import build_context, rank_strategies
    from app.engine.strategy_generator import generate_strategies

    session = SessionLocal()
    try:
        circuit, total_laps = "bahrain", 57
        ctx = build_context(circuit, total_laps, session)
        ranked = rank_strategies(generate_strategies(circuit, total_laps), ctx)
        cfg = MonteCarloConfig(n_sims=500, seed=0)
        results = robustness_analysis(ranked, ctx, cfg, session)

        assert len(results) > 0
        assert len(results) <= cfg.display_k

        keys = [_multiset_key(d.strategy) for d in results]
        assert len(set(keys)) == len(keys), "Returned set contains duplicate multiset classes"
    finally:
        session.close()


@pytest.mark.integration
def test_win_probabilities_sum_to_one_across_displayed_set():
    """
    Win-probability is the CRN payoff: fraction of shared-scenario races each shape wins.
    Argmin per sim column picks exactly one winner, so the displayed set sums to ~1, every
    value is in [0,1], and the values aren't all identical (some shape wins more often).
    """
    from db.session import SessionLocal
    from app.engine.evaluator import build_context, rank_strategies
    from app.engine.strategy_generator import generate_strategies

    session = SessionLocal()
    try:
        ctx = build_context("bahrain", 57, session)
        ranked = rank_strategies(generate_strategies("bahrain", 57), ctx)
        results = robustness_analysis(ranked, ctx, MonteCarloConfig(n_sims=1000, seed=0), session)

        probs = [r.win_probability for r in results]
        assert all(0.0 <= p <= 1.0 for p in probs)
        assert sum(probs) == pytest.approx(1.0, abs=1e-9)
        assert max(probs) > min(probs), "win-probability should discriminate between shapes"
    finally:
        session.close()


@pytest.mark.integration
def test_bahrain_robustness_completes_under_3s():
    """Performance gate: 200-candidate pool × 2000 sims must stay interactive."""
    import time
    from db.session import SessionLocal
    from app.engine.evaluator import build_context, rank_strategies
    from app.engine.strategy_generator import generate_strategies

    session = SessionLocal()
    try:
        ctx = build_context("bahrain", 57, session)
        ranked = rank_strategies(generate_strategies("bahrain", 57), ctx)
        cfg = MonteCarloConfig(n_sims=2000, seed=0)
        t0 = time.perf_counter()
        robustness_analysis(ranked, ctx, cfg, session)
        elapsed = time.perf_counter() - t0
        assert elapsed < 3.0, f"Robustness analysis took {elapsed:.2f}s (limit: 3s)"
    finally:
        session.close()


@pytest.mark.integration
def test_top_distributions_have_real_spread():
    """Distributions must not be collapsed points — std should be on the order of seconds."""
    from db.session import SessionLocal
    from app.engine.evaluator import build_context, rank_strategies
    from app.engine.strategy_generator import generate_strategies

    session = SessionLocal()
    try:
        ctx = build_context("bahrain", 57, session)
        ranked = rank_strategies(generate_strategies("bahrain", 57), ctx)
        cfg = MonteCarloConfig(n_sims=1000, seed=0)
        results = robustness_analysis(ranked, ctx, cfg, session)
        for d in results:
            assert d.p10_s < d.p90_s, f"{d.strategy.key}: distribution is a point (p10==p90)"
    finally:
        session.close()


@pytest.mark.integration
def test_singapore_wider_than_bahrain():
    """
    Gate 3: Singapore (SC rate 0.28) must produce wider distributions than
    Bahrain (SC rate 0.08). If they look the same, expected_sc_rate is not
    being consulted and Limitation C is not resolved.
    """
    from db.session import SessionLocal
    from app.engine.evaluator import build_context, rank_strategies
    from app.engine.strategy_generator import generate_strategies

    CIRCUITS = {"bahrain": 57, "singapore": 62}

    session = SessionLocal()
    try:
        avg_std: dict[str, float] = {}
        for circuit, total_laps in CIRCUITS.items():
            ctx = build_context(circuit, total_laps, session)
            ranked = rank_strategies(generate_strategies(circuit, total_laps), ctx)
            cfg = MonteCarloConfig(n_sims=1000, seed=0)
            results = robustness_analysis(ranked, ctx, cfg, session)
            avg_std[circuit] = float(np.mean([d.std_s for d in results]))

        assert avg_std["singapore"] > avg_std["bahrain"], (
            f"Singapore avg std ({avg_std['singapore']:.2f}s) should exceed "
            f"Bahrain ({avg_std['bahrain']:.2f}s) — check expected_sc_rate resolver"
        )
    finally:
        session.close()
