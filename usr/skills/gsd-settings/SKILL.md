---
name: gsd-settings
description: Configure GSD workflow toggles and model profile
allowed-tools:
  - code_execution_tool
  - input
---

<objective>
Interactive configuration of GSD workflow agents and model profile via multi-question prompt.

Handles:
- Config existence ensuring
- Current settings reading and parsing
- Interactive 6-question prompt (model, research, plan_check, verifier, auto-advance, branching)
- Config merging and writing
- Confirmation display with quick command references
</objective>

<process>

### Step 1: Ensure Config and Load State

Create `.planning/config.json` with defaults if it doesn't exist.

Default values:
```json
{
  "mode": "yolo",
  "depth": "quick",
  "model_profile": "balanced",
  "commit_docs": true,
  "parallelization": true,
  "workflow": {
    "research": true,
    "plan_check": true,
    "verifier": true,
    "auto_advance": false
  },
  "git": {
    "branching_strategy": "none"
  }
}
```

Read `.planning/config.json` to load current settings.

### Step 2: Read Current Config

Parse current values (default to `true` if not present):
- `workflow.research` — spawn researcher during plan-phase
- `workflow.plan_check` — spawn plan checker during plan-phase
- `workflow.verifier` — spawn verifier during execute-phase
- `workflow.auto_advance` — chain stages automatically
- `model_profile` — which model each agent uses (default: `balanced`)
- `git.branching_strategy` — branching approach (default: `"none"`)

### Step 3: Present Settings

Present all settings to the user with current values pre-selected. Use `input` for each question in sequence:

**Question 1: Model Profile**
"Which model profile for agents?"
Options:
- "Quality" — Opus everywhere except verification (highest cost)
- "Balanced (Recommended)" — Opus for planning, Sonnet for execution/verification
- "Budget" — Sonnet for writing, Haiku for research/verification (lowest cost)

**Question 2: Plan Researcher**
"Spawn Plan Researcher? (researches domain before planning)"
Options:
- "Yes" — Research phase goals before planning
- "No" — Skip research, plan directly

**Question 3: Plan Checker**
"Spawn Plan Checker? (verifies plans before execution)"
Options:
- "Yes" — Verify plans meet phase goals
- "No" — Skip plan verification

**Question 4: Execution Verifier**
"Spawn Execution Verifier? (verifies phase completion)"
Options:
- "Yes" — Verify must-haves after execution
- "No" — Skip post-execution verification

**Question 5: Auto-Advance**
"Auto-advance pipeline? (discuss → plan → execute automatically)"
Options:
- "No (Recommended)" — Manual clear and paste between stages
- "Yes" — Chain stages via subordinate agents (same isolation)

**Question 6: Git Branching**
"Git branching strategy?"
Options:
- "None (Recommended)" — Commit directly to current branch
- "Per Phase" — Create branch for each phase (gsd/phase-{N}-{name})
- "Per Milestone" — Create branch for entire milestone (gsd/{version}-{name})

### Step 4: Update Config

Merge new settings into existing config.json:

```json
{
  ...existing_config,
  "model_profile": "quality" | "balanced" | "budget",
  "workflow": {
    "research": true/false,
    "plan_check": true/false,
    "verifier": true/false,
    "auto_advance": true/false
  },
  "git": {
    "branching_strategy": "none" | "phase" | "milestone"
  }
}
```

Write updated config to `.planning/config.json`.

### Step 5: Save as Defaults (Optional)

Ask the user:
"Save these as default settings for all new projects?"
- "Yes" — New projects start with these settings (saved to the user's home directory under `.gsd/defaults.json`)
- "No" — Only apply to this project

If "Yes": Write the same config object (minus project-specific fields) to `~/.gsd/defaults.json`:

```bash
mkdir -p ~/.gsd
```

Write `~/.gsd/defaults.json` with:
```json
{
  "mode": <current>,
  "depth": <current>,
  "model_profile": <current>,
  "commit_docs": <current>,
  "parallelization": <current>,
  "branching_strategy": <current>,
  "workflow": {
    "research": <current>,
    "plan_check": <current>,
    "verifier": <current>,
    "auto_advance": <current>
  }
}
```

### Step 6: Confirm

Display:

```
GSD - SETTINGS UPDATED

| Setting              | Value |
|----------------------|-------|
| Model Profile        | {quality/balanced/budget} |
| Plan Researcher      | {On/Off} |
| Plan Checker         | {On/Off} |
| Execution Verifier   | {On/Off} |
| Auto-Advance         | {On/Off} |
| Git Branching        | {None/Per Phase/Per Milestone} |
| Saved as Defaults    | {Yes/No} |

These settings apply to future gsd-plan-phase and gsd-execute-phase skill runs.

Quick reference:
- Use `gsd-plan-phase` with --research to force research
- Use `gsd-plan-phase` with --skip-research to skip research
- Use `gsd-plan-phase` with --skip-verify to skip plan check
```

</process>

<success_criteria>
- [ ] Current config read
- [ ] User presented with 6 settings (profile + 4 workflow toggles + git branching)
- [ ] Config updated with model_profile, workflow, and git sections
- [ ] User offered to save as global defaults (~/.gsd/defaults.json)
- [ ] Changes confirmed to user
</success_criteria>
