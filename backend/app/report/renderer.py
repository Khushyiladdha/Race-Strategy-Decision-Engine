"""
Report rendering: Jinja2 HTML (always available) and WeasyPrint PDF (lazy — its native stack is
only needed when actually writing a PDF, so this module imports fine on Windows without it).
"""
import sys
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.api import schemas
from app.report import style

_env = Environment(
    loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
    autoescape=select_autoescape(["html", "xml", "j2"]),
)


@dataclass(frozen=True)
class ReportMeta:
    generated: str        # ISO date, e.g. 2026-07-12
    engine_version: str
    n_sims: int
    seed: int
    ranking: str          # "Mean" | "P90"


# --- geometry --------------------------------------------------------------

def stints_from(pit_laps: list[int], compounds: list[str], total_laps: int):
    """(compound, start_lap, end_lap) tuples — mirrors the backend/frontend stint tiling."""
    bounds = [0, *pit_laps, total_laps]
    return [
        (compounds[i], bounds[i] + 1, bounds[i + 1]) for i in range(len(compounds))
    ]


def stint_svg(stints, total_laps: int, width: int = 520, height: int = 56) -> str:
    """Inline SVG gantt matching the on-screen timeline — one bar per stint, pit gaps, lap axis."""
    pad, bar_top, bar_h, pit_gap = 8, 20, 24, 5

    def x(lap: float) -> float:
        return pad + (lap / total_laps) * (width - 2 * pad)

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%">'
    ]
    for i, (compound, start, end) in enumerate(stints):
        c = style.COMPOUND[compound]
        is_last = i == len(stints) - 1
        x0 = x(start - 1)
        x1 = x(end) - (0 if is_last else pit_gap)
        w = max(0.0, x1 - x0)
        laps = end - start + 1
        stroke = "" if c["stroke"] == "none" else f' stroke="{c["stroke"]}" stroke-width="1"'
        parts.append(
            f'<text x="{x0:.1f}" y="12" font-size="8" fill="{style.MUTED}" '
            f'font-family="monospace">{compound} · {laps}L</text>'
        )
        parts.append(
            f'<rect x="{x0:.1f}" y="{bar_top}" width="{w:.1f}" height="{bar_h}" rx="3" '
            f'fill="{c["fill"]}"{stroke} />'
        )
        if w > 12:
            parts.append(
                f'<text x="{x0 + w / 2:.1f}" y="{bar_top + bar_h / 2:.1f}" font-size="12" '
                f'fill="{c["text"]}" font-family="monospace" text-anchor="middle" '
                f'dominant-baseline="central">{c["letter"]}</text>'
            )

    ticks = list(range(0, total_laps + 1, 10))
    if ticks[-1] != total_laps:
        ticks.append(total_laps)
    for t in ticks:
        parts.append(
            f'<line x1="{x(t):.1f}" y1="{bar_top + bar_h}" x2="{x(t):.1f}" '
            f'y2="{bar_top + bar_h + 3}" stroke="{style.HAIRLINE}" stroke-width="1" />'
        )
        parts.append(
            f'<text x="{x(t):.1f}" y="{height - 4}" font-size="8" fill="{style.AXIS}" '
            f'font-family="monospace" text-anchor="middle">{t}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


# --- rendering -------------------------------------------------------------

def _format_race_time(seconds: float) -> str:
    total = round(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"


def _context(report: schemas.ReportResponse, meta: ReportMeta) -> dict:
    rec = report.recommendation
    v = report.validation
    chips = [
        {**style.COMPOUND[c]}
        for c in rec.compounds
    ]
    return {
        "report": report,
        "meta": meta,
        "style": style,
        "chips": chips,
        "finish": _format_race_time(rec.distribution.mean_s),
        "win_pct": round(rec.win_probability * 100),
        "sc_pct": round(report.recommendation.distribution.sc_benefit_freq * 100),
        "timing_err": f"{v.timing.time_error_s:+.1f}",
        "rec_svg": stint_svg(stints_from(rec.pit_laps, rec.compounds, v.total_laps), v.total_laps),
        "engine_svg": stint_svg(
            stints_from(v.predicted_pit_laps, v.predicted_compounds, v.total_laps), v.total_laps
        ),
        "actual_svg": stint_svg(
            stints_from(v.actual.pit_laps, v.actual.compounds, v.total_laps), v.total_laps
        ),
    }


def render_report_html(report: schemas.ReportResponse, meta: ReportMeta) -> str:
    return _env.get_template("report.html.j2").render(**_context(report, meta))


def render_report_pdf(report: schemas.ReportResponse, meta: ReportMeta) -> bytes:
    """HTML -> PDF via WeasyPrint. Imported lazily so this module loads without the native stack."""
    from weasyprint import HTML  # noqa: PLC0415 — deliberate lazy import

    html = render_report_html(report, meta)
    return HTML(string=html).write_pdf()
