---
phase: quick-1
plan: 1
description: "Fix v1.3 post-ship issues: auto-load extension, SKILL.md updates, Flask install, requirements.txt, Dockerfile"
tasks: 5
---

# Quick Task 1: Fix v1.3 Post-Ship Issues

## Context

After shipping v1.3, testing revealed several issues with the app builder workflow:
1. Flask not installed in container — apps fail with "no module named flask"
2. Agent ignores system prompt tips and builds apps outside the Apps System
3. Agent rewrites entire HTML files from scratch instead of editing templates in place
4. Template requirements.txt files have Flask commented out
5. Agent wastes tokens calling skills_tool:load manually

## Tasks

### Task 1: Install Flask and update Dockerfile
- **files**: `docker/run/fs/ins/install_additional.sh`
- **action**: Add `pip3 install --break-system-packages flask` to Dockerfile install script
- **verify**: grep for "flask" in install_additional.sh
- **done**: Flask baked into future Docker builds

### Task 2: Fix template requirements.txt files
- **files**: `apps/_templates/*/requirements.txt` (all 7)
- **action**: Uncomment `flask>=3.0.0` in all template requirements.txt files
- **verify**: All 7 files contain uncommented `flask>=3.0.0`
- **done**: pip install -r requirements.txt actually installs Flask

### Task 3: Update SKILL.md with pip install step, in-place edit rule, mobile rule
- **files**: `usr/skills/web-app-builder/SKILL.md`
- **action**: Add pip install step after Step 4, add in-place edit instruction to Step 5, add mobile-responsive rule, update trigger patterns
- **verify**: SKILL.md contains "Install dependencies", "in place", "Mobile-responsive", broad trigger patterns
- **done**: Agent installs deps, edits files in place, preserves responsive layouts

### Task 4: Create auto-load extension for deterministic skill loading
- **files**: `python/extensions/message_loop_prompts_after/_62_auto_load_triggered_skills.py`
- **action**: Create extension that matches user message against SKILL.md trigger_patterns and auto-loads matching skills before LLM processes the message
- **verify**: Extension file exists with AutoLoadTriggeredSkills class
- **done**: Skills load deterministically based on keywords, no LLM decision needed

### Task 5: Update system prompt tips
- **files**: `prompts/agent.system.main.tips.md`
- **action**: Remove manual skills_tool:load instruction, add "skill auto-loads" and "execute all steps end-to-end" directives
- **verify**: No "FIRST: skills_tool:load" instruction, has "auto-loads" and "Execute ALL steps"
- **done**: Agent doesn't waste tokens on manual skill loading, executes without stopping
