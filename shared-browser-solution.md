# Implementation Guide: Transitioning from VNC to Playwright for Collaborative AI Browsing

This guide outlines the architectural shift from a **pixel-based VNC streaming stack** to a **DOM-native Playwright implementation** for your shared AI agent browser. By moving away from VNC, you solve the inherent issues of **unreliable agent control** and **UI rendering mismatches** caused by resolution scaling.

---

## 1. Why Remove the VNC Stack?

Your current implementation uses a "pixel-first" approach where a virtual display (`Xvfb`) is captured as a video stream (`x11vnc`) and sent to the UI. This creates three primary failure points:

*   **Resolution Mismatch:** Resizing a 1080p virtual desktop into a 420px drawer requires pixel scaling, which often makes text unreadable and UI elements hard for the agent to "see" accurately.
*   **Blind Control:** The agent drives the browser via CDP but the user only sees a delayed pixel stream; the agent cannot reliably "sense" if the user has manually moved a slider or clicked a button without a full DOM re-scan.
*   **High Latency:** The `websockify` bridge adds overhead that can lead to "action drift," where the agent clicks an element that has already moved or changed state.

**Switching to Playwright** allows you to treat the browser as a **DOM-native environment** where the agent and user interact with the actual code of the page, not a video of it.

---

## 2. Target Architecture: The "Embedded Orchestrator" Model

Instead of streaming a desktop, you will run a **headful Playwright instance** that is either rendered directly on the host machine (for local use) or managed via a **Live View interface** (for remote use).

### Key Components:
1.  **Playwright Core:** Handles direct browser control via **Chrome DevTools Protocol (CDP)**, ensuring actions like `click` and `type` are executed only when elements are "actionable".
2.  **Viewport Synchronization:** The browser is launched with a **fixed viewport** (e.g., 420px width) that matches your UI drawer, forcing websites to render their native mobile/responsive layouts.
3.  **Human-in-the-Loop (HIL) Loop:** A structured "Observe-Propose-Execute" cycle that allows the user to intervene at any stage.

---

## 3. Implementation Steps

### Step 1: Replace `Xvfb` with Playwright Context
In your `browser_agent.py`, replace the VNC connection logic with a **persistent browser context**. This allows the agent to maintain session state (cookies, logins) while giving the user visibility.

```python
# New implementation using Playwright
from playwright.sync_api import sync_playwright

def launch_shared_browser():
    pw = sync_playwright().start()
    # Launch headful so you can see it locally, or use a Live View proxy
    browser = pw.chromium.launch(headless=False) 
    
    # CRITICAL: Set viewport to your drawer size (420px) 
    # to solve rendering/scaling issues
    context = browser.new_context(
        viewport={'width': 420, 'height': 800},
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X)..."
    )
    return context.new_page()
```
*Note: Setting the viewport ensures the website renders correctly for the container size, removing the need for `xrandr` resizing.*

### Step 2: Implement the "Suggest-then-Execute" Loop
To prevent the agent and user from "fighting" over the cursor, implement a **collaborative execution module**.

1.  **Agent Proposes:** The LLM suggests an action (e.g., `click("#submit")`) and highlights the target element in the UI.
2.  **User Oversight:** The UI displays a **5-second countdown**; if the user does not "Pause" or "Reject," the agent executes the action.
3.  **Dynamic Adaptation:** If the user manually navigates to a new page, the agent's next "Observe" step detects the new URL and updates its internal state automatically.

### Step 3: Frontend Integration (Alpine.js)
Replace the VNC `<iframe>` with a **Live View component**. If running locally, you can simply embed the Playwright-controlled window. For remote setups, use an **Action Guard** interface that displays real-time screenshots and text-based action histories.

---

## 4. Solving Your Specific Problems

### How this solves Reliable Control:
Playwright uses **Auto-Waiting** and **Actionability Checks**. Before the agent clicks, Playwright verifies that the element is attached to the DOM, visible, stable (not moving), and enabled. This eliminates the "hit or miss" nature of VNC coordinates.

### How this solves UI Rendering:
By launching the browser with a `viewport` width of 420px, the browser engine itself handles the layout. You no longer have to scale a 1080p stream; the website will natively stack its elements for a narrow window, just like a mobile browser.

### How this solves User Interaction:
Using a **"Pause/Resume" mechanism**, the user can take full control of the browser at any time. Because the agent and user share the same **Playwright Page object**, any action the user takes (like solving a CAPTCHA) is immediately reflected in the agent's next DOM snapshot.

---

## 5. Security & Safety Gates
Because the agent now has direct DOM access, implement **Action Guards** for irreversible tasks.
*   **Irreversibility Heuristics:** Require manual approval for actions like `file_upload`, `payment_submission`, or `email_send`.
*   **Sandboxing:** Run the Playwright instance inside a **Docker container** to isolate the agent's browser from your local file system and personal browser cookies.

By following this DOM-native Playwright path, you move from a **visual stream** to **collaborative intelligence**, ensuring your homemade agent is both reliable and perfectly integrated into your UI.