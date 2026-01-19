---
name: gmail
description: Use when the user asks to "read my email", "search my gmail", "send an email", "check my inbox", "manage gmail labels", "organize my email", "triage my inbox", "summarize emails", "find action items", "analyze security alerts", or mentions Gmail operations like reading messages, composing emails, searching for emails, managing folders/labels, or analyzing email content. Provides direct Gmail API integration with Claude Code Agent orchestration of RLM (Recursive Language Model) analysis for complex tasks, plus simple scripts for basic operations.
version: 0.4.0
---

# Gmail Integration Skill

This skill provides direct Gmail API integration for reading, searching, sending emails, and managing labels. It features an **autonomous agent mode** that accepts natural language goals and automatically executes sophisticated email analyses, plus simple scripts for basic operations.

## Operating Modes

This skill supports three modes of operation:

### RLM Analysis (RECOMMENDED - via Claude Code Agent)
**Claude Code's Agent orchestrates Recursive Language Model analysis for complex email tasks.**
- For: Everyone - Agent handles complexity automatically
- Features: Natural language interpretation, multi-turn dialogue, automatic cost optimization
- Budget: Default $1.00 limit (Agent asks confirmation for higher costs)
- Best for: Inbox triage, security analysis, action items, summaries, >20 emails

**How it works:**
1. User: "Triage my inbox"
2. Agent interprets goal → selects `inbox_triage()` function
3. Agent constructs RLM code → executes via `gmail_rlm_repl.py`
4. Agent presents results naturally → caches for follow-up questions

See `RLM_AGENT_GUIDE.md` for complete orchestration guidance.

### Normal Mode
For simple, direct email operations.
- Max 100 emails per query
- Direct API calls without LLM analysis
- Best for: Sending emails, reading 1-5 specific messages, applying labels

**Scripts:** `gmail_read.py`, `gmail_send.py`, `gmail_labels.py`

### RLM Mode (Direct/Script Mode)
For power users who want full control.
- Write custom Python code with RLM functions
- Direct subprocess execution of `gmail_rlm_repl.py`
- Pagination for 1000+ emails
- Best for: Custom logic, automation pipelines

**Script:** `gmail_rlm_repl.py --code "your_code_here"`

**Mode Selection Guidelines:**

| Scenario | Recommended Mode | Reason |
|----------|-----------------|--------|
| Triage security alerts | **RLM (via Agent)** | Complex analysis, pre-built workflow |
| Check 10 unread emails | Normal | Small dataset, simple task |
| Send an email | Normal | Single operation |
| Summarize inbox | **RLM (via Agent)** | Content analysis required |
| Find action items across 500 emails | **RLM (via Agent)** | Large-scale LLM processing |
| Apply label to 5 messages | Normal | Simple batch operation |
| Custom email analysis logic | RLM (Direct) | Need full Python control |

## 🤖 Claude Code Agent Orchestration Guide

**IMPORTANT:** For complex email analysis tasks, Claude Code's Agent should directly orchestrate RLM (Recursive Language Model) operations instead of using subprocess agents. This provides better control, natural dialogue, and cost optimization.

### When to Activate RLM Orchestration

Activate when user requests:
- ✅ "Triage my inbox" / "Organize my emails"
- ✅ "Summarize my emails" / "What's in my inbox?"
- ✅ "Find action items" / "What do I need to do?"
- ✅ "Analyze security alerts" / "Check for threats"
- ✅ "Find emails from..." / "Search for..." (with analysis intent)
- ✅ "What are the urgent emails?"
- ✅ Any request involving >20 emails or requiring content analysis
- ✅ Security-specific: "Triage alerts", "Find attack chains", "Detect phishing"

### Use Normal Mode Only For:
- ❌ Sending a single specific email (`gmail_send.py`)
- ❌ Reading exactly 1-5 specific emails by ID
- ❌ Adding/removing a specific label from specific emails
- ❌ Very simple operations that don't require analysis

### How RLM Orchestration Works

1. **Interpret user goal** → Determine intent, scope, workflow
2. **Select RLM functions** → Choose pre-built workflows or compose custom logic
3. **Construct Python code** → Build code to pass to `gmail_rlm_repl.py`
4. **Estimate cost** → Calculate approximate cost, warn if >$1, confirm if >$2
5. **Execute subprocess** → Run `gmail_rlm_repl.py --code "..."`
6. **Present results** → Format naturally in markdown
7. **Multi-turn dialogue** → Cache results for follow-up questions

