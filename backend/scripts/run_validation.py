"""
Stage 4 — historical validation runner.

Runs the full engine on every cached race the engine can generate for, compares its top
recommendation to the actual winner, prints a predicted-vs-actual table, and writes
data/validation/report.{json,md}.

Usage:
    python scripts/run_validation.py
    python scripts/run_validation.py --sims 5000 --seed 42
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.session import SessionLocal
from app.engine.monte_carlo import MonteCarloConfig
from app.engine.persistence import save_validation_report
from app.engine.validation import aggregate, validate_all


def _pits(pits) -> str:
    return "/".join(str(p) for p in pits) if pits else "-"


def main() -> None:
    parser = argparse.ArgumentParser(description="F1 engine historical validation")
    parser.add_argument("--sims", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", default="data/validation", help="output directory")
    args = parser.parse_args()

    cfg = MonteCarloConfig(n_sims=args.sims, seed=args.seed)

    session = SessionLocal()
    try:
        results = validate_all(session, cfg)
        if not results:
            print("No races could be validated (none generatable).")
            return

        header = (
            f"{'circuit':<12}{'pred stops':>11}{'act stops':>10}"
            f"{'pred pits':>12}{'act pits':>12}"
            f"{'1st err':>8}{'MAE':>7}{'cmp':>9}{'timeErr':>9}  explanation"
        )
        print(header)
        print("-" * len(header))
        for r in results:
            mae = f"{r.pit_lap_mae:.1f}" if r.pit_lap_mae is not None else "N/A"
            terr = f"{r.timing.time_error_s:+.1f}" if r.timing.time_error_s == r.timing.time_error_s else "N/A"
            print(
                f"{r.circuit_key:<12}"
                f"{r.predicted.strategy.n_stops:>11}"
                f"{r.actual.n_stops:>10}"
                f"{_pits(r.predicted.strategy.pit_laps):>12}"
                f"{_pits(r.actual.pit_laps):>12}"
                f"{r.first_stop_abs_error:>8}"
                f"{mae:>7}"
                f"{r.compound_match:>9}"
                f"{terr:>9}"
                f"  {r.candidate_explanation}"
            )

        agg = aggregate(results)
        print()
        print(f"Races validated        : {agg['races_validated']}")
        print(f"Pit-lap MAE (matched)  : {agg['pit_lap_mae']} laps")
        print(f"First-stop MAE         : {agg['first_stop_mae']} laps")
        print(f"Stop-count mismatches  : {agg['stop_count_mismatches']}/{agg['races_validated']}")
        print(f"Compound exact matches : {agg['compound_exact_matches']}/{agg['races_validated']}")
        print(f"Mean abs timing error  : {agg['mean_abs_time_error_s']} s "
              f"(signed {agg['mean_signed_time_error_s']:+} s)")

        json_path, md_path = save_validation_report(results, args.out, seed=cfg.seed)
        print()
        print(f"Wrote {json_path}")
        print(f"Wrote {md_path}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
