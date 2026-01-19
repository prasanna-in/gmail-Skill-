---
name: gmail
description: Use when the user asks to "read my email", "search my gmail", "send an email", "check my inbox", "manage gmail labels", "organize my email", "triage my inbox", "summarize emails", "find action items", "analyze security alerts", or mentions Gmail operations like reading messages, composing emails, searching for emails, managing folders/labels, or analyzing email content. Provides direct Gmail API integration with autonomous agent mode for complex analysis, plus simple scripts for basic operations.
version: 0.3.0
---

# Gmail Integration Skill

This skill provides direct Gmail API integration for reading, searching, sending emails, and managing labels. It features an **autonomous agent mode** that accepts natural language goals and automatically executes sophisticated email analyses, plus simple scripts for basic operations.

## Operating Modes

This skill supports three modes of operation:

### Agent Mode (RECOMMENDED - NEW)
**Natural language interface with autonomous goal interpretation.**
- For: Everyone, especially non-technical users and SOC analysts
- Features: Multi-turn dialogue, session persistence, automatic optimization
- Budget: Default $1.00 limit (configurable)
- Best for: Most tasks - security triage, inbox management, email analysis

```bash
# Natural language goals
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage security alerts from last week"
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Find action items with deadlines"
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Summarize my week"

# Interactive dialogue
> Triage my inbox
Agent: [Results...]
> Show me urgent emails
Agent: [Urgent emails...]
```

See `AGENT.md` for comprehensive documentation.

### Normal Mode
For typical email tasks - reading specific emails, sending messages, managing labels.
- Max 100 emails per query
- Direct, simple operations
- Best for: specific lookups, sending, labeling

### RLM Mode (Script Mode)
For large-scale email analysis with custom Python code.
- Pagination for 1000+ emails
- Recursive LLM sub-queries to avoid context overflow
- Best for: Custom workflows, power users, automation pipelines

**Mode Selection Guidelines:**

| Scenario | Recommended Mode | Reason |
|----------|-----------------|--------|
| Triage security alerts | **Agent** | Natural language, pre-built workflow |
| Check 10 unread emails | Normal | Small dataset, simple task |
| Send an email | Normal | Single operation |
| Summarize inbox | **Agent** | Natural language, automatic optimization |
| Find action items across 500 emails | **Agent** | Pre-built workflow with optimization |
| Apply label to 5 messages | Normal | Simple batch operation |
| Custom email analysis logic | RLM/Script | Need full Python control |

## 🤖 When Claude Code Should Use Agent Mode

**IMPORTANT:** Claude Code should default to Agent Mode for most user requests. Only use Normal Mode for very simple operations.

### Use Agent Mode When User Asks:
- ✅ "Triage my inbox" / "Organize my emails"
- ✅ "Summarize my emails" / "What's in my inbox?"
- ✅ "Find action items" / "What do I need to do?"
- ✅ "Analyze security alerts" / "Check for threats"
- ✅ "Find emails from..." / "Search for..."
- ✅ "What are the urgent emails?"
- ✅ Any request involving >20 emails or analysis/summarization
- ✅ Any request that requires understanding email content

**How to invoke:**
```bash
.venv/bin/python skills/gmail/scripts/gmail_agent.py "USER'S GOAL IN NATURAL LANGUAGE"
```

**Examples:**
```bash
# User: "Triage my inbox"
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage my inbox"

# User: "Find urgent emails from last week"
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Find urgent emails from last week"

# User: "Summarize security alerts"
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Summarize security alerts" --query "label:security-alerts"

# User: "What action items do I have?"
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Find action items with deadlines"
```

### Use Normal Mode Only When:
- ❌ Sending a single specific email (`gmail_send.py`)
- ❌ Reading exactly 1-5 specific emails by ID
- ❌ Adding/removing a specific label from specific emails
- ❌ Very simple operations that don't require analysis

### Claude Code Implementation Pattern

When user makes a Gmail request:

1. **Parse the user's intent** - What are they trying to accomplish?
2. **Choose mode:**
   - If it involves analysis, summarization, search, triage, or >5 emails → **Agent Mode**
   - If it's a single simple operation → Normal Mode
3. **For Agent Mode:**
   - Extract the user's natural language goal
   - Call `gmail_agent.py` with that goal
   - The agent handles everything else automatically
4. **Present results** to the user

**Example Claude Code flow:**
```
User: "What urgent emails do I have this week?"

Claude thinks: This requires analyzing email content + filtering → Agent Mode

Claude executes:
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Find urgent emails from this week" \
  --query "newer_than:7d" \
  --max-results 100

Claude presents: [Agent's formatted output to user]
```

## Agent Mode Quick Start