### Workflow Decision Matrix

| User Goal | RLM Function | Estimated Cost (100 emails) |
|-----------|-------------|----------------------------|
| Triage inbox | `inbox_triage(emails)` | $0.20 |
| Weekly summary | `weekly_summary(emails)` | $0.10 |
| Action items | `find_action_items(emails)` | $0.15 |
| Security triage | `security_triage(emails)` | $0.40 |
| Attack chains | `detect_attack_chains(emails)` | $0.50 |
| Phishing detection | `phishing_analysis(emails)` | $0.30 |
| Sender analysis | `sender_analysis(emails, top_n=5)` | $0.15 |
| Custom analysis | Compose with chunking + LLM queries | Varies |

### Example Orchestration

**User Request:** "Triage my inbox"

**Agent Actions:**
1. **Interpret:** User wants emails categorized by urgency
2. **Select:** `inbox_triage(emails)` workflow
3. **Construct Code:**
```python
result = inbox_triage(emails)
print(f'Urgent: {len(result["urgent"])}')
print(f'Action Required: {len(result["action_required"])}')
FINAL(f'Found {len(result["urgent"])} urgent emails')
```
4. **Estimate:** ~100 emails × $0.002 = $0.20
5. **Execute:**
```bash
.venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py \
  --query "is:inbox newer_than:7d" \
  --max-results 100 \
  --max-budget 1.00 \
  --code "result = inbox_triage(emails); FINAL(str(len(result['urgent'])) + ' urgent emails')"
```
6. **Present:** "Inbox Triage Complete: 5 urgent emails, 12 action required, 48 FYI, 23 newsletters"
7. **Prepare follow-up:** Cache result for "Show me urgent emails"

### Complete Documentation

For comprehensive orchestration guidance, see:
- **RLM_AGENT_GUIDE.md** - Complete orchestration patterns, cost optimization, multi-turn dialogue
- **references/rlm-function-reference.md** - All available RLM functions with signatures and examples
- **examples/agent-conversations.md** - 10+ complete conversation examples showing expected behavior

### Key Principles

1. **Direct Orchestration:** Agent constructs RLM code and calls subprocess directly
2. **Cost Transparency:** Always estimate costs, warn before expensive operations
3. **Result Caching:** Keep RLM results in memory for follow-up questions (avoid re-execution)
4. **Natural Presentation:** Format results in readable markdown, not raw JSON
5. **Budget Control:** Default $1.00, ask confirmation for operations >$2.00

## RLM Mode Quick Reference

**NOTE:** Claude Code's Agent should orchestrate RLM directly (see section above). This reference is for understanding the underlying RLM subprocess interface.

### Direct RLM Execution (for power users)

```bash
# Execute RLM code directly
.venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py \
  --query "GMAIL_QUERY" \
  --max-results MAX_EMAILS \
  --max-budget BUDGET \
  --code "RLM_CODE"
```

### Pre-built Workflow Examples

```bash
# Inbox triage
.venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py \
  --query "is:inbox newer_than:7d" \
  --max-results 100 \
  --code "result = inbox_triage(emails); FINAL_VAR('result')"

# Security alert triage
.venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py \
  --query "label:security-alerts newer_than:7d" \
  --max-results 500 \
  --max-budget 2.00 \
  --code "result = security_triage(emails); FINAL(result['executive_summary'])"

# Find action items
.venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py \
  --query "newer_than:14d" \
  --max-results 300 \
  --code "items = find_action_items(emails); FINAL_VAR('items')"

# Weekly summary
.venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py \
  --query "newer_than:7d" \
  --max-results 500 \
  --code "summary = weekly_summary(emails); FINAL(summary)"
```

### Custom Analysis Examples

```bash
# Top senders summary (parallel processing)
.venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py \
  --query "newer_than:7d" \
  --max-results 200 \
  --code "
by_sender = chunk_by_sender(emails)
top_5 = list(by_sender.items())[:5]

summaries = parallel_map(
    'Summarize emails from this sender',
    [msgs for _, msgs in top_5],
    lambda msgs: str([m['snippet'] for m in msgs[:10]]),
    max_workers=5
)

output = '\n\n'.join([f'**{s[0]}** ({len(s[1])} emails): {summaries[i]}' for i, s in enumerate(top_5)])
FINAL(output)
"
```

### Available RLM Functions

**Core:** `llm_query()`, `parallel_llm_query()`, `parallel_map()`, `FINAL()`, `FINAL_VAR()`, `get_session()`

