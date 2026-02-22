# CONVERSION-RULES.md

**Authoritative reference for Phase 2, 3, and 4 executors.**
**Source:** STACK.md (researched 2026-02-21) + RESEARCH.md Phase 1 decisions.
**Audience:** Any agent or human converting Claude Code `agents/*.md` and `skills/*.md` files into Agent Zero `SKILL.md` format.

---

## §1 Purpose and Scope

This file is the authoritative conversion reference for transforming Claude Code `agents/*.md` and `skills/*.md` files into Agent Zero `SKILL.md` format.

The `agent_zero/skills/` directory in this repo is a **distribution artifact** — end users copy it to their Agent Zero skill root:
- Global skill root: `usr/skills/`
- Project-scoped skill root: `usr/projects/{project}/.a0proj/skills/`

Agent Zero discovers skills by `rglob("SKILL.md")` across all configured skill roots. Hidden directories (paths starting with `.`) are ignored. The `CONVERSION-RULES.md` file living inside `agent_zero/skills/` is intentional — Agent Zero ignores it because it is not named `SKILL.md`.

**What this document covers:**
- Frontmatter field mapping (§2): which fields to keep, transform, or drop
- Name transformation rules (§3): how to make all skill names valid Agent Zero slugs
- Tool name translation table (§4): Claude Code tool names → Agent Zero tool names
- What to strip from skill bodies (§5): forbidden content that breaks Agent Zero execution
- call_subordinate invocation pattern (§6): how to replace Claude Code `Task()` calls
- Size-split policy (§7): when and how to split oversized SKILL.md files
- Inline expansion for orchestrators (§8): handling `@`-include references
- Validation checklist (§9): 16-point check for each converted SKILL.md
- Directory layout (§10): target output structure

**What this document does NOT cover:**
- Body content prescriptions — each skill retains its original structure and personality
- Scheduling or ordering of conversions — see ROADMAP.md

---

## §2 Frontmatter Field Mapping

Source: STACK.md §3.3. Apply these rules to every Claude Code source file during conversion.

| Claude Code Field | Present In | Maps To Agent Zero Field | Action |
|------------------|-----------|--------------------------|--------|
| `name` | agents, skills | `name` | REQUIRED. Transform per §3. |
| `description` | agents, skills | `description` | REQUIRED. Direct copy. Trim to 1024 chars if needed. Rewrite if absent or Claude Code-specific. |
| `tools` (comma-separated string) | agents | `allowed-tools` (YAML list) | Convert value: split on comma, trim whitespace, translate each tool name per §4. |
| `allowed-tools` (YAML list) | skills | `allowed-tools` | Same field name. Translate each tool name per §4. |
| `model` | agents | — | DROP. Agent Zero does not support per-skill model override. |
| `color` | some agents | — | DROP. Claude Code UI display only. Not parsed by Agent Zero. |
| `argument-hint` | skills | — | DROP. Claude Code CLI help text. No Agent Zero equivalent. |
| `agent` | skills | — | DROP. Claude Code subagent directive. Agent Zero uses `call_subordinate` at runtime instead. |
| `version` | either | `version` | KEEP if present. Optional in Agent Zero. |
| `author` | either | `author` | KEEP if present. Optional in Agent Zero. |
| `license` | either | `license` | KEEP if present. Optional in Agent Zero. |
| `tags` | either | `tags` | KEEP if present. Optional in Agent Zero. |
| `triggers` | either | `triggers` | KEEP if present. Optional in Agent Zero. |
| `compatibility` | either | `compatibility` | KEEP if present. Max 500 chars. Optional in Agent Zero. |

**Note on `tools` alias:** Agent Zero's parser accepts `tools:` as an alias for `allowed-tools:` — but the VALUES must still be translated from Claude Code tool names to Agent Zero tool names. The alias only covers the field name, not the values.

