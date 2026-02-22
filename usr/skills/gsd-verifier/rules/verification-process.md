# Verification Process: Steps 1-10

Detailed step-by-step procedure for the gsd-verifier skill. Load this file via `skills_tool` before beginning verification.

---

## Step 0: Check for Previous Verification

Use `code_execution_tool` to check:

```bash
ls "$PHASE_DIR"/*-VERIFICATION.md 2>/dev/null
```

**If previous verification exists with a `gaps:` section — RE-VERIFICATION MODE:**

1. Read the previous VERIFICATION.md via `code_execution_tool` (`cat "$PHASE_DIR"/*-VERIFICATION.md`)
2. Parse the YAML frontmatter section between the `---` fences
3. Extract `must_haves` (truths, artifacts, key_links)
4. Extract `gaps` (items that failed)
5. Set `is_re_verification = true`
6. **Skip to Step 3** with optimization:
   - **Failed items:** Full 3-level verification (exists, substantive, wired)
   - **Passed items:** Quick regression check (existence + basic sanity only)

**If no previous verification OR no `gaps:` section — INITIAL MODE:**

Set `is_re_verification = false`, proceed with Step 1.

---

## Step 1: Load Context (Initial Mode Only)

Use `code_execution_tool` to gather context:

```bash
ls "$PHASE_DIR"/*-PLAN.md 2>/dev/null
ls "$PHASE_DIR"/*-SUMMARY.md 2>/dev/null
```

Read the ROADMAP.md via `code_execution_tool` (`cat .planning/ROADMAP.md`) and locate the `### Phase {PHASE_NUM}:` header. Extract the phase goal — this is the outcome to verify, not the tasks.

Also read REQUIREMENTS.md via `code_execution_tool`:

```bash
grep -E "Phase $PHASE_NUM" .planning/REQUIREMENTS.md 2>/dev/null
```

---

## Step 2: Establish Must-Haves (Initial Mode Only)

In re-verification mode, must-haves come from Step 0.

**Option A: Must-haves in PLAN frontmatter**

```bash
grep -l "must_haves:" "$PHASE_DIR"/*-PLAN.md 2>/dev/null
```

If found, read each PLAN.md that has `must_haves:` and parse the YAML section between the opening `---` fences. Extract:
- `must_haves.truths` — list of observable, testable behaviors
- `must_haves.artifacts` — list of `{ path, provides, min_lines }` objects
- `must_haves.key_links` — list of `{ from, to, via, pattern }` objects

**Option B: Use Success Criteria from ROADMAP.md**

If no must_haves in frontmatter, read ROADMAP.md and find the `### Phase {PHASE_NUM}:` section. Parse the `**Success Criteria**` subsection. If non-empty:
1. Use each success criterion directly as a truth
2. Derive artifacts for each truth — ask "What must EXIST?" and map to concrete file paths
3. Derive key links for each artifact — ask "What must be CONNECTED?"
4. Document must-haves before proceeding

**Option C: Derive from phase goal (fallback)**

If no must_haves in frontmatter AND no Success Criteria:
1. Extract the goal from ROADMAP.md
2. Derive truths: "What must be TRUE?" — list 3-7 observable, testable behaviors
3. Derive artifacts for each truth
4. Derive key links for each artifact
5. Document derived must-haves before proceeding

---

## Step 3: Verify Observable Truths

For each truth, determine if the codebase enables it.

**Verification status:**
- `VERIFIED`: All supporting artifacts pass all checks
- `FAILED`: One or more artifacts missing, stub, or unwired
- `UNCERTAIN`: Can't verify programmatically (needs human)

For each truth:
1. Identify supporting artifacts
2. Check artifact status (Step 4)
3. Check wiring status (Step 5)
4. Determine truth status

---

## Step 4: Verify Artifacts (Three Levels)

**Checking artifacts from must_haves.artifacts:**

For each artifact in the list, use `code_execution_tool` to:

1. **Level 1 — Existence check:**
   ```bash
   [ -f "path/to/artifact" ] && echo "EXISTS" || echo "MISSING"
   ```

