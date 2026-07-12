import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api import schemas
from app.report.renderer import ReportMeta, render_report_html, stint_svg, stints_from
from app.report.summary import confidence_note, executive_summary


# --- fixtures --------------------------------------------------------------

def _strat(mean: float, win: float, compounds=None, pit_laps=None) -> schemas.StrategyOut:
    compounds = compounds or ["SOFT", "SOFT", "HARD"]
    pit_laps = pit_laps or [14, 36]
    return schemas.StrategyOut(
        key="X",
        n_stops=len(pit_laps),
        pit_laps=pit_laps,
        compounds=compounds,
        win_probability=win,
        histogram=[0] * 32,
        breakdown=schemas.Breakdown(
            base_s=0, compound_offset_s=0, degradation_s=0, fuel_s=0, pit_s=0, total_s=0
        ),
        distribution=schemas.DistributionOut(
            mean_s=mean, std_s=0, p10_s=0, p50_s=0, p90_s=0, best_s=0, worst_s=0,
            sc_benefit_freq=0, n_sims=0,
        ),
    )


def _validation(mae, explanation="Same compounds, reordered") -> schemas.ValidationDetailOut:
    return schemas.ValidationDetailOut(
        circuit_key="bahrain",
        total_laps=57,
        predicted=schemas.PredictedSummaryOut(
            strategy_key="X", deterministic_time_s=0, mean_s=0, std_s=0, p10_s=0, p50_s=0,
            p90_s=0, sc_benefit_freq=0, seed=0, n_simulations=0,
        ),
        predicted_pit_laps=[14, 36],
        predicted_compounds=["SOFT", "SOFT", "HARD"],
        robust_pick_key="X",
        actual=schemas.ActualStrategyOut(
            winner="VER", pit_laps=[14, 36], compounds=["SOFT", "SOFT", "HARD"], n_stops=2
        ),
        field_median_first_stop=15,
        metrics=schemas.ValidationMetricsOut(
            stop_count_match=True, pit_lap_mae=mae, first_stop_abs_error=2, compound_match="partial"
        ),
        timing=schemas.TimingAxisOut(
            predicted_total_s=0, actual_total_est_s=0, time_error_s=0, green_lap_median_s=0,
            lap_coverage=0.9,
        ),
        flags=[],
        explanation=explanation,
    )


_META = ReportMeta(generated="2026-07-12", engine_version="0.5.0", n_sims=2000, seed=0, ranking="Mean")


# --- stint geometry --------------------------------------------------------

def test_stints_from_tiles_the_race():
    assert stints_from([14, 36], ["SOFT", "SOFT", "HARD"], 57) == [
        ("SOFT", 1, 14),
        ("SOFT", 15, 36),
        ("HARD", 37, 57),
    ]


def test_stint_svg_one_rect_per_stint():
    svg = stint_svg(stints_from([14, 36], ["SOFT", "SOFT", "HARD"], 57), 57)
    assert svg.count("<rect") == 3
    assert svg.startswith("<svg")


# --- executive summary -----------------------------------------------------

def test_executive_summary_plural_and_compounds():
    s = executive_summary(_strat(5651, 0.13, ["SOFT", "MEDIUM", "SOFT"], [24, 43]), _validation(9))
    assert "Soft–Medium–Soft" in s
    assert "pit stops on laps 24 and 43" in s
    assert "mean pit-lap error of 9 laps" in s


def test_executive_summary_singular_lap():
    s = executive_summary(_strat(5651, 0.13), _validation(1))
    assert "error of 1 lap " in s  # trailing space => not "laps"


def test_executive_summary_null_mae_branch():
    s = executive_summary(_strat(5651, 0.13), _validation(None))
    assert "different number of stops" in s


# --- confidence note -------------------------------------------------------

def test_confidence_note_similar_when_tight():
    note = confidence_note([_strat(5651.0, 0.13), _strat(5651.05, 0.12)])
    assert "similarly" in note and "preference" in note


def test_confidence_note_dominant_when_clear_and_winning():
    note = confidence_note([_strat(5651.0, 0.6), _strat(5654.0, 0.2)])
    assert "Dominant" in note


def test_confidence_note_frontrunner_middle():
    note = confidence_note([_strat(5651.0, 0.3), _strat(5654.0, 0.2)])
    assert "front-runner" in note


# --- integration -----------------------------------------------------------

@pytest.mark.integration
def test_build_report_carries_summary_and_note():
    from db.session import SessionLocal

    session = SessionLocal()
    try:
        report = services_build(session, "bahrain")
        assert "recommends" in report.executive_summary
        assert report.confidence_note
    finally:
        session.close()


@pytest.mark.integration
def test_render_report_html_contains_sections():
    from db.session import SessionLocal

    session = SessionLocal()
    try:
        report = services_build(session, "bahrain")
        html = render_report_html(report, _META)
        for needle in ("Race Strategy Report", "Executive summary", "VER", "<svg", "Monte Carlo"):
            assert needle in html
    finally:
        session.close()


@pytest.mark.integration
def test_render_report_pdf_produces_pdf_bytes():
    """Skips where WeasyPrint's native stack is absent (Windows); runs in Docker/Linux."""
    pytest.importorskip("weasyprint")
    from db.session import SessionLocal
    from app.report.renderer import render_report_pdf

    session = SessionLocal()
    try:
        report = services_build(session, "bahrain")
        pdf = render_report_pdf(report, _META)
        assert pdf[:4] == b"%PDF"
    finally:
        session.close()


def services_build(session, circuit: str) -> schemas.ReportResponse:
    from app.api import services

    return services.build_report(session, schemas.ReportRequest(circuit_key=circuit, n_sims=300))
