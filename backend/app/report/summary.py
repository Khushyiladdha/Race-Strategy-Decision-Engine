"""
Plain-English observations for the report — shared by the on-screen ReportView and the PDF, so the
two never drift. Pure functions over the API schemas; no PDF/WeasyPrint dependency here.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.api import schemas

_SIMILAR_SPREAD_S = 0.3  # top strategies within this are effectively tied


def _title(compound: str) -> str:
    return compound[:1] + compound[1:].lower()


def executive_summary(
    recommendation: schemas.StrategyOut,
    validation: schemas.ValidationDetailOut,
) -> str:
    comps = "–".join(_title(c) for c in recommendation.compounds)
    multi = len(recommendation.pit_laps) > 1
    pits = " and ".join(str(p) for p in recommendation.pit_laps)
    finish = _format_race_time(recommendation.distribution.mean_s)
    win = f"{round(recommendation.win_probability * 100)}%"

    mae = validation.metrics.pit_lap_mae
    if mae is None:
        validation_part = (
            "Historical validation shows the engine and the actual winner ran a different "
            "number of stops at this circuit"
        )
    else:
        validation_part = (
            f"Historical validation indicates a mean pit-lap error of {mae:g} "
            f"lap{'' if mae == 1 else 's'} at this circuit"
        )
    reason = f" ({validation.explanation.lower()})" if validation.explanation else ""

    return (
        f"The engine recommends a {comps} strategy with pit {'stops' if multi else 'stop'} on "
        f"lap{'s' if multi else ''} {pits}. {validation_part}{reason}. Under the current "
        f"assumptions this strategy has the highest expected performance — a {win} win probability "
        f"and an expected finish of {finish}."
    )


def confidence_note(strategies: list[schemas.StrategyOut]) -> str:
    """Interpret the headline win-probability using the real top-two spread."""
    top = strategies[0]
    spread = (
        strategies[1].distribution.mean_s - top.distribution.mean_s
        if len(strategies) > 1
        else float("inf")
    )
    if spread < _SIMILAR_SPREAD_S:
        return (
            f"Multiple strategies perform similarly (<{_SIMILAR_SPREAD_S:g} s spread). "
            "Treat the recommendation as a preference rather than a certainty."
        )
    if top.win_probability >= 0.5:
        return "Dominant strategy identified — it wins the majority of simulated races."
    return "A clear front-runner, though several alternatives remain competitive."


def _format_race_time(seconds: float) -> str:
    total = round(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"
