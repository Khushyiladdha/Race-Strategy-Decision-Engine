# Deployment guide

The backend deploys to **Hugging Face Spaces** (Docker) and the frontend to **Vercel**. Everything is
prepared; the commands below are yours to run (they touch your accounts).

> Replace `OWNER`, `REPO`, and `HF_USER` throughout.

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

## 1. Backend → Hugging Face Spaces (Docker)

The `backend/` directory is a self-contained Docker Space: `backend/Dockerfile` carries WeasyPrint's
native libraries, `backend/README.md` has the Space front-matter (`sdk: docker`, `app_port: 7860`),
and the image defaults to the bundled SQLite snapshot — **no external database needed**.

```bash
# 1. Create a Docker Space at https://huggingface.co/new-space  (SDK: Docker)
# 2. Add it as a remote and push ONLY the backend subtree as the Space root:
git remote add space https://huggingface.co/spaces/HF_USER/race-strategy-engine
git subtree push --prefix backend space main
```

The Space builds the Dockerfile and serves on port 7860. Your API base URL will be
`https://HF_USER-race-strategy-engine.hf.space`.

**After the frontend is up**, add its origin to the Space's CORS allow-list: in the Space
**Settings → Variables**, set `CORS_ORIGINS` to your Vercel URL (comma-separated for multiple), e.g.
`https://REPO.vercel.app`.

---

## 2. Frontend → Vercel

```bash
# https://vercel.com/new → import OWNER/REPO
#   Root Directory:     frontend
#   Framework Preset:   Vite   (build: npm run build, output: dist — already in vercel.json)
#   Environment Variable:
#     VITE_API_BASE = https://HF_USER-race-strategy-engine.hf.space
```

Deploy. Then copy the resulting `https://REPO.vercel.app` URL back into the Space's `CORS_ORIGINS`
(step 1) and redeploy the Space if needed.

---

## 3. Wire the live links

Fill the live URLs into `README.md` (the screenshots/demo section) and you're done — a stranger can
click the Vercel link and use the engine end to end.

## Updating the cached data

The deployed backend serves a snapshot. To add races: run `python scripts/fetch_races.py` against a
local Postgres, then `python scripts/export_sqlite.py`, commit the refreshed `backend/data/race_data.db`,
and `git subtree push --prefix backend space main` again.
