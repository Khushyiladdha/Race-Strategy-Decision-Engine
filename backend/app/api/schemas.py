"""
Pydantic v2 request/response models.

These mirror the engine dataclasses field-for-field; there is no business logic here. The
DistributionOut deliberately omits the raw 2000-element `samples` array — only summary stats
cross the wire.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field


# --- ops -------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    version: str
    database: Literal["connected", "error"]


class VersionResponse(BaseModel):
    engine_version: str
    api_version: str
    validation_report: Optional[str] = None   # ISO mtime of report.json, or null


# --- discovery -------------------------------------------------------------

class RaceListItem(BaseModel):
    id: int
    year: int
    round: int
    circuit_key: str
    can_generate: bool
    reason: str
    total_laps: int


# --- strategy evaluation ---------------------------------------------------

class EvaluateRequest(BaseModel):
    circuit_key: str
    total_laps: Optional[int] = Field(default=None, description="Defaults to race distance from cache")
    n_sims: int = 2000
    seed: int = 0
    robust_metric: Literal["mean_s", "p90_s"] = "mean_s"
    top_k: int = 8


class Breakdown(BaseModel):
    """The five additive components; they sum to total_s."""
    base_s: float
    compound_offset_s: float
    degradation_s: float
    fuel_s: float            # negative: fuel burn-off makes the car faster
    pit_s: float
    total_s: float


class DistributionOut(BaseModel):
    """Monte Carlo summary. Raw samples are intentionally not serialized."""
    mean_s: float
    std_s: float
    p10_s: float
    p50_s: float
    p90_s: float
    best_s: float
    worst_s: float
    sc_benefit_freq: float
    n_sims: int


class StrategyOut(BaseModel):
    key: str
    n_stops: int
    pit_laps: list[int]
    compounds: list[str]
    win_probability: float   # P(this shape is fastest) across the displayed set; sums to 1
    histogram: list[int]     # MC-sample counts over EvaluateResponse.histogram_lo..hi (shared bins)
    breakdown: Breakdown
    distribution: DistributionOut


class EvaluateResponse(BaseModel):
    circuit_key: str
    total_laps: int
    sc_rate_per_lap: float
    n_strategies_generated: int
    deterministic_top_key: str
    robust_top_key: str
    strategies: list[StrategyOut]
    histogram_lo: float          # shared x-domain for every strategy's histogram
    histogram_hi: float
    runtime_ms: int
    generated_at: str


# --- validation ------------------------------------------------------------

class TimingAxisOut(BaseModel):
    predicted_total_s: float
    actual_total_est_s: float
    time_error_s: float
    green_lap_median_s: float
    lap_coverage: float


class ActualStrategyOut(BaseModel):
    winner: str
    pit_laps: list[int]
    compounds: list[str]
    n_stops: int


class ValidationMetricsOut(BaseModel):
    stop_count_match: bool
    pit_lap_mae: Optional[float] = None
    first_stop_abs_error: int
    compound_match: str


class PredictedSummaryOut(BaseModel):
    """Matches the persisted `.summary()` block in report.json (not the live DistributionOut)."""
    strategy_key: str
    deterministic_time_s: float
    mean_s: float
    std_s: float
    p10_s: float
    p50_s: float
    p90_s: float
    sc_benefit_freq: float
    seed: int
    n_simulations: int


class ValidationDetailOut(BaseModel):
    circuit_key: str
    total_laps: int
    predicted: PredictedSummaryOut
    predicted_pit_laps: list[int]
    predicted_compounds: list[str]
    robust_pick_key: str
    actual: ActualStrategyOut
    field_median_first_stop: float
    metrics: ValidationMetricsOut
    timing: TimingAxisOut
    flags: list[str]
    explanation: str


class ValidationAllResponse(BaseModel):
    aggregate: dict
    races: list[ValidationDetailOut]


# --- report ----------------------------------------------------------------

class DegradationPoint(BaseModel):
    lap: int
    loss_s: float


class DegradationCurve(BaseModel):
    compound: str
    a: float
    b: float
    max_observed: int
    curve: list[DegradationPoint]


class DegradationResponse(BaseModel):
    circuit_key: str
    compounds: list[DegradationCurve]


class ReportRequest(BaseModel):
    circuit_key: str
    n_sims: int = 2000
    seed: int = 0


class ReportResponse(BaseModel):
    circuit_key: str
    recommendation: StrategyOut
    validation: ValidationDetailOut
    explanation: str
    executive_summary: str       # one-paragraph brief, shared by the on-screen view and the PDF
    confidence_note: str         # data-driven read on the win-probability
    generated_at: str
