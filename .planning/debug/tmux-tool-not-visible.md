---
status: diagnosed
trigger: "Investigate why TmuxTool is not being registered/visible to the agent"
created: 2026-02-25T00:00:00Z
updated: 2026-02-25T00:00:00Z
---

## Current Focus

hypothesis: Two independent root causes confirmed. Volume persistence + compose mount gap.
test: Code tracing complete
expecting: n/a
next_action: return structured diagnosis to user

## Symptoms

expected: Agent knows and can use tmux_tool after docker compose up --build -d
actual: Agent says it has no knowledge of TmuxTool; only knows terminal_agent
errors: Agent says "I don't have a tool called TmuxTool"
reproduction: docker compose up --build -d, then ask agent to use tmux_tool
started: After phase-11 commits adding tmux_tool.py and agent.system.tool.tmux.md

## Eliminated

- hypothesis: Missing base class (Tool) inheritance in TmuxTool
  evidence: tmux_tool.py line 12: `class TmuxTool(Tool)` — correct
  timestamp: 2026-02-25

- hypothesis: Wrong method name (not execute())
  evidence: tmux_tool.py line 25: `async def execute(self, **kwargs)` — correct
  timestamp: 2026-02-25

- hypothesis: No __init__.py needed
  evidence: extract_tools.load_classes_from_file uses importlib.util.spec_from_file_location — no __init__.py required
  timestamp: 2026-02-25

- hypothesis: .dockerignore excludes python/tools/ or prompts/
  evidence: .dockerignore only excludes usr/* (except usr/skills/**), python/tools/ and prompts/ are NOT excluded
  timestamp: 2026-02-25

- hypothesis: Prompt glob pattern doesn't match tmux filename
  evidence: agent.system.tools.py line 19: pattern is "agent.system.tool.*.md" — matches "agent.system.tool.tmux.md"
  timestamp: 2026-02-25

- hypothesis: Tool name mismatch between prompt and file
  evidence: Prompt says `### tmux_tool:` and uses `"tool_name": "tmux_tool"`. File is tmux_tool.py. get_tool(name) looks for name+".py". All consistent.
  timestamp: 2026-02-25

## Evidence

- timestamp: 2026-02-25
  checked: python/helpers/extract_tools.py load_classes_from_folder
  found: Tools are NOT loaded via glob scan of the folder. Each tool is loaded on-demand by filename: get_tool(name) → get_paths(self, "tools", name+".py") → load_classes_from_file(path, Tool)
  implication: No registration step needed. Tool file must exist at python/tools/{tool_name}.py or usr/tools/{tool_name}.py.

- timestamp: 2026-02-25
  checked: agent.py line 989 get_tool()
  found: Tool loading: subagents.get_paths(self, "tools", name+".py", default_root="python") — checks project/, usr/, python/ in order. For "tmux_tool" → looks for python/tools/tmux_tool.py. File exists.
  implication: Tool class loading path is correct IF /a0/python/tools/tmux_tool.py exists.

- timestamp: 2026-02-25
  checked: prompts/agent.system.tools.py BuidToolsPrompt.get_variables()
  found: Scans dirs for "agent.system.tool.*.md". Dirs = [get_abs_path(""), backup_dirs] = ["/a0", "/a0/prompts"]. Finds agent.system.tool.tmux.md in /a0/prompts/. Prompt injection path is correct IF /a0/prompts/agent.system.tool.tmux.md exists.
  implication: Prompt file loading is correct IF the file is present in /a0.

- timestamp: 2026-02-25
  checked: DockerfileLocal + docker/run/fs/ins/copy_A0.sh
  found: copy_A0.sh only copies /git/agent-zero → /a0 IF /a0/run_ui.py does not exist. Uses `cp -rn` (no-overwrite).
  implication: ROOT CAUSE 2 — if /a0 is pre-populated (e.g. from volume persistence via /per), new files are never copied.

- timestamp: 2026-02-25
  checked: docker-compose.yml volumes
  found: Only mounts: agent-zero-data:/per, ./webui:/a0/webui, ./apps:/a0/apps. Does NOT mount ./python or ./prompts into /a0.
  implication: ROOT CAUSE 1 — python/tools/ and prompts/ are NOT live-mounted. After `docker compose up --build -d`, the container filesystem is fresh, but only the webui and apps directories are live from host. Everything else (including python/tools/tmux_tool.py and prompts/agent.system.tool.tmux.md) must come from the image build via copy_A0.sh.

- timestamp: 2026-02-25
  checked: docker/run/fs/exe/initialize.sh
  found: Runs `cp -r --no-preserve=ownership,mode /per/* /` at startup. This copies persistent volume contents over root filesystem.
  implication: If /per has stale /a0 content (from a previous deployment), it overlays the new container filesystem before copy_A0.sh runs. Then copy_A0.sh sees /a0/run_ui.py exists and skips the copy entirely.

## Resolution

root_cause: TWO root causes identified.

ROOT CAUSE 1 (immediate/primary): python/tools/ and prompts/ directories are not volume-mounted in docker-compose.yml. The agent runs from /a0/ which is populated by copy_A0.sh at container start from /git/agent-zero. While the image build correctly includes the new files, there is NO live-reload path from the host filesystem into /a0/python/ or /a0/prompts/. This means:
  a) If the container was never fully rebuilt (image cache), old files are used.
  b) If /per volume has stale /a0 data (persistent volume from previous run), copy_A0.sh is skipped.

ROOT CAUSE 2 (volume persistence): The /per persistent volume is copied over the root filesystem at every container start (initialize.sh). If a previous container run wrote /a0 content into /per (directly or indirectly), those stale files persist across container recreation. copy_A0.sh then skips the copy because /a0/run_ui.py already "exists". This is the most likely cause of "still no knowledge after docker compose up --build".

fix: See structured diagnosis in response.
verification: Not applied (diagnose-only mode).
files_changed: []
