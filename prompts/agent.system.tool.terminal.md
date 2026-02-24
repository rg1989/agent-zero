### terminal_agent:

Runs a shell command in the persistent shared tmux session that is visible to the user in the right-side drawer.

**REQUIRED STEP BEFORE USE**: call `open_app` first to show the terminal drawer:
`open_app` → `{ "action": "open", "app": "shared-terminal" }`

!!! Both you and the user share the exact same live tmux session — every command you run appears in their terminal in real time
!!! The session persists between tasks; previous commands and output remain visible
!!! Use `&` to background long-running processes (servers, watchers) and return immediately
!!! For silent background work the user doesn't need to see, prefer `code_execution_tool` instead

#### Arguments:
* `command` (string, required) — shell command to execute in the shared terminal
* `timeout` (string, optional) — seconds to wait for the command to finish before returning (default: "10"; use higher values for slow commands)

#### Usage: run a visible command in the shared terminal
```json
{
    "thoughts": ["Opening the terminal so the user can watch."],
    "tool_name": "open_app",
    "tool_args": { "action": "open", "app": "shared-terminal" }
}
```
then:
```json
{
    "thoughts": ["Running the build in the shared terminal."],
    "headline": "Running build",
    "tool_name": "terminal_agent",
    "tool_args": { "command": "cd /a0 && npm run build", "timeout": "60" }
}
```

#### Usage: start a background process (non-blocking)
```json
{
    "thoughts": ["Starting the dev server in the background."],
    "headline": "Starting dev server",
    "tool_name": "terminal_agent",
    "tool_args": { "command": "npm run dev &", "timeout": "5" }
}
```

#### Usage: check current directory / environment
```json
{
    "thoughts": ["Checking where we are."],
    "tool_name": "terminal_agent",
    "tool_args": { "command": "pwd && ls -la" }
}
```
