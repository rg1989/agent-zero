---
name: gsd-research-phase
description: Research how to implement a phase (standalone — usually use gsd-plan-phase instead which integrates research automatically)
allowed-tools:
  - code_execution_tool
  - call_subordinate
---

<objective>
Research how to implement a phase. Spawns gsd-phase-researcher agent with full phase context.

**Note:** This is a standalone research skill. For most workflows, use `gsd-plan-phase` instead which integrates research automatically.

**Use this skill when:**
- You want to research without planning yet
- You want to re-research after planning is complete
- You need to investigate before deciding if a phase is feasible

**Orchestrator role:** Parse the phase number provided by the user, validate against roadmap, check existing research, gather context, spawn researcher agent, present results.

**Why subagent:** Research burns context fast (web searches, source verification, documentation review). Fresh context window for investigation keeps the main context lean for user interaction.
</objective>

<context>
Phase number: provided by the user (required).

Normalize phase input before any directory lookups.
</context>

<process>

## Step 0: Initialize Context

Load phase context by reading `.planning/ROADMAP.md` to identify the phase directory, name, goal, and associated file paths. Extract: `phase_dir`, `phase_number`, `phase_name`, `phase_found`, `commit_docs`, `has_research`, `state_path`, `requirements_path`, `context_path`, `research_path`.

Select the researcher model from project configuration in `.planning/config.json` (`model_profile` field).

## Step 1: Validate Phase

Look up the phase entry in `.planning/ROADMAP.md` by phase number to get `phase_number`, `phase_name`, and `goal`.

**If phase not found:** Error and exit — list available phases from ROADMAP.md.
**If phase found:** Extract `phase_number`, `phase_name`, `goal` from the roadmap entry.

## Step 2: Check Existing Research

Check if a RESEARCH.md file exists at the phase directory path.

**If exists:** Offer:
1. Update research — re-run researcher with existing research as context
2. View existing — display the RESEARCH.md content
3. Skip — exit without changes

Wait for user response before continuing.

**If doesn't exist:** Continue directly.

## Step 3: Gather Phase Context

Use paths from initialization. Do not inline file contents in orchestrator context — pass paths to the researcher agent.

Files the researcher will load:
- `requirements_path` — project requirements
- `context_path` — phase context from gsd-discuss-phase (if exists)
- `state_path` — project decisions and history

Present summary with phase description and what files the researcher will load.

## Step 4: Spawn gsd-phase-researcher Subagent

Research modes: ecosystem (default), feasibility, implementation, comparison.

Use `call_subordinate` to delegate phase research:
- **message**: Start with the researcher's full role identity and instructions (the researcher is a GSD phase researcher agent). Include:
  - Research type: "Phase Research — investigating HOW to implement a specific phase well"
  - Key insight: The question is NOT "which library should I use?" — it is "What do I not know that I don't know?" For this phase, discover: established architecture patterns, libraries that form the standard stack, problems people commonly hit, what is SOTA vs what training data thinks is SOTA, what should NOT be hand-rolled.
  - Objective: "Research implementation approach for Phase [phase_number]: [phase_name], Mode: ecosystem"
  - Files to read: requirements_path, context_path (if exists), state_path
  - Additional context: phase description
  - Downstream consumer note: "Your RESEARCH.md will be loaded by gsd-plan-phase which uses these sections: Standard Stack, Architecture Patterns, Don't Hand-Roll, Common Pitfalls, Code Examples. Be prescriptive, not exploratory. 'Use X' not 'Consider X or Y.'"
  - Quality gate: verify all domains investigated, negative claims verified with official docs, multiple sources for critical claims, confidence levels assigned honestly, section names match what plan-phase expects
  - Output: write to `.planning/phases/[phase_dir]/[phase_num]-RESEARCH.md`
  - Expected return format: `## RESEARCH COMPLETE`, `## CHECKPOINT REACHED`, or `## RESEARCH INCONCLUSIVE`
- **reset**: `"true"` for a new research session

## Step 5: Handle Agent Return

**`## RESEARCH COMPLETE`:** Display summary. Offer:
1. Plan phase — use `gsd-plan-phase` to proceed to planning
2. Dig deeper — spawn continuation for more investigation
3. Review full — display the RESEARCH.md content
4. Done — exit

**`## CHECKPOINT REACHED`:** Present checkpoint details to user. Get user response. Spawn continuation subagent (see Step 6).

**`## RESEARCH INCONCLUSIVE`:** Show what was attempted. Offer:
1. Add context — provide missing information and retry
2. Try different mode — switch to feasibility or implementation mode
3. Manual — user will research manually

## Step 6: Spawn Continuation Research Subagent

Use `call_subordinate` to continue research after a checkpoint:
- **message**: Include the researcher's full role identity as a GSD phase researcher agent. Reference the existing RESEARCH.md file as prior state (provide the path for the researcher to read). Include the checkpoint type and the user's response to the checkpoint.
- **reset**: `"false"` to continue the same research thread

After continuation returns: handle return in the same way as Step 5.

</process>

<success_criteria>
- [ ] Phase validated against roadmap
- [ ] Existing research checked and user informed
- [ ] gsd-phase-researcher spawned with full context (phase number, name, goal, file paths)
- [ ] `## CHECKPOINT REACHED` handled correctly — continuation spawned
- [ ] `## RESEARCH INCONCLUSIVE` handled — user offered alternatives
- [ ] User knows next steps after research completes
</success_criteria>
