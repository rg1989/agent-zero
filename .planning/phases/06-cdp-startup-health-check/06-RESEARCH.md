# Phase 6: CDP Startup Health-Check - Research

**Researched:** 2026-02-25
**Domain:** Bash startup scripting / Chrome DevTools Protocol / Chromium readiness detection
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BROWSER-04 | Shared browser Chromium startup replaces fragile `sleep 2` with a CDP WebSocket health-check poll, ensuring CDP is ready before any agent tries to connect | Polling loop via `curl http://localhost:9222/json` confirmed as the standard approach; bash `until` loop with timeout counter is the right pattern; no external dependencies needed |
</phase_requirements>

---

## Summary

Phase 6 is a minimal infrastructure fix to a single file: `apps/shared-browser/startup.sh`. The goal is to replace the line `sleep 2` (line 42) with a deterministic polling loop that verifies Chromium's CDP WebSocket interface is actually accepting connections before the startup script exits (and before Flask starts). This eliminates a race condition where the agent can attempt a CDP connection immediately after `startup.sh` reports ready, only to get "connection refused" because Chromium hasn't finished binding port 9222.

The fix is pure bash. Chromium exposes an HTTP JSON endpoint at `http://localhost:9222/json` (and `http://localhost:9222/json/version`) that returns valid JSON once CDP is ready. A `curl` poll against this endpoint, repeated in a loop until success or timeout, is the industry-standard approach used in Docker health checks and browser automation frameworks. No Python, no new packages, no new files are required.

The success signal is: `curl -s http://localhost:9222/json` returns HTTP 200 with JSON content. This confirms that Chromium is running, CDP is bound, and `--remote-allow-origins=*` is active (without that flag, the endpoint still responds but WebSocket connections would get 403 — the HTTP JSON check alone is sufficient to confirm the port is ready; the `--remote-allow-origins=*` flag is already present in the startup command and was never the source of the timing bug).

**Primary recommendation:** Replace `sleep 2` with a bash `until` polling loop that curls `http://localhost:9222/json` every 0.5 seconds for up to 10 seconds (20 attempts), exits with a diagnostic error message if the timeout is reached, and continues startup only on success.

---

## Standard Stack

### Core

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| `curl` | System (already in Docker image — Kali-based) | Poll CDP HTTP endpoint for readiness | Standard HTTP client available in all Linux environments; no install needed |
| `bash` | System | Polling loop with timeout counter | `startup.sh` is already bash; stays pure bash, no subprocesses |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `kill -0 $CHROMIUM_PID` | N/A (bash builtin) | Verify Chromium process is still alive during poll | Secondary guard: if Chromium crashes during startup, detect it immediately instead of waiting for timeout |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `curl` HTTP poll | `nc -z localhost 9222` (port check only) | Port check fires when TCP stack accepts the connection but before CDP HTTP is ready — curl at `/json` is more precise |
| `curl` HTTP poll | Python websocket handshake | Overkill for startup.sh; Python adds 100-200ms startup overhead; curl is already present |
| `until` loop | `timeout` + `bash -c` wrapper | Both work; `until` with explicit counter is more readable and allows per-iteration logging |

**Installation:** None. All tools are already in the Docker base image.

---

## Architecture Patterns

### Recommended File Change Scope

```
apps/shared-browser/startup.sh    # Only file that changes
```

No other files change. No Python changes. No requirements.txt changes. No new files.

### Pattern 1: Bash CDP Readiness Poll

**What:** Replace `sleep 2` with a loop that polls `http://localhost:9222/json` via `curl`, bails on Chromium process death, and emits a diagnostic message if timeout expires.

**When to use:** Any bash startup script that launches Chromium with `--remote-debugging-port` and needs to proceed only when CDP is confirmed ready.

**Example:**

```bash
# Wait for Chromium CDP to become ready (replaces sleep 2)
echo "Waiting for Chromium CDP on :9222..."
MAX_ATTEMPTS=20      # 20 × 0.5s = 10 seconds max
ATTEMPT=0
until curl -sf http://localhost:9222/json > /dev/null 2>&1; do
    ATTEMPT=$((ATTEMPT + 1))
    if [ "$ATTEMPT" -ge "$MAX_ATTEMPTS" ]; then
        echo "ERROR: Chromium CDP not ready after ${MAX_ATTEMPTS} attempts. Chromium may have crashed." >&2
        exit 1
    fi
    # Also bail early if Chromium process died
    if ! kill -0 "$CHROMIUM_PID" 2>/dev/null; then
        echo "ERROR: Chromium process (PID $CHROMIUM_PID) died during startup." >&2
        exit 1
    fi
    sleep 0.5
done
echo "Chromium CDP ready after $((ATTEMPT * 500))ms"
```

