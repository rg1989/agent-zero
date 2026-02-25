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
