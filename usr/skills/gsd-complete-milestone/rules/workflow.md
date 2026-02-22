# gsd-complete-milestone: Full Workflow

This file contains the complete step-by-step workflow for milestone completion.
Referenced by `SKILL.md` — load this file when executing the detailed steps.

---

## Step 1: Verify Readiness

Run a comprehensive readiness check by reading ROADMAP.md and all phase directories:

```bash
# Check phase completion status
ls .planning/phases/
for dir in .planning/phases/*/; do
  echo "Phase: $dir"
  ls "$dir"*-SUMMARY.md 2>/dev/null && echo "  COMPLETE" || echo "  INCOMPLETE (missing SUMMARY.md)"
done
```

Verify:
- Which phases belong to this milestone?
- All phases complete (all plans have summaries)?
- Progress is 100%.

**Requirements completion check (REQUIRED before presenting):**

Read REQUIREMENTS.md traceability table:
- Count total requirements vs checked-off (`[x]`) requirements
- Identify any non-Complete rows in the traceability table

Present:

    Milestone: [Name, e.g., "v1.0 MVP"]

    Includes:
    - Phase 1: Foundation (2/2 plans complete)
    - Phase 2: Authentication (2/2 plans complete)
    - Phase 3: Core Features (3/3 plans complete)

    Total: {phase_count} phases, {total_plans} plans, all complete
    Requirements: {N}/{M} requirements checked off

**If requirements incomplete** (N < M):

    Unchecked Requirements:
    - [ ] {REQ-ID}: {description} (Phase {X})
    - [ ] {REQ-ID}: {description} (Phase {Y})

Present 3 options:
1. **Proceed anyway** — mark milestone complete with known gaps
2. **Run audit first** — use gsd-audit-milestone skill to assess gap severity
3. **Abort** — return to development

If user selects "Proceed anyway": note incomplete requirements in MILESTONES.md under `### Known Gaps`.

**Mode-aware gate:**

In yolo mode (`.planning/config.json` has `"mode": "yolo"`):
- Auto-approve milestone scope verification
- Show breakdown summary without prompting
- Proceed to gather_stats

In interactive mode:
- Show: "Ready to mark this milestone as shipped? (yes / wait / adjust scope)"
- Wait for confirmation. "adjust scope": Ask which phases to include. "wait": Stop.

---

## Step 2: Gather Stats

Calculate milestone statistics:

```bash
git log --oneline --grep="feat(" | head -20
git diff --stat HEAD | tail -1
git log --format="%ai" | tail -1
git log --format="%ai" | head -1
```

Present:

    Milestone Stats:
    - Phases: [X-Y]
    - Plans: [Z] total
    - Tasks: [N] total (from phase summaries)
    - Files modified: [M]
    - Timeline: [Days] days ([Start] -> [End])
    - Git range: feat(XX-XX) -> feat(YY-YY)

---

## Step 3: Extract Accomplishments

Read all phase SUMMARY.md files in the milestone range:

```bash
cat .planning/phases/*-*/*-SUMMARY.md
```

Extract 4-6 key accomplishments from the one-liner fields and deliverables sections. Present:

    Key accomplishments for this milestone:
    1. [Achievement from phase 1]
    2. [Achievement from phase 2]
    3. [Achievement from phase 3]
    4. [Achievement from phase 4]

---

## Step 4: Archive Milestone

Create the milestones directory and archive files:

```bash
mkdir -p .planning/milestones
```

**Create `.planning/milestones/v{version}-ROADMAP.md`:**

Include: milestone header (status, phases, date), full phase details, milestone summary (decisions, issues, tech debt).

The archive document structure follows the milestone-archive.md template (in the GSD installation templates/ directory), which defines sections for: milestone header with status and shipped date, phases list with plan checkboxes, milestone summary with key decisions, issues resolved, issues deferred, and technical debt incurred.

**Create `.planning/milestones/v{version}-REQUIREMENTS.md`:**

Copy REQUIREMENTS.md and add archive header. Mark all requirements as complete (checkboxes checked). Note requirement outcomes (validated, adjusted, dropped).

**Update MILESTONES.md** (create if not exists):

Append entry with: version, date, phase/plan/task counts, key accomplishments.

**Verify:** `ls .planning/milestones/` shows the two archived files.

**Phase archival (optional):** After archival, ask the user:
- "Yes — move to milestones/v{version}-phases/"
- "Skip — keep phases in place"

If "Yes":
```bash
mkdir -p .planning/milestones/v{version}-phases
# Move each phase directory:
mv .planning/phases/{phase-dir} .planning/milestones/v{version}-phases/
```

---

## Step 5: Full PROJECT.md Evolution Review

Read all phase summaries, then perform a full review of PROJECT.md:

```bash
cat .planning/phases/*-*/*-SUMMARY.md
cat .planning/PROJECT.md
```

**Full review checklist:**

1. **"What This Is" accuracy:**
   - Compare current description to what was built
   - Update if product has meaningfully changed

