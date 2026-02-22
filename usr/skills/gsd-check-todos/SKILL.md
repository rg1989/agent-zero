---
name: gsd-check-todos
description: List pending todos and select one to work on
allowed-tools:
  - code_execution_tool
  - input
---

<objective>
List all pending todos, allow selection, load full context for the selected todo, and route to appropriate action.

Handles:
- Todo counting and listing with area filtering
- Interactive selection with full context loading
- Roadmap correlation checking
- Action routing (work now, add to phase, brainstorm, create phase)
- STATE.md updates and git commits
</objective>

<context>
Arguments: the user-provided area filter (optional)

Todo state and roadmap correlation are loaded in-workflow using shell commands and targeted reads.
</context>

<process>

<step name="init_context">
Load todo context by listing `.planning/todos/pending/` and reading each file's frontmatter.

Extract: `todo_count`, `todos` (array with title, area, created), `pending_dir`.

If `todo_count` is 0:
```
No pending todos.

Todos are captured during work sessions with gsd-add-todo.

* * *

Would you like to:

1. Continue with current phase (use gsd-progress)
2. Add a todo now (use gsd-add-todo)
```

Exit.
</step>

<step name="parse_filter">
Check for area filter in arguments:
- `gsd-check-todos` -> show all
- `gsd-check-todos api` -> filter to area:api only
</step>

<step name="list_todos">
Use the todos array (already filtered by area if specified).

Parse and display as numbered list:

```
Pending Todos:

1. Add auth token refresh (api, 2d ago)
2. Fix modal z-index issue (ui, 1d ago)
3. Refactor database connection pool (database, 5h ago)

* * *

Reply with a number to view details, or:
- Specify an area filter to narrow the list
- q to exit
```

Format age as relative time from created timestamp.
</step>

<step name="handle_selection">
Wait for user to reply with a number.

If valid: load selected todo, proceed.
If invalid: "Invalid selection. Reply with a number (1-[N]) or q to exit."
</step>

<step name="load_context">
Read the todo file completely. Display:

```
## [title]

**Area:** [area]
**Created:** [date] ([relative time] ago)
**Files:** [list or "None"]

### Problem
[problem section content]

### Solution
[solution section content]
```

If `files` field has entries, read and briefly summarize each.
</step>

<step name="check_roadmap">
Check for roadmap:

If `.planning/ROADMAP.md` exists:
1. Read the roadmap
2. Check if todo's area matches an upcoming phase
3. Check if todo's files overlap with a phase's scope
4. Note any match for action options
</step>

<step name="offer_actions">
**If todo maps to a roadmap phase:**

Use `input` to ask:
- header: "Action"
- question: "This todo relates to Phase [N]: [name]. What would you like to do?"
- options:
  - "Work on it now" -- move to done, start working
  - "Add to phase plan" -- include when planning Phase [N]
  - "Brainstorm approach" -- think through before deciding
  - "Put it back" -- return to list

**If no roadmap match:**

Use `input` to ask:
- header: "Action"
- question: "What would you like to do with this todo?"
- options:
  - "Work on it now" -- move to done, start working
  - "Create a phase" -- use gsd-add-phase with this scope
  - "Brainstorm approach" -- think through before deciding
  - "Put it back" -- return to list
</step>

<step name="execute_action">
**Work on it now:**
Using `code_execution_tool`:
```bash
mv ".planning/todos/pending/[filename]" ".planning/todos/done/"
```
Update STATE.md todo count. Present problem/solution context. Begin work or ask how to proceed.

**Add to phase plan:**
Note todo reference in phase planning notes. Keep in pending. Return to list or exit.

**Create a phase:**
Display: `gsd-add-phase [description from todo]`
Keep in pending. User runs command in fresh context.

**Brainstorm approach:**
Keep in pending. Start discussion about problem and approaches.

**Put it back:**
Return to list_todos step.
</step>

<step name="update_state">
After any action that changes todo count:

Re-list `.planning/todos/pending/` to get updated count, then update STATE.md "### Pending Todos" section if exists.
</step>

<step name="git_commit">
If todo was moved to done/, commit the change using `code_execution_tool`:

```bash
git rm --cached .planning/todos/pending/[filename] 2>/dev/null || true
git add .planning/todos/done/[filename] .planning/STATE.md
git commit -m "docs: start work on todo - [title]"
```

Confirm: "Committed: docs: start work on todo - [title]"
</step>

</process>

<success_criteria>
- [ ] All pending todos listed with title, area, age
- [ ] Area filter applied if specified
- [ ] Selected todo's full context loaded
- [ ] Roadmap context checked for phase match
- [ ] Appropriate actions offered
- [ ] Selected action executed
- [ ] STATE.md updated if todo count changed
- [ ] Changes committed to git (if todo moved to done/)
</success_criteria>
