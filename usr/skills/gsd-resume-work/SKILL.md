---
name: gsd-resume-work
description: Resume work from previous session with full context restoration
allowed-tools:
  - code_execution_tool
  - input
---

<objective>
Restore complete project context and resume work seamlessly from previous session.

Handles:
- STATE.md loading (or reconstruction if missing)
- Checkpoint detection (.continue-here files)
- Incomplete work detection (PLAN without SUMMARY)
- Status presentation
- Context-aware next action routing
</objective>

<trigger>
Use this skill when:
- Starting a new session on an existing project
- User says "continue", "what's next", "where were we", "resume"
- Any planning operation when .planning/ already exists
- User returns after time away from project
</trigger>

<process>

### Step 1: Initialize

Load all context by reading the planning directory:

```bash
ls .planning/ 2>/dev/null
```

Parse: state_exists, roadmap_exists, project_exists, planning_exists.

Also check for any interrupted agent sessions by looking for agent-history.json files or interrupted agent markers.

**If `state_exists` is true:** Proceed to load_state.
**If `state_exists` is false but `roadmap_exists` or `project_exists` is true:** Offer to reconstruct STATE.md.
**If `planning_exists` is false:** This is a new project — suggest using `gsd-new-project`.

### Step 2: Load State

Read and parse STATE.md, then PROJECT.md:

```bash
cat .planning/STATE.md
cat .planning/PROJECT.md
```

**From STATE.md extract:**
- Project Reference: Core value and current focus
- Current Position: Phase X of Y, Plan A of B, Status
- Progress: Visual progress bar
- Recent Decisions: Key decisions affecting current work
- Pending Todos: Ideas captured during sessions
- Blockers/Concerns: Issues carried forward
- Session Continuity: Where we left off, any resume files

**From PROJECT.md extract:**
- What This Is: Current accurate description
- Requirements: Validated, Active, Out of Scope
- Key Decisions: Full decision log with outcomes
- Constraints: Hard limits on implementation

### Step 3: Check Incomplete Work

Look for incomplete work that needs attention:

```bash
# Check for continue-here files (mid-plan resumption)
ls .planning/phases/*/.continue-here*.md 2>/dev/null

# Check for plans without summaries (incomplete execution)
for plan in .planning/phases/*/*-PLAN.md; do
  summary="${plan/PLAN/SUMMARY}"
  [ ! -f "$summary" ] && echo "Incomplete: $plan"
done 2>/dev/null
```

Also check if an interrupted agent marker exists (look for agent-history.json or similar).

**If .continue-here file exists:**
- This is a mid-plan resumption point
- Read the file for specific resumption context
- Flag: "Found mid-plan checkpoint"

**If PLAN without SUMMARY exists:**
- Execution was started but not completed
- Flag: "Found incomplete plan execution"

**If interrupted agent found:**
- Subagent was spawned but session ended before completion
- Flag: "Found interrupted agent"

### Step 4: Present Status

Present complete project status to user:

```
╔══════════════════════════════════════════════════════════════╗
║  PROJECT STATUS                                               ║
╠══════════════════════════════════════════════════════════════╣
║  Building: [one-liner from PROJECT.md]                        ║
║                                                               ║
║  Phase: [X] of [Y] - [Phase name]                            ║
║  Plan:  [A] of [B] - [Status]                                ║
║  Progress: [progress bar] XX%                                ║
║                                                               ║
║  Last activity: [date] - [what happened]                     ║
╚══════════════════════════════════════════════════════════════╝

[If incomplete work found:]
Incomplete work detected:
    - [.continue-here file or incomplete plan]

[If interrupted agent found:]
Interrupted agent detected: [task description, timestamp]
    Resume with: call_subordinate with reset: "false" and the agent ID

[If pending todos exist:]
[N] pending todos

[If blockers exist:]
Carried concerns:
    - [blocker 1]
```

### Step 5: Determine Next Action

