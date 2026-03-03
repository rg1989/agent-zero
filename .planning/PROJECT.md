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
- ✓ CDP startup health-check: curl-based poll on /json endpoint before Agent Zero connects — v1.1
- ✓ Browser navigate-with-verification: `navigate_and_wait()` with readyState poll, Observe→Act→Verify in SKILL.md — v1.1
- ✓ Claude CLI single-turn: `claude_single_turn()` with CLAUDECODE env fix — v1.1
- ✓ Claude CLI multi-turn: `ClaudeSession` with `--resume UUID`, session recovery — v1.1
- ✓ Claude CLI skill: `usr/skills/claude-cli/SKILL.md` documents complete interaction pattern — v1.1
- ✓ tmux primitives: send text/keys, read screen, wait_ready with prompt detection + idle fallback — v1.2
- ✓ Interactive CLI lifecycle: start, send, detect readiness, exit cleanly — v1.2
- ✓ OpenCode session wrapper: `OpenCodeSession` class with `.start()/.send()/.exit()` — v1.2
- ✓ CLI orchestration skill: `usr/skills/cli-orchestration/SKILL.md` with Read-Detect-Write-Verify cycle — v1.2

### Active

<!-- Current scope. Building toward these. -->

(Defined in REQUIREMENTS.md — v1.3 App Builder)

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

## Current Milestone: v1.3 App Builder

**Goal:** Agent Zero reliably creates, configures, and manages web apps using the Apps System — every time, not just sometimes — with a rich template library for instant scaffolding

**Target features:**
- Bulletproof web-app-builder skill rewrite with mandatory verification steps
- System prompt integration so the agent always knows about the Apps System
- Expanded template library: dashboards, file/media tools, CRUD apps, utilities
- Template auto-selection with user override capability

---
*Last updated: 2026-03-03 after milestone v1.3 started*
