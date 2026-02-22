---
name: gsd-quick
description: Execute a quick task with GSD guarantees (atomic commits, state tracking) but skip optional agents
allowed-tools:
  - code_execution_tool
  - call_subordinate
  - input
---

<objective>
Execute small, ad-hoc tasks with GSD guarantees (atomic commits, STATE.md tracking).

Quick mode is the same GSD system with a shorter path:
- Spawns gsd-planner (quick mode) + gsd-executor
- Quick tasks live in `.planning/quick/` separate from planned phases
- Updates STATE.md "Quick Tasks Completed" table (NOT ROADMAP.md)

**Default:** Skips research, plan-checker, verifier. Use when you know exactly what to do.

**`--full` flag:** Enables plan-checking (max 2 iterations) and post-execution verification. Use when you want quality guarantees without full milestone ceremony.

The task description and optional `--full` flag are provided by the user when invoking this skill.
</objective>

<process>

## Step 1: Parse Arguments and Get Task Description

Parse the user's input for:
- `--full` flag → store as `FULL_MODE` (true/false)
- Remaining text → use as `DESCRIPTION` if non-empty

If `DESCRIPTION` is empty after parsing, use `input` to ask:
- header: "Quick Task"
- question: "What do you want to do?"

Store response as `DESCRIPTION`.

If still empty: re-prompt "Please provide a task description."

If `FULL_MODE`:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GSD ► QUICK TASK (FULL MODE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

◆ Plan checking + verification enabled
```

## Step 2: Initialize

Load project state by reading `.planning/STATE.md` and `.planning/config.json`. Extract: model preferences, `commit_docs`, date, next quick task number (`next_num` = count of existing dirs in `.planning/quick/` + 1, formatted as 3 digits: 001, 002...), slug (lowercase, hyphens, max 40 chars derived from `DESCRIPTION`).

Resolve: `quick_dir` = `.planning/quick/`, `task_dir` = `.planning/quick/[next_num]-[slug]/`.

**If `.planning/ROADMAP.md` does not exist:** Error — Quick mode requires an active project with ROADMAP.md. Use the `gsd-new-project` skill first.

Note: Quick tasks can run mid-phase. Validation only checks ROADMAP.md exists, not phase status.

## Step 3: Create Task Directory

```bash
mkdir -p "[task_dir]"
```

## Step 4: Report Task Creation

Report to user:
```
Creating quick task [next_num]: [DESCRIPTION]
Directory: [task_dir]
```

Store `QUICK_DIR` = `task_dir` for use in orchestration.

## Step 5: Spawn gsd-planner Subagent (Quick Mode)

**If `FULL_MODE`:** Use `quick-full` mode with stricter constraints.
**If NOT `FULL_MODE`:** Use standard `quick` mode.

Use `call_subordinate` to create a quick task plan:
- **message**: Include the planner's full role identity as a GSD planner in quick mode. Include:
  - Mode: `quick-full` (if FULL_MODE) or `quick`
  - Directory: `[QUICK_DIR]`
  - Description: `[DESCRIPTION]`
  - Files to read: `.planning/STATE.md` (project state), `./CLAUDE.md` if it exists (project-specific guidelines)
  - Project skills: check `.agents/skills/` directory if it exists — read SKILL.md files, plans should account for project skill rules
  - Constraints: create a SINGLE plan with 1-3 focused tasks; quick tasks should be atomic and self-contained; no research phase; target ~30% context usage (40% for full mode)
  - If FULL_MODE: MUST generate `must_haves` in plan frontmatter (truths, artifacts, key_links); each task MUST have `files`, `action`, `verify`, `done` fields
  - Output: write plan to `[QUICK_DIR]/[next_num]-PLAN.md`
  - Expected return: `## PLANNING COMPLETE` with plan path
- **reset**: `"true"`

After planner returns:
1. Verify plan exists at `[QUICK_DIR]/[next_num]-PLAN.md`
2. Report: "Plan created: [QUICK_DIR]/[next_num]-PLAN.md"
3. If plan not found: Error — "Planner failed to create [next_num]-PLAN.md"

## Step 5.5: Plan-checker Loop (only when FULL_MODE)

Skip entirely if NOT FULL_MODE.

Display:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GSD ► CHECKING PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

◆ Spawning plan checker...
```

Use `call_subordinate` to verify the quick plan:
- **message**: Include the checker's full role identity as a GSD plan quality checker agent. Include:
  - Mode: quick-full
  - Task Description: `[DESCRIPTION]`
  - Files to read: `[QUICK_DIR]/[next_num]-PLAN.md`
  - Scope: this is a quick task, not a full phase. Skip checks requiring a ROADMAP phase goal.
  - Check dimensions: requirement coverage (does plan address task description?), task completeness (do tasks have files, action, verify, done fields?), key links (are referenced files real?), scope sanity (1-3 tasks appropriate for quick task?), must_haves derivation (traceable to task description?)
  - Skip: context compliance (no CONTEXT.md), cross-plan deps (single plan), ROADMAP alignment
  - Expected return: `## VERIFICATION PASSED` — all checks pass, or `## ISSUES FOUND` — structured issue list
- **reset**: `"true"`

**Handle checker return:**
- **`## VERIFICATION PASSED`:** Display confirmation, proceed to step 6.
- **`## ISSUES FOUND`:** Display issues, enter revision loop.

**Revision loop (max 2 iterations):**

Track `iteration_count` (starts at 1 after initial plan + check).

If iteration_count < 2: Display `Sending back to planner for revision... (iteration [N]/2)`

Use `call_subordinate` for planner revision:
- **message**: Include planner role identity. Mode: quick-full (revision). Files to read: existing plan at `[QUICK_DIR]/[next_num]-PLAN.md`. Checker issues: `[structured_issues_from_checker]`. Instructions: make targeted updates to address issues, do NOT replan from scratch unless issues are fundamental, return what changed.
- **reset**: `"true"`

After planner returns: spawn checker again, increment iteration_count.

If iteration_count >= 2: Display `Max iterations reached. [N] issues remain:` + issue list. Offer: 1) Force proceed, 2) Abort.

