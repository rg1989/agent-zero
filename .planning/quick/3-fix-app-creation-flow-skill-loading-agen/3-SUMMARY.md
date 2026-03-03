---
phase: quick-3
plan: "01"
subsystem: skills
tags: [skills, web-app-builder, auto-load, agent-loop, fix]
dependency_graph:
  requires: []
  provides: [web-app-builder skill correct tool usage, persistent auto-load directive]
  affects: [usr/skills/web-app-builder/SKILL.md, python/extensions/message_loop_prompts_after/_62_auto_load_triggered_skills.py]
tech_stack:
  added: []
  patterns: [extras_persistent for cross-iteration directive injection]
key_files:
  created: []
  modified:
    - usr/skills/web-app-builder/SKILL.md
    - python/extensions/message_loop_prompts_after/_62_auto_load_triggered_skills.py
decisions:
  - "Use extras_persistent instead of extras_temporary so auto-load directive survives across agent loop iterations"
  - "Add explicit TOOL USAGE section to SKILL.md banning Python runtime and mandating terminal runtime with curl"
  - "Add explicit EXECUTION FLOW section to SKILL.md forbidding mid-sequence stops after Step 2"
metrics:
  duration: "~10 minutes"
  completed: "2026-03-03"
  tasks_completed: 3
  files_modified: 2
---

# Quick Task 3: Fix App Creation Flow — Skill Loading & Agent Execution Summary

**One-liner:** Fixed web-app-builder skill to mandate terminal runtime for curl calls and persist the auto-load directive across agent loop iterations so the agent executes all 8 steps without stopping.

## What Was Done

### Task 1 — SKILL.md: Add TOOL USAGE and EXECUTION FLOW directives (commit: ccd054f)

Added two new sections to `usr/skills/web-app-builder/SKILL.md` immediately after the CRITICAL line and before "How routing works":

**TOOL USAGE — READ THIS FIRST:**
- Explicitly mandates `code_execution_tool` with `runtime: "terminal"` for all bash steps
- Explicitly bans `runtime: "python"` and Python module imports
- Provides a correct JSON tool call example showing `runtime: "terminal"`

**EXECUTION FLOW — DO NOT STOP:**
- Mandates executing all 8 steps in a single uninterrupted sequence
- Explicitly forbids stopping to ask "shall I proceed?" between steps
- Only allows stopping for errors or invalid app names

Also updated Step 2 to add "immediately continue to Step 3 without waiting for user input" and added a `# Use code_execution_tool with runtime: "terminal"` comment to Step 3's code block.

All existing content (steps 1–8, management commands, troubleshooting, template quick reference, YAML frontmatter) preserved intact.

### Task 2 — Persist auto-load directive across agent loop iterations (commit: e189508)

Changed line 66 in `python/extensions/message_loop_prompts_after/_62_auto_load_triggered_skills.py`:

```python
# Before (directive cleared after first iteration):
loop_data.extras_temporary["auto_loaded_skills_directive"] = directive

# After (directive persists for duration of conversation):
loop_data.extras_persistent["auto_loaded_skills_directive"] = directive
```

**Why this matters:** `extras_temporary` is cleared by `agent.py` at the start of each loop iteration (line 561). If the agent stops after Step 2 and a new iteration begins, the "execute all steps end-to-end" directive was silently dropped. Switching to `extras_persistent` ensures the directive remains visible for the full app-building sequence.

### Task 3 — Verify previously-fixed issues (no changes)

Confirmed both previously-fixed issues remain intact:
- `python/tools/skills_tool.py` line 126: uses `.get(DATA_NAME_LOADED_SKILLS)` — no KeyError
- `python/extensions/message_loop_prompts_after/_62_auto_load_triggered_skills.py` line 48: uses `.get(DATA_NAME_LOADED_SKILLS) or []`
- `docker/run/fs/ins/install_additional.sh`: NO `pip3 install flask` line (already removed)

## Deviations from Plan

None — plan executed exactly as written.

## Root Causes Fixed

| # | Issue | Root Cause | Fix |
|---|-------|------------|-----|
| 1 | Agent uses Python runtime instead of terminal | SKILL.md had no explicit tool-usage instructions | Added TOOL USAGE section with JSON example and explicit ban on Python runtime |
| 2 | Agent stops after Step 2 waiting for user input | SKILL.md had no "do not stop" directive | Added EXECUTION FLOW section; updated Step 2 to say "immediately continue" |
| 3 | Auto-load directive disappears on iteration 2+ | Used `extras_temporary` which is cleared each iteration | Changed to `extras_persistent` |

## Self-Check

Files modified:
- [x] `usr/skills/web-app-builder/SKILL.md` — TOOL USAGE and EXECUTION FLOW sections present
- [x] `python/extensions/message_loop_prompts_after/_62_auto_load_triggered_skills.py` — line 66 uses `extras_persistent`

Commits:
- [x] ccd054f — feat(quick-3): add TOOL USAGE and EXECUTION FLOW directives to SKILL.md
- [x] e189508 — fix(quick-3): persist auto-load directive across agent loop iterations

**Self-Check: PASSED**