Agent Mode is the **recommended interface** for most Gmail operations. It provides a natural language interface that automatically converts your goals into sophisticated email analyses.

### Basic Usage

```bash
# Run a goal in agent mode
.venv/bin/python skills/gmail/scripts/gmail_agent.py "your goal here"

# Examples
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage my inbox"
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Find action items"
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Summarize my week"
```

### Security Workflows

```bash
# Security alert triage (P1-P5 classification, IOCs, kill chains)
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage security alerts from last week" \
  --query "label:security-alerts newer_than:7d" \
  --max-budget 2.00

# Attack chain detection
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Find attack chains in alerts" \
  --query "label:security-alerts newer_than:24h"

# Phishing analysis
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Analyze phishing attempts" \
  --query "newer_than:7d"
```

### General Email Workflows

```bash
# Inbox management
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage my inbox" \
  --query "is:inbox newer_than:7d"

# Sender analysis
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Summarize emails from top 5 senders" \
  --max-results 200

# Action items
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Find action items with deadlines" \
  --query "newer_than:7d"

# Weekly summary
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Summarize my week" \
  --query "newer_than:7d" \
  --max-results 500
```

### Multi-Turn Dialogue

Agent mode supports interactive conversations:

```bash
$ .venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage security alerts"
Agent: Found 47 alerts. 5 P1, 12 P2, 30 P3+...
Session saved: ~/.gmail_agent_sessions/session_20250119_143022.json

> Show me P1 details
Agent: [P1 alert details...]

> What IOCs were found?
Agent: [IOC list...]

> done
Session ended. Use --resume to continue later.
```

### Session Management

```bash
# Resume a previous session
.venv/bin/python skills/gmail/scripts/gmail_agent.py --resume session_20250119_143022

# List all sessions
.venv/bin/python skills/gmail/scripts/gmail_agent.py --list-sessions

# Sessions are stored in ~/.gmail_agent_sessions/
```

### Advanced Options

```bash
# Custom budget (default: $1.00)
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Analyze 1000 emails" --max-budget 5.00

# Different output formats
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage alerts" --format json
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage alerts" --format html > report.html

# Debug mode (shows generated code)
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage alerts" --debug

# Non-interactive mode (for scripts)
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Summary" --non-interactive

# Custom model
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Quick task" --model claude-haiku-4-20250514
```

### Script Mode (Power Users)

For advanced users who want full control with Python code:

```bash
.venv/bin/python skills/gmail/scripts/gmail_agent.py --script "
result = security_triage(emails)
print(f'P1: {len(result[\"classifications\"][\"P1\"])}')
FINAL(result['executive_summary'])
"
```

**Note:** For comprehensive Agent Mode documentation, see `AGENT.md`.

## Prerequisites & Setup

Before using this skill, the user must complete a one-time OAuth2 setup:

### Step 1: Google Cloud Console Setup

The user needs to create OAuth2 credentials:

1. Visit https://console.cloud.google.com
2. Create a new project (or select existing)
3. Enable "Gmail API" for the project
4. Configure OAuth consent screen (Desktop app type)
5. Create "OAuth 2.0 Client ID" credentials
6. Download credentials JSON file
7. Save as `credentials/credentials.json`

### Step 2: Run Initial Authentication

Execute the authentication script to obtain tokens:

```bash
python skills/gmail/scripts/gmail_auth.py
```

This will:
- Open a browser for OAuth consent
- User grants permissions
- Save tokens to `credentials/token.json`
- Tokens auto-refresh in future operations

**If you encounter authentication errors**, the user needs to re-run `gmail_auth.py`.

For detailed setup instructions, refer to [references/troubleshooting.md](references/troubleshooting.md).

## Reading and Searching Emails

Use `gmail_read.py` to search for and retrieve emails.

### Basic Usage

```bash
python skills/gmail/scripts/gmail_read.py \
  --query "SEARCH_QUERY" \
  --max-results 10 \
  --format metadata
```

### Arguments

- `--query`: Gmail search query (required)
- `--max-results`: Number of emails to return (default: 10, max: 100)
- `--format`: Output detail level
  - `minimal`: Just message IDs and thread IDs
  - `metadata`: Includes subject, from, to, date, snippet (recommended)
  - `full`: Includes complete email body text

### Output Format

The script returns JSON with this structure:

```json
{
  "status": "success",
  "result_count": 2,
  "query": "is:unread",
  "messages": [
    {
      "id": "18d1a2b3c4d5e6f7",
      "threadId": "18d1a2b3c4d5e6f7",
      "subject": "Meeting Tomorrow",
      "from": "John Doe <john@example.com>",
      "to": "user@gmail.com",
      "date": "Wed, 15 Jan 2026 10:30:00 -0800",
      "snippet": "Quick reminder about our meeting...",
      "body": "..." // Only in 'full' format
    }
  ]
}
```

