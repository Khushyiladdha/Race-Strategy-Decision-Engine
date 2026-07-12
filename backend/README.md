# Race Strategy Engine — Backend

FastAPI service for the [Race Strategy Decision Engine](../README.md). Containerized via
`Dockerfile` and deployed to [Railway](../DEPLOY.md) (Docker); the frontend talks to it from Vercel.

- **Run locally (Postgres):** `docker compose up --build backend` from the repo root (serves `:8000`).
- **Self-contained (SQLite):** the image defaults to `DATABASE_URL=sqlite:///data/race_data.db` and a
  bundled snapshot, so it runs with no external database — which is how it deploys to Railway.
- **Port:** the server binds `${PORT:-7860}`, so it uses the `PORT` that Railway injects (and `8000`
  under docker-compose).
- **Docs:** Swagger at `/docs`; the API is namespaced under `/api/v1`.
- **Tests:** `pytest tests/ -q` (125 passing; 2 PDF tests skip without WeasyPrint's native libraries,
  which are present in the Docker image).

### Scripts
- `scripts/fetch_races.py` — pull + cache races via FastF1.
- `scripts/fit_all.py` — fit degradation curves per circuit × compound.
- `scripts/run_validation.py` — regenerate the historical validation report.
- `scripts/export_sqlite.py` — snapshot Postgres → the bundled SQLite file for deploy.
