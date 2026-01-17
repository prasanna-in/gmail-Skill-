# RLM Patterns for Gmail Analysis

This document provides patterns and examples for using the RLM (Recursive Language Model) mode of the Gmail skill. RLM enables large-scale email analysis by recursively processing data in chunks.

## Core Concepts

### What is RLM?

RLM (Recursive Language Models) is an approach where:
1. Data is loaded into a REPL environment (emails as Python variables)
2. Code examines and partitions the data
3. LLM is called recursively via `llm_query()` on smaller chunks
4. Results are aggregated into a final answer

### Why Use RLM?

| Problem | RLM Solution |
|---------|--------------|
| 100 email limit per query | Pagination + chunking handles 1000+ |
| Context degradation with many emails | Each sub-query has fresh, focused context |
| Complex multi-step analysis | Programmatic workflows with LLM calls |
| Memory/token limits | Process in batches, aggregate results |

## Basic Patterns

### Pattern 1: Simple Chunked Summary

Process emails in fixed-size batches:

```python
# Process 20 emails at a time
all_summaries = []
for chunk in chunk_by_size(emails, 20):
    summary = llm_query(
        'Summarize these emails in 2-3 sentences',
        context=str([e['snippet'] for e in chunk])
    )
    all_summaries.append(summary)

# Combine summaries
final = llm_query(
    'Combine these summaries into one coherent overview',
    context='\n\n'.join(all_summaries)
)
FINAL(final)
```

### Pattern 2: Group by Sender

Analyze emails organized by who sent them:

```python
by_sender = chunk_by_sender(emails)
summaries = []

# Process top 10 senders by volume
top_senders = sorted(by_sender.items(), key=lambda x: -len(x[1]))[:10]

for sender, msgs in top_senders:
    summary = llm_query(
        f'What is {sender} emailing about? Be brief.',
        context=str([m['snippet'] for m in msgs[:10]])  # Limit context
    )
    summaries.append(f"**{sender}** ({len(msgs)} emails): {summary}")

FINAL('## Inbox Summary by Sender\n\n' + '\n\n'.join(summaries))
```

### Pattern 3: Time-Based Analysis

Analyze email patterns over time:

```python
by_week = chunk_by_date(emails, 'week')
weekly_summaries = []

for week, msgs in sorted(by_week.items()):
    summary = llm_query(
        f'Summarize the key topics and activity for {week}',
        context=batch_extract_summaries(msgs, max_chars=3000)
    )
    weekly_summaries.append(f"### {week}\n{summary}")

FINAL('## Weekly Email Activity\n\n' + '\n\n'.join(weekly_summaries))
```

### Pattern 4: Action Item Extraction

Find actionable items across many emails:

```python
all_items = []

for chunk in chunk_by_size(emails, 15):
    items = llm_query(
        'Extract any action items, deadlines, or requests. '
        'Format as bullet points. Return "None" if no actions.',
        context=str([{'from': e['from'], 'subject': e['subject'], 'snippet': e['snippet']} for e in chunk])
    )
    if items.strip().lower() != 'none':
        all_items.append(items)

# Consolidate and prioritize
if all_items:
    final = llm_query(
        'Consolidate these action items, remove duplicates, and prioritize them',
        context='\n\n'.join(all_items)
    )
    FINAL('## Action Items\n\n' + final)
else:
    FINAL('No action items found in the analyzed emails.')
```

### Pattern 5: Email Classification

Categorize emails programmatically:

```python
categories = {
    'urgent': [],
    'action_required': [],
    'fyi': [],
    'promotional': [],
    'other': []
}

for email in emails:
    category = llm_query(
        'Classify this email into exactly one category: urgent, action_required, fyi, promotional, or other. '
        'Reply with just the category name.',
        context=f"From: {email['from']}\nSubject: {email['subject']}\nPreview: {email['snippet']}"
    ).strip().lower()

    if category in categories:
        categories[category].append(email['id'])
    else:
        categories['other'].append(email['id'])

# Output structured result
FINAL_VAR('categories')
```

## Advanced Patterns

### Pattern 6: Two-Pass Analysis

First filter, then deep analyze:

