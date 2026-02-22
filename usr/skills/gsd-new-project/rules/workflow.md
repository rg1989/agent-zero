# gsd-new-project: Complete Workflow

Full step-by-step workflow for the new-project skill. Read and follow this from start to finish.

* * *

## Step 1: Setup

**MANDATORY FIRST STEP — Execute these checks before ANY user interaction:**

Load initialization context by reading `.planning/config.json` (if exists), checking for `.planning/` directory existence, detecting whether existing code is present in the working directory, and checking if git is initialized.

Parse context for: project already exists (has `.planning/ROADMAP.md`), has existing code, is brownfield, has git, project path.

**If project already exists:** Error — project already initialized. Use the `gsd-progress` skill instead.

**If git not initialized:**
```bash
git init
```

* * *

## Step 2: Brownfield Offer

**If auto mode:** Skip to Step 4 (assume greenfield, synthesize PROJECT.md from provided document).

**If existing code detected but no codebase map (`.planning/codebase/` doesn't exist):**

Use `input` to ask:
- header: "Codebase"
- question: "I detected existing code in this directory. Would you like to map the codebase first?"
- options:
  - "Map codebase first" — Run the `gsd-map-codebase` skill to understand existing architecture (Recommended)
  - "Skip mapping" — Proceed with project initialization

**If "Map codebase first":** Instruct user to run the `gsd-map-codebase` skill first, then return. Exit.

**If "Skip mapping" OR no existing code detected:** Continue to Step 3.

* * *

## Step 2a: Auto Mode Config (auto mode only)

**If auto mode:** Collect config settings upfront before processing the idea document.

YOLO mode is implicit in auto mode. Ask remaining config questions using `input`:

**Round 1 — Core settings:**
- Depth: Quick (Recommended) / Standard / Comprehensive
- Execution: Parallel (Recommended) / Sequential
- Git Tracking: Yes (Recommended) / No

**Round 2 — Workflow agents:**
- Research: Yes (Recommended) / No
- Plan Check: Yes (Recommended) / No
- Verifier: Yes (Recommended) / No
- AI Models: Balanced (Recommended) / Quality / Budget

Create `.planning/config.json`:

```json
{
  "mode": "yolo",
  "depth": "[selected]",
  "parallelization": true,
  "commit_docs": true,
  "model_profile": "balanced",
  "workflow": {
    "research": true,
    "plan_check": true,
    "verifier": true,
    "auto_advance": true
  }
}
```

**If commit_docs = No:** Add `.planning/` to `.gitignore`.

Create directory and commit:
```bash
mkdir -p .planning
git add .planning/config.json
git commit -m "chore: add project config"
```

Persist auto-advance by writing `workflow.auto_advance: true` to config.json.

Proceed to Step 4 (skip Steps 3 and 5).

* * *

## Step 3: Deep Questioning

**If auto mode:** Skip. Extract project context from provided document and proceed to Step 4.

**Display stage banner:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GSD ► QUESTIONING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Open the conversation (freeform, NOT structured input):**

Ask: "What do you want to build?"

Wait for their response. This gives you the context needed to ask intelligent follow-up questions.

**Follow the thread:** Based on what they said, ask follow-up questions that dig into their response. Use structured input with options that probe what they mentioned — interpretations, clarifications, concrete examples.

Keep following threads. Each answer opens new threads to explore. Ask about:
- What excited them
- What problem sparked this
- What they mean by vague terms
- What it would actually look like
- What's already decided

**Questioning techniques:**
- Challenge vagueness: "What does that mean exactly?"
- Make abstract concrete: "Can you give me an example of what that would look like?"
- Surface assumptions: "Are you assuming users will do X?"
- Find edges: "What happens when a user does Y?"
- Reveal motivation: "Why is this the right solution to that problem?"

**Context checklist (background — don't ask mechanically):**
- What problem are they solving?
- Who are the users?
- What does "done" look like?
- What constraints exist (tech, budget, timeline)?
- What's in scope for v1? What's explicitly out?
- What have they already decided?
- What's the core value proposition?

**Decision gate:**

When you could write a clear PROJECT.md, use `input`:
- header: "Ready?"
- question: "I think I understand what you're after. Ready to create PROJECT.md?"
- options:
  - "Create PROJECT.md" — Let's move forward
  - "Keep exploring" — I want to share more / ask me more

If "Keep exploring": ask what they want to add, or identify gaps and probe naturally.

Loop until "Create PROJECT.md" selected.

* * *

## Step 4: Write PROJECT.md

**If auto mode:** Synthesize from provided document. No "Ready?" gate needed — proceed directly to commit.

Synthesize all context into `.planning/PROJECT.md`.

**Structure:**
```markdown
# [Project Name]

**Core value:** [The ONE thing this project must do well]

## What We're Building

[2-3 sentences describing the product and who it's for]

## Tech Stack

[Only include if decided during questioning]

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| [Choice from questioning] | [Why] | — Pending |

## Requirements

### Validated
(None yet — ship to validate)

### Active
- [ ] [Requirement 1]
- [ ] [Requirement 2]

### Out of Scope
- [Exclusion 1] — [why]

---
*Last updated: [date] after initialization*
```

**For brownfield projects (codebase map exists):**

Read `.planning/codebase/ARCHITECTURE.md` and `STACK.md` if they exist. Infer Validated requirements from what the codebase already does.

**Do not compress. Capture everything gathered during questioning.**

Create directory and commit:
```bash
mkdir -p .planning
git add .planning/PROJECT.md
git commit -m "docs: initialize project"
```

* * *

## Step 5: Workflow Preferences

**If auto mode:** Skip — config was collected in Step 2a. Proceed to Step 5.5.

**Check for saved defaults** at `~/.gsd/defaults.json`. If the file exists, offer to use saved defaults:

```
input(
  question: "Use your saved default settings?",
  header: "Defaults",
  options: ["Yes (Recommended)", "No"]
)
```

If "Yes": read saved defaults, use those values for config.json, skip to **Commit config.json** below.
If "No" or no defaults file: proceed with questions.

**Round 1 — Core workflow settings:**

Use `input` with these questions:
- **Mode**: YOLO (Recommended — auto-approve, just execute) / Interactive (confirm at each step)
- **Depth**: Quick (3-5 phases, 1-3 plans) / Standard (5-8 phases, 3-5 plans) / Comprehensive (8-12 phases, 5-10 plans)
- **Execution**: Parallel (Recommended) / Sequential
- **Git Tracking**: Yes (Recommended) / No

**Round 2 — Workflow agents:**

| Agent | When it runs | What it does |
|-------|--------------|--------------|
| Researcher | Before planning each phase | Investigates domain, finds patterns, surfaces gotchas |
| Plan Checker | After plan is created | Verifies plan actually achieves the phase goal |
| Verifier | After phase execution | Confirms must-haves were delivered |

Use `input` for each:
- Research: Yes (Recommended) / No
- Plan Check: Yes (Recommended) / No
- Verifier: Yes (Recommended) / No
- AI Models: Balanced (Recommended — Sonnet) / Quality (Opus) / Budget (Haiku)

Create `.planning/config.json`:

```json
{
  "mode": "yolo|interactive",
  "depth": "quick|standard|comprehensive",
  "parallelization": true|false,
  "commit_docs": true|false,
  "model_profile": "quality|balanced|budget",
  "workflow": {
    "research": true|false,
    "plan_check": true|false,
    "verifier": true|false
  }
}
```

**If commit_docs = No:**
- Add `.planning/` to `.gitignore`

Commit config:
```bash
git add .planning/config.json
git commit -m "chore: add project config"
```

**Note:** The `gsd-settings` skill can update these preferences later.

* * *

## Step 5.5: Resolve Model Profile

Use researcher, synthesizer, and roadmapper model selections from config to guide which capability level to use when spawning subagents.

* * *

## Step 6: Research Decision

**If auto mode:** Default to "Research first" without asking.

Use `input`:
- header: "Research"
- question: "Research the domain ecosystem before defining requirements?"
- options:
  - "Research first (Recommended)" — Discover standard stacks, expected features, architecture patterns
  - "Skip research" — I know this domain well, go straight to requirements

**If "Research first":**

Display:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GSD ► RESEARCHING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Researching [domain] ecosystem...
```

Create research directory:
```bash
mkdir -p .planning/research
```

**Determine milestone context:** Greenfield (no Validated requirements yet) or Subsequent (Validated requirements exist in PROJECT.md).

Display:
```
◆ Spawning 4 researchers in parallel...
  → Stack research
  → Features research
  → Architecture research
  → Pitfalls research
```

Spawn 4 parallel gsd-project-researcher subagents via `call_subordinate`:

**Stack researcher:**
- **message**: Role identity as GSD project researcher. Research type: "Stack dimension". Milestone context (greenfield/subsequent). Question: "What's the standard 2025 stack for [domain]?" Path to PROJECT.md. Output: prescriptive library recommendations with versions and rationale. Expected output location: `.planning/research/STACK.md`
- **reset**: `"true"`

**Features researcher:**
- **message**: Role identity. Research type: "Features dimension". Question: "What features do [domain] products have? What's table stakes vs differentiating?" Path to PROJECT.md. Output: categorize features (table stakes / differentiators / anti-features). Expected output: `.planning/research/FEATURES.md`
- **reset**: `"true"`

**Architecture researcher:**
- **message**: Role identity. Research type: "Architecture dimension". Question: "How are [domain] systems typically structured?" Path to PROJECT.md. Output: component boundaries, data flow, suggested build order. Expected output: `.planning/research/ARCHITECTURE.md`
- **reset**: `"true"`

**Pitfalls researcher:**
- **message**: Role identity. Research type: "Pitfalls dimension". Question: "What do [domain] projects commonly get wrong?" Path to PROJECT.md. Output: specific pitfalls with warning signs and prevention strategies. Expected output: `.planning/research/PITFALLS.md`
- **reset**: `"true"`

After all 4 researchers complete, spawn a synthesizer via `call_subordinate`:
- **message**: Task: synthesize research outputs into SUMMARY.md. Read: `.planning/research/STACK.md`, `FEATURES.md`, `ARCHITECTURE.md`, `PITFALLS.md`. Output to: `.planning/research/SUMMARY.md`. Commit after writing.
- **reset**: `"true"`

Display completion:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GSD ► RESEARCH COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Key Findings
[Summary from SUMMARY.md]
```

**If "Skip research":** Continue to Step 7.

* * *

## Step 7: Define Requirements

Display:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GSD ► DEFINING REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Load context:** Read PROJECT.md. Extract: core value, stated constraints, explicit scope boundaries.

**If research exists:** Read `FEATURES.md` and extract feature categories.

**If auto mode:**
- Auto-include all table stakes features
- Include features explicitly mentioned in provided document
- Auto-defer differentiators not mentioned in document
- Skip per-category input loops
- Skip "Any additions?" question
- Skip requirements approval gate
- Generate REQUIREMENTS.md and commit directly

**Present features by category (interactive mode only):**

For each research category, show table stakes and differentiators, then use `input`:
- header: "[Category]"
- question: "Which [category] features are in v1?"
- multiSelect: true
- options: list each feature with brief description; include "None for v1" option

Track responses:
- Selected features → v1 requirements
- Unselected table stakes → v2 (users expect these)
- Unselected differentiators → out of scope

**If no research:** Gather requirements through conversation. Ask: "What are the main things users need to be able to do?" For each capability: ask clarifying questions, probe related capabilities, group into categories.

**Identify gaps:**

Use `input`:
- header: "Additions"
- question: "Any requirements research missed?"
- options: "No, research covered it" / "Yes, let me add some"

**Validate core value:** Cross-check requirements against Core Value from PROJECT.md. Surface gaps.

**Generate REQUIREMENTS.md:**

Create `.planning/REQUIREMENTS.md` with:
- v1 Requirements grouped by category (checkboxes, REQ-IDs in `[CATEGORY]-[NUMBER]` format)
- v2 Requirements (deferred)
- Out of Scope (explicit exclusions with reasoning)
- Traceability section (empty — filled by roadmapper)

**Requirement quality criteria:**
- Specific and testable: "User can reset password via email link" (not "Handle password reset")
- User-centric: "User can X" (not "System does Y")
- Atomic: one capability per requirement
- Independent: minimal dependencies

**Present full requirements list (interactive mode only)** for user confirmation. If adjustments needed, return to scoping.

Commit:
```bash
git add .planning/REQUIREMENTS.md
git commit -m "docs: define v1 requirements"
```

* * *

## Step 8: Create Roadmap

Display:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GSD ► CREATING ROADMAP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

◆ Spawning roadmapper...
```

Spawn gsd-roadmapper via `call_subordinate`:
- **message**: Include roadmapper role identity. Provide paths via `files_to_read`: PROJECT.md, REQUIREMENTS.md, research SUMMARY.md (if exists), config.json. Instructions: (1) derive phases from requirements, (2) map every v1 requirement to exactly one phase, (3) derive 2-5 success criteria per phase, (4) validate 100% coverage, (5) write ROADMAP.md, STATE.md, update REQUIREMENTS.md traceability, (6) return `## ROADMAP CREATED` with summary. Write files FIRST then return.
- **reset**: `"true"`

**Handle roadmapper return:**

**If `## ROADMAP BLOCKED`:**
- Present blocker information
- Work with user to resolve
- Re-spawn when resolved

**If `## ROADMAP CREATED`:**

Read the created ROADMAP.md and present inline:

```
Proposed Roadmap

[N] phases | [X] requirements mapped | All v1 requirements covered

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
...
```

**If auto mode:** Skip approval — commit directly.

**Approval gate (interactive mode only):**

Use `input`:
- header: "Roadmap"
- question: "Does this roadmap structure work for you?"
- options:
  - "Approve" — Commit and continue
  - "Adjust phases" — Tell me what to change
  - "Review full file" — Show raw ROADMAP.md

**If "Adjust phases":** Get user notes. Re-spawn roadmapper with revision context (include existing ROADMAP.md path and user feedback). After revision, present again. Loop until approved.

**If "Review full file":** Read and display ROADMAP.md, then re-ask.

**Commit (after approval or auto mode):**
```bash
git add .planning/ROADMAP.md .planning/STATE.md .planning/REQUIREMENTS.md
git commit -m "docs: create roadmap ([N] phases)"
```

* * *

## Step 9: Done

Present completion summary:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GSD ► PROJECT INITIALIZED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Project Name]

| Artifact       | Location                    |
|----------------|-----------------------------|
| Project        | .planning/PROJECT.md        |
| Config         | .planning/config.json       |
| Research       | .planning/research/         |
| Requirements   | .planning/REQUIREMENTS.md   |
| Roadmap        | .planning/ROADMAP.md        |

[N] phases | [X] requirements | Ready to build
```

**If auto mode:**

Display:
```
AUTO-ADVANCING → DISCUSS PHASE 1
```

Use the `gsd-discuss-phase` skill for Phase 1 in auto mode.

**If interactive mode:**

```
Next Up

Phase 1: [Phase Name] — [Goal from ROADMAP.md]

Use the gsd-discuss-phase skill for Phase 1 to gather context and clarify approach.

Also available:
- gsd-plan-phase for Phase 1 — skip discussion, plan directly
```