Based on project state, determine the most logical next action:

**If interrupted agent exists:**
→ Primary: Resume interrupted agent (call_subordinate with reset: "false")
→ Option: Start fresh (abandon agent work)

**If .continue-here file exists:**
→ Primary: Resume from checkpoint
→ Option: Start fresh on current plan

**If incomplete plan (PLAN without SUMMARY):**
→ Primary: Complete the incomplete plan
→ Option: Abandon and move on

**If phase in progress, all plans complete:**
→ Primary: Transition to next phase
→ Option: Review completed work

**If phase ready to plan:**
→ Check if CONTEXT.md exists for this phase:
- If CONTEXT.md missing:
  → Primary: Discuss phase vision (how user imagines it working)
  → Secondary: Plan directly (skip context gathering)
- If CONTEXT.md exists:
  → Primary: Plan the phase
  → Option: Review roadmap

**If phase ready to execute:**
→ Primary: Execute next plan
→ Option: Review the plan first

### Step 6: Offer Options

Present contextual options based on project state:

```
What would you like to do?

[Primary action based on state — e.g.:]
1. Use the `gsd-execute-phase` skill for phase {phase}
   OR
1. Use the `gsd-discuss-phase` skill for phase {N} [if CONTEXT.md missing]
   OR
1. Use the `gsd-plan-phase` skill for phase {N} [if CONTEXT.md exists]

[Secondary options:]
2. Review current phase status
3. Check pending todos
4. Something else
```

When offering phase planning, check for CONTEXT.md existence:

```bash
ls .planning/phases/XX-name/*-CONTEXT.md 2>/dev/null
```

If missing, suggest discuss-phase before plan. If exists, offer plan directly.

Wait for user selection.

### Step 7: Route to Workflow

Based on user selection, route to appropriate skill:

- **Execute plan:**
  ```
  ## Next Up

  **{phase}-{plan}: [Plan Name]** — [objective from PLAN.md]

  Use the `gsd-execute-phase` skill for phase {phase}
  ```

- **Plan phase:**
  ```
  ## Next Up

  **Phase [N]: [Name]** — [Goal from ROADMAP.md]

  Use the `gsd-plan-phase` skill for phase [N]

  Also available:
  - Use `gsd-discuss-phase` — gather context first
  ```

- **Check todos:** Read `.planning/todos/pending/`, present summary.
- **Review alignment:** Read PROJECT.md, compare to current state.
- **Something else:** Ask what they need.

### Step 8: Update Session

Before proceeding to routed workflow, update session continuity in STATE.md:

```markdown
## Session Continuity

Last session: [now]
Stopped at: Session resumed, proceeding to [action]
Resume file: [updated if applicable]
```

This ensures if session ends unexpectedly, next resume knows the state.

</process>

<reconstruction>
If STATE.md is missing but other artifacts exist:

"STATE.md missing. Reconstructing from artifacts..."

1. Read PROJECT.md → Extract "What This Is" and Core Value
2. Read ROADMAP.md → Determine phases, find current position
3. Scan *-SUMMARY.md files → Extract decisions, concerns
4. Count pending todos in .planning/todos/pending/
5. Check for .continue-here files → Session continuity

Reconstruct and write STATE.md, then proceed normally.

This handles cases where:
- Project predates STATE.md introduction
- File was accidentally deleted
- Cloning repo without full .planning/ state
</reconstruction>

<quick_resume>
If user says "continue" or "go":
- Load state silently
- Determine primary action
- Execute immediately without presenting options

"Continuing from [state]... [action]"
</quick_resume>

<success_criteria>
Resume is complete when:

- [ ] STATE.md loaded (or reconstructed)
- [ ] Incomplete work detected and flagged
- [ ] Clear status presented to user
- [ ] Contextual next actions offered
- [ ] User knows exactly where project stands
- [ ] Session continuity updated
</success_criteria>
