# DEPRECATED: Agent Module

**Status:** This module is deprecated and will be removed in a future version.

## Why Deprecated

This standalone agent module (1,348 lines of Python code) has been replaced with a documentation-driven approach where Claude Code's general-purpose Agent directly orchestrates RLM operations.

## What Replaces It

Instead of calling `gmail_agent.py` as a subprocess, Claude Code's Agent now:

1. Reads comprehensive documentation (`SKILL.md`, `RLM_AGENT_GUIDE.md`)
2. Interprets user goals using its native understanding
3. Constructs appropriate RLM code
4. Executes `gmail_rlm_repl.py` subprocess directly
5. Presents results naturally in the conversation

## Benefits of New Approach

1. **Code Reduction:** Eliminated 1,348 lines of custom agent code
2. **Better Integration:** Leverages Claude Code's native multi-turn dialogue
3. **Maintainability:** New workflows added via documentation, not code
4. **Flexibility:** Agent adapts approach based on full context
5. **Cost Transparency:** Native budget management and confirmation

## Migration

**Old (Deprecated):**
```bash
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage my inbox"
```

**New (Recommended):**
User says to Claude Code: "Triage my inbox"
→ Claude Code's Agent automatically:
  - Reads SKILL.md to identify RLM orchestration trigger
  - Reads RLM_AGENT_GUIDE.md for orchestration workflow
  - Constructs: `result = inbox_triage(emails); FINAL(...)`
  - Executes: `gmail_rlm_repl.py --code "..."`
  - Presents results naturally

## Backward Compatibility

The `gmail_agent.py` script remains functional for now but shows deprecation warnings. It will be removed in a future version (v0.5.0 or later).

## Documentation References

- `SKILL.md` - When to activate RLM orchestration
- `RLM_AGENT_GUIDE.md` - Complete orchestration guide
- `references/rlm-function-reference.md` - All RLM functions
- `examples/agent-conversations.md` - 10+ complete conversation examples

## Timeline

- **v0.4.0 (current):** Deprecation notices added, old code kept for compatibility
- **v0.5.0 (future):** This module will be removed entirely

---

**For Questions:** See `SKILL.md` for current usage patterns.
