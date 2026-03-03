---
phase: quick-3
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - usr/skills/web-app-builder/SKILL.md
  - python/extensions/message_loop_prompts_after/_62_auto_load_triggered_skills.py
autonomous: true
requirements: [FIX-TOOL-RUNTIME, FIX-AGENT-STOPS, ALREADY-FIXED-SKILLS-TOOL, ALREADY-FIXED-DOCKER]

must_haves:
  truths:
    - "Agent uses code_execution_tool with runtime terminal (NOT python) for all curl/bash steps in the web-app-builder skill"
    - "Agent executes all 8 steps end-to-end without stopping for user input between steps"
    - "Agent never tries to import python.helpers.webapp_manager or call python/helpers/webapp.py"
  artifacts:
    - path: "usr/skills/web-app-builder/SKILL.md"
      provides: "Clear instructions forcing terminal runtime and no-stop execution"
    - path: "python/extensions/message_loop_prompts_after/_62_auto_load_triggered_skills.py"
      provides: "Persistent directive that survives across iterations"
  key_links:
    - from: "_62_auto_load_triggered_skills.py"
      to: "agent loop_data.extras_persistent"
      via: "directive injection persists across iterations"
      pattern: "extras_persistent.*auto_loaded_skills_directive"
---

<objective>
Fix the web-app-builder skill so the agent correctly uses bash/terminal runtime for all curl-based API calls and executes the full 8-step sequence without stopping for user confirmation.

Purpose: The agent currently (a) uses Python runtime with broken subprocess/import calls instead of terminal runtime with curl, and (b) stops after step 2 waiting for user input instead of continuing through all 8 steps.

Output: Updated SKILL.md with explicit tool-usage instructions and persistent auto-load directive that survives across agent loop iterations.
</objective>

<execution_context>
@/Users/rgv250cc/.claude/get-shit-done/workflows/execute-plan.md
@/Users/rgv250cc/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@usr/skills/web-app-builder/SKILL.md
@python/extensions/message_loop_prompts_after/_62_auto_load_triggered_skills.py
@python/extensions/message_loop_prompts_after/_65_include_loaded_skills.py
@prompts/agent.system.tool.code_exe.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add explicit tool-usage and no-stop directives to SKILL.md</name>
  <files>usr/skills/web-app-builder/SKILL.md</files>
  <action>
Add a new section immediately after the "CRITICAL: Follow the MANDATORY SEQUENCE below exactly" line and before the "How routing works" section. This new section must contain two critical directives:

**1. Tool Usage Directive — insert this block:**

```markdown
## TOOL USAGE — READ THIS FIRST

All bash commands in this skill MUST be executed using `code_execution_tool` with `runtime: "terminal"`.

DO NOT use `runtime: "python"` for any step. DO NOT import any Python modules (there is no `python.helpers.webapp_manager` or `python/helpers/webapp.py`). The webapp API is HTTP-only — all interactions use `curl` commands via the terminal.

Correct tool call format for every bash step:
~~~json
{
    "thoughts": ["Executing step N of web-app-builder skill..."],
    "headline": "Step N: <description>",
    "tool_name": "code_execution_tool",
    "tool_args": {
        "runtime": "terminal",
        "session": 0,
        "reset": false,
        "code": "<bash commands from the step>"
    }
}
~~~
```

**2. Execution Flow Directive — add immediately after the tool usage block:**

```markdown
## EXECUTION FLOW — DO NOT STOP

Execute ALL 8 steps in a single uninterrupted sequence. After announcing your template selection in Step 2, IMMEDIATELY proceed to Step 3 (allocate port) in the same response. Do NOT wait for user confirmation between steps.

The only acceptable reasons to stop mid-sequence are:
- A step returns an error (STOP and report it)
- The app name is invalid or reserved in Step 1 (STOP and ask for a new name)

Do NOT stop to ask "shall I proceed?" or "would you like me to continue?" — just execute.
```

Additionally, update the Step 2 section. After the line that says `"I'll use the **{template-name}** template..."`, add this sentence: "Then immediately continue to Step 3 without waiting for user input. Only stop if the user actively interrupts."

Also update Step 3's bash code block to add a comment at the top: `# Use code_execution_tool with runtime: "terminal" for this command`

Do NOT change any other content in SKILL.md — keep all existing steps, code blocks, management commands, and troubleshooting exactly as they are.
  </action>
  <verify>
