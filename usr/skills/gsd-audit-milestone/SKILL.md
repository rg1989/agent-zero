---
name: gsd-audit-milestone
description: Audit milestone completion against original intent before archiving
allowed-tools:
  - code_execution_tool
  - call_subordinate
---

<objective>
Verify milestone achieved its definition of done. Check requirements coverage, cross-phase integration, and end-to-end flows.

This skill IS the orchestrator. Reads existing VERIFICATION.md files (phases already verified during execute-phase), aggregates tech debt and deferred gaps, then spawns an integration checker for cross-phase wiring.
</objective>

<context>
Version: the optional milestone version provided by the user (defaults to current milestone if not provided)

Core planning files are resolved in-workflow and loaded only as needed.

Completed Work:
- `.planning/phases/*/*-SUMMARY.md`
- `.planning/phases/*/*-VERIFICATION.md`
</context>

<process>

## 0. Initialize Milestone Context

Load milestone context by reading `.planning/ROADMAP.md` to identify the current milestone version, name, phase count, and completed phases. Also determine whether planning docs should be committed.

Additionally, read the project config to resolve which model to use for the integration checker.

## 1. Determine Milestone Scope

Using the phases list from the roadmap:

- Parse version from the user-provided argument or detect current version from ROADMAP.md
- Identify all phase directories in scope
- Extract milestone definition of done from ROADMAP.md
- Extract requirements mapped to this milestone from REQUIREMENTS.md

## 2. Read All Phase Verifications

For each phase directory, read the VERIFICATION.md file. Use find-phase logic to resolve the correct directory (handles archived phases by checking both active and archived locations).

From each VERIFICATION.md, extract:
- **Status:** passed | gaps_found
- **Critical gaps:** (if any — these are blockers)
- **Non-critical gaps:** tech debt, deferred items, warnings
- **Anti-patterns found:** TODOs, stubs, placeholders
- **Requirements coverage:** which requirements satisfied/blocked

If a phase is missing VERIFICATION.md, flag it as "unverified phase" — this is a blocker.

## 3. Spawn Integration Checker

With phase context collected, extract `MILESTONE_REQ_IDS` from REQUIREMENTS.md traceability table — all REQ-IDs assigned to phases in this milestone.

Use `call_subordinate` to delegate cross-phase integration checking:
- **message**: Include the subordinate's full role identity as an integration checker specialist. Provide: the list of phase directories, phase exports from SUMMARY files, API routes created, and the full list of milestone requirement IDs with descriptions and assigned phases. Instruct the subordinate to verify cross-phase wiring and E2E user flows, and to map each integration finding to affected requirement IDs where applicable. Request a structured report.
- **reset**: `"true"` for a new integration check

## 4. Collect Results

Combine:
- Phase-level gaps and tech debt (from step 2)
- Integration checker's report (wiring gaps, broken flows)

## 5. Check Requirements Coverage (3-Source Cross-Reference)

MUST cross-reference three independent sources for each requirement:

### 5a. Parse REQUIREMENTS.md Traceability Table

Extract all REQ-IDs mapped to milestone phases from the traceability table:
- Requirement ID, description, assigned phase, current status, checked-off state (`[x]` vs `[ ]`)

### 5b. Parse Phase VERIFICATION.md Requirements Tables

For each phase's VERIFICATION.md, extract the expanded requirements table:
- Requirement | Source Plan | Description | Status | Evidence
- Map each entry back to its REQ-ID

### 5c. Extract SUMMARY.md Frontmatter Cross-Check

For each phase's SUMMARY.md, read the frontmatter and extract the `requirements-completed` field. This provides a third independent data source for cross-reference.

### 5d. Status Determination Matrix

For each REQ-ID, determine status using all three sources:

| VERIFICATION.md Status | SUMMARY Frontmatter | REQUIREMENTS.md | Final Status |
|------------------------|---------------------|-----------------|--------------|
| passed                 | listed              | `[x]`           | **satisfied**  |
| passed                 | listed              | `[ ]`           | **satisfied** (update checkbox) |
| passed                 | missing             | any             | **partial** (verify manually) |
| gaps_found             | any                 | any             | **unsatisfied** |
| missing                | listed              | any             | **partial** (verification gap) |
| missing                | missing             | any             | **unsatisfied** |

