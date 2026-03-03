# Roadmap: Agent Zero Enhanced Fork

## Milestones

- ✅ **v1.0 Foundation & Apps System** - Phases 1-5 (shipped 2026-02-25)
- ✅ **v1.1 Reliability** - Phases 6-10 (shipped 2026-02-25)
- ✅ **v1.2 Terminal Orchestration** - Phases 11-15 (shipped 2026-02-25)
- 🚧 **v1.3 App Builder** - Phases 16-18 (in progress)

## Phases

<details>
<summary>✅ v1.0 Foundation & Apps System (Phases 1-5) - SHIPPED 2026-02-25</summary>

| Phase | Name | Status |
|-------|------|--------|
| 1 | Apps System Core | Complete |
| 2 | Core Built-in Apps | Complete |
| 3 | GSD Skill Pack | Complete |
| 4 | Neon UI + UX | Complete |
| 5 | Scaffolding + Skills | Complete |

</details>

<details>
<summary>✅ v1.1 Reliability (Phases 6-10) - SHIPPED 2026-02-25</summary>

| Phase | Name | Status |
|-------|------|--------|
| 6 | CDP Startup Health-Check | Complete |
| 7 | Browser Navigate-with-Verification | Complete |
| 8 | Claude CLI Single-Turn + Env Fix | Complete |
| 9 | Claude CLI Multi-Turn Sessions | Complete |
| 10 | Claude CLI Skill Documentation | Complete |

</details>

<details>
<summary>✅ v1.2 Terminal Orchestration (Phases 11-15) - SHIPPED 2026-02-25</summary>

| Phase | Name | Status |
|-------|------|--------|
| 11 | tmux Primitive Infrastructure | Complete |
| 12 | Readiness Detection | Complete |
| 13 | Interactive CLI Session Lifecycle | Complete |
| 14 | OpenCode Session Wrapper | Complete |
| 15 | CLI Orchestration Skill Documentation | Complete |

</details>

### 🚧 v1.3 App Builder (In Progress)

**Milestone Goal:** Agent Zero reliably creates, configures, and manages web apps using the Apps System -- every time, not just sometimes -- with a rich template library for instant scaffolding and intelligent template selection.

- [x] **Phase 16: Skill Reliability Core** - Rewrite web-app-builder SKILL.md with mandatory sequence enforcement, name validation, health verification, and system prompt integration so the agent always routes app requests correctly (completed 2026-03-03)
- [x] **Phase 17: Template Library Expansion** - Four new app templates (dashboard, file/media tool, CRUD app, utility SPA) built and working in apps/_templates/ (completed 2026-03-03)
- [ ] **Phase 18: Template Catalog and Auto-Selection** - Template catalog file, updated decision guide, and auto-selection logic so the agent picks the right template for each request

## Phase Details

### Phase 16: Skill Reliability Core
**Goal**: The agent recognizes every app creation request, routes it through the web-app-builder skill, and the skill enforces a bulletproof sequence -- allocate, copy, customize, register, start, verify -- with name validation and health checks that prevent broken deployments
**Depends on**: Nothing (existing infrastructure works; this rewrites the skill and adds system prompt awareness)
**Requirements**: SKILL-01, SKILL-02, SKILL-03, SKILL-04
**Success Criteria** (what must be TRUE):
  1. When a user asks "build me a todo app" or any app creation request, the agent uses the web-app-builder skill -- it never writes ad-hoc Flask scripts outside the Apps System
  2. The skill enforces a mandatory sequence (allocate port, copy template, customize, register, start, verify) and no step can be skipped -- if any step fails, the agent reports the failure instead of proceeding with a broken app
  3. Before registering an app, the agent validates the app name against reserved paths (`shared-browser`, `shared-terminal`, `webapp`, `ws`, etc.) and naming rules (lowercase, alphanumeric + hyphens) -- invalid names are rejected with a clear message
  4. After starting an app, the agent polls the app's allocated port (HTTP request) until it gets a response before declaring success to the user -- no more "your app is ready" when the process crashed on startup
**Plans**: 1 plan
Plans:
- [ ] 16-01-PLAN.md -- System prompt routing + SKILL.md rewrite with mandatory sequence, name validation, and health check

