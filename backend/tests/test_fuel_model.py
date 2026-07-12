import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.fuel_model import fuel_correction


def test_zero_lap_gives_zero_correction():
    assert fuel_correction(0) == 0.0


def test_correction_increases_monotonically():
    times = [fuel_correction(n) for n in range(0, 60)]
    assert all(times[i] < times[i + 1] for i in range(len(times) - 1))


def test_custom_k():
    assert fuel_correction(10, k=0.05) == pytest.approx(0.5)


def test_negative_lap_raises():
    with pytest.raises(ValueError):
        fuel_correction(-1)
