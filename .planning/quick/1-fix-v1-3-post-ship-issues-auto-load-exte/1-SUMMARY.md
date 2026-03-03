---
phase: quick-1
plan: 1
status: complete
tasks_completed: 5
files_changed: 13
---

# Quick Task 1: Fix v1.3 Post-Ship Issues — Summary

## What Changed

### 1. Flask installed in Docker image
- Added `pip3 install --break-system-packages flask` to `docker/run/fs/ins/install_additional.sh`
- Flask is now baked into every fresh build

### 2. Template requirements.txt fixed (all 7)
- Uncommented `flask>=3.0.0` in all template requirements.txt files
- `pip install -r requirements.txt` now actually installs Flask

### 3. SKILL.md v3.0.0 updated with 4 improvements
- **Pip install step** after Step 4 (copy template): runs `pip3 install -r requirements.txt` automatically
- **In-place edit instruction** in Step 5: tells agent to use sed/python replace, not rewrite entire files
- **Mobile-responsive rule** in Step 5: preserve viewport meta, media queries, flexible layouts
- **Broader trigger patterns**: `" app"`, `"dashboard"`, `"tracker"`, `"manager"`, `"monitor"`, `"viewer"` etc.

### 4. Auto-load extension created
- New file: `python/extensions/message_loop_prompts_after/_62_auto_load_triggered_skills.py`
- Runs at `message_loop_prompts_after` hook, before skill injection (`_65`)
- Matches user message against SKILL.md `trigger_patterns` (substring, deterministic)
- Auto-loads matching skills into agent context — no `skills_tool:load` call needed
- Injects directive: "skill already loaded, proceed immediately, execute all steps"

### 5. System prompt tips updated
- Removed "FIRST: skills_tool:load" instruction
- Added "skill auto-loads into your context, do NOT call skills_tool:load"
- Added "Execute ALL steps end-to-end in one go — do not stop to describe plans"
- Added mobile-responsive constraint to PROJECT.md

## Decisions
- Auto-load extension over prompt-only enforcement: deterministic, can't be ignored by LLM
- Broad trigger patterns with low false-positive cost: skill loads but agent ignores if irrelevant
- `extras_temporary` for directive: only shows on first turn, doesn't persist
