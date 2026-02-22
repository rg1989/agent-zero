---
name: gsd-add-phase
description: Add a new integer phase to the end of the current milestone in the roadmap
allowed-tools:
  - code_execution_tool
---

<objective>
Add a new integer phase to the end of the current milestone in the roadmap.

Handles:
- Phase number calculation (next sequential integer)
- Directory creation with slug generation
- Roadmap structure updates
- STATE.md roadmap evolution tracking
</objective>

<context>
Arguments: the user-provided phase description

Roadmap and state are resolved in-workflow via phase operation initialization and targeted reads.
</context>

<process>

<step name="parse_arguments">
Parse the command arguments:
- All arguments become the phase description
- Example: `gsd-add-phase Add authentication` -> description = "Add authentication"
- Example: `gsd-add-phase Fix critical performance issues` -> description = "Fix critical performance issues"

If no arguments provided:

```
ERROR: Phase description required
Usage: gsd-add-phase <description>
Example: gsd-add-phase Add authentication system
```

Exit.
</step>

<step name="init_context">
Load phase operation context by reading `.planning/ROADMAP.md` and `.planning/STATE.md`.

Check that the roadmap exists. If not:
```
ERROR: No roadmap found (.planning/ROADMAP.md)
Use the gsd-new-project skill to initialize.
```
Exit.
</step>

<step name="add_phase">
**Perform the phase addition using `code_execution_tool`:**

The operation must:
- Find the highest existing integer phase number in ROADMAP.md
- Calculate next phase number (max + 1)
- Generate a slug from the description (lowercase, hyphens, no special chars)
- Create the phase directory (`.planning/phases/{NN}-{slug}/`)
- Insert the phase entry into ROADMAP.md with Goal, Depends on, and Plans sections

Extract: `phase_number`, `padded`, `name`, `slug`, `directory`.
</step>

<step name="update_project_state">
Update STATE.md to reflect the new phase:

1. Read `.planning/STATE.md`
2. Under "## Accumulated Context" -> "### Roadmap Evolution" add entry:
   ```
   - Phase {N} added: {description}
   ```

If "Roadmap Evolution" section doesn't exist, create it.
</step>

<step name="completion">
Present completion summary:

```
Phase {N} added to current milestone:
- Description: {description}
- Directory: .planning/phases/{phase-num}-{slug}/
- Status: Not planned yet

Roadmap updated: .planning/ROADMAP.md

* * *

## Next Up

**Phase {N}: {description}**

Use the gsd-plan-phase skill to plan this phase.

(Start fresh context window first for best results)

* * *

**Also available:**
- Use gsd-add-phase to add another phase
- Review roadmap

* * *
```
</step>

</process>

<success_criteria>
- [ ] Phase number calculated as next sequential integer
- [ ] Phase directory created at correct path
- [ ] Roadmap updated with new phase entry
- [ ] STATE.md updated with roadmap evolution note
- [ ] User informed of next steps
</success_criteria>
