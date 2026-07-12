# Race Strategy Engine — Frontend

React + Vite + TypeScript + Tailwind v4 + D3 UI for the
[Race Strategy Decision Engine](../README.md).

```bash
npm install
npm run dev            # http://localhost:5173
npm run build          # type-check + production build
npm test               # Vitest
npm run lint           # ESLint
```

Set `VITE_API_BASE` (see `.env.example`) to point at a deployed backend; it defaults to
`http://localhost:8000` for local development.

Pages: **Dashboard** (config, hero, strategy board, confidence ribbons, stint timelines, outcome
histogram), **Validation**, **Model** (tyre-degradation curves), **Report** (PDF export), and a
**Style guide** component gallery.
