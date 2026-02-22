---
name: gsd-health
description: Diagnose planning directory health and optionally repair issues
allowed-tools:
  - code_execution_tool
  - input
---

<objective>
Validate `.planning/` directory integrity and report actionable issues. Checks for missing files, invalid configurations, inconsistent state, and orphaned plans. Optionally repairs auto-fixable issues.
</objective>

<context>
Arguments: the user-provided flag (optional: `--repair` to auto-fix repairable issues)

Parses `--repair` flag from arguments and adjusts behavior accordingly.
</context>

<process>

<step name="parse_args">
**Parse arguments:**

Check if `--repair` flag is present in the provided arguments.

Set `repair_mode = true` if `--repair` is found, otherwise `repair_mode = false`.
</step>

<step name="run_health_check">
**Run health validation using `code_execution_tool`:**

Check each of the following items, collecting errors, warnings, and info:

**Required files (errors if missing):**
- `.planning/` directory exists (E001)
- `.planning/PROJECT.md` exists (E002)
- `.planning/ROADMAP.md` exists (E003)
- `.planning/STATE.md` exists (E004 - repairable)
- `.planning/config.json` exists and parses as valid JSON (E005 - repairable)

**State consistency (warnings if inconsistent):**
- PROJECT.md has required sections: Project Goal, Milestone Strategy, Key Decisions (W001)
- STATE.md references valid phase numbers that exist in ROADMAP.md (W002 - repairable)
- config.json exists (W003 - repairable)
- config.json has valid field values (W004)
- Phase directory names follow NN-name format (W005)
- Phase in ROADMAP.md has a corresponding directory (W006)
- Phase directory exists but is not in ROADMAP.md (W007)

**Info (non-blocking):**
- Plans without SUMMARY.md (may be in progress) (I001)

Collect all findings into: `errors[]`, `warnings[]`, `info[]`, `repairable_count`.

**If repair_mode is true**, perform repairs for repairable issues:
- E004 (STATE.md missing): Regenerate STATE.md from ROADMAP.md structure
- E005 (config.json parse error): Reset config.json to defaults
- W002 (invalid phase reference in STATE.md): Update to valid phase reference
- W003 (config.json missing): Create config.json with defaults

Record all `repairs_performed[]`.
</step>

<step name="format_output">
**Format and display results:**

```
GSD Health Check

Status: HEALTHY | DEGRADED | BROKEN
Errors: N | Warnings: N | Info: N
```

**If repairs were performed:**
```
## Repairs Performed

- config.json: Created with defaults
- STATE.md: Regenerated from roadmap
```

**If errors exist:**
```
## Errors

- [E001] .planning/ directory not found
  Fix: Use gsd-new-project to initialize

- [E002] PROJECT.md not found
  Fix: Use gsd-new-project to create

- [E005] config.json: JSON parse error
  Fix: Re-run with --repair to reset to defaults
```

**If warnings exist:**
```
## Warnings

- [W001] PROJECT.md missing required section
  Fix: Manually add missing section

- [W005] Phase directory "1-setup" doesn't follow NN-name format
  Fix: Rename to match pattern (e.g., 01-setup)
```

**If info exists:**
```
## Info

- [I001] 02-implementation/02-01-PLAN.md has no SUMMARY.md
  Note: May be in progress
```

**Footer (if repairable issues exist and --repair was NOT used):**
```
* * *
N issues can be auto-repaired. Re-run with --repair flag.
```
</step>

<step name="offer_repair">
**If repairable issues exist and --repair was NOT used:**

Use `input` to ask:
- question: "Would you like to run repairs to fix [N] issues automatically?"
- options: "Yes -- repair now" | "No -- show results only"

If yes, re-run the health check with repair mode enabled and display updated results.
</step>

<step name="verify_repairs">
**If repairs were performed:**

Re-run the health check (without repair mode) to confirm issues are resolved.

Report final status after repairs.
</step>

</process>

<error_codes>

| Code | Severity | Description | Repairable |
|------|----------|-------------|------------|
| E001 | error | .planning/ directory not found | No |
| E002 | error | PROJECT.md not found | No |
| E003 | error | ROADMAP.md not found | No |
| E004 | error | STATE.md not found | Yes |
| E005 | error | config.json parse error | Yes |
| W001 | warning | PROJECT.md missing required section | No |
| W002 | warning | STATE.md references invalid phase | Yes |
| W003 | warning | config.json not found | Yes |
| W004 | warning | config.json invalid field value | No |
| W005 | warning | Phase directory naming mismatch | No |
| W006 | warning | Phase in ROADMAP but no directory | No |
| W007 | warning | Phase on disk but not in ROADMAP | No |
| I001 | info | Plan without SUMMARY (may be in progress) | No |

</error_codes>

<repair_actions>

| Action | Effect | Risk |
|--------|--------|------|
| createConfig | Create config.json with defaults | None |
| resetConfig | Delete and recreate config.json | Loses custom settings |
| regenerateState | Create STATE.md from ROADMAP structure | Loses session history |

**Not repairable (too risky):**
- PROJECT.md, ROADMAP.md content
- Phase directory renaming
- Orphaned plan cleanup

</repair_actions>

<success_criteria>
- [ ] All planning directory files checked for existence
- [ ] State consistency validated against roadmap
- [ ] Errors, warnings, and info clearly categorized
- [ ] Repairable issues fixed if --repair flag provided
- [ ] Final status reported (HEALTHY / DEGRADED / BROKEN)
</success_criteria>
