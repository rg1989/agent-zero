---
name: gsd-execute-phase
description: Execute all plans in a phase with wave-based parallelization — orchestrates plan executor subagents, handles checkpoints, verifies phase goal, and updates roadmap
allowed-tools:
  - code_execution_tool
  - call_subordinate
  - input
---

<objective>
Execute all plans in a phase using wave-based parallel execution.

Orchestrator stays lean: discover plans, analyze dependencies, group into waves, spawn subagents, collect results. Each subagent loads the full execute-plan context and handles its own plan.

Context budget: ~15% orchestrator, 100% fresh per subagent.

For consistent output formatting, follow the project's standard UI/brand conventions (professional markdown output, avoid excessive emoji, use clear headers).
</objective>

<context>
Phase: the phase number or name provided by the user

**Flags:**
- `--gaps-only` — Execute only gap closure plans (plans with `gap_closure: true` in frontmatter). Use after verify-work creates fix plans.
- `--auto` — Auto-advance to next phase after successful verification.

Context files are resolved by loading `.planning/ROADMAP.md` and identifying all PLAN.md files in the target phase directory.
</context>

<process>

<step name="initialize" priority="first">
Load phase context from `.planning/ROADMAP.md` and identify all PLAN.md files in the target phase directory. Read `.planning/STATE.md` before any operation to load project context.

Parse for: `executor_model`, `verifier_model`, `commit_docs`, `parallelization`, `branching_strategy`, `phase_dir`, `phase_number`, `phase_name`, `plans`, `incomplete_plans`, `plan_count`.

**If phase directory not found:** Error — phase directory not found.
**If no plans found in phase:** Error — no plans found in phase.
**If STATE.md missing but .planning/ exists:** Offer reconstruct or continue.

When parallelization is disabled, plans within a wave execute sequentially.
</step>

<step name="handle_branching">
Check branching strategy from project config:

**"none":** Skip, continue on current branch.

**"phase" or "milestone":** Use pre-computed branch name:

```bash
git checkout -b "$BRANCH_NAME" 2>/dev/null || git checkout "$BRANCH_NAME"
```

All subsequent commits go to this branch. User handles merging.
</step>

<step name="validate_phase">
Report: "Found {plan_count} plans in {phase_dir} ({incomplete_count} incomplete)"
</step>

<step name="discover_and_group_plans">
Read all PLAN.md files in the phase directory. Parse frontmatter for `wave`, `autonomous`, `gap_closure` fields.

**Filtering:** Skip plans where a SUMMARY.md already exists. If `--gaps-only`: also skip non-gap_closure plans. If all filtered: "No matching incomplete plans" — exit.

Report:

```
## Execution Plan

**Phase {X}: {Name}** — {total_plans} plans across {wave_count} waves

| Wave | Plans | What it builds |
|------|-------|----------------|
| 1 | 01-01, 01-02 | {from plan objectives, 3-8 words} |
| 2 | 01-03 | ... |
```
</step>

<step name="execute_waves">
Execute each wave in sequence. Within a wave: parallel if parallelization enabled, sequential if not.

**For each wave:**

1. **Describe what's being built (BEFORE spawning):**

   Read each plan's `<objective>`. Extract what's being built and why.

   ```
   * * *
   ## Wave {N}

   **{Plan ID}: {Plan Name}**
   {2-3 sentences: what this builds, technical approach, why it matters}

   Spawning {count} agent(s)...
   * * *
   ```

   - Bad: "Executing terrain generation plan"
   - Good: "Procedural terrain generator using Perlin noise — creates height maps, biome zones, and collision meshes. Required before vehicle physics can interact with ground."

2. **Spawn executor subagents:**

   Pass paths only — executors read files themselves with their fresh 200k context.
   This keeps orchestrator context lean (~10-15%).

   ## Spawn Plan Executor Subagent

   Use `call_subordinate` to execute a single plan:
   - **message**: Include the executor's full role identity as a plan execution specialist,
     the plan file path, phase context, wave number, and expected return format
     (`## PLAN COMPLETE`, `## CHECKPOINT REACHED`, or `## PLAN FAILED`).
     The message should include:
     ```
     <objective>
     Execute plan {plan_number} of phase {phase_number}-{phase_name}.
     Commit each task atomically. Create SUMMARY.md. Update STATE.md and ROADMAP.md.
     </objective>

     <files_to_read>
     Read these files at execution start using the Read tool:
     - {phase_dir}/{plan_file} (Plan)
     - .planning/STATE.md (State)
     - .planning/config.json (Config, if exists)
     - ./CLAUDE.md (Project instructions, if exists)
     - .agents/skills/ (Project skills, if exists)
     </files_to_read>

     <success_criteria>
     - [ ] All tasks executed
     - [ ] Each task committed individually
     - [ ] SUMMARY.md created in plan directory
     - [ ] STATE.md updated with position and decisions
     - [ ] ROADMAP.md updated with plan progress
     </success_criteria>
     ```
   - **reset**: `"true"` for each new plan execution

   For gap closure plans (plans with `gap_closure: true`), use the same call_subordinate
   pattern with context indicating gap closure mode in the message.