### 5e. FAIL Gate and Orphan Detection

**REQUIRED:** Any `unsatisfied` requirement MUST force `gaps_found` status on the milestone audit.

**Orphan detection:** Requirements present in REQUIREMENTS.md traceability table but absent from ALL phase VERIFICATION.md files MUST be flagged as orphaned. Orphaned requirements are treated as `unsatisfied` — they were assigned but never verified by any phase.

## 6. Aggregate into MILESTONE-AUDIT.md

Create `.planning/v{version}-MILESTONE-AUDIT.md` with YAML frontmatter:

```
(frontmatter)
milestone: {version}
audited: {timestamp}
status: passed | gaps_found | tech_debt
scores:
  requirements: N/M
  phases: N/M
  integration: N/M
  flows: N/M
gaps:
  requirements:
    - id: "{REQ-ID}"
      status: "unsatisfied | partial | orphaned"
      phase: "{assigned phase}"
      claimed_by_plans: ["{plan files that reference this requirement}"]
      completed_by_plans: ["{plan files whose SUMMARY marks it complete}"]
      verification_status: "passed | gaps_found | missing | orphaned"
      evidence: "{specific evidence or lack thereof}"
  integration: [...]
  flows: [...]
tech_debt:
  - phase: 01-auth
    items:
      - "TODO: add rate limiting"
(end frontmatter)
```

Plus full markdown report with tables for requirements, phases, integration, tech debt.

**Status values:**
- `passed` — all requirements met, no critical gaps, minimal tech debt
- `gaps_found` — critical blockers exist
- `tech_debt` — no blockers but accumulated deferred items need review

## 7. Present Results

Route by status per the `<offer_next>` section.

</process>

<offer_next>
Output this markdown directly (not as a code block). Route based on status:

**If passed:**

## Milestone {version} — Audit Passed

**Score:** {N}/{M} requirements satisfied
**Report:** .planning/v{version}-MILESTONE-AUDIT.md

All requirements covered. Cross-phase integration verified. E2E flows complete.

**Next Up:** Use the `gsd-complete-milestone` skill — archive and tag

* * *

**If gaps_found:**

## Milestone {version} — Gaps Found

**Score:** {N}/{M} requirements satisfied
**Report:** .planning/v{version}-MILESTONE-AUDIT.md

### Unsatisfied Requirements

{For each unsatisfied requirement:}
- **{REQ-ID}: {description}** (Phase {X})
  - {reason}

### Cross-Phase Issues

{For each integration gap:}
- **{from} → {to}:** {issue}

### Broken Flows

{For each flow gap:}
- **{flow name}:** breaks at {step}

**Next Up:** Use the `gsd-plan-milestone-gaps` skill — create phases to complete milestone

**Also available:** Use the `gsd-complete-milestone` skill — proceed anyway (accept tech debt)

* * *

**If tech_debt (no blockers but accumulated debt):**

## Milestone {version} — Tech Debt Review

**Score:** {N}/{M} requirements satisfied
**Report:** .planning/v{version}-MILESTONE-AUDIT.md

All requirements met. No critical blockers. Accumulated tech debt needs review.

### Tech Debt by Phase

{For each phase with debt:}
**Phase {X}: {name}**
- {item 1}
- {item 2}

### Total: {N} items across {M} phases

**Options:**
- A. Use `gsd-complete-milestone` — accept debt, track in backlog
- B. Use `gsd-plan-milestone-gaps` — address debt before completing
</offer_next>

<success_criteria>
- [ ] Milestone scope identified
- [ ] All phase VERIFICATION.md files read
- [ ] SUMMARY.md `requirements-completed` frontmatter extracted for each phase
- [ ] REQUIREMENTS.md traceability table parsed for all milestone REQ-IDs
- [ ] 3-source cross-reference completed (VERIFICATION + SUMMARY + traceability)
- [ ] Orphaned requirements detected (in traceability but absent from all VERIFICATIONs)
- [ ] Tech debt and deferred gaps aggregated
- [ ] Integration checker spawned with milestone requirement IDs
- [ ] v{version}-MILESTONE-AUDIT.md created with structured requirement gap objects
- [ ] FAIL gate enforced — any unsatisfied requirement forces gaps_found status
- [ ] Results presented with actionable next steps
</success_criteria>
