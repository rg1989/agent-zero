---
name: gsd-discuss-phase
description: Gather phase context through adaptive questioning before planning
allowed-tools:
  - code_execution_tool
  - input
  - call_subordinate
---

<objective>
Extract implementation decisions that downstream agents need — researcher and planner will use CONTEXT.md to know what to investigate and what choices are locked.

How it works:
1. Analyze the phase to identify gray areas (UI, UX, behavior, etc.)
2. Present gray areas — user selects which to discuss
3. Deep-dive each selected area until satisfied
4. Create CONTEXT.md with decisions that guide research and planning

Output: {phase_num}-CONTEXT.md — decisions clear enough that downstream agents can act without asking the user again
</objective>

<downstream_awareness>
CONTEXT.md feeds into:

1. gsd-phase-researcher — Reads CONTEXT.md to know WHAT to research
   - "User wants card-based layout" → researcher investigates card component patterns
   - "Infinite scroll decided" → researcher looks into virtualization libraries

2. gsd-planner — Reads CONTEXT.md to know WHAT decisions are locked
   - "Pull-to-refresh on mobile" → planner includes that in task specs
   - "Claude's Discretion: loading skeleton" → planner can decide approach

Your job: Capture decisions clearly enough that downstream agents can act on them without asking the user again.
Not your job: Figure out HOW to implement. That's what research and planning do with the decisions you capture.
</downstream_awareness>

<philosophy>
User = founder/visionary. Agent = builder.

The user knows: How they imagine it working, what it should look/feel like, what's essential vs nice-to-have, specific behaviors or references they have in mind.

The user doesn't know (and shouldn't be asked): Codebase patterns, technical risks, implementation approach, success metrics.

Ask about vision and implementation choices. Capture decisions for downstream agents.
</philosophy>

<scope_guardrail>
CRITICAL: No scope creep.

The phase boundary comes from ROADMAP.md and is FIXED. Discussion clarifies HOW to implement what's scoped, never WHETHER to add new capabilities.

Allowed (clarifying ambiguity):
- "How should posts be displayed?" (layout, density, info shown)
- "What happens on empty state?" (within the feature)

Not allowed (scope creep):
- "Should we also add comments?" (new capability)
- "What about search/filtering?" (new capability)

The heuristic: Does this clarify how we implement what's already in the phase, or does it add a new capability?

When user suggests scope creep, say: "[Feature X] would be a new capability — that's its own phase. Want me to note it for the roadmap backlog? For now, let's focus on [phase domain]."

Capture the idea in a "Deferred Ideas" section. Don't lose it, don't act on it.
</scope_guardrail>

<gray_area_identification>
Gray areas are implementation decisions the user cares about — things that could go multiple ways and would change the result.

How to identify gray areas:
1. Read the phase goal from ROADMAP.md
2. Understand the domain:
   - Something users SEE → visual presentation, interactions, states matter
   - Something users CALL → interface contracts, responses, errors matter
   - Something users RUN → invocation, output, behavior modes matter
   - Something users READ → structure, tone, depth, flow matter
   - Something being ORGANIZED → criteria, grouping, handling exceptions matter
3. Generate phase-specific gray areas — concrete decisions for THIS phase, not generic categories

Examples:
```
Phase: "User authentication"
→ Session handling, Error responses, Multi-device policy, Recovery flow

Phase: "Organize photo library"
→ Grouping criteria, Duplicate handling, Naming convention, Folder structure

Phase: "CLI for database backups"
→ Output format, Flag design, Progress reporting, Error recovery
```

The key question: What decisions would change the outcome that the user should weigh in on?

