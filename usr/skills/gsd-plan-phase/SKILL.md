---
name: gsd-plan-phase
description: Create detailed phase plan (PLAN.md) with verification loop — orchestrates research, planning, and plan-checking subagents
allowed-tools:
  - code_execution_tool
  - call_subordinate
  - search_engine
---

<objective>
Create executable phase prompts (PLAN.md files) for a roadmap phase with integrated research and verification.

**Default flow:** Research (if needed) → Plan → Verify → Done

**Orchestrator role:** Parse arguments, validate phase, research domain (unless skipped), spawn gsd-planner, verify with gsd-plan-checker, iterate until pass or max iterations, present results.

**Flags:**
- `--research` — Force re-research even if RESEARCH.md exists
- `--skip-research` — Skip research, go straight to planning
- `--gaps` — Gap closure mode (reads VERIFICATION.md, skips research)
- `--skip-verify` — Skip verification loop

For library documentation lookup, use `search_engine` or search directly — the Context7 MCP tool is Claude Code-specific and is not available in Agent Zero.

**Output formatting:** For consistent output, use professional markdown: clear headers, avoid excessive emoji. Use `━` banners for stage transitions.
</objective>

<process>

## Step 1: Initialize

Load all context in one pass (paths only — do not inline file contents in orchestrator context):

Read `.planning/config.json` to extract: `research_enabled`, `plan_checker_enabled`, `commit_docs`, model preferences.

Read `.planning/ROADMAP.md` to extract: phase directory, phase number, phase name, phase slug, padded phase, has research, has context, has plans, plan count, roadmap exists.

Resolve file paths (null if files don't exist): `state_path`, `roadmap_path`, `requirements_path`, `context_path`, `research_path`, `verification_path`, `uat_path`.

**If `.planning/` does not exist:** Error — use the `gsd-new-project` skill first.

## Step 2: Parse and Normalize Arguments

Extract from the phase number and flags provided by the user:
- Phase number (integer or decimal like `2.1`), or auto-detect next unplanned phase if omitted
- Flags: `--research`, `--skip-research`, `--gaps`, `--skip-verify`

**If no phase number:** Detect next unplanned phase from ROADMAP.md.

**If phase directory doesn't exist:** Create it:
```bash
mkdir -p ".planning/phases/[padded_phase]-[phase_slug]"
```

## Step 3: Validate Phase

Look up the phase entry in `.planning/ROADMAP.md` by phase number to get `phase_number`, `phase_name`, and `goal`.

**If phase not found:** Error with list of available phases.

## Step 4: Load CONTEXT.md

Check if a CONTEXT.md exists for this phase (from the `gsd-discuss-phase` skill).

If CONTEXT.md exists: display "Using phase context from: [context_path]"

If no CONTEXT.md exists: use `input` to ask:
- header: "No context"
- question: "No CONTEXT.md found for Phase [X]. Plans will use research and requirements only. Continue or capture context first?"
- options:
  - "Continue without context" — Plan using research + requirements only
  - "Run discuss-phase first" — Capture design decisions before planning

If "Run discuss-phase first": instruct user to use `gsd-discuss-phase` for this phase, then exit.

## Step 5: Handle Research

**Skip if:** `--gaps` flag, `--skip-research` flag, or `research_enabled` is false without `--research` override.

**If RESEARCH.md exists AND no `--research` flag:** Use existing, skip to step 6.

**If RESEARCH.md missing OR `--research` flag:**

Display:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GSD ► RESEARCHING PHASE [X]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

◆ Spawning researcher...
```

### Spawn gsd-phase-researcher Subagent

Use `call_subordinate` to delegate phase research:
- **message**: Include the researcher's full role identity as a GSD phase researcher agent. Include: research type (phase research), phase number and name, phase goal and description, phase requirement IDs that MUST be addressed, paths to context, requirements, and state files for the researcher to read, instruction to read `./CLAUDE.md` if it exists (project-specific guidelines), and the expected output location (`[phase_dir]/[phase_num]-RESEARCH.md`). Also check `.agents/skills/` directory for project skill patterns.
- **reset**: `"true"` for a new research session

### Handle Researcher Return

- **`## RESEARCH COMPLETE`:** Display confirmation, continue to step 6.
- **`## RESEARCH BLOCKED`:** Display blocker. Offer: 1) Provide context, 2) Skip research, 3) Abort.

## Step 6: Check Existing Plans

Check for `*-PLAN.md` files in the phase directory.

**If plans exist:** Offer:
1. Add more plans
2. View existing plans
3. Replan from scratch

## Step 7: Use Context Paths

Ensure paths from initialization are available: `state_path`, `roadmap_path`, `requirements_path`, `research_path`, `verification_path`, `uat_path`, `context_path`.

## Step 8: Spawn gsd-planner Subagent

Display:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GSD ► PLANNING PHASE [X]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

