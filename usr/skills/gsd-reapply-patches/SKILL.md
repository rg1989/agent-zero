---
name: gsd-reapply-patches
description: Reapply local modifications after a GSD update
allowed-tools:
  - code_execution_tool
  - input
---

<purpose>
After a GSD update wipes and reinstalls files, this skill merges user's previously saved local modifications back into the new version. Uses intelligent comparison to handle cases where the upstream file also changed.
</purpose>

<process>

## Step 1: Detect backed-up patches

Check for local patches directory. The GSD local patches directory is located at the default path (typically `~/.claude/gsd-local-patches` for global installs, or `./.claude/gsd-local-patches` for local installs). Use `code_execution_tool` to check both locations:

```bash
if [ -d ~/.claude/gsd-local-patches ]; then
  PATCHES_DIR=~/.claude/gsd-local-patches
elif [ -d ./.claude/gsd-local-patches ]; then
  PATCHES_DIR=./.claude/gsd-local-patches
else
  PATCHES_DIR=""
fi
echo "$PATCHES_DIR"
```

Read `backup-meta.json` from the patches directory.

**If no patches found:**
```
No local patches found. Nothing to reapply.

Local patches are automatically saved when you run gsd-update
after modifying any GSD workflow, command, or agent files.
```
Exit.

## Step 2: Show patch summary

```
## Local Patches to Reapply

**Backed up from:** v{from_version}
**Current version:** {read VERSION file}
**Files modified:** {count}

| # | File | Status |
|---|------|--------|
| 1 | {file_path} | Pending |
| 2 | {file_path} | Pending |
```

## Step 3: Merge each file

For each file in `backup-meta.json`:

1. **Read the backed-up version** (user's modified copy from the patches directory)
2. **Read the newly installed version** (current file after update)
3. **Compare and merge:**

   - If the new file is identical to the backed-up file: skip (modification was incorporated upstream)
   - If the new file differs: identify the user's modifications and apply them to the new version

   **Merge strategy:**
   - Read both versions fully
   - Identify sections the user added or modified (look for additions, not just differences from path replacement)
   - Apply user's additions/modifications to the new version
   - If a section the user modified was also changed upstream: flag as conflict, show both versions, ask user which to keep

4. **Write merged result** to the installed location using `code_execution_tool`
5. **Report status:**
   - `Merged` — user modifications applied cleanly
   - `Skipped` — modification already in upstream
   - `Conflict` — user chose resolution

## Step 4: Update manifest

After reapplying, note which files were modified for future update tracking. The manifest will be regenerated automatically on the next update run.

## Step 5: Cleanup option

Ask user (use `input` tool):
- "Keep patch backups for reference?" → preserve the patches directory
- "Clean up patch backups?" → remove the patches directory

## Step 6: Report

```
## Patches Reapplied

| # | File | Status |
|---|------|--------|
| 1 | {file_path} | Merged |
| 2 | {file_path} | Skipped (already upstream) |
| 3 | {file_path} | Conflict resolved |

{count} file(s) updated. Your local modifications are active again.
```

</process>

<success_criteria>
- [ ] All backed-up patches processed
- [ ] User modifications merged into new version
- [ ] Conflicts resolved with user input
- [ ] Status reported for each file
</success_criteria>