Read the updated SKILL.md and confirm:
1. The "TOOL USAGE" section exists between the CRITICAL line and "How routing works"
2. The "EXECUTION FLOW" section exists
3. The JSON example shows runtime: "terminal"
4. Step 2 includes the "immediately continue" instruction
5. All original content (steps 1-8, management commands, troubleshooting) is preserved intact
6. The YAML frontmatter is unchanged
  </verify>
  <done>SKILL.md contains explicit instructions that force terminal runtime usage and continuous execution, while preserving all existing step content.</done>
</task>

<task type="auto">
  <name>Task 2: Make auto-load directive persistent across agent loop iterations</name>
  <files>python/extensions/message_loop_prompts_after/_62_auto_load_triggered_skills.py</files>
  <action>
The current auto-load directive is injected into `loop_data.extras_temporary`, which gets cleared after every iteration (see agent.py line 561). This means the "Execute ALL steps end-to-end" instruction disappears after the first agent response. If the agent stops after step 2 and a new loop iteration starts, the directive is gone.

Fix: Change the directive injection from `extras_temporary` to `extras_persistent` so it survives across iterations for the duration of the conversation.

On line 66, change:
```python
loop_data.extras_temporary["auto_loaded_skills_directive"] = directive
```
to:
```python
loop_data.extras_persistent["auto_loaded_skills_directive"] = directive
```

This is a single-line change. The `extras_persistent` dict is already used by `_65_include_loaded_skills.py` for injecting skill content, so this is the correct pattern. The directive will now remain in the agent's context as long as the skill is loaded.

No other changes to this file.
  </action>
  <verify>
1. Read the updated file and confirm line 66 uses `extras_persistent` instead of `extras_temporary`
2. Confirm no other lines were changed
3. Run: `cd /Users/rgv250cc/Documents/Projects/agent-zero && python -c "import python.extensions.message_loop_prompts_after._62_auto_load_triggered_skills"` to verify no import errors
  </verify>
  <done>The auto-load directive persists across agent loop iterations, ensuring the "execute all steps without stopping" instruction remains visible to the agent throughout the entire app-building sequence.</done>
</task>

<task type="auto">
  <name>Task 3: Verify already-fixed issues (skills_tool.py and install_additional.sh)</name>
  <files>python/tools/skills_tool.py, docker/run/fs/ins/install_additional.sh</files>
  <action>
These two issues were already fixed in prior commits. This task is verification-only — do NOT modify these files.

**Verify skills_tool.py (Issue 3 — KeyError fix):**
Confirm that line 126 uses `.get()` instead of direct dict access:
```python
if not self.agent.data.get(DATA_NAME_LOADED_SKILLS):
```
This prevents the KeyError when `loaded_skills` key doesn't exist yet. Also confirm line 48 in `_62_auto_load_triggered_skills.py` uses the same `.get()` pattern.

**Verify install_additional.sh (Issue 4 — pip3 fix):**
Confirm there is NO line containing `pip3 install flask` in the file. Flask is installed via `requirements.txt` during Docker build, so the redundant line was correctly removed.

Report the verification results. No file changes needed.
  </action>
  <verify>
1. `grep -n "\.get(DATA_NAME_LOADED_SKILLS)" python/tools/skills_tool.py` — should show line 126
2. `grep -n "pip3 install flask" docker/run/fs/ins/install_additional.sh` — should return no results
3. `grep -n "\.get(DATA_NAME_LOADED_SKILLS)" python/extensions/message_loop_prompts_after/_62_auto_load_triggered_skills.py` — should show line 48
  </verify>
  <done>Both previously-fixed issues confirmed: skills_tool.py uses .get() to avoid KeyError, and install_additional.sh has no redundant pip3 install flask line.</done>
</task>

</tasks>

<verification>
After all tasks complete:
1. SKILL.md has explicit "TOOL USAGE" section mandating runtime: "terminal" for all bash steps
2. SKILL.md has explicit "EXECUTION FLOW" section mandating uninterrupted 8-step execution
3. Auto-load directive uses extras_persistent (not extras_temporary)
4. Previously-fixed issues (skills_tool.py .get(), install_additional.sh pip3 removal) confirmed intact
5. No regressions — all existing SKILL.md content preserved, all existing Python imports valid
</verification>

<success_criteria>
- SKILL.md contains tool-usage block with JSON example showing runtime: "terminal"
- SKILL.md contains execution-flow block forbidding mid-sequence stops
- _62_auto_load_triggered_skills.py uses extras_persistent on line 66
- Both prior fixes verified in place
- Python import check passes for the modified extension
</success_criteria>

<output>
After completion, create `.planning/quick/3-fix-app-creation-flow-skill-loading-agen/3-SUMMARY.md`
</output>
