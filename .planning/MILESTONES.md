# Milestones

## v1.3 -- App Builder

**Shipped:** 2026-03-03
**Focus:** Agent Zero reliably creates, configures, and manages web apps using the Apps System with a rich template library and intelligent template selection

### What Shipped

| Feature | Status |
|---------|--------|
| web-app-builder SKILL.md v3.0.0 rewrite (mandatory 8-step sequence) | Shipped |
| System prompt integration (app request routing) | Shipped |
| Name validation and health-check polling | Shipped |
| Real-time dashboard template (SSE + Chart.js) | Shipped |
| File/media tool template (drag-drop + conversion) | Shipped |
| CRUD app template (Flask + SQLite) | Shipped |
| Utility SPA template (minimal skeleton) | Shipped |
| Template catalog (_CATALOG.md) with structured metadata | Shipped |
| _GUIDE.md decision tree for all 7 templates | Shipped |
| Auto-selection with keyword matching and user override | Shipped |

### Stats

- **Phases:** 16-18 (3 phases, 6 plans, 11 tasks)
- **Requirements:** 11/11 satisfied (SKILL-01–05, TMPL-01–06)
- **Git range:** 228f1e3 → 5cdf132
- **Code:** ~2,400 lines added across 28 files
- **Audit:** TECH DEBT — 6 info-level items, zero runtime blockers

### Key Accomplishments

1. Rewrote web-app-builder SKILL.md v3.0.0 with mandatory 8-step sequence, name validation, and post-start health-check polling
2. Added system prompt routing so the agent always uses the Apps System for app requests
3. Built 4 new production-quality templates: utility SPA, real-time dashboard, CRUD app, file/media tool
4. Created machine-readable template catalog with structured metadata for all 7 templates
5. Updated decision tree covering all 7 templates with clear selection criteria
6. Added auto-selection logic with keyword matching and user override

### Phases

| Phase | Name | Status |
|-------|------|--------|
| 16 | Skill Reliability Core | Complete |
| 17 | Template Library Expansion | Complete |
| 18 | Template Catalog and Auto-Selection | Complete |

---

## v1.2 -- Terminal Orchestration

**Shipped:** 2026-02-25
**Focus:** Agent Zero interacts with the shared terminal and interactive CLIs

### What Shipped

| Feature | Status |
|---------|--------|
| tmux primitives (send, keys, read, wait_ready) | Shipped |
| Interactive CLI lifecycle (start, send, detect, exit) | Shipped |
| OpenCode session wrapper | Shipped |
| CLI orchestration skill documentation | Shipped |

### Phases

| Phase | Name | Status |
|-------|------|--------|
| 11 | tmux Primitive Infrastructure | Complete |
| 12 | Readiness Detection | Complete |
| 13 | Interactive CLI Session Lifecycle | Complete |
| 14 | OpenCode Session Wrapper | Complete |
| 15 | CLI Orchestration Skill Documentation | Complete |

---

## v1.1 -- Reliability

**Shipped:** 2026-02-25
**Focus:** CDP health checks, browser verification, Claude CLI control

### What Shipped

| Feature | Status |
|---------|--------|
| CDP startup health-check (sleep to poll) | Shipped |
| Browser navigate-with-verification | Shipped |
| Claude CLI single-turn + env fix | Shipped |
| Claude CLI multi-turn sessions | Shipped |
| Claude CLI skill documentation | Shipped |

### Phases

| Phase | Name | Status |
|-------|------|--------|
| 6 | CDP Startup Health-Check | Complete |
| 7 | Browser Navigate-with-Verification | Complete |
| 8 | Claude CLI Single-Turn + Env Fix | Complete |
| 9 | Claude CLI Multi-Turn Sessions | Complete |
| 10 | Claude CLI Skill Documentation | Complete |

---

## v1.0 -- Foundation & Apps System

**Shipped:** 2026-02-25
**Focus:** Build the core Apps System and enhanced Agent Zero experience

### What Shipped

| Feature | Status |
|---------|--------|
| Apps System (port allocation, routing, proxy) | Shipped |
| App Manager (registry, lifecycle, autostart) | Shipped |
| Web App API (`/webapp/*` endpoints) | Shipped |
| Apps Modal UI (gallery, controls, status) | Shipped |
| Shared Browser (noVNC + VNC) | Shipped |
| Shared Terminal (tmux + ttyd) | Shipped |
| GSD Skill Pack (50 skills) | Shipped |
| Neon UI Theme (light/dark) | Shipped |
| App Templates (Flask Basic, Dashboard, Static HTML) | Shipped |
| Skill Forge + Web App Builder | Shipped |
| Welcome screen redesign + auto-reload | Shipped |

### Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | Apps System Core | Complete |
| 2 | Core Built-in Apps | Complete |
| 3 | GSD Skill Pack | Complete |
| 4 | Neon UI + UX | Complete |
| 5 | Scaffolding + Skills | Complete |

---

*Milestone v1.0 archived: 2026-02-25*
*Milestone v1.1 archived: 2026-02-25*
*Milestone v1.2 archived: 2026-02-25*
*Milestone v1.3 archived: 2026-03-03*

