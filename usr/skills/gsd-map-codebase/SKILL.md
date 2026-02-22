---
name: gsd-map-codebase
description: Analyze codebase with parallel mapper agents to produce .planning/codebase/ documents covering tech stack, architecture, conventions, and concerns
allowed-tools:
  - code_execution_tool
  - call_subordinate
---

<objective>
Analyze existing codebase using parallel gsd-codebase-mapper agents to produce structured codebase documents.

Each mapper agent explores a focus area and **writes documents directly** to `.planning/codebase/`. The orchestrator only receives confirmations, keeping context usage minimal.

Output: .planning/codebase/ folder with 7 structured documents about the codebase state.
</objective>

<context>
Focus area: the optional focus area provided by the user (e.g., 'api' or 'auth') — if provided, tells agents to focus on specific subsystem.

**Load project state if exists:**
Check for `.planning/STATE.md` — loads context if project already initialized.

**This skill can run:**
- Before running gsd-new-project (brownfield codebases) — creates codebase map first
- After running gsd-new-project (greenfield codebases) — updates codebase map as code evolves
- Anytime to refresh codebase understanding
</context>

<when_to_use>
**Use gsd-map-codebase for:**
- Brownfield projects before initialization (understand existing code first)
- Refreshing codebase map after significant changes
- Onboarding to an unfamiliar codebase
- Before major refactoring (understand current state)
- When STATE.md references outdated codebase info

**Skip gsd-map-codebase for:**
- Greenfield projects with no code yet (nothing to map)
- Trivial codebases (fewer than 5 files)
</when_to_use>

<philosophy>
**Why dedicated mapper agents:**
- Fresh context per domain (no token contamination)
- Agents write documents directly (no context transfer back to orchestrator)
- Orchestrator only summarizes what was created (minimal context usage)
- Faster execution (agents run simultaneously)

**Document quality over length:**
Include enough detail to be useful as reference. Prioritize practical examples (especially code patterns) over arbitrary brevity.

**Always include file paths:**
Documents are reference material for planning/execution. Always include actual file paths formatted with backticks: `src/services/user.ts`.
</philosophy>

<process>

<step name="init_context" priority="first">
Load codebase mapping context by reading `.planning/STATE.md` and `.planning/config.json`.

Extract: `mapper_model`, `commit_docs`, existing maps status, codebase_dir_exists.
</step>

<step name="check_existing">
Check if `.planning/codebase/` already exists.

If `.planning/codebase/` exists:

```bash
ls -la .planning/codebase/
```

Present options:

```
.planning/codebase/ already exists with these documents:
[List files found]

What's next?
1. Refresh - Delete existing and remap codebase
2. Update - Keep existing, only update specific documents
3. Skip - Use existing codebase map as-is
```

Wait for user response via `input`.

If "Refresh": Delete `.planning/codebase/`, continue to create_structure.
If "Update": Ask which documents to update, continue to spawn_agents (filtered).
If "Skip": Exit workflow.

**If doesn't exist:**
Continue to create_structure.
</step>

<step name="create_structure">
Create `.planning/codebase/` directory:

```bash
mkdir -p .planning/codebase
```

**Expected output files:**
- STACK.md (from tech mapper)
- INTEGRATIONS.md (from tech mapper)
- ARCHITECTURE.md (from arch mapper)
- STRUCTURE.md (from arch mapper)
- CONVENTIONS.md (from quality mapper)
- TESTING.md (from quality mapper)
- CONCERNS.md (from concerns mapper)

Continue to spawn_agents.
</step>

<step name="spawn_agents">
## Spawn Parallel Codebase Mapper Subagents

Use `call_subordinate` to spawn 4 parallel mapper agents (one per focus area).
Each agent writes its documents directly to `.planning/codebase/`.

**Agent 1 — Tech stack focus:**
- **message**: Include the agent's full role identity as a codebase analysis specialist
  focused on technology stack and integrations, the project root path, and instruction to
  write STACK.md and INTEGRATIONS.md to `.planning/codebase/`. Include any user-provided
  focus area to guide analysis. The agent should explore thoroughly and return confirmation only.

  Message outline:
  > You are a codebase analysis specialist focused on technology stack and integrations.
  > Analyze this codebase for languages, runtime, frameworks, dependencies, configuration,
  > external APIs, databases, auth providers, and webhooks.
  > Write directly to .planning/codebase/: STACK.md and INTEGRATIONS.md.
  > Explore thoroughly. Write documents directly. Return confirmation only with line counts.
- **reset**: `"true"`

**Agent 2 — Architecture focus:**
- **message**: Include the agent's full role identity as a codebase analysis specialist
  focused on architecture and structure, instruction to write ARCHITECTURE.md and
  STRUCTURE.md to `.planning/codebase/`.

  Message outline:
  > You are a codebase analysis specialist focused on architecture and directory structure.
  > Analyze patterns, layers, data flow, abstractions, entry points, directory layout,
  > key locations, and naming conventions.
  > Write directly to .planning/codebase/: ARCHITECTURE.md and STRUCTURE.md.
  > Explore thoroughly. Write documents directly. Return confirmation only with line counts.
