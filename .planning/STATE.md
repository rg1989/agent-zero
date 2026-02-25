# State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-25)

**Core value:** Agent Zero can build, run, and persist web applications directly within its own UI
**Current focus:** Phase 15 complete — v1.2 milestone DONE

## Current Position

Phase: 15 of 15 (CLI Orchestration Skill Documentation)
Plan: 1 of 1 complete — Phase 15 DONE
Status: Phase 15 complete — usr/skills/cli-orchestration/SKILL.md written (371 lines); CLI-06 satisfied; v1.2 milestone complete
Last activity: 2026-02-25 — Phase 15 Plan 01 complete; CLI-06 satisfied

Progress: [████████████████████] 100% (15-01 complete — all phases done)

## Performance Metrics

**Velocity:**
- Total plans completed: 6 (v1.2)
- Average duration: 6 min
- Total execution time: 39 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 11-tmux-primitive-infrastructure | 2 | 14 min | 7 min |
| 12-readiness-detection | 1 | 2 min | 2 min |
| 13-interactive-cli-session-lifecycle | 2 | 20 min | 10 min |
| 14-opencode-session-wrapper | 1 | 2 min | 2 min |
| 15-cli-orchestration-skill-documentation | 1 | 3 min | 3 min |

*Updated after each plan completion*

## Accumulated Context

### Decisions

- v1.2 architecture: New `tmux_tool` Python class for shared terminal interaction; `code_execution_tool` and `terminal_agent.py` left untouched
- Prompt detection strategy: prompt pattern first, idle timeout fallback (10s minimum for AI CLI response times)
- No sentinel injection: shared terminal is user-visible; only stability polling + prompt matching are allowed
- ANSI stripping required before any capture-pane parsing: `re.sub(r'\x1b(?:\][^\x07]*\x07|[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)` — OSC branch must come FIRST (2-char branch range includes `]`)
- [Phase 11]: ANSI_RE OSC branch must precede 2-char branch: ] (0x5D) falls in \-_ range so ordering matters
- [Phase 11-02]: Docker live-reload pattern: bind mount ./python:/a0/python and ./prompts:/a0/prompts so tool/prompt changes reach container without rebuild; copy_A0.sh uses cp -ru (update-newer) without presence-check guard
- [Phase 12-readiness-detection]: wait_ready initial 0.3s delay before first capture prevents stale-prompt false positive at send/wait boundary
- [Phase 12-readiness-detection]: wait_ready uses -S -50 lines (not -100): only last prompt line needed; smaller capture faster in tight poll loop
- [Phase 12-readiness-detection]: Default prompt_pattern r'[$#>%]\s*$' matches bash/zsh/sh/node prompts; does NOT match Continue? [y/N] sub-prompts
- [Phase 13-01]: OpenCode ready state has TWO forms: (1) initial startup = status bar '/a0  ...  1.2.14'; (2) post-response = hints bar 'ctrl+t variants  tab agents'; combined prompt_pattern uses negative lookahead to exclude 'esc interrupt' (busy state indicator)
- [Phase 13-01]: OpenCode v1.2.14 installed in Docker at /root/.opencode/bin/opencode; /exit exits cleanly in 1-2s (no hang regression); startup ~1.5s; prompt_pattern: r'^(?:\s*/a0\s+\d+\.\d+\.\d+\s*$|(?!.*esc interrupt).*ctrl\+t variants\s+tab agents)'
- [Phase 13-02]: CLI-04 exit via Ctrl+P palette + type 'exit' + Enter (not direct /exit send which triggers agent picker in v1.2.14)
- [Phase 13-02]: OPENCODE_PROMPT_PATTERN two-branch regex: startup (/a0 + version) OR post-response (ctrl+t without esc interrupt) — exported from tmux_tool.py for Phase 14
- [Phase 14-01]: OpenCodeSession constants (ANSI_RE, OPENCODE_PROMPT_PATTERN, OPENCODE_START_TIMEOUT) copied into opencode_cli.py with source comment — direct import from tmux_tool fails because agent.py dependency pulls nest_asyncio which is absent in standalone Python contexts
- [Phase 14-01]: OpenCodeSession is a sync class with time.sleep polling — asyncio is in Tool dispatch layer only; helper modules run synchronously matching claude_cli.py pattern
- [Phase 14-01]: send() returns full ANSI-stripped pane content (300 lines); differential response extraction deferred to Phase 15 SKILL.md
- [Phase 15-01]: usr/skills/cli-orchestration/SKILL.md documents both layers — tmux_tool primitive actions and OpenCodeSession high-level API; CLI-06 satisfied; Read-Detect-Write-Verify cycle established as the required interaction pattern for all interactive CLI orchestration

### Carried from v1.1

- CLAUDECODE fix is per-subprocess env only — never globally unset
- `ClaudeSession` uses `--resume UUID` for multi-turn
- `websocket-client>=1.9.0` required in requirements.txt

### Pending Todos

None yet.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-02-25
Stopped at: Completed 15-01-PLAN.md — Phase 15 done; v1.2 milestone complete
Resume file: None
