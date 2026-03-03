---
phase: quick-6
plan: 01
subsystem: agent-prompts
tags: [bug-fix, url-fix, app-builder, system-prompt, skill]
dependency_graph:
  requires: []
  provides: [correct-internal-url-guidance, standalone-app-prohibition, fallback-prevention]
  affects: [prompts/agent.system.main.tips.md, usr/skills/web-app-builder/SKILL.md]
tech_stack:
  added: []
  patterns: [internal-vs-external-url-distinction, explicit-prohibition-directives]
key_files:
  created: []
  modified:
    - prompts/agent.system.main.tips.md
    - usr/skills/web-app-builder/SKILL.md
decisions:
  - "Use explicit WARNING with 'Connection refused' language so agent recognizes the error pattern before it occurs"
  - "Place URL section before MANDATORY SEQUENCE in SKILL.md so it's read before any steps are attempted"
  - "FALLBACK FORBIDDEN placed as a named section so it's scannable and distinct from the execution flow"
metrics:
  duration: "2 minutes"
  completed: "2026-03-03"
  tasks_completed: 2
  files_modified: 2
---

# Phase quick-6 Plan 01: Fix Root Cause of App Creation Failures Summary

**One-liner:** Corrected internal-vs-external URL confusion (localhost:50000 vs http://localhost/webapp) and added explicit standalone-app prohibitions in both system prompt and SKILL.md.

## What Was Built

Fixed the two-part failure chain that caused broken app creation:

1. **Root cause:** Agent was curling `localhost:50000` from inside the Docker container. Port 50000 is the HOST-side port mapping — the container's web server runs on port 80. This produced `ConnectionRefusedError`, causing the webapp API calls to fail.

2. **Failure cascade:** When the API calls failed, no guardrails prevented the agent from "working around" the failure by writing a standalone Flask app from scratch in the workdir — bypassing the entire Apps System.

## Changes Made

### `prompts/agent.system.main.tips.md`
- Updated item 6 to distinguish external user URL from internal API URL
- Added `## CRITICAL: Internal vs External URLs` section with explicit bullet points explaining the port mapping
- Added `## FORBIDDEN — Standalone Apps` section with 5 specific prohibitions

### `usr/skills/web-app-builder/SKILL.md`
- Updated YAML `description` field to mention `http://localhost/webapp (not port 50000)`
- Added `## INTERNAL vs EXTERNAL URLs — READ THIS CAREFULLY` section with a comparison table (inserted between EXECUTION FLOW and How routing works)
- Added `## FALLBACK FORBIDDEN` section with explicit list of prohibited actions

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix system prompt — correct internal URLs and add standalone app prohibition | 5016e14 | prompts/agent.system.main.tips.md |
| 2 | Fix SKILL.md — add URL clarification and fallback prevention directive | 85d4ba0 | usr/skills/web-app-builder/SKILL.md |

## Verification Results

- `localhost:50000` appears only in user-facing contexts (telling user their app URL, routing diagram, and warning NOT to use it for curl)
- `FALLBACK FORBIDDEN` section present in SKILL.md
- `FORBIDDEN` section present in tips.md
- `http://localhost/webapp` appears 3 times in tips.md and 12 times in SKILL.md
- No instruction tells the agent to curl localhost:50000 from inside the container

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files confirmed:
- FOUND: prompts/agent.system.main.tips.md (verified via Read tool)
- FOUND: usr/skills/web-app-builder/SKILL.md (verified via Read tool)

Commits confirmed:
- FOUND: 5016e14 (Task 1 commit)
- FOUND: 85d4ba0 (Task 2 commit)
