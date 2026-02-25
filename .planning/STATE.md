# State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-25)

**Core value:** Agent Zero can build, run, and persist web applications directly within its own UI
**Current focus:** Defining new milestone

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-02-25 — Milestone v1.1 Reliability started

## Accumulated Context

- Apps run in ports 9000–9099; name-based routing via proxy
- Shared browser and shared terminal are core protected apps
- bg-remover app skeleton exists in `apps/bg-remover/` (unregistered, not yet committed)
- webui files modified (CSS, HTML preferences/sidebar/messages) — in-progress UI changes
- Frontend: vanilla JS/HTML/CSS + Alpine.js; no build step required
- Backend: Python/FastAPI in `python/`
