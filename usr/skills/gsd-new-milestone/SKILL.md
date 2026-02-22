---
name: gsd-new-milestone
description: Start a new milestone cycle — update PROJECT.md and route to requirements
allowed-tools:
  - code_execution_tool
  - input
  - call_subordinate
---

<objective>
Start a new milestone: questioning → research (optional) → requirements → roadmap.

Brownfield equivalent of gsd-new-project. Project exists, PROJECT.md has history. Gathers "what's next", updates PROJECT.md, then runs requirements → roadmap cycle.

Creates/Updates:
- `.planning/PROJECT.md` — updated with new milestone goals
- `.planning/research/` — domain research (optional, NEW features only)
- `.planning/REQUIREMENTS.md` — scoped requirements for this milestone
- `.planning/ROADMAP.md` — phase structure (continues numbering)
- `.planning/STATE.md` — reset for new milestone

After: Use the `gsd-plan-phase` skill to start execution.
</objective>

<process>

## 1. Load Context

- Read PROJECT.md (existing project, validated requirements, decisions)
- Read MILESTONES.md (what shipped previously)
- Read STATE.md (pending todos, blockers)
- Check for MILESTONE-CONTEXT.md (from gsd-discuss-phase if available)

## 2. Gather Milestone Goals

**If MILESTONE-CONTEXT.md exists:**
- Use features and scope from discuss-milestone
- Present summary for confirmation

**If no context file:**
- Present what shipped in last milestone
- Ask: "What do you want to build next?"
- Use `input` to explore features, priorities, constraints, scope

## 3. Determine Milestone Version

- Parse last version from MILESTONES.md
- Suggest next version (v1.0 → v1.1, or v2.0 for major)
- Confirm with user

## 4. Update PROJECT.md

Add/update:

```markdown
## Current Milestone: v[X.Y] [Name]

**Goal:** [One sentence describing milestone focus]

**Target features:**
- [Feature 1]
- [Feature 2]
```

Update Active requirements section and "Last updated" footer.

## 5. Update STATE.md

```markdown
## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: [today] — Milestone v[X.Y] started
```

Keep Accumulated Context section from previous milestone.

## 6. Cleanup and Commit

Delete MILESTONE-CONTEXT.md if exists (consumed).

Commit: `docs: start milestone v[X.Y] [Name]` — include PROJECT.md and STATE.md.

## 7. Research Decision

Ask the user: "Research the domain ecosystem for new features before defining requirements?"
- "Research first (Recommended)" — Discover patterns, features, architecture for NEW capabilities
- "Skip research" — Go straight to requirements

Persist the choice to config: write `workflow.research: true/false` to `.planning/config.json`.

**If "Research first":**

Display:
```
GSD - RESEARCHING

Spawning 4 researchers in parallel...
Stack, Features, Architecture, Pitfalls
```

Create `.planning/research/` directory if needed.

Spawn 4 parallel research agents using `call_subordinate`. Each agent is a project researcher focusing on one dimension:

**Stack researcher:**
- **message**: Include full role identity as a project researcher specializing in technology stack. The project is a subsequent milestone adding [target features] to an existing app. Provide the existing context from PROJECT.md. Ask: What stack additions/changes are needed for the new features? Write findings to `.planning/research/STACK.md`. Focus on versions current as of today, rationale, and integration with existing stack.
- **reset**: `"true"`

**Features researcher:**
- **message**: Include full role identity as a project researcher specializing in feature analysis. The project is adding [target features] to an existing app. Provide existing features already built. Ask: How do the target features typically work? What are table stakes vs differentiators? Write to `.planning/research/FEATURES.md`. Note complexity and dependencies.
- **reset**: `"true"`

**Architecture researcher:**
- **message**: Include full role identity as a project researcher specializing in architecture. The project is adding [target features] to an existing system. Provide existing architecture from PROJECT.md. Ask: How do target features integrate with existing architecture? What are integration points, new components, data flow changes? Write to `.planning/research/ARCHITECTURE.md`.
- **reset**: `"true"`

**Pitfalls researcher:**
- **message**: Include full role identity as a project researcher specializing in pitfalls. Focus on common mistakes when adding these specific features to an existing system of this type. Ask: Common mistakes, warning signs, prevention strategy, which phase should address each pitfall? Write to `.planning/research/PITFALLS.md`.
- **reset**: `"true"`

After all 4 complete, spawn a research synthesizer:
- **message**: Include full role identity as a research synthesizer. Read the four research files in `.planning/research/` (STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md). Synthesize into `.planning/research/SUMMARY.md`. Include: stack additions summary, feature table stakes, key architectural decisions, top pitfalls to watch for. Commit after writing.
- **reset**: `"true"`

Display key findings from SUMMARY.md:
```
GSD - RESEARCH COMPLETE

**Stack additions:** [from SUMMARY.md]
**Feature table stakes:** [from SUMMARY.md]
**Watch Out For:** [from SUMMARY.md]
```