### Phase 17: Template Library Expansion
**Goal**: Four new production-quality app templates exist in `apps/_templates/` covering the most common app creation requests -- dashboards, file tools, CRUD apps, and lightweight utilities -- so the agent has a rich scaffolding library beyond the original three templates
**Depends on**: Nothing (templates are independent files; can be built in parallel with Phase 16)
**Requirements**: TMPL-01, TMPL-02, TMPL-03, TMPL-04
**Success Criteria** (what must be TRUE):
  1. A real-time dashboard template exists in `apps/_templates/` with periodic data refresh (JavaScript polling or SSE), at least one chart library (Chart.js or Plotly), and a responsive grid layout -- copying the template and starting the app produces a working dashboard with sample data
  2. A file/media tool template exists with drag-and-drop upload UI, a file listing page, download endpoints, and at least one format conversion capability -- copying and starting produces a working file manager
  3. A CRUD app template exists with SQLite database integration, a model definition pattern, and list/detail/create/edit/delete views -- copying and starting produces a working data management app with sample model
  4. A utility/tool SPA template exists as a minimal single-page skeleton suitable for calculators, text tools, viewers, and similar lightweight apps -- copying and starting produces a working single-page app with a sample tool
**Plans**: 3 plans
Plans:
- [ ] 17-01-PLAN.md -- Utility SPA template + real-time dashboard template (SSE + multi-chart)
- [ ] 17-02-PLAN.md -- CRUD app template (SQLite + list/detail/create/edit/delete views)
- [ ] 17-03-PLAN.md -- File/media tool template (drag-drop upload, listing, download, conversion)

### Phase 18: Template Catalog and Auto-Selection
**Goal**: The agent intelligently selects the best template for each user request using a catalog of all available templates and a decision guide -- and the user can override the selection if they prefer a different starting point
**Depends on**: Phase 16 (skill rewrite includes auto-selection hook), Phase 17 (new templates must exist to be cataloged)
**Requirements**: TMPL-05, TMPL-06, SKILL-05
**Success Criteria** (what must be TRUE):
  1. A template catalog file exists (in `apps/_templates/` or the skill directory) listing every available template with its description, typical use cases, and selection criteria -- the agent can read this file to understand what templates are available
  2. `apps/_templates/_GUIDE.md` is updated with a decision tree that covers all seven templates (three existing + four new) with clear "pick this when..." criteria
  3. When a user requests an app, the agent auto-selects the best-matching template based on the request and tells the user which template was chosen before proceeding -- the selection is visible in the conversation
  4. If the user asks to use a different template than the one auto-selected, the agent switches without friction -- override is a simple conversation, not a restart
**Plans**: TBD

## Progress

**Execution Order:**
Phases 16 and 17 can run in parallel (no dependencies between them). Phase 18 depends on both 16 and 17.

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Apps System Core | v1.0 | - | Complete | 2026-02-25 |
| 2. Core Built-in Apps | v1.0 | - | Complete | 2026-02-25 |
| 3. GSD Skill Pack | v1.0 | - | Complete | 2026-02-25 |
| 4. Neon UI + UX | v1.0 | - | Complete | 2026-02-25 |
| 5. Scaffolding + Skills | v1.0 | - | Complete | 2026-02-25 |
| 6. CDP Startup Health-Check | v1.1 | 1/1 | Complete | 2026-02-25 |
| 7. Browser Navigate-with-Verification | v1.1 | 1/1 | Complete | 2026-02-25 |
| 8. Claude CLI Single-Turn + Env Fix | v1.1 | 1/1 | Complete | 2026-02-25 |
| 9. Claude CLI Multi-Turn Sessions | v1.1 | 1/1 | Complete | 2026-02-25 |
| 10. Claude CLI Skill Documentation | v1.1 | 1/1 | Complete | 2026-02-25 |
| 11. tmux Primitive Infrastructure | v1.2 | 2/2 | Complete | 2026-02-25 |
| 12. Readiness Detection | v1.2 | 1/1 | Complete | 2026-02-25 |
| 13. Interactive CLI Session Lifecycle | v1.2 | 2/2 | Complete | 2026-02-25 |
| 14. OpenCode Session Wrapper | v1.2 | 1/1 | Complete | 2026-02-25 |
| 15. CLI Orchestration Skill Documentation | v1.2 | 1/1 | Complete | 2026-02-25 |
| 16. Skill Reliability Core | 1/1 | Complete    | 2026-03-03 | - |
| 17. Template Library Expansion | 3/3 | Complete   | 2026-03-03 | - |
| 18. Template Catalog and Auto-Selection | v1.3 | 0/? | Not started | - |
