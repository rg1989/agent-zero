

## 🔀 Fork Enhancements

> This is a heavily extended fork of [frdel/agent-zero](https://github.com/frdel/agent-zero), built by **[Roman Grinevich](https://github.com/rg1989/)** — [LinkedIn](https://www.linkedin.com/in/roman-grinevich-03b13bab/).
> Nearly every commit beyond the initial setup represents original work — covering infrastructure, agent capabilities, UI, and structured workflows.
> Below is a summary of what has been built on top of the upstream base.

---

### 🧩 1. Smart App Hosting System — Port-Free, URL-First

The biggest infrastructure addition is a **first-class web app hosting layer** built directly into the Docker container. Agents can create, register, start, and stop web applications — each accessible at a clean `/{app-name}/` URL, with ports completely hidden from the user.

**How it works:**
- Apps run internally on ports `9000–9099`
- A FastAPI proxy middleware (`python/helpers/app_proxy.py`) routes `/{app-name}/` → the correct internal port, for both HTTP and WebSockets
- App metadata is stored in a persistent JSON registry (`apps/.app_registry.json`) that survives container restarts
- The `AppManager` singleton (`python/helpers/app_manager.py`) handles lifecycle: register, start, stop, restart, status, autostart
- A REST API (`/webapp`) lets agents and the UI manage the full app lifecycle programmatically

**Built-in apps:**
| App | Port | Description |
|-----|------|-------------|
| `shared-browser` | 9003 | Headless Chromium via CDP — agent + user browser |
| `shared-terminal` | 9004 | Web terminal via ttyd + tmux — agent + user terminal |

**Agent capability:** agents use a `web_app_builder` skill and templates to scaffold, register, and open new apps in the UI drawer — all without ever touching a port number.

---

### 🌐 2. Shared Browser — CDP Infrastructure for Agent + User

The shared browser replaces the legacy VNC stack with a **native Chrome DevTools Protocol (CDP)** implementation. Both the human user (via the in-UI browser panel) and the agent can interact with the same live Chromium instance.

**Technical highlights:**
- Headless Chromium runs inside Docker, exposed at port 9222 (CDP) and `9003` (control UI)
- `apps/shared-browser/app.py`: Flask server implementing a REST API over CDP WebSocket — screenshot, click, scroll, keyboard, navigate, evaluate JS
- `startup.sh`: polls CDP `/json` endpoint before marking the service ready (health-check, not a blind sleep)
- `usr/skills/shared-browser/SKILL.md`: documents the **Observe → Act → Verify** workflow pattern, including `navigate_and_wait()` which polls `document.readyState === 'complete'` after every navigation — no more race conditions
- Fully accessible to the agent via skills, and to the user via the UI drawer

---

### 💻 3. Shared Terminal — tmux Infrastructure for Agent + User

The shared terminal provides a **persistent tmux session** accessible from both the browser (via ttyd) and the agent (via tmux primitives).

**Architecture:**
- `apps/shared-terminal/startup.sh`: pre-creates a `tmux new-session -d -s shared` so the session survives UI disconnects
- ttyd serves the terminal in the browser at `/shared-terminal/`
- The agent interacts with the same session via `python/tools/tmux_tool.py`

**TmuxTool** (`python/tools/tmux_tool.py`) exposes five atomic primitives the agent calls directly:

| Action | Description |
|--------|-------------|
| `send` | Type text + Enter into the tmux pane |
| `keys` | Send special key combos (Ctrl+P, Tab, Escape, etc.) |
| `read` | Capture current pane content, ANSI-stripped |
| `wait_ready` | Poll until a shell prompt pattern appears or output stabilizes |

These primitives enable the agent to **act exactly like a human user at the keyboard** — including navigating TUI applications, responding to prompts, and reading live output.

---

### 🤖 4. CLI Orchestration — Claude Code & OpenCode via tmux (Subscription, Not API Key)

The most novel capability: the agent can **drive interactive coding CLIs** (Claude Code, OpenCode) as if it were a human user, **using a subscription account instead of paying per API token**.

This is architecturally significant — instead of calling Claude via API key, the agent launches Claude Code or OpenCode inside the shared tmux session, types prompts, reads responses, and chains multi-turn conversations. Cost: subscription flat rate. Quality: full model access.

#### Claude CLI (`python/helpers/claude_cli.py`)

- **Single-turn**: `claude_single_turn(prompt)` — subprocess call with `--print --output-format json`, parses response
- **Multi-turn**: `claude_turn(prompt, session_id)` — uses `--resume UUID` for stateful chaining; `ClaudeSession` wrapper auto-tracks session ID
- **Critical env fix**: `CLAUDECODE=1` is set by Claude Code and blocks nested `claude` binary launches. Fix: build a clean `env` dict per subprocess call, never mutating global `os.environ`
- **Dead session recovery**: `claude_turn_with_recovery()` detects expired sessions and restarts transparently

#### OpenCode (`python/helpers/opencode_cli.py`)

OpenCode runs as a full TUI inside tmux — there's no subprocess mode. The integration was built through **empirical observation** (documented in `.planning/phases/13-01-OBSERVATION.md`):

- `OpenCodeSession.start()`: launches OpenCode via `tmux send-keys`, waits for the specific prompt pattern
- `OpenCodeSession.send(prompt)`: types the prompt, waits for readiness using dual-strategy polling (prompt pattern match + output stability fallback)
- `OpenCodeSession.exit()`: uses Ctrl+P command palette → `exit` (NOT `/exit` — triggers an agent-picker bug in OpenCode v1.2.14)
- All ANSI escape codes stripped from captured output

#### CLI Orchestration Skill (`usr/skills/cli-orchestration/SKILL.md`)

Documents the complete orchestration patterns: when to use single-turn vs. multi-turn, session coordination, completion detection, security considerations, and anti-patterns to avoid.

---

### 📦 5. GSD Skill Pack — 50+ Structured Agent Skills

A full **Get Stuff Done (GSD)** skill pack is bundled in `usr/skills/`, using the open `SKILL.md` standard (compatible with Claude Code, Cursor, Codex CLI, Copilot, and Goose).

Skills are organized into four layers:

| Layer | Count | Examples |
|-------|-------|---------|
| **GSD Orchestrators** | 20+ | `plan-phase`, `execute-phase`, `verify-work`, `new-project`, `audit-milestone` |
| **GSD Subagents** | 10+ | `gsd-planner`, `gsd-executor`, `gsd-verifier`, `gsd-debugger`, `gsd-roadmapper` |
| **Specialist Roles** | 8 | `architect`, `backend-developer`, `frontend-developer`, `qa-tester`, `security-auditor` |
| **App & Skill Builders** | 3 | `web-app-builder`, `skill-forge`, `cli-orchestration` |

The GSD framework enables **structured, multi-phase project execution** with planning, verification, and gap-closure loops — all orchestrated by the agent itself using skills as its operational vocabulary.

---

### 🎨 6. Neon UI Theme

A custom **neon-mode UI theme** was applied to the webui (`webui/index.css`, ~38KB) with:
- Dynamic glow colors on hover (randomized per element, CSS `filter` based)
- Full dark/light mode support
- Styled app drawer with animated slide-in/out
- Clean tab system for managing open apps

---

### 🗺️ Planning-Driven Development

All enhancements were built using the GSD workflow, with a full planning directory (`.planning/`) tracking:
- `PROJECT.md` — goals, validated requirements, key decisions
- `ROADMAP.md` — phased milestones (v1.0 shipped, v1.1 shipped, v1.2 complete)
- Per-phase plans, research docs, observation files, and UAT results

**Shipped milestones:**

| Milestone | Phases | What was built |
|-----------|--------|----------------|
| v1.0 | 1–5 | Apps system, shared browser (noVNC→CDP), shared terminal, GSD skill pack, Neon UI |
| v1.1 | 6–10 | CDP startup health-check, navigate-with-verification, Claude CLI single + multi-turn |
| v1.2 | 11–15 | TmuxTool primitives, readiness detection, OpenCode lifecycle, OpenCodeSession, CLI orchestration skill |

