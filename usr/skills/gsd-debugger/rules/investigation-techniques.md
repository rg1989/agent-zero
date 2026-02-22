# Investigation Techniques

Six systematic techniques for investigating bugs. Use multiple techniques together for best results.

## Meta-Debugging Philosophy

**User = Reporter, You = Investigator.** The user knows symptoms; you find the cause. Never ask the user what's causing the bug — investigate it yourself.

**When debugging your own code:** Treat it as foreign. Your implementation decisions are hypotheses, not facts. The code's behavior is truth; your mental model is a guess. Prioritize code you recently touched.

**Cognitive biases to avoid:**

| Bias | Trap | Antidote |
|------|------|----------|
| **Confirmation** | Only look for evidence supporting your hypothesis | Actively seek disconfirming evidence. "What would prove me wrong?" |
| **Anchoring** | First explanation becomes your anchor | Generate 3+ independent hypotheses before investigating any |
| **Availability** | Recent bugs → assume similar cause | Treat each bug as novel until evidence suggests otherwise |
| **Sunk Cost** | Spent 2 hours on one path, keep going despite evidence | Every 30 min: "If I started fresh, is this still the path I'd take?" |

**Systematic disciplines:**
- Change one variable at a time. Multiple changes = no idea what mattered.
- Read entire functions, not just "relevant" lines. Skimming misses crucial details.
- "I don't know why this fails" = good. "It must be X" = dangerous.

**When to restart:** Consider starting over when: 2+ hours with no progress, 3+ failed fixes, you can't explain the current behavior, or the fix works but you don't know why. Restart protocol: write certainties, list what's been ruled out, form new hypotheses (different from before), begin again from evidence gathering.

## Binary Search / Divide and Conquer

**When:** Large codebase, long execution path, many possible failure points.

**How:** Cut problem space in half repeatedly until you isolate the issue.

1. Identify boundaries (where works, where fails)
2. Add logging/testing at midpoint
3. Determine which half contains the bug
4. Repeat until you find exact line

**Example:** API returns wrong data
- Test: Data leaves database correctly? YES
- Test: Data reaches frontend correctly? NO
- Test: Data leaves API route correctly? YES
- Test: Data survives serialization? NO
- **Found:** Bug in serialization layer (4 tests eliminated 90% of code)

## Rubber Duck Debugging

**When:** Stuck, confused, mental model doesn't match reality.

**How:** Explain the problem out loud in complete detail.

Write or say:
1. "The system should do X"
2. "Instead it does Y"
3. "I think this is because Z"
4. "The code path is: A -> B -> C -> D"
5. "I've verified that..." (list what you tested)
6. "I'm assuming that..." (list assumptions)

Often you'll spot the bug mid-explanation: "Wait, I never verified that B returns what I think it does."

## Minimal Reproduction

**When:** Complex system, many moving parts, unclear which part fails.

**How:** Strip away everything until smallest possible code reproduces the bug.

1. Copy failing code to new file
2. Remove one piece (dependency, function, feature)
3. Test: Does it still reproduce? YES = keep removed. NO = put back.
4. Repeat until bare minimum
5. Bug is now obvious in stripped-down code

**Example:**
```jsx
// Start: 500-line React component with 15 props, 8 hooks, 3 contexts
// End after stripping:
function MinimalRepro() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    setCount(count + 1); // Bug: infinite loop, missing dependency array
  });

  return <div>{count}</div>;
}
// The bug was hidden in complexity. Minimal reproduction made it obvious.
```

## Working Backwards

**When:** You know correct output, don't know why you're not getting it.

**How:** Start from desired end state, trace backwards.

1. Define desired output precisely
2. What function produces this output?
3. Test that function with expected input - does it produce correct output?
   - YES: Bug is earlier (wrong input)
   - NO: Bug is here
4. Repeat backwards through call stack
5. Find divergence point (where expected vs actual first differ)

**Example:** UI shows "User not found" when user exists
```
Trace backwards:
1. UI displays: user.error → Is this the right value to display? YES
2. Component receives: user.error = "User not found" → Correct? NO, should be null
3. API returns: { error: "User not found" } → Why?
4. Database query: SELECT * FROM users WHERE id = 'undefined' → AH!
5. FOUND: User ID is 'undefined' (string) instead of a number
```