**Chunking:** `chunk_by_size()`, `chunk_by_sender()`, `chunk_by_date()`, `chunk_by_thread()`, `chunk_by_time()`

**Filtering:** `filter_emails()`, `filter_by_keyword()`, `filter_by_sender()`

**Workflows:** `inbox_triage()`, `weekly_summary()`, `find_action_items()`, `sender_analysis()`

**Security:** `security_triage()`, `detect_attack_chains()`, `phishing_analysis()`, `classify_alerts()`, `extract_iocs()`, `map_to_mitre()`, `correlate_by_source_ip()`, `detect_suspicious_senders()`, `analyze_attachments()`, `extract_and_analyze_urls()`

For complete function reference, see `references/rlm-function-reference.md`.

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

### Workflow 1: Email Analysis/Triage (Agent Orchestrates RLM)

When user asks to "triage my inbox" or "organize my emails" or "what's important?":

**✅ Agent Orchestrates RLM:**
Agent interprets goal → executes `inbox_triage(emails)` via gmail_rlm_repl.py

The workflow automatically:
- Categorizes emails (urgent/action/fyi/newsletter)
- Identifies important senders
- Extracts action items
- Agent presents formatted summary

See `examples/agent-conversations.md` Example 1 for complete dialogue.

### Workflow 2: Security Alert Analysis (Agent Orchestrates RLM)

When user asks to "check security alerts" or "analyze threats":

**✅ Agent Orchestrates RLM:**
Agent interprets goal → executes `security_triage(emails)` via gmail_rlm_repl.py

The workflow automatically:
- Classifies alerts (P1-P5)
- Extracts IOCs
- Detects kill chains
- Maps to MITRE ATT&CK
- Agent presents executive summary

See `examples/agent-conversations.md` Example 2 for complete dialogue with cost confirmation.

### Workflow 3: Find Action Items (Agent Orchestrates RLM)

When user asks "what do I need to do?" or "find action items":

**✅ Agent Orchestrates RLM:**
Agent interprets goal → executes `find_action_items(emails)` via gmail_rlm_repl.py

The workflow automatically:
- Extracts tasks from emails
- Identifies deadlines
- Assigns priority
- Agent presents grouped by urgency

See `examples/agent-conversations.md` Example 3 for complete dialogue.

### Workflow 4: Summarize Inbox (Agent Orchestrates RLM)

When user asks "summarize my emails" or "what happened this week?":

**✅ Agent Orchestrates RLM:**
Agent interprets goal → executes `weekly_summary(emails)` via gmail_rlm_repl.py

See `examples/agent-conversations.md` Example 4 for complete dialogue.

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

**If analyzing content or >5 emails → Agent Orchestrates RLM:**
Agent composes: `filter_by_sender(emails, 'john@') + llm_query for summary`

**If just reading 1-5 emails → Use Normal Mode:**
```bash
.venv/bin/python skills/gmail/scripts/gmail_read.py \
  --query "from:john@example.com" \
  --max-results 5 \
  --format full
```

### 🎯 Quick Decision Guide for Claude Code Agent

| User Request | Mode | Action |
|--------------|------|--------|
| "Triage my inbox" | **RLM Orchestration** | Execute `inbox_triage()` via gmail_rlm_repl.py |
| "Find urgent emails" | **RLM Orchestration** | Compose filter + classification logic |
| "Summarize this week" | **RLM Orchestration** | Execute `weekly_summary()` via gmail_rlm_repl.py |
| "Check security alerts" | **RLM Orchestration** | Execute `security_triage()` via gmail_rlm_repl.py |
| "Find action items" | **RLM Orchestration** | Execute `find_action_items()` via gmail_rlm_repl.py |
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
- `--model`: Model for LLM sub-queries (default: claude-sonnet-4-20250514)
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
  - Added `--model` flag for model selection (default: claude-sonnet-4-20250514)
  - Added `--json-output` flag includes session stats with token counts
  - Requires `ANTHROPIC_API_KEY` environment variable
- 0.2.0: Added RLM (Recursive Language Model) mode for large-scale email analysis
  - `gmail_bulk_read.py` - Pagination for 1000+ emails
  - `gmail_rlm_repl.py` - Python REPL with recursive LLM calls
  - `gmail_rlm_helpers.py` - Chunking and aggregation utilities
- 0.1.0: Initial release with read, send, and label operations

For skill updates or issues, check the project README.