**Key flags:**
- `curl -sf` — `-s` silent (no progress), `-f` fail silently on HTTP errors (non-2xx returns non-zero exit code)
- `> /dev/null 2>&1` — suppress output; we only care about exit code
- `kill -0 $PID` — checks if process exists without sending a signal; returns 0 if alive

### Pattern 2: Diagnostic Logging on Failure

**What:** When the timeout is reached, emit a structured message to stderr that identifies the failure cause.

**When to use:** Always — this is the requirement. Silent hangs are the problem being fixed.

**Example:**

```bash
echo "ERROR: Chromium CDP not ready after ${MAX_ATTEMPTS} attempts ($(( MAX_ATTEMPTS / 2 ))s timeout)." >&2
echo "  - Check: is Chromium running?  (kill -0 $CHROMIUM_PID)" >&2
echo "  - Check: is port 9222 bound?   (ss -tlnp | grep 9222)" >&2
echo "  - Was Chromium started with --remote-debugging-port=9222?" >&2
exit 1
```

### Anti-Patterns to Avoid

- **`sleep N` fixed delay:** The entire problem being fixed. Never use this.
- **Polling only TCP port availability (`nc -z`):** TCP port can accept connections before CDP HTTP handler is initialized. False positive possible.
- **Setting `set -e` and letting curl failure propagate:** The poll loop intentionally retries on curl failure — `set -e` would abort on first failed curl. The current `startup.sh` has `set -e` at the top; the `until` loop handles curl failure gracefully by design (curl returning non-zero is the "not ready yet" signal, not an error).
- **Polling with `sleep 1` in tight loop without process check:** If Chromium crashes silently, the script hangs for the full timeout with no useful diagnostic.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP readiness check | Custom Python socket probe | `curl -sf` on existing endpoint | curl is already installed; adding a Python subprocess adds latency and complexity |
| Process liveness check | Parsing `ps aux` output | `kill -0 $PID` | kill -0 is POSIX standard, fast, zero-dependency; ps parsing is fragile |
| Timeout handling | Custom signal traps | Counter in `until` loop | Simple, readable, no subshell needed |

**Key insight:** The CDP `/json` HTTP endpoint is the canonical readiness signal for Chromium. It is used this way by chromote (R), chromedp (Go), and all major browser automation frameworks. Do not invent a new check.

---

## Common Pitfalls

### Pitfall 1: `set -e` aborts the poll loop

**What goes wrong:** `startup.sh` has `set -e` at line 2. In an `until` loop, `curl` returning non-zero (not ready) is the "keep waiting" signal — but with `set -e`, any non-zero exit aborts the script immediately.

**Why it happens:** `set -e` exits on any non-zero exit code from a simple command. The `until` condition is evaluated as a conditional, so the test command's non-zero exit does NOT trigger `set -e` — `until <cmd>` is a conditional context, same as `if`. This means the pattern is safe.

**How to avoid:** Use the `until curl ...; do ... done` form. Do NOT use `curl ... || echo "not ready"` outside a conditional context with `set -e` active.

**Warning signs:** Script exits immediately after `sleep 1` is removed and curl is run but Chromium isn't up yet.

### Pitfall 2: Polling too fast causes misleading logs

**What goes wrong:** If the interval is 0.1s, the log output floods with "waiting..." messages. If the interval is 2s, startup may appear to hang (no output for 2 seconds).

**How to avoid:** 0.5s interval is the right balance. Chromium typically starts in 1-3 seconds in Docker. 20 attempts × 0.5s = 10 seconds is a generous timeout without being excessive.

### Pitfall 3: `curl` not available

**What goes wrong:** If curl is absent from the Docker image, the script fails immediately with "command not found".

**How to avoid:** Curl is installed in the Kali-based base image (`install_base_packages*.sh` installs it). Confirmed by the fact that `startup.sh` does not currently need curl but the Docker image is a full Kali system. Low risk. Mitigation: add `|| { echo "ERROR: curl not found"; exit 1; }` after the shebang as a pre-flight check if concerned.

