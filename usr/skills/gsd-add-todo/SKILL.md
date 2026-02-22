---
name: gsd-add-todo
description: Capture idea or task as a structured todo from current conversation context
allowed-tools:
  - code_execution_tool
  - input
---

<objective>
Capture an idea, task, or issue that surfaces during a GSD session as a structured todo for later work. Enables "thought -> capture -> continue" flow without losing context.

Handles:
- Directory structure creation
- Content extraction from arguments or conversation
- Area inference from file paths
- Duplicate detection and resolution
- Todo file creation with frontmatter
- STATE.md updates
- Git commits
</objective>

<context>
Arguments: the user-provided todo description (optional)

Todo state and roadmap correlation are loaded in-workflow using shell commands and targeted reads.
</context>

<process>

<step name="init_context">
Load todo context by reading `.planning/STATE.md` and listing `.planning/todos/` if it exists.

Extract from available state: `todo_count`, `todos`, `pending_dir`.

Ensure directories exist using `code_execution_tool`:
```bash
mkdir -p .planning/todos/pending .planning/todos/done
```

Note existing areas from the todos for consistency in infer_area step.
</step>

<step name="extract_content">
**With arguments:** Use as the title/focus.
- `gsd-add-todo Add auth token refresh` -> title = "Add auth token refresh"

**Without arguments:** Analyze recent conversation to extract:
- The specific problem, idea, or task discussed
- Relevant file paths mentioned
- Technical details (error messages, line numbers, constraints)

Formulate:
- `title`: 3-10 word descriptive title (action verb preferred)
- `problem`: What's wrong or why this is needed
- `solution`: Approach hints or "TBD" if just an idea
- `files`: Relevant paths with line numbers from conversation
</step>

<step name="infer_area">
Infer area from file paths:

| Path pattern | Area |
|--------------|------|
| `src/api/*`, `api/*` | `api` |
| `src/components/*`, `src/ui/*` | `ui` |
| `src/auth/*`, `auth/*` | `auth` |
| `src/db/*`, `database/*` | `database` |
| `tests/*`, `__tests__/*` | `testing` |
| `docs/*` | `docs` |
| `.planning/*` | `planning` |
| `scripts/*`, `bin/*` | `tooling` |
| No files or unclear | `general` |

Use existing area from step 2 if similar match exists.
</step>

<step name="check_duplicates">
Search for key words from title in existing todos using `code_execution_tool`:
```bash
grep -l -i "[key words from title]" .planning/todos/pending/*.md 2>/dev/null
```

If potential duplicate found:
1. Read the existing todo
2. Compare scope

If overlapping, use `input` to ask:
- header: "Duplicate?"
- question: "Similar todo exists: [title]. What would you like to do?"
- options:
  - "Skip" -- keep existing todo
  - "Replace" -- update existing with new context
  - "Add anyway" -- create as separate todo
</step>

<step name="create_file">
Get current date and timestamp from `code_execution_tool`:
```bash
date -u +"%Y-%m-%dT%H:%M:%SZ"
date +"%Y-%m-%d"
```

Generate slug for the title (lowercase, hyphens, no special chars, max 40 chars).

Write to `.planning/todos/pending/{date}-{slug}.md`:

Example todo file format (YAML frontmatter between triple-dashes, then body sections):

    created: [timestamp]
    title: [title]
    area: [area]
    files:
      - [file:lines]

    ## Problem

    [problem description - enough context for future use weeks later]

    ## Solution

    [approach hints or "TBD"]
</step>

<step name="update_state">
If `.planning/STATE.md` exists:

1. Re-read `.planning/todos/pending/` to count todos
2. Update "### Pending Todos" under "## Accumulated Context"
</step>

<step name="git_commit">
Commit the todo and any updated state using `code_execution_tool`:

```bash
git add .planning/todos/pending/[filename] .planning/STATE.md
git commit -m "docs: capture todo - [title]"
```

Confirm: "Committed: docs: capture todo - [title]"
</step>

<step name="confirm">
```
Todo saved: .planning/todos/pending/[filename]

  [title]
  Area: [area]
  Files: [count] referenced

* * *

Would you like to:

1. Continue with current work
2. Add another todo (use gsd-add-todo again)
3. View all todos (use gsd-check-todos)
```
</step>

</process>

<success_criteria>
- [ ] Directory structure exists
- [ ] Todo file created with valid frontmatter
- [ ] Problem section has enough context for future reference
- [ ] No duplicates (checked and resolved)
- [ ] Area consistent with existing todos
- [ ] STATE.md updated if exists
- [ ] Todo and state committed to git
</success_criteria>