## Differential Debugging

**When:** Something used to work and now doesn't. Works in one environment but not another.

**Time-based (worked, now doesn't):**
- What changed in code since it worked?
- What changed in environment? (Node version, OS, dependencies)
- What changed in data?
- What changed in configuration?

**Environment-based (works in dev, fails in prod):**
- Configuration values
- Environment variables
- Network conditions (latency, reliability)
- Data volume
- Third-party service behavior

**Process:** List differences, test each in isolation, find the difference that causes failure.

**Example:** Works locally, fails in CI
```
Differences:
- Node version: Same ✓
- Environment variables: Same ✓
- Timezone: Different! ✗

Test: Set local timezone to UTC (like CI)
Result: Now fails locally too
FOUND: Date comparison logic assumes local timezone
```

**Git Bisect (for time-based):**
```bash
git bisect start
git bisect bad              # Current commit is broken
git bisect good abc123      # This commit worked
# Git checks out middle commit
git bisect bad              # or good, based on testing
# Repeat until culprit found
```

100 commits between working and broken: ~7 tests to find exact breaking commit.

## Observability First

**When:** Always. Before making any fix.

**Add visibility before changing behavior:**

```javascript
// Strategic logging (useful):
console.log('[handleSubmit] Input:', { email, password: '***' });
console.log('[handleSubmit] Validation result:', validationResult);
console.log('[handleSubmit] API response:', response);

// Assertion checks:
console.assert(user !== null, 'User is null!');
console.assert(user.id !== undefined, 'User ID is undefined!');

// Timing measurements:
console.time('Database query');
const result = await db.query(sql);
console.timeEnd('Database query');

// Stack traces at key points:
console.log('[updateUser] Called from:', new Error().stack);
```

**Workflow:** Add logging -> Run code -> Observe output -> Form hypothesis -> Then make changes.

## Comment Out Everything

**When:** Many possible interactions, unclear which code causes issue.

**How:**
1. Comment out everything in function/file
2. Verify bug is gone
3. Uncomment one piece at a time
4. After each uncomment, test
5. When bug returns, you found the culprit

**Example:** Some middleware breaks requests, but you have 8 middleware functions
```javascript
app.use(helmet()); // Uncomment, test → works
app.use(cors()); // Uncomment, test → works
app.use(compression()); // Uncomment, test → works
app.use(bodyParser.json({ limit: '50mb' })); // Uncomment, test → BREAKS
// FOUND: Body size limit too high causes memory issues
```

## Technique Selection Guide

| Situation | Technique |
|-----------|-----------|
| Large codebase, many files | Binary search |
| Confused about what's happening | Rubber duck, Observability first |
| Complex system, many interactions | Minimal reproduction |
| Know the desired output | Working backwards |
| Used to work, now doesn't | Differential debugging, Git bisect |
| Many possible causes | Comment out everything, Binary search |
| Always | Observability first (before making changes) |

## Combining Techniques

Techniques compose. Often you'll use multiple together:

1. **Differential debugging** to identify what changed
2. **Binary search** to narrow down where in code
3. **Observability first** to add logging at that point
4. **Rubber duck** to articulate what you're seeing
5. **Minimal reproduction** to isolate just that behavior
6. **Working backwards** to find the root cause

## Research vs. Reasoning

**Use web search (search_engine) when:**
- Error messages from unfamiliar libraries (search exact message in quotes)
- Library/framework behavior doesn't match expectations (check official docs)
- Domain knowledge gaps (auth flows, database indexes, platform differences)
- Recent ecosystem changes (package updates, new framework versions)

**Use code reasoning when:**
- Bug is in YOUR code (read, trace, add logging)
- You have all information needed
- Logic error (off-by-one, wrong conditional, state management)
- Answer is in behavior, not documentation

**Balance:** Start with 5-10 min search if error is unfamiliar. If no answers, switch to reasoning. Alternate as needed.