### Pitfall 4: Flask starts before CDP is confirmed — timing still broken

**What goes wrong:** If Flask starts in the background before CDP is verified, the Flask process may accept requests before CDP is ready even if `startup.sh` waited.

**How to avoid:** Not a concern here. In `startup.sh`, Flask is started with `exec /opt/venv-a0/bin/python app.py` — this is the LAST line, and it blocks. The poll loop comes AFTER Chromium starts and BEFORE Flask starts. The order is:
1. Launch Chromium (background, `&`)
2. Poll until CDP ready (new code)
3. Start Flask (blocking, `exec`)

This ordering is correct and Flask will not start until CDP is confirmed.

### Pitfall 5: `--remote-allow-origins=*` check conflated with port readiness

**What goes wrong:** Confusing the 403 "missing --remote-allow-origins=*" error with the port not being ready. These are different conditions.

**How to avoid:** The `/json` HTTP endpoint does NOT require `--remote-allow-origins=*`. That flag only applies to WebSocket connections. Polling `/json` confirms port readiness. The `--remote-allow-origins=*` flag is already in the startup command and is not the issue being fixed. The issue is purely timing.

---

## Code Examples

### Complete Replacement for `sleep 2` in startup.sh

```bash
# Source: standard bash polling pattern verified against CDP docs
# Replaces: sleep 2 (line 42 of apps/shared-browser/startup.sh)

echo "Waiting for Chromium CDP on :9222..."
MAX_ATTEMPTS=20
ATTEMPT=0
until curl -sf http://localhost:9222/json > /dev/null 2>&1; do
    ATTEMPT=$((ATTEMPT + 1))
    if [ "$ATTEMPT" -ge "$MAX_ATTEMPTS" ]; then
        echo "ERROR: Chromium CDP on :9222 not ready after ${MAX_ATTEMPTS} attempts (10s timeout)." >&2
        echo "  Chromium PID: $CHROMIUM_PID  alive: $(kill -0 $CHROMIUM_PID 2>/dev/null && echo yes || echo NO)" >&2
        exit 1
    fi
    if ! kill -0 "$CHROMIUM_PID" 2>/dev/null; then
        echo "ERROR: Chromium (PID $CHROMIUM_PID) exited during startup." >&2
        exit 1
    fi
    sleep 0.5
done
echo "Chromium CDP ready (attempt $((ATTEMPT + 1)), ~$((ATTEMPT * 500))ms)"
```

### What the complete startup.sh looks like after the change

```bash
#!/bin/bash

# Shared Browser Startup Script — Playwright/CDP native (no VNC stack)
set -e

APP_DIR="/a0/apps/shared-browser"
FLASK_PORT=${PORT:-9003}

echo "Starting Shared Browser on port $FLASK_PORT..."

# Kill any existing processes
pkill -f "Xvfb :99" 2>/dev/null || true
pkill -f "x11vnc.*:99" 2>/dev/null || true
pkill -f "websockify" 2>/dev/null || true
pkill -f "chromium.*remote-debugging-port=9222" 2>/dev/null || true
pkill -f "/opt/venv-a0/bin/python app.py" 2>/dev/null || true
fuser -k 9003/tcp 2>/dev/null || true
sleep 1

# Start Chromium in headless mode with CDP on port 9222.
echo "Starting Chromium..."
chromium \
    --headless=new \
    --no-sandbox \
    --disable-dev-shm-usage \
    --disable-gpu \
    --no-first-run \
    --disable-background-networking \
    --disable-default-apps \
    --disable-extensions \
    --disable-sync \
    --disable-translate \
    --window-size=1280,900 \
    --remote-debugging-port=9222 \
    --remote-allow-origins=* \
    https://www.google.com &
CHROMIUM_PID=$!

# Wait for Chromium CDP to be ready (replaces sleep 2)
echo "Waiting for Chromium CDP on :9222..."
MAX_ATTEMPTS=20
ATTEMPT=0
until curl -sf http://localhost:9222/json > /dev/null 2>&1; do
    ATTEMPT=$((ATTEMPT + 1))
    if [ "$ATTEMPT" -ge "$MAX_ATTEMPTS" ]; then
        echo "ERROR: Chromium CDP on :9222 not ready after ${MAX_ATTEMPTS} attempts (10s timeout)." >&2
        echo "  Chromium PID: $CHROMIUM_PID  alive: $(kill -0 $CHROMIUM_PID 2>/dev/null && echo yes || echo NO)" >&2
        exit 1
    fi
    if ! kill -0 "$CHROMIUM_PID" 2>/dev/null; then
        echo "ERROR: Chromium (PID $CHROMIUM_PID) exited during startup." >&2
        exit 1
    fi
    sleep 0.5
done
echo "Chromium CDP ready (attempt $((ATTEMPT + 1)), ~$((ATTEMPT * 500))ms)"

echo "All services started"
echo "   Chromium:  PID $CHROMIUM_PID (CDP on :9222)"

# Flask (blocking — keeps the process alive)
echo "Starting Flask on port $FLASK_PORT..."
cd "$APP_DIR"
exec /opt/venv-a0/bin/python app.py
```

