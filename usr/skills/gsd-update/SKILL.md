---
name: gsd-update
description: Update GSD to latest version with changelog display
allowed-tools:
  - code_execution_tool
  - input
---

<objective>
Check for GSD updates, install if available, and display what changed.

Handles:
- Version detection (local vs global installation)
- npm version checking
- Changelog fetching and display
- User confirmation with clean install warning
- Update execution and cache clearing
- Restart reminder
</objective>

<process>

<step name="get_installed_version">
Detect whether GSD is installed locally or globally by checking both locations using `code_execution_tool`:

```bash
if [ -f ./.claude/get-shit-done/VERSION ]; then
  cat ./.claude/get-shit-done/VERSION
  echo "LOCAL"
elif [ -f ~/.claude/get-shit-done/VERSION ]; then
  cat ~/.claude/get-shit-done/VERSION
  echo "GLOBAL"
else
  echo "UNKNOWN"
fi
```

Parse output:
- If last line is "LOCAL": installed version is first line, use `--local` flag for update
- If last line is "GLOBAL": installed version is first line, use `--global` flag for update
- If "UNKNOWN": proceed to install step (treat as version 0.0.0)

**If VERSION file missing:**
```
## GSD Update

**Installed version:** Unknown

Your installation doesn't include version tracking.

Running fresh install...
```

Proceed to install step (treat as version 0.0.0 for comparison).
</step>

<step name="check_latest_version">
Check npm for latest version using `code_execution_tool`:

```bash
npm view get-shit-done-cc version 2>/dev/null
```

**If npm check fails:**
```
Couldn't check for updates (offline or npm unavailable).

To update manually: `npx get-shit-done-cc --global`
```

Exit.
</step>

<step name="compare_versions">
Compare installed vs latest:

**If installed == latest:**
```
## GSD Update

**Installed:** X.Y.Z
**Latest:** X.Y.Z

You're already on the latest version.
```

Exit.

**If installed > latest:**
```
## GSD Update

**Installed:** X.Y.Z
**Latest:** A.B.C

You're ahead of the latest release (development version?).
```

Exit.
</step>

<step name="show_changes_and_confirm">
**If update available**, fetch and show what's new BEFORE updating:

1. Fetch changelog from GitHub raw URL using `code_execution_tool`
2. Extract entries between installed and latest versions
3. Display preview and ask for confirmation using `input`:

```
## GSD Update Available

**Installed:** 1.5.10
**Latest:** 1.5.15

### What's New
────────────────────────────────────────────────────────────

## [1.5.15] - 2026-01-20

### Added
- Feature X

## [1.5.14] - 2026-01-18

### Fixed
- Bug fix Y

────────────────────────────────────────────────────────────

**Note:** The installer performs a clean install of GSD folders:
- `commands/gsd/` will be wiped and replaced
- `get-shit-done/` will be wiped and replaced
- `agents/gsd-*` files will be replaced

(Paths are relative to your install location: `~/.claude/` for global, `./.claude/` for local)

Your custom files in other locations are preserved:
- Custom commands not in `commands/gsd/` ✓
- Custom agents not prefixed with `gsd-` ✓
- Custom hooks ✓
- Your CLAUDE.md files ✓

If you've modified any GSD files directly, they'll be automatically backed up to `gsd-local-patches/` and can be reapplied with gsd-reapply-patches after the update.
```

Ask user: "Proceed with update?" (options: "Yes, update now" / "No, cancel")

**If user cancels:** Exit.
</step>

<step name="run_update">
Run the update using the install type detected in the first step using `code_execution_tool`:

**If LOCAL install:**
```bash
npx get-shit-done-cc --local
```

**If GLOBAL install (or unknown):**
```bash
npx get-shit-done-cc --global
```

Capture output. If install fails, show error and exit.

Clear the update cache so statusline indicator disappears:

**If LOCAL install:**
```bash
rm -f ./.claude/cache/gsd-update-check.json
```

**If GLOBAL install:**
```bash
rm -f ~/.claude/cache/gsd-update-check.json
```
</step>

<step name="display_result">
Format completion message (changelog was already shown in confirmation step):

```
╔═══════════════════════════════════════════════════════════╗
║  GSD Updated: v1.5.10 → v1.5.15                           ║
╚═══════════════════════════════════════════════════════════╝

Restart your agent environment to pick up the new commands.

View full changelog: https://github.com/glittercowboy/get-shit-done/blob/main/CHANGELOG.md
```
</step>

<step name="check_local_patches">
After update completes, check if the installer detected and backed up any locally modified files.

Use `code_execution_tool` to check for backup metadata:
```bash
ls ~/.claude/gsd-local-patches/backup-meta.json 2>/dev/null || ls ./.claude/gsd-local-patches/backup-meta.json 2>/dev/null
```

**If patches found:**

```
Local patches were backed up before the update.
Use the gsd-reapply-patches skill to merge your modifications into the new version.
```

**If no patches:** Continue normally.
</step>
</process>

<success_criteria>
- [ ] Installed version read correctly
- [ ] Latest version checked via npm
- [ ] Update skipped if already current
- [ ] Changelog fetched and displayed BEFORE update
- [ ] Clean install warning shown
- [ ] User confirmation obtained
- [ ] Update executed successfully
- [ ] Restart reminder shown
</success_criteria>
