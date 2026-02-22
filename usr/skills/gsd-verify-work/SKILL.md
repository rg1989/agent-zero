---
name: gsd-verify-work
description: Validate built features through conversational UAT
allowed-tools:
  - code_execution_tool
  - call_subordinate
---

<objective>
Validate built features through conversational testing with persistent state.

Purpose: Confirm what was built actually works from the user's perspective. One test at a time, plain text responses, no interrogation. When issues are found, automatically diagnose, plan fixes, and prepare for execution.

Phase: the phase number provided by the user (optional — if not provided, the skill checks for active sessions or prompts for phase).

Output: {phase_num}-UAT.md tracking all test results. If issues found: diagnosed gaps, verified fix plans ready for re-execution.

The UAT.md template (in the GSD installation templates/ directory) defines the UAT session structure with test results, status, and issue tracking fields including frontmatter (status, phase, source, started, updated), Current Test section, Tests section, Summary counts, and Gaps section.
</objective>

<philosophy>
**Show expected, ask if reality matches.**

Present what SHOULD happen. User confirms or describes what's different.
- "yes" / "y" / "next" / empty → pass
- Anything else → logged as issue, severity inferred

No Pass/Fail buttons. No severity questions. Just: "Here's what should happen. Does it?"
</philosophy>

<process>

<step name="initialize">
If a phase number was provided by the user, load context by reading:
- `.planning/ROADMAP.md` to find the phase directory
- `.planning/STATE.md` for project context

Identify: `phase_dir`, `phase_number`, `phase_name`.
</step>

<step name="check_active_session">
**First: Check for active UAT sessions**

```bash
find .planning/phases -name "*-UAT.md" -type f 2>/dev/null | head -5
```

**If active sessions exist AND no phase provided:**

Read each file's frontmatter (status, phase) and Current Test section.

Display inline:

    Active UAT Sessions

    | # | Phase | Status | Current Test | Progress |
    |---|-------|--------|--------------|----------|
    | 1 | 04-comments | testing | 3. Reply to Comment | 2/6 |
    | 2 | 05-auth | testing | 1. Login Form | 0/4 |

    Reply with a number to resume, or provide a phase number to start new.

Wait for user response.
- If user replies with number → Load that file, go to `resume_from_file`
- If user replies with phase number → Treat as new session, go to `create_uat_file`

**If active sessions exist AND phase provided:**
Check if session exists for that phase. If yes, offer to resume or restart.
If no, continue to `create_uat_file`.

**If no active sessions AND no phase provided:**

    No active UAT sessions.
    Provide a phase number to start testing.

**If no active sessions AND phase provided:**
Continue to `create_uat_file`.
</step>

<step name="find_summaries">
**Find what to test:**

```bash
ls "$phase_dir"/*-SUMMARY.md 2>/dev/null
```

Read each SUMMARY.md to extract testable deliverables.
</step>

<step name="extract_tests">
**Extract testable deliverables from SUMMARY.md:**

Parse for:
1. **Accomplishments** - Features/functionality added
2. **User-facing changes** - UI, workflows, interactions

Focus on USER-OBSERVABLE outcomes, not implementation details.

For each deliverable, create a test:
- name: Brief test name
- expected: What the user should see/experience (specific, observable)

Examples:
- Accomplishment: "Added comment threading with infinite nesting"
  -> Test: "Reply to a Comment"
  -> Expected: "Clicking Reply opens inline composer below comment. Submitting shows reply nested under parent with visual indentation."

Skip internal/non-observable items (refactors, type changes, etc.).
</step>

<step name="create_uat_file">
**Create UAT file with all tests:**

```bash
mkdir -p "$phase_dir"
```

Build test list from extracted deliverables.

Create file at `.planning/phases/XX-name/{phase_num}-UAT.md`:

    ---
    status: testing
    phase: XX-name
    source: [list of SUMMARY.md files]
    started: [ISO timestamp]
    updated: [ISO timestamp]
    ---

    ## Current Test
    (OVERWRITE each test - shows where we are)

    number: 1
    name: [first test name]
    expected: |
      [what user should observe]
    awaiting: user response

    ## Tests

    ### 1. [Test Name]
    expected: [observable behavior]
    result: [pending]

    ...

    ## Summary

    total: [N]
    passed: 0
    issues: 0
    pending: [N]
    skipped: 0

    ## Gaps

    [none yet]

Proceed to `present_test`.
</step>

<step name="present_test">
**Present current test to user:**

