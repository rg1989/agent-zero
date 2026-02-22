---
name: gsd-progress
description: Check project progress, show context, and route to next action (execute or plan)
allowed-tools:
  - code_execution_tool
---

<objective>
Check project progress, summarize recent work and what's ahead, then intelligently route to the next action — either executing an existing plan or creating the next one. Provides situational awareness before continuing work.
</objective>

<process>

### Step 1: Initialize Context

Load progress context by reading the planning directory:
- Check if `.planning/` exists — if not, suggest using `gsd-new-project`
- Check for STATE.md, ROADMAP.md, PROJECT.md
- Extract: project_exists, roadmap_exists, state_exists, current_phase, next_phase

If no `.planning/` directory:
```
No planning structure found. Use the `gsd-new-project` skill to start a new project.
```
Exit.

If STATE.md missing: suggest using `gsd-new-project`.

If ROADMAP.md missing but PROJECT.md exists: This means a milestone was completed and archived. Go to Route F (between milestones).

If both missing: suggest `gsd-new-project`.

### Step 2: Load Project Data

Read the following files for structured data:
- `.planning/ROADMAP.md` — all phases, their goals, and disk status
- `.planning/STATE.md` — current position, decisions, blockers, session continuity
- `.planning/PROJECT.md` — project description and core value

From ROADMAP.md, determine for each phase:
- Disk status: complete (has all summaries) / partial (some summaries) / planned (has plans, no summaries) / empty (directory only) / no_directory
- Goal and dependencies per phase
- Plan and summary counts

### Step 3: Gather Recent Work Context

Find the 2-3 most recent SUMMARY.md files by looking at modification dates in `.planning/phases/`. For each, read the one-liner from the file's first paragraph or frontmatter to show "what we've been working on".

### Step 4: Parse Current Position

From STATE.md, extract:
- Current Phase: X of Y
- Current Plan: A of B
- Status
- Paused at (if work was paused)
- Key decisions made
- Blockers/concerns
- Pending todos count

### Step 5: Generate Progress Report

Present a rich status report:

```
# [Project Name]

**Progress:** [progress bar from phase counts, e.g. [████░░░░░░] 40%]
**Profile:** [quality/balanced/budget from config]

## Recent Work
- [Phase X, Plan Y]: [what was accomplished - 1 line]
- [Phase X, Plan Z]: [what was accomplished - 1 line]

## Current Position
Phase [N] of [total]: [phase-name]
Plan [M] of [phase-total]: [status]
CONTEXT: [exists / not gathered]

## Key Decisions Made
- [decision 1]
- [decision 2]

## Blockers/Concerns
- [blocker 1] (or "None")

## Pending Todos
- [count] pending

## Active Debug Sessions
- [count] active (only show if count > 0)

## What's Next
[Next phase/plan objective from roadmap]
```

### Step 6: Route to Next Action

Determine next action based on verified file counts.

**Step 6a: Count plans, summaries, and UAT files in current phase**

List files in the current phase directory:
- Count *-PLAN.md files
- Count *-SUMMARY.md files
- Count *-UAT.md files

State: "This phase has {X} plans, {Y} summaries."

**Step 6b: Check for unaddressed UAT gaps**

Check for UAT.md files with status "diagnosed" (has gaps needing fixes):
- Look for `status: diagnosed` in any UAT.md in the current phase directory

Track: uat_with_gaps = count of UAT.md files with status "diagnosed"

**Step 6c: Route based on counts**

| Condition | Meaning | Action |
|-----------|---------|--------|
| uat_with_gaps > 0 | UAT gaps need fix plans | Go to Route E |
| summaries < plans | Unexecuted plans exist | Go to Route A |
| summaries = plans AND plans > 0 | Phase complete | Go to Step 6d |
| plans = 0 | Phase not yet planned | Go to Route B |

**Route A: Unexecuted plan exists**

Find the first PLAN.md without matching SUMMARY.md. Read its objective section.

```
## Next Up

**{phase}-{plan}: [Plan Name]** — [objective summary]

Use the `gsd-execute-phase` skill for phase {phase}
```

**Route B: Phase needs planning**

Check if `{padded_phase}-CONTEXT.md` exists in the phase directory.

If CONTEXT.md exists:
```
## Next Up

**Phase {N}: {Name}** — {Goal from ROADMAP.md}
Context gathered, ready to plan

Use the `gsd-plan-phase` skill for phase {N}
```

If CONTEXT.md does NOT exist:
```
## Next Up

**Phase {N}: {Name}** — {Goal from ROADMAP.md}

Use the `gsd-discuss-phase` skill for phase {N} — gather context and clarify approach

Also available:
- Use `gsd-plan-phase` directly — skip discussion, plan directly
```

**Route E: UAT gaps need fix plans**

UAT.md exists with gaps (diagnosed issues).

```
## UAT Gaps Found

**{phase_num}-UAT.md** has {N} gaps requiring fixes.

Use the `gsd-plan-phase` skill with --gaps flag for phase {phase}

Also available:
- Use `gsd-execute-phase` — execute phase plans
- Use `gsd-verify-work` — run more UAT testing
```



**Step 6d: Check milestone status (only when phase complete)**

Read ROADMAP.md and identify: current phase number and all phase numbers in the current milestone section.

Count total phases and identify the highest phase number.

**Route based on milestone status:**

| Condition | Meaning | Action |
|-----------|---------|--------|
| current phase < highest phase | More phases remain | Go to Route C |
| current phase = highest phase | Milestone complete | Go to Route D |



**Route C: Phase complete, more phases remain**

```
## Phase {Z} Complete

## Next Up

**Phase {Z+1}: {Name}** — {Goal from ROADMAP.md}

Use the `gsd-discuss-phase` skill for phase {Z+1} — gather context and clarify approach

Also available:
- Use `gsd-plan-phase` — skip discussion, plan directly
- Use `gsd-verify-work` for phase {Z} — user acceptance test before continuing
```



**Route D: Milestone complete**

```
## Milestone Complete

All {N} phases finished!

## Next Up

**Complete Milestone** — archive and prepare for next

Use the `gsd-complete-milestone` skill

Also available:
- Use `gsd-verify-work` — user acceptance test before completing milestone
```



**Route F: Between milestones (ROADMAP.md missing, PROJECT.md exists)**

Read MILESTONES.md to find the last completed milestone version.

```
## Milestone v{X.Y} Complete

Ready to plan the next milestone.

## Next Up

**Start Next Milestone** — questioning → research → requirements → roadmap

Use the `gsd-new-milestone` skill
```



**Edge cases:**

- Phase complete but next phase not planned → offer `gsd-plan-phase` for next phase
- All work complete → offer milestone completion
- Blockers present → highlight before offering to continue
- Handoff file exists → mention it, offer `gsd-resume-work`

</process>

<success_criteria>
- [ ] Rich context provided (recent work, decisions, issues)
- [ ] Current position clear with visual progress
- [ ] What's next clearly explained
- [ ] Smart routing: gsd-execute-phase if plans exist, gsd-plan-phase if not
- [ ] User confirms before any action
- [ ] Seamless handoff to appropriate gsd skill
</success_criteria>
