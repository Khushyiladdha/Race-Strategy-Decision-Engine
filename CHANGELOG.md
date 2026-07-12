# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-07-12

First public release. A complete, tested, validated F1 pit-strategy engine with a UI, a PDF report,
and deploy configuration.

### Added

- **Data foundation** — FastF1 → PostgreSQL cache of six varied 2023 races; a bundled SQLite snapshot
  for self-contained deployment.
- **Domain models** — fuel burn-off, per-circuit pit loss, safety-car rate (published table +
  empirical-first resolver), and tyre degradation `deg(n)=a·n+b·n²` fit with `scipy.optimize.curve_fit`
  under non-negativity constraints; each a pure, unit-tested function.
- **Strategy engine** — exhaustive 1–2 stop generation (FIA two-compound rule, min stint length) with
  closed-form O(stints) evaluation of total race time.
- **Monte Carlo robustness** — discrete Poisson safety-car events + degradation noise scaled by
  extrapolation; common random numbers across strategies yielding a real **win probability** per shape.
- **Historical validation** — predicted vs. actual-winner comparison per race, with pit-lap MAE, an
  independent free-air timing axis, and auto-generated, data-backed explanations for each disagreement.
- **API** — typed FastAPI (`/api/v1`) for races, strategy evaluation, validation, degradation curves,
  and reports; Swagger at `/docs`; env-driven CORS.
- **Frontend** — React + D3 pit-wall UI: Dashboard (config, hero, strategy board, confidence ribbons,
  stint timelines, outcome-distribution histogram), Validation, Model insights (degradation curves),
  Report, and a Style guide. A disciplined design system (FIA tyre colors, reserved purple accent).
- **PDF report** — Jinja2 → WeasyPrint one-page briefing with embedded metadata, a page footer, an
  executive summary, and a data-driven confidence note.
- **Deploy** — Dockerfile (WeasyPrint native stack), docker-compose, Vercel config, and a deployment
  guide.

### Validation (5 generatable 2023 races)

- Pit-lap MAE **4.38 laps**, first-stop MAE **4.2 laps**, mean absolute timing error **34 s**.
- Surfaced a systematic ~0.5 s/lap free-air timing bias and Singapore's real 1-stop-vs-2-stop
  disagreement.

[1.0.0]: https://github.com/OWNER/REPO/releases/tag/v1.0.0