- **reset**: `"true"`

**Agent 3 — Quality focus:**
- **message**: Include the agent's full role identity as a codebase analysis specialist
  focused on code conventions and testing practices, instruction to write CONVENTIONS.md
  and TESTING.md to `.planning/codebase/`.

  Message outline:
  > You are a codebase analysis specialist focused on coding conventions and testing patterns.
  > Analyze code style, naming, patterns, error handling, test framework, structure, mocking,
  > and coverage.
  > Write directly to .planning/codebase/: CONVENTIONS.md and TESTING.md.
  > Explore thoroughly. Write documents directly. Return confirmation only with line counts.
- **reset**: `"true"`

**Agent 4 — Concerns focus:**
- **message**: Include the agent's full role identity as a codebase analysis specialist
  focused on technical concerns and risks, instruction to write CONCERNS.md to
  `.planning/codebase/`.

  Message outline:
  > You are a codebase analysis specialist focused on technical debt, known issues, and
  > areas of concern.
  > Analyze tech debt, bugs, security risks, performance issues, and fragile areas.
  > Write directly to .planning/codebase/: CONCERNS.md.
  > Explore thoroughly. Write document directly. Return confirmation only with line counts.
- **reset**: `"true"`

After all agents complete, verify all 7 documents exist in `.planning/codebase/`.

Continue to collect_confirmations.
</step>

<step name="collect_confirmations">
Wait for all 4 agents to complete.

**Expected confirmation format from each agent:**

```
## Mapping Complete

**Focus:** {focus}
**Documents written:**
- `.planning/codebase/{DOC1}.md` ({N} lines)
- `.planning/codebase/{DOC2}.md` ({N} lines)

Ready for orchestrator summary.
```

**What you receive:** Just file paths and line counts. NOT document contents.

If any agent failed, note the failure and continue with successful documents.

Continue to verify_output.
</step>

<step name="verify_output">
Verify all documents created successfully:

```bash
ls -la .planning/codebase/
wc -l .planning/codebase/*.md
```

**Verification checklist:**
- All 7 documents exist
- No empty documents (each should have more than 20 lines)

If any documents missing or empty, note which agents may have failed.

Continue to scan_for_secrets.
</step>

<step name="scan_for_secrets">
**CRITICAL SECURITY CHECK:** Scan output files for accidentally leaked secrets before committing.

```bash
grep -E '(sk-[a-zA-Z0-9]{20,}|sk_live_[a-zA-Z0-9]+|sk_test_[a-zA-Z0-9]+|ghp_[a-zA-Z0-9]{36}|gho_[a-zA-Z0-9]{36}|glpat-[a-zA-Z0-9_-]+|AKIA[A-Z0-9]{16}|xox[baprs]-[a-zA-Z0-9-]+|-----BEGIN.*PRIVATE KEY|eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.)' .planning/codebase/*.md 2>/dev/null && echo "SECRETS_FOUND" || echo "CLEAN"
```

**If secrets found:**

```
SECURITY ALERT: Potential secrets detected in codebase documents!

Found patterns that look like API keys or tokens in:
[show match output]

This would expose credentials if committed.

Action required:
1. Review the flagged content above
2. If these are real secrets, they must be removed before committing
3. Consider adding sensitive files to the deny permissions list

Pausing before commit. Reply "safe to proceed" if the flagged content is not actually sensitive.
```

Wait for user confirmation before continuing.

**If no secrets found:**
Continue to commit_codebase_map.
</step>

<step name="commit_codebase_map">
Commit the codebase map:

```bash
git add .planning/codebase/*.md
git commit -m "docs: map existing codebase"
```

Continue to offer_next.
</step>

<step name="offer_next">
Present completion summary and next steps.

```bash
wc -l .planning/codebase/*.md
```

**Output format:**

```
Codebase mapping complete.

Created .planning/codebase/:
- STACK.md ([N] lines) - Technologies and dependencies
- ARCHITECTURE.md ([N] lines) - System design and patterns
- STRUCTURE.md ([N] lines) - Directory layout and organization
- CONVENTIONS.md ([N] lines) - Code style and patterns
- TESTING.md ([N] lines) - Test structure and practices
- INTEGRATIONS.md ([N] lines) - External services and APIs
- CONCERNS.md ([N] lines) - Technical debt and issues

* * *
## Next Up

**Initialize project** — use codebase context for planning

Use the gsd-new-project skill.

Also available:
- Re-run mapping: use gsd-map-codebase skill
- Review specific file: cat .planning/codebase/STACK.md
- Edit any document before proceeding
* * *
```

End workflow.
</step>

</process>

<success_criteria>
- [ ] .planning/codebase/ directory created
- [ ] 4 gsd-codebase-mapper subagents spawned via call_subordinate
- [ ] Agents write documents directly (orchestrator doesn't receive document contents)
- [ ] All 7 codebase documents exist
- [ ] Security scan completed before commit
- [ ] Clear completion summary with line counts
- [ ] User offered clear next steps
</success_criteria>