```python
# Pass 1: Quick filter for relevant emails
relevant = []
for chunk in chunk_by_size(emails, 30):
    for email in chunk:
        is_relevant = llm_query(
            'Is this email about project deadlines or deliverables? Reply YES or NO only.',
            context=f"Subject: {email['subject']}\nSnippet: {email['snippet']}"
        ).strip().upper()

        if 'YES' in is_relevant:
            relevant.append(email)

print(f"Found {len(relevant)} relevant emails")

# Pass 2: Deep analysis of relevant emails only
if relevant:
    analysis = llm_query(
        'Analyze these project-related emails. What are the key deadlines and deliverables?',
        context=batch_extract_summaries(relevant, max_chars=4000)
    )
    FINAL(f"## Project Analysis\n\nAnalyzed {len(relevant)} relevant emails.\n\n{analysis}")
else:
    FINAL("No project-related emails found.")
```

### Pattern 7: Keyword Pre-filtering

Use Python to filter before LLM analysis (more efficient):

```python
# Programmatic filter (fast, no LLM calls)
urgent_keywords = ['urgent', 'asap', 'immediately', 'critical', 'deadline']
potentially_urgent = filter_emails(
    emails,
    lambda e: any(kw in e.get('subject', '').lower() or kw in e.get('snippet', '').lower()
                  for kw in urgent_keywords)
)

print(f"Pre-filtered to {len(potentially_urgent)} potentially urgent emails")

# LLM verification (accurate but slower)
confirmed_urgent = []
for email in potentially_urgent:
    is_urgent = llm_query(
        'Is this email genuinely urgent or time-sensitive? Reply YES or NO.',
        context=extract_email_summary(email)
    ).strip().upper()

    if 'YES' in is_urgent:
        confirmed_urgent.append(email)

# Summarize confirmed urgent emails
if confirmed_urgent:
    summary = llm_query(
        'Summarize these urgent emails and what actions are needed',
        context=batch_extract_summaries(confirmed_urgent)
    )
    FINAL(f"## Urgent Emails ({len(confirmed_urgent)})\n\n{summary}")
else:
    FINAL("No confirmed urgent emails found.")
```

### Pattern 8: Hierarchical Summarization

Summarize in levels for very large datasets:

```python
# Level 1: Summarize each chunk
chunk_summaries = []
for i, chunk in enumerate(chunk_by_size(emails, 25)):
    summary = llm_query(
        'Summarize the main topics and themes in these emails (2-3 sentences)',
        context=batch_extract_summaries(chunk, max_chars=3000)
    )
    chunk_summaries.append(f"Batch {i+1}: {summary}")

# Level 2: Summarize the summaries
if len(chunk_summaries) > 5:
    # Further consolidate if many batches
    meta_summaries = []
    for i in range(0, len(chunk_summaries), 5):
        batch = chunk_summaries[i:i+5]
        meta = llm_query(
            'Synthesize these summaries into key themes',
            context='\n\n'.join(batch)
        )
        meta_summaries.append(meta)

    final = llm_query(
        'Create a comprehensive executive summary from these themes',
        context='\n\n'.join(meta_summaries)
    )
else:
    final = llm_query(
        'Create a comprehensive executive summary from these batch summaries',
        context='\n\n'.join(chunk_summaries)
    )

FINAL(f"## Executive Summary ({len(emails)} emails analyzed)\n\n{final}")
```

### Pattern 9: Thread Analysis

Analyze email conversations:

```python
by_thread = chunk_by_thread(emails)

# Find threads with multiple messages (actual conversations)
conversations = {tid: msgs for tid, msgs in by_thread.items() if len(msgs) > 1}

print(f"Found {len(conversations)} email threads with multiple messages")

thread_summaries = []
for thread_id, messages in list(conversations.items())[:10]:  # Top 10 threads
    # Sort by date within thread
    sorted_msgs = sort_emails(messages, by='date', reverse=False)

    summary = llm_query(
        'Summarize this email conversation. Who is involved and what is being discussed?',
        context='\n---\n'.join([extract_email_summary(m) for m in sorted_msgs])
    )

    subject = sorted_msgs[0].get('subject', 'No Subject')
    thread_summaries.append(f"**{subject}** ({len(messages)} emails)\n{summary}")

FINAL('## Email Conversations\n\n' + '\n\n'.join(thread_summaries))
```

### Pattern 10: Comparative Analysis