Parse the `messages` array to access email data.

### Common Search Queries

For comprehensive query syntax, see [examples/search-examples.md](examples/search-examples.md).

**Basic filters:**
- `is:unread` - Unread messages only
- `is:starred` - Starred messages
- `from:user@example.com` - From specific sender
- `to:me` - Sent directly to user
- `subject:invoice` - Subject contains "invoice"

**Date ranges:**
- `after:2026/01/01` - After specific date
- `newer_than:7d` - Last 7 days
- `older_than:1m` - Older than 1 month

**Attachments:**
- `has:attachment` - Any attachment
- `filename:pdf` - PDF files
- `larger:5M` - Files larger than 5MB

**Combining queries:**
- `from:boss@company.com is:unread` - Unread from specific sender
- `subject:invoice has:attachment after:2026/01/01` - Recent invoices with attachments

### Example: Check Unread Emails

When the user asks "check my unread emails":

```bash
python skills/gmail/scripts/gmail_read.py \
  --query "is:unread" \
  --max-results 20 \
  --format metadata
```

Then parse the JSON output and summarize the results for the user.

## Sending Emails

Use `gmail_send.py` to compose and send emails.

### Basic Usage

```bash
python skills/gmail/scripts/gmail_send.py \
  --to "recipient@example.com" \
  --subject "Email Subject" \
  --body "Email body text"
```

### Arguments

- `--to`: Recipient email(s), comma-separated (required)
- `--subject`: Email subject line (required)
- `--body`: Email body text (required, OR use --body-file)
- `--body-file`: Path to file containing body text (alternative to --body)
- `--cc`: CC recipient(s), comma-separated (optional)
- `--bcc`: BCC recipient(s), comma-separated (optional)
- `--attach`: File path to attach (optional, can use multiple times)

### Output Format

```json
{
  "status": "success",
  "message_id": "18d1a2b3c4d5e6f7",
  "thread_id": "18d1a2b3c4d5e6f7",
  "to": ["recipient@example.com"],
  "subject": "Meeting Tomorrow"
}
```

### Examples

**Simple email:**
```bash
python skills/gmail/scripts/gmail_send.py \
  --to "colleague@example.com" \
  --subject "Quick Update" \
  --body "The project is on track for delivery next week."
```

**Multiple recipients with CC:**
```bash
python skills/gmail/scripts/gmail_send.py \
  --to "team@example.com,manager@example.com" \
  --cc "stakeholder@example.com" \
  --subject "Q1 Results" \
  --body "Please see Q1 performance summary attached." \
  --attach /path/to/report.pdf
```

**Important Notes:**
- Gmail has a 25MB total attachment size limit
- Sent messages automatically appear in the "Sent" folder
- Email addresses are validated before sending
- Use quotes around recipient lists containing commas

## Managing Labels

Use `gmail_labels.py` to create labels and organize emails.

### List All Labels

```bash
python skills/gmail/scripts/gmail_labels.py \
  --action list
```

Returns JSON with all labels (system and user-created).

### Create New Label

```bash
python skills/gmail/scripts/gmail_labels.py \
  --action create \
  --name "Work/Projects"
```

**Note:** Use "/" for hierarchical labels (like folders).

### Apply Label to Messages

```bash
python skills/gmail/scripts/gmail_labels.py \
  --action apply \
  --label-name "Important" \
  --message-ids "18d1a2b3c4d5e6f7,18d1a2b3c4d5e6f8"
```

### Remove Label from Messages

```bash
python skills/gmail/scripts/gmail_labels.py \
  --action remove \
  --label-name "Important" \
  --message-ids "18d1a2b3c4d5e6f7"
```

### Label Management Notes

- Messages can have multiple labels (unlike traditional folders)
- System labels (INBOX, SENT, TRASH, SPAM) cannot be created or deleted
- Removing a label doesn't delete the message
- Label names are case-sensitive

## Common Workflows

### Workflow 1: Email Analysis/Triage (Use Agent Mode)

When user asks to "triage my inbox" or "organize my emails" or "what's important?":

**✅ Use Agent Mode:**
```bash
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage my inbox and show urgent emails"
```

The agent automatically:
- Categorizes emails (urgent/action/fyi/newsletter)
- Identifies important senders
- Extracts action items
- Provides formatted summary

### Workflow 2: Security Alert Analysis (Use Agent Mode)

When user asks to "check security alerts" or "analyze threats":

**✅ Use Agent Mode:**
```bash
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage security alerts from last week" \
  --query "label:security-alerts newer_than:7d" \
  --max-budget 2.00
```