2. **Level 2 — Substantive check (not a stub):**
   ```bash
   wc -l "path/to/artifact"
   grep -n "export\|function\|class\|const.*=\|return" "path/to/artifact" | head -10
   ```
   Compare line count against `min_lines` from the artifact spec. Check that the file has real implementation patterns, not just placeholder content or `return null`/`return []`.

3. **Level 3 — Wiring check (imported and used):**
   ```bash
   # Import check
   grep -r "import.*ArtifactName" src/ --include="*.ts" --include="*.tsx" 2>/dev/null | wc -l

   # Usage check (beyond imports)
   grep -r "ArtifactName" src/ --include="*.ts" --include="*.tsx" 2>/dev/null | grep -v "import" | wc -l
   ```

**Artifact status mapping:**

| Exists | Substantive | Wired | Status |
| ------ | ----------- | ----- | ------ |
| Yes | Yes | Yes | VERIFIED |
| Yes | Yes | No | ORPHANED |
| Yes | No | - | STUB |
| No | - | - | MISSING |

---

## Step 5: Verify Key Links (Wiring)

Key links are critical connections. If broken, the goal fails even with all artifacts present.

**Checking key links from must_haves.key_links:**

For each key link with `{ from, to, via, pattern }`, use `code_execution_tool`:

```bash
grep -n "pattern" "from_file_path" 2>/dev/null
```

If `pattern` matches content found in `from`, the link is WIRED. If the grep returns nothing, the link is NOT_WIRED.

**Fallback patterns (if must_haves.key_links not defined):**

Component → API:
```bash
grep -E "fetch\(['\"].*api_path|axios\.(get|post).*api_path" "$component" 2>/dev/null
```

API → Database:
```bash
grep -E "prisma\.$model|db\.$model|$model\.(find|create|update|delete)" "$route" 2>/dev/null
grep -E "return.*json.*\w+|res\.json\(\w+" "$route" 2>/dev/null
```

Form → Handler:
```bash
grep -E "onSubmit=\{|handleSubmit" "$component" 2>/dev/null
grep -A 10 "onSubmit.*=" "$component" | grep -E "fetch|axios|mutate|dispatch" 2>/dev/null
```

State → Render:
```bash
grep -E "useState.*state_var|\[state_var," "$component" 2>/dev/null
grep -E "\{.*state_var.*\}|\{state_var\." "$component" 2>/dev/null
```

---

## Step 6: Check Requirements Coverage

**6a. Extract requirement IDs from PLAN frontmatter:**

```bash
grep -A5 "^requirements:" "$PHASE_DIR"/*-PLAN.md 2>/dev/null
```

Collect all requirement IDs declared across plans for this phase.

**6b. Cross-reference against REQUIREMENTS.md:**

For each requirement ID, use `code_execution_tool`:
```bash
grep -n "REQ-ID\|REQUIREMENT-ID" .planning/REQUIREMENTS.md 2>/dev/null
```

Find the requirement's full description and map it to supporting truths/artifacts verified in Steps 3-5. Determine status:
- `SATISFIED`: Implementation evidence found that fulfills the requirement
- `BLOCKED`: No evidence or contradicting evidence
- `NEEDS_HUMAN`: Can't verify programmatically (UI behavior, UX quality)

**6c. Check for orphaned requirements:**

```bash
grep -E "Phase $PHASE_NUM" .planning/REQUIREMENTS.md 2>/dev/null
```

If REQUIREMENTS.md maps additional IDs to this phase that don't appear in ANY plan's `requirements` field, flag as ORPHANED. These must appear in the verification report.

---

## Step 7: Scan for Anti-Patterns

Identify files modified in this phase from SUMMARY.md key-files section. If not available:

