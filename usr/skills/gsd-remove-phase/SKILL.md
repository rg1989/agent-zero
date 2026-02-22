---
name: gsd-remove-phase
description: Remove a future phase from roadmap and renumber subsequent phases
allowed-tools:
  - code_execution_tool
---

<objective>
Remove an unstarted future phase from the project roadmap, delete its directory, renumber all subsequent phases to maintain a clean linear sequence, and commit the change. The git commit serves as the historical record of removal.

Purpose: Clean removal of work you've decided not to do, without polluting context with cancelled/deferred markers.
Output: Phase deleted, all subsequent phases renumbered, git commit as historical record.
</objective>

<context>
Phase: the user-provided phase number to remove (integer or decimal)

Roadmap and state are resolved via targeted reads of `.planning/ROADMAP.md` and `.planning/STATE.md`.
</context>

<process>

<step name="parse_arguments">
Parse the command arguments:
- Argument is the phase number to remove (integer or decimal)
- Example: `gsd-remove-phase 17` → phase = 17
- Example: `gsd-remove-phase 16.1` → phase = 16.1

If no argument provided:

```
ERROR: Phase number required
Usage: gsd-remove-phase <phase-number>
Example: gsd-remove-phase 17
```

Exit.
</step>

<step name="init_context">
Read `.planning/STATE.md` and `.planning/ROADMAP.md` to determine:
- Current phase number
- Whether the target phase exists
- Phase directory and name

If the roadmap does not exist or the phase is not found, report and exit.
</step>

<step name="validate_future_phase">
Verify the phase is a future phase (not started):

1. Compare target phase to current phase from STATE.md
2. Target must be > current phase number

If target <= current phase:

```
ERROR: Cannot remove Phase {target}

Only future phases can be removed:
- Current phase: {current}
- Phase {target} is current or completed

To abandon current work, use gsd-pause-work instead.
```

Exit.
</step>

<step name="confirm_removal">
Present removal summary and confirm:

```
Removing Phase {target}: {Name}

This will:
- Delete: .planning/phases/{target}-{slug}/
- Renumber all subsequent phases
- Update: ROADMAP.md, STATE.md

Proceed? (y/n)
```

Wait for confirmation.
</step>

<step name="execute_removal">
**Perform the entire removal operation using `code_execution_tool`:**

1. Delete the target phase directory
2. Renumber all subsequent directories (in reverse order to avoid conflicts)
3. Rename all files inside renumbered directories (PLAN.md, SUMMARY.md, etc.)
4. Update ROADMAP.md (remove section, renumber all phase references, update dependencies)
5. Update STATE.md (decrement phase count if applicable)

If the phase has executed plans (SUMMARY.md files), warn the user and ask for explicit confirmation before proceeding with force removal.

Report extracted values: phases removed, directories renamed, files renamed, ROADMAP.md updated, STATE.md updated.
</step>

<step name="commit">
Stage and commit the removal using `code_execution_tool`:

```bash
git add .planning/
git commit -m "chore: remove phase {target} ({original-phase-name})"
```

The commit message preserves the historical record of what was removed.
</step>

<step name="completion">
Present completion summary:

```
Phase {target} ({original-name}) removed.

Changes:
- Deleted: .planning/phases/{target}-{slug}/
- Renumbered: {N} directories and {M} files
- Updated: ROADMAP.md, STATE.md
- Committed: chore: remove phase {target} ({original-name})

## What's Next

Would you like to:
- Check progress -- see updated roadmap status
- Continue with current phase
- Review roadmap
```
</step>

</process>

<anti_patterns>

- Don't remove completed phases (have SUMMARY.md files) without explicit user confirmation
- Don't remove current or past phases
- Don't manually renumber — the removal logic handles all renumbering
- Don't add "removed phase" notes to STATE.md — git commit is the record
- Don't modify completed phase directories
</anti_patterns>

<success_criteria>
Phase removal is complete when:

- [ ] Target phase validated as future/unstarted
- [ ] Phase directory deleted and subsequent phases renumbered
- [ ] Changes committed with descriptive message
- [ ] User informed of changes
</success_criteria>
