# Phase 13: Interactive CLI Session Lifecycle - Research

**Researched:** 2026-02-25
**Domain:** OpenCode TUI orchestration via tmux, interactive CLI lifecycle management, Docker binary installation
**Confidence:** HIGH (architecture/approach), MEDIUM (OpenCode TUI prompt patterns — empirical observation required)

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CLI-01 | Agent Zero can start an interactive CLI tool in the shared terminal and wait for its initial ready prompt | TUI mode: `opencode send to tmux pane → wait_ready with opencode-specific prompt_pattern`. Must install opencode in Docker first. Startup takes 2–5s; TUI renders logo + bordered input area. |
| CLI-02 | Agent Zero can send a prompt to a running interactive CLI and read its response | TUI mode (persistent process): `tmux_tool send` text + Enter into running opencode pane, then `wait_ready` with timeout=120 and opencode-specific prompt_pattern to wait for LLM response. |
| CLI-03 | Agent Zero can detect when an interactive CLI has finished responding and is ready for next input | Dual-strategy: (1) opencode-specific prompt pattern on last non-blank line (primary); (2) content stability fallback (secondary). Exact pattern requires empirical observation (Plan 13-01). |
| CLI-04 | Agent Zero can interrupt or exit an interactive CLI session cleanly | TUI `/exit` command via `tmux_tool send`; fallback is `keys: C-c`. In v1.2.5, process exits cleanly after `/exit` (hang regression fixed). Verify shell prompt returns post-exit. |
</phase_requirements>

---

## Summary

Phase 13 implements interactive CLI session lifecycle management for OpenCode running in TUI mode inside the shared Docker tmux session. The four requirements (CLI-01 through CLI-04) cover the full lifecycle: start → wait-for-ready → send-prompt → wait-for-response → repeat → exit-cleanly. All four must use `tmux_tool` primitives (Phase 11/12 infrastructure) with prompt patterns derived empirically from the actual installed binary — not assumed from documentation.

The most critical pre-condition discovered during research: **OpenCode is not installed in the Docker container**. The host binary at `/Users/rgv250cc/.opencode/bin/opencode` is a macOS ARM64 Mach-O binary — it cannot run inside the Kali Linux aarch64 container. Plan 13-01 must install a Linux aarch64 OpenCode binary in Docker before any empirical observation can take place. The install method is `curl -fsSL https://opencode.ai/install | bash` inside the container, which places the binary at `/root/.opencode/bin/opencode`.

