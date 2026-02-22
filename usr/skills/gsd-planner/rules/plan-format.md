# Plan Format

The PLAN.md structure template and all frontmatter fields.

## PLAN.md Structure

```markdown
---
phase: XX-name
plan: NN
type: execute
wave: N                     # Execution wave (1, 2, 3...)
depends_on: []              # Plan IDs this plan requires
files_modified: []          # Files this plan touches
autonomous: true            # false if plan has checkpoints
requirements: []            # REQUIRED — Requirement IDs from ROADMAP. MUST NOT be empty.
user_setup: []              # Human-required setup (omit if empty)

must_haves:
  truths: []                # Observable behaviors
  artifacts: []             # Files that must exist
  key_links: []             # Critical connections
---

<objective>
[What this plan accomplishes]

Purpose: [Why this matters]
Output: [Artifacts created]
</objective>

<execution_context>
Plans must include an execution_context section that references:
1. The GSD execute-plan workflow — a reference guide for executing plan tasks step-by-step
2. The GSD summary template — defines the SUMMARY.md output format for completed plans

In a Claude Code environment, these are referenced as @-file paths. In Agent Zero,
describe in prose what context the executor needs: the execute-plan workflow governs how
tasks are committed atomically, deviations are handled, and checkpoints are returned;
the summary template defines what sections SUMMARY.md must contain.
</execution_context>

<context>
[Reference the planning files the executor needs to read]
- .planning/PROJECT.md (project context)
- .planning/ROADMAP.md (phase requirements)
- .planning/STATE.md (current position and decisions)

[Only include prior plan SUMMARY references if genuinely needed]
[path/to/relevant/source.ts — if task touches an existing file worth reading]
</context>

<tasks>

<task type="auto">
  <name>Task 1: [Action-oriented name]</name>
  <files>path/to/file.ext</files>
  <action>[Specific implementation]</action>
  <verify>[Command or check]</verify>
  <done>[Acceptance criteria]</done>
</task>

</tasks>

<verification>
[Overall phase checks]
</verification>

<success_criteria>
[Measurable completion]
</success_criteria>

<output>
After completion, create `.planning/phases/XX-name/{phase}-{plan}-SUMMARY.md`
</output>
```

## Frontmatter Fields

| Field | Required | Purpose |
|-------|----------|---------|
| `phase` | Yes | Phase identifier (e.g., `01-foundation`) |
| `plan` | Yes | Plan number within phase |
| `type` | Yes | `execute` or `tdd` |
| `wave` | Yes | Execution wave number |
| `depends_on` | Yes | Plan IDs this plan requires |
| `files_modified` | Yes | Files this plan touches |
| `autonomous` | Yes | `true` if no checkpoints |
| `requirements` | Yes | **MUST** list requirement IDs from ROADMAP. Every roadmap requirement ID MUST appear in at least one plan. |
| `user_setup` | No | Human-required setup items |
| `must_haves` | Yes | Goal-backward verification criteria |

Wave numbers are pre-computed during planning. Execute-phase reads `wave` directly from frontmatter.

## Context Section Rules

Only include prior plan SUMMARY references if genuinely needed (uses types/exports from prior plan, or prior plan made decision affecting this one).

**Anti-pattern:** Reflexive chaining (02 refs 01, 03 refs 02...). Independent plans need NO prior SUMMARY references.

## User Setup Frontmatter

When external services involved:

```yaml
user_setup:
  - service: stripe
    why: "Payment processing"
    env_vars:
      - name: STRIPE_SECRET_KEY
        source: "Stripe Dashboard -> Developers -> API keys"
    dashboard_config:
      - task: "Create webhook endpoint"
        location: "Stripe Dashboard -> Developers -> Webhooks"
```

Only include what Claude literally cannot do.

## TDD Plan Structure

TDD candidates get dedicated plans (type: tdd). One feature per TDD plan.

```markdown
---
phase: XX-name
plan: NN
type: tdd
---

<objective>
[What feature and why]
Purpose: [Design benefit of TDD for this feature]
Output: [Working, tested feature]
</objective>

<feature>
  <name>[Feature name]</name>
  <files>[source file, test file]</files>
  <behavior>
    [Expected behavior in testable terms]
    Cases: input -> expected output
  </behavior>
  <implementation>[How to implement once tests pass]</implementation>
</feature>
```

**Red-Green-Refactor Cycle:**
- **RED:** Create test file → write failing test → run (MUST fail) → commit: `test({phase}-{plan}): add failing test for [feature]`
- **GREEN:** Write minimal code to pass → run (MUST pass) → commit: `feat({phase}-{plan}): implement [feature]`
- **REFACTOR:** Clean up → run tests (MUST pass) → commit: `refactor({phase}-{plan}): clean up [feature]`

TDD plans target ~40% context (lower than standard 50%) due to the RED→GREEN→REFACTOR back-and-forth.

## Plan Validation

For each created PLAN.md, verify:

Required plan frontmatter fields:
- `phase`, `plan`, `type`, `wave`, `depends_on`, `files_modified`, `autonomous`, `must_haves`

Required plan structure elements (parse XML):
- Each `<task>` must have: `<name>`, `<files>` (for auto tasks), `<action>`, `<verify>`, `<done>`
- If `autonomous: false` → plan must have at least one checkpoint task
- Checkpoint task + implementation tasks → `autonomous: false`

**If errors exist:** Fix before committing.