◆ Spawning planner...
```

Use `call_subordinate` to create phase plans:
- **message**: Include the planner's full role identity as a GSD planner agent. Include: phase number, mode (standard or gap_closure for `--gaps`), paths to all context files via `files_to_read` block (state, roadmap, requirements, context, research, verification if --gaps, UAT if --gaps), phase requirement IDs (every ID MUST appear in a plan's `requirements` field), instruction to read `./CLAUDE.md` if it exists, instruction to check `.agents/skills/` directory. Also include downstream consumer note: output consumed by `gsd-execute-phase` and needs frontmatter (wave, depends_on, files_modified, autonomous), tasks in XML format, verification criteria, and must_haves for goal-backward verification.
- **reset**: `"true"` for a new planning session

## Step 9: Handle Planner Return

- **`## PLANNING COMPLETE`:** Display plan count. If `--skip-verify` or `plan_checker_enabled` is false: skip to step 13. Otherwise: proceed to step 10.
- **`## CHECKPOINT REACHED`:** Present to user, get response, spawn continuation (step 12).
- **`## PLANNING INCONCLUSIVE`:** Show attempts, offer: Add context / Retry / Manual.

## Step 10: Spawn gsd-plan-checker Subagent

Display:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GSD ► VERIFYING PLANS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

◆ Spawning plan checker...
```

Use `call_subordinate` to verify plan quality:
- **message**: Include the checker's full role identity as a GSD plan quality checker agent. Include: phase number, phase goal from ROADMAP, paths to all PLAN.md files created by the planner (via `files_to_read` block), roadmap path, requirements path, context path, phase requirement IDs (MUST ALL be covered), instruction to read `./CLAUDE.md` if it exists, instruction to check `.agents/skills/` directory. Expected return format: `## VERIFICATION PASSED` — all checks pass, or `## ISSUES FOUND` — structured issue list.
- **reset**: `"true"` for each verification round

## Step 11: Handle Checker Return

- **`## VERIFICATION PASSED`:** Display confirmation, proceed to step 13.
- **`## ISSUES FOUND`:** Display issues, check iteration count, proceed to step 12.

## Step 12: Revision Loop (Max 3 Iterations)

Track `iteration_count` (starts at 1 after initial plan + check).

**If iteration_count < 3:**

Display: `Sending back to planner for revision... (iteration [N]/3)`

Use `call_subordinate` to send planner a revision:
- **message**: Include planner role identity. Mode: revision. Paths to existing PLAN.md files and CONTEXT.md. Structured issues from checker. Instruction: make targeted updates, do NOT replan from scratch unless issues are fundamental, return what changed.
- **reset**: `"true"`

After planner returns: spawn checker again (step 10), increment iteration_count.

**If iteration_count >= 3:**

Display: `Max iterations reached. [N] issues remain:` + issue list

Offer: 1) Force proceed, 2) Provide guidance and retry, 3) Abandon.

## Step 13: Present Final Status

**If auto-advance is enabled** (user provided `--auto` flag or `workflow.auto_advance` is true in config):

Display:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GSD ► AUTO-ADVANCING TO EXECUTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Plans ready. Spawning execute-phase...
```

Use `call_subordinate` to spawn execute-phase:
- **message**: Include the executor orchestrator role identity. Run execute-phase for this phase number in auto mode. Include path to phase directory and all PLAN.md files.
- **reset**: `"true"`

**Handle execute-phase return:**
- `## PHASE COMPLETE` — Display final summary. Auto-advance pipeline finished. Suggest next: `gsd-discuss-phase [next_phase] --auto`
- `## GAPS FOUND` or `## VERIFICATION FAILED` — Display result, stop chain. Suggest manual continuation with `gsd-execute-phase [phase]`

**If auto-advance is NOT enabled:** Present completion output:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GSD ► PHASE [X] PLANNED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase [X]: [Name] — [N] plan(s) in [M] wave(s)

| Wave | Plans  | What it builds |
|------|--------|----------------|
| 1    | 01, 02 | [objectives]   |
| 2    | 03     | [objective]    |

Research: [Completed | Used existing | Skipped]
Verification: [Passed | Passed with override | Skipped]

Next Up: Execute Phase [X] — run all [N] plans

Use the gsd-execute-phase skill for Phase [X].

Also available:
- cat .planning/phases/[phase-dir]/*-PLAN.md — review plans
- gsd-plan-phase [X] --research — re-research first
```

</process>

<success_criteria>
- [ ] `.planning/` directory validated
- [ ] Phase validated against roadmap
- [ ] Phase directory created if needed
- [ ] CONTEXT.md loaded early (step 4) and passed to ALL agents
- [ ] Research completed (unless --skip-research or --gaps or exists)
- [ ] gsd-phase-researcher spawned with CONTEXT.md
- [ ] Existing plans checked
- [ ] gsd-planner spawned with CONTEXT.md + RESEARCH.md
- [ ] Plans created (`## PLANNING COMPLETE` or `## CHECKPOINT REACHED` handled)
- [ ] gsd-plan-checker spawned with CONTEXT.md
- [ ] Verification passed OR user override OR max iterations with user decision
- [ ] User sees status between agent spawns
- [ ] User knows next steps
</success_criteria>
