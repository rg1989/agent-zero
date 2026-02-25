---
status: diagnosed
phase: 11-tmux-primitive-infrastructure
source: 11-01-SUMMARY.md
started: 2026-02-25T14:30:00Z
updated: 2026-02-25T14:50:00Z
---

## Current Test

[testing complete]

## Tests

### 1. TmuxTool auto-registered in agent
expected: Open a new agent chat. Ask the agent: "What tmux tool actions do you have?" The agent should describe three actions: send, keys, and read — without needing external docs.
result: issue
reported: "Agent described terminal_agent capabilities (run commands, background processes, live output) — no mention of TmuxTool send/keys/read actions"
severity: major

### 2. send action executes commands
expected: Ask the agent to use TmuxTool send to run `echo "hello from tmux"` in the shared terminal. The command should execute and you should see it run in the shared terminal panel.
result: issue
reported: "Agent replied: I don't have a tool called TmuxTool with action and text parameters. Only terminal_agent is available."
severity: major

### 3. read action returns clean output
expected: After running a command, ask the agent to use TmuxTool read to show the current terminal contents. The returned text should be readable — no escape sequences like `ESC[32m`, `]0;bash`, or other ANSI artifacts.
result: skipped
reason: Blocked by TmuxTool not being registered (same root cause as tests 1 and 2)

### 4. keys action sends key names
expected: With an interactive command running (or at a shell prompt), ask the agent to use TmuxTool keys to send "ctrl+c" to the terminal. The signal should be delivered — any running process terminates or the prompt returns.
result: skipped
reason: Blocked by TmuxTool not being registered (same root cause as tests 1 and 2)

### 5. send vs keys distinction respected
expected: Ask the agent to send a command containing a word like "Tab" as text (e.g., `echo "Tab here"`). The word "Tab" should appear literally in the terminal — not be interpreted as the Tab key. (Tests that send passes text as single argument, not split.)
result: skipped
reason: Blocked by TmuxTool not being registered (same root cause as tests 1 and 2)

## Summary

total: 5
passed: 0
issues: 2
pending: 0
skipped: 3

## Gaps

- truth: "Agent knows about TmuxTool send/keys/read actions via auto-registered prompt docs"
  status: failed
  reason: "User reported: Agent described terminal_agent capabilities only. After container rebuild, agent still replied 'I don't have a tool called TmuxTool' when asked directly."
  severity: major
  test: 1
  root_cause: "Stale /a0 in persistent Docker volume (agent-zero-data) — copy_A0.sh skips copy when run_ui.py already exists, so new tmux_tool.py and agent.system.tool.tmux.md from rebuilt image never reach /a0/. Additionally python/tools/ and prompts/ are not bind-mounted so no live-reload path exists."
  artifacts:
    - path: "docker/run/fs/ins/copy_A0.sh"
      issue: "Presence check `if [ ! -f run_ui.py ]` prevents copy when /a0 populated from stale volume"
    - path: "docker-compose.yml"
      issue: "python/ and prompts/ not bind-mounted; only webui/ and apps/ have live-reload"
  missing:
    - "Clear stale volume OR fix copy_A0.sh to always apply new files from image"
    - "Add bind mounts for python/ and prompts/ to docker-compose.yml"
  debug_session: ".planning/debug/tmux-tool-not-visible.md"
