# Agent Zero — Enhanced Fork

## What This Is

A personal fork of [Agent Zero](https://github.com/frdel/agent-zero) — a general-purpose agentic AI framework — extended with an Apps System for running and managing web applications, a Neon UI theme, GSD skill packs, and core built-in apps (shared browser via VNC, shared terminal via tmux). The agent reliably creates web apps from a library of 7 templates with automatic selection, mandatory verification steps, and health-check polling. The fork is designed for local/Docker use as a personal AI workstation with first-class web app hosting capabilities.

## Core Value

Agent Zero can build, run, and persist web applications directly within its own UI — no manual port management, no lost processes, just `/{app-name}/` access.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ Apps System with dynamic port allocation (9000–9099) and name-based routing — v1.0
- ✓ App Manager: registry persistence, lifecycle management (start/stop/restart), autostart — v1.0
- ✓ App Proxy: HTTP and WebSocket proxying, reserved path protection, status pages — v1.0
- ✓ Web App API: REST endpoints for app management (`/webapp/*`) — v1.0
- ✓ Apps Modal UI: visual app gallery with status indicators and controls — v1.0
- ✓ Shared Browser app: VNC-based collaborative browser via noVNC — v1.0
- ✓ Shared Terminal app: persistent tmux session via web terminal — v1.0
- ✓ GSD Skill Pack: 50 skills (8 specialist roles, 31 orchestrators, 11 subagents) — v1.0
- ✓ Neon UI theme: full light/dark mode with glow effects — v1.0
- ✓ App templates: Flask Basic, Flask Dashboard, Static HTML scaffolding — v1.0
- ✓ Skill Forge and Web App Builder meta-skills — v1.0
- ✓ Welcome screen redesign and auto-reload UI — v1.0
- ✓ CDP startup health-check: curl-based poll on /json endpoint before Agent Zero connects — v1.1
- ✓ Browser navigate-with-verification: `navigate_and_wait()` with readyState poll, Observe→Act→Verify in SKILL.md — v1.1
- ✓ Claude CLI single-turn: `claude_single_turn()` with CLAUDECODE env fix — v1.1
- ✓ Claude CLI multi-turn: `ClaudeSession` with `--resume UUID`, session recovery — v1.1
- ✓ Claude CLI skill: `usr/skills/claude-cli/SKILL.md` documents complete interaction pattern — v1.1
- ✓ tmux primitives: send text/keys, read screen, wait_ready with prompt detection + idle fallback — v1.2
- ✓ Interactive CLI lifecycle: start, send, detect readiness, exit cleanly — v1.2
- ✓ OpenCode session wrapper: `OpenCodeSession` class with `.start()/.send()/.exit()` — v1.2
- ✓ CLI orchestration skill: `usr/skills/cli-orchestration/SKILL.md` with Read-Detect-Write-Verify cycle — v1.2
- ✓ web-app-builder SKILL.md v3.0.0 with mandatory 8-step sequence, name validation, health-check polling — v1.3
- ✓ System prompt routing: agent always uses Apps System for app creation requests — v1.3
- ✓ 4 new templates: utility SPA, real-time dashboard (SSE + Chart.js), CRUD app (Flask + SQLite), file/media tool — v1.3
- ✓ Template catalog (_CATALOG.md) with structured metadata for all 7 templates — v1.3
- ✓ _GUIDE.md decision tree covering all 7 templates with selection criteria — v1.3
- ✓ Auto-selection in SKILL.md Step 2 with keyword matching and user override — v1.3

### Active

<!-- Current scope. Building toward these. -->

(No active milestone — run `/gsd:new-milestone` to start next)

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Upstream Agent Zero core changes — this is a fork; upstream changes are pulled separately
- Mobile app — web-first, desktop/Docker target
- Multi-user / auth system — single-user personal assistant
- Database migration tooling — templates use simple SQLite; no schema versioning needed
- CI/CD for apps — apps are quick prototypes, not production deployments

## Context

- Fork of [frdel/agent-zero](https://github.com/frdel/agent-zero) — upstream divergence managed manually
- Runs via Docker or local Python; accessed at `http://localhost:50000`
- `apps/` directory holds all web apps; core apps are `shared-browser` and `shared-terminal`
- `apps/_templates/` provides 7 scaffolding templates (flask-basic, flask-dashboard, static-html, utility-spa, dashboard-realtime, crud-app, file-tool)
- `apps/_templates/_CATALOG.md` — machine-readable template catalog
- `apps/_templates/_GUIDE.md` — decision tree for template selection
- `usr/skills/web-app-builder/SKILL.md` — mandatory 8-step app creation workflow (v3.0.0)
- `usr/skills/` holds custom skills; `skills/` holds GSD skill pack
- `webui/` is the frontend (vanilla JS/HTML/CSS with Alpine.js)
- Registry persisted in `apps/.app_registry.json`
- Python backend: FastAPI-based, `python/` module
- Shipped v1.3 with ~2,400 LOC added across 28 code files

## Constraints

- **Tech stack**: Python (Flask/FastAPI), vanilla JS/HTML/CSS frontend, Docker
- **Compatibility**: Must not break upstream Agent Zero core behavior
- **Ports**: Apps use range 9000–9099; Agent Zero itself on 50000 (Docker: 50001→80)
- **Mobile-responsive**: All apps must work on phone screens — viewport meta, media queries, flexible layouts are mandatory

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Name-based routing over port exposure | Users shouldn't need to manage ports | ✓ Good |
| noVNC for shared browser | Zero install, browser-based VNC client | ✓ Good |
| Registry in JSON file | Simple, survives restarts, no DB dependency | ✓ Good |
| SKILL.md standard for GSD skills | Compatible with Claude Code, Cursor, Codex | ✓ Good |
| SKILL.md v3 full rewrite over patching v2 | v2 had no validation, no health check, underscore examples — patching wasn't viable | ✓ Good |
| Name validation before resource allocation | Fail fast, no cleanup needed for invalid names | ✓ Good |
| HTTP poll health check (curl loop) | Shell-native, no Python imports, 10s timeout with clear HEALTHY/FAILED branches | ✓ Good |
| YAML-in-markdown catalog format | Machine-readable without parser, human-readable in terminal | ✓ Good |
| SSE + polling fallback for dashboard | SSE simpler than WebSockets, degrades gracefully | ✓ Good |
| flask-basic as default for ambiguous requests | Most flexible template, fewest assumptions | ✓ Good |

---
*Last updated: 2026-03-03 after v1.3 milestone*