Read Current Test section from UAT file.

Display:

    +----------------------------------------------------------+
    |  CHECKPOINT: Verification Required                       |
    +----------------------------------------------------------+

    Test {number}: {name}

    {expected}

    ----------------------------------------------------------
    -> Type "pass" or describe what's wrong
    ----------------------------------------------------------

Wait for user response (plain text).
</step>

<step name="process_response">
**Process user response and update file:**

**If response indicates pass:**
Empty response, "yes", "y", "ok", "pass", "next", "approved"

Update Tests section:

    ### {N}. {name}
    expected: {expected}
    result: pass

**If response indicates skip:**
"skip", "can't test", "n/a"

Update Tests section:

    ### {N}. {name}
    expected: {expected}
    result: skipped
    reason: [user's reason if provided]

**If response is anything else:**
Treat as issue description.

Infer severity from description:
- Contains: crash, error, exception, fails, broken, unusable → blocker
- Contains: doesn't work, wrong, missing, can't → major
- Contains: slow, weird, off, minor, small → minor
- Contains: color, font, spacing, alignment, visual → cosmetic
- Default if unclear: major

Update Tests section:

    ### {N}. {name}
    expected: {expected}
    result: issue
    reported: "{verbatim user response}"
    severity: {inferred}

Append to Gaps section (structured YAML):

    - truth: "{expected behavior from test}"
      status: failed
      reason: "User reported: {verbatim user response}"
      severity: {inferred}
      test: {N}
      artifacts: []
      missing: []

**After any response:**

Update Summary counts. Update frontmatter.updated timestamp.

If more tests remain → Update Current Test, go to `present_test`
If no more tests → Go to `complete_session`
</step>

<step name="resume_from_file">
**Resume testing from UAT file:**

Read the full UAT file. Find first test with `result: [pending]`.

Announce:

    Resuming: Phase {phase} UAT
    Progress: {passed + issues + skipped}/{total}
    Issues found so far: {issues count}

    Continuing from Test {N}...

Update Current Test section with the pending test. Proceed to `present_test`.
</step>

<step name="complete_session">
**Complete testing and commit:**

Update frontmatter: status: complete, updated: [now]

Clear Current Test section:

    ## Current Test

    [testing complete]

Commit the UAT file:

```bash
git add ".planning/phases/XX-name/{phase_num}-UAT.md"
git commit -m "test({phase_num}): complete UAT - {passed} passed, {issues} issues"
```

Present summary:

    UAT Complete: Phase {phase}

    | Result  | Count |
    |---------|-------|
    | Passed  | {N}   |
    | Issues  | {N}   |
    | Skipped | {N}   |

**If issues > 0:** Proceed to `diagnose_issues`

**If issues == 0:**

    All tests passed. Ready to continue.
    - Plan next phase: use gsd-plan-phase skill
    - Execute next phase: use gsd-execute-phase skill
</step>

<step name="diagnose_issues">
**Diagnose root causes before planning fixes:**

Display:

    {N} issues found. Diagnosing root causes...
    Spawning parallel debug agents to investigate each issue.

## Spawn Diagnosis Subagents

Use `call_subordinate` to delegate parallel issue diagnosis:
- **message**: Include the subordinate's full role identity (debugging specialist), the UAT context (phase number, UAT file path, the specific issue truth + reported symptom + severity), which SUMMARY.md and source files to inspect, and the expected return format (`## ROOT CAUSE FOUND` with root_cause field, or `## CHECKPOINT REACHED` if blocked)
- **reset**: `"true"` for each new diagnosis agent (fresh context per issue)

Spawn one subordinate per issue in parallel. Collect root causes. Update UAT.md Gaps section with diagnosed root causes. Proceed to `plan_gap_closure`.

Diagnosis runs automatically — no user prompt needed.
</step>

<step name="plan_gap_closure">
**Auto-plan fixes from diagnosed gaps:**

Display:

    GSD: PLANNING FIXES
    Spawning planner for gap closure...

## Spawn Planning Subagent

Use `call_subordinate` to delegate gap closure planning:
- **message**: Include the subordinate's full role identity (GSD planner in gap_closure mode), the phase context (phase number, phase directory path, paths to UAT file with diagnoses, STATE.md, ROADMAP.md), and the expected return format (`## PLANNING COMPLETE` when done or `## PLANNING INCONCLUSIVE` with explanation)
- **reset**: `"true"` (fresh planner context)

On return:
- **PLANNING COMPLETE:** Proceed to `verify_gap_plans`
- **PLANNING INCONCLUSIVE:** Report and offer manual intervention
</step>

<step name="verify_gap_plans">
**Verify fix plans with checker:**

Display:

    GSD: VERIFYING FIX PLANS
    Spawning plan checker...

Initialize: `iteration_count = 1`

## Spawn Plan Checker Subagent

Use `call_subordinate` to delegate plan verification:
- **message**: Include the subordinate's full role identity (GSD plan checker), the verification context (phase number, phase goal: "Close diagnosed gaps from UAT", paths to all PLAN.md files in the phase directory), and the expected return format (`## VERIFICATION PASSED` when all checks pass, or `## ISSUES FOUND` with structured issue list)
- **reset**: `"true"` (fresh checker context)

On return:
- **VERIFICATION PASSED:** Proceed to `present_ready`
- **ISSUES FOUND:** Proceed to `revision_loop`
</step>

<step name="revision_loop">
**Iterate planner and checker until plans pass (max 3):**

**If iteration_count < 3:**

Display: `Sending back to planner for revision... (iteration {N}/3)`

## Spawn Revision Planner Subagent

Use `call_subordinate` to delegate plan revision:
- **message**: Include the subordinate's full role identity (GSD planner in revision mode), the revision context (phase number, paths to existing PLAN.md files, the structured issues returned by the checker), and instructions to make targeted updates — NOT replan from scratch unless issues are fundamental. Expected return: `## PLANNING COMPLETE`
- **reset**: `"true"` (fresh planner context for revision)

After planner returns → spawn checker again (verify_gap_plans logic).
Increment iteration_count.

**If iteration_count >= 3:**

Display: `Max iterations reached. {N} issues remain.`

Offer options:
1. Force proceed (execute despite issues)
2. Provide guidance (user gives direction, retry)
3. Abandon (exit, user runs plan-phase manually)

Wait for user response.
</step>

<step name="present_ready">
**Present completion and next steps:**

    GSD: FIXES READY

    Phase {X}: {Name} — {N} gap(s) diagnosed, {M} fix plan(s) created

    | Gap | Root Cause | Fix Plan |
    |-----|------------|----------|
    | {truth 1} | {root_cause} | {phase}-04 |
    | {truth 2} | {root_cause} | {phase}-04 |

    Plans verified and ready for execution.

    ## Next Up

    Execute fixes — run fix plans
    Use gsd-execute-phase skill with --gaps-only flag

</step>

</process>

<update_rules>
**Batched writes for efficiency:**

Keep results in memory. Write to file only when:
1. **Issue found** — Preserve the problem immediately
2. **Session complete** — Final write before commit
3. **Checkpoint** — Every 5 passed tests (safety net)

| Section | Rule | When Written |
|---------|------|--------------|
| Frontmatter.status | OVERWRITE | Start, complete |
| Frontmatter.updated | OVERWRITE | On any file write |
| Current Test | OVERWRITE | On any file write |
| Tests.{N}.result | OVERWRITE | On any file write |
| Summary | OVERWRITE | On any file write |
| Gaps | APPEND | When issue found |

On context reset: File shows last checkpoint. Resume from there.
</update_rules>

<severity_inference>
**Infer severity from user's natural language:**

| User says | Infer |
|-----------|-------|
| "crashes", "error", "exception", "fails completely" | blocker |
| "doesn't work", "nothing happens", "wrong behavior" | major |
| "works but...", "slow", "weird", "minor issue" | minor |
| "color", "spacing", "alignment", "looks off" | cosmetic |

Default to **major** if unclear. User can correct if needed.

**Never ask "how severe is this?"** — just infer and move on.
</severity_inference>

<success_criteria>
- [ ] UAT file created with all tests from SUMMARY.md
- [ ] Tests presented one at a time with expected behavior
- [ ] User responses processed as pass/issue/skip
- [ ] Severity inferred from description (never asked)
- [ ] Batched writes: on issue, every 5 passes, or completion
- [ ] Committed on completion
- [ ] If issues: parallel debug agents diagnose root causes via call_subordinate
- [ ] If issues: planning subagent creates fix plans (gap_closure mode) via call_subordinate
- [ ] If issues: checker subagent verifies fix plans via call_subordinate
- [ ] If issues: revision loop until plans pass (max 3 iterations)
- [ ] Ready for re-execution when complete
</success_criteria>
