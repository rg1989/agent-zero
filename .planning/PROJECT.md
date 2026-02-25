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

### Active

<!-- Current scope. Building toward these. -->

- [ ] TERM-01: Agent Zero can send text + Enter to a named tmux pane (shared terminal)
- [ ] TERM-02: Agent Zero can send text without Enter (partial input to interactive prompt)
- [ ] TERM-03: Agent Zero can send special keys to tmux pane (Ctrl+C, Ctrl+D, Tab, arrows)
- [ ] TERM-04: Agent Zero can capture current terminal screen content (tmux capture-pane)
- [ ] TERM-05: Agent Zero can detect when terminal is ready for input (prompt detection + idle fallback)
- [ ] CLI-01: Agent Zero can start an interactive CLI session in the shared terminal
- [ ] CLI-02: Agent Zero can send prompts to a running interactive CLI and read responses
- [ ] CLI-03: Agent Zero can detect when a CLI has finished responding and is ready for next input
- [ ] CLI-04: Agent Zero can gracefully interrupt or exit an interactive CLI session
- [ ] CLI-05: Pre-built OpenCode CLI orchestration wrapper (`opencode_session()`)
- [ ] CLI-06: Generic CLI orchestration skill documents the complete pattern for any CLI tool

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

## Current Milestone: v1.2 Terminal Orchestration

**Goal:** Agent Zero can interact with the shared terminal and interactive CLIs as a human would — type, read screen, send special keys, detect readiness — enabling orchestration of any CLI agent

**Target features:**
- tmux_tool: new Python tool for sending/reading shared terminal (tmux send-keys + capture-pane)
- Prompt detection: poll-based readiness check with prompt pattern + idle timeout fallback
- OpenCode CLI wrapper: `opencode_session()` following ClaudeSession pattern from v1.1
- CLI orchestration skill: `usr/skills/cli-orchestration/SKILL.md` for generic + tool-specific patterns

---
*Last updated: 2026-02-25 after milestone v1.2 started*
