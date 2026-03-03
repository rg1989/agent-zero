---
phase: quick-7
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - usr/bin/webapp-helper
  - usr/skills/web-app-builder/SKILL.md
  - prompts/agent.system.main.tips.md
autonomous: true
requirements: [QUICK-7]

must_haves:
  truths:
    - "webapp-helper script exists at usr/bin/webapp-helper and is executable"
    - "Each subcommand (validate-name, alloc-port, init, register, start, stop, health-check, status) works correctly"
    - "SKILL.md Steps 1, 3, 4, 6, 7, 8 use webapp-helper instead of raw curl/bash"
    - "Agent system tips mention webapp-helper as the tool for webapp operations"
    - "All output is machine-parseable single-line, exit codes are 0=success 1=error"
  artifacts:
    - path: "usr/bin/webapp-helper"
      provides: "CLI wrapper for all webapp API interactions"
      min_lines: 150
    - path: "usr/skills/web-app-builder/SKILL.md"
      provides: "Updated skill using webapp-helper subcommands"
      contains: "webapp-helper"
    - path: "prompts/agent.system.main.tips.md"
      provides: "System tips mentioning webapp-helper"
      contains: "webapp-helper"
  key_links:
    - from: "usr/bin/webapp-helper"
      to: "http://localhost/webapp"
      via: "curl calls hardcoded in script"
      pattern: "API_URL.*localhost/webapp"
    - from: "usr/skills/web-app-builder/SKILL.md"
      to: "usr/bin/webapp-helper"
      via: "subcommand references in Steps 1,3,4,6,7,8"
      pattern: "webapp-helper"
---

<objective>
Create a `webapp-helper` CLI script that encapsulates all webapp API calls, template init, name validation, and health checks. Then update SKILL.md and system tips to use it.

Purpose: Eliminate agent hallucination errors by hiding URL construction, file paths, reserved name lists, and multi-step operations behind simple CLI subcommands. The agent calls `webapp-helper validate-name foo` instead of constructing regex checks and curl payloads from memory.

Output: Executable script at `usr/bin/webapp-helper`, updated SKILL.md, updated system tips.
</objective>

<execution_context>
@/Users/rgv250cc/.claude/get-shit-done/workflows/execute-plan.md
@/Users/rgv250cc/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@usr/skills/web-app-builder/SKILL.md
@prompts/agent.system.main.tips.md
@python/helpers/app_proxy.py (lines 22-44 for _RESERVED set)
@python/api/webapp.py (for API payload format)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create the webapp-helper bash script</name>
  <files>usr/bin/webapp-helper</files>
  <action>
Create directory `usr/bin/` if it does not exist. Create `usr/bin/webapp-helper` as a bash script with `chmod +x`.

**Top-of-file constants (hardcoded ONCE):**
```
API_URL="http://localhost/webapp"
APPS_DIR="/a0/apps"
TEMPLATES_DIR="/a0/apps/_templates"
```

**Reserved names list** (from `python/helpers/app_proxy.py` `_RESERVED` frozenset, plus built-in app names):
```
RESERVED="login logout health dev-ping socket.io static message poll settings_get settings_set csrf_token chat_create chat_load upload webapp mcp a2a shared-browser shared-terminal"
```

**Subcommands to implement:**

1. `validate-name <name>` — Check regex `^[a-z][a-z0-9-]{0,28}[a-z0-9]$` using bash `[[ ]]` with `=~`. Check against RESERVED blocklist. Output: `VALID` (exit 0) or `ERROR: <reason>` (exit 1). Also reject single-char names (regex enforces min 2).

2. `alloc-port` — `curl -sf "$API_URL?action=alloc_port"`, extract port using `python3 -c "import sys,json; print(json.load(sys.stdin)['port'])"`. Output: just the port number. Exit 1 if curl fails or JSON has `error` key.

3. `init <app-name> <template>` — Validate template exists in `$TEMPLATES_DIR/$template` (not a file starting with `_`). Copy with `cp -r`. Run `pip3 install --break-system-packages -q -r "$APPS_DIR/$app_name/requirements.txt" 2>/dev/null || true`. Output: `OK: App initialized at $APPS_DIR/$app_name/` or `ERROR: <reason>`.

