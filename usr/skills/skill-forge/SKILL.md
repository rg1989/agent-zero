---
name: "skill-forge"
description: "Creates a new Agent Zero skill on the fly during a conversation. This skill actively writes the SKILL.md file to disk — use it whenever the user asks to create, save, teach, or capture something as a reusable skill. Works from a description, from current conversation context, or from scratch interactively."
version: "1.0.0"
author: "Agent Zero"
tags: ["meta", "skills", "creation", "workflow", "forge"]
trigger_patterns:
  - "create a skill"
  - "create skill"
  - "make a skill"
  - "save as a skill"
  - "save this as a skill"
  - "save as skill"
  - "add a skill"
  - "add skill"
  - "new skill"
  - "build a skill"
  - "write a skill"
  - "teach you to"
  - "teach you how to"
  - "skill for"
  - "skill that"
  - "turn this into a skill"
  - "make this a skill"
---

# Skill Forge

You are creating a new Agent Zero skill — an actionable SKILL.md file written to disk that will be available immediately for future conversations.

**This is an active creation workflow. You will gather requirements, write the file, and confirm success. Do not just describe how to create a skill — actually create it.**

---

## Step 1: Gather Requirements

Collect the following before writing anything. If the user already provided details (in the message or earlier in the conversation), use those — only ask for what is missing.

### Required
- **What does the skill do?** — the purpose in one sentence
- **What should trigger it?** — list of 3–8 phrases/keywords a user might say
- **What should the agent actually do?** — the instructions the agent will follow

### Optional (but good to ask about if not obvious)
- **Name** (defaults to a slug derived from the purpose)
- **Tags** (categories; derive from purpose if not provided)
- **Author** (defaults to the user's name or "Agent Zero")

### If the user says "save what we just did" or "turn this into a skill"
Synthesise the skill content from the current conversation — infer purpose, triggers, and instructions from what was just discussed. Confirm your interpretation with the user before writing.

---

## Step 2: Derive the Slug

Generate the directory/file name from the skill name:
- Lowercase only
- Replace spaces and special characters with hyphens
- Strip leading/trailing hyphens
- Max 40 characters

Examples: "code review" → `code-review`, "analyse CSV data" → `analyse-csv-data`

---

## Step 3: Check for Conflicts

Before writing, check if the skill already exists:

```bash
ls /a0/usr/skills/{slug}/SKILL.md 2>/dev/null && echo "EXISTS" || echo "NEW"
```

- **NEW** → proceed
- **EXISTS** → tell the user: "A skill named '{slug}' already exists. Overwrite it?" — wait for confirmation before proceeding.

---

## Step 4: Write the Skill

Create the directory and write the SKILL.md file using `code_execution_tool` or the terminal:

```bash
mkdir -p /a0/usr/skills/{slug}
```

Then write the file. Use the following template — fill in all placeholders from Step 1:

```markdown
---
name: "{slug}"
description: "{one-sentence description of what the skill does and when to use it}"
version: "1.0.0"
author: "{author}"
tags: [{comma-separated quoted tags}]
trigger_patterns:
  - "{trigger 1}"
  - "{trigger 2}"
  - "{trigger 3}"
  ...
---

# {Skill Title}

## When to Use
{Describe the exact conditions that should trigger this skill — be specific.}

## What to Do
{Step-by-step instructions the agent should follow. Be concrete and actionable.
Use numbered steps for sequences, bullet points for options.}

## Examples

**User says:** "{example trigger phrase}"

**Agent does:**
{Describe what the agent should do in response — the expected behaviour.}

## Notes
{Any caveats, edge cases, or important reminders. Remove this section if empty.}
```

Write the complete file in one operation. Do not write a partial file and iterate.

---

## Step 5: Verify

After writing, verify the file exists and is non-empty:

```bash
cat /a0/usr/skills/{slug}/SKILL.md | head -20
```

If the file looks correct, proceed to Step 6. If it is missing or malformed, fix it before confirming.

---

## Step 6: Confirm

Report back to the user with:

1. **Location**: `/a0/usr/skills/{slug}/SKILL.md`
2. **How to trigger it**: give 2–3 example phrases from the trigger patterns
3. **When it takes effect**: skills are available immediately — no restart needed

Example confirmation message:
> Skill **{name}** created at `/a0/usr/skills/{slug}/SKILL.md`.
>
> Trigger it by saying things like:
> - "{trigger 1}"
> - "{trigger 2}"
>
> The skill is active immediately.

---

## Quality Checklist

Before confirming, verify your SKILL.md meets these standards:

- [ ] `name` is lowercase with hyphens, no spaces
- [ ] `description` clearly states when AND why to use this skill (one sentence)
- [ ] At least 3 `trigger_patterns` that a real user would naturally say
- [ ] The body has a clear **What to Do** section with concrete steps, not vague advice
- [ ] Instructions are written for the agent, not for the user (the agent reads this)
- [ ] No placeholder text left unfilled

---

## Common Mistakes to Avoid

- **Do not** write a skill that just describes a concept — skills must tell the agent what to DO
- **Do not** leave `{placeholders}` in the written file
- **Do not** make trigger patterns too generic (e.g., "help", "do it") — they should be specific enough to avoid false triggers
- **Do not** forget to actually execute the file write — confirming without writing is useless
- **Do not** write the skill to `skills/` (read-only core directory) — always use `/a0/usr/skills/`