The agent automatically:
- Classifies alerts (P1-P5)
- Extracts IOCs
- Detects kill chains
- Maps to MITRE ATT&CK
- Provides executive summary

### Workflow 3: Find Action Items (Use Agent Mode)

When user asks "what do I need to do?" or "find action items":

**✅ Use Agent Mode:**
```bash
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Find action items with deadlines from this week" \
  --query "newer_than:7d"
```

The agent automatically:
- Extracts tasks from emails
- Identifies deadlines
- Assigns priority
- Groups by urgency

### Workflow 4: Summarize Inbox (Use Agent Mode)

When user asks "summarize my emails" or "what happened this week?":

**✅ Use Agent Mode:**
```bash
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Summarize my week" \
  --query "newer_than:7d" \
  --max-results 500
```

### Workflow 5: Simple Label Management (Use Normal Mode)

When user asks to "label specific emails" with known message IDs:

**❌ Use Normal Mode (not agent):**

1. **Create label:**
   ```bash
   .venv/bin/python skills/gmail/scripts/gmail_labels.py --action create --name "Support"
   ```

2. **Apply label to specific messages:**
   ```bash
   .venv/bin/python skills/gmail/scripts/gmail_labels.py --action apply --label-name "Support" --message-ids "ID1,ID2,ID3"
   ```

### Workflow 6: Send Single Email (Use Normal Mode)

When user asks to "send an email to John":

**❌ Use Normal Mode (not agent):**
```bash
.venv/bin/python skills/gmail/scripts/gmail_send.py \
  --to "john@example.com" \
  --subject "Meeting Follow-up" \
  --body "Thanks for the meeting today..."
```

### Workflow 7: Read Specific Emails (Mixed Mode)

When user asks "show me emails from John":

**If analyzing content or >5 emails → Use Agent Mode:**
```bash
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Summarize emails from John" \
  --query "from:john@example.com"
```

**If just reading 1-5 emails → Use Normal Mode:**
```bash
.venv/bin/python skills/gmail/scripts/gmail_read.py \
  --query "from:john@example.com" \
  --max-results 5 \
  --format full
```

### 🎯 Quick Decision Guide for Claude Code

| User Request | Mode | Command |
|--------------|------|---------|
| "Triage my inbox" | **Agent** | `gmail_agent.py "Triage my inbox"` |
| "Find urgent emails" | **Agent** | `gmail_agent.py "Find urgent emails"` |
| "Summarize this week" | **Agent** | `gmail_agent.py "Summarize my week"` |
| "Check security alerts" | **Agent** | `gmail_agent.py "Triage security alerts"` |
| "Find action items" | **Agent** | `gmail_agent.py "Find action items"` |
| "Send email to John" | Normal | `gmail_send.py --to john@...` |
| "Create label 'Work'" | Normal | `gmail_labels.py --action create --name Work` |
| "Show me 3 emails from..." | Normal | `gmail_read.py --query "from:..." --max-results 3` |

## Error Handling

### Authentication Errors

If you see errors like:
- `"No valid credentials found"`
- `"Token refresh failed"`

**Solution:** User needs to re-authenticate:
```bash
python skills/gmail/scripts/gmail_auth.py
```

### Permission Errors

If you see `"Insufficient permissions"`:

**Cause:** The token was created with insufficient OAuth scopes.

**Solution:** Re-authenticate with broader scopes:
```bash
python gmail_auth.py --scopes gmail.modify
```

### Invalid Query Errors

If search fails with `"Invalid query"`:

**Solution:** Check query syntax. Refer to [examples/search-examples.md](examples/search-examples.md) for valid patterns.

### Common Error Types in JSON Output

All scripts return errors in this format:

```json
{
  "status": "error",
  "error_type": "ErrorTypeName",
  "message": "Human-readable description"
}
```

Error types:
- `MissingCredentials`: OAuth setup not completed
- `AuthenticationError`: Token issues
- `SearchError`: Invalid search query
- `SendError`: Email sending failed
- `LabelError`: Label operation failed
- `ValidationError`: Invalid email address or parameters

## Additional Resources

- **API Reference:** [references/api-reference.md](references/api-reference.md) - Complete Gmail API details
- **Troubleshooting:** [references/troubleshooting.md](references/troubleshooting.md) - Common issues and solutions
- **Search Examples:** [examples/search-examples.md](examples/search-examples.md) - Comprehensive query patterns
- **RLM Patterns:** [references/rlm-patterns.md](references/rlm-patterns.md) - Recursive analysis examples
- **Google Documentation:** https://developers.google.com/gmail/api

---

## RLM Mode Operations

RLM (Recursive Language Model) mode enables large-scale email analysis by:
1. Fetching emails with pagination (1000+)
2. Loading data into a Python REPL environment
3. Using recursive LLM calls to process chunks
4. Aggregating results into a final answer

