---
name: gmail
description: Use when the user asks to "read my email", "search my gmail", "send an email", "check my inbox", "manage gmail labels", "organize my email", or mentions Gmail operations like reading messages, composing emails, searching for emails, or managing folders/labels. Provides direct Gmail API integration for email reading, sending, and label management on personal Gmail accounts.
version: 0.2.0
---

# Gmail Integration Skill

This skill provides direct Gmail API integration for reading, searching, sending emails, and managing labels. All operations use standalone Python scripts that return JSON output for easy parsing.

## Operating Modes

This skill supports two modes of operation:

### Normal Mode (Default)
For typical email tasks - reading specific emails, sending messages, managing labels.
- Max 100 emails per query
- Direct, simple operations
- Best for: specific lookups, sending, labeling

### RLM Mode (Recursive Language Model)
For large-scale email analysis - processing 100+ emails with complex workflows.
- Pagination for 1000+ emails
- Recursive LLM sub-queries to avoid context overflow
- Best for: inbox summaries, trend analysis, bulk classification

**Mode Selection Guidelines:**

| Scenario | Mode | Reason |
|----------|------|--------|
| Check 10 unread emails | Normal | Small dataset, simple task |
| Send an email | Normal | Single operation |
| Summarize last month's inbox | **RLM** | 100+ emails, needs aggregation |
| Find action items across 500 emails | **RLM** | Complex analysis, chunking needed |
| Apply label to 5 messages | Normal | Simple batch operation |
| Categorize all emails by sender | **RLM** | Multi-step classification |

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

### Workflow 1: Find and Organize Emails

When user asks to "organize my support emails with a label":

1. **Search for emails:**
   ```bash
   python gmail_read.py --query "from:support@company.com" --format minimal
   ```

2. **Create label:**
   ```bash
   python gmail_labels.py --action create --name "Support"
   ```

3. **Apply label to messages:**
   ```bash
   python gmail_labels.py --action apply --label-name "Support" --message-ids "ID1,ID2,ID3"
   ```

### Workflow 2: Read and Reply

When user asks to "read my emails from John and send a reply":

1. **Search for emails:**
   ```bash
   python gmail_read.py --query "from:john@example.com" --max-results 5 --format full
   ```

2. **Parse the response and present to user**

3. **Send reply:**
   ```bash
   python gmail_send.py --to "john@example.com" --subject "Re: Previous Subject" --body "Reply text"
   ```

### Workflow 3: Daily Email Summary

When user asks "what emails did I get today?":

```bash
python gmail_read.py --query "newer_than:1d" --max-results 50 --format metadata
```

Parse the JSON and present a summary organized by sender or label.

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

Version: 0.3.0
Last Updated: 2026-01-17

**Changelog:**
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
