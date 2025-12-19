# Hydra Persistent Memory Architecture
## Cognitive Memory System Design

> **Goal**: Enable Claude to maintain context, learn preferences, remember decisions, and operate with accumulated wisdom across sessions.

---

## Memory Tiers (Inspired by Cognitive Science)

### 1. CORE MEMORY (`core.yaml`)
**Purpose**: Immutable truths, constitutional constraints, identity
**Update Frequency**: Rarely (only with explicit user approval)
**Read at**: Every session start

Contains:
- Constitutional constraints (NEVER violate)
- System identity and purpose
- Immutable infrastructure facts (IPs, node roles)
- Critical safety rules

### 2. USER MEMORY (`user.yaml`)
**Purpose**: Everything about Shaun - preferences, patterns, communication style
**Update Frequency**: As learned during sessions
**Read at**: Every session start

Contains:
- Communication preferences
- Technical preferences (languages, frameworks, tools)
- Work patterns (when active, response expectations)
- Learned dislikes and pet peeves
- Project priorities

### 3. DECISIONS MEMORY (`decisions.yaml`)
**Purpose**: Architectural decisions and their rationale (ADRs)
**Update Frequency**: When significant decisions are made
**Read at**: When working on related features

Contains:
- Past decisions with context and rationale
- Alternatives considered
- Outcomes observed
- Lessons learned

### 4. WORKING MEMORY (`working.yaml`)
**Purpose**: Current context, active tasks, recent focus
**Update Frequency**: Every session
**Read at**: Every session start

Contains:
- Current active priorities
- In-progress work items
- Recent context that carries forward
- Unresolved questions

### 5. PATTERNS MEMORY (`patterns.yaml`)
**Purpose**: Learned patterns - what works, what doesn't
**Update Frequency**: As patterns emerge
**Read at**: When relevant

Contains:
- Effective approaches discovered
- Anti-patterns to avoid
- Debugging patterns for common issues
- Performance optimizations found

### 6. EPISODIC MEMORY (`episodes/`)
**Purpose**: Significant events and their outcomes
**Update Frequency**: After notable events
**Read at**: When relevant context needed

Contains:
- Major accomplishments
- Failures and root causes
- User feedback moments
- System incidents

---

## File Structure

```
/mnt/user/appdata/hydra-dev/memory/
├── core.yaml                # Immutable truths
├── user.yaml                # User preferences
├── decisions.yaml           # ADR-style decisions
├── working.yaml             # Current context
├── patterns.yaml            # Learned patterns
└── episodes/                # Episodic memories
    ├── 2025-12-18_game_library.yaml
    └── ...
```

---

## Bootstrap Protocol

At session start, Claude should:

```bash
# 1. Load core truths (ALWAYS)
cat /mnt/user/appdata/hydra-dev/memory/core.yaml

# 2. Load user preferences (ALWAYS)
cat /mnt/user/appdata/hydra-dev/memory/user.yaml

# 3. Load working context (ALWAYS)
cat /mnt/user/appdata/hydra-dev/memory/working.yaml

# 4. Load decisions if doing architecture work
cat /mnt/user/appdata/hydra-dev/memory/decisions.yaml

# 5. Load patterns if debugging or implementing
cat /mnt/user/appdata/hydra-dev/memory/patterns.yaml
```

---

## Memory Update Protocol

### When to Update Core Memory
- NEVER without explicit user approval
- Only for fundamental changes to system identity

### When to Update User Memory
After observing:
- Explicit preference statements ("I prefer X")
- Repeated corrections ("No, do it this way")
- Enthusiasm indicators ("Yes! That's exactly what I wanted")
- Frustration indicators ("That's not what I asked for")

### When to Update Decisions Memory
After:
- Making architectural choices
- Choosing between alternatives
- Completing significant implementations
- Learning from failures

### When to Update Working Memory
- At session end: summarize active work
- At session start: verify still relevant
- When priorities shift

### When to Update Patterns Memory
After:
- Finding effective solutions
- Discovering anti-patterns
- Solving recurring problems
- Optimizing performance

---

## Integration with Existing Files

| Existing File | Relationship | Action |
|---------------|--------------|--------|
| STATE.json | Cluster state, session history | Keep - operational state |
| CLAUDE.md | Project instructions | Keep - static docs, add memory bootstrap |
| knowledge/*.md | Domain facts | Keep - reference docs |
| data/memory/*.json | Old memory system | Deprecate - migrate to new structure |

---

## Session End Protocol

Before session ends, Claude should:

1. **Update working.yaml** with:
   - What was accomplished
   - What's in progress
   - Active priorities
   - Unresolved questions

2. **Update user.yaml** if preferences learned

3. **Update decisions.yaml** if architectural decisions made

4. **Update patterns.yaml** if new patterns discovered

5. **Create episode** if significant event occurred

---

## Memory Decay & Relevance

Some memories should decay:
- Old working context (archive after 7 days)
- Outdated patterns (mark as deprecated)
- Superseded decisions (keep for history, mark as superseded)

Some memories are permanent:
- Core constraints
- User preferences (unless explicitly changed)
- Successful patterns
- Decision history (for learning)
