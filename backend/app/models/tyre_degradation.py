import json
import sys
import warnings
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db.models import Race, Lap
from app.models.fuel_model import fuel_correction

_PARAMS_DIR = Path(__file__).parent.parent.parent / "data" / "fitted_params"
_MIN_LAPS_TO_FIT = 5
_FALLBACK_COEFFS = {"a": 0.05, "b": 0.001}

# Availability gate. A fit can clear _MIN_LAPS_TO_FIT on a single stint
# (bahrain/MEDIUM: 6 laps, 1 stint) and still report fallback=False. Sample size in
# laps is misleading; stints are the real unit of evidence. The strategy generator
# must never see a compound that fails this gate.
_MIN_STINTS_TO_FIT = 3
_MIN_LAPS_FOR_AVAILABILITY = 20


def _quadratic(n: np.ndarray, a: float, b: float) -> np.ndarray:
    return a * n + b * n ** 2


def _params_path(circuit_key: str, compound: str) -> Path:
    return _PARAMS_DIR / f"{compound.upper()}_{circuit_key.lower()}.json"


def fit_degradation(circuit_key: str, compound: str, session) -> dict:
    """
    Fit deg(n) = a*n + b*n^2 to valid stint laps for this circuit+compound.

    Steps:
    1. Load is_valid laps for the compound from all cached races at this circuit.
    2. Strip lap 1 of each stint (out-lap) and the last lap of each stint (in-lap).
    3. Fuel-correct each lap: raw + k*L, normalising to a full-fuel car.
       (Prediction is the inverse: model - k*L. See evaluator.py.)
    4. Subtract the stint minimum, leaving only the degradation delta.
    5. Fit quadratic to (lap_in_stint -> delta), bounded a,b >= 0.
    6. Save params to disk; return them.

    Falls back to _FALLBACK_COEFFS if < _MIN_LAPS_TO_FIT data points.

    NOTE: `base_lap_s` is diagnostic only. It is NOT a per-compound pace -- compound
    is collinear with race phase (track evolution, fuel, dirty air), so the fitted
    intercept ranks softs slower than hards. Use compound_pace.py instead.
    Degradation (a, b) IS identifiable, because it is estimated within stints.
    """
    _PARAMS_DIR.mkdir(parents=True, exist_ok=True)

    races = (
        session.query(Race)
        .filter(Race.circuit_key == circuit_key.lower())
        .all()
    )

    # collect (lap_in_stint, fuel_corrected_time) pairs per stint
    n_values: list[float] = []
    delta_values: list[float] = []
    raw_base_times: list[float] = []
    n_stints = 0

    for race in races:
        laps = (
            session.query(Lap)
            .filter(
                Lap.race_id == race.id,
                Lap.compound == compound.upper(),
                Lap.is_valid == True,
                Lap.lap_time_s.isnot(None),
                Lap.stint_number.isnot(None),
            )
            .order_by(Lap.driver, Lap.stint_number, Lap.lap_number)
            .all()
        )

        # group by (driver, stint)
        stints: dict[tuple, list] = {}
        for lap in laps:
            key = (lap.driver, lap.stint_number)
            stints.setdefault(key, []).append(lap)

        for _, stint_laps in stints.items():
            if len(stint_laps) < 3:
                continue
            # trim first and last lap (out/in laps)
            core = stint_laps[1:-1]
            if len(core) < 2:
                continue
            n_stints += 1

            # fuel-correct: raw lap time already contains the fuel benefit,
            # so add it back to normalise every lap to a full-fuel car
            corrected = [
                lap.lap_time_s + fuel_correction(lap.lap_number)
                for lap in core
            ]

            # lap_in_stint index: 1-based position within the trimmed core
            base = min(corrected)
            raw_base_times.append(base)

            for i, t in enumerate(corrected, start=1):
                n_values.append(float(i))
                delta_values.append(t - base)

    n_arr = np.array(n_values)
    d_arr = np.array(delta_values)

    base_lap_s = float(np.median(raw_base_times)) if raw_base_times else 90.0
    max_stint_lap = int(max(n_values)) if n_values else 0

    common = {
        "base_lap_s": base_lap_s,
        "n_laps_fit": len(n_arr),
        "n_stints": n_stints,
        "max_stint_lap_observed": max_stint_lap,
    }

    def _rmse(a: float, b: float) -> float:
        if len(n_arr) == 0:
            return float("nan")
        return float(np.sqrt(np.mean((_quadratic(n_arr, a, b) - d_arr) ** 2)))

    if len(n_arr) < _MIN_LAPS_TO_FIT:
        warnings.warn(
            f"Insufficient data for {compound} at {circuit_key} "
            f"({len(n_arr)} laps). Using fallback coefficients."
        )
        fb = _FALLBACK_COEFFS
        result = {**fb, **common, "fit_rmse": _rmse(fb["a"], fb["b"]), "fallback": True}
    else:
        try:
            # Bounds keep a,b >= 0 so degradation can only stay flat or worsen.
            # Unconstrained, real data yields b<0 — a parabola that turns downward
            # inside the observed stint range, predicting tyres get faster with age.
            popt, _ = curve_fit(
                _quadratic,
                n_arr,
                d_arr,
                p0=[0.05, 0.001],
                bounds=([0.0, 0.0], [np.inf, np.inf]),
                maxfev=5000,
            )
            a, b = float(popt[0]), float(popt[1])
            result = {"a": a, "b": b, **common, "fit_rmse": _rmse(a, b), "fallback": False}
        except RuntimeError:
            warnings.warn(f"curve_fit failed for {compound}/{circuit_key}; using fallback.")
            fb = _FALLBACK_COEFFS
            result = {**fb, **common, "fit_rmse": _rmse(fb["a"], fb["b"]), "fallback": True}

    path = _params_path(circuit_key, compound)
    path.write_text(json.dumps(result, indent=2))
    return result


