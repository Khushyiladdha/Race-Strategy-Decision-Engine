import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.compound_pace import COMPOUND_OFFSET_S, circuit_base_lap_s, compound_offset


def test_offsets_increase_softest_to_hardest():
    """Softer compound is always faster at equal fuel and tyre age."""
    assert COMPOUND_OFFSET_S["SOFT"] < COMPOUND_OFFSET_S["MEDIUM"] < COMPOUND_OFFSET_S["HARD"]


def test_soft_is_the_reference():
    assert compound_offset("SOFT") == 0.0


def test_compound_offset_is_case_insensitive():
    assert compound_offset("soft") == compound_offset("SOFT")


def test_unknown_compound_raises():
    with pytest.raises(ValueError):
        compound_offset("ULTRASOFT")


@pytest.mark.integration
def test_circuit_base_lap_in_sane_band():
    from db.session import SessionLocal
    session = SessionLocal()
    try:
        for circuit in ["bahrain", "spanish", "japanese", "singapore"]:
            base = circuit_base_lap_s(circuit, session)
            assert 60.0 < base < 120.0, f"{circuit}: implausible base pace {base}"
    finally:
        session.close()


@pytest.mark.integration
def test_unknown_circuit_raises():
    from db.session import SessionLocal
    session = SessionLocal()
    try:
        with pytest.raises(ValueError):
            circuit_base_lap_s("monaco", session)
    finally:
        session.close()