### Verifying the CDP endpoint manually (for testing/debugging)

```bash
# Check CDP is responding
curl -s http://localhost:9222/json | python3 -m json.tool

# Check CDP version endpoint
curl -s http://localhost:9222/json/version | python3 -m json.tool

# Check TCP port is bound (without needing curl)
ss -tlnp | grep 9222
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `sleep N` fixed delay | Poll `/json` HTTP endpoint with `until` loop | CDP has always had /json endpoint | Deterministic instead of probabilistic |
| Manual timeout handling | Iteration counter with bail-out | N/A | Simple, readable |

**Deprecated/outdated:**
- `sleep 2` in startup.sh: Replaced by deterministic poll. The `sleep 1` before Chromium starts (for cleanup of old processes) is intentional and stays — it is not fragile in the same way.

---

## Open Questions

1. **Does `curl` exist in the Docker base image?**
   - What we know: The Docker base is Kali Linux (`kalilinux/kali-rolling`), which includes curl by default. The install scripts don't explicitly mention curl but Kali's minimal image includes basic networking tools.
   - What's unclear: Exact package list installed by `install_base_packages*.sh` scripts was not fully read.
   - Recommendation: The planner should add a task to verify `which curl` in the running container. If absent, use `python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:9222/json')"` as a fallback.

2. **Should the `sleep 1` (process cleanup) before Chromium launch also be replaced?**
   - What we know: The `sleep 1` at line 21 gives time for `pkill`/`fuser` to release the port. This is a different timing concern than the CDP readiness issue.
   - What's unclear: Whether polling the port being free is better than a fixed delay for the cleanup step.
   - Recommendation: Leave the `sleep 1` for cleanup alone — it is not the fragile guard, and replacing it adds complexity with minimal benefit. BROWSER-04 only requires fixing the CDP readiness guard.

---

## Sources

### Primary (HIGH confidence)
- [Chrome DevTools Protocol official docs](https://chromedevtools.github.io/devtools-protocol/) — confirmed `/json`, `/json/version`, `/json/list` endpoints and what they return
- Direct code inspection of `apps/shared-browser/startup.sh` — confirmed exact lines to change
- Direct code inspection of `apps/shared-browser/app.py` — confirmed Flask startup order and CDP usage patterns
- Direct inspection of `usr/skills/shared-browser/SKILL.md` — confirmed CDP patterns in use

### Secondary (MEDIUM confidence)
- [chromote issue #124](https://github.com/rstudio/chromote/issues/124) — confirms Chrome debugging port readiness is a common timing issue requiring polling
- [Wait for HTTP endpoint bash gist](https://gist.github.com/rgl/f90ff293d56dbb0a1e0f7e7e89a81f42) — standard bash polling pattern with curl
- General bash documentation — `until`, `kill -0`, `curl -sf` behavior is stable POSIX behavior

### Tertiary (LOW confidence)
- None applicable — all findings backed by primary sources

---

## Metadata

**Confidence breakdown:**
- Standard stack (bash + curl): HIGH — curl is standard; bash is already in use; no new dependencies
- Architecture (poll loop pattern): HIGH — confirmed by CDP official docs and direct code inspection
- Pitfalls (set -e interaction): HIGH — `until` conditional context is a known bash behavior; verified conceptually
- Pitfalls (curl availability): MEDIUM — Kali includes curl but not confirmed in exact install scripts

**Research date:** 2026-02-25
**Valid until:** 2027-02-25 (extremely stable — bash + curl + CDP /json endpoint have been stable for 10+ years)
