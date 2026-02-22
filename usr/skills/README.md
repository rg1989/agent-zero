# GSD Skill Pack for Agent Zero

A skill pack that brings the GSD (Get Shit Done) workflow system into Agent Zero.

## What's Included

**50 skills across 3 categories:**

| Category | Count | Skills |
|---|---|---|
| Specialist role agents | 8 | architect, backend-developer, code-reviewer, database-architect, devops-engineer, frontend-developer, qa-tester, security-auditor |
| GSD orchestrator skills | 31 | gsd-add-phase, gsd-add-todo, gsd-audit-milestone, gsd-check-todos, gsd-cleanup, gsd-complete-milestone, gsd-debug, gsd-discuss-phase, gsd-execute-phase, gsd-full-feature, gsd-health, gsd-help, gsd-insert-phase, gsd-join-discord, gsd-list-phase-assumptions, gsd-map-codebase, gsd-new-milestone, gsd-new-project, gsd-pause-work, gsd-plan-milestone-gaps, gsd-plan-phase, gsd-progress, gsd-quick, gsd-reapply-patches, gsd-remove-phase, gsd-research-phase, gsd-resume-work, gsd-set-profile, gsd-settings, gsd-update, gsd-verify-work |
| GSD subagent skills | 11 | gsd-codebase-mapper, gsd-debugger, gsd-executor, gsd-integration-checker, gsd-phase-researcher, gsd-plan-checker, gsd-planner, gsd-project-researcher, gsd-research-synthesizer, gsd-roadmapper, gsd-verifier |

## Installation

### Global (available to all Agent Zero projects)

```bash
cp -r agent_zero/skills/* /path/to/agent-zero/usr/skills/
```

### Project-scoped (available to one project only)

```bash
cp -r agent_zero/skills/* /path/to/agent-zero/usr/projects/{your-project}/.a0proj/skills/
```

Replace `{your-project}` with your Agent Zero project name.

## How Agent Zero Discovers Skills

Agent Zero discovers skills by scanning for SKILL.md files with `rglob("SKILL.md")` across all configured skill roots. Each skill lives in its own subdirectory. Hidden directories (paths starting with `.`) are ignored. The `CONVERSION-RULES.md` file in this directory is intentionally included — Agent Zero ignores it because it is not named SKILL.md.

## Key Skills to Know

| Skill | Purpose |
|---|---|
| `gsd-new-project` | Bootstrap a new project with GSD structure |
| `gsd-plan-phase` | Plan a new development phase |
| `gsd-execute-phase` | Execute a planned phase atomically |
| `gsd-verify-work` | Verify completed work against requirements |
| `gsd-debug` | Debug issues using structured investigation |
| `gsd-full-feature` | Build a complete feature end-to-end |
| `gsd-audit-milestone` | Audit milestone completion against requirements |
| `gsd-help` | List all available GSD skills and usage |

## Note

Project-scoped skills take priority over global skills when both roots are configured.
