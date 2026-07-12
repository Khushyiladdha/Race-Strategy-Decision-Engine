import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.engine.monte_carlo import MonteCarloConfig
from app.engine.validation import (
    ActualStrategy,
    _compound_match,
    _pit_lap_error,
    dedup_pit_laps,
)


# ---------------------------------------------------------------------------
# Pure-function unit tests (no DB)
# ---------------------------------------------------------------------------

def test_dedup_collapses_in_out_lap_pairs():
    """The PitStop double-count: [14,15,36,37] is a real 2-stop at 14 and 36."""
    assert dedup_pit_laps([14, 15, 36, 37]) == [14, 36]


def test_dedup_leaves_clean_stops_untouched():
    assert dedup_pit_laps([18, 40]) == [18, 40]


def test_dedup_handles_unsorted_and_singletons():
    assert dedup_pit_laps([37, 14, 36, 15]) == [14, 36]
    assert dedup_pit_laps([22]) == [22]
    assert dedup_pit_laps([]) == []


def test_dedup_collapses_triple_runs():
    """A 3-lap run (rare, but possible) still collapses to a single stop."""
    assert dedup_pit_laps([20, 21, 22, 45]) == [20, 45]


# --- pit-lap error math ----------------------------------------------------

def test_mae_when_stop_counts_match():
    mae, first = _pit_lap_error((20, 41), (14, 36))
    assert mae == pytest.approx((6 + 5) / 2)
    assert first == 6


def test_mae_is_none_when_stop_counts_differ():
    """A 1-stop vs a 2-stop can't have a well-defined pit MAE; first-stop error still counts."""
    mae, first = _pit_lap_error((25,), (14, 36))
    assert mae is None
    assert first == 11


def test_first_stop_error_zero_when_no_stops():
    mae, first = _pit_lap_error((), ())
    assert mae == 0.0
    assert first == 0


def test_mae_sorts_before_pairing():
    """Order of pit laps shouldn't matter — stops are compared smallest-to-smallest."""
    mae, _ = _pit_lap_error((41, 20), (36, 14))
    assert mae == pytest.approx((6 + 5) / 2)


# --- compound-match classifier ---------------------------------------------

def test_compound_match_exact():
    assert _compound_match(("SOFT", "HARD"), ("SOFT", "HARD")) == "exact"


def test_compound_match_partial_same_set_different_order():
    assert _compound_match(("SOFT", "HARD"), ("HARD", "SOFT")) == "partial"


def test_compound_match_partial_different_length_same_set():
    assert _compound_match(("SOFT", "SOFT", "HARD"), ("SOFT", "HARD")) == "partial"


def test_compound_match_mismatch_different_set():
    assert _compound_match(("SOFT", "HARD"), ("MEDIUM", "HARD")) == "mismatch"


# --- ActualStrategy dataclass ----------------------------------------------

def test_actual_strategy_exposes_compound_sequence():
    a = ActualStrategy(
        driver="VER",
        stints=(("SOFT", 14), ("SOFT", 22), ("HARD", 21)),
        pit_laps=(14, 36),
        n_stops=2,
    )
    assert a.compounds == ("SOFT", "SOFT", "HARD")
    assert a.n_stops == 2


# ---------------------------------------------------------------------------
# Integration tests (require populated Postgres)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_extract_bahrain_winner_matches_known_result():
    """VER won 2023 Bahrain on SOFT-SOFT-HARD, stopping at 14 and 36."""
    from db.session import SessionLocal
    from app.engine.validation import extract_actual_strategy

    session = SessionLocal()
    try:
        a = extract_actual_strategy("bahrain", "VER", session)
        assert a is not None
        assert a.n_stops == 2
        assert a.compounds == ("SOFT", "SOFT", "HARD")
        assert a.pit_laps == (14, 36)
    finally:
        session.close()


@pytest.mark.integration
def test_detect_sc_laps_returns_a_contiguous_looking_set():
    from db.session import SessionLocal
    from app.engine.validation import detect_sc_laps

    session = SessionLocal()
    try:
        sc = detect_sc_laps("singapore", session)   # SC-heavy race
        assert isinstance(sc, set)
        # Singapore 2023 had neutralizations; expect at least some flagged laps
        assert all(isinstance(x, int) and x >= 1 for x in sc)
    finally:
        session.close()


@pytest.mark.integration
def test_validate_bahrain_shows_explainable_disagreement():
    """
    The engine's free-air optimum stops later than VER's real undercut. This must show up
    as a non-zero first-stop error, not a spurious perfect match.
    """
    from db.session import SessionLocal
    from app.engine.validation import validate_race

    session = SessionLocal()
    try:
        cfg = MonteCarloConfig(n_sims=500, seed=0)
        rv = validate_race("bahrain", session, cfg)
        assert rv is not None
        assert rv.actual.driver == "VER"
        assert rv.first_stop_abs_error > 0, "engine should not exactly match VER's undercut"
        # timing axis populated and plausible
        assert rv.timing.actual_total_est_s > 0
        assert 0.5 < rv.timing.lap_coverage <= 1.0
    finally:
        session.close()


@pytest.mark.integration
def test_australian_is_skipped():
    """Engine cannot generate at Australia; validate_race returns None, not a crash."""
    from db.session import SessionLocal
    from app.engine.validation import validate_race

    session = SessionLocal()
    try:
        cfg = MonteCarloConfig(n_sims=200, seed=0)
        assert validate_race("australian", session, cfg) is None
    finally:
        session.close()


@pytest.mark.integration
def test_validate_all_produces_finite_aggregate():
    from db.session import SessionLocal
    from app.engine.validation import aggregate, validate_all

    session = SessionLocal()
    try:
        cfg = MonteCarloConfig(n_sims=300, seed=0)
        results = validate_all(session, cfg)
        assert len(results) >= 4          # 5 generatable races (Australia excluded)
        agg = aggregate(results)
        assert agg["races_validated"] == len(results)
        assert agg["first_stop_mae"] is not None
        assert agg["mean_abs_time_error_s"] is not None
    finally:
        session.close()


@pytest.mark.integration
def test_report_round_trips_with_mc_summary_fields():
    """Persisted JSON must carry the exact MC-summary schema the user asked to save."""
    from db.session import SessionLocal
    from app.engine.persistence import load_validation_report, save_validation_report
    from app.engine.validation import validate_all

    session = SessionLocal()
    try:
        cfg = MonteCarloConfig(n_sims=300, seed=42)
        results = validate_all(session, cfg)
        with tempfile.TemporaryDirectory() as tmp:
            json_path, md_path = save_validation_report(results, tmp, seed=cfg.seed)
            loaded = load_validation_report(json_path)

            assert md_path.exists()
            assert "aggregate" in loaded
            assert len(loaded["races"]) == len(results)
            pred = loaded["races"][0]["predicted"]
            for field in ("strategy_key", "mean_s", "std_s", "p10_s", "p50_s", "p90_s",
                          "sc_benefit_freq", "seed", "n_simulations"):
                assert field in pred
            assert pred["seed"] == 42
            assert pred["n_simulations"] == 300
    finally:
        session.close()
