# Goal-Backward Methodology

How to derive must_haves (truths, artifacts, key_links) from the phase goal.

## The Problem with Forward Planning

Forward planning asks: "What should we build?" → produces tasks.

This fails because tasks can be "complete" without achieving the goal. You build what you planned, not what was needed.

Goal-backward asks: "What must be TRUE for the goal to be achieved?" → produces requirements tasks must satisfy. Every task earns its place by contributing to a truth.

## The 5-Step Process

### Step 0: Extract Requirement IDs

Read ROADMAP.md `**Requirements:**` line for this phase. Strip brackets if present (e.g., `[AUTH-01, AUTH-02]` → `AUTH-01, AUTH-02`). Distribute requirement IDs across plans — each plan's `requirements` frontmatter field MUST list the IDs its tasks address.

**CRITICAL:** Every requirement ID MUST appear in at least one plan. Plans with an empty `requirements` field are invalid.

### Step 1: State the Goal

Take phase goal from ROADMAP.md. Must be outcome-shaped, not task-shaped.
- Good: "Working chat interface" (outcome)
- Bad: "Build chat components" (task)

### Step 2: Derive Observable Truths

"What must be TRUE for this goal to be achieved?" List 3-7 truths from USER's perspective.

For "working chat interface":
- User can see existing messages
- User can type a new message
- User can send the message
- Sent message appears in the list
- Messages persist across page refresh

**Test:** Each truth verifiable by a human using the application.

### Step 3: Derive Required Artifacts

For each truth: "What must EXIST for this to be true?"

"User can see existing messages" requires:
- Message list component (renders Message[])
- Messages state (loaded from somewhere)
- API route or data source (provides messages)
- Message type definition (shapes the data)

**Test:** Each artifact = a specific file or database object.

### Step 4: Derive Required Wiring

For each artifact: "What must be CONNECTED for this to function?"

Message list component wiring:
- Imports Message type (not using `any`)
- Receives messages prop or fetches from API
- Maps over messages to render (not hardcoded)
- Handles empty state (not just crashes)

### Step 5: Identify Key Links

"Where is this most likely to break?" Key links = critical connections where breakage causes cascading failures.

For chat interface:
- Input onSubmit -> API call (if broken: typing works but sending doesn't)
- API save -> database (if broken: appears to send but doesn't persist)
- Component -> real data (if broken: shows placeholder, not messages)

## Must-Haves Output Format

```yaml
must_haves:
  truths:
    - "User can see existing messages"
    - "User can send a message"
    - "Messages persist across refresh"
  artifacts:
    - path: "src/components/Chat.tsx"
      provides: "Message list rendering"
      min_lines: 30
    - path: "src/app/api/chat/route.ts"
      provides: "Message CRUD operations"
      exports: ["GET", "POST"]
    - path: "prisma/schema.prisma"
      provides: "Message model"
      contains: "model Message"
  key_links:
    - from: "src/components/Chat.tsx"
      to: "/api/chat"
      via: "fetch in useEffect"
      pattern: "fetch.*api/chat"
    - from: "src/app/api/chat/route.ts"
      to: "prisma.message"
      via: "database query"
      pattern: "prisma\\.message\\.(find|create)"
```

## Common Failures

**Truths too vague:**
- Bad: "User can use chat"
- Good: "User can see messages", "User can send message", "Messages persist"

**Artifacts too abstract:**
- Bad: "Chat system", "Auth module"
- Good: "src/components/Chat.tsx", "src/app/api/auth/login/route.ts"

**Missing wiring:**
- Bad: Listing components without how they connect
- Good: "Chat.tsx fetches from /api/chat via useEffect on mount"

**Key links too generic:**
- Bad: "Components connected"
- Good: Specific from/to/via/pattern that a verification agent can grep for

## Self-Check Before Returning Plans

For each plan, verify:
- [ ] Every locked decision from CONTEXT.md has a task implementing it
- [ ] No task implements a deferred idea from CONTEXT.md
- [ ] Every requirement ID from ROADMAP appears in at least one plan's `requirements` field
- [ ] Each truth is verifiable by a human user
- [ ] Each artifact has a specific file path
- [ ] Each key link has a grep-able pattern

## Dependency Graph Building

Before grouping tasks into plans, build the dependency graph explicitly.

**For each task record:**
- `needs`: What must exist before this runs
- `creates`: What this produces
- `has_checkpoint`: Requires user interaction?

**Wave assignment:**
```
if plan.depends_on is empty:
  plan.wave = 1
else:
  plan.wave = max(waves[dep] for dep in plan.depends_on) + 1
```

**Prefer vertical slices (parallel) over horizontal layers (sequential):**

Vertical slices (PREFER):
```
Plan 01: User feature (model + API + UI)    ← Wave 1
Plan 02: Product feature (model + API + UI) ← Wave 1
```

Horizontal layers (AVOID):
```
Plan 01: Create all models    ← Wave 1
Plan 02: Create all APIs      ← Wave 2 (blocked by 01)
Plan 03: Create all UIs       ← Wave 3 (blocked by 02)
```

**File ownership:** Each file belongs to ONE plan. If two plans touch the same file, the later plan depends on the earlier one.
