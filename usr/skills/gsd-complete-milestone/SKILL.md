---
name: gsd-complete-milestone
description: Archive completed milestone and prepare for next version
allowed-tools:
  - code_execution_tool
---

<objective>
Mark a milestone (e.g., "1.0", "1.1", "2.0") complete, archive to milestones/, and update ROADMAP.md and REQUIREMENTS.md.

The version number is provided by the user when invoking this skill.

Purpose: Create historical record of shipped version, archive milestone artifacts (roadmap + requirements), and prepare for next milestone.
Output: Milestone archived (roadmap + requirements), PROJECT.md evolved, git tagged.
</objective>

<process>

## Pre-flight Check

Before executing the milestone completion flow, check whether a milestone audit has been run:

- Look for `.planning/v{version}-MILESTONE-AUDIT.md`
- If missing or stale: recommend using the `gsd-audit-milestone` skill first
- If audit status is `gaps_found`: recommend using the `gsd-plan-milestone-gaps` skill first
- If audit passed: proceed to the milestone completion flow

Display preflight status:

    Pre-flight Check

    {If no v{version}-MILESTONE-AUDIT.md:}
    No milestone audit found. Run gsd-audit-milestone first to verify
    requirements coverage, cross-phase integration, and E2E flows.

    {If audit has gaps:}
    Milestone audit found gaps. Run gsd-plan-milestone-gaps to create
    phases that close the gaps, or proceed anyway to accept as tech debt.

    {If audit passed:}
    Milestone audit passed. Proceeding with completion.

## Milestone Completion Flow

The full step-by-step workflow is in `rules/workflow.md`. The 8 steps are:

1. **Verify readiness** — Check all phases have completed plans (SUMMARY.md exists). Analyze ROADMAP.md for phase/plan counts. Check requirements completion against REQUIREMENTS.md traceability table. Surface incomplete requirements with proceed/audit/abort options.

2. **Gather stats** — Calculate milestone statistics: phase range, plan count, task count, file changes, LOC, and git timeline. Present a summary table.

3. **Extract accomplishments** — Read all phase SUMMARY.md files in the milestone range. Extract 4-6 key accomplishments from their one-liners and summaries. Present for review.

4. **Archive milestone** — Create `.planning/milestones/v{version}-ROADMAP.md` and `.planning/milestones/v{version}-REQUIREMENTS.md` using the milestone-archive.md template structure (which defines the archive document with shipped summary, phases list, requirements outcome, and key decisions sections). Update MILESTONES.md with stats.

5. **Full PROJECT.md evolution review** — Compare current description to what was built. Move shipped requirements to Validated. Update Key Decisions table. Check constraints. Update "Last updated" footer.

6. **Reorganize ROADMAP.md** — Group completed milestone phases under a `<details>` block with milestone header. Delete original REQUIREMENTS.md (fresh for next milestone).

7. **Create git tag and commit** — Stage milestone files. Commit: `chore: complete v{version} milestone`. Create annotated tag: `git tag -a v{version} -m "v{version} [Name] ..."`. Ask about pushing tag to remote.

8. **Offer next steps** — Display completion summary and prompt: use the `gsd-new-milestone` skill to start the next milestone.

See `rules/workflow.md` for the complete step-by-step instructions, command examples, template formats, and mode-aware gates.

## Reference Files

Detailed workflow steps are in this skill's directory:
- `rules/workflow.md` — complete step-by-step milestone completion workflow (archive, tag, next steps)

</process>

<success_criteria>

- Milestone archived to `.planning/milestones/v{version}-ROADMAP.md`
- Requirements archived to `.planning/milestones/v{version}-REQUIREMENTS.md`
- `.planning/REQUIREMENTS.md` deleted (fresh for next milestone)
- ROADMAP.md reorganized with milestone grouping
- PROJECT.md full evolution review completed
- All shipped requirements moved to Validated in PROJECT.md
- MILESTONES.md entry created with stats and accomplishments
- Key Decisions updated with outcomes
- Git tag v{version} created
- Commit successful
- User knows next steps (use gsd-new-milestone to start next milestone)

</success_criteria>

<critical_rules>

- **Verify completion first:** All phases must have SUMMARY.md files before archiving
- **User confirmation:** Wait for approval at verification gates (unless in yolo mode)
- **Archive before deleting:** Always create archive files before updating or deleting originals
- **One-line summary:** Collapsed milestone in ROADMAP.md should be a single line with link
- **Fresh requirements:** Next milestone starts with gsd-new-milestone which includes requirements definition
- **Known gaps:** If user proceeds with incomplete requirements, record them in MILESTONES.md under Known Gaps

</critical_rules>