Agent handles these (don't ask): Technical implementation details, architecture patterns, performance optimization, scope.
</gray_area_identification>

<process>

### Step 1: Initialize

Require a phase number from the user. If not provided, ask for it.

Load the phase context: read `.planning/ROADMAP.md` to identify the phase directory, name, and goal. Check for existing RESEARCH.md, CONTEXT.md, and PLAN.md files in the phase directory.

Extract: phase_found, phase_dir, phase_number, phase_name, phase_slug, padded_phase, has_research, has_context, has_plans, plan_count.

If phase_found is false:
```
Phase [X] not found in roadmap. Use the `gsd-progress` skill to see available phases.
```
Exit.

If phase_found is true: Continue to Step 2.

### Step 2: Check Existing Context

If CONTEXT.md already exists:

Ask the user:
- "Update it" — Review and revise existing context
- "View it" — Show me what's there
- "Skip" — Use existing context as-is

If "Update": Load existing, continue to Step 3.
If "View": Display CONTEXT.md, then offer update/skip.
If "Skip": Exit.

If CONTEXT.md does not exist and plans exist:

Ask the user:
- "Continue and replan after" — Capture context, then use `gsd-plan-phase` to replan
- "View existing plans" — Show plans before deciding
- "Cancel" — Skip this skill

If "Continue and replan after": Continue to Step 3.
If "View existing plans": Display plan files, then offer "Continue" / "Cancel".
If "Cancel": Exit.

If neither context nor plans exist: Continue to Step 3.

### Step 3: Analyze Phase

Read the phase description from ROADMAP.md and determine:

1. Domain boundary — What capability is this phase delivering? State it clearly.
2. Gray areas — For each relevant category, identify 1-2 specific ambiguities that would change implementation.
3. Skip assessment — If no meaningful gray areas exist, note this.

Example analysis for "Post Feed" phase:
```
Domain: Displaying posts from followed users
Gray areas:
- Layout style (cards vs timeline vs grid)
- Loading pattern (infinite scroll vs pagination)
- Empty state (what shows when no posts exist)
- Post metadata (time, author, reactions count)
```

### Step 4: Present Gray Areas

Present the domain boundary and gray areas to user.

First state the boundary:
```
Phase [X]: [Name]
Domain: [What this phase delivers]

We'll clarify HOW to implement this.
(New capabilities belong in other phases.)
```

Then ask the user which areas to discuss (multi-select). Generate 3-4 phase-specific gray areas as concrete options with brief descriptions.

Do NOT include a "skip" or "you decide" option.

### Step 5: Discuss Areas

For each selected area, conduct a focused discussion loop.

Philosophy: 4 questions per area, then check.

For each area:
1. Announce: "Let's talk about [Area]."
2. Ask 4 questions, each with 2-3 concrete choices. Include "You decide" as an option when reasonable.
3. After 4 questions, ask: "More questions about [area], or move to next?"
   - "More questions" → ask 4 more, then check again
   - "Next area" → proceed to next selected area
4. After all areas: "That covers [list areas]. Ready to create context?"
   - Options: "Create context" / "Revisit an area"

Question design: Options should be concrete, not abstract ("Cards" not "Option A").

Scope creep handling: If user mentions something outside the phase domain, say:
"[Feature] sounds like a new capability — that belongs in its own phase. I'll note it as a deferred idea. Back to [current area]: [return to current question]"

Track deferred ideas internally.

### Step 6: Write CONTEXT.md

Note on output structure: The CONTEXT.md captures decisions for downstream agents using this structure: Phase Boundary (scope anchor), Implementation Decisions (one section per discussed area with specific decisions), Specific Ideas (references, examples, "I want it like X" moments), and Deferred Ideas (out-of-scope ideas captured for later). Categories are NOT predefined — they emerge from what was actually discussed.

Find or create phase directory: if `phase_dir` is null (phase in roadmap but no directory), create `.planning/phases/{padded_phase}-{phase_slug}`.

File location: `{phase_dir}/{padded_phase}-CONTEXT.md`

Write the file with this structure:
```
# Phase [X]: [Name] - Context

**Gathered:** [date]
**Status:** Ready for planning

<domain>
## Phase Boundary
[What this phase delivers from ROADMAP.md]
</domain>

<decisions>
## Implementation Decisions

### [Area 1 that was discussed]
- [Decision captured]

### [Area N that was discussed]
- [Decision captured]

### Claude's Discretion
[Areas where user said "you decide"]
</decisions>

<specifics>
## Specific Ideas
[References, examples, "I want it like X" moments — or "No specific requirements"]
</specifics>

<deferred>
## Deferred Ideas
[Ideas that came up but belong in other phases — or "None"]
</deferred>

* * *
*Phase: {padded_phase}-{phase_slug}*
*Context gathered: [date]*
```

### Step 7: Confirm Creation

Present summary and next steps:

```
Created: .planning/phases/{padded_phase}-{phase_slug}/{padded_phase}-CONTEXT.md

## Decisions Captured

### [Category]
- [Key decision]

## Next Up

**Phase {PHASE}: [Name]** — [Goal from ROADMAP.md]

Use the `gsd-plan-phase` skill

Also available: Use `gsd-plan-phase` with --skip-research to plan without research
```

### Step 8: Commit and Update State

If docs are being committed, commit the CONTEXT.md file with message: `docs({padded_phase}): capture phase context`.

Update the planning state to record: phase context gathered, path to the CONTEXT.md file.

### Step 9: Auto-Advance Check

Check if the user provided an `--auto` flag or if auto-advance is enabled in `.planning/config.json` (key `workflow.auto_advance`).

If auto-advance is enabled:

Display:
```
GSD - AUTO-ADVANCING TO PLAN

Context captured. Spawning plan-phase...
```

Use `call_subordinate` to delegate to a planning agent:
- **message**: Include the full role identity of a planning specialist, the phase number, that context has been gathered, and to run the gsd-plan-phase workflow for this phase
- **reset**: `"true"` for a new task

Handle return:
- PLANNING COMPLETE → plan-phase handles chaining to execute-phase via its own auto-advance
- PLANNING INCONCLUSIVE / CHECKPOINT → Display result, stop chain with message:
  "Auto-advance stopped: Planning needs input. Use the `gsd-plan-phase` skill to continue manually."

If auto-advance is NOT enabled: Show manual next steps from Step 7.

</process>

<success_criteria>
- Phase validated against roadmap
- Gray areas identified through intelligent analysis (not generic questions)
- User selected which areas to discuss
- Each selected area explored until user satisfied
- Scope creep redirected to deferred ideas
- CONTEXT.md captures actual decisions, not vague vision
- Deferred ideas preserved for future phases
- State updated with session info
- User knows next steps
</success_criteria>