4. `register <app-name> <port> <start-cmd> [description]` — POST to API_URL with JSON body `{"action":"register","name":"...","port":N,"cmd":"...","cwd":"/a0/apps/<name>","description":"..."}`. Parse response for `error` key. Output: `OK: Registered` or `ERROR: <reason>`.

5. `start <app-name>` — POST `{"action":"start","name":"..."}`. Output: `OK: Started` or `ERROR: <reason>`.

6. `stop <app-name>` — POST `{"action":"stop","name":"..."}`. Output: `OK: Stopped` or `ERROR: <reason>`.

7. `health-check <port> [timeout_seconds]` — Default timeout 10s. Poll `http://127.0.0.1:<port>/` every 0.5s using `curl -sf -o /dev/null`. Output: `HEALTHY` (exit 0) or `FAILED: not responding after Ns` (exit 1).

8. `status [app-name]` — If app-name given: GET `$API_URL?action=status&name=<name>`, output JSON. If no app-name: GET `$API_URL?action=list`, output JSON.

**Script structure:** Use a `case "$1" in` dispatch. Include a `usage()` function printed on no args or `--help`. Every subcommand validates its argument count and prints usage on error.

**Error handling pattern for curl+API calls:**
```bash
RESPONSE=$(curl -sf -X POST "$API_URL" -H "Content-Type: application/json" -d "$PAYLOAD") || { echo "ERROR: API request failed"; exit 1; }
ERROR=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',''))" 2>/dev/null)
if [ -n "$ERROR" ]; then echo "ERROR: $ERROR"; exit 1; fi
```

Use `set -euo pipefail` at the top. Use `#!/usr/bin/env bash`.
  </action>
  <verify>
Run `bash -n usr/bin/webapp-helper` to syntax-check.
Run `chmod +x usr/bin/webapp-helper` to ensure executable.
Verify the script has all 8 subcommands: `grep -c 'validate-name\|alloc-port\|init\|register\|start\|stop\|health-check\|status' usr/bin/webapp-helper` should be >= 8.
Verify constants are at top: `head -20 usr/bin/webapp-helper` shows API_URL, APPS_DIR, TEMPLATES_DIR.
  </verify>
  <done>
usr/bin/webapp-helper exists, is executable, passes bash syntax check, has all 8 subcommands with consistent error handling, hardcoded constants at top, reserved names list matching app_proxy.py _RESERVED.
  </done>
</task>

<task type="auto">
  <name>Task 2: Update SKILL.md to use webapp-helper subcommands</name>
  <files>usr/skills/web-app-builder/SKILL.md</files>
  <action>
Rewrite Steps 1, 3, 4, 6, 7, 8 in SKILL.md to use `webapp-helper` subcommands. Steps 2 (template selection) and 5 (customization) remain unchanged.

**Step 1 — Validate the app name:** Replace the entire validation bash block (regex check + reserved name loop) with:
```bash
APP_NAME="chosen-name"
webapp-helper validate-name "$APP_NAME"
```
Keep the explanation of rules (regex, reserved names) as documentation but mark the old bash block as replaced. Simplify to show: run the command, if output is `VALID` proceed, if `ERROR:` stop and ask user for new name.

**Step 3 — Allocate a port:** Replace the curl+python3 pipeline with:
```bash
PORT=$(webapp-helper alloc-port)
echo "Allocated port: $PORT"
```
If exit code is non-zero, STOP. Remove the old curl command.

**Step 4 — Copy the template:** Replace the `cp -r` + `ls` verify + `pip3 install` with:
```bash
webapp-helper init "$APP_NAME" "{TEMPLATE}"
```
This handles copy, verification, and pip install. If exit code is non-zero, STOP. Remove old multi-command block.

**Step 6 — Register the app:** Replace the curl POST with:
```bash
webapp-helper register "$APP_NAME" "$PORT" "{START_CMD}" "{DESCRIPTION}"
```
Remove old curl command. Note: cwd is derived automatically (always `/a0/apps/<name>`).

**Step 7 — Start the app:** Replace the curl POST with:
```bash
webapp-helper start "$APP_NAME"
```
Remove old curl command.

**Step 8 — Verify the app is running:** Replace the for-loop polling with:
```bash
webapp-helper health-check "$PORT"
```
Keep the instructions about what to do on HEALTHY vs FAILED.

