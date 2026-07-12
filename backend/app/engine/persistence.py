"""
Persist Stage 4 validation results as a machine-readable JSON artifact and a
human-readable Markdown briefing.

The JSON embeds the Monte Carlo summary (mean/std/percentiles/sc_benefit_freq/seed/
n_simulations) per race so Stages 5 (API) and 8 (PDF report) can render results without
re-running the engine. Raw 2000-sample arrays are deliberately NOT persisted — the summary
is what downstream stages need; anyone wanting histograms can re-simulate from the seed.

Files are written UTF-8 explicitly: the Markdown uses check/cross glyphs, and Python's
default open() encoding on Windows (cp1252) would fail on them.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.engine.validation import RaceValidation, aggregate

_CHECK = "✅"   # ✅
_CROSS = "❌"   # ❌


def race_validation_to_dict(rv: RaceValidation, seed: int) -> dict:
    """Full per-race record for report.json."""
    return {
        "circuit_key": rv.circuit_key,
        "total_laps": rv.total_laps,
        "predicted": rv.predicted.summary(seed),                 # the MC summary schema
        "predicted_pit_laps": list(rv.predicted.strategy.pit_laps),
        "predicted_compounds": [st.compound for st in rv.predicted.strategy.stints],
        "robust_pick_key": rv.robust_pick_key,
        "actual": {
            "winner": rv.actual.driver,
            "pit_laps": list(rv.actual.pit_laps),
            "compounds": list(rv.actual.compounds),
            "n_stops": rv.actual.n_stops,
        },
        "field_median_first_stop": rv.field_median_first_stop,
        "metrics": {
            "stop_count_match": rv.stop_count_match,
            "pit_lap_mae": rv.pit_lap_mae,
            "first_stop_abs_error": rv.first_stop_abs_error,
            "compound_match": rv.compound_match,
        },
        "timing": {
            "predicted_total_s": round(rv.timing.predicted_total_s, 2),
            "actual_total_est_s": round(rv.timing.actual_total_est_s, 2),
            "time_error_s": round(rv.timing.time_error_s, 2),
            "green_lap_median_s": round(rv.timing.green_lap_median_s, 3),
            "lap_coverage": round(rv.timing.lap_coverage, 3),
        },
        "flags": list(rv.flags),
        "explanation": rv.candidate_explanation,
    }


def _fmt_pits(pits) -> str:
    return "/".join(str(p) for p in pits) if pits else "-"


def _mark(ok: bool) -> str:
    return _CHECK if ok else _CROSS


def _compound_mark(match: str) -> str:
    """Three-state: exact sequence, same compounds reordered (partial), or different set."""
    return {"exact": _CHECK, "partial": "~", "mismatch": _CROSS}.get(match, _CROSS)


def _summary_table(results: list[RaceValidation]) -> str:
    """The concise at-a-glance table: Race | Stops | Pit MAE | Compound | Timing | Explanation."""
    rows = [
        "| Race | Stop Count | Pit MAE | Compound | Timing Err | Explanation |",
        "|------|:----------:|:-------:|:--------:|:----------:|-------------|",
    ]
    for r in results:
        mae = f"{r.pit_lap_mae:.1f} laps" if r.pit_lap_mae is not None else "N/A"
        terr = f"{r.timing.time_error_s:+.1f} s" if r.timing.time_error_s == r.timing.time_error_s else "N/A"
        rows.append(
            f"| {r.circuit_key.title()} "
            f"| {_mark(r.stop_count_match)} "
            f"| {mae} "
            f"| {_compound_mark(r.compound_match)} "
            f"| {terr} "
            f"| {r.candidate_explanation} |"
        )
    return "\n".join(rows) + "\n\n_Compound: " + _CHECK + " exact sequence · ~ same compounds reordered · " + _CROSS + " different compounds_"


def _timing_table(results: list[RaceValidation]) -> str:
    """Independent timing-model axis: predicted vs reconstructed actual."""
    rows = [
        "| Race | Predicted (s) | Actual est. (s) | Error (s) | Lap coverage |",
        "|------|--------------:|----------------:|----------:|:------------:|",
    ]
    for r in results:
        t = r.timing
        if t.time_error_s != t.time_error_s:   # NaN
            rows.append(f"| {r.circuit_key.title()} | - | - | N/A | {t.lap_coverage:.0%} |")
            continue
        rows.append(
            f"| {r.circuit_key.title()} "
            f"| {t.predicted_total_s:.1f} "
            f"| {t.actual_total_est_s:.1f} "
            f"| {t.time_error_s:+.1f} "
            f"| {t.lap_coverage:.0%} |"
        )
    return "\n".join(rows)


def _detailed_misses(results: list[RaceValidation], top_n: int = 3) -> str:
    """Prose scaffolding for the largest disagreements, ranked by first-stop error."""
    ranked = sorted(results, key=lambda r: r.first_stop_abs_error, reverse=True)[:top_n]
    blocks: list[str] = []
    for r in ranked:
        pred_seq = "-".join(st.compound[0] for st in r.predicted.strategy.stints)
        act_seq = "-".join(c[0] for c in r.actual.compounds)
        block = [
            f"### {r.circuit_key.title()} — first-stop error {r.first_stop_abs_error} laps",
            "",
            f"- **Engine (deterministic top-1):** `{r.predicted.strategy.key}` "
            f"({pred_seq}), stops at {_fmt_pits(r.predicted.strategy.pit_laps)}",
            f"- **Actual winner ({r.actual.driver}):** {act_seq}, "
            f"stops at {_fmt_pits(r.actual.pit_laps)}",
            f"- **Robust pick (Stage 3):** `{r.robust_pick_key}`"
            + ("  _(differs from deterministic headline)_"
               if r.robust_pick_key != r.predicted.strategy.key else ""),
            f"- **Field median first stop:** lap {r.field_median_first_stop:.0f}",
            f"- **Timing axis:** predicted {r.timing.predicted_total_s:.1f}s vs "
            f"actual est. {r.timing.actual_total_est_s:.1f}s "
            f"({r.timing.time_error_s:+.1f}s)",
        ]
        if r.flags:
            block.append("- **Data-driven flags:**")
            block.extend(f"  - {f}" for f in r.flags)
        block += [
            "",
            f"_Candidate explanation: **{r.candidate_explanation}.**_ "
            "The engine optimizes free-air pace and does not model track position, traffic "
            "or the undercut — so an earlier real stop is expected where those forces dominate. "
            "<!-- Add hand-written analysis here. -->",
            "",
        ]
        blocks.append("\n".join(block))
    return "\n".join(blocks)


def build_markdown(results: list[RaceValidation], agg: dict) -> str:
    lines = [
        "# Stage 4 — Historical Validation Report",
        "",
        "The engine optimizes **free-air race time**: it ignores track position, traffic and "
        "the undercut. It is therefore *expected* to disagree with what teams actually did — and "
        "those disagreements, explained below, are the point of this stage. Validation runs over "
        "the cached races the engine can generate for; Australia is excluded (only one compound "
        "survives the data gate).",
        "",
        "## At a glance",
        "",
        _summary_table(results),
        "",
        "**Aggregate** — "
        f"pit-lap MAE (stop-count matches): "
        f"**{agg['pit_lap_mae'] if agg['pit_lap_mae'] is not None else 'N/A'} laps** · "
        f"first-stop MAE: **{agg['first_stop_mae']} laps** · "
        f"stop-count mismatches: **{agg['stop_count_mismatches']}/{agg['races_validated']}** · "
        f"exact compound matches: **{agg['compound_exact_matches']}/{agg['races_validated']}** · "
        f"mean abs timing error: **{agg['mean_abs_time_error_s']} s**",
        "",
        "## Timing-model axis (independent of strategy choice)",
        "",
        "Predicted total vs a free-air reconstruction of the winner's time "
        "(`median green lap × laps + stops × pit-loss`). Both sides are free-air, so this "
        "isolates the pace/degradation model from the strategy recommendation.",
        "",
        _timing_table(results),
        "",
        "## Largest disagreements",
        "",
        _detailed_misses(results),
    ]
    return "\n".join(lines)


def save_validation_report(
    results: list[RaceValidation],
    out_dir: str | Path,
    seed: int,
) -> tuple[Path, Path]:
    """Write report.json and report.md. Returns their paths."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    agg = aggregate(results)
    payload = {
        "aggregate": agg,
        "races": [race_validation_to_dict(r, seed) for r in results],
    }

    json_path = out / "report.json"
    md_path = out / "report.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(results, agg), encoding="utf-8")
    return json_path, md_path


def load_validation_report(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