3. **Wait for all agents in wave to complete.**

4. **Report completion — spot-check claims first:**

   For each SUMMARY.md:
   - Verify first 2 files from `key-files.created` exist on disk
   - Check `git log --oneline --all --grep="{phase}-{plan}"` returns at least 1 commit
   - Check for `## Self-Check: FAILED` marker

   If ANY spot-check fails: report which plan failed, route to failure handler — ask "Retry plan?" or "Continue with remaining waves?"

   If pass:

   ```
   * * *
   ## Wave {N} Complete

   **{Plan ID}: {Plan Name}**
   {What was built — from SUMMARY.md}
   {Notable deviations, if any}

   {If more waves: what this enables for next wave}
   * * *
   ```

   - Bad: "Wave 2 complete. Proceeding to Wave 3."
   - Good: "Terrain system complete — 3 biome types, height-based texturing, physics collision meshes. Vehicle physics (Wave 3) can now reference ground surfaces."

5. **Handle failures:**

   **Known Claude Code bug (classifyHandoffIfNeeded):** If an agent reports "failed" with error containing `classifyHandoffIfNeeded is not defined`, this is a Claude Code runtime bug — not a GSD or agent issue. The error fires in the completion handler AFTER all tool calls finish. In this case: run the same spot-checks as step 4 (SUMMARY.md exists, git commits present, no Self-Check: FAILED). If spot-checks PASS — treat as successful. If spot-checks FAIL — treat as real failure below.

   For real failures: report which plan failed — ask "Continue?" or "Stop?" — if continue, dependent plans may also fail. If stop, partial completion report.

6. **Execute checkpoint plans between waves** — see `<checkpoint_handling>`.

7. **Proceed to next wave.**
</step>

<step name="checkpoint_handling">
Plans with `autonomous: false` require user interaction.

**Auto-mode checkpoint handling:**

Read auto-advance config from `.planning/config.json` (field: `workflow.auto_advance`).

When executor returns a checkpoint AND auto-advance is enabled:
- **human-verify** — Auto-spawn continuation agent with `{user_response}` = `"approved"`. Log `Auto-approved checkpoint`.
- **decision** — Auto-spawn continuation agent with `{user_response}` = first option from checkpoint details. Log `Auto-selected: [option]`.
- **human-action** — Present to user (existing behavior below). Auth gates cannot be automated.

**Standard flow (not auto-mode, or human-action type):**

1. Spawn agent for checkpoint plan
2. Agent runs until checkpoint task or auth gate — returns structured state
3. Agent return includes: completed tasks table, current task + blocker, checkpoint type/details, what's awaited
4. **Present to user:**

   ```
   ## Checkpoint: [Type]

   **Plan:** 03-03 Dashboard Layout
   **Progress:** 2/3 tasks complete

   [Checkpoint Details from agent return]
   [Awaiting section from agent return]
   ```

5. User responds via `input`: "approved"/"done" | issue description | decision selection
6. **Spawn continuation agent (NOT resume):**
   - Completed tasks table: from checkpoint return
   - Resume task number + name: current task
   - User response: what user provided
   - Resume instructions: based on checkpoint type
7. Continuation agent verifies previous commits, continues from resume point
8. Repeat until plan completes or user stops

**Why fresh agent, not resume:** Resume relies on internal serialization that breaks with parallel tool calls. Fresh agents with explicit state are more reliable.

**Checkpoints in parallel waves:** Agent pauses and returns while other parallel agents may complete. Present checkpoint, spawn continuation, wait for all before next wave.
</step>

<step name="aggregate_results">
After all waves:

```markdown
## Phase {X}: {Name} Execution Complete

**Waves:** {N} | **Plans:** {M}/{total} complete

| Wave | Plans | Status |
|------|-------|--------|
| 1 | plan-01, plan-02 | Complete |
| CP | plan-03 | Verified |
| 2 | plan-04 | Complete |

### Plan Details
1. **03-01**: [one-liner from SUMMARY.md]
2. **03-02**: [one-liner from SUMMARY.md]

### Issues Encountered
[Aggregate from SUMMARYs, or "None"]
```
</step>

<step name="close_parent_artifacts">
**For decimal/polish phases only (X.Y pattern):** Close the feedback loop by resolving parent UAT and debug artifacts.

