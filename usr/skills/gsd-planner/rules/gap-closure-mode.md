# Gap Closure Mode and Revision Mode

Two special operating modes for gsd-planner.

## Gap Closure Mode

Triggered by `--gaps` flag. Creates plans to address verification or UAT failures.

### Step 1: Find Gap Sources

Use `code_execution_tool` to check for gap files in the phase directory:

```bash
# Check for VERIFICATION.md (code verification gaps)
ls "$phase_dir"/*-VERIFICATION.md 2>/dev/null

# Check for UAT.md with diagnosed status (user testing gaps)
grep -l "status: diagnosed" "$phase_dir"/*-UAT.md 2>/dev/null
```

Read STATE.md and ROADMAP.md via `code_execution_tool` to load phase context and identify the phase directory.

### Step 2: Parse Gaps

Each gap has: truth (failed behavior), reason, artifacts (files with issues), missing (things to add/fix).

### Step 3: Load Existing SUMMARYs

Use `code_execution_tool` to read all existing SUMMARY.md files in the phase directory to understand what's already built and how.

### Step 4: Find Next Plan Number

Use `code_execution_tool` to list existing PLAN.md files. If plans 01-03 exist, next is 04.

### Step 5: Group Gaps into Plans

Group by: same artifact, same concern, dependency order (can't wire if artifact is stub → fix stub first).

### Step 6: Create Gap Closure Tasks

```xml
<task name="{fix_description}" type="auto">
  <files>{artifact.path}</files>
  <action>
    For each item in gap.missing:
    - {missing item}

    Reference existing code: {from SUMMARYs}
    Gap reason: {gap.reason}
  </action>
  <verify>{How to confirm gap is closed}</verify>
  <done>{Observable truth now achievable}</done>
</task>
```

### Step 7: Write Gap Closure PLAN.md Files

```yaml
---
phase: XX-name
plan: NN              # Sequential after existing
type: execute
wave: 1               # Gap closures typically single wave
depends_on: []
files_modified: [...]
autonomous: true
gap_closure: true     # Flag for tracking
---
```

### Step 8: Commit

Use `code_execution_tool` to run:
```bash
git add .planning/phases/$PHASE-*/$PHASE-*-PLAN.md .planning/ROADMAP.md
git commit -m "docs($PHASE): create gap closure plans"
```

## Revision Mode

Triggered when the orchestrator provides `<revision_context>` with checker issues. NOT starting fresh — making targeted updates to existing plans.

**Mindset:** Surgeon, not architect. Minimal changes for specific issues.

### Step 1: Load Existing Plans

Use `code_execution_tool` to read all existing PLAN.md files in the phase directory. Build mental model of current plan structure, existing tasks, must_haves.

### Step 2: Parse Checker Issues

Issues come in structured format:

```yaml
issues:
  - plan: "16-01"
    dimension: "task_completeness"
    severity: "blocker"
    description: "Task 2 missing <verify> element"
    fix_hint: "Add verification command for build output"
```

Group by plan, dimension, severity.

### Step 3: Revision Strategy

| Dimension | Strategy |
|-----------|----------|
| requirement_coverage | Add task(s) for missing requirement |
| task_completeness | Add missing elements to existing task |
| dependency_correctness | Fix depends_on, recompute waves |
| key_links_planned | Add wiring task or update action |
| scope_sanity | Split into multiple plans |
| must_haves_derivation | Derive and add must_haves to frontmatter |

### Step 4: Make Targeted Updates

**DO:** Edit specific flagged sections, preserve working parts, update waves if dependencies change.

**DO NOT:** Rewrite entire plans for minor issues, add unnecessary tasks, break existing working plans.

### Step 5: Validate Changes

- [ ] All flagged issues addressed
- [ ] No new issues introduced
- [ ] Wave numbers still valid
- [ ] Dependencies still correct
- [ ] Files on disk updated

### Step 6: Commit

Use `code_execution_tool` to run:
```bash
git add .planning/phases/$PHASE-*/$PHASE-*-PLAN.md
git commit -m "fix($PHASE): revise plans based on checker feedback"
```

### Step 7: Return Revision Summary

```markdown
## REVISION COMPLETE

**Issues addressed:** {N}/{M}

### Changes Made

| Plan | Change | Issue Addressed |
|------|--------|-----------------|
| 16-01 | Added <verify> to Task 2 | task_completeness |
| 16-02 | Added logout task | requirement_coverage (AUTH-02) |

### Files Updated

- .planning/phases/16-xxx/16-01-PLAN.md
- .planning/phases/16-xxx/16-02-PLAN.md

{If any issues NOT addressed:}

### Unaddressed Issues

| Issue | Reason |
|-------|--------|
| {issue} | {why - needs user input, architectural change, etc.} |
```