```bash
grep -E "^\- \`" "$PHASE_DIR"/*-SUMMARY.md | sed 's/.*`\([^`]*\)`.*/\1/' | sort -u
```

For each file, use `code_execution_tool` to run anti-pattern detection:

```bash
# TODO/FIXME/placeholder comments
grep -n -E "TODO|FIXME|XXX|HACK|PLACEHOLDER" "$file" 2>/dev/null
grep -n -E "placeholder|coming soon|will be here" "$file" -i 2>/dev/null

# Empty implementations
grep -n -E "return null|return \{\}|return \[\]|=> \{\}" "$file" 2>/dev/null

# Console.log only implementations
grep -n -B 2 -A 2 "console\.log" "$file" 2>/dev/null | grep -E "^\s*(const|function|=>)"
```

Categorize findings:
- Blocker (prevents goal achievement)
- Warning (incomplete but not blocking)
- Info (notable but acceptable)

---

## Step 8: Identify Human Verification Needs

**Always needs human:** Visual appearance, user flow completion, real-time behavior, external service integration, performance feel, error message clarity.

**Needs human if uncertain:** Complex wiring that grep can't trace, dynamic state behavior, edge cases.

Format each human verification item:

```markdown
### 1. {Test Name}

**Test:** {What to do}
**Expected:** {What should happen}
**Why human:** {Why can't verify programmatically}
```

---

## Step 9: Determine Overall Status

- **passed** — All truths VERIFIED, all artifacts pass all three levels, all key links WIRED, no blocker anti-patterns
- **gaps_found** — One or more truths FAILED, artifacts MISSING/STUB, key links NOT_WIRED, or blocker anti-patterns found
- **human_needed** — All automated checks pass but items flagged for human verification

**Score:** `verified_truths / total_truths`

---

## Step 10: Structure Gap Output (If Gaps Found)

Structure gaps in YAML frontmatter for the `gsd-plan-phase` skill (when called with gap-closure mode):

```yaml
gaps:
  - truth: "Observable truth that failed"
    status: failed
    reason: "Brief explanation"
    artifacts:
      - path: "src/path/to/file.tsx"
        issue: "What's wrong"
    missing:
      - "Specific thing to add/fix"
```

Fields:
- `truth`: The observable truth that failed
- `status`: failed or partial
- `reason`: Brief explanation
- `artifacts`: Files with issues
- `missing`: Specific things to add or fix

**Group related gaps by concern** — if multiple truths fail from the same root cause, note this to help the planner create focused plans.

---

## VERIFICATION.md Output Structure

After completing all steps, write the report to `.planning/phases/{phase_dir}/{phase_num}-VERIFICATION.md`:

```markdown
---
phase: XX-name
verified: YYYY-MM-DDTHH:MM:SSZ
status: passed | gaps_found | human_needed
score: N/M must-haves verified
re_verification: # Only if previous VERIFICATION.md existed
  previous_status: gaps_found
  previous_score: 2/5
  gaps_closed:
    - "Truth that was fixed"
  gaps_remaining: []
  regressions: []
gaps: # Only if status: gaps_found
  - truth: "Observable truth that failed"
    status: failed
    reason: "Why it failed"
    artifacts:
      - path: "src/path/to/file.tsx"
        issue: "What's wrong"
    missing:
      - "Specific thing to add/fix"
human_verification: # Only if status: human_needed
  - test: "What to do"
    expected: "What should happen"
    why_human: "Why can't verify programmatically"
---

# Phase {X}: {Name} Verification Report

**Phase Goal:** {goal from ROADMAP.md}
**Verified:** {timestamp}
**Status:** {status}
**Re-verification:** {Yes — after gap closure | No — initial verification}

## Goal Achievement

### Observable Truths

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1   | {truth} | VERIFIED   | {evidence}     |
| 2   | {truth} | FAILED     | {what's wrong} |

**Score:** {N}/{M} truths verified

### Required Artifacts

| Artifact | Expected    | Status | Details |
| -------- | ----------- | ------ | ------- |
| `path`   | description | status | details |

### Key Link Verification

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |

### Human Verification Required

{Items needing human testing}

### Gaps Summary

{Narrative summary of what is missing and why}

---

_Verified: {timestamp}_
_Verifier: Claude (gsd-verifier)_
```
