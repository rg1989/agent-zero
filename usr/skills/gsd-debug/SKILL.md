---
name: gsd-debug
description: Systematic debugging with persistent state across context resets — uses scientific method with subagent isolation to investigate issues, handle checkpoints, and spawn continuations
allowed-tools:
  - code_execution_tool
  - call_subordinate
  - input
---

<objective>
Debug issues using scientific method with subagent isolation.

**Orchestrator role:** Gather symptoms, spawn gsd-debugger agent, handle checkpoints, spawn continuations.

**Why subagent:** Investigation burns context fast (reading files, forming hypotheses, testing). Fresh 200k context per investigation. Main context stays lean for user interaction.
</objective>

<context>
User's issue: the issue description provided by the user

Check for active sessions:

```bash
ls .planning/debug/*.md 2>/dev/null | grep -v resolved | head -5
```
</context>

<process>

## 0. Initialize Context

Load project state by reading `.planning/STATE.md` and `.planning/config.json` to determine workflow preferences (commit_docs setting).

Select the debugger model from project configuration (defaults to the primary model if not configured).

## 1. Check Active Sessions

If active sessions exist AND no issue provided by user:
- List sessions with status, hypothesis, next action
- User picks number to resume OR describes new issue

If issue provided by user OR user describes new issue:
- Continue to symptom gathering

## 2. Gather Symptoms (if new issue)

Use `input` to ask the user for each:

1. **Expected behavior** - What should happen?
2. **Actual behavior** - What happens instead?
3. **Error messages** - Any errors? (paste or describe)
4. **Timeline** - When did this start? Ever worked?
5. **Reproduction** - How do you trigger it?

After all gathered, confirm ready to investigate.

## 3. Spawn gsd-debugger Subagent

Fill the investigation prompt with gathered symptoms. Use `call_subordinate` to delegate investigation:

- **message**: Include the subordinate's full role identity as a debugging specialist,
  the issue context (slug, expected behavior, actual behavior, errors, reproduction steps,
  timeline), which debug file to create (`.planning/debug/{slug}.md`), and the expected
  return format (`## ROOT CAUSE FOUND`, `## CHECKPOINT REACHED`, or
  `## INVESTIGATION INCONCLUSIVE`)
- **reset**: `"true"` for a new investigation

Example message structure:
> You are a debugging specialist using the scientific method. Issue: {slug}.
> Expected: {expected}. Actual: {actual}. Errors: {errors}. Reproduction: {reproduction}.
> Timeline: {timeline}.
> Create debug file at: .planning/debug/{slug}.md
> Return one of: ## ROOT CAUSE FOUND, ## CHECKPOINT REACHED, or ## INVESTIGATION INCONCLUSIVE.

The investigation prompt should also include:

```
<objective>
Investigate issue: {slug}

**Summary:** {trigger}
</objective>

<symptoms>
expected: {expected}
actual: {actual}
errors: {errors}
reproduction: {reproduction}
timeline: {timeline}
</symptoms>

<mode>
symptoms_prefilled: true
goal: find_and_fix
</mode>

<debug_file>
Create: .planning/debug/{slug}.md
</debug_file>
```

## 4. Handle Agent Return

**If `## ROOT CAUSE FOUND`:**
- Display root cause and evidence summary
- Offer options:
  - "Fix now" - spawn fix subagent
  - "Plan fix" - suggest running the gsd-plan-phase skill with gaps mode
  - "Manual fix" - done

**If `## CHECKPOINT REACHED`:**
- Present checkpoint details to user
- Get user response via `input`
- Spawn continuation agent (see step 5)

**If `## INVESTIGATION INCONCLUSIVE`:**
- Show what was checked and eliminated
- Offer options:
  - "Continue investigating" - spawn new agent with additional context
  - "Manual investigation" - done
  - "Add more context" - gather more symptoms, spawn again

## 5. Spawn Continuation Debugging Subagent

When user responds to checkpoint, use `call_subordinate` to continue investigation after checkpoint response:

- **message**: Include the subordinate's full role identity as a debugging specialist,
  reference to the existing debug file (`.planning/debug/{slug}.md` contains prior state),
  the checkpoint type and user's response, and the same expected return format
  (`## ROOT CAUSE FOUND`, `## CHECKPOINT REACHED`, or `## INVESTIGATION INCONCLUSIVE`)
- **reset**: `"false"` to continue the same investigation thread

The continuation prompt should also include:

```
<objective>
Continue debugging {slug}. Evidence is in the debug file.
</objective>

<prior_state>
<files_to_read>
- .planning/debug/{slug}.md (Debug session state)
</files_to_read>
</prior_state>

<checkpoint_response>
**Type:** {checkpoint_type}
**Response:** {user_response}
</checkpoint_response>

<mode>
goal: find_and_fix
</mode>
```

</process>

<success_criteria>
- [ ] Active sessions checked
- [ ] Symptoms gathered (if new)
- [ ] gsd-debugger subagent spawned with context via call_subordinate
- [ ] Checkpoints handled correctly
- [ ] Root cause confirmed before fixing
</success_criteria>