The v0.15 hang regression that was the original blocker noted in STATE.md has been confirmed **fixed** (issue #3213 closed, fix merged before v1.2.5). OpenCode v1.2.5 explicitly exits after TUI `/exit` via a process.exit() call. There is a separate subprocess.Popen hang issue (#11891, OPEN) but it only affects piped stdout in non-interactive mode; tmux-based TUI interaction is not affected. The opencode run mode (batch, exits per turn) is explicitly NOT the right approach for CLI-01..04 — the requirements describe a persistent interactive session with multi-turn capability, which requires TUI mode.

**Primary recommendation:** Plan 13-01 = install opencode in Docker + run observation session (TUI startup, response boundary, exit). Plan 13-02 = implement CLI-01..04 using verified prompt patterns from Plan 13-01 findings. The `wait_ready` action from Phase 12 is the core primitive; Phase 13 adds a custom `prompt_pattern` for opencode's TUI ready-state indicator (which differs from shell `$ `).

---

## Standard Stack

### Core

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| `tmux_tool` (Phase 11/12) | Project-local | All four terminal interactions (send, keys, read, wait_ready) | Already implemented and verified; the only sentinel-free primitive for shared terminal |
| `TmuxTool.wait_ready` | Phase 12 | Detect CLI ready state with custom `prompt_pattern` | Phase 12 specifically exposes `prompt_pattern` arg for overriding in non-standard CLIs like OpenCode |
| OpenCode binary | v1.2.5 (Linux aarch64) | The interactive CLI under orchestration | Phase 13 is scoped to OpenCode specifically |
| `curl -fsSL https://opencode.ai/install \| bash` | Latest (installs to `/root/.opencode/bin`) | Install OpenCode in Docker | Official install method; supports aarch64 Linux |

### Supporting

| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| `ollama` (host) | Via `host.docker.internal:11434` | LLM backend for opencode in Docker | Required for CLI-02/CLI-03 testing (sending prompts and reading AI responses) |
| `ai.opencode.json` config | `~/.config/opencode/` | Bind-mount or copy to configure opencode's LLM provider in Docker | Must point `baseURL` to `http://host.docker.internal:11434/v1` for Docker-to-host Ollama access |
| `docker exec` + `tmux send-keys` | docker CLI | Run install command or verify binary inside container | Only used in 13-01 setup steps |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| TUI mode (persistent process) | `opencode run` (batch mode, exits per turn) | `opencode run` exits after each response — not a "running interactive CLI session" as required by CLI-01..04. Use `opencode run` for Phase 14 wrapper if TUI proves unreliable, but Phase 13 requirements specify the interactive session pattern. |
| TUI mode in tmux | `opencode serve` HTTP API | `opencode serve` is a headless HTTP server — no terminal interaction, no tmux, no prompt patterns. Valid fallback if TUI has hang issues, but adds HTTP client complexity. STATE.md flags this as fallback only. |
| Install in Docker image (Dockerfile rebuild) | Install at runtime via tmux pane | Rebuild required for Dockerfile change; runtime install works immediately in current container. For Phase 13 observation, runtime install is faster. For production, add to `install_additional.sh`. |

**Installation (inside Docker container):**
```bash
curl -fsSL https://opencode.ai/install | bash
export PATH=/root/.opencode/bin:$PATH
opencode --version   # verify: 1.2.5
```

---

## Architecture Patterns

### Recommended Project Structure

```
python/tools/tmux_tool.py          # No changes needed (Phase 11/12 complete)
prompts/agent.system.tool.tmux.md  # No changes needed (Phase 11/12 complete)
# Phase 13 produces: documented patterns captured in 13-01 observation log
# These patterns feed directly into Phase 14 (OpenCodeSession wrapper) and Phase 15 (SKILL.md)
```

No new Python files in Phase 13. The work product is: (1) verified prompt patterns, startup time, exit sequence from 13-01, and (2) agent-level code in 13-02 that uses `tmux_tool` with the verified patterns.

### Pattern 1: CLI Lifecycle via tmux_tool (CLI-01 through CLI-04)

**What:** Complete four-step lifecycle using Phase 11/12 primitives with empirically verified opencode-specific parameters.

**When to use:** Any time Agent Zero needs to orchestrate OpenCode in the shared terminal.

```python
# CLI-01: Start OpenCode TUI and wait for initial ready state
# send "opencode /path/to/project" to tmux pane
# wait_ready with timeout=30, prompt_pattern=<EMPIRICALLY_DETERMINED>

# Step 1: Send start command
{ "action": "send", "text": "opencode /a0" }
# Step 2: Wait for TUI ready state
{ "action": "wait_ready", "timeout": 30, "prompt_pattern": "<PATTERN_FROM_13-01>" }

# CLI-02 + CLI-03: Send prompt and wait for response
{ "action": "send", "text": "Explain what /a0/python/tools/tmux_tool.py does" }
{ "action": "wait_ready", "timeout": 120, "prompt_pattern": "<PATTERN_FROM_13-01>" }

# Read the response
{ "action": "read", "lines": 200 }

# CLI-04: Exit cleanly
{ "action": "send", "text": "/exit" }
{ "action": "wait_ready", "timeout": 15 }
# Verify shell prompt returned: default r'[$#>%]\s*$' should match
```

**Key parameter: `prompt_pattern`** — The exact regex for opencode's ready state MUST come from 13-01 empirical observation. Placeholder `<PATTERN_FROM_13-01>` must be replaced with actual observed text.

### Pattern 2: OpenCode TUI Startup Observation Protocol (Plan 13-01)

**What:** Structured observation session to capture exact screen text at each lifecycle stage.

**Observation sequence:**
```
1. Verify version: opencode --version  → must match installed version
2. Start TUI:      opencode /a0        → capture screen every 2s during startup
3. Observe:        capture-pane output when TUI is "ready" (blank input area, logo shown)
4. Send prompt:    type a short question, press Enter
5. Observe:        capture-pane output WHILE processing (busy state)
6. Observe:        capture-pane output WHEN response complete (ready-again state)
7. Exit:           type /exit, press Enter
8. Observe:        capture-pane output after exit (shell prompt returned)
```

**What to record from each observation:**
- Exact text of the LAST NON-BLANK LINE at each state
- Whether any `>`, `~`, or special character appears as input indicator
- Whether ANSI stripping leaves a clean pattern-matchable string
- Time from start command to ready state (for `timeout` in CLI-01)
- Time for a short response (for `timeout` guidance in CLI-02/03)

### Pattern 3: Docker-to-Host Ollama Config

**What:** Configure OpenCode in Docker to reach Ollama running on the host machine.

```json
// ~/.config/opencode/ai.opencode.json (to be bind-mounted or copied into Docker)
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama (local)",
      "options": {
        "baseURL": "http://host.docker.internal:11434/v1"
      },
      "models": {
        "qwen2.5-coder:latest": { "name": "Qwen 2.5 Coder (local)" }
      }
    }
  }
}
```

**Note:** `host.docker.internal` resolves to `192.168.65.254` inside Docker Desktop on macOS. This is confirmed reachable from the Docker container as long as Ollama is running on the host.

### Pattern 4: Bind Mount for OpenCode Config (docker-compose.yml addition)

**What:** Mount host opencode config into Docker container so opencode in Docker uses the same provider config.

```yaml
# docker-compose.yml addition to volumes:
- ~/.config/opencode:/root/.config/opencode:ro
```

**Alternative (no docker-compose change):** Copy config manually during 13-01 observation:
```bash
docker exec agent-zero mkdir -p /root/.config/opencode
docker cp ~/.config/opencode/ai.opencode.json agent-zero:/root/.config/opencode/
```

### Anti-Patterns to Avoid

- **Using default `wait_ready` prompt_pattern for OpenCode TUI:** The default `r'[$#>%]\s*$'` matches shell prompts. OpenCode TUI ready state may look completely different (e.g., a blank text input area with specific border characters, not ending in `$`). Using the wrong pattern causes either false positives or infinite waits.
- **Using opencode run mode for CLI-01..04:** `opencode run` exits after each response. CLI-02 says "send a prompt to a **running** interactive CLI" — implies persistent process. Use TUI mode.
- **Hardcoding a prompt pattern without observation:** Any pattern guessed from documentation is hypothesis, not fact. TUI prompt borders depend on terminal size, theme, and version. Must observe actual bytes in the tmux pane.
- **Starting Ollama inside Docker:** Ollama requires a GPU or significant CPU resources; it should run on the host. Docker container should connect to `host.docker.internal` instead.
- **Assuming opencode exits cleanly before checking version:** The hang regression was version-specific (v0.15.x). Current version 1.2.5 has the fix, but ALWAYS verify version at plan start per STATE.md decision.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Prompt detection for OpenCode TUI | New polling logic | `TmuxTool._wait_ready()` with custom `prompt_pattern` | Phase 12 already provides configurable `prompt_pattern` arg; just supply the right pattern from 13-01 observation |
| ANSI stripping of TUI output | New regex | `ANSI_RE` in `tmux_tool.py` | Already handles all ANSI families including OSC sequences; battle-tested in Phase 11/12 |
| Process lifecycle management | Custom subprocess or PTY | tmux_tool `send` + `keys` | TUI runs IN tmux; interact via tmux send-keys, not via PTY or subprocess pipe |
| Session state detection | Parsing TUI screen content structurally | Last-non-blank-line pattern match | TUI output is noisy (borders, status, logo); only the last input indicator line matters |
| Multi-turn conversation tracking | Custom session ID management | OpenCode's built-in `--session` / TUI session continuity | TUI maintains session automatically; use `opencode --session <id>` to resume if needed |

**Key insight:** Phase 12's `wait_ready` was explicitly designed with Phase 13 in mind — the `prompt_pattern` override exists specifically because non-shell CLIs need different patterns. The infrastructure is ready; Phase 13 only needs to discover the right pattern through empirical observation.

---

## Common Pitfalls

### Pitfall 1: OpenCode Not Installed in Docker

**What goes wrong:** Attempting to run `opencode` in the shared tmux session fails with `-bash: opencode: command not found`.

**Why it happens:** The host binary is macOS ARM64 (Mach-O). Docker container is Kali Linux aarch64. Incompatible binary formats. The docker-compose.yml has no opencode volume mount.

**How to avoid:** Plan 13-01 first task: install opencode in Docker using `curl -fsSL https://opencode.ai/install | bash` (via docker exec or tmux send). Add `/root/.opencode/bin` to PATH for the tmux session. Verify with `opencode --version` before proceeding.

**Warning signs:** `tmux_tool send "opencode --version"` followed by `read` shows "command not found".

### Pitfall 2: Wrong prompt_pattern for OpenCode TUI Ready State

**What goes wrong:** `wait_ready` either returns immediately (false positive) or times out indefinitely (false negative) when waiting for OpenCode to be ready for input.

**Why it happens:** OpenCode TUI does NOT present a traditional shell prompt like `$ `. Its input area is a bordered TUI widget — after ANSI stripping it might look like empty space, or it might show a specific indicator character. Using `r'[$#>%]\s*$'` will not match the actual TUI state.

**How to avoid:** Plan 13-01 empirical observation is mandatory before Plan 13-02 implementation. Capture the pane at the "ready" state and inspect the last non-blank line to determine the actual pattern.

**Warning signs:** In Plan 13-02, `wait_ready` always returns "timed out" even when the TUI is clearly visible in the browser terminal.

### Pitfall 3: Ollama Not Running During CLI-02/03 Testing

**What goes wrong:** OpenCode TUI starts but hangs when you send a prompt — it tries to reach Ollama at `localhost:11434` (container-local, not host), gets connection refused, and either hangs or shows an error.

**Why it happens:** The existing `ai.opencode.json` config points to `localhost:11434`. Inside Docker, `localhost` is the container itself — Ollama is not there. The config must be updated to use `host.docker.internal:11434` for Docker-to-host connectivity.

**How to avoid:** Before running Plan 13-01 observation, ensure: (a) Ollama is started on the host (`ollama serve`), (b) opencode config inside Docker points to `host.docker.internal:11434` not `localhost:11434`.

**Warning signs:** OpenCode TUI starts, logo appears, but sending a prompt produces a network error or infinite spinner.

### Pitfall 4: TUI Exit Hang (Historical — v0.15.x, NOT v1.2.5)

**What goes wrong:** In opencode v0.15.0–v0.15.2, issuing `/exit` or Ctrl+C in the TUI caused a hang of 50+ seconds waiting for the `ensureTitle()` LLM call to complete.

**Why it happens:** The `ensureTitle()` function generated session titles via LLM but lacked a timeout, blocking graceful shutdown.

**How to avoid:** This regression is **fixed** in v1.2.5 (issue #3213 closed). The fix adds explicit `process.exit()` calls in `exit.tsx`, `worker.ts`, and `run.ts`. VERIFY `opencode --version` equals 1.2.5 or later before testing CLI-04 exit behavior. If a future rebuild installs a different version, re-check for hang regression.

**Warning signs:** After `/exit`, `wait_ready` times out and `read` shows the TUI still on screen instead of the shell prompt.

### Pitfall 5: Subprocess.Popen Hang (Issue #11891 — affects run mode, NOT TUI)

**What goes wrong:** When using `opencode run <prompt>` via Python subprocess.Popen, the process hangs waiting for a permission dialog that it can't render.

**Why it happens:** In headless subprocess mode, OpenCode may invoke the "question tool" requesting user permission — a dialog that renders in TUI but blocks forever in piped stdout mode.

**How to avoid:** Phase 13 uses TUI mode via tmux (not subprocess.Popen), so this bug does NOT apply. The workaround (`"permission": "allow"` in config) is only needed if you were using `opencode run` via subprocess. If Phase 14's `OpenCodeSession` wrapper uses `opencode run` via subprocess (possible), add `"permission": "allow"` to the config.

**Warning signs:** Only appears in subprocess/non-terminal opencode run mode. Not relevant for tmux TUI interaction.

### Pitfall 6: TUI Startup Logo Masking the Ready State

**What goes wrong:** After starting opencode in the tmux pane, the screen shows the ANSI logo art with box-drawing characters. ANSI stripping may leave garbled text, and `wait_ready` may trigger too early on logo content.

**Why it happens:** The opencode TUI renders a full-screen logo on startup before the input area becomes active. This logo contains box-drawing characters (`█`, `▄`, `▀`) that survive ANSI stripping as Unicode characters.

**How to avoid:** In Plan 13-01 observation, capture multiple samples during startup (at t=0.5s, t=1s, t=2s, t=3s, t=5s) to see what the pane looks like at each stage. The stable "ready" state should be distinguishable from the startup rendering. Consider using a unique text pattern that appears in the stable ready state — likely the input cursor area or a status bar element.

**Warning signs:** `wait_ready` returns "ready (stable)" immediately after `opencode` start, before the TUI input area is actually ready.

---

## Code Examples

Verified patterns from project source and empirical analysis:

### OpenCode Installation in Docker (via docker exec)
```bash
# Run from host during Plan 13-01 setup (or via tmux_tool send in the agent)
docker exec agent-zero bash -c "curl -fsSL https://opencode.ai/install | bash"
docker exec agent-zero bash -c "echo 'export PATH=/root/.opencode/bin:\$PATH' >> /root/.bashrc"
docker exec agent-zero bash -c "export PATH=/root/.opencode/bin:\$PATH && opencode --version"
```

### OpenCode Config for Docker (host.docker.internal)
```bash
# Copy config into Docker container to point Ollama at host.docker.internal
docker exec agent-zero mkdir -p /root/.config/opencode
docker cp ~/.config/opencode/ai.opencode.json agent-zero:/root/.config/opencode/ai.opencode.json
# Edit inside container to replace localhost with host.docker.internal
docker exec agent-zero sed -i 's|localhost:11434|host.docker.internal:11434|g' /root/.config/opencode/ai.opencode.json
```

### CLI Lifecycle via tmux_tool (skeleton — prompt_pattern TBD from 13-01)
```python
# CLI-01: Start OpenCode TUI
send_result = tmux_tool(action="send", text="opencode /a0")
ready = tmux_tool(action="wait_ready", timeout=30, prompt_pattern="<OBSERVED_READY_PATTERN>")
# Check ready.message for "ready (prompt matched)" or "ready (stable)"

# CLI-02: Send a prompt
send_result = tmux_tool(action="send", text="What does /a0/python/tools/tmux_tool.py do?")

# CLI-03: Wait for response
ready = tmux_tool(action="wait_ready", timeout=120, prompt_pattern="<OBSERVED_READY_PATTERN>")
response = tmux_tool(action="read", lines=300)

# Repeat CLI-02 + CLI-03 for multi-turn...

# CLI-04: Exit
send_result = tmux_tool(action="send", text="/exit")
shell_ready = tmux_tool(action="wait_ready", timeout=15)
# Default prompt_pattern r'[$#>%]\s*$' should detect shell prompt return
```

### Prompt Pattern Test (for 13-01 observation)
```python
# Run after capturing TUI ready state to test what the last non-blank line looks like
import subprocess, re
ANSI_RE = re.compile(r'\x1b(?:\][^\x07]*\x07|[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
result = subprocess.run(
    ["tmux", "capture-pane", "-t", "shared", "-p", "-S", "-50"],
    capture_output=True, text=True
)
clean = ANSI_RE.sub("", result.stdout).rstrip()
lines = [l for l in clean.splitlines() if l.strip()]
print("Last non-blank line:", repr(lines[-1]) if lines else "(empty)")
print("Full clean output:")
print(clean)
```

### Version Check (mandatory at Plan 13-01 start)
```bash
# Inside Docker (via docker exec or tmux_tool send):
opencode --version
# Expected: 1.2.5
# If < 1.2.5: assess hang regression risk before proceeding (see STATE.md)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded `sleep N` after interactive CLI start | `wait_ready` with `prompt_pattern` override | Phase 12 (ready for Phase 13) | Eliminates timing fragility; detects readiness based on actual terminal state |
| Assuming opencode exits cleanly (v0.15.x era) | Verified clean exit in v1.2.5 | Issue #3213 fixed ~Jan 2026 | Can reliably use `/exit` for CLI-04; no need for `opencode serve` fallback |
| `opencode serve` as backup for hang regression | TUI mode primary (regression fixed) | v1.2.5 confirmed | Simplifies Phase 13 implementation; TUI is the natural interactive approach |
| Single timeout for all CLI tools | Per-CLI `timeout` argument in `wait_ready` | Phase 12 design | Phase 13 sets `timeout=120` for AI response waits vs `timeout=10` for shell commands |

**Deprecated/outdated:**
- `opencode serve` HTTP mode as primary approach: was the fallback if TUI hung in v0.15. Not needed for v1.2.5. Still valid if someone needs headless HTTP API access.
- Fixed `await asyncio.sleep(10)` between sends: replaced by `wait_ready` with `timeout=120`.

---

## Open Questions

1. **What exactly does OpenCode TUI show on the last non-blank line when ready for input?**
   - What we know: TUI uses a Bubble Tea / SolidJS-based interface with a bordered input area; prompt is a styled text widget; processing state disables the widget; ANSI stripping leaves box-drawing characters
   - What's unclear: The exact text pattern of the last non-blank line in the "ready" state after ANSI stripping. Could be `>`, `~>`, a blank line with only box-drawing chars, or something else entirely.
   - Recommendation: This is the central empirical question of Plan 13-01. Cannot be answered without running the binary. The observation protocol in Plan 13-01 must capture this at multiple stages.

2. **What text appears on screen DURING AI processing (busy state)?**
   - What we know: The prompt widget enters "disabled" state during model execution; a spinner or progress indicator likely appears
   - What's unclear: What specific text/pattern appears that distinguishes "processing" from "ready"
   - Recommendation: Capture pane content every 2 seconds after sending a prompt. Document what the last non-blank line looks like during processing vs after completion.

3. **Does the stability fallback (identical consecutive captures) reliably distinguish opencode "processing" from "ready"?**
   - What we know: During AI response generation, text streams to the screen (content changes); when done, screen stabilizes
   - What's unclear: Whether the stability check fires too early if the model pauses mid-response (buffering), or too late if the terminal has an animated spinner that keeps changing
   - Recommendation: Test with both a short (1-line) and long (multi-paragraph) prompt. If stability fires prematurely, may need to combine with prompt pattern match (currently the design already does this: prompt pattern is primary, stability is secondary).

4. **Does opencode require any interactive auth on first startup in Docker?**
   - What we know: opencode stores auth in `~/.local/share/opencode/`; Ollama provider has no API key; the config uses Ollama with `npm: "@ai-sdk/openai-compatible"`
   - What's unclear: Whether first startup in a fresh Docker environment prompts for any auth or "welcome" interaction
   - Recommendation: Plan 13-01 observation will reveal this. If an auth prompt appears, it must be handled (or pre-empted by copying auth files from host) before proceeding to CLI lifecycle testing.

5. **Should Plan 13-02 add opencode installation to `install_additional.sh` for permanent Docker image inclusion?**
   - What we know: Runtime installation works for testing but is not persistent across container rebuilds
   - What's unclear: Whether the project wants opencode permanently in the Docker image (requires Dockerfile rebuild) or installed on demand
   - Recommendation: Install at runtime for Phase 13 (no rebuild required). If Phase 14/15 usage is production-critical, add to `install_additional.sh` in a separate sub-task. This is a project scope decision that falls outside Plan 13-02.

---

## Sources

### Primary (HIGH confidence)

- `/Users/rgv250cc/Documents/Projects/agent-zero/python/tools/tmux_tool.py` — Phase 11/12 implementation; all four actions confirmed implemented; `wait_ready` with `prompt_pattern` arg; ANSI_RE regex
- `/Users/rgv250cc/Documents/Projects/agent-zero/.planning/REQUIREMENTS.md` — CLI-01..04 definitions; explicit exclusions (pexpect, libtmux, TTYSession, sentinel injection); traceability table
- `/Users/rgv250cc/Documents/Projects/agent-zero/.planning/STATE.md` — Phase 13 decisions: empirical-first approach; hang regression check required; opencode serve as fallback noted
- `/Users/rgv250cc/Documents/Projects/agent-zero/.planning/ROADMAP.md` — Phase 13 two-plan structure; 13-01 observation + 13-02 implementation; Phase 14 OpenCodeSession wrapper context
- `/Users/rgv250cc/Documents/Projects/agent-zero/usr/skills/claude-cli/SKILL.md` — Pattern reference for multi-turn CLI orchestration; HOST-ONLY scope note (opencode follows same constraint)
- `/Users/rgv250cc/Documents/Projects/agent-zero/docker-compose.yml` — Volume mounts confirmed: python, prompts, webui, apps; NO opencode mount; confirms installation gap
- `docker exec agent-zero` runtime inspection — Container is Kali Linux aarch64; tmux session "shared" confirmed running; opencode confirmed NOT installed; prompt pattern: `(venv) root@<id>:/a0/apps/shared-terminal# `
- `/Users/rgv250cc/.opencode/bin/opencode` — macOS ARM64 binary (Mach-O); version 1.2.5; `--help` output shows TUI (default), `run`, `serve`, `session` commands
- `curl -fsSL https://opencode.ai/install` install script — Confirmed install dir: `$HOME/.opencode/bin`; supports `aarch64` (maps to `arm64`); binary from `github.com/anomalyco/opencode/releases`

### Secondary (MEDIUM confidence)

- GitHub Issue #3213 (sst/opencode) — v0.15 hang regression; CLOSED/COMPLETED; root cause was `ensureTitle()` blocking on LLM request; fix: `process.exit()` in exit.tsx/worker.ts/run.ts (WebFetch verified)
- GitHub Issue #4506 (sst/opencode) — Hang on config errors; CLOSED; fix: enhanced error handling with guaranteed process exit; merged via PR #13168 (WebFetch verified)
- GitHub Issue #11891 (anomalyco/opencode) — subprocess.Popen hang in `opencode run --format json`; OPEN; root cause: question tool permission dialog in non-PTY mode; workaround: `"permission": "allow"` config (WebFetch verified)
- `opencode.ai/docs/tui/` — TUI commands: `/exit` (aliases `/quit`, `/q`); keybind `ctrl+x q`; input is bordered text widget; disabled during processing (WebFetch, official docs)
- `opencode.ai/docs/cli/` — `opencode run` flags: `--session`/`-s`, `--continue`/`-c`, `--format json`; non-interactive batch mode (WebFetch, official docs)
- `opencode.ai/changelog` — v1.2.14 down to v1.1.61 listed; v1.2.0 added timeout config CLI flag; no explicit hang fix entry but issue #3213 closed before these versions (WebFetch, official changelog)
- `deepwiki.com/sst/opencode/6.2-terminal-user-interface-(tui)` — TUI lifecycle: SSE streaming, message.completed event, sticky scroll, disabled/enabled prompt state transitions (WebFetch)
- `deepwiki.com/sst/opencode/6.5-tui-prompt-component-and-input-handling` — Prompt has left border with color changes; disabled prop during processing; extmarks for attached files (WebFetch)

### Tertiary (LOW confidence)

- `~/.config/opencode/ai.opencode.json` — Ollama provider config with `localhost:11434`; models: qwen3:8b, qwen2.5-coder. Valid for host; needs `host.docker.internal` for Docker. Format confirmed valid for v1.2.5.
- Host docker.internal connectivity test — `192.168.65.254` resolves inside Docker; Ollama port 11434 refused (Ollama not running at test time); connectivity confirmed working when Ollama runs.

---

## Metadata

**Confidence breakdown:**
- Standard stack (tmux_tool primitives): HIGH — fully implemented in Phase 11/12, actively tested in Phase 12 UAT
- OpenCode installation approach: HIGH — official install script confirmed; aarch64 support verified; Docker path determined
- Architecture (TUI vs run mode): HIGH — requirements unambiguously require persistent interactive process (multi-turn CLI-02, CLI-03 "running" language)
- v0.15 hang regression status: HIGH — issue #3213 confirmed closed with fix merged before v1.2.5
- OpenCode TUI prompt pattern: LOW — must be empirically observed; cannot determine from docs alone. This is the central unknown that Plan 13-01 exists to resolve.
- Ollama/LLM connectivity: MEDIUM — host.docker.internal confirmed reachable from Docker; Ollama not running at research time; config change needed for Docker baseURL

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 for OpenCode-specific patterns (fast-moving project; check changelog before Plan 13-02 if >2 weeks since 13-01); stable indefinitely for tmux/Python stack findings
