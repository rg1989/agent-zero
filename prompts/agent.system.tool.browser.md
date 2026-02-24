### browser_agent:

Controls a browser to navigate websites, click, fill forms, extract content, etc.

**NEVER attempt to use playwright, python scripts, or terminal commands to control any browser directly. This tool is the only correct way to interact with browsers.**

**TWO MODES — choose the right one:**

#### `use_shared=false` (default) — hidden headless browser
- Runs an invisible browser the user **cannot see**
- Use only for background/silent data extraction tasks
- ⚠️ If you use this mode when the user wants to see the browser, nothing will happen visibly

#### `use_shared=true` — shared browser panel (VISIBLE TO USER)
- Controls the **same Chromium instance shown in the right-side drawer**
- The user sees every navigation, click, and scroll in real time
- **Always use this mode when the user wants to watch** or you want to demonstrate something
- **REQUIRED STEP BEFORE USE**: call `open_app` first to start the browser and open the drawer:
  `open_app` → `{ "action": "open", "app": "shared-browser" }`

**⚠️ CRITICAL — when the user says "use the shared browser", "navigate the shared browser", "show me", or "let me watch", you MUST:**
1. Call `open_app` → `{ "action": "open", "app": "shared-browser" }` first
2. Then call `browser_agent` with `"use_shared": "true"`

**Calling `browser_agent` without `"use_shared": "true"` runs a hidden browser the user CANNOT see — it will appear as if nothing happened.**

#### Arguments:
* `message` (string, required) — task instructions for the browser agent; be specific and end with "end task"
* `reset` (string) — `"true"` to start a fresh session, `"false"` to continue (default)
* `use_shared` (string) — `"true"` to control the visible shared browser, `"false"` for hidden headless (default)

#### Usage: show the user something in the shared browser
```json
{
    "thoughts": ["I'll open the shared browser and navigate there visibly."],
    "tool_name": "open_app",
    "tool_args": { "action": "open", "app": "shared-browser" }
}
```
then:
```json
{
    "thoughts": ["Navigating in the visible shared browser so the user can see."],
    "headline": "Opening page in shared browser",
    "tool_name": "browser_agent",
    "tool_args": {
        "message": "Go to https://example.com and end task",
        "reset": "true",
        "use_shared": "true"
    }
}
```

#### Usage: silent background browsing (user does NOT need to see)
```json
{
    "thoughts": ["Extracting data quietly in the background."],
    "headline": "Fetching page data",
    "tool_name": "browser_agent",
    "tool_args": {
        "message": "Open https://example.com, extract all product names, end task",
        "reset": "true",
        "use_shared": "false"
    }
}
```

#### Usage: continue existing session
```json
{
    "thoughts": ["Continuing the open session."],
    "headline": "Continuing with existing browser session",
    "tool_name": "browser_agent",
    "tool_args": {
        "message": "Considering open pages, click the login button and end task",
        "reset": "false",
        "use_shared": "true"
    }
}
```

Other notes:
- downloads default to /a0/tmp/downloads
- pass secrets and credentials in `message` when needed
- when following up an existing session start message with: "Considering open pages, ..."
- don't use phrase "wait for instructions" — use "end task" instead