**Skip if** phase number has no decimal (e.g., `3`, `04`) — only applies to gap-closure phases like `4.1`, `03.1`.

1. Detect decimal phase and derive parent phase number
2. Find parent UAT file in the parent phase directory
3. **If no parent UAT found:** Skip this step
4. Update UAT gap statuses: for each gap entry with `status: failed`, update to `status: resolved`
5. If all gaps now resolved, update UAT frontmatter status to `resolved`
6. For each gap that has a `debug_session:` field: update debug file status to `resolved`, move to `.planning/debug/resolved/`
7. Commit updated artifacts
</step>

<step name="verify_phase_goal">
Verify phase achieved its GOAL, not just completed tasks.

Read phase goal from `.planning/ROADMAP.md` and requirement IDs from plan frontmatter.

## Spawn Phase Verifier Subagent

Use `call_subordinate` to verify phase goal achievement:
- **message**: Include the verifier's full role identity as a phase verification specialist,
  the phase directory path, phase goal (from ROADMAP.md), phase requirement IDs,
  and instruction to check must_haves against the actual codebase and create VERIFICATION.md.
  Expected return: status of `passed`, `human_needed`, or `gaps_found`.
- **reset**: `"true"`

Read status after verifier completes:

```bash
grep "^status:" "$PHASE_DIR"/*-VERIFICATION.md | cut -d: -f2 | tr -d ' '
```

| Status | Action |
|--------|--------|
| `passed` | Proceed to update_roadmap |
| `human_needed` | Present items for human testing, get approval or feedback |
| `gaps_found` | Present gap summary, offer gap closure path |

**If human_needed:**

```
## Phase {X}: {Name} — Human Verification Required

All automated checks passed. {N} items need human testing:

{From VERIFICATION.md human_verification section}

"approved" — continue | Report issues — gap closure
```

**If gaps_found:**

```
## Phase {X}: {Name} — Gaps Found

**Score:** {N}/{M} must-haves verified
**Report:** {phase_dir}/{phase_num}-VERIFICATION.md

### What's Missing
{Gap summaries from VERIFICATION.md}

* * *
## Next Up

Run gap planning using the gsd-plan-phase skill with `--gaps` flag.

Also: `cat {phase_dir}/{phase_num}-VERIFICATION.md` — full report
Also: run gsd-verify-work skill — manual testing first
```

Gap closure cycle: run gsd-plan-phase skill with `--gaps` flag — reads VERIFICATION.md — creates gap plans with `gap_closure: true` — run gsd-execute-phase skill with `--gaps-only` — verifier re-runs.
</step>

<step name="update_roadmap">
**Mark phase complete and update all tracking files:**

```bash
# Mark phase checkbox complete in ROADMAP.md, update STATUS, advance STATE.md to next phase
# Update REQUIREMENTS.md traceability for this phase's requirement IDs
```

Commit updated planning documents.
</step>

<step name="offer_next">
**Exception:** If gaps_found, the verify_phase_goal step already presents the gap-closure path. No additional routing needed — skip auto-advance.

**Auto-advance detection:**

1. Check if `--auto` flag was provided
2. Read `workflow.auto_advance` from `.planning/config.json`

**If `--auto` flag present OR auto_advance config is true (AND verification passed with no gaps):**

```
AUTO-ADVANCING TO TRANSITION
Phase {X} verified, continuing chain
```

Execute the transition workflow inline (do NOT use call_subordinate — orchestrator context is ~10-15%, transition needs phase completion data already in context). Follow transition workflow steps, passing through the `--auto` flag.

**If neither `--auto` nor auto_advance is true:**

The workflow ends. The user invokes the next step manually.
</step>

</process>

<context_efficiency>
Orchestrator: ~10-15% context. Subagents: fresh 200k each. No polling (call_subordinate blocks). No context bleed.
</context_efficiency>

<failure_handling>
- **classifyHandoffIfNeeded false failure:** Agent reports "failed" but error is `classifyHandoffIfNeeded is not defined` — Claude Code runtime bug, not GSD. Spot-check (SUMMARY exists, commits present) — if pass, treat as success
- **Agent fails mid-plan:** Missing SUMMARY.md — report, ask user how to proceed
- **Dependency chain breaks:** Wave 1 fails — Wave 2 dependents likely fail — user chooses attempt or skip
- **All agents in wave fail:** Systemic issue — stop, report for investigation
- **Checkpoint unresolvable:** "Skip this plan?" or "Abort phase execution?" — record partial progress in STATE.md
</failure_handling>

<resumption>
Re-run gsd-execute-phase skill — discover_plans finds completed SUMMARYs — skips them — resumes from first incomplete plan — continues wave execution.

STATE.md tracks: last completed plan, current wave, pending checkpoints.
</resumption>
