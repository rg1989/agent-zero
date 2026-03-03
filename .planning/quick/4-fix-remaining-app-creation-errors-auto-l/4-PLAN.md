---
phase: quick-4
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - python/extensions/tool_execute_before/_20_enforce_skill_runtimes.py
  - usr/extensions/tool_execute_before/_20_enforce_skill_runtimes.py
  - usr/skills/web-app-builder/SKILL.md
autonomous: true
requirements: [QUICK-4-HOOK, QUICK-4-SKILL]
must_haves:
  truths:
    - "Runtime enforcement hook lives in python/extensions/ where default_root guarantees discovery"
    - "No duplicate hook exists in usr/extensions/"
    - "SKILL.md Step 5 crud-app section lists all template files and forbids rewriting app.py"
    - "SKILL.md Step 5 crud-app section gives explicit 4-step customization (SQL, queries, list.html, form.html)"
  artifacts:
    - path: "python/extensions/tool_execute_before/_20_enforce_skill_runtimes.py"
      provides: "Runtime enforcement hook in guaranteed discovery path"
      contains: "EnforceSkillRuntimes"
    - path: "usr/skills/web-app-builder/SKILL.md"
      provides: "Improved crud-app customization guidance"
      contains: "DO NOT rewrite app.py"
  key_links:
    - from: "python/extensions/tool_execute_before/_20_enforce_skill_runtimes.py"
      to: "python/tools/skills_tool.py"
      via: "DATA_NAME_LOADED_SKILLS import"
      pattern: "from python.tools.skills_tool import DATA_NAME_LOADED_SKILLS"
---

<objective>
Fix two app creation issues that waste tokens and time: (1) move the runtime enforcement hook from usr/extensions/ to python/extensions/ so it is always discovered via the default_root="python" fallback, and (2) improve SKILL.md Step 5's crud-app section to prevent the agent from rewriting template files from scratch.

Purpose: Reduce failed attempts and wasted tokens during app creation by making runtime enforcement reliable and preventing template over-customization.
Output: Moved extension hook, updated SKILL.md
</objective>

<execution_context>
@/Users/rgv250cc/.claude/get-shit-done/workflows/execute-plan.md
@/Users/rgv250cc/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@usr/extensions/tool_execute_before/_20_enforce_skill_runtimes.py
@usr/skills/web-app-builder/SKILL.md
@python/extensions/tool_execute_before/_10_replace_last_tool_output.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Move runtime enforcement hook to guaranteed discovery path</name>
  <files>
    python/extensions/tool_execute_before/_20_enforce_skill_runtimes.py
    usr/extensions/tool_execute_before/_20_enforce_skill_runtimes.py
  </files>
  <action>
Copy `usr/extensions/tool_execute_before/_20_enforce_skill_runtimes.py` to `python/extensions/tool_execute_before/_20_enforce_skill_runtimes.py`. The file content stays exactly the same — no modifications needed.

Then delete `usr/extensions/tool_execute_before/_20_enforce_skill_runtimes.py` to avoid confusion (two copies = ambiguous which runs).

Also delete the `usr/extensions/tool_execute_before/` directory if it is now empty (and `usr/extensions/` if that is also empty after removal). Use `rmdir` to only remove if empty — do not force-delete.

Verify the new file has the same content as the original by checking it imports `Extension` and defines `EnforceSkillRuntimes`.
  </action>
  <verify>
Run: `python -c "import python.extensions.tool_execute_before._20_enforce_skill_runtimes"` — should import without error.
Run: `ls python/extensions/tool_execute_before/_20_enforce_skill_runtimes.py` — file exists.
Run: `ls usr/extensions/tool_execute_before/_20_enforce_skill_runtimes.py 2>&1` — should show "No such file".
  </verify>
  <done>Hook file exists only in python/extensions/tool_execute_before/ and imports cleanly. No copy remains in usr/extensions/.</done>
</task>

<task type="auto">
  <name>Task 2: Improve SKILL.md Step 5 crud-app guidance to prevent template over-customization</name>
  <files>usr/skills/web-app-builder/SKILL.md</files>
  <action>
In `usr/skills/web-app-builder/SKILL.md`, replace the existing "For `crud-app`:" section (lines 220-223, the 3-line block under the crud-app heading) with a more detailed version. The new section should be:

```
**For `crud-app`:**
After copying, your app directory contains these files — do NOT create or delete any:
`app.py`, `templates/base.html`, `templates/list.html`, `templates/form.html`, `templates/detail.html`, `static/style.css`, `static/app.js`, `requirements.txt`

**DO NOT rewrite app.py or create new template files.** The template already has working HTML, CSS, routing, and CRUD operations. Only make these targeted changes:

1. **Edit `CREATE_TABLE_SQL`** in app.py — change the `items` table columns to match your entity (e.g., `title TEXT`, `author TEXT`, `genre TEXT`)
2. **Update SQL queries** in each route function to match your new column names
3. **Update `templates/list.html`** — change table column headers and `{{ item.field }}` references to your columns
4. **Update `templates/form.html`** — change form field labels and input names to your columns
5. **Update `templates/detail.html`** — change displayed field labels and values to your columns
6. **Rename entity** — use `sed -i 's/items/yourentity/g; s/item/yourentity/g'` across app.py and templates (adjust for plural/singular)
```

Keep the surrounding sections (dashboard-realtime above, file-tool below) unchanged. Make sure the formatting is consistent with the other template sections (using bold for the template name header).
  </action>
  <verify>
Run: `grep -c "DO NOT rewrite app.py" usr/skills/web-app-builder/SKILL.md` — should return 1.
Run: `grep -c "templates/list.html" usr/skills/web-app-builder/SKILL.md` — should return at least 2 (one in the file inventory, one in customization step).
Run: `grep "CREATE_TABLE_SQL" usr/skills/web-app-builder/SKILL.md` — should appear in the crud-app section.
  </verify>
  <done>SKILL.md Step 5 crud-app section lists all template files, explicitly forbids rewriting app.py, and provides a 6-step targeted customization guide. The agent can follow these steps without creating monolithic replacements.</done>
</task>

</tasks>

<verification>
1. Runtime hook discovery: `python -c "import python.extensions.tool_execute_before._20_enforce_skill_runtimes; print('OK')"` prints OK
2. No stale copy: `test ! -f usr/extensions/tool_execute_before/_20_enforce_skill_runtimes.py && echo "CLEAN"`
3. SKILL.md integrity: `grep -A2 'For .crud-app' usr/skills/web-app-builder/SKILL.md` shows new guidance
4. SKILL.md still valid: Step 5 section still has all 7 template subsections (flask-dashboard, flask-basic, static-html, dashboard-realtime, utility-spa, crud-app, file-tool)
</verification>

<success_criteria>
- Runtime enforcement hook is in python/extensions/tool_execute_before/ (guaranteed path) and removed from usr/extensions/
- SKILL.md Step 5 crud-app section explicitly lists template files and forbids rewriting app.py
- SKILL.md Step 5 crud-app section provides targeted 6-step customization instructions
- No other SKILL.md sections are modified
</success_criteria>

<output>
After completion, create `.planning/quick/4-fix-remaining-app-creation-errors-auto-l/4-SUMMARY.md`
</output>