2. **Core Value check:**
   - Still the right priority? Did shipping reveal a different core value?
   - Update if the ONE thing has shifted

3. **Requirements audit:**

   Validated section:
   - All Active requirements shipped this milestone: move to Validated
   - Format: `- {requirement} — v{version}`

   Active section:
   - Remove requirements moved to Validated
   - Add new requirements for next milestone
   - Keep unaddressed requirements

   Out of Scope audit:
   - Review each item — reasoning still valid?
   - Remove irrelevant items
   - Add requirements invalidated during milestone

4. **Context update:**
   - Current codebase state (LOC, tech stack)
   - User feedback themes (if any)
   - Known issues or technical debt

5. **Key Decisions audit:**
   - Extract all decisions from milestone phase summaries
   - Add to Key Decisions table with outcomes
   - Mark as: Good, Revisit, or Pending

6. **Constraints check:**
   - Any constraints changed during development? Update as needed.

Update PROJECT.md inline. Update "Last updated" footer:

    ---
    *Last updated: [date] after v{version} milestone*

---

## Step 6: Reorganize ROADMAP.md and Delete Originals

Update `.planning/ROADMAP.md` — group completed milestone phases:

    # Roadmap: [Project Name]

    ## Milestones

    - [v1.0 MVP] — Phases 1-4 (shipped YYYY-MM-DD)
    - [v1.1 Security] — Phases 5-6 (in progress)

    ## Phases

    v1.0 MVP (Phases 1-4) — SHIPPED YYYY-MM-DD

    - [x] Phase 1: Foundation (2/2 plans) — completed YYYY-MM-DD
    - [x] Phase 2: Authentication (2/2 plans) — completed YYYY-MM-DD
    - [x] Phase 3: Core Features (3/3 plans) — completed YYYY-MM-DD
    - [x] Phase 4: Polish (1/1 plan) — completed YYYY-MM-DD

    ### v{Next} [Name] (In Progress / Planned)

    - [ ] Phase 5: [Name] ([N] plans)

    ## Progress

    | Phase             | Milestone | Plans Complete | Status      | Completed  |
    | ----------------- | --------- | -------------- | ----------- | ---------- |
    | 1. Foundation     | v1.0      | 2/2            | Complete    | YYYY-MM-DD |
    | 5. Security Audit | v1.1      | 0/1            | Not started | -          |

Then delete originals:

```bash
rm .planning/REQUIREMENTS.md
```

Note: ROADMAP.md is reorganized in place (not deleted).

---

## Step 7: Update STATE.md

Verify and update remaining STATE.md fields after archival:

**Project Reference:**

    ## Project Reference

    See: .planning/PROJECT.md (updated [today])

    **Core value:** [Current core value from PROJECT.md]
    **Current focus:** [Next milestone or "Planning next milestone"]

**Accumulated Context:**
- Clear decisions summary (full log in PROJECT.md)
- Clear resolved blockers
- Keep open blockers for next milestone

---

## Step 8: Git Tag and Commit

Create git tag:

```bash
git tag -a v{version} -m "v{version} [Name]

Delivered: [One sentence]

Key accomplishments:
- [Item 1]
- [Item 2]
- [Item 3]

See .planning/MILESTONES.md for full details."
```

Confirm: "Tagged: v{version}"

Ask: "Push tag to remote? (y/n)"

If yes:
```bash
git push origin v{version}
```

Commit milestone completion:

```bash
git add .planning/milestones/v{version}-ROADMAP.md
git add .planning/milestones/v{version}-REQUIREMENTS.md
git add .planning/MILESTONES.md
git add .planning/PROJECT.md
git add .planning/STATE.md
git commit -m "chore: complete v{version} milestone"
```

---

## Step 9: Offer Next Steps

    Milestone v{version} [Name] complete

    Shipped:
    - [N] phases ([M] plans, [P] tasks)
    - [One sentence of what shipped]

    Archived:
    - milestones/v{version}-ROADMAP.md
    - milestones/v{version}-REQUIREMENTS.md

    Summary: .planning/MILESTONES.md
    Tag: v{version}

    * * *

    ## Next Up

    Start Next Milestone — questioning -> research -> requirements -> roadmap

    Use the `gsd-new-milestone` skill

    (`/clear` first for a fresh context window)

    * * *

---

## Milestone Naming Conventions

**Version conventions:**
- `v1.0` — Initial MVP
- `v1.1`, `v1.2` — Minor updates, new features, fixes
- `v2.0`, `v3.0` — Major rewrites, breaking changes, new direction

**Names:** Short 1-2 words (v1.0 MVP, v1.1 Security, v1.2 Performance, v2.0 Redesign).

**What qualifies for a milestone:**
- Initial release, public releases, major feature sets shipped, before archiving planning

**What does NOT qualify:**
- Every phase completion (too granular), work in progress, internal dev iterations
- Heuristic: "Is this deployed/usable/shipped?" Yes = milestone. No = keep working.
