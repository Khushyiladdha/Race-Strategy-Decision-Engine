import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.engine.strategy_generator import (
    MIN_STINT_LAPS,
    Stint,
    Strategy,
    can_generate,
    generate_strategies,
    parse_key,
)

BAHRAIN_LAPS = 57


@pytest.fixture(scope="module")
def bahrain():
    return generate_strategies("bahrain", BAHRAIN_LAPS)


# --- key round-trips and identifies ---------------------------------------

def test_key_format_one_stop():
    s = Strategy(stints=(Stint("SOFT", 1, 18), Stint("HARD", 19, 57)))
    assert s.key == "S-H@18"


def test_key_format_two_stop():
    s = Strategy(stints=(
        Stint("SOFT", 1, 14), Stint("MEDIUM", 15, 32), Stint("HARD", 33, 57),
    ))
    assert s.key == "S-M-H@14,32"


def test_key_round_trips():
    compounds, pit_laps = parse_key("S-M-H@14,32")
    assert compounds == ("SOFT", "MEDIUM", "HARD")
    assert pit_laps == (14, 32)


@pytest.mark.integration
def test_keys_are_unique_across_the_whole_set(bahrain):
    """
    If keys collide the key is a label, not an identifier, and Stage 3's
    distribution map would silently overwrite entries.
    """
    keys = [s.key for s in bahrain]
    assert len(set(keys)) == len(keys)


# --- legality --------------------------------------------------------------

@pytest.mark.integration
def test_every_strategy_uses_at_least_two_compounds(bahrain):
    for s in bahrain:
        assert len({st.compound for st in s.stints}) >= 2


@pytest.mark.integration
def test_stints_tile_the_race_exactly(bahrain):
    for s in bahrain:
        assert s.stints[0].start_lap == 1
        assert s.stints[-1].end_lap == BAHRAIN_LAPS
        for prev, nxt in zip(s.stints, s.stints[1:]):
            assert nxt.start_lap == prev.end_lap + 1, "gap or overlap between stints"
        assert sum(st.length for st in s.stints) == BAHRAIN_LAPS


@pytest.mark.integration
def test_no_stint_shorter_than_minimum(bahrain):
    for s in bahrain:
        for st in s.stints:
            assert st.length >= MIN_STINT_LAPS


@pytest.mark.integration
def test_pit_laps_strictly_increasing(bahrain):
    for s in bahrain:
        pits = s.pit_laps
        assert list(pits) == sorted(set(pits))


# --- the availability gate keeps guesses out of the optimizer -------------

@pytest.mark.integration
def test_bahrain_yields_no_medium_strategies(bahrain):
    """bahrain/MEDIUM fit on a single 6-lap stint. It must never be offered."""
    for s in bahrain:
        for st in s.stints:
            assert st.compound != "MEDIUM"


@pytest.mark.integration
def test_australian_cannot_generate():
    """Three red flags fragment the stints; only HARD survives the gate."""
    ok, reason = can_generate("australian")
    assert not ok
    assert "two-compound rule" in reason
    with pytest.raises(ValueError, match="two-compound rule"):
        generate_strategies("australian", 58)


@pytest.mark.integration
def test_spanish_can_generate_with_all_three():
    ok, _ = can_generate("spanish")
    assert ok


# --- search space size -----------------------------------------------------

@pytest.mark.integration
def test_search_space_is_the_expected_order_of_magnitude(bahrain):
    """Guards against an off-by-one silently blowing up or collapsing the space."""
    assert 5_000 < len(bahrain) < 30_000


@pytest.mark.integration
def test_generation_is_fast(bahrain):
    t0 = time.perf_counter()
    generate_strategies("bahrain", BAHRAIN_LAPS)
    assert time.perf_counter() - t0 < 1.0