### RLM Prerequisites

RLM mode requires the `ANTHROPIC_API_KEY` environment variable to be set:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

The API key is used for LLM sub-queries via the Anthropic Python SDK.

### When to Use RLM Mode

Use RLM mode when:
- Analyzing 100+ emails
- User requests summary of large time periods ("summarize my inbox this month")
- Complex multi-step workflows are needed
- Action item extraction across many emails
- Email classification or categorization tasks
- Trend analysis or pattern detection

### Bulk Read (Pagination)

Use `gmail_bulk_read.py` to fetch large numbers of emails:

```bash
python skills/gmail/scripts/gmail_bulk_read.py \
  --query "newer_than:30d" \
  --max-results 500 \
  --format metadata \
  --output-file /tmp/emails.json
```

**Arguments:**
- `--query`: Gmail search query (required)
- `--max-results`: Number of emails (default: 500, recommended max: 1000)
- `--format`: Output detail level (minimal, metadata, full)
- `--output-file`: Save to file instead of stdout (recommended for large results)
- `--quiet`: Suppress progress messages

**Output:** Same JSON format as `gmail_read.py`, with pagination metadata.

### RLM REPL Environment

Use `gmail_rlm_repl.py` for recursive email analysis:

```bash
python skills/gmail/scripts/gmail_rlm_repl.py \
  --query "is:unread" \
  --max-results 200 \
  --code "
# Group emails by sender
by_sender = chunk_by_sender(emails)

# Summarize top 5 senders
summaries = []
for sender, msgs in list(by_sender.items())[:5]:
    summary = llm_query(
        f'Summarize emails from {sender}',
        context=str([m['snippet'] for m in msgs])
    )
    summaries.append(f'{sender}: {summary}')

FINAL('\\n'.join(summaries))
"
```

**Arguments:**
- `--query`: Gmail search query (OR use --load-file)
- `--load-file`: Load emails from JSON file (from gmail_bulk_read.py)
- `--max-results`: Maximum emails to fetch (default: 200)
- `--format`: Email format (minimal, metadata, full)
- `--code`: Python code to execute in RLM environment
- `--code-file`: Load code from file instead
- `--model`: Model for LLM sub-queries (default: claude-3-5-haiku-20241022)
- `--json-output`: Return result as JSON with session stats (token usage)

### Built-in Variables

| Variable | Description |
|----------|-------------|
| `emails` | List of email dicts: id, threadId, subject, from, to, date, snippet, body |
| `metadata` | Query metadata: query, count, format |

### Built-in Functions

**Core Functions:**
| Function | Description |
|----------|-------------|
| `llm_query(prompt, context, model=None, json_output=False)` | Recursive LLM call via Anthropic SDK |
| `parallel_llm_query(prompts, max_workers, model=None, json_output=False)` | Execute multiple LLM queries in parallel |
| `parallel_map(prompt, chunks, context_fn, max_workers, model=None, json_output=False)` | Apply prompt to chunks in parallel |
| `FINAL(result)` | Output final result (string) |
| `FINAL_VAR(var_name)` | Output variable as JSON |
| `get_session()` | Get session stats (token usage, call count) |

**Chunking Functions:**
| Function | Description |
|----------|-------------|
| `chunk_by_size(emails, n)` | Split into n-sized chunks |
| `chunk_by_sender(emails)` | Group by sender email address |
| `chunk_by_sender_domain(emails)` | Group by sender domain |
| `chunk_by_date(emails, period)` | Group by 'day', 'week', or 'month' |
| `chunk_by_thread(emails)` | Group by thread ID |

**Filter Functions:**
| Function | Description |
|----------|-------------|
| `filter_emails(emails, predicate)` | Filter with custom function |
| `filter_by_keyword(emails, kw)` | Filter by keyword in subject/snippet/body |
| `filter_by_sender(emails, pattern)` | Filter by sender pattern |

**Utility Functions:**
| Function | Description |
|----------|-------------|
| `sort_emails(emails, by, reverse)` | Sort by field |
| `get_top_senders(emails, n)` | Get top N senders by count |
| `extract_email_summary(email)` | Text summary of one email |
| `batch_extract_summaries(emails, max_chars)` | Combined summary with char limit |
| `aggregate_results(results, separator)` | Combine multiple results |
| `prepare_llm_batch(chunks, prompt, fields)` | Prepare prompts for parallel_llm_query |

### RLM Example: Inbox Summary

Summarize 200 emails by sender:

