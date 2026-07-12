"""
Exhaustive enumeration of legal pit strategies.

The search space is 21k-45k strategies per race -- small enough to evaluate
every one in well under a second. No solver, no heuristic search.
"""
import sys
from dataclasses import dataclass
from itertools import product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.tyre_degradation import available_compounds

MIN_STINT_LAPS = 5

_ABBREV = {"SOFT": "S", "MEDIUM": "M", "HARD": "H"}
_EXPAND = {v: k for k, v in _ABBREV.items()}


@dataclass(frozen=True)
class Stint:
    compound: str
    start_lap: int  # inclusive, 1-based
    end_lap: int    # inclusive

    @property
    def length(self) -> int:
        return self.end_lap - self.start_lap + 1


@dataclass(frozen=True)
class Strategy:
    stints: tuple[Stint, ...]

    @property
    def pit_laps(self) -> tuple[int, ...]:
        """Laps on which the car pits -- the last lap of every stint but the final one."""
        return tuple(s.end_lap for s in self.stints[:-1])

    @property
    def n_stops(self) -> int:
        return len(self.stints) - 1

    @property
    def key(self) -> str:
        """
        Stable, serializable identifier: 'S-H@18' or 'S-M-H@14,32'.

        Derived, never stored, so it cannot drift from the stints. Compound sequence
        plus pit laps uniquely determines a strategy for a fixed total_laps, since
        stints tile 1..N with no gaps. Monte Carlo, the API and the frontend all key
        off this -- the dataclass hash is salted per-process and won't serialize.
        """
        compounds = "-".join(_ABBREV[s.compound] for s in self.stints)
        laps = ",".join(str(p) for p in self.pit_laps)
        return f"{compounds}@{laps}"


def parse_key(key: str) -> tuple[tuple[str, ...], tuple[int, ...]]:
    """Inverse of Strategy.key. Returns (compounds, pit_laps)."""
    compounds_part, _, laps_part = key.partition("@")
    compounds = tuple(_EXPAND[c] for c in compounds_part.split("-"))
    pit_laps = tuple(int(x) for x in laps_part.split(",")) if laps_part else ()
    return compounds, pit_laps


def _build(compounds: tuple[str, ...], pit_laps: tuple[int, ...], total_laps: int) -> Strategy:
    """Tile laps 1..total_laps into stints split at pit_laps."""
    bounds = (0,) + pit_laps + (total_laps,)
    stints = tuple(
        Stint(compound=c, start_lap=bounds[i] + 1, end_lap=bounds[i + 1])
        for i, c in enumerate(compounds)
    )
    return Strategy(stints=stints)


def can_generate(circuit_key: str) -> tuple[bool, str]:
    """
    Whether this circuit has enough compound data to build any legal strategy.

    Red-flagged races fragment stints: 2023 Australian shows 12 MEDIUM "stints" of
    exactly 3 laps (restart artifacts) and only 2 real ones, so MEDIUM is excluded
    and only HARD survives. Such a circuit cannot satisfy the two-compound rule.
    Callers enumerating circuits should skip these with the reason, not crash.
    """
    compounds = available_compounds(circuit_key)
    if len(compounds) < 2:
        return False, (
            f"only {len(compounds)} compound(s) with sufficient data "
            f"({', '.join(compounds) or 'none'}); cannot satisfy the two-compound rule"
        )
    return True, f"{len(compounds)} compounds: {', '.join(compounds)}"


def generate_strategies(
    circuit_key: str,
    total_laps: int,
    *,
    min_stint_laps: int = MIN_STINT_LAPS,
) -> list[Strategy]:
    """
    Every legal 1-stop and 2-stop strategy for this circuit.

    Legality:
      1. 1 or 2 stops only
      2. >= 2 distinct compounds (FIA dry-race rule)
      3. every stint >= min_stint_laps
      4. stints tile 1..total_laps, pit laps strictly increasing
      5. compound has enough real data at this circuit -- fallback coefficients
         are guesses, and must never reach the evaluator
    """
    ok, reason = can_generate(circuit_key)
    if not ok:
        raise ValueError(f"{circuit_key}: {reason}")

    compounds = available_compounds(circuit_key)
    out: list[Strategy] = []

    # 1-stop: one pit lap, two stints
    for pit in range(min_stint_laps, total_laps - min_stint_laps + 1):
        for combo in product(compounds, repeat=2):
            if len(set(combo)) < 2:
                continue
            out.append(_build(combo, (pit,), total_laps))

    # 2-stop: two pit laps, three stints
    for p1 in range(min_stint_laps, total_laps - 2 * min_stint_laps + 1):
        for p2 in range(p1 + min_stint_laps, total_laps - min_stint_laps + 1):
            for combo in product(compounds, repeat=3):
                if len(set(combo)) < 2:
                    continue
                out.append(_build(combo, (p1, p2), total_laps))

    return out
