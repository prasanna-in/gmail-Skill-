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

## Credentials

Stored in `credentials/` (gitignored):
- `credentials.json` - OAuth client credentials (user provides from Google Cloud Console)
- `token.json` - Auto-generated auth tokens

If you see authentication errors, re-run `gmail_auth.py`.
