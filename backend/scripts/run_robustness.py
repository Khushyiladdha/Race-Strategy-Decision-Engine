"""
Robustness analysis demo — textual precursor to the Confidence Ribbon.

Usage:
    python scripts/run_robustness.py bahrain
    python scripts/run_robustness.py singapore --metric p90_s
    python scripts/run_robustness.py bahrain singapore  # compare two circuits
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse

from db.models import Race
from db.session import SessionLocal
from app.engine.evaluator import build_context, rank_strategies
from app.engine.monte_carlo import MonteCarloConfig, _multiset_key, robustness_analysis
from app.engine.strategy_generator import can_generate, generate_strategies
from app.models.safety_car import SC_RATE_PER_LAP, _MIN_RACES_FOR_ESTIMATE, expected_sc_rate

CIRCUIT_LAPS: dict[str, int] = {
    "bahrain": 57,
    "spanish": 66,
    "singapore": 62,
    "austrian": 71,
    "japanese": 53,
    "australian": 58,
}


def _sc_rate_source(circuit: str, session) -> tuple[float, str]:
    """Return (rate, source_label) for display."""
    key = circuit.lower()
    n_races = session.query(Race).filter(Race.circuit_key == key).count()
    if n_races >= _MIN_RACES_FOR_ESTIMATE:
        rate = expected_sc_rate(circuit, session)
        return rate, "empirical"
    rate = expected_sc_rate(circuit, session)
    if key in SC_RATE_PER_LAP:
        return rate, "assumed (table)"
    return rate, "assumed (global default)"


def run_for_circuit(circuit: str, total_laps: int, cfg: MonteCarloConfig, session) -> None:
    ok, reason = can_generate(circuit)
    if not ok:
        print(f"\n[SKIP] {circuit}: {reason}")
        return

    p_sc, source = _sc_rate_source(circuit, session)
    print(f"\n{'='*70}")
    print(f"Circuit : {circuit}   Laps: {total_laps}   SC rate/lap: {p_sc:.3f} ({source})")
    print(f"Metric  : {cfg.robust_metric}   Sims: {cfg.n_sims}   Pool: <={cfg.max_candidates}")
    print(f"{'='*70}")

    ctx = build_context(circuit, total_laps, session)
    strategies = generate_strategies(circuit, total_laps)
    ranked = rank_strategies(strategies, ctx)

    t0 = time.perf_counter()
    distributions = robustness_analysis(ranked, ctx, cfg, session)
    elapsed = time.perf_counter() - t0

    print(f"\n{'shape key':<22} {'det(s)':>8} {'mean':>8} {'std':>6} "
          f"{'P10':>8} {'P50':>8} {'P90':>8} {'sc_freq':>8}")
    print("-" * 84)
    for d in distributions:
        print(
            f"{d.strategy.key:<22}"
            f"{d.deterministic_time_s:>8.1f}"
            f"{d.mean_s:>8.1f}"
            f"{d.std_s:>6.1f}"
            f"{d.p10_s:>8.1f}"
            f"{d.p50_s:>8.1f}"
            f"{d.p90_s:>8.1f}"
            f"{d.sc_benefit_freq:>8.3f}"
        )

    print(f"\nReturned {len(distributions)} distinct shape(s) in {elapsed:.2f}s")
    if len(distributions) >= 2:
        spread_ms = (distributions[-1].mean_s - distributions[0].mean_s) * 1000
        print(f"Mean spread across top shapes: {spread_ms:.0f} ms")

    # Quick sanity: confirm all multisets are distinct
    keys = [_multiset_key(d.strategy) for d in distributions]
    if len(set(keys)) != len(keys):
        print("[WARNING] Duplicate multiset classes in results — dedup logic may be broken")
    else:
        print("Multiset dedup: OK (all shapes are distinct equivalence classes)")


def main() -> None:
    parser = argparse.ArgumentParser(description="F1 strategy robustness analysis")
    parser.add_argument(
        "circuits",
        nargs="+",
        metavar="CIRCUIT",
        help=f"Circuit key(s). Known: {sorted(CIRCUIT_LAPS)}",
    )
    parser.add_argument("--metric", default="mean_s", choices=["mean_s", "p90_s"])
    parser.add_argument("--sims", type=int, default=2000)
    parser.add_argument("--display", type=int, default=8, help="Number of shapes to show")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    cfg = MonteCarloConfig(
        n_sims=args.sims,
        seed=args.seed,
        robust_metric=args.metric,
        display_k=args.display,
    )

    session = SessionLocal()
    try:
        for circuit in args.circuits:
            circuit = circuit.lower()
            total_laps = CIRCUIT_LAPS.get(circuit)
            if total_laps is None:
                print(f"[SKIP] Unknown circuit '{circuit}'. Known: {sorted(CIRCUIT_LAPS)}")
                continue
            run_for_circuit(circuit, total_laps, cfg, session)
    finally:
        session.close()


if __name__ == "__main__":
    main()
