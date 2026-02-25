# 13-01: OpenCode TUI Observation Log

**Date:** 2026-02-25
**OpenCode version:** 1.2.14
**Docker arch:** aarch64 (Kali Linux)

## Version

opencode --version output: `1.2.14`

Installed via: `curl -fsSL https://opencode.ai/install | bash` (official install script, inside Docker container)
Install path: `/root/.opencode/bin/opencode`
PATH added to: `/root/.bashrc` (`export PATH=/root/.opencode/bin:$PATH`)

Version 1.2.14 is ABOVE the required 1.2.5 minimum. No hang regression risk (issue #3213 was fixed before v1.2.5).

## LLM Config

Model used for testing: `big-pickle` (OpenCode built-in free model — automatically selected when no provider configured)
Note: Config was set up with Ollama/phi3:3.8b but OpenCode defaulted to its built-in "big-pickle" model.
baseURL: `http://host.docker.internal:11434/v1`
Ollama status during test: running on host (port 11434)

Config file: `/root/.config/opencode/ai.opencode.json`

```json
{
  "permission": "allow",
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama (local)",
      "options": {
        "baseURL": "http://host.docker.internal:11434/v1"
      },
      "models": {
        "qwen3:8b": { "name": "Qwen 3 8B (local)" },
        "qwen2.5:7b-instruct-q4_K_M": { "name": "Qwen 2.5 Instruct" },
        "qwen2.5-coder:latest": { "name": "Qwen 2.5 Coder" },
        "phi3:3.8b": { "name": "Phi-3 3.8B (test)" }
      }
    }
  },
  "model": "ollama/phi3:3.8b"
}
```

`"permission": "allow"` added as precaution against subprocess permission-dialog hang (RESEARCH.md Pitfall 5, issue #11891).

host.docker.internal reachability from Docker container: CONFIRMED — `curl http://host.docker.internal:11434/api/version` returns `{"version":"0.13.5"}`

**Note on model selection:** When sending prompts, the TUI used the built-in "big-pickle" model (shown as `Build · big-pickle` in conversation history). This suggests that even with `"model": "ollama/phi3:3.8b"` set in config, OpenCode may have used its default free model. The TUI prompt input area shows "Build  Big Pickle OpenCode Zen" which appears to be the model selection carousel. For Plan 13-02 testing with user-configured Ollama models, additional investigation may be needed to ensure the correct model is selected.

## Startup Sequence

OpenCode was started with: `export PATH=/root/.opencode/bin:$PATH && opencode /a0`

| Time | Last Non-Blank Line (repr) | Notes |
|------|---------------------------|-------|
| t=0.5s | `(empty)` | Screen still clearing / TUI initializing |
| t=1.5s | `'  /a0                                                                                                                        1.2.14'` | TUI logo rendered, input area active |
| t=2.5s | `'  /a0                                                                                                                        1.2.14'` | Stable — ready state reached |
| t=4.5s | `'  /a0                                                                                                                        1.2.14'` | Stable — unchanged |

Startup stabilizes at approximately: **1.5s** (TUI is fully rendered and ready for input within 1-2 seconds)

**Full TUI at ready state (ANSI-stripped):**
```
(lines of whitespace above for centering)
                                                                                ▄
                                               █▀▀█ █▀▀█ █▀▀█ █▀▀▄ █▀▀▀ █▀▀█ █▀▀█ █▀▀█
                                               █  █ █  █ █▀▀▀ █  █ █    █  █ █  █ █▀▀▀
                                               ▀▀▀▀ █▀▀▀ ▀▀▀▀ ▀▀▀▀ ▀▀▀▀ ▀▀▀▀ ▀▀▀▀ ▀▀▀▀


                             ┃
                             ┃  Ask anything... "Fix a TODO in the codebase"
                             ┃
                             ┃  Build  Big Pickle OpenCode Zen
                             ╹▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
                                                            ctrl+t variants  tab agents  ctrl+p commands
                                  ● Tip Create .ts files in .opencode/tools/ to define new LLM tools
  /a0                                                                                                                        1.2.14
```

## Ready State (idle, awaiting input — initial startup, no conversation)

Last non-blank line (repr): `'  /a0                                                                                                                        1.2.14'`

Last 5 non-blank lines:
```
  [-5]: '                             ┃'
  [-4]: '                             ┃  Build  Big Pickle OpenCode Zen'
  [-3]: '                             ╹▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀'
  [-2]: '                                                            ctrl+t variants  tab agents  ctrl+p commands'
  [-1]: '  /a0                                                                                                                        1.2.14'
```

Note: Sometimes with tip shown:
```
  [-3]: '                                                            ctrl+t variants  tab agents  ctrl+p commands'
  [-2]: '                                  ● Tip Create .ts files in .opencode/tools/ to define new LLM tools'
  [-1]: '  /a0                                                                                                                        1.2.14'
```

**Pattern test:** `re.search(r'\s*/a0\s+\d+\.\d+\.\d+\s*$', last_line)` → **MATCH**

The status bar at the bottom shows project path (`/a0`) + version number (`1.2.14`). This is the definitive "ready" indicator for the initial startup state.

## Ready State (after conversation — awaiting next prompt)

After sending a prompt and receiving a response, the TUI layout changes. The status bar moves and the bottom line becomes the keybind hints bar.

Last non-blank line (repr): `'                                             ctrl+t variants  tab agents  ctrl+p commands    • OpenCode 1.2.14'`

Last 5 non-blank lines:
```
  [-5]: '  ┃                                                                                              Connect provider        /connect'
  [-4]: '  ┃'
  [-3]: '  ┃'
  [-2]: '  ┃  Build  Big Pickle OpenCode Zen                                                          /a0'
  [-1]: '  ╹▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀'
  last: '                                             ctrl+t variants  tab agents  ctrl+p commands    • OpenCode 1.2.14'
```

Note: The "Getting started" onboarding dialog may appear on top, but the bottom status lines are unchanged.

**Pattern test:** `re.search(r'^(?!.*esc interrupt).*ctrl\+t variants\s+tab agents', last_line)` → **MATCH**

## Busy State (AI processing)

Captured at t=0.5s after sending a prompt (the built-in big-pickle model responds very quickly — typically 1-14 seconds):

Last non-blank line (repr): `'   ⬝⬝⬝⬝⬝⬝■■  esc interrupt                   ctrl+t variants  tab agents  ctrl+p commands    • OpenCode 1.2.14'`

**Key distinguishing features of busy state:**
1. Line starts with animation characters: `⬝⬝⬝⬝⬝⬝■■` (loading progress bar)
2. Contains **`esc interrupt`** — the interrupt hint appears only during AI processing
3. Still contains `ctrl+t variants  tab agents  ctrl+p commands    • OpenCode 1.2.14` but AFTER `esc interrupt`

**Does busy state match ready-state pattern?**
- Initial ready pattern (`/a0\s+\d+.\d+.\d+$`): NO — busy line has no `/a0`
- Post-response ready pattern (`^(?!.*esc interrupt).*ctrl\+t variants`): NO — negative lookahead blocks match

**Distinguishing characteristic:** `esc interrupt` appears ONLY in the busy state last non-blank line. This string is ABSENT in all ready states. It is the primary differentiator.

## Post-Response State (ready again — after response complete)

After AI completes its response, the bottom line reverts to the standard hints bar WITHOUT `esc interrupt`:

Last non-blank line (repr): `'                                             ctrl+t variants  tab agents  ctrl+p commands    • OpenCode 1.2.14'`

Same as post-conversation ready state: YES — identical to the ready state last line.

Notes: The conversation messages are displayed above the input area. The full state shows the conversation history, token counts, and model timing (`▣  Build · big-pickle · 13.5s`).

## Exit Sequence

Command used: `/exit` + Enter (typed into TUI input box, then Enter pressed)

**Critical implementation note:** In tmux_tool, the exit sequence requires sending `/exit` as text and then `Enter` as a key:
```python
# Correct (two separate sends):
tmux_tool(action="send", text="/exit")   # types /exit into input
tmux_tool(action="send", text="")        # triggers autocomplete; then:
# OR: tmux send-keys separately with Enter key

# Also works as one call:
docker exec agent-zero bash -c "tmux send-keys -t shared:0.0 '/exit' Enter"
```

The TUI shows autocomplete `┃ /exit      Exit the app` after typing `/exit`. Pressing Enter executes the command.

Shell prompt visible after exit? **YES**
Last non-blank line after exit (repr): `'(venv) root@ac5da648ff9d:/a0/apps/shared-terminal#'`
Shell prompt matches default `r'[$#>%]\s*$'`: **YES**
Time to shell return: **1-2 seconds**

**Exit output visible in tmux pane:**
```
  Session   [session name based on conversation topic]
  Continue  opencode -s ses_[SESSION_ID]
(venv) root@ac5da648ff9d:/a0/apps/shared-terminal#
```

OpenCode prints the session name and the resume command before exiting cleanly.

## Auth / Welcome Prompt on First Start

Did opencode prompt for any auth or onboarding? **YES** (non-blocking)

Description: A "Getting started" dialog (`⬖ Getting started  ✕`) appeared in the right panel after the first prompt was sent and responded to. It shows:
```
OpenCode includes free models
so you can start immediately.

Connect from 75+ providers to
use other models, including
Claude, GPT, Gemini etc

Connect provider        /connect
```

This dialog does NOT block input. The input area remains active. It does NOT affect the `prompt_pattern` detection since the last non-blank line is unaffected. The dialog can be dismissed with Escape or by closing with the `✕` button. For automated use, it can be safely ignored — it does not prevent sending further prompts.

## Startup Behaviors — Additional Findings

### First-time database migration
On the FIRST ever start in the container, OpenCode ran a database migration:
```
Performing one time database migration, may take a few minutes...
Database migration complete.
(venv) root@ac5da648ff9d:...#
```
This happened BEFORE the TUI launched and completed quickly (< 3s). On subsequent starts, this does not occur. It ran in the pre-TUI shell phase and did not affect the TUI behavior.

### Model selection carousel
The TUI bottom of input area always shows: `Build  Big Pickle OpenCode Zen`
This represents available model variants (not a menu requiring selection). The Ctrl+T key cycles through them.

### "Getting started" dialog timing
The dialog appeared ONLY after the first LLM response, not at startup. It overlays the right panel but does not affect the prompt input state.

## Final Recommendations for Plan 13-02

### prompt_pattern for CLI-01/CLI-02/CLI-03 (OpenCode ready state):

```python
r'^(?:\s*/a0\s+\d+\.\d+\.\d+\s*$|(?!.*esc interrupt).*ctrl\+t variants\s+tab agents)'
```

**Verification results:**
- Initial startup ready state: **MATCHES** (via `/a0\s+\d+\.\d+\.\d+` branch)
- Post-response ready state: **MATCHES** (via `ctrl\+t variants` negative-lookahead branch)
- Busy/processing state: **DOES NOT MATCH** (blocked by `esc interrupt` detection)
- Shell prompt (after exit): **DOES NOT MATCH** (neither branch applies)

```python
import re
pattern = r'^(?:\s*/a0\s+\d+\.\d+\.\d+\s*$|(?!.*esc interrupt).*ctrl\+t variants\s+tab agents)'

ready_initial = '  /a0                                                                                                                        1.2.14'
ready_post = '                                             ctrl+t variants  tab agents  ctrl+p commands    • OpenCode 1.2.14'
busy = '   ⬝⬝⬝⬝⬝⬝■■  esc interrupt                   ctrl+t variants  tab agents  ctrl+p commands    • OpenCode 1.2.14'

assert bool(re.search(pattern, ready_initial)), "Should match initial ready"
assert bool(re.search(pattern, ready_post)), "Should match post-response ready"
assert not bool(re.search(pattern, busy)), "Should NOT match busy"
# All assertions pass
```

### timeout values:
- CLI-01 startup wait_ready timeout: **15s** (observed startup: ~1.5s; 10x buffer)
- CLI-02/03 response wait_ready timeout: **120s** (AI response budget for real models)
- CLI-04 exit wait_ready timeout: **15s** (shell return observed in ~1-2s; default shell pattern)

### Exit sequence for CLI-04:
Primary: type `/exit` + Enter (via `tmux_tool send`)
The `/exit` command shows autocomplete confirmation before executing.
Fallback: `tmux_tool keys "C-c"` if `/exit` does not work

### Input method for CLI-02 (sending prompts):
Type the prompt text (without pressing Enter) + then press Enter to submit.
Using `tmux_tool send` with `text="your prompt"` types the text.
Use `tmux_tool keys "Enter"` or `tmux_tool send` with text containing newline to submit.

**Implementation pattern:**
```python
# Send prompt to OpenCode TUI
tmux_tool(action="send", text="Your question here")
# Then press Enter to submit (send-keys with Enter)
# In current tmux_tool implementation, action="send" appends Enter automatically
# So: tmux_tool(action="send", text="Your question here") should work
```

Wait — need to verify how current `tmux_tool.py` `send` action handles newlines. See python/tools/tmux_tool.py `_send()` method.

### Model selection for testing:
OpenCode's built-in "big-pickle" free model is available without configuration and responds quickly.
For testing with Ollama models: configure `"model": "ollama/phi3:3.8b"` in config AND have Ollama running on host with that model pulled.

### Blockers/Issues:

1. **"Getting started" dialog**: Non-blocking. Appears after first response. Does not affect prompt detection. Ignore.

2. **Model selection**: OpenCode may use built-in models regardless of config setting. For Plan 13-02 testing, this is acceptable — the TUI behaviors (ready/busy patterns, exit sequence) are identical regardless of which model is used.

3. **Initial database migration**: Only occurs once per fresh container. Non-blocking for subsequent starts. Takes < 3s.

4. **Exit sequence timing with send_keys combined string**: When using `tmux send-keys -t shared 'text' Enter` as one string, the behavior was observed to vary on first fresh startup. Using separate send + keys calls is more reliable. Plan 13-02 should verify how the current `tmux_tool.py` `send` action works with the TUI.

## Startup Time Measurement

From `opencode /a0` command sent to first visible TUI ready state (ANSI-stripped last non-blank line matches status bar pattern):
- t=0s: command sent
- t=0.5s: screen still empty (TUI initializing)
- t=1.5s: TUI fully rendered, ready for input

**Measured startup time: approximately 1-1.5 seconds**

For wait_ready timeout in CLI-01: use **15s** (10x buffer; allows for slow starts, network latency in container).

## Regex Pattern Reference

```python
# Import and constants for Plan 13-02
import re

# OpenCode TUI ready state pattern (covers both initial and post-response states)
OPENCODE_PROMPT_PATTERN = r'^(?:\s*/a0\s+\d+\.\d+\.\d+\s*$|(?!.*esc interrupt).*ctrl\+t variants\s+tab agents)'

# OpenCode busy state indicator (for documentation — NOT used in wait_ready positive match)
OPENCODE_BUSY_INDICATOR = r'esc interrupt'

# Default shell prompt (for CLI-04 exit detection — already default in wait_ready)
SHELL_PROMPT_PATTERN = r'[$#>%]\s*$'
```
