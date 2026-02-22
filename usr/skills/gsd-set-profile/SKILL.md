---
name: gsd-set-profile
description: Switch model profile for GSD agents (quality/balanced/budget)
allowed-tools:
  - code_execution_tool
---

<objective>
Switch the model profile used by GSD agents. Controls which model each agent uses, balancing quality vs token spend.

Handles:
- Argument validation (quality/balanced/budget)
- Config file creation if missing
- Profile update in config.json
- Confirmation with model table display
</objective>

<process>

<step name="validate">
Validate the user-provided profile argument:

Valid profiles are: `quality`, `balanced`, `budget`

If the argument is not one of these three values:
```
Error: Invalid profile "{provided-value}"
Valid profiles: quality, balanced, budget
```
Exit.
</step>

<step name="ensure_and_load_config">
Ensure config exists and load current state:

Use `code_execution_tool` to check if `.planning/config.json` exists. If it does not exist, create it with default content:
```json
{
  "model_profile": "balanced"
}
```

Read current config from `.planning/config.json`.
</step>

<step name="update_config">
Update the `model_profile` field in the config to the validated profile value.

Write updated config back to `.planning/config.json`.
</step>

<step name="confirm">
Display confirmation with model table for the selected profile:

```
Model profile set to: {profile}

Agents will now use:

| Agent | Model |
|-------|-------|
| planner | [model for selected profile] |
| executor | [model for selected profile] |
| verifier | [model for selected profile] |
| ... | ... |

Next spawned agents will use the new profile.
```

Model mapping by profile:
- **quality**: highest capability models for all agents
- **balanced**: mix of capable and efficient models
- **budget**: cost-effective models for all agents
</step>

</process>

<success_criteria>
- [ ] Argument validated against allowed profiles
- [ ] Config file ensured and loaded
- [ ] Config updated with new model_profile
- [ ] Confirmation displayed with model table
</success_criteria>