```bash
python skills/gmail/scripts/gmail_rlm_repl.py \
  --query "newer_than:7d" \
  --max-results 200 \
  --code "
by_sender = chunk_by_sender(emails)
top = sorted(by_sender.items(), key=lambda x: -len(x[1]))[:10]

summaries = []
for sender, msgs in top:
    summary = llm_query(
        f'What is {sender} emailing about?',
        context=str([m['snippet'] for m in msgs[:10]])
    )
    summaries.append(f'**{sender}** ({len(msgs)}): {summary}')

FINAL('## Weekly Inbox Summary\\n\\n' + '\\n\\n'.join(summaries))
"
```

### RLM Example: Action Items

Extract action items from many emails:

```bash
python skills/gmail/scripts/gmail_rlm_repl.py \
  --query "newer_than:14d" \
  --max-results 300 \
  --code "
all_items = []
for chunk in chunk_by_size(emails, 20):
    items = llm_query(
        'Extract action items. Format: - [ACTION]. Return None if no actions.',
        context=str([{'from': e['from'], 'subject': e['subject'], 'snippet': e['snippet']} for e in chunk])
    )
    if items.strip().lower() != 'none':
        all_items.append(items)

if all_items:
    final = llm_query('Prioritize these action items:', context='\\n'.join(all_items))
    FINAL(final)
else:
    FINAL('No action items found.')
"
```

### RLM Example: Email Classification

Categorize emails:

```bash
python skills/gmail/scripts/gmail_rlm_repl.py \
  --query "is:unread" \
  --max-results 100 \
  --code "
categories = {'urgent': [], 'action_required': [], 'fyi': [], 'other': []}

for email in emails:
    cat = llm_query(
        'Classify: urgent, action_required, fyi, or other. Reply with just the category.',
        context=f\"From: {email['from']}\\nSubject: {email['subject']}\\nPreview: {email['snippet']}\"
    ).strip().lower()

    if cat in categories:
        categories[cat].append(email['id'])
    else:
        categories['other'].append(email['id'])

FINAL_VAR('categories')
"
```

For more RLM patterns and examples, see [references/rlm-patterns.md](references/rlm-patterns.md).

### Parallel Processing

For large email sets, use parallel functions to speed up analysis (3-5x faster):

**`parallel_llm_query(prompts, max_workers=5)`**
Execute multiple LLM queries concurrently. Takes a list of (prompt, context) tuples.

**`parallel_map(prompt, chunks, context_fn, max_workers=5)`**
Apply same prompt to multiple chunks in parallel. Simpler interface for common patterns.

**`prepare_llm_batch(chunks, prompt_template, context_fields)`**
Helper to prepare (prompt, context) tuples from email chunks.

**Example: Parallel inbox summary**
```python
# Process 10 sender groups concurrently (5x faster than sequential)
by_sender = chunk_by_sender(emails)
top_senders = list(by_sender.items())[:10]

prompts = [
    (f'Summarize emails from {sender}',
     str([m['snippet'] for m in msgs[:10]]))
    for sender, msgs in top_senders
]

results = parallel_llm_query(prompts, max_workers=5)

summaries = [
    f'**{sender}**: {result}'
    for (sender, _), result in zip(top_senders, results)
]
FINAL('\n\n'.join(summaries))
```

**Example: Using parallel_map**
```python
# Summarize email chunks in parallel
chunks = chunk_by_size(emails, 20)
results = parallel_map(
    'Summarize these emails',
    chunks[:5],
    context_fn=lambda c: str([e['snippet'] for e in c]),
    max_workers=5
)
FINAL('\n---\n'.join(results))
```

---

## Security Alert Triage (RLM)

RLM mode includes specialized security analysis workflows for SOC/security teams processing Gmail-delivered security alerts.

### Security Prerequisites

In addition to RLM prerequisites, security workflows work best with:
- Security alerts forwarded to Gmail (from CrowdStrike, Splunk, Azure Sentinel, etc.)
- Gmail labels for organizing security alerts (e.g., "security-alerts")
- `ANTHROPIC_API_KEY` set for LLM-powered analysis

### Security Workflows

**`security_triage(emails)`** - Complete security alert triage pipeline

Performs comprehensive analysis:
- Severity classification (P1-P5)
- IOC extraction (IPs, domains, hashes, URLs)
- Kill chain detection via time correlation
- Source IP correlation analysis
- Suspicious sender/phishing detection
- Attachment and URL risk assessment
- Executive summary generation

Returns structured triage results with classifications, IOCs, detected attack chains, and actionable summary.

**`detect_attack_chains(emails, window_minutes=5)`** - Multi-pass correlation for sophisticated attacks

Analyzes temporal alert patterns to identify multi-stage attacks like:
- Initial Access → Execution → Persistence
- Reconnaissance → Exploitation → Lateral Movement
- Data Staging → Exfiltration

Returns detected attack chains with MITRE ATT&CK mappings, confidence scores, and affected systems.

