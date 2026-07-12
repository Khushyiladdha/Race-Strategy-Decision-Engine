# Deployment guide

The backend deploys to **Railway** (Docker) and the frontend to **Vercel**. Everything is already
prepared — the `backend/Dockerfile` binds Railway's injected `$PORT`, ships a bundled SQLite snapshot
(no external database needed), and reads CORS origins from an env var. `backend/railway.json` points
Railway at the Dockerfile and adds a `/health` health check.

> Replace `OWNER`, `REPO`, and the generated Railway/Vercel URLs throughout.

---

## 0. Create the GitHub repo, push, and cut the v1.0.0 release

The project is already a local git repository with a `v1.0.0` tag. Publish it:

```bash
# from the repo root
gh repo create OWNER/REPO --public --source=. --remote=origin --push
git push origin v1.0.0
gh release create v1.0.0 --title "v1.0.0" --notes-file RELEASE_NOTES.md
```

(Without the GitHub CLI: create the repo on github.com, then
`git remote add origin https://github.com/OWNER/REPO.git && git push -u origin main --tags`, and draft
a release from the `v1.0.0` tag pasting `RELEASE_NOTES.md`.)

---

## 1. Backend → Railway (Docker)

Railway builds `backend/Dockerfile` directly from the repo — no code changes required.

1. Go to [railway.app](https://railway.app) → **New Project → Deploy from GitHub repo** → pick
   `OWNER/REPO`.
2. Open the service → **Settings**:
   - **Root Directory:** `backend` — so Railway uses `backend/Dockerfile` and `backend/railway.json`.
   - Railway auto-detects the Dockerfile builder; the health check (`/health`) comes from
     `railway.json`.
3. **Variables** (Settings → Variables):

   | Variable | Value | Notes |
   |---|---|---|
   | `PORT` | *(leave unset)* | Railway injects it automatically; the server binds `${PORT}`. |
   | `CORS_ORIGINS` | *(set in step 4, after the frontend is live)* | Comma-separated allowed origins. |

   `DATABASE_URL` does **not** need setting — the image defaults to the bundled SQLite snapshot.
4. Deploy. Under **Settings → Networking**, **Generate Domain** → you get
   `https://<name>.up.railway.app`. That is your API base URL.

**Verify the backend** (replace the host):

```bash
curl https://<name>.up.railway.app/health
# {"status":"ok","version":"0.5.0","database":"connected"}

# Swagger UI in a browser:
#   https://<name>.up.railway.app/docs

curl -X POST https://<name>.up.railway.app/api/v1/strategy/evaluate \
  -H "Content-Type: application/json" \
  -d '{"circuit_key":"bahrain","n_sims":500}'
# 200 with { "strategies": [...], "robust_top_key": "...", "histogram_lo": ... }
```

---

## 2. Frontend → Vercel

```
https://vercel.com/new → import OWNER/REPO
  Root Directory:      frontend
  Framework Preset:    Vite   (build: npm run build, output: dist — already in vercel.json)
  Environment Variable:
    VITE_API_BASE = https://<name>.up.railway.app
```

Deploy → you get `https://REPO.vercel.app`.

---

## 3. Close the CORS loop

Back on **Railway → Variables**, set:

```
CORS_ORIGINS = https://REPO.vercel.app
```

(Comma-separate if you have several, e.g. a preview domain.) Railway redeploys automatically.

---

## 4. End-to-end verification

Open `https://REPO.vercel.app` and confirm:

- **Dashboard** — pick a circuit → the strategy board, confidence ribbons, and outcome histogram load.
- **Model** — the tyre-degradation curves render.
- **Validation** — the predicted-vs-actual comparison loads.
- **Report → Export PDF** — downloads a PDF (this exercises Railway's WeasyPrint stack end to end).

No CORS errors in the browser console means `CORS_ORIGINS` is set correctly.

Finally, fill the live URLs into `README.md` (the demo/screenshots section).

---

## Fallback: backend on Render (truly free)

Render has a genuinely free tier (Railway's free usage is trial-credit based). Same Dockerfile, same
env vars — the only trade-off is that a free Render service **sleeps after ~15 min idle**, so the
first request after idle cold-starts for ~30–60 s.

1. [render.com](https://render.com) → **New → Web Service** → connect the repo.
2. **Root Directory:** `backend` · **Runtime:** Docker (auto-detected from the Dockerfile).
3. **Health Check Path:** `/health`.
4. **Environment:** `CORS_ORIGINS = https://REPO.vercel.app` (Render injects `PORT` automatically).
5. Deploy → use the resulting `https://<name>.onrender.com` as the Vercel `VITE_API_BASE`.

---

## Updating the cached data

The deployed backend serves a snapshot. To add races: run `python scripts/fetch_races.py` against a
local Postgres, then `python scripts/export_sqlite.py`, commit the refreshed
`backend/data/race_data.db`, and push — Railway redeploys on push.
