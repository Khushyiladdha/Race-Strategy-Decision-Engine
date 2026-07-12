import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.pit_loss import pit_loss


def test_known_circuits_return_positive():
    for circuit in ["bahrain", "spanish", "singapore", "austrian", "brazilian", "australian"]:
        assert pit_loss(circuit) > 0


def test_unknown_circuit_returns_default():
    val = pit_loss("unknown_circuit_xyz")
    assert val > 0


def test_case_insensitive():
    assert pit_loss("Bahrain") == pit_loss("bahrain")
