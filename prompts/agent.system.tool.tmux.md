### tmux_tool:

Interact directly with the shared tmux terminal session (the same terminal visible to the user in the drawer).
Use this tool to orchestrate interactive CLI sessions — NOT for simple shell commands (use `terminal_agent` for those).

**REQUIRED STEP BEFORE USE**: call `open_app` first:
`{ "action": "open", "app": "shared-terminal" }`

!!! The shared tmux session is named `shared` — all actions target it by default
!!! `send` types text + Enter; `keys` sends key sequences WITHOUT Enter; `read` captures what is on screen
!!! No sentinel markers are ever injected — screen capture is the only observation mechanism
!!! Both `terminal_agent` and `tmux_tool` share the same `shared` session — coordinate use
!!! Always call `wait_ready` after `send` before injecting the next input
!!! Default timeout is 10s — use timeout: 120 when waiting for AI CLI responses (OpenCode, claude)
!!! `wait_ready` returns current pane content in its response (same as `read`)
!!! prompt_pattern matches last non-blank line only — sub-prompts like "Continue? [y/N]" do NOT trigger ready

#### Arguments:
* `action` (string, required) — `send` | `keys` | `read` | `wait_ready`
* `text` (string) — for `send`: the text to type (Enter is added automatically)
* `keys` (string or list) — for `keys`: tmux key names space-separated, e.g. `"C-c"`, `"Tab"`, `"Escape"`, `"Up"`
* `pane` (string, optional) — tmux pane target (default: `"shared"`)
* `lines` (number, optional) — for `read`: scrollback lines to capture (default: 100)
* `timeout` (number, optional) — for `wait_ready`: seconds before giving up (default: 10). Use 120 when waiting on AI CLI responses.
* `prompt_pattern` (string, optional) — for `wait_ready`: regex anchored to line-end (default: `"[$#>%]\\s*$"` — matches bash/zsh/sh/node prompts). Override for non-standard shells.

#### Special key names:
`C-c` (Ctrl+C), `C-d` (Ctrl+D), `Tab`, `BTab` (Shift+Tab), `Escape`, `Enter`,
`Up`, `Down`, `Left`, `Right`, `BSpace`, `PPage` (Page Up), `NPage` (Page Down)

#### send vs keys distinction:
- `send` — for literal text that needs Enter appended: running commands, submitting prompts, typing a path. The text is passed as a single literal string; tmux will not interpret words like "Tab" as key names.
- `keys` — for special keys and partial input that must NOT have Enter appended: Ctrl+C to interrupt, Tab for completion, `y` or `n` to answer an inline y/N prompt, arrow keys for menu navigation.

#### tmux_tool vs terminal_agent distinction:
- Use `terminal_agent` for simple shell commands with known exit codes (it uses sentinels internally for exit-code detection).
- Use `tmux_tool` for interactive CLIs where you need to observe prompts and respond: package managers asking y/N, pagers, REPLs, interactive installers, AI CLI tools.

#### Usage: run a command (send + Enter)
```json
{ "tool_name": "tmux_tool", "tool_args": { "action": "send", "text": "ls -la" } }
```

#### Usage: answer inline y/N prompt (keys, no Enter)
```json
{ "tool_name": "tmux_tool", "tool_args": { "action": "keys", "keys": "y" } }
```

#### Usage: interrupt a running process (Ctrl+C)
```json
{ "tool_name": "tmux_tool", "tool_args": { "action": "keys", "keys": "C-c" } }
```

#### Usage: read current terminal screen
```json
{ "tool_name": "tmux_tool", "tool_args": { "action": "read" } }
```

#### Usage: wait for terminal to be ready after sending a command
```json
{ "tool_name": "tmux_tool", "tool_args": { "action": "wait_ready" } }
```

#### Usage: wait with longer timeout (for AI CLI tools that take 30-120s)
```json
{ "tool_name": "tmux_tool", "tool_args": { "action": "wait_ready", "timeout": 120 } }
```

#### Usage: wait with custom prompt pattern (for non-standard CLI prompts)
```json
{ "tool_name": "tmux_tool", "tool_args": { "action": "wait_ready", "prompt_pattern": "opencode> $" } }
```

## OpenCode Lifecycle Pattern

Use these exact tmux_tool calls to orchestrate an OpenCode session.
All patterns verified empirically in Phase 13 (see 13-01-OBSERVATION.md).

The ready-state pattern covers two TUI states:
- Initial startup: status bar at bottom shows `/a0  ...  1.2.14`
- Post-response: hints bar shows `ctrl+t variants  tab agents` WITHOUT `esc interrupt` (busy indicator)

```
OPENCODE_PROMPT_PATTERN = ^(?:\s*/a0\s+\d+\.\d+\.\d+\s*$|(?!.*esc interrupt).*ctrl\+t variants\s+tab agents)
OPENCODE_START_TIMEOUT  = 15 (seconds)
```

### CLI-01: Start OpenCode and wait for ready state
```json
{"tool_name": "tmux_tool", "tool_args": {"action": "send", "text": "opencode /a0"}}
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 15, "prompt_pattern": "^(?:\\s*/a0\\s+\\d+\\.\\d+\\.\\d+\\s*$|(?!.*esc interrupt).*ctrl\\+t variants\\s+tab agents)"}}
```

### CLI-02 + CLI-03: Send prompt, wait for response, read result
```json
{"tool_name": "tmux_tool", "tool_args": {"action": "send", "text": "Your prompt here"}}
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 120, "prompt_pattern": "^(?:\\s*/a0\\s+\\d+\\.\\d+\\.\\d+\\s*$|(?!.*esc interrupt).*ctrl\\+t variants\\s+tab agents)"}}
{"tool_name": "tmux_tool", "tool_args": {"action": "read", "lines": 300}}
```

### CLI-04: Exit cleanly
```json
{"tool_name": "tmux_tool", "tool_args": {"action": "keys", "keys": "C-p"}}
{"tool_name": "tmux_tool", "tool_args": {"action": "send", "text": "exit"}}
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 15}}
```
!!! After exit, wait_ready uses the default shell prompt pattern — OpenCode pattern is NOT needed here.
!!! Verify shell prompt is restored: the last non-blank line should end with $ or # character.
!!! OpenCode exits cleanly in 1-2 seconds and prints the session name + resume command before quitting.

IMPORTANT (v1.2.14 behavior): Do NOT use `{"action": "send", "text": "/exit"}` directly — the `/` character
immediately triggers the AGENT PICKER, not the command autocomplete. Instead use Ctrl+P (commands palette),
type "exit" to filter to "Exit the app", then press Enter. The three-step sequence above is the verified method.

### Multi-turn loop
Repeat CLI-02+CLI-03 steps for each prompt. Each send/wait_ready/read cycle is one turn.
OpenCode maintains session context automatically within the TUI process.

### Notes on OpenCode TUI behavior
- First ever start in container: runs a one-time DB migration (< 3s, non-blocking, exits to shell before TUI)
- "Getting started" dialog appears after first LLM response — does NOT block input; ignore it
- Built-in "big-pickle" free model is available without any provider configuration
- Resume a previous session: `opencode -s ses_[SESSION_ID]` (session ID shown at exit)
- Typing `/` in the input area opens the AGENT PICKER (not command autocomplete); use Ctrl+P for commands
