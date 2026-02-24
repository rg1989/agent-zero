### open_app:
Opens, closes, or manages tabs in the integrated app drawer — a side panel that slides in from the right of the chat, showing live apps in browser-like tabs. Multiple apps can be open as tabs simultaneously. Use it proactively to show the user something in the shared browser or any other running app.

!!! The drawer shrinks the chat area (does NOT cover it) — both stay visible at the same time
!!! Each app gets its own tab; switching tabs does not reload the app
!!! The drawer toggle is only shown when at least one tab is open
!!! Always open the drawer BEFORE calling browser_agent with use_shared=true — the user needs to see the panel
!!! The shared browser's Chromium is reachable at localhost:9222 (used by browser_agent use_shared=true)
!!! Always open the drawer BEFORE calling terminal_agent — the user needs to see the terminal panel
!!! Available core apps: "shared-browser" (collaborative browser), "shared-terminal" (persistent tmux shell)

#### Arguments:
 * "action" (string, required) : "open" to add an app tab and show it, "close" to hide the drawer (tabs stay), "close_tab" to remove a specific tab.
 * "app" (string, required for "open" and "close_tab") : The registered app name, e.g. "shared-browser".

#### Usage examples:
##### 1: Open shared browser in the drawer
```json
{
    "thoughts": ["Opening the shared browser so the user can watch me navigate."],
    "tool_name": "open_app",
    "tool_args": { "action": "open", "app": "shared-browser" }
}
```
##### 2: Open a second app as a new tab
```json
{
    "thoughts": ["Adding another app tab while keeping shared-browser open."],
    "tool_name": "open_app",
    "tool_args": { "action": "open", "app": "my-dashboard" }
}
```
##### 3: Close a specific tab
```json
{
    "thoughts": ["Closing the shared-browser tab."],
    "tool_name": "open_app",
    "tool_args": { "action": "close_tab", "app": "shared-browser" }
}
```
##### 4: Hide the drawer (keep tabs loaded)
```json
{
    "thoughts": ["Hiding the drawer but keeping the apps loaded."],
    "tool_name": "open_app",
    "tool_args": { "action": "close" }
}
```