**`phishing_analysis(emails)`** - Specialized phishing detection

Categorizes phishing attempts:
- Credential harvesting
- Business email compromise (BEC)
- Brand impersonation
- Malicious attachments
- Malicious links

Returns detailed phishing analysis with risk levels.

**`enrich_with_threat_intel(iocs)`** - Prepare IOCs for threat intelligence enrichment

Structures IOC data for integration with VirusTotal, AbuseIPDB, AlienVault OTX, or MISP (future enhancement).

### Security Helper Functions

**Severity & Classification:**
- `extract_severity(alert)` - Normalize severity from security tools (CrowdStrike, Splunk, etc.)
- `classify_alerts(emails, llm_query)` - Batch classify alerts into P1-P5 with LLM

**IOC Extraction:**
- `extract_iocs(emails)` - Extract IPs, domains, file hashes, email addresses, URLs
- `validate_email_auth(email)` - Check SPF/DKIM/DMARC authentication status

**MITRE ATT&CK Mapping:**
- `map_to_mitre(alert, llm_query)` - Map alerts to MITRE technique IDs

**Time-Based Correlation:**
- `chunk_by_time(emails, minutes)` - Group alerts into time windows for kill chain detection
- `detect_kill_chains(time_windows, llm_query)` - Analyze windows for attack sequences

**Threat Analysis:**
- `correlate_by_source_ip(emails, llm_query)` - Group and analyze alerts by source IP
- `detect_suspicious_senders(emails, llm_query)` - Identify phishing, spoofing, domain squatting

**Risk Assessment:**
- `analyze_attachments(emails)` - Risk scoring for email attachments
- `extract_and_analyze_urls(emails)` - Identify suspicious URLs
- `deduplicate_security_alerts(emails)` - Remove duplicate alerts (e.g., same vuln across servers)

### Security Example: Daily Alert Triage

Process last 7 days of security alerts:

```bash
python skills/gmail/scripts/gmail_rlm_repl.py \
  --query "label:security-alerts newer_than:7d" \
  --max-results 500 \
  --max-budget 2.00 \
  --code "
# Complete security triage
result = security_triage(emails)

# Print summary
print(f'Total Alerts: {result[\"summary\"][\"total_alerts\"]}')
print(f'P1 Critical: {len(result[\"classifications\"][\"P1\"])}')
print(f'P2 High: {len(result[\"classifications\"][\"P2\"])}')
print(f'Kill Chains Detected: {len(result[\"kill_chains\"])}')
print(f'Unique IOCs: {len(result[\"iocs\"][\"ips\"])} IPs, {len(result[\"iocs\"][\"domains\"])} domains')

# Output executive summary
FINAL(result['executive_summary'])
"
```

### Security Example: Kill Chain Detection

Detect multi-stage attacks in time windows:

```bash
python skills/gmail/scripts/gmail_rlm_repl.py \
  --query "label:security-alerts newer_than:24h" \
  --max-results 200 \
  --code "
# Detect attack chains with 5-minute correlation windows
chains = detect_attack_chains(emails, window_minutes=5)

# Filter to P1/P2 severity
critical_chains = [c for c in chains if c['severity'] in ['P1', 'P2']]

if critical_chains:
    output = '## Critical Attack Chains Detected\\n\\n'
    for chain in critical_chains:
        output += f\"**{chain['attack_id']}** ({chain['severity']})\\n\"
        output += f\"Pattern: {chain['pattern']}\\n\"
        output += f\"Duration: {chain['duration_minutes']} minutes\\n\"
        output += f\"MITRE: {', '.join(chain['mitre_techniques'])}\\n\"
        output += f\"Confidence: {chain['confidence']:.0%}\\n\"
        output += f\"Affected: {', '.join(chain['affected_systems'][:3])}\\n\\n\"
    FINAL(output)
else:
    FINAL('No critical attack chains detected.')
"
```

### Security Example: IOC Extraction

Extract and correlate indicators of compromise:

```bash
python skills/gmail/scripts/gmail_rlm_repl.py \
  --query "label:security-alerts subject:malware" \
  --max-results 100 \
  --code "
# Extract all IOCs
iocs = extract_iocs(emails)

print(f'Extracted {len(iocs[\"ips\"])} IPs')
print(f'Extracted {len(iocs[\"domains\"])} domains')
print(f'Extracted {len(iocs[\"file_hashes\"][\"sha256\"])} SHA256 hashes')

# Correlate alerts by source IP
if iocs['ips']:
    ip_analysis = correlate_by_source_ip(emails, llm_query)

    # Find IPs with multiple alerts (potential coordinated attack)
    high_activity = {ip: data for ip, data in ip_analysis.items() if data['alert_count'] >= 5}

    output = f'## High-Activity Source IPs ({len(high_activity)})\\n\\n'
    for ip, data in sorted(high_activity.items(), key=lambda x: -x[1]['alert_count'])[:10]:
        output += f\"**{ip}**: {data['alert_count']} alerts, {data['attack_type']}, {data['severity']}\\n\"

    FINAL(output)
else:
    FINAL('No IPs found in alerts.')
"
```

