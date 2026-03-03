---
phase: quick-6
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - prompts/agent.system.main.tips.md
  - usr/skills/web-app-builder/SKILL.md
autonomous: true
requirements: [ROOT-CAUSE-FIX]

must_haves:
  truths:
    - "Agent uses http://localhost (not localhost:50000) for all API calls inside the container"
    - "Agent never creates standalone Flask apps outside the Apps System when a step fails"
    - "System prompt clearly distinguishes internal API URLs from external browser URLs"
  artifacts:
    - path: "prompts/agent.system.main.tips.md"
      provides: "Corrected URL guidance and standalone app prohibition"
      contains: "http://localhost/"
    - path: "usr/skills/web-app-builder/SKILL.md"
      provides: "URL clarification section and fallback prevention directive"
      contains: "INTERNAL vs EXTERNAL URLs"
  key_links:
    - from: "prompts/agent.system.main.tips.md"
      to: "usr/skills/web-app-builder/SKILL.md"
      via: "consistent URL guidance"
      pattern: "http://localhost/"
---

<objective>
Fix the root cause of app creation failures: the agent tries API calls to localhost:50000 from inside the Docker container (which only exposes port 80 internally), gets ConnectionRefusedError, and then bypasses the Apps System entirely by writing standalone Flask apps.

Purpose: Eliminate the two-part failure chain — wrong URL causes step failure, missing guardrails allow fallback to ad-hoc apps.
Output: Updated system prompt and SKILL.md with correct internal URLs and strict fallback prevention.
</objective>

<execution_context>
@/Users/rgv250cc/.claude/get-shit-done/workflows/execute-plan.md
@/Users/rgv250cc/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@prompts/agent.system.main.tips.md
@usr/skills/web-app-builder/SKILL.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix system prompt — correct internal URLs and add standalone app prohibition</name>
  <files>prompts/agent.system.main.tips.md</files>
  <action>
Edit `prompts/agent.system.main.tips.md` — the "Apps System" section at the bottom.

**Changes to make:**

1. After line "Apps are served at localhost:50000/{app_name}/ via the built-in proxy", add a prominent URL clarification block:

```
## CRITICAL: Internal vs External URLs

- **User's browser (EXTERNAL):** `localhost:50000/{app_name}/` — this is what you tell the user
- **API calls from inside this container (INTERNAL):** `http://localhost/webapp` — this is what YOU use in curl commands
- Port 50000 is the HOST-side mapping. Inside this container, the web server runs on port 80
- If you call localhost:50000 from inside the container, you WILL get "Connection refused"
- ALL curl commands to the webapp API MUST use `http://localhost/webapp` (no port number)
```

2. Add a PROHIBITION section after the URL clarification:

```
## FORBIDDEN — Standalone Apps

NEVER create standalone Flask/Python apps outside the Apps System. Specifically:
- NEVER write your own app.py with `Flask(__name__)` from scratch
- NEVER pick your own port (5000, 8000, 8080, etc.)
- NEVER save apps to the workdir instead of /a0/apps/
- If ANY step in the 8-step sequence fails, STOP and report the error to the user
- Do NOT "work around" a failure by building something outside the Apps System
```

3. In the existing numbered list, update item 6 to reinforce: change "Apps are served at localhost:50000/{app_name}/ via the built-in proxy" to "Tell the user their app is at localhost:50000/{app_name}/ (external URL). Your API calls inside the container use http://localhost/webapp (no port)."
  </action>
  <verify>
Read prompts/agent.system.main.tips.md and confirm:
- "CRITICAL: Internal vs External URLs" section exists
- "http://localhost/webapp" appears as the internal URL
- "FORBIDDEN" section with standalone app prohibition exists
- No reference to localhost:50000 as an API endpoint the agent should curl
  </verify>
  <done>System prompt has clear internal/external URL distinction and explicit prohibition against standalone apps</done>
</task>

<task type="auto">
  <name>Task 2: Fix SKILL.md — add URL clarification and fallback prevention directive</name>
  <files>usr/skills/web-app-builder/SKILL.md</files>
  <action>
Edit `usr/skills/web-app-builder/SKILL.md` with three changes:

**Change 1:** Add a new section between the "EXECUTION FLOW" section and the "How routing works" section. Insert this block:

```markdown
---

## INTERNAL vs EXTERNAL URLs — READ THIS CAREFULLY

You are running INSIDE a Docker container. The web server runs on port 80 inside the container.

| Context | URL | Example |
|---------|-----|---------|
| YOUR curl commands (inside container) | `http://localhost/webapp` | `curl -s "http://localhost/webapp?action=list"` |
| User's browser (outside container) | `localhost:50000/{app_name}/` | Tell user: "Your app is at localhost:50000/my-app/" |

**WARNING:** `localhost:50000` is the HOST-side port mapping. If you curl localhost:50000 from inside the container, you will get `Connection refused`. Always use `http://localhost/webapp` (no port number) for all API calls.

---
```

**Change 2:** Add a FALLBACK PREVENTION section right after the new URL section:

```markdown
## FALLBACK FORBIDDEN

If ANY step in the sequence below fails:
1. STOP immediately
2. Report the exact error to the user
3. Do NOT attempt to "work around" the failure

Specifically, you MUST NEVER:
- Write your own Flask app from scratch (e.g., `from flask import Flask; app = Flask(__name__)`)
- Pick your own port number (5000, 8000, 8080, etc.)
- Save an app to the workdir or any path outside `/a0/apps/`
- Skip the template copy step and write code from scratch
- Ignore errors and continue to the next step

These actions bypass the Apps System and produce broken apps that cannot be managed, proxied, or persisted. The ONLY correct path is the 8-step sequence below.

---
```

**Change 3:** In the SKILL.md description field in the YAML frontmatter (line 3), change:
`"Apps are served at localhost:50000/{app_name}/ with no extra port forwarding required."`
to:
`"Build, deploy, and manage local web applications within Agent Zero. Apps are served to the user at localhost:50000/{app_name}/. Internal API calls use http://localhost/webapp (not port 50000)."`

This ensures even the skill description reinforces the correct URL pattern.
  </action>
  <verify>
Read usr/skills/web-app-builder/SKILL.md and confirm:
- "INTERNAL vs EXTERNAL URLs" section exists between EXECUTION FLOW and How routing works
- "FALLBACK FORBIDDEN" section exists with explicit prohibitions
- YAML description mentions "http://localhost/webapp"
- The table showing internal vs external URLs is present
- "Connection refused" warning about localhost:50000 is present
  </verify>
  <done>SKILL.md has clear URL guidance distinguishing internal API calls from external browser URLs, plus strict fallback prevention that forbids standalone Flask apps</done>
</task>

</tasks>

<verification>
1. Read both files and confirm all new sections are present
2. Grep for "localhost:50000" — should only appear in USER-FACING contexts (telling the user their app URL), never as a curl target
3. Grep for "FALLBACK FORBIDDEN" — should appear in SKILL.md
4. Grep for "FORBIDDEN" — should appear in tips.md
5. Grep for "http://localhost/webapp" — should appear in both files as the correct internal URL
</verification>

<success_criteria>
- prompts/agent.system.main.tips.md has Internal vs External URL section and standalone app prohibition
- usr/skills/web-app-builder/SKILL.md has URL clarification table, fallback prevention directive, and updated description
- No instructions tell the agent to curl localhost:50000 from inside the container
- Both files consistently use http://localhost/webapp as the internal API URL
</success_criteria>

<output>
After completion, create `.planning/quick/6-fix-root-cause-of-app-creation-failures-/6-SUMMARY.md`
</output>