def load_params(circuit_key: str, compound: str) -> dict:
    """Load previously fitted params from disk. Raises FileNotFoundError if not fitted yet."""
    path = _params_path(circuit_key, compound)
    if not path.exists():
        raise FileNotFoundError(
            f"No fitted params for {compound}/{circuit_key}. Run fit_degradation first."
        )
    return json.loads(path.read_text())


def is_compound_available(circuit_key: str, compound: str) -> tuple[bool, str]:
    """
    Whether a compound has enough real evidence at this circuit to enter the optimizer.

    Returns (available, reason). A fallback coefficient is a guess presented as data,
    and a single stint is not a sample -- neither may reach the strategy generator.
    """
    try:
        p = load_params(circuit_key, compound)
    except FileNotFoundError:
        return False, "not fitted"

    if p.get("fallback", False):
        return False, f"fallback coefficients ({p['n_laps_fit']} laps)"
    if p.get("n_stints", 0) < _MIN_STINTS_TO_FIT:
        return False, f"only {p.get('n_stints', 0)} stint(s)"
    if p["n_laps_fit"] < _MIN_LAPS_FOR_AVAILABILITY:
        return False, f"only {p['n_laps_fit']} laps"
    return True, f"{p['n_stints']} stints, {p['n_laps_fit']} laps"


def available_compounds(circuit_key: str) -> list[str]:
    """Compounds with enough evidence at this circuit, in pace order."""
    return [
        c for c in ("SOFT", "MEDIUM", "HARD")
        if is_compound_available(circuit_key, c)[0]
    ]


def predict_lap_time(lap_in_stint: int, base_lap_s: float, a: float, b: float) -> float:
    """
    Predicted lap time at a given stint lap number using fitted degradation coefficients.

    Coefficients from fit_degradation are bounded non-negative. Hand-supplied or
    legacy params may have b<0, which would make the curve turn downward past its
    vertex; clamp there so degradation never reverses.
    """
    n = float(lap_in_stint)
    if b < 0:
        n = min(n, -a / (2 * b))
    return base_lap_s + a * n + b * n ** 2