**Agent Zero REQUIRED fields summary:**
- `name` — 1–64 chars, regex `^[a-z0-9-]+$`, no leading/trailing hyphens, no `--`
- `description` — non-empty, max 1024 chars

---

## §3 Name Transformation Rules

Claude Code skill names use colon-separated namespacing (`gsd:debug`). Agent Zero requires names matching `^[a-z0-9-]+$`. Apply these rules in order:

1. **Replace `:` with `-`** — this is the primary transformation (e.g., `gsd:debug` → `gsd-debug`)
2. **Lowercase all characters** — if any uppercase exists
3. **Remove leading or trailing hyphens** — `name.startswith("-")` or `name.endswith("-")` fails validation
4. **Collapse consecutive hyphens** — `--` in name fails validation; replace `--` with `-`
5. **Verify against regex** — final name must match `^[a-z0-9-]+$` and be 1–64 characters

**The directory name MUST match the `name` field exactly.** Agent Zero uses `_normalize_name(s.path.name)` for deduplication — mismatches cause subtle bugs.

**Verified transformation examples:**

| Claude Code Name | Agent Zero Name | Rule Applied |
|-----------------|----------------|--------------|
| `gsd:debug` | `gsd-debug` | Replace `:` with `-` |
| `gsd:plan-phase` | `gsd-plan-phase` | Replace `:` with `-` |
| `gsd:execute-phase` | `gsd-execute-phase` | Replace `:` with `-` |
| `gsd:verify-work` | `gsd-verify-work` | Replace `:` with `-` |
| `architect` | `architect` | Valid as-is |
| `gsd-debugger` | `gsd-debugger` | Valid as-is |
| `qa-tester` | `qa-tester` | Valid as-is |
| `backend-developer` | `backend-developer` | Valid as-is |

All agent names in `agents/*.md` are already lowercase-hyphen format and will pass `^[a-z0-9-]+$` without modification. Only skill names with colons require transformation.

---

## §4 Tool Name Translation Table

Claude Code tools are native Claude API capabilities. Agent Zero tools are Python modules in `python/tools/`. They do not have a 1-to-1 correspondence. Translate every tool name in `allowed-tools` using this table.

| Claude Code Tool | Agent Zero Equivalent | Notes |
|-----------------|----------------------|-------|
| `Bash` | `code_execution_tool` | Agent Zero executes shell via code_execution_tool |
| `Read` | `code_execution_tool` | No dedicated read tool; agents read files via shell (`cat`) or `document_query` |
| `Write` | `code_execution_tool` | File writes via shell (`tee`, `echo`, Python) |
| `Edit` | `code_execution_tool` | File edits via shell or scripting |
| `Glob` | `code_execution_tool` | File finding via shell (`find`, `ls`) |
| `Grep` | `code_execution_tool` | Pattern search via shell (`grep`, `rg`) |
| `WebSearch` | `search_engine` | Direct equivalent |
| `WebFetch` | `browser_open` or `browser_do` | Browser-based fetch |
| `Task` | `call_subordinate` | Spawning subordinate agents |
| `AskUserQuestion` | `input` | Requesting user input |
| `TodoWrite` | `code_execution_tool` | No native equivalent; write file via shell |
| `mcp__context7__*` | NOT MAPPED | MCP tools are not available in Agent Zero by default. Replace with `search_engine` for web lookups, or add prose fallback instructions describing what information to retrieve manually. |

**Note on `mcp__context7__*`:** This has no direct Agent Zero equivalent. Replace with `search_engine` for web-based lookups, or add prose fallback instructions in the skill body describing what information to retrieve manually and how.

**`allowed-tools` is advisory in Agent Zero** — unlike Claude Code's `tools:` which gates actual tool access, Agent Zero's `allowed-tools` is a whitelist hint. Agents will use their available tools regardless. List Agent Zero tool names that are semantically appropriate for the skill's function.

---

## §5 What to Strip from Every Converted Body

