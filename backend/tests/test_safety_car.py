import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.safety_car import sc_probability_per_lap, _GLOBAL_DEFAULT_SC_PROB


def _mock_session(races):
    session = MagicMock()
    session.query.return_value.filter.return_value.all.return_value = races
    return session


def test_falls_back_to_default_with_no_races():
    session = _mock_session([])
    prob = sc_probability_per_lap("bahrain", session)
    assert prob == _GLOBAL_DEFAULT_SC_PROB


def test_falls_back_with_one_race():
    session = _mock_session([MagicMock()])  # only 1 race
    prob = sc_probability_per_lap("bahrain", session)
    assert prob == _GLOBAL_DEFAULT_SC_PROB


def test_probability_in_unit_interval():
    # With no real DB, fall back path always returns a valid probability
    session = _mock_session([])
    prob = sc_probability_per_lap("bahrain", session)
    assert 0.0 <= prob <= 1.0
