"""
Fit degradation curves for every circuit x compound pair and report availability.

Usage:
    python scripts/fit_all.py
"""
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.models import Race
from db.session import SessionLocal
from app.models.tyre_degradation import fit_degradation, is_compound_available

COMPOUNDS = ["SOFT", "MEDIUM", "HARD"]


def main() -> None:
    session = SessionLocal()
    try:
        circuits = [r.circuit_key for r in session.query(Race).order_by(Race.round).all()]

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for circuit in circuits:
                for compound in COMPOUNDS:
                    fit_degradation(circuit, compound, session)

        print(f"{'circuit':<12}{'compound':<10}{'stints':>7}{'laps':>7}{'rmse':>8}"
              f"{'a':>10}{'b':>11}  {'status'}")
        print("-" * 88)

        excluded = []
        for circuit in circuits:
            for compound in COMPOUNDS:
                from app.models.tyre_degradation import load_params
                p = load_params(circuit, compound)
                ok, reason = is_compound_available(circuit, compound)
                if not ok:
                    excluded.append((circuit, compound, reason))
                status = "available" if ok else f"EXCLUDED ({reason})"
                rmse = p.get("fit_rmse", float("nan"))
                print(f"{circuit:<12}{compound:<10}{p.get('n_stints', 0):>7}"
                      f"{p['n_laps_fit']:>7}{rmse:>8.3f}{p['a']:>10.5f}{p['b']:>11.6f}  {status}")

        print()
        print(f"{len(excluded)} compound(s) excluded from the optimizer:")
        for circuit, compound, reason in excluded:
            print(f"  {circuit}/{compound}: {reason}")

        print()
        print("Circuit readiness for strategy generation:")
        from app.engine.strategy_generator import can_generate
        for circuit in circuits:
            ok, reason = can_generate(circuit)
            print(f"  [{'OK ' if ok else 'SKIP'}] {circuit:<12} {reason}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
