# Agent Zero — Enhanced Fork

## What This Is

A personal fork of [Agent Zero](https://github.com/frdel/agent-zero) — a general-purpose agentic AI framework — extended with an Apps System for running and managing web applications, a Neon UI theme, GSD skill packs, and core built-in apps (shared browser via VNC, shared terminal via tmux). The fork is designed for local/Docker use as a personal AI workstation with first-class web app hosting capabilities.

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

### Active

<!-- Current scope. Building toward these. -->

- [ ] BROWSER-01: Agent Zero navigates to URLs via CDP Page.navigate (not visual address bar)
- [ ] BROWSER-02: Agent Zero observes browser state with screenshot before every browser action
- [ ] BROWSER-03: Agent Zero verifies navigation succeeded (URL/title check)
- [ ] BROWSER-04: Shared browser Chromium always starts with CDP remote origins enabled
- [ ] BROWSER-05: Agent Zero follows Observe → Act → Verify for all browser interactions
- [ ] CLAUDE-01: Agent Zero can launch `claude` CLI in shared terminal or as a subprocess
- [ ] CLAUDE-02: Agent Zero can send a prompt to a running claude session and receive a response
- [ ] CLAUDE-03: Agent Zero can detect when claude has finished responding
- [ ] CLAUDE-04: Agent Zero can run a complete multi-turn session with claude
- [ ] CLAUDE-05: Dedicated skill documents the complete claude CLI interaction pattern

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Upstream Agent Zero core changes — this is a fork; upstream changes are pulled separately
- Mobile app — web-first, desktop/Docker target
- Multi-user / auth system — single-user personal assistant

## Context

- Fork of [frdel/agent-zero](https://github.com/frdel/agent-zero) — upstream divergence managed manually
- Runs via Docker or local Python; accessed at `http://localhost:50000`
- `apps/` directory holds all web apps; core apps are `shared-browser` and `shared-terminal`
- `apps/_templates/` provides scaffolding for new apps
- `usr/skills/` holds custom skills; `skills/` holds GSD skill pack
- `webui/` is the frontend (vanilla JS/HTML/CSS with Alpine.js)
- Registry persisted in `apps/.app_registry.json`
- Python backend: FastAPI-based, `python/` module

## Constraints

- **Tech stack**: Python (Flask/FastAPI), vanilla JS/HTML/CSS frontend, Docker
- **Compatibility**: Must not break upstream Agent Zero core behavior
- **Ports**: Apps use range 9000–9099; Agent Zero itself on 50000 (Docker: 50001→80)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Name-based routing over port exposure | Users shouldn't need to manage ports | ✓ Good |
| noVNC for shared browser | Zero install, browser-based VNC client | ✓ Good |
| Registry in JSON file | Simple, survives restarts, no DB dependency | ✓ Good |
| SKILL.md standard for GSD skills | Compatible with Claude Code, Cursor, Codex | ✓ Good |

## Current Milestone: v1.1 Reliability

**Goal:** Make browser control and Claude Code CLI work reliably as intended

**Target features:**
- Browser: CDP-based navigation, observe-act-verify workflow, Chromium CDP startup fix
- Claude Code CLI: launch, interactive control, multi-turn sessions, dedicated skill

---
*Last updated: 2026-02-25 after GSD initialization (new-milestone)*