## Step 6: Spawn gsd-executor Subagent

Use `call_subordinate` to execute the quick task plan:
- **message**: Include the executor's full role identity as a GSD plan execution specialist. Include:
  - "Execute quick task [next_num]."
  - Files to read: `[QUICK_DIR]/[next_num]-PLAN.md` (plan), `.planning/STATE.md` (project state), `./CLAUDE.md` if it exists (project instructions), `.agents/skills/` if it exists (project skills)
  - Constraints: execute all tasks in the plan; commit each task atomically; create summary at `[QUICK_DIR]/[next_num]-SUMMARY.md`; do NOT update ROADMAP.md (quick tasks are separate from planned phases)
  - Expected return: `## PLAN COMPLETE` or `## CHECKPOINT REACHED`
- **reset**: `"true"`

After executor returns:
1. Verify summary exists at `[QUICK_DIR]/[next_num]-SUMMARY.md`
2. Extract commit hash from executor output
3. If summary not found: Error — "Executor failed to create [next_num]-SUMMARY.md"

## Step 6.5: Verification (only when FULL_MODE)

Skip entirely if NOT FULL_MODE.

Display:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GSD ► VERIFYING RESULTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

◆ Spawning verifier...
```

Use `call_subordinate` to verify goal achievement:
- **message**: Include verifier role identity. Task: verify quick task goal achievement. Task directory: `[QUICK_DIR]`. Task goal: `[DESCRIPTION]`. Files to read: `[QUICK_DIR]/[next_num]-PLAN.md`. Instruction: check must_haves against actual codebase. Create VERIFICATION.md at `[QUICK_DIR]/[next_num]-VERIFICATION.md`.
- **reset**: `"true"`

Read verification status from `[QUICK_DIR]/[next_num]-VERIFICATION.md` (the `status:` field).

| Status | Action |
|--------|--------|
| `passed` | Store VERIFICATION_STATUS = "Verified", continue to step 7 |
| `human_needed` | Display items needing manual check, store VERIFICATION_STATUS = "Needs Review", continue |
| `gaps_found` | Display gap summary, offer: 1) Re-run executor to fix gaps, 2) Accept as-is. Store VERIFICATION_STATUS = "Gaps" |

## Step 7: Update STATE.md

Update STATE.md with the quick task completion record.

**7a. Check if "Quick Tasks Completed" section exists** in STATE.md.

**7b. If section doesn't exist, create it** after the Blockers/Concerns section:

If FULL_MODE:
```markdown
### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
```

If NOT FULL_MODE:
```markdown
### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
```

**Note:** If the table already exists, match its existing column format.

**7c. Append new row to table:**

If FULL_MODE (or table has Status column):
```
| [next_num] | [DESCRIPTION] | [date] | [commit_hash] | [VERIFICATION_STATUS] | [next_num]-[slug] |
```

If NOT FULL_MODE (no Status column):
```
| [next_num] | [DESCRIPTION] | [date] | [commit_hash] | [next_num]-[slug] |
```

**7d. Update "Last activity" line:**
```
Last activity: [date] - Completed quick task [next_num]: [DESCRIPTION]
```

## Step 8: Final Commit and Completion

Stage and commit quick task artifacts:

File list:
- `[QUICK_DIR]/[next_num]-PLAN.md`
- `[QUICK_DIR]/[next_num]-SUMMARY.md`
- `.planning/STATE.md`
- If FULL_MODE and verification file exists: `[QUICK_DIR]/[next_num]-VERIFICATION.md`

```bash
git add [file_list]
git commit -m "docs(quick-[next_num]): [DESCRIPTION]"
```

Get final commit hash:
```bash
commit_hash=$(git rev-parse --short HEAD)
```

Display completion:

If FULL_MODE:
```
GSD > QUICK TASK COMPLETE (FULL MODE)

Quick Task [next_num]: [DESCRIPTION]

Summary: [QUICK_DIR]/[next_num]-SUMMARY.md
Verification: [QUICK_DIR]/[next_num]-VERIFICATION.md ([VERIFICATION_STATUS])
Commit: [commit_hash]

Ready for next task: gsd-quick skill
```

If NOT FULL_MODE:
```
GSD > QUICK TASK COMPLETE

Quick Task [next_num]: [DESCRIPTION]

Summary: [QUICK_DIR]/[next_num]-SUMMARY.md
Commit: [commit_hash]

Ready for next task: gsd-quick skill
```

</process>

<success_criteria>
- [ ] ROADMAP.md validation passes
- [ ] User provides task description
- [ ] `--full` flag parsed from arguments when present
- [ ] Slug generated (lowercase, hyphens, max 40 chars)
- [ ] Next number calculated (001, 002, 003...)
- [ ] Directory created at `.planning/quick/NNN-slug/`
- [ ] `[next_num]-PLAN.md` created by planner
- [ ] (--full) Plan checker validates plan, revision loop capped at 2 iterations
- [ ] gsd-executor spawned with plan path and returns `## PLAN COMPLETE` or `## CHECKPOINT REACHED`
- [ ] `[next_num]-SUMMARY.md` created by executor
- [ ] (--full) `[next_num]-VERIFICATION.md` created by verifier
- [ ] STATE.md updated with quick task row (Status column when --full)
- [ ] Artifacts committed atomically
</success_criteria>
