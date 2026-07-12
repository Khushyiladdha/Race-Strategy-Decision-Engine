import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.tyre_degradation import fit_degradation, predict_lap_time


def test_predict_lap_time_monotonically_increases():
    """Tyre degradation must make the car slower lap-over-lap within a stint."""
    base = 90.0
    a, b = 0.05, 0.001
    times = [predict_lap_time(n, base, a, b) for n in range(1, 40)]
    assert all(times[i] < times[i + 1] for i in range(len(times) - 1)), (
        "Degradation curve must be non-decreasing over stint laps"
    )


def test_predict_lap_time_at_lap_zero_equals_base():
    assert predict_lap_time(0, 90.0, 0.05, 0.001) == 90.0


def test_predict_lap_time_uses_coefficients():
    result = predict_lap_time(10, 90.0, 0.1, 0.0)
    assert abs(result - 91.0) < 1e-9


def test_predict_lap_time_clamps_negative_curvature():
    """Legacy b<0 coefficients must not make the car speed up past the vertex."""
    a, b = 0.15, -0.0073          # the pre-fix Bahrain SOFT fit; vertex ~lap 10
    times = [predict_lap_time(n, 90.0, a, b) for n in range(1, 40)]
    assert all(times[i] <= times[i + 1] + 1e-9 for i in range(len(times) - 1))


@pytest.mark.integration
def test_fitted_coefficients_are_non_negative():
    """
    A fit yielding b<0 predicts tyres getting faster with age — never valid.
    Exercises the real fitted output, not hand-picked coefficients.
    Requires a populated Postgres (Stage 0 cache).
    """
    from db.session import SessionLocal

    session = SessionLocal()
    try:
        for compound in ["SOFT", "MEDIUM", "HARD"]:
            params = fit_degradation("bahrain", compound, session)
            assert params["a"] >= 0, f"{compound}: a={params['a']} must be >= 0"
            assert params["b"] >= 0, f"{compound}: b={params['b']} must be >= 0"
            assert params["max_stint_lap_observed"] > 0
    finally:
        session.close()