**If "Skip research":** Continue to Step 8.

## 8. Define Requirements

Display:
```
GSD - DEFINING REQUIREMENTS
```

Read PROJECT.md: core value, current milestone goals, validated requirements (what exists).

If research exists: Read FEATURES.md, extract feature categories.

Present features by category:
```
## [Category 1]
**Table stakes:** Feature A, Feature B
**Differentiators:** Feature C, Feature D
**Research notes:** [any relevant notes]
```

If no research: Gather requirements through conversation. Ask: "What are the main things users need to do with [new features]?" Clarify, probe for related capabilities, group into categories.

Scope each category via `input` (multi-select):
- "[Feature 1]" — [brief description]
- "[Feature 2]" — [brief description]
- "None for this milestone" — Defer entire category

Track: Selected → this milestone. Unselected table stakes → future. Unselected differentiators → out of scope.

Ask if there are gaps research didn't cover. If yes, capture additions.

**Generate REQUIREMENTS.md:**
- v1 Requirements grouped by category (checkboxes, REQ-IDs)
- Future Requirements (deferred)
- Out of Scope (explicit exclusions with reasoning)
- Traceability section (empty, filled by roadmap)

**REQ-ID format:** `[CATEGORY]-[NUMBER]` (AUTH-01, NOTIF-02). Continue numbering from existing.

**Requirement quality criteria:**
- Specific and testable: "User can reset password via email link" (not "Handle password reset")
- User-centric: "User can X" (not "System does Y")
- Atomic: One capability per requirement
- Independent: Minimal dependencies on other requirements

Present full requirements list for confirmation. If user wants adjustments, return to scoping.

Commit requirements: `docs: define milestone v[X.Y] requirements` — include REQUIREMENTS.md.

## 9. Create Roadmap

Display:
```
GSD - CREATING ROADMAP

Spawning roadmapper...
```

Find the starting phase number: read MILESTONES.md for last phase number. Continue from there (v1.0 ended at phase 5 → v1.1 starts at phase 6).

Spawn roadmapper using `call_subordinate`:
- **message**: Include full role identity as a roadmap architect. Read `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/research/SUMMARY.md` (if exists), `.planning/config.json`, and `.planning/MILESTONES.md`. Create roadmap for milestone v[X.Y]: start phase numbering from [N], derive phases from THIS MILESTONE's requirements only, map every requirement to exactly one phase, derive 2-5 success criteria per phase (observable user behaviors), validate 100% coverage, write ROADMAP.md, STATE.md, and update REQUIREMENTS.md traceability immediately. Return ROADMAP CREATED with summary.
- **reset**: `"true"`

**Handle return:**

If `## ROADMAP BLOCKED`: Present blocker, work with user, re-spawn.

If `## ROADMAP CREATED`: Read ROADMAP.md, present inline:

```
## Proposed Roadmap

**[N] phases** | **[X] requirements mapped** | All covered

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| [N] | [Name] | [Goal] | [REQ-IDs] | [count] |
```

Ask for approval:
- "Approve" — Commit and continue
- "Adjust phases" — Tell me what to change
- "Review full file" — Show raw ROADMAP.md

If "Adjust": Get notes, re-spawn roadmapper with revision context, loop until approved.
If "Review": Display raw ROADMAP.md, re-ask.

Commit roadmap after approval: `docs: create milestone v[X.Y] roadmap ([N] phases)` — include ROADMAP.md, STATE.md, REQUIREMENTS.md.

## 10. Done

Display:
```
GSD - MILESTONE INITIALIZED

**Milestone v[X.Y]: [Name]**

| Artifact       | Location                    |
|----------------|-----------------------------|
| Project        | `.planning/PROJECT.md`      |
| Research       | `.planning/research/`       |
| Requirements   | `.planning/REQUIREMENTS.md` |
| Roadmap        | `.planning/ROADMAP.md`      |

**[N] phases** | **[X] requirements** | Ready to build

## Next Up

**Phase [N]: [Phase Name]** — [Goal]

Use the `gsd-discuss-phase` skill — gather context and clarify approach

Also: Use the `gsd-plan-phase` skill — skip discussion, plan directly
```

</process>

<success_criteria>
- [ ] PROJECT.md updated with Current Milestone section
- [ ] STATE.md reset for new milestone
- [ ] MILESTONE-CONTEXT.md consumed and deleted (if existed)
- [ ] Research completed (if selected) — 4 parallel agents, milestone-aware
- [ ] Requirements gathered and scoped per category
- [ ] REQUIREMENTS.md created with REQ-IDs
- [ ] Roadmapper spawned with phase numbering context
- [ ] Roadmap files written immediately (not draft)
- [ ] User feedback incorporated (if any)
- [ ] ROADMAP.md phases continue from previous milestone
- [ ] All commits made (if planning docs committed)
- [ ] User knows next step: use `gsd-discuss-phase` or `gsd-plan-phase`

Atomic commits: Each phase commits its artifacts immediately.
</success_criteria>
