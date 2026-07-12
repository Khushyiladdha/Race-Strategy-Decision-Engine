// Typed client for the Stage 5 API. Interfaces mirror the Pydantic schemas field-for-field.

// Overridable at build time (Vercel sets VITE_API_BASE to the deployed backend URL).
const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

// --- ops -------------------------------------------------------------------

export interface HealthResponse {
  status: string
  version: string
  database: 'connected' | 'error'
}

export interface VersionResponse {
  engine_version: string
  api_version: string
  validation_report: string | null
}

// --- discovery -------------------------------------------------------------

export interface RaceListItem {
  id: number
  year: number
  round: number
  circuit_key: string
  can_generate: boolean
  reason: string
  total_laps: number
}

// --- strategy evaluation ---------------------------------------------------

export interface Breakdown {
  base_s: number
  compound_offset_s: number
  degradation_s: number
  fuel_s: number
  pit_s: number
  total_s: number
}

export interface DistributionOut {
  mean_s: number
  std_s: number
  p10_s: number
  p50_s: number
  p90_s: number
  best_s: number
  worst_s: number
  sc_benefit_freq: number
  n_sims: number
}

export interface StrategyOut {
  key: string
  n_stops: number
  pit_laps: number[]
  compounds: string[]
  win_probability: number
  histogram: number[]
  breakdown: Breakdown
  distribution: DistributionOut
}

export interface EvaluateRequest {
  circuit_key: string
  total_laps?: number
  n_sims?: number
  seed?: number
  robust_metric?: 'mean_s' | 'p90_s'
  top_k?: number
}

export interface EvaluateResponse {
  circuit_key: string
  total_laps: number
  sc_rate_per_lap: number
  n_strategies_generated: number
  deterministic_top_key: string
  robust_top_key: string
  strategies: StrategyOut[]
  histogram_lo: number
  histogram_hi: number
  runtime_ms: number
  generated_at: string
}

export interface DegradationPoint {
  lap: number
  loss_s: number
}

export interface DegradationCurve {
  compound: string
  a: number
  b: number
  max_observed: number
  curve: DegradationPoint[]
}

export interface DegradationResponse {
  circuit_key: string
  compounds: DegradationCurve[]
}

// --- validation ------------------------------------------------------------

export interface TimingAxisOut {
  predicted_total_s: number
  actual_total_est_s: number
  time_error_s: number
  green_lap_median_s: number
  lap_coverage: number
}

export interface PredictedSummaryOut {
  strategy_key: string
  deterministic_time_s: number
  mean_s: number
  std_s: number
  p10_s: number
  p50_s: number
  p90_s: number
  sc_benefit_freq: number
  seed: number
  n_simulations: number
}

export interface ActualStrategyOut {
  winner: string
  pit_laps: number[]
  compounds: string[]
  n_stops: number
}

export interface ValidationMetricsOut {
  stop_count_match: boolean
  pit_lap_mae: number | null
  first_stop_abs_error: number
  compound_match: string
}

export interface ValidationDetailOut {
  circuit_key: string
  total_laps: number
  predicted: PredictedSummaryOut
  predicted_pit_laps: number[]
  predicted_compounds: string[]
  robust_pick_key: string
  actual: ActualStrategyOut
  field_median_first_stop: number
  metrics: ValidationMetricsOut
  timing: TimingAxisOut
  flags: string[]
  explanation: string
}

export interface ValidationAllResponse {
  aggregate: Record<string, unknown>
  races: ValidationDetailOut[]
}

// --- report ----------------------------------------------------------------

export interface ReportRequest {
  circuit_key: string
  n_sims?: number
  seed?: number
}

export interface ReportResponse {
  circuit_key: string
  recommendation: StrategyOut
  validation: ValidationDetailOut
  explanation: string
  executive_summary: string
  confidence_note: string
  generated_at: string
}

// --- transport -------------------------------------------------------------

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error((detail as { detail?: string }).detail ?? `${path} -> ${res.status}`)
  }
  return (await res.json()) as T
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error((detail as { detail?: string }).detail ?? `${path} -> ${res.status}`)
  }
  return (await res.json()) as T
}

export const getHealth = () => getJson<HealthResponse>('/health')
export const getVersion = () => getJson<VersionResponse>('/version')
export const getRaces = () => getJson<RaceListItem[]>('/api/v1/races')
export const evaluateStrategy = (req: EvaluateRequest) =>
  postJson<EvaluateResponse>('/api/v1/strategy/evaluate', req)
export const getValidationAll = () => getJson<ValidationAllResponse>('/api/v1/validation')
export const getValidation = (circuit: string) =>
  getJson<ValidationDetailOut>(`/api/v1/validation/${circuit}`)
export const generateReport = (req: ReportRequest) =>
  postJson<ReportResponse>('/api/v1/report/generate', req)
export const reportPdfUrl = (circuit: string) => `${API_BASE}/api/v1/report/pdf/${circuit}`
export const getDegradation = (circuit: string) =>
  getJson<DegradationResponse>(`/api/v1/degradation/${circuit}`)
