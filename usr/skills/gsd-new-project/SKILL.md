---
name: gsd-new-project
description: Initialize a new project with deep context gathering, research, requirements definition, and roadmap creation
allowed-tools:
  - code_execution_tool
  - call_subordinate
  - input
---

<objective>
Initialize a new project through a unified flow: questioning, research (optional), requirements definition, and roadmap creation. This is the most leveraged moment in any project — deep questioning here means better plans, better execution, and better outcomes.

**Creates:**
- `.planning/PROJECT.md` — project context
- `.planning/config.json` — workflow preferences
- `.planning/research/` — domain research (optional)
- `.planning/REQUIREMENTS.md` — scoped requirements
- `.planning/ROADMAP.md` — phase structure
- `.planning/STATE.md` — project memory

**After this skill:** Use the `gsd-plan-phase` skill to start planning Phase 1.
</objective>

<context_notes>
**Questioning technique:** Use structured questioning: ask one question at a time, start broad and move to specifics, follow threads that open up, surface assumptions, challenge vagueness, make abstract ideas concrete, find edges. Confirm understanding before proceeding to the next stage.

**Output formatting:** For all output, follow professional markdown conventions: clear headers, concise descriptions, avoid excessive emoji. Use `━` banners for stage transitions.

**PROJECT.md template:** Sections include: Project Name, Core Value, Tech Stack, Key Decisions (table), Current State, and Requirements (Validated / Active / Out of Scope with checkboxes).

**REQUIREMENTS.md template:** Defines v1 requirements with IDs in `[CATEGORY]-[NUMBER]` format (e.g., AUTH-01), grouped by category, with v2 deferred requirements, out-of-scope exclusions, and a traceability table.

**Auto mode:** If `--auto` flag is provided by the user (detected in the initial prompt), skip brownfield mapping and deep questioning. Extract project context from the provided idea document. Config questions are asked first (Step 2a). Research, requirements, and roadmap are created automatically with smart defaults. Auto-advance to `gsd-discuss-phase` after completion.
</context_notes>

<process>

## New Project Flow

The new-project skill operates in 9 sequential steps:

1. **Setup** — Initialize context, check if project exists, check git status
2. **Brownfield Offer** — Detect existing code; offer codebase mapping if needed
3. **Deep Questioning** — Multi-round conversation to understand the project vision
4. **Write PROJECT.md** — Synthesize all context into the project document
5. **Workflow Preferences** — Collect config settings (mode, depth, agents, models)
6. **Research Decision** — Offer domain research before defining requirements
7. **Define Requirements** — Scope v1 requirements by category with REQ-IDs
8. **Create Roadmap** — Spawn roadmapper to create phase structure
9. **Done** — Present summary and next steps

See `rules/workflow.md` for the complete step-by-step workflow.

## call_subordinate Pattern

This skill spawns multiple subagents during execution:

### Spawn gsd-project-researcher Subagents (Step 6 — Research)

Use `call_subordinate` to spawn 4 parallel project researchers (if research selected):
- **message**: Include the researcher's full role identity as a GSD project researcher agent. Include: research type (Stack/Features/Architecture/Pitfalls), milestone context (greenfield or subsequent), the research question for this dimension, path to PROJECT.md for context, and expected output location (`.planning/research/STACK.md`, `FEATURES.md`, `ARCHITECTURE.md`, or `PITFALLS.md`)
- **reset**: `"true"` for each new researcher session

After all 4 researchers complete, spawn a research synthesizer:
- **message**: Include the synthesizer's full role identity, paths to all 4 research files, and output location (`.planning/research/SUMMARY.md`)
- **reset**: `"true"`

### Spawn gsd-roadmapper Subagent (Step 8 — Roadmap)

Use `call_subordinate` to create the roadmap:
- **message**: Include the roadmapper's full role identity as a GSD roadmapper agent. Include: paths to PROJECT.md, REQUIREMENTS.md, research SUMMARY.md (if exists), and config.json. Instructions: derive phases from requirements, map every v1 requirement to exactly one phase, derive 2-5 success criteria per phase, validate 100% coverage, write ROADMAP.md, STATE.md, update REQUIREMENTS.md traceability, return `## ROADMAP CREATED` or `## ROADMAP BLOCKED`
- **reset**: `"true"`

**Handle roadmapper return:**
- `## ROADMAP CREATED` — Read and present the roadmap, get user approval (unless auto mode), commit
- `## ROADMAP BLOCKED` — Present blocker, work with user to resolve, re-spawn when resolved

For roadmap revisions, re-spawn with revision context:
- **message**: Include roadmapper role, path to existing ROADMAP.md, user feedback notes. Instruct: update roadmap in place, return `## ROADMAP REVISED`
- **reset**: `"true"`

## Reference Files

Detailed step-by-step workflow is in this skill's directory:
- `rules/workflow.md` — complete new-project workflow (Steps 1-9 with all substeps, prompts, and gates)

</process>

<success_criteria>
- [ ] `.planning/` directory created
- [ ] Git repo initialized (if not already)
- [ ] Brownfield detection completed
- [ ] Deep questioning completed (threads followed, not rushed) OR auto mode extracted from document
- [ ] PROJECT.md captures full project context — committed
- [ ] config.json has workflow mode, depth, parallelization, model profile — committed
- [ ] Research completed if selected (4 parallel researcher agents spawned, synthesizer run) — committed
- [ ] Requirements gathered and scoped (v1/v2/out of scope per category)
- [ ] REQUIREMENTS.md created with REQ-IDs — committed
- [ ] gsd-roadmapper spawned with full context
- [ ] ROADMAP.md created with phases, requirement mappings, success criteria
- [ ] STATE.md initialized
- [ ] REQUIREMENTS.md traceability updated
- [ ] User knows next step is to use the `gsd-discuss-phase` skill for Phase 1

**Atomic commits:** Each stage commits its artifacts immediately. If context is lost mid-flow, artifacts persist.
</success_criteria>
