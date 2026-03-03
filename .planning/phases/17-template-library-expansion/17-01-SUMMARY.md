---
phase: 17-template-library-expansion
plan: "01"
subsystem: app-templates
tags: [templates, spa, sse, dashboard, chart.js, flask]
dependency_graph:
  requires: []
  provides: [utility-spa-template, dashboard-realtime-template]
  affects: [apps/_templates/_GUIDE.md]
tech_stack:
  added: []
  patterns:
    - Flask static file server with base tag injection (utility-spa)
    - Server-Sent Events streaming with SSE+polling fallback (dashboard-realtime)
    - Chart.js v4 multi-chart layout (line, bar, doughnut)
key_files:
  created:
    - apps/_templates/utility-spa/serve.py
    - apps/_templates/utility-spa/index.html
    - apps/_templates/utility-spa/style.css
    - apps/_templates/utility-spa/app.js
    - apps/_templates/utility-spa/requirements.txt
    - apps/_templates/dashboard-realtime/app.py
    - apps/_templates/dashboard-realtime/templates/index.html
    - apps/_templates/dashboard-realtime/static/style.css
    - apps/_templates/dashboard-realtime/requirements.txt
  modified: []
decisions:
  - utility-spa uses serve.py (static-html pattern) not Flask templates — no Python logic needed for SPA tools
  - dashboard-realtime uses SSE as primary channel with polling fallback — SSE is simpler than WebSockets and degrades gracefully
  - Chart instances stored and updated via .data + .update("none") rather than destroy/recreate — avoids flicker on live updates
  - Status dot shows three states: connected (SSE active), reconnecting (SSE error, switching to poll), error (poll active)
metrics:
  duration: "4min"
  completed_date: "2026-03-03"
  tasks_completed: 2
  files_created: 9
  files_modified: 0
---

# Phase 17 Plan 01: Two New App Templates (utility-spa + dashboard-realtime) Summary

Two production-ready app templates added to `apps/_templates/`: a minimal vanilla-JS single-page tool template and a Flask/SSE real-time dashboard with three Chart.js chart types.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create utility-spa template | 0713066 | serve.py, index.html, style.css, app.js, requirements.txt |
| 2 | Create dashboard-realtime template | db7a55f | app.py, templates/index.html, static/style.css, requirements.txt |

## What Was Built

### utility-spa (`apps/_templates/utility-spa/`)

Minimal single-page app template for lightweight tools — calculators, text processors, unit converters, viewers.

- **serve.py** — Flask static file server following the `static-html` template pattern exactly. Reads `APP_NAME` and `PORT` from env, injects `<base href="/{APP_NAME}/">` after `<head>`, serves all other files from `.`. Listens on `0.0.0.0`.
- **index.html** — Three-section layout: input textarea, action button row, output area. Includes instructional comment about base tag injection. Relative paths: `href="style.css"`, `src="app.js"`. No CDN dependencies.
- **style.css** — Dark theme with same CSS custom properties as all other templates (`--bg`, `--surface`, `--border`, `--text`, `--accent`, `--green`, `--orange`, `--radius`, `--font`, `--mono`). Adds `.tool-input`, `.tool-actions`, `.tool-output` classes. Responsive stack on mobile.
- **app.js** — Text transformer sample (uppercase, lowercase, title case, reverse, char count). DOM refs, transform functions, button wiring, copy-to-clipboard. Comment block explains the input→process→output pattern for replacement.
- **requirements.txt** — Standard flask-pre-installed comment.

### dashboard-realtime (`apps/_templates/dashboard-realtime/`)

Flask dashboard with Server-Sent Events as the primary data channel and polling as fallback. Distinct from `flask-dashboard` (polling only, single line chart).

- **app.py** — Flask app with three routes:
  - `GET /` — renders `templates/index.html` with `app_name`, `title`
  - `GET /api/stream` — SSE endpoint (`mimetype="text/event-stream"`, `Cache-Control: no-cache`, `Connection: keep-alive`). Generator yields `data: {json}\n\n` every 2 seconds.
  - `GET /api/data` — polling fallback returning identical JSON shape
  - `generate_data()` — shared function producing 4 metric cards, line chart (12 time points, 2 datasets), bar chart (6 categories), doughnut chart (4 segments)
- **templates/index.html** — Self-contained dashboard. Chart.js v4 from CDN. SSE via `EventSource("api/stream")`. Three charts: full-width line (time series), side-by-side bar + doughnut in `.charts-grid`. Status dot (green+glow connected, orange pulse reconnecting, red error). Chart instances updated via `.data = newData; .update("none")` — no destroy/recreate.
- **static/style.css** — Dashboard dark theme matching `flask-dashboard`. Adds `.charts-grid` (2-column responsive grid), `.chart-full`, `.chart-wrap-line` (280px), `.chart-wrap-bar` / `.chart-wrap-doughnut` (240px). Stacks to 1-column on mobile.
- **requirements.txt** — Standard flask-pre-installed comment.

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **utility-spa uses serve.py pattern (not Flask templates)** — The template requires no Python backend logic. Matching the `static-html` pattern keeps it minimal and appropriate for pure front-end tools.

2. **dashboard-realtime uses SSE + polling fallback** — SSE is simpler than WebSockets, supported in all modern browsers, and degrades gracefully. The polling fallback ensures the dashboard works even if the SSE connection is blocked.

3. **Chart update via .data + .update("none")** — Avoids the visual flicker of destroy/recreate. All three charts store their instances in variables and update data in-place, matching the pattern from `flask-dashboard`.

4. **Status dot: three states** — `connected` (SSE active, green glow), `reconnecting` (SSE error, orange pulse), `error` (poll active, red static) — gives the user clear feedback on data freshness without extra UI.

## Self-Check: PASSED

All 9 created files confirmed present on disk. Both task commits (0713066, db7a55f) confirmed in git history.