### Security Example: Phishing Analysis

Detect and categorize phishing attempts:

```bash
python skills/gmail/scripts/gmail_rlm_repl.py \
  --query "is:unread newer_than:3d" \
  --max-results 100 \
  --code "
# Run phishing analysis
results = phishing_analysis(emails)

# Build report
report = '## Phishing Analysis Report\\n\\n'
report += f\"Credential Harvesting: {len(results['credential_harvesting'])}\\n\"
report += f\"BEC Attempts: {len(results['bec_attempts'])}\\n\"
report += f\"Brand Impersonation: {len(results['brand_impersonation'])}\\n\"
report += f\"Malicious Attachments: {len(results['malicious_attachments'])}\\n\"
report += f\"Malicious Links: {len(results['malicious_links'])}\\n\\n\"

# Add details for high-risk items
if results['credential_harvesting']:
    report += '### Credential Harvesting Attempts\\n'
    for attempt in results['credential_harvesting'][:5]:
        report += f\"- {attempt['subject']} ({attempt['reason']})\\n\"

report += f\"\\n### Summary\\n{results['summary']}\"

FINAL(report)
"
```

### Security Budget Controls

Security triage can process large alert volumes. Use budget controls:

```bash
# Limit to $2.00 budget
--max-budget 2.00

# Limit to 50 LLM calls
--max-calls 50

# Adjust recursion depth for parallel processing
--max-depth 10
```

### Security Caching

Security patterns are cached separately with 7-day TTL (vs 24-hour general cache):
- IOC analyses are cached (same malware hash seen 100 times)
- MITRE mappings are cached (same technique patterns)
- Severity classifications are cached (same alert types)

Historical threat patterns are stored for recurring attack detection (30-day retention).

---

## Implementation Notes

**For Claude:**

1. **Always use absolute paths** when calling scripts
2. **Parse JSON output** - all scripts return structured JSON on stdout
3. **Check status field** - `"success"` or `"error"`
4. **Handle errors gracefully** - provide clear guidance to user
5. **Combine operations** when appropriate (search → filter → label)
6. **Respect user privacy** - don't log email contents

**Token Management:**
- Tokens auto-refresh automatically in all scripts
- No need to manually manage authentication after initial setup
- If refresh fails, user needs to re-run `gmail_auth.py`

**Performance Considerations:**
- Use `--format metadata` for most queries (faster, less data)
- Use `--format full` only when body content is needed
- Limit `--max-results` to avoid excessive API calls
- Gmail API has rate limits (see api-reference.md)

**Security:**
- Credentials are stored in `credentials/`
- Never log or display credential contents
- Token files are gitignored
- All OAuth flows use HTTPS

## Skill Version

Version: 0.4.0
Last Updated: 2026-01-19

**Changelog:**
- 0.4.0: Security-focused RLM enhancements
  - Added `gmail_security_helpers.py` - Security analysis functions (severity, IOCs, MITRE, correlation)
  - Added `gmail_security_workflows.py` - High-level workflows (security_triage, detect_attack_chains, phishing_analysis)
  - Added `gmail_security_schemas.py` - JSON schemas for structured security data
  - Enhanced caching with `SecurityPatternCache` (7-day TTL for security patterns)
  - Added `ThreatPatternStore` for cross-session threat tracking (30-day retention)
  - Security functions integrated into RLM REPL environment
  - New capabilities: kill chain detection, source IP correlation, suspicious sender detection, IOC extraction
- 0.3.0: RLM enhancement - Anthropic SDK migration and session tracking
  - Migrated `llm_query()` from Claude CLI subprocess to Anthropic Python SDK
  - Added session tracking with token usage stats (`get_session()`)
  - Added `--model` flag for model selection (default: claude-3-5-haiku-20241022)
  - Added `--json-output` flag includes session stats with token counts
  - Requires `ANTHROPIC_API_KEY` environment variable
- 0.2.0: Added RLM (Recursive Language Model) mode for large-scale email analysis
  - `gmail_bulk_read.py` - Pagination for 1000+ emails
  - `gmail_rlm_repl.py` - Python REPL with recursive LLM calls
  - `gmail_rlm_helpers.py` - Chunking and aggregation utilities
- 0.1.0: Initial release with read, send, and label operations

For skill updates or issues, check the project README.