Remove ALL of the following from skill body content before finalizing. These elements are Claude Code-specific and will break or confuse Agent Zero execution.

- **`@`-file include references** (e.g., `@skills/workflows/execute-plan.md`) — Agent Zero does not preprocess `@` includes; they become literal text and break instructions. Either inline the referenced content directly, or drop the line.

- **`$ARGUMENTS` literals** — Claude Code injects slash command arguments via `$ARGUMENTS`. Agent Zero does not do string substitution. Replace with prose like "the user-provided [argument description]" or `{argument-name}` template variable explained in surrounding prose.

- **Hardcoded `/Users/rgv250cc/` absolute paths** — Agent Zero agents run in arbitrary environments. Replace with relative paths or generic descriptions. Example: replace `/Users/rgv250cc/Documents/Projects/ClaudeCode` with "the project root directory".

- **`gsd-tools.cjs` invocations** — the GSD runtime binary is not available in Agent Zero. Replace each `node /Users/rgv250cc/.claude/get-shit-done/bin/gsd-tools.cjs ...` call with a prose description of what the step accomplishes, using Agent Zero primitives:
  - File I/O operations → `code_execution_tool` (run shell commands)
  - State persistence → `memory_save` / `memory_load`
  - Progress reporting → describe the output format in prose

- **Claude Code slash command references** (`/gsd:debug`, `/gsd:plan-phase`, etc.) — replace with "use the `gsd-debug` skill" or equivalent prose referencing the Agent Zero skill name.

- **`Task(...)` Python API calls in code blocks** — Claude Code Python API. Replace with prose: "Use `call_subordinate` to delegate to a subordinate agent. See §6 for the invocation pattern."

- **GSD `.planning/` state management details** — `.planning/STATE.md`, ROADMAP.md write-back logic, and phase advancement commands are GSD runtime concepts. Adapt to describe the intent without the runtime tooling.

**What to KEEP:**
- XML-tagged sections (`<objective>`, `<process>`, `<context>`) — Agent Zero's model reads these well
- Markdown tables, checklists, and code examples — valid SKILL.md body content
- Original structure and section headers — preserves each skill's behavioral identity
- Instructional prose written in imperative language

---

## §6 call_subordinate Invocation Pattern

When a Claude Code skill uses `Task(prompt=..., subagent_type="gsd-debugger")`, the Agent Zero equivalent is a `call_subordinate` tool call.

**JSON tool call format (for reference — do NOT include raw JSON in SKILL.md bodies):**

```json
{
  "thoughts": ["I need to delegate to a specialist subagent."],
  "tool_name": "call_subordinate",
  "tool_args": {
    "message": "You are a [role]. Your task: [detailed prompt with full context, symptoms, files to check, expected return format]",
    "reset": "true"
  }
}
```

**Rules for call_subordinate usage:**

1. **`reset: "true"`** — use for brand-new subtasks; gives the subordinate a fresh context window
2. **`reset: "false"`** — use for follow-up messages to an already-running subordinate in the same session
3. **Do NOT use the `profile` parameter** — pass the subordinate's full role identity and behavioral instructions in the `message` field instead. This ensures portability across any Agent Zero installation that does not have matching profile files. Including `"profile": "gsd-debugger"` will fail silently in installations without that profile.
4. **`message` field must be self-contained** — include: the subordinate's role, the full issue context, symptom details, which files to check, and the expected return format

**How to document this pattern in SKILL.md bodies (use prose, not raw JSON):**

```markdown
## Spawn Debugging Subagent

Use `call_subordinate` to delegate investigation:
- **message**: Include the subordinate's full role identity, the issue context (slug,
  symptoms, expected behavior, actual behavior), which files to check, and the
  expected return format (e.g., `## ROOT CAUSE FOUND` or `## CHECKPOINT REACHED`)
- **reset**: `"true"` for a new investigation; `"false"` for a follow-up to the
  same subordinate

