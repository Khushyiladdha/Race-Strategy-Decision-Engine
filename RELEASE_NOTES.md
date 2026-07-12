# Race Strategy Decision Engine — v1.0.0

The first release of an F1 pit-stop strategy engine that runs on **real data**, is **tested end to
end**, and **validates itself against real race outcomes**.

## Highlights

🏎️ **Real F1 data, no fabrication.** Timing and stint data pulled via FastF1 for six varied 2023
races and cached; every domain model is fit to that data, not hand-tuned.

🧮 **Exhaustive + honest.** Enumerates every legal 1–2 stop strategy (~5k–45k per race) and scores each
in closed form in well under a second — no black-box solver.

🎲 **Monte Carlo with a real confidence number.** Discrete safety-car events and degradation noise,
compared across strategies with common random numbers, produce a genuine **win probability** per
strategy (and it's honest — at Bahrain the top shapes are near-tied, so confidence is correctly low).

📊 **It validates itself.** For each cached race it compares its free-air optimum to what the winner
actually did — pit-lap MAE **4.38 laps**, mean timing error **34 s** — and explains every disagreement
in plain English (undercut, overcut, safety-car overlap, compound unavailable).

📄 **A report you could hand to a strategist.** A one-page WeasyPrint PDF: recommended strategy,
predicted-vs-actual timelines, an executive summary, a data-driven confidence note, embedded metadata,
and a page footer.

🎨 **A design system with integrity.** A pit-wall aesthetic where FIA tyre colors encode compound only
and purple is reserved exclusively for the fastest result — enforced by a hex-in-components lint gate.

## By the numbers

- **139 tests** (125 backend, 14 frontend).
- **5 races validated**, 9 build stages, one exhaustive engine.
- Backend: FastAPI + SQLAlchemy + scipy/numpy. Frontend: React 19 + TypeScript + D3 + Tailwind v4.

## Notable engineering decisions

- Quantities the data **can't** identify (compound pace, pit loss, safety-car rate) are filled with
  **published constants, clearly labelled** — never silently guessed.
- Degradation coefficients are **constrained non-negative** so the model is monotonic; the ~21 ms RMSE
  cost is documented.
- The deployed backend is **self-contained** — a bundled SQLite snapshot means no external database.

See [CHANGELOG.md](CHANGELOG.md) for the full list and [README.md](README.md) for the full write-up.
