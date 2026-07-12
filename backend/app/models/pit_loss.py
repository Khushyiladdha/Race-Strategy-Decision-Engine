# Approximate pit-lane time loss (seconds) per circuit.
# Derived from pit delta data (entry + stationary + exit relative to flying lap pace).
# Values sourced from published F1 timing analysis; update as more circuits are added.
_PIT_LOSS_SECONDS: dict[str, float] = {
    "bahrain": 22.0,
    "spanish": 19.0,
    "singapore": 24.0,
    "austrian": 20.0,
    "brazilian": 23.0,
    "australian": 21.0,
}

_DEFAULT_PIT_LOSS = 21.5


def pit_loss(circuit_key: str) -> float:
    """Return the expected pit stop time loss in seconds for a given circuit."""
    return _PIT_LOSS_SECONDS.get(circuit_key.lower(), _DEFAULT_PIT_LOSS)