Compare patterns across groups:

```python
by_domain = chunk_by_sender_domain(emails)

# Focus on top domains
top_domains = sorted(by_domain.items(), key=lambda x: -len(x[1]))[:5]

domain_profiles = []
for domain, msgs in top_domains:
    profile = llm_query(
        f'Characterize the emails from {domain}. What type of communication is it? '
        'Is it professional, promotional, automated, personal?',
        context=batch_extract_summaries(msgs[:15], max_chars=2000)
    )
    domain_profiles.append({
        'domain': domain,
        'count': len(msgs),
        'profile': profile
    })

# Create comparison
comparison = llm_query(
    'Compare these email sources. Which require attention vs can be filtered?',
    context=json.dumps(domain_profiles, indent=2)
)

FINAL(f"## Email Source Analysis\n\n{comparison}\n\n### Details\n" +
      '\n'.join([f"- **{d['domain']}** ({d['count']}): {d['profile']}" for d in domain_profiles]))
```

## Best Practices

### 1. Limit Context Size

Always cap the context you pass to `llm_query()`:

```python
# Good - limited context
context = batch_extract_summaries(emails, max_chars=4000)

# Bad - potentially huge context
context = str(emails)  # Could be megabytes!
```

### 2. Use Progress Logging

For long operations, log progress to stderr:

```python
for i, chunk in enumerate(chunk_by_size(emails, 20)):
    print(f"Processing chunk {i+1}...", file=sys.stderr)
    # ... process ...
```

### 3. Handle Empty Results

Always check for empty data:

```python
by_sender = chunk_by_sender(emails)
if not by_sender:
    FINAL("No emails to analyze.")
else:
    # ... proceed with analysis ...
```

### 4. Fail Gracefully

Handle LLM errors in loops:

```python
results = []
for email in emails:
    result = llm_query('Analyze this', context=email['snippet'])
    if not result.startswith('[LLM Error'):
        results.append(result)
    else:
        print(f"Skipped email {email['id']}: {result}", file=sys.stderr)
```

### 5. Pre-filter When Possible

Use Python filtering before LLM calls:

```python
# Fast Python filter first
recent = filter_emails(emails, lambda e: '2026' in e.get('date', ''))

# Then LLM analysis on filtered set
summary = llm_query('Summarize', context=batch_extract_summaries(recent))
```

## Available Functions Reference

### Data Functions

| Function | Description |
|----------|-------------|
| `chunk_by_size(emails, n)` | Split into n-sized chunks |
| `chunk_by_sender(emails)` | Group by sender email |
| `chunk_by_sender_domain(emails)` | Group by sender domain |
| `chunk_by_date(emails, period)` | Group by day/week/month |
| `chunk_by_thread(emails)` | Group by thread ID |
| `filter_emails(emails, predicate)` | Filter with custom function |
| `filter_by_keyword(emails, kw)` | Filter by keyword |
| `filter_by_sender(emails, pattern)` | Filter by sender pattern |
| `sort_emails(emails, by, reverse)` | Sort by field |
| `get_top_senders(emails, n)` | Get top N senders by count |

### Output Functions

| Function | Description |
|----------|-------------|
| `extract_email_summary(email)` | Create text summary of one email |
| `batch_extract_summaries(emails, max_chars)` | Combined summary with char limit |
| `aggregate_results(results, separator)` | Combine multiple results |
| `deduplicate_emails(emails)` | Remove duplicate emails |

### Core Functions

| Function | Description |
|----------|-------------|
| `llm_query(prompt, context)` | Recursive LLM call via Claude CLI |
| `FINAL(result)` | Set final output (string) |
| `FINAL_VAR(var_name)` | Set variable as output (JSON) |

## Troubleshooting

### "LLM Error: Query timed out"

The sub-query took too long. Solutions:
- Reduce context size passed to `llm_query()`
- Increase timeout: `llm_query(prompt, context, timeout=180)`

### "LLM Error: Claude CLI not found"

Ensure `claude` is in your PATH. Test with: `which claude`

### Code execution errors

Check your Python syntax. Common issues:
- Missing quotes in strings
- Unbalanced parentheses
- Using undefined variables

### No output / FINAL not called

Ensure your code calls `FINAL(result)` or `FINAL_VAR(name)` at the end.