Example message structure:
> You are a debugging specialist with expertise in [domain]. Issue: {slug}.
> Symptoms: {symptoms}. Expected: {expected}. Actual: {actual}.
> Check these files: {file_list}.
> Return a structured report with ## ROOT CAUSE FOUND or ## CHECKPOINT REACHED.
```

**Source:** `frdel/agent-zero:python/tools/call_subordinate.py` — execute method signature: `async def execute(self, message="", reset="", **kwargs)`. GitHub issue #174 cross-verified.

---

## §7 Size-Split Policy

**500-line limit is a POLICY threshold, not advisory.** Any SKILL.md body that exceeds 500 lines after stripping (§5) must be split.

Rationale: Agent Zero allows a maximum of 5 concurrent loaded skills. Large bodies consume agent context quickly. The `skills_tool` `read_file` method supports on-demand loading of auxiliary files from within a skill directory.

### Split Strategy

When a post-strip body exceeds 500 lines:

1. Create a `rules/` subdirectory inside the skill directory
2. Move detailed reference content (tables, checklists, verbose protocol steps) into named `rules/*.md` files
3. The core `SKILL.md` retains: role identity, orchestration loop, structured return formats, and a `## Reference Files` section
4. In the `## Reference Files` section, document each rules file with its purpose and instruct the agent:

```markdown
## Reference Files

Detailed protocols in this skill directory. Use `skills_tool` with `method=read_file` to load as needed:
- `rules/investigation-protocol.md` — hypothesis formation and test methodology
- `rules/verification-steps.md` — 16-point validation checklist
```

### When to Split vs. When Not to Split

- **ALWAYS measure post-strip line count before deciding to split.** Raw line counts include gsd-tools.cjs blocks and `@`-includes that will be removed; do not split based on raw counts.
- If post-strip body is **under 500 lines** → no split
- If post-strip body is **500–800 lines** → one auxiliary `rules/` file for the densest section
- If post-strip body is **800+ lines** → split into multiple `rules/` files by concern (one file per logical area)

### Specific Guidance for Large Files

**For gsd-debugger and gsd-planner (raw counts: 1,201 and 1,182 lines):**
"Determine split strategy in Phase 4 after initial strip. Do not pre-design the split architecture." Post-strip size is unknown until stripping is complete; raw counts include substantial gsd-tools.cjs blocks that will be removed.

**For Phase 3 orchestrators with large inlined workflows (e.g., new-project workflow: 1,116 lines raw):**
Apply the split strategy — create a core `SKILL.md` with the orchestration logic and a `rules/workflow.md` (or similarly named file) for the detailed workflow steps. The Phase 3 planner will enumerate which orchestrators require this treatment.

### Post-Strip Audit Step

Before finalizing any conversion:
1. Count lines in the stripped SKILL.md body (not including frontmatter)
2. If count > 500: identify the densest section (usually a large table or checklist), move it to `rules/`
3. Re-count after moving; repeat if still > 500
4. Add `## Reference Files` section to SKILL.md listing all created `rules/` files

---

## §8 Inline Expansion for Orchestrator @-includes

Phase 3 orchestrator skills in `skills/*.md` are stubs that reference `@`-includes pointing to `skills/workflows/*.md`. The workflow content must be inlined because Agent Zero does not preprocess `@` references.

**Process:**

1. Read the referenced workflow file (e.g., `skills/workflows/execute-plan.md`)
2. Inline its content directly into the SKILL.md body, replacing the `@`-reference line
3. Strip all forbidden elements (§5) from the inlined content — apply §5 rules to the combined content
4. Count post-strip, post-inline body line count
5. If the combined post-strip body exceeds 500 lines, apply the split policy (§7)

**Decision rule for inline vs. split:**
- If inlined workflow + skill stub combined is under 500 lines post-strip → inline fully, no split
- If combined is 500–800 lines → move the workflow steps into `rules/workflow.md`, keep the skill stub intro and orchestration summary in `SKILL.md`
- If combined is 800+ lines → split by concern: `rules/workflow-steps.md` for detailed steps, `rules/reference-tables.md` for lookup tables, etc.

**Known large workflows requiring split treatment:**
- `new-project.md` (1,116 lines raw) → referenced by skills/new-project.md (ORCH-28)
- `complete-milestone.md` (700 lines raw) → referenced by skills/complete-milestone.md (ORCH-06)
- `verify-work.md` (569 lines raw) → referenced by skills/verify-work.md (ORCH-23)
- `transition.md` (544 lines raw) → referenced implicitly by transition orchestrators

---

## §9 16-Point Validation Checklist

Run this checklist against every converted SKILL.md before marking it complete. Source: STACK.md §4.3.

- [ ] File is named exactly `SKILL.md` (case-sensitive)
- [ ] File lives in its own subdirectory under the skills root
- [ ] First non-whitespace content is `---` (opening frontmatter fence)
- [ ] `name` field is present and non-empty
- [ ] `name` matches `^[a-z0-9-]+$` (lowercase letters, digits, and hyphens only)
- [ ] `name` length is 1–64 characters
- [ ] `name` does not start or end with `-`
- [ ] `name` does not contain `--`
- [ ] `description` field is present and non-empty
- [ ] `description` is at most 1024 characters
- [ ] `compatibility` (if present) is at most 500 characters
- [ ] No Claude Code-specific `@`-includes in the body
- [ ] No hardcoded absolute paths in the body
- [ ] No `$ARGUMENTS` placeholder in the body
- [ ] `allowed-tools` lists Agent Zero tool names (not Claude Code tool names: no `Read`, `Bash`, `Glob`, `Grep`, `Write`, `Edit`, `Task`, `AskUserQuestion`, `TodoWrite`, `mcp__*`)
- [ ] Body is under 500 lines (or split policy from §7 has been applied)

**Authoritative validator:** Agent Zero's `python/helpers/skills.py` function `validate_skill_md(path: Path) -> List[str]`. Use this in Phase 5 validation if a Python environment is available. Empty list = valid.

---

## §10 Directory Layout

Target output structure for the `agent_zero/skills/` distribution directory:

```
agent_zero/
  skills/
    CONVERSION-RULES.md        # this file — Phase 1 deliverable (ignored by Agent Zero loader)
    architect/                 # Phase 2 — one directory per skill
      SKILL.md
    backend-developer/         # Phase 2
      SKILL.md
    qa-tester/                 # Phase 2
      SKILL.md
    gsd-debugger/              # Phase 2/4 — subagent
      SKILL.md
      rules/                   # created only if post-strip body > 500 lines
        investigation-protocol.md
        structured-returns.md
    gsd-debug/                 # Phase 3 — was gsd:debug (colon → hyphen)
      SKILL.md
    gsd-plan-phase/            # Phase 3 — was gsd:plan-phase
      SKILL.md
    gsd-execute-phase/         # Phase 3 — was gsd:execute-phase
      SKILL.md
    gsd-verify-work/           # Phase 3 — was gsd:verify-work
      SKILL.md
    new-project/               # Phase 3 orchestrator with large inlined workflow
      SKILL.md
      rules/
        workflow.md            # detailed workflow steps (if post-strip > 500 lines)
    ...                        # remaining 43+ skill directories
```

**Naming convention:** The subdirectory name MUST match the `name` field in the SKILL.md frontmatter exactly. See §3 for transformation rules.

**Distribution note:** The `agent_zero/skills/` directory is a copy-ready distribution folder. End users copy the entire `agent_zero/skills/` directory to their Agent Zero skill root. The `CONVERSION-RULES.md` file at the root will be ignored by Agent Zero's skill loader (it is not named `SKILL.md`) and can remain in the distribution without harm.
