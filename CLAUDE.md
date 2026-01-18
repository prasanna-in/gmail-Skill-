# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Gmail Skill is a Claude Code integration that provides direct Gmail API access for email operations. It supports two operating modes:

- **Normal Mode**: Single script calls for specific operations (max 100 emails)
- **RLM Mode**: Recursive Language Model processing for large-scale analysis (1000+ emails with parallel LLM sub-queries)

## Common Commands

### Setup & Authentication

```bash
# Install dependencies (uses uv package manager)
uv sync

# Run OAuth2 authentication (one-time setup, opens browser)
.venv/bin/python skills/gmail/scripts/gmail_auth.py

# Set Anthropic API key for RLM mode (required for llm_query calls)
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Running Scripts

All scripts require the virtual environment Python:

```bash
# Read/search emails
.venv/bin/python skills/gmail/scripts/gmail_read.py --query "is:unread" --max-results 20 --format metadata

# Send email
.venv/bin/python skills/gmail/scripts/gmail_send.py --to "user@example.com" --subject "Subject" --body "Body"

# Manage labels
.venv/bin/python skills/gmail/scripts/gmail_labels.py --action list

# Bulk read (for large datasets)
.venv/bin/python skills/gmail/scripts/gmail_bulk_read.py --query "newer_than:30d" --max-results 500

# RLM analysis
.venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py --query "newer_than:7d" --max-results 200 --code "
by_sender = chunk_by_sender(emails)
FINAL(str(len(by_sender)) + ' unique senders')
"
```

### Development

```bash
# Format code
uv run black skills/gmail/scripts/

# Run tests
uv run pytest

# Syntax check
python3 -m py_compile skills/gmail/scripts/gmail_read.py
```

## Architecture

```
skills/gmail/
├── SKILL.md              # Skill definition Claude reads for usage instructions
├── scripts/              # Python execution scripts
│   ├── gmail_common.py   # Shared: OAuth2, message parsing, validation
│   ├── gmail_auth.py     # One-time OAuth setup (browser flow)
│   ├── gmail_read.py     # Search and retrieve emails
│   ├── gmail_send.py     # Compose and send emails
│   ├── gmail_labels.py   # Label management (CRUD)
│   ├── gmail_bulk_read.py    # Pagination for 1000+ emails
│   ├── gmail_rlm_repl.py     # Python REPL with LLM sub-queries
│   └── gmail_rlm_helpers.py  # Chunking, filtering, aggregation
├── references/           # API docs, troubleshooting
└── examples/             # Search query patterns
```

### Key Design Patterns

1. **All scripts return JSON** - Parse `status` field ("success" or "error")
2. **OAuth tokens auto-refresh** - After initial `gmail_auth.py`, tokens are managed automatically
3. **Scopes are minimal** - Each script requests only needed permissions (readonly, send, labels)
4. **RLM uses Anthropic SDK** - `llm_query()` calls Claude via Anthropic Python SDK (requires `ANTHROPIC_API_KEY`)

### RLM Built-in Functions

When writing `--code` for `gmail_rlm_repl.py`:

- `llm_query(prompt, context, model=None, json_output=False)` - Recursive LLM call via Anthropic SDK
- `parallel_llm_query(prompts, max_workers=5, model=None, json_output=False)` - Concurrent LLM calls
- `parallel_map(prompt, chunks, context_fn, max_workers=5, model=None, json_output=False)` - Apply prompt to chunks
- `get_session()` - Get session stats (token usage, call count)
- `chunk_by_size/sender/date/thread(emails)` - Grouping functions
- `filter_by_keyword/sender(emails, pattern)` - Filtering functions
- `FINAL(result)` / `FINAL_VAR(var)` - Output final result

**CLI options:** `--model` selects LLM model (default: claude-sonnet-4-20250514), `--json-output` includes session stats in output.

### RLM Safety Controls

- `--max-budget USD` - Stop if cost exceeds budget (default: $5.00)
- `--max-calls N` - Stop after N LLM calls (default: 100)
- `--max-depth N` - Max recursion depth (default: 3)
- `--no-cache` - Disable query caching

### Pre-built Workflows

```python
# Classify emails into categories
result = inbox_triage(emails)  # Returns {urgent:[], action_required:[], fyi:[], newsletter:[]}

# Generate executive summary
summary = weekly_summary(emails)

# Extract action items with deadlines
items = find_action_items(emails)  # Returns [{task, deadline, sender, priority}]
```

## Credentials

Stored in `credentials/` (gitignored):
- `credentials.json` - OAuth client credentials (user provides from Google Cloud Console)
- `token.json` - Auto-generated auth tokens

If you see authentication errors, re-run `gmail_auth.py`.

## Learnings & Common Pitfalls

### 1. Anthropic API vs OpenAI API Differences

**Bug:** Using `response_format={"type": "json_object"}` parameter with Anthropic SDK causes `TypeError: Messages.create() got an unexpected keyword argument 'response_format'`.

**Root Cause:** The `response_format` parameter is OpenAI-specific. Anthropic's Claude API does not support this parameter.

**Solution:** Instead of using API-level JSON mode, append JSON formatting instructions to the prompt:
```python
# DON'T do this with Anthropic:
response = client.messages.create(
    model=model,
    messages=[...],
    response_format={"type": "json_object"}  # ❌ OpenAI-only
)

# DO this instead:
prompt = original_prompt + "\n\nIMPORTANT: Respond with valid JSON only. No markdown, no explanation, just the JSON."
response = client.messages.create(
    model=model,
    messages=[{"role": "user", "content": prompt}]  # ✅ Works with Anthropic
)
```

### 2. Environment Variables in Subprocesses

**Bug:** `ANTHROPIC_API_KEY` not available when running scripts, even though it's set in shell profile.

**Root Cause:** Environment variables in `~/.zshrc` or `~/.bashrc` are only loaded for interactive shells. When Claude Code runs bash commands, they may not inherit these variables.

**Solution:** Either:
1. Source the profile before running: `source ~/.zshrc && python script.py`
2. Export in the current session: `export ANTHROPIC_API_KEY="..."`
3. Add startup check in script to provide clear error message

### 3. Recursion Depth with Parallel Workers

**Bug:** `RecursionDepthExceededError` when using `parallel_map` with low `--max-depth`.

**Root Cause:** With `ThreadPoolExecutor`, multiple worker threads increment the shared `current_depth` counter concurrently, causing it to exceed limits unexpectedly.

**Solution:** Set higher `--max-depth` (e.g., 50) when using parallel processing, or use sequential processing for depth-sensitive operations.

### 4. Model Deprecation

**Issue:** Model `claude-3-5-haiku-20241022` shows deprecation warnings.

**Solution:** Update to current models like `claude-sonnet-4-20250514` or `claude-haiku-4-20250514`. Keep `MODEL_PRICING` dict updated with new model costs.