**Also update the "Management commands" section** at the bottom to show webapp-helper equivalents:
```bash
# List all apps
webapp-helper status

# Stop
webapp-helper stop my-app

# Start
webapp-helper start my-app

# Health check
webapp-helper health-check 9003
```
Keep the curl versions as a "Raw API" reference below, but lead with webapp-helper.

**Keep unchanged:** Steps 2 and 5, the TOOL USAGE section, EXECUTION FLOW, INTERNAL vs EXTERNAL URLs, FALLBACK FORBIDDEN, How routing works, Troubleshooting, Template customization quick reference. Also keep the SKILL.md YAML frontmatter unchanged.

**Update the description** in the YAML frontmatter to mention webapp-helper: add "Uses webapp-helper CLI for API interactions." to the end of the description string.
  </action>
  <verify>
Verify webapp-helper appears in Steps 1, 3, 4, 6, 7, 8: `grep -c 'webapp-helper' usr/skills/web-app-builder/SKILL.md` should be >= 10.
Verify Steps 2 and 5 are preserved: `grep -c 'Auto-select a template\|Customize the app' usr/skills/web-app-builder/SKILL.md` should be 2.
Verify no raw curl commands remain in Steps 1, 3, 4, 6, 7, 8 (curl should only appear in Management commands "Raw API" section and Troubleshooting).
  </verify>
  <done>
SKILL.md Steps 1, 3, 4, 6, 7, 8 use webapp-helper subcommands. Steps 2 and 5 unchanged. Management commands section leads with webapp-helper. Old curl commands preserved only as raw API reference.
  </done>
</task>

<task type="auto">
  <name>Task 3: Update system tips to mention webapp-helper</name>
  <files>prompts/agent.system.main.tips.md</files>
  <action>
In `prompts/agent.system.main.tips.md`, update the "Apps System -- MANDATORY" section:

1. Add a line after the opening paragraph: `Use the `webapp-helper` CLI for all webapp API operations (name validation, port allocation, init, register, start, stop, health checks). Do NOT construct raw curl commands to http://localhost/webapp -- use webapp-helper subcommands instead.`

2. Update point 4 to read: `4. NEVER pick your own port -- use `webapp-helper alloc-port` to allocate ports`

3. Update the "CRITICAL: Internal vs External URLs" section to add: `- **CLI helper:** `webapp-helper` handles all internal API calls -- you never need to construct URLs manually`

Keep everything else unchanged. The tips file is small; make targeted edits only.
  </action>
  <verify>
`grep -c 'webapp-helper' prompts/agent.system.main.tips.md` should be >= 3.
Verify the rest of the file is intact: `wc -l prompts/agent.system.main.tips.md` should be close to original line count (was 53 lines, expect ~56-58 after additions).
  </verify>
  <done>
System tips mention webapp-helper as the tool for all webapp operations. Raw curl construction is explicitly discouraged. Port allocation points to webapp-helper alloc-port.
  </done>
</task>

</tasks>

<verification>
1. `bash -n usr/bin/webapp-helper` -- script has no syntax errors
2. `grep -c 'webapp-helper' usr/skills/web-app-builder/SKILL.md` -- at least 10 occurrences
3. `grep -c 'webapp-helper' prompts/agent.system.main.tips.md` -- at least 3 occurrences
4. All 8 subcommands present in script: validate-name, alloc-port, init, register, start, stop, health-check, status
5. SKILL.md Steps 2 and 5 unchanged (template selection and customization)
6. No raw curl to localhost/webapp in SKILL.md Steps 1, 3, 4, 6, 7, 8
</verification>

<success_criteria>
- webapp-helper script exists, is executable, passes syntax check, has all 8 subcommands
- SKILL.md uses webapp-helper in 6 of 8 steps (Steps 2 and 5 stay manual)
- System tips direct agent to use webapp-helper instead of raw curl
- All output formats are machine-parseable (single line, consistent exit codes)
- Constants (API_URL, APPS_DIR, TEMPLATES_DIR, RESERVED) are hardcoded once at script top
</success_criteria>

<output>
After completion, create `.planning/quick/7-create-webapp-helper-cli-script-that-enc/7-SUMMARY.md`
</output>
