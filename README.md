

## 🔀 Fork Enhancements

> This is a heavily extended fork of [frdel/agent-zero](https://github.com/frdel/agent-zero), built by **[Roman Grinevich](https://github.com/rg1989/)** — [LinkedIn](https://www.linkedin.com/in/roman-grinevich-03b13bab/).
> Nearly every commit beyond the initial setup represents original work — covering infrastructure, agent capabilities, UI, and structured workflows.
> Below is a summary of what has been built on top of the upstream base.

---

### 🧩 1. Smart App Hosting System — Port-Free, URL-First

The biggest infrastructure addition is a **first-class web app hosting layer** built directly into the Docker container. Agents can create, register, start, and stop web applications — each accessible at a clean `/{app-name}/` URL, with ports completely hidden from the user.

**How it works:**
- Apps run internally on ports `9000–9099`
- A FastAPI proxy middleware (`python/helpers/app_proxy.py`) routes `/{app-name}/` → the correct internal port, for both HTTP and WebSockets
- App metadata is stored in a persistent JSON registry (`apps/.app_registry.json`) that survives container restarts
- The `AppManager` singleton (`python/helpers/app_manager.py`) handles lifecycle: register, start, stop, restart, status, autostart
- A REST API (`/webapp`) lets agents and the UI manage the full app lifecycle programmatically

**Built-in apps:**
| App | Port | Description |
|-----|------|-------------|
| `shared-browser` | 9003 | Headless Chromium via CDP — agent + user browser |
| `shared-terminal` | 9004 | Web terminal via ttyd + tmux — agent + user terminal |

**Agent capability:** agents use a `web_app_builder` skill and templates to scaffold, register, and open new apps in the UI drawer — all without ever touching a port number.

---

### 🌐 2. Shared Browser — CDP Infrastructure for Agent + User

The shared browser replaces the legacy VNC stack with a **native Chrome DevTools Protocol (CDP)** implementation. Both the human user (via the in-UI browser panel) and the agent can interact with the same live Chromium instance.

**Technical highlights:**
- Headless Chromium runs inside Docker, exposed at port 9222 (CDP) and `9003` (control UI)
- `apps/shared-browser/app.py`: Flask server implementing a REST API over CDP WebSocket — screenshot, click, scroll, keyboard, navigate, evaluate JS
- `startup.sh`: polls CDP `/json` endpoint before marking the service ready (health-check, not a blind sleep)
- `usr/skills/shared-browser/SKILL.md`: documents the **Observe → Act → Verify** workflow pattern, including `navigate_and_wait()` which polls `document.readyState === 'complete'` after every navigation — no more race conditions
- Fully accessible to the agent via skills, and to the user via the UI drawer

---

### 💻 3. Shared Terminal — tmux Infrastructure for Agent + User

The shared terminal provides a **persistent tmux session** accessible from both the browser (via ttyd) and the agent (via tmux primitives).

**Architecture:**
- `apps/shared-terminal/startup.sh`: pre-creates a `tmux new-session -d -s shared` so the session survives UI disconnects
- ttyd serves the terminal in the browser at `/shared-terminal/`
- The agent interacts with the same session via `python/tools/tmux_tool.py`

**TmuxTool** (`python/tools/tmux_tool.py`) exposes five atomic primitives the agent calls directly:

| Action | Description |
|--------|-------------|
| `send` | Type text + Enter into the tmux pane |
| `keys` | Send special key combos (Ctrl+P, Tab, Escape, etc.) |
| `read` | Capture current pane content, ANSI-stripped |
| `wait_ready` | Poll until a shell prompt pattern appears or output stabilizes |

These primitives enable the agent to **act exactly like a human user at the keyboard** — including navigating TUI applications, responding to prompts, and reading live output.

---

### 🤖 4. CLI Orchestration — Claude Code & OpenCode via tmux (Subscription, Not API Key)

The most novel capability: the agent can **drive interactive coding CLIs** (Claude Code, OpenCode) as if it were a human user, **using a subscription account instead of paying per API token**.

This is architecturally significant — instead of calling Claude via API key, the agent launches Claude Code or OpenCode inside the shared tmux session, types prompts, reads responses, and chains multi-turn conversations. Cost: subscription flat rate. Quality: full model access.

#### Claude CLI (`python/helpers/claude_cli.py`)

- **Single-turn**: `claude_single_turn(prompt)` — subprocess call with `--print --output-format json`, parses response
- **Multi-turn**: `claude_turn(prompt, session_id)` — uses `--resume UUID` for stateful chaining; `ClaudeSession` wrapper auto-tracks session ID
- **Critical env fix**: `CLAUDECODE=1` is set by Claude Code and blocks nested `claude` binary launches. Fix: build a clean `env` dict per subprocess call, never mutating global `os.environ`
- **Dead session recovery**: `claude_turn_with_recovery()` detects expired sessions and restarts transparently

#### OpenCode (`python/helpers/opencode_cli.py`)

OpenCode runs as a full TUI inside tmux — there's no subprocess mode. The integration was built through **empirical observation** (documented in `.planning/phases/13-01-OBSERVATION.md`):

- `OpenCodeSession.start()`: launches OpenCode via `tmux send-keys`, waits for the specific prompt pattern
- `OpenCodeSession.send(prompt)`: types the prompt, waits for readiness using dual-strategy polling (prompt pattern match + output stability fallback)
- `OpenCodeSession.exit()`: uses Ctrl+P command palette → `exit` (NOT `/exit` — triggers an agent-picker bug in OpenCode v1.2.14)
- All ANSI escape codes stripped from captured output

#### CLI Orchestration Skill (`usr/skills/cli-orchestration/SKILL.md`)

Documents the complete orchestration patterns: when to use single-turn vs. multi-turn, session coordination, completion detection, security considerations, and anti-patterns to avoid.

---

### 📦 5. GSD Skill Pack — 50+ Structured Agent Skills

A full **Get Stuff Done (GSD)** skill pack is bundled in `usr/skills/`, using the open `SKILL.md` standard (compatible with Claude Code, Cursor, Codex CLI, Copilot, and Goose).

Skills are organized into four layers:

| Layer | Count | Examples |
|-------|-------|---------|
| **GSD Orchestrators** | 20+ | `plan-phase`, `execute-phase`, `verify-work`, `new-project`, `audit-milestone` |
| **GSD Subagents** | 10+ | `gsd-planner`, `gsd-executor`, `gsd-verifier`, `gsd-debugger`, `gsd-roadmapper` |
| **Specialist Roles** | 8 | `architect`, `backend-developer`, `frontend-developer`, `qa-tester`, `security-auditor` |
| **App & Skill Builders** | 3 | `web-app-builder`, `skill-forge`, `cli-orchestration` |

The GSD framework enables **structured, multi-phase project execution** with planning, verification, and gap-closure loops — all orchestrated by the agent itself using skills as its operational vocabulary.

---

### 🎨 6. Neon UI Theme

A custom **neon-mode UI theme** was applied to the webui (`webui/index.css`, ~38KB) with:
- Dynamic glow colors on hover (randomized per element, CSS `filter` based)
- Full dark/light mode support
- Styled app drawer with animated slide-in/out
- Clean tab system for managing open apps

---

### 🗺️ Planning-Driven Development

All enhancements were built using the GSD workflow, with a full planning directory (`.planning/`) tracking:
- `PROJECT.md` — goals, validated requirements, key decisions
- `ROADMAP.md` — phased milestones (v1.0 shipped, v1.1 shipped, v1.2 complete)
- Per-phase plans, research docs, observation files, and UAT results

**Shipped milestones:**

| Milestone | Phases | What was built |
|-----------|--------|----------------|
| v1.0 | 1–5 | Apps system, shared browser (noVNC→CDP), shared terminal, GSD skill pack, Neon UI |
| v1.1 | 6–10 | CDP startup health-check, navigate-with-verification, Claude CLI single + multi-turn |
| v1.2 | 11–15 | TmuxTool primitives, readiness detection, OpenCode lifecycle, OpenCodeSession, CLI orchestration skill |

---


<div align="center">

> ### 🚨 **AGENT ZERO SKILLS** 🚨
> **Skills System** - portable, structured agent capabilities using the open `SKILL.md` standard (compatible with Claude Code, Codex and more).
> 
> **Plus:** Git-based Projects with authentication for public/private repositories - clone codebases directly into isolated workspaces.
> 
> See [Usage Guide](./docs/guides/usage.md) and [Projects Tutorial](./docs/guides/projects.md) to get started.
</div>



[![Showcase](/docs/res/showcase-thumb.png)](https://youtu.be/lazLNcEYsiQ)


## A personal, organic agentic framework that grows and learns with you



- Agent Zero is not a predefined agentic framework. It is designed to be dynamic, organically growing, and learning as you use it.
- Agent Zero is fully transparent, readable, comprehensible, customizable, and interactive.
- Agent Zero uses the computer as a tool to accomplish its (your) tasks.

# ⚙️ Installation

Click to open a video to learn how to install Agent Zero:

[![Easy Installation guide](/docs/res/easy_ins_vid.png)](https://www.youtube.com/watch?v=w5v5Kjx51hs)

A detailed setup guide for Windows, macOS, and Linux with a video can be found in the Agent Zero Documentation at [this page](./docs/setup/installation.md).

### ⚡ Quick Start

```bash
# Pull and run with Docker

docker pull agent0ai/agent-zero
docker run -p 50001:80 agent0ai/agent-zero

# Visit http://localhost:50001 to start
```


# 💡 Key Features

1. **General-purpose Assistant**

- Agent Zero is not pre-programmed for specific tasks (but can be). It is meant to be a general-purpose personal assistant. Give it a task, and it will gather information, execute commands and code, cooperate with other agent instances, and do its best to accomplish it.
- It has a persistent memory, allowing it to memorize previous solutions, code, facts, instructions, etc., to solve tasks faster and more reliably in the future.

![Agent 0 Working](/docs/res/ui_screen2.png)

2. **Computer as a Tool**

- Agent Zero uses the operating system as a tool to accomplish its tasks. It has no single-purpose tools pre-programmed. Instead, it can write its own code and use the terminal to create and use its own tools as needed.
- The only default tools in its arsenal are online search, memory features, communication (with the user and other agents), and code/terminal execution. Everything else is created by the agent itself or can be extended by the user.
- Tool usage functionality has been developed from scratch to be the most compatible and reliable, even with very small models.
- **Default Tools:** Agent Zero includes tools like knowledge, code execution, and communication.
- **Creating Custom Tools:** Extend Agent Zero's functionality by creating your own custom tools.
- **Skills (SKILL.md Standard):** Skills are contextual expertise loaded dynamically when relevant. They use the open SKILL.md standard (developed by Anthropic), making them compatible with Claude Code, Cursor, Goose, OpenAI Codex CLI, and GitHub Copilot.

3. **Multi-agent Cooperation**

- Every agent has a superior agent giving it tasks and instructions. Every agent then reports back to its superior.
- In the case of the first agent in the chain (Agent 0), the superior is the human user; the agent sees no difference.
- Every agent can create its subordinate agent to help break down and solve subtasks. This helps all agents keep their context clean and focused.

![Multi-agent](docs/res/usage/multi-agent.png)

4. **Completely Customizable and Extensible**

- Almost nothing in this framework is hard-coded. Nothing is hidden. Everything can be extended or changed by the user.
- The whole behavior is defined by a system prompt in the **prompts/default/agent.system.md** file. Change this prompt and change the framework dramatically.
- The framework does not guide or limit the agent in any way. There are no hard-coded rails that agents have to follow.
- Every prompt, every small message template sent to the agent in its communication loop can be found in the **prompts/** folder and changed.
- Every default tool can be found in the **python/tools/** folder and changed or copied to create new predefined tools.
- **Automated configuration** via `A0_SET_` environment variables for deployment automation and easy setup.

![Prompts](/docs/res/profiles.png)

5. **Communication is Key**

- Give your agent a proper system prompt and instructions, and it can do miracles.
- Agents can communicate with their superiors and subordinates, asking questions, giving instructions, and providing guidance. Instruct your agents in the system prompt on how to communicate effectively.
- The terminal interface is real-time streamed and interactive. You can stop and intervene at any point. If you see your agent heading in the wrong direction, just stop and tell it right away.
- There is a lot of freedom in this framework. You can instruct your agents to regularly report back to superiors asking for permission to continue. You can instruct them to use point-scoring systems when deciding when to delegate subtasks. Superiors can double-check subordinates' results and dispute. The possibilities are endless.

## 🚀 Real-world use cases

- **Financial Analysis & Charting** - `"Find last month's Bitcoin/USD price trend, correlate with major cryptocurrency news events, generate annotated chart with highlighted key dates"`

- **Excel Automation Pipeline** - `"Scan incoming directory for financial spreadsheets, validate and clean data, consolidate from multiple sources, generate executive reports with flagged anomalies"`

- **API Integration Without Code** - `"Use this Google Gemini API snippet to generate product images, remember the integration for future use"` - agent learns and stores the solution in memory

- **Automated Server Monitoring** - `"Check server status every 30 minutes: CPU usage, disk space, memory. Alert if metrics exceed thresholds"` (scheduled task with project-scoped credentials)

- **Multi-Client Project Isolation** - Separate projects for each client with isolated memory, custom instructions, and dedicated secrets - prevents context bleed across sensitive work

## 🐳 Fully Dockerized, with Speech-to-Text and TTS

![Settings](docs/res/settings-page-ui1.png)

- Customizable settings allow users to tailor the agent's behavior and responses to their needs.
- The Web UI output is very clean, fluid, colorful, readable, and interactive; nothing is hidden.
- You can load or save chats directly within the Web UI.
- The same output you see in the terminal is automatically saved to an HTML file in **logs/** folder for every session.

![Time example](/docs/res/time_example.jpg)

- Agent output is streamed in real-time, allowing users to read along and intervene at any time.
- No coding is required; only prompting and communication skills are necessary.
- With a solid system prompt, the framework is reliable even with small models, including precise tool usage.

## 👀 Keep in Mind

1. **Agent Zero Can Be Dangerous!**

- With proper instruction, Agent Zero is capable of many things, even potentially dangerous actions concerning your computer, data, or accounts. Always run Agent Zero in an isolated environment (like Docker) and be careful what you wish for.

2. **Agent Zero Is Prompt-based.**

- The whole framework is guided by the **prompts/** folder. Agent guidelines, tool instructions, messages, utility AI functions, it's all there.


## 📚 Read the Documentation

| Page | Description |
|-------|-------------|
| [Installation](./docs/setup/installation.md) | Installation, setup and configuration |
| [Usage](./docs/guides/usage.md) | Basic and advanced usage |
| [Guides](./docs/guides/) | Step-by-step guides: Usage, Projects, API Integration, MCP Setup, A2A Setup |
| [Development Setup](./docs/setup/dev-setup.md) | Development and customization |
| [WebSocket Infrastructure](./docs/developer/websockets.md) | Real-time WebSocket handlers, client APIs, filtering semantics, envelopes |
| [Extensions](./docs/developer/extensions.md) | Extending Agent Zero |
| [Connectivity](./docs/developer/connectivity.md) | External API endpoints, MCP server connections, A2A protocol |
| [Architecture](./docs/developer/architecture.md) | System design and components |
| [Contributing](./docs/guides/contribution.md) | How to contribute |
| [Troubleshooting](./docs/guides/troubleshooting.md) | Common issues and their solutions |


## 🎯 Changelog

### v0.9.8 - Skills, UI Redesign & Git projects
[Release video](https://youtu.be/NV7s78yn6DY)

- Skills
    - Skills System replacing the legacy Instruments with a new `SKILL.md` standard for structured, portable agent capabilities.
    - Built-in skills, and UI support for importing and listing skills
- Real-time WebSocket infrastructure replacing the polling-based approach for UI state synchronization
- UI Redesign
    - Process groups to visually group agent actions with expand/collapse support
    - Timestamps, steps count and execution time with tool-specific badges
    - Step detail modals with key-value and raw JSON display
    - Collapsible responses with show more/less and copy buttons on code blocks and tables
    - Message queue system allowing users to queue messages while the agent is still processing
    - In-browser file editor for viewing and editing files without leaving the UI
    - Welcome screen redesign with info and warning banners for connection security, missing API keys, and system resources
    - Scheduler redesign with standalone modal, separate task list, detail and editor components, and project support
    - Smooth response rendering and scroll stabilization across chat, terminals, and image viewer
    - Chat width setting and reworked preferences panel
    - Image viewer improvements with scroll support and expanded viewer
    - Redesigned sidebar with reusable dropdown component and streamlined buttons
    - Inline button confirmations for critical actions
    - Improved login design and new logout button
    - File browser enhanced with rename and file actions dropdown
- Git projects
    - Git-based projects with clone authentication for public and private repositories
- Four new LLM providers: CometAPI, Z.AI, Moonshot AI, and AWS Bedrock
- Microsoft Dev Tunnels integration for secure remote access
- User data migration to `/usr` directory for cleaner separation of user and system files
- Subagents system with configurable agent profiles for different roles
- Memory operations offloaded to deferred tasks for better performance
- Environment variables can now configure settings via `A0_SET_*` prefix in `.env`
- Automatic migration with overwrite support for `.env`, scheduler, knowledge, and legacy directories
- Projects support extended to MCP, A2A, and external API
- Workdir outside project support for more flexible file organization
- Agent number tracking in backend and responses for multi-agent identification
- Many bug fixes and stability improvements across the UI, MCP tools, scheduler, uploads, and WebSocket handling


### v0.9.7 - Projects
[Release video](https://youtu.be/RrTDp_v9V1c)
- Projects management
    - Support for custom instructions
    - Integration with memory, knowledge, files
    - Project specific secrets 
- New Welcome screen/Dashboard
- New Wait tool
- Subordinate agent configuration override support
- Support for multiple documents at once in document_query_tool
- Improved context on interventions
- Openrouter embedding support
- Frontend components refactor and polishing
- SSH metadata output fix
- Support for windows powershell in local TTY utility
- More efficient selective streaming for LLMs
- UI output length limit improvements

### v0.9.6 - Memory Dashboard
[Release video](https://youtu.be/sizjAq2-d9s)
- Memory Management Dashboard
- Kali update
- Python update + dual installation
- Browser Use update
- New login screen
- LiteLLM retry on temporary errors
- Github Copilot provider support

### v0.9.5 - Secrets
[Release video](https://www.youtube.com/watch?v=VqxUdt7pjd8)
- Secrets management - agent can use credentials without seeing them
- Agent can copy paste messages and files without rewriting them
- LiteLLM global configuration field
- Custom HTTP headers field for browser agent
- Progressive web app support
- Extra model params support for JSON
- Short IDs for files and memories to prevent LLM errors
- Tunnel component frontend rework
- Fix for timezone change bug
- Notifications z-index fix

### v0.9.4 - Connectivity, UI
[Release video](https://www.youtube.com/watch?v=C2BAdDOduIc)
- External API endpoints
- Streamable HTTP MCP A0 server
- A2A (Agent to Agent) protocol - server+client
- New notifications system
- New local terminal interface for stability
- Rate limiter integration to models
- Delayed memory recall
- Smarter autoscrolling in UI
- Action buttons in messages
- Multiple API keys support
- Download streaming
- Tunnel URL QR code
- Internal fixes and optimizations

### v0.9.3 - Subordinates, memory, providers Latest
[Release video](https://www.youtube.com/watch?v=-LfejFWL34k)
- Faster startup/restart
- Subordinate agents can have dedicated prompts, tools and system extensions
- Streamable HTTP MCP server support
- Memory loading enhanced by AI filter
- Memory AI consolidation when saving memories
- Auto memory system configuration in settings
- LLM providers available are set by providers.yaml configuration file
- Venice.ai LLM provider supported
- Initial agent message for user + as example for LLM
- Docker build support for local images
- File browser fix

### v0.9.2 - Kokoro TTS, Attachments
[Release video](https://www.youtube.com/watch?v=sPot_CAX62I)

- Kokoro text-to-speech integration
- New message attachments system
- Minor updates: log truncation, hyperlink targets, component examples, api cleanup

### v0.9.1 - LiteLLM, UI improvements
[Release video](https://youtu.be/crwr0M4Spcg)
- Langchain replaced with LiteLLM
    - Support for reasoning models streaming
    - Support for more providers
    - Openrouter set as default instead of OpenAI
- UI improvements
    - New message grouping system
    - Communication smoother and more efficient
    - Collapsible messages by type
    - Code execution tool output improved
    - Tables and code blocks scrollable
    - More space efficient on mobile
- Streamable HTTP MCP servers support
- LLM API URL added to models config for Azure, local and custom providers

### v0.9.0 - Agent roles, backup/restore
[Release video](https://www.youtube.com/watch?v=rMIe-TC6H-k)
- subordinate agents can use prompt profiles for different roles
- backup/restore functionality for easier upgrades
- security and bug fixes

### v0.8.7 - Formatting, Document RAG Latest
[Release video](https://youtu.be/OQJkfofYbus)
- markdown rendering in responses
- live response rendering
- document Q&A tool

### v0.8.6 - Merge and update
[Release video](https://youtu.be/l0qpK3Wt65A)
- Merge with Hacking Edition
- browser-use upgrade and integration re-work
- tunnel provider switch

### v0.8.5 - **MCP Server + Client**
[Release video](https://youtu.be/pM5f4Vz3_IQ)

- Agent Zero can now act as MCP Server
- Agent Zero can use external MCP servers as tools

### v0.8.4.1 - 2
Default models set to gpt-4.1
- Code execution tool improvements
- Browser agent improvements
- Memory improvements
- Various bugfixes related to context management
- Message formatting improvements
- Scheduler improvements
- New model provider
- Input tool fix
- Compatibility and stability improvements

### v0.8.4
[Release video](https://youtu.be/QBh_h_D_E24)

- **Remote access (mobile)**

### v0.8.3.1
[Release video](https://youtu.be/AGNpQ3_GxFQ)

- **Automatic embedding**

### v0.8.3
[Release video](https://youtu.be/bPIZo0poalY)

- ***Planning and scheduling***

### v0.8.2
[Release video](https://youtu.be/xMUNynQ9x6Y)

- **Multitasking in terminal**
- **Chat names**

### v0.8.1
[Release video](https://youtu.be/quv145buW74)

- **Browser Agent**
- **UX Improvements**

### v0.8
[Release video](https://youtu.be/cHDCCSr1YRI)

- **Docker Runtime**
- **New Messages History and Summarization System**
- **Agent Behavior Change and Management**
- **Text-to-Speech (TTS) and Speech-to-Text (STT)**
- **Settings Page in Web UI**
- **SearXNG Integration Replacing Perplexity + DuckDuckGo**
- **File Browser Functionality**
- **KaTeX Math Visualization Support**
- **In-chat File Attachments**

### v0.7
[Release video](https://youtu.be/U_Gl0NPalKA)

- **Automatic Memory**
- **UI Improvements**
- **Instruments**
- **Extensions Framework**
- **Reflection Prompts**
- **Bug Fixes**

## 🤝 Community and Support

- [Join our Discord](https://discord.gg/B8KZKNsPpj) for live discussions or [visit our Skool Community](https://www.skool.com/agent-zero).
- [Follow our YouTube channel](https://www.youtube.com/@AgentZeroFW) for hands-on explanations and tutorials
- [Report Issues](https://github.com/agent0ai/agent-zero/issues) for bug fixes and features
