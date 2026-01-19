# RLM Function Reference

Complete catalog of all functions available in the `gmail_rlm_repl.py` environment.

## Table of Contents

- [Core RLM Functions](#core-rlm-functions)
- [Chunking Functions](#chunking-functions)
- [Filter Functions](#filter-functions)
- [Utility Functions](#utility-functions)
- [Pre-built Workflows](#pre-built-workflows)
- [Security Helper Functions](#security-helper-functions)
- [Security Workflows](#security-workflows)

---

## Core RLM Functions

These functions are injected into the RLM environment by `gmail_rlm_repl.py`.

### `llm_query(prompt, context, model=None, json_output=False)`

Perform a recursive LLM call via Anthropic SDK.

**Parameters:**
- `prompt` (str): The prompt/question to ask the LLM
- `context` (str): Context data (emails, text, etc.)
- `model` (str, optional): Model to use (default: claude-sonnet-4-20250514)
- `json_output` (bool): Request JSON-formatted response

**Returns:** String response from LLM

**Example:**
```python
summary = llm_query(
    "Summarize these emails in 3 bullet points",
    context=str([e['snippet'] for e in emails[:10]])
)
```

**Cost:** ~$0.001-0.01 per call depending on context size and model

---

### `parallel_llm_query(prompts, max_workers=5, model=None, json_output=False)`

Execute multiple LLM queries concurrently for faster processing.

**Parameters:**
- `prompts` (list): List of (prompt, context) tuples
- `max_workers` (int): Number of parallel workers (default: 5)
- `model` (str, optional): Model to use
- `json_output` (bool): Request JSON-formatted responses

**Returns:** List of responses in same order as input

**Example:**
```python
by_sender = chunk_by_sender(emails)
top_5 = list(by_sender.items())[:5]

prompts = [
    (f"Summarize emails from {sender}", str([m['snippet'] for m in msgs]))
    for sender, msgs in top_5
]

results = parallel_llm_query(prompts, max_workers=5)
# results[0] corresponds to top_5[0], etc.
```

**Performance:** 3-5x faster than sequential `llm_query()` calls

---

### `parallel_map(func_prompt, chunks, context_fn, max_workers=5, model=None, json_output=False)`

Apply the same prompt to multiple chunks in parallel. Simpler interface than `parallel_llm_query`.

**Parameters:**
- `func_prompt` (str): The prompt to apply to each chunk
- `chunks` (list): List of data chunks
- `context_fn` (callable): Function to extract context from each chunk
- `max_workers` (int): Number of parallel workers (default: 5)
- `model` (str, optional): Model to use
- `json_output` (bool): Request JSON responses

**Returns:** List of results, one per chunk

**Example:**
```python
chunks = chunk_by_size(emails, 20)

summaries = parallel_map(
    func_prompt="Summarize these emails focusing on action items",
    chunks=chunks,
    context_fn=lambda chunk: str([e['snippet'] for e in chunk]),
    max_workers=5
)
```

---

### `FINAL(result)`

Output the final result of the RLM execution.

**Parameters:**
- `result` (str): The final result to output

**Example:**
```python
result = weekly_summary(emails)
FINAL(result)
```

---

### `FINAL_VAR(var_name)`

Output a variable as JSON-formatted final result.

**Parameters:**
- `var_name` (str): Name of variable to output

**Example:**
```python
result = inbox_triage(emails)
FINAL_VAR('result')
# Outputs: {"urgent": [...], "action_required": [...], ...}
```

---

### `get_session()`

Get session statistics (token usage, cost, LLM calls).

**Returns:** Dict with session info
```python
{
    "total_tokens": 15000,
    "total_cost": 0.45,
    "llm_calls": 12
}
```

**Example:**
```python
result = security_triage(emails)
session = get_session()
print(f"Analysis cost: ${session['total_cost']:.2f}")
FINAL(result['executive_summary'])
```

---

## Chunking Functions

### `chunk_by_size(emails, chunk_size=20)`

Split emails into fixed-size chunks.

**Parameters:**
- `emails` (list): List of email dictionaries
- `chunk_size` (int): Emails per chunk (default: 20)

**Returns:** List of email chunks

**Example:**
```python
chunks = chunk_by_size(emails, 20)
for i, chunk in enumerate(chunks):
    print(f"Chunk {i+1}: {len(chunk)} emails")
```

**Use Case:** Batch processing for LLM context limits

---

### `chunk_by_sender(emails)`

Group emails by sender email address.

**Parameters:**
- `emails` (list): List of email dictionaries

**Returns:** Dict mapping sender email to list of their emails

**Example:**
```python
by_sender = chunk_by_sender(emails)
for sender, msgs in by_sender.items():
    print(f"{sender}: {len(msgs)} emails")
```

**Use Case:** Sender analysis, communication pattern detection

---

### `chunk_by_sender_domain(emails)`

Group emails by sender's domain.

**Parameters:**
- `emails` (list): List of email dictionaries

**Returns:** Dict mapping domain to list of emails

**Example:**
```python
by_domain = chunk_by_sender_domain(emails)
company_emails = by_domain.get('company.com', [])
```

**Use Case:** Organizational analysis, domain filtering

---

### `chunk_by_date(emails, period='day')`

Group emails by date period.

**Parameters:**
- `emails` (list): List of email dictionaries
- `period` (str): 'day', 'week', or 'month'

**Returns:** Dict mapping date key to list of emails

**Example:**
```python
by_week = chunk_by_date(emails, period='week')
for week, msgs in sorted(by_week.items()):
    print(f"{week}: {len(msgs)} emails")
```

**Use Case:** Time-based analysis, weekly summaries

---

### `chunk_by_thread(emails)`

Group emails by thread ID.

**Parameters:**
- `emails` (list): List of email dictionaries

**Returns:** Dict mapping thread ID to list of emails in thread

**Example:**
```python
by_thread = chunk_by_thread(emails)
for thread_id, thread_emails in by_thread.items():
    if len(thread_emails) > 1:
        print(f"Conversation thread with {len(thread_emails)} messages")
```

**Use Case:** Conversation analysis, thread summarization

---

### `chunk_by_time(emails, window_minutes=5)` *(Security)*

Group emails into time windows for correlation analysis.

**Parameters:**
- `emails` (list): List of email dictionaries with 'date' field
- `window_minutes` (int): Size of time buckets (default: 5)

**Returns:** Dict mapping window timestamp to emails in that window

**Example:**
```python
windows = chunk_by_time(security_alerts, window_minutes=5)
for window_time, alerts in windows.items():
    if len(alerts) >= 3:
        print(f"{window_time}: {len(alerts)} alerts (potential kill chain)")
```

**Use Case:** Kill chain detection, attack correlation

---

## Filter Functions

### `filter_emails(emails, predicate)`

Filter emails using a custom predicate function.

**Parameters:**
- `emails` (list): List of email dictionaries
- `predicate` (callable): Function that takes email dict, returns bool

**Returns:** Filtered list of emails

**Example:**
```python
# Keep only emails with attachments mentioned
with_attachments = filter_emails(
    emails,
    lambda e: 'attachment' in e.get('snippet', '').lower()
)
```

---

### `filter_by_keyword(emails, keyword, fields=None)`

Filter emails containing a keyword.

**Parameters:**
- `emails` (list): List of email dictionaries
- `keyword` (str): Keyword to search for (case-insensitive)
- `fields` (list, optional): Fields to search (default: ['subject', 'snippet', 'body'])

**Returns:** Emails containing the keyword

**Example:**
```python
urgent_emails = filter_by_keyword(emails, 'urgent')
invoice_emails = filter_by_keyword(emails, 'invoice', fields=['subject'])
```

---

### `filter_by_sender(emails, sender_pattern)`

Filter emails from senders matching a pattern.

**Parameters:**
- `emails` (list): List of email dictionaries
- `sender_pattern` (str): Substring to match in 'from' field (case-insensitive)

**Returns:** Emails from matching senders

**Example:**
```python
company_emails = filter_by_sender(emails, '@company.com')
boss_emails = filter_by_sender(emails, 'boss@company.com')
```

---

## Utility Functions

### `sort_emails(emails, by='date', reverse=True)`

Sort emails by a field.

**Parameters:**
- `emails` (list): List of email dictionaries
- `by` (str): Field to sort by ('date', 'from', 'subject')
- `reverse` (bool): Sort descending (default: True for newest first)

**Returns:** Sorted list of emails

**Example:**
```python
newest_first = sort_emails(emails, by='date', reverse=True)
alphabetical = sort_emails(emails, by='from', reverse=False)
```

---

### `get_top_senders(emails, n=10)`

Get the top N senders by email count.

**Parameters:**
- `emails` (list): List of email dictionaries
- `n` (int): Number of top senders to return (default: 10)

**Returns:** List of (sender, count) tuples, sorted by count descending

**Example:**
```python
top_5 = get_top_senders(emails, 5)
for sender, count in top_5:
    print(f"{sender}: {count} emails")
```

---

### `extract_email_summary(email)`

Create a concise text summary of a single email.

**Parameters:**
- `email` (dict): Email dictionary

**Returns:** Formatted summary string

**Example:**
```python
for email in emails[:5]:
    print(extract_email_summary(email))
    print("---")
```

**Output Format:**
```
From: John Doe <john@example.com>
Subject: Meeting Tomorrow
Date: Wed, 15 Jan 2026 10:30:00 -0800
Preview: Quick reminder about our meeting...
```

---

### `batch_extract_summaries(emails, max_chars=4000)`

Create a combined summary of multiple emails, respecting character limit.

**Parameters:**
- `emails` (list): List of email dictionaries
- `max_chars` (int): Maximum total characters (default: 4000)

**Returns:** Combined summary string

**Example:**
```python
context = batch_extract_summaries(emails[:20], max_chars=3000)
summary = llm_query("Summarize these emails", context=context)
```

**Use Case:** Building context for LLM queries without exceeding limits

---

### `aggregate_results(results, separator='\n\n---\n\n')`

Combine multiple LLM sub-query results into a single output.

**Parameters:**
- `results` (list): List of result strings
- `separator` (str): String to put between results

**Returns:** Aggregated result string

**Example:**
```python
chunk_summaries = parallel_map("Summarize", chunks, str, max_workers=5)
final_summary = aggregate_results(chunk_summaries, separator="\n\n")
FINAL(final_summary)
```

---

### `deduplicate_emails(emails)`

Remove duplicate emails based on message ID.

**Parameters:**
- `emails` (list): List of email dictionaries

**Returns:** Deduplicated list

**Example:**
```python
unique_emails = deduplicate_emails(emails)
print(f"Removed {len(emails) - len(unique_emails)} duplicates")
```

---

### `prepare_llm_batch(chunks, prompt_template, context_fields=None)`

Prepare batch of (prompt, context) tuples for `parallel_llm_query`.

**Parameters:**
- `chunks` (list): List of email chunks
- `prompt_template` (str): Prompt to use for each chunk
- `context_fields` (list, optional): Email fields to include in context

**Returns:** List of (prompt, context) tuples

**Example:**
```python
chunks = chunk_by_size(emails, 20)
batch = prepare_llm_batch(
    chunks,
    "Summarize these emails",
    context_fields=['subject', 'snippet']
)
results = parallel_llm_query(batch, max_workers=5)
```

---

## Pre-built Workflows

### `inbox_triage(emails)`

Classify emails into categories using LLM.

**Categories:** urgent, action_required, fyi, newsletter

**Parameters:**
- `emails` (list): List of email dictionaries

**Returns:** Dict mapping category to list of emails
```python
{
    "urgent": [...],
    "action_required": [...],
    "fyi": [...],
    "newsletter": [...]
}
```

**Example:**
```python
result = inbox_triage(emails)
print(f"Urgent: {len(result['urgent'])}")
print(f"Action Required: {len(result['action_required'])}")

# Show urgent email subjects
for email in result['urgent']:
    print(f"  - {email['subject']}")

FINAL(f"Found {len(result['urgent'])} urgent emails")
```

**Cost:** ~$0.002 per email

---

### `weekly_summary(emails)`

Generate an executive summary of emails.

**Parameters:**
- `emails` (list): List of email dictionaries

**Returns:** Executive summary string

**Process:**
1. Groups emails by day
2. Summarizes each day in parallel
3. Combines into overall executive brief

**Example:**
```python
summary = weekly_summary(emails)
FINAL(summary)
```

**Output Example:**
```
**Key Themes:**
- Project Alpha launch preparation
- Q1 budget review meetings
- Customer feedback on new feature

**Important Action Items:**
- Complete proposal by Friday
- Schedule team sync for next week
- Review and approve budget

**Notable Updates:**
- New client signed contract
- Product release postponed to next month
```

**Cost:** ~$0.001 per email

---

### `find_action_items(emails)`

Extract action items with deadlines.

**Parameters:**
- `emails` (list): List of email dictionaries

**Returns:** List of action item dicts
```python
[
    {
        "task": "Review proposal",
        "deadline": "Friday",
        "sender": "boss@company.com",
        "priority": "high"
    },
    ...
]
```

**Example:**
```python
items = find_action_items(emails)
for item in items:
    print(f"[{item['priority'].upper()}] {item['task']} - due: {item.get('deadline', 'N/A')}")
```

**Cost:** ~$0.0015 per email

---

### `sender_analysis(emails, top_n=5)`

Analyze communication patterns for top senders.

**Parameters:**
- `emails` (list): List of email dictionaries
- `top_n` (int): Number of top senders to analyze (default: 5)

**Returns:** Dict mapping sender to analysis
```python
{
    "sender@domain.com": {
        "count": 45,
        "summary": "Primarily discusses project updates and requests reviews...",
        "tone": "formal"
    },
    ...
}
```

**Example:**
```python
analysis = sender_analysis(emails, top_n=3)
for sender, info in analysis.items():
    print(f"{sender} ({info['count']} emails):")
    print(f"  Tone: {info['tone']}")
    print(f"  Summary: {info['summary']}\n")
```

**Cost:** ~$0.003 per sender analyzed

---

## Security Helper Functions

### `extract_severity(alert)`

Normalize severity from different security tool formats.

**Parameters:**
- `alert` (dict): Email dictionary with security alert data

**Returns:** Normalized priority: "P1" | "P2" | "P3" | "P4" | "P5"

**Supported Tools:**
- CrowdStrike, Splunk, Azure Sentinel, Palo Alto, Elastic, Microsoft Defender, Cisco Secure, Fortinet

**Example:**
```python
for alert in security_emails:
    severity = extract_severity(alert)
    if severity == "P1":
        print(f"CRITICAL: {alert['subject']}")
```

---

### `classify_alerts(emails, llm_query, batch_size=20)`

Batch classification of security alerts into P1-P5 severity levels.

**Parameters:**
- `emails` (list): List of email dictionaries
- `llm_query` (callable): The llm_query function
- `batch_size` (int): Alerts per LLM call (default: 20)

**Returns:** Dict mapping priority to list of alerts
```python
{
    "P1": [...],  # Critical
    "P2": [...],  # High
    "P3": [...],  # Medium
    "P4": [...],  # Low
    "P5": [...]   # Info
}
```

**Example:**
```python
classifications = classify_alerts(security_emails, llm_query)
print(f"P1 Critical: {len(classifications['P1'])}")
print(f"P2 High: {len(classifications['P2'])}")
```

**Cost:** ~$0.002 per alert

---

### `extract_iocs(emails)`

Extract Indicators of Compromise from security alerts.

**Parameters:**
- `emails` (list): List of email dictionaries

**Returns:** Dict with IOC lists
```python
{
    "ips": ["192.168.1.1", ...],
    "domains": ["malicious.com", ...],
    "file_hashes": {
        "md5": [...],
        "sha1": [...],
        "sha256": [...]
    },
    "email_addresses": ["attacker@evil.com", ...],
    "urls": ["http://phishing.site", ...]
}
```

**Example:**
```python
iocs = extract_iocs(security_alerts)
print(f"Extracted {len(iocs['ips'])} IPs")
print(f"Extracted {len(iocs['domains'])} domains")
print(f"Extracted {len(iocs['file_hashes']['sha256'])} SHA256 hashes")

for ip in iocs['ips']:
    check_threat_intel(ip)
```

**Cost:** Free (regex-based)

---

### `map_to_mitre(alert, llm_query=None)`

Map security alert to MITRE ATT&CK technique IDs.

**Parameters:**
- `alert` (dict): Email dictionary with security alert
- `llm_query` (callable, optional): LLM function for enhanced mapping

**Returns:** List of MITRE technique IDs

**Example:**
```python
techniques = map_to_mitre(phishing_alert, llm_query)
print(f"MITRE Techniques: {', '.join(techniques)}")
# Output: "T1566.001, T1059.001"
```

**Pattern Matching:** Covers 15+ common techniques
**LLM Enhancement:** Optional for ambiguous alerts

---

### `correlate_by_source_ip(emails, llm_query)`

Group alerts by source IP and analyze for coordinated attacks.

**Parameters:**
- `emails` (list): List of email dictionaries
- `llm_query` (callable): The llm_query function

**Returns:** Dict mapping IPs to analysis
```python
{
    "192.168.1.100": {
        "alert_count": 5,
        "timespan_minutes": 15,
        "attack_type": "Brute Force",
        "severity": "P2",
        "first_seen": "2025-01-15T10:00:00",
        "last_seen": "2025-01-15T10:15:00",
        "alerts": [...]
    },
    ...
}
```

**Example:**
```python
ip_analysis = correlate_by_source_ip(firewall_alerts, llm_query)
for ip, data in ip_analysis.items():
    if data['alert_count'] >= 10:
        print(f"HIGH ACTIVITY: {ip} - {data['attack_type']}")
```

**Cost:** ~$0.001 per IP analyzed

---

### `detect_suspicious_senders(emails, llm_query=None)`

Identify phishing attempts, spoofing, and domain squatting.

**Parameters:**
- `emails` (list): List of email dictionaries
- `llm_query` (callable, optional): LLM for enhanced analysis

**Returns:** List of suspicious sender detections
```python
[
    {
        "sender": "admin@g00gle.com",
        "reason": "Domain squatting detected",
        "confidence": 0.95,
        "email_id": "...",
        "auth_failed": True
    },
    ...
]
```

**Checks:**
- Lookalike domains (goog1e.com vs google.com)
- Display name spoofing
- Failed authentication (SPF/DKIM/DMARC)
- Brand impersonation

**Example:**
```python
suspicious = detect_suspicious_senders(inbox_emails, llm_query)
for detection in suspicious:
    if detection['confidence'] > 0.8:
        print(f"⚠️ {detection['sender']}: {detection['reason']}")
```

**Cost:** Free (pattern-based) + ~$0.0005 per email if LLM used

---

### `analyze_attachments(emails)`

Extract attachment metadata and identify risk indicators.

**Parameters:**
- `emails` (list): List of email dictionaries

**Returns:** List of risky attachments
```python
[
    {
        "filename": "invoice.exe",
        "mime_type": "application/x-msdownload",
        "risk_level": "HIGH",
        "reason": "Executable file in financial context",
        "email_id": "...",
        "email_subject": "..."
    },
    ...
]
```

**Risk Indicators:**
- Dangerous file extensions (.exe, .bat, .ps1, etc.)
- Financial context (invoice, payment)
- Urgency indicators

**Example:**
```python
risky_attachments = analyze_attachments(inbox)
for attachment in risky_attachments:
    if attachment['risk_level'] == 'HIGH':
        print(f"⚠️ HIGH RISK: {attachment['filename']} - {attachment['reason']}")
```

**Cost:** Free (metadata analysis only)

---

### `extract_and_analyze_urls(emails)`

Extract URLs and identify suspicious links.

**Parameters:**
- `emails` (list): List of email dictionaries

**Returns:** List of suspicious URLs
```python
[
    {
        "url": "http://bit.ly/abc123",
        "display_text": "unknown",
        "risk_level": "MEDIUM",
        "reason": "URL shortener in financial context",
        "email_id": "...",
        "email_subject": "..."
    },
    ...
]
```

**Checks:**
- URL shorteners (bit.ly, tinyurl)
- Suspicious TLDs (.xyz, .top, .tk)
- IP addresses as domains
- Excessive subdomains

**Example:**
```python
suspicious_urls = extract_and_analyze_urls(phishing_emails)
for url_data in suspicious_urls:
    print(f"{url_data['risk_level']}: {url_data['url']}")
    print(f"  Reason: {url_data['reason']}")
```

**Cost:** Free (pattern-based)

---

### `deduplicate_security_alerts(emails, similarity_threshold=0.9)`

Remove duplicate security alerts based on content similarity.

**Parameters:**
- `emails` (list): List of email dictionaries
- `similarity_threshold` (float): Similarity score 0.0-1.0 (default: 0.9)

**Returns:** Deduplicated list of emails

**Use Case:** Consolidate recurring alerts (e.g., same vuln across 50 servers)

**Example:**
```python
unique_alerts = deduplicate_security_alerts(vuln_scan_results)
print(f"Reduced from {len(all_alerts)} to {len(unique_alerts)} unique alerts")
```

**Cost:** Free

---

## Security Workflows

### `security_triage(emails, deduplicate=True, include_executive_summary=True)`

Complete security alert triage pipeline.

**Parameters:**
- `emails` (list): List of email dictionaries (security alerts)
- `deduplicate` (bool): Remove duplicates (default: True)
- `include_executive_summary` (bool): Generate LLM summary (default: True)

**Returns:** Comprehensive triage results
```python
{
    "summary": {
        "total_alerts": 500,
        "unique_alerts": 347,
        "critical_count": 5,
        "kill_chains_detected": 2
    },
    "classifications": {
        "P1": [...],
        "P2": [...],
        "P3": [...],
        "P4": [...],
        "P5": [...]
    },
    "iocs": {
        "ips": [...],
        "domains": [...],
        "file_hashes": {...},
        ...
    },
    "kill_chains": [
        {
            "pattern": "Initial Access → Execution",
            "mitre_techniques": ["T1566", "T1059"],
            "severity": "P1",
            ...
        }
    ],
    "source_ip_analysis": {...},
    "suspicious_senders": [...],
    "risky_attachments": [...],
    "suspicious_urls": [...],
    "executive_summary": "LLM-generated brief for CISO"
}
```

**Pipeline Steps:**
1. Deduplicate recurring alerts
2. Classify by severity (P1-P5)
3. Extract IOCs
4. Detect kill chains (5-min windows)
5. Correlate by source IP
6. Identify suspicious senders
7. Analyze attachments and URLs
8. Generate executive summary

**Example:**
```python
result = security_triage(security_alerts)
print(f"P1 Critical: {len(result['classifications']['P1'])}")
print(f"Kill Chains: {len(result['kill_chains'])}")
print(f"\n{result['executive_summary']}")
```

**Cost:** ~$0.004 per alert

---

### `detect_attack_chains(emails, window_minutes=5, min_alerts_per_chain=2)`

Multi-pass correlation for sophisticated attack detection.

**Parameters:**
- `emails` (list): List of email dictionaries (security alerts)
- `window_minutes` (int): Time window size (default: 5)
- `min_alerts_per_chain` (int): Minimum alerts for a chain (default: 2)

**Returns:** List of detected attack chains
```python
[
    {
        "attack_id": "chain_20250115_001",
        "start_time": "2025-01-15T10:00:00",
        "end_time": "2025-01-15T10:25:00",
        "duration_minutes": 25,
        "pattern": "Phishing → Execution → C2 Callback",
        "mitre_techniques": ["T1566", "T1059", "T1071"],
        "severity": "P1",
        "confidence": 0.92,
        "affected_systems": ["user@company.com", "192.168.1.50"],
        "alert_count": 5,
        "alerts": [...]
    },
    ...
]
```

**Analysis Passes:**
1. Group into time windows
2. Detect patterns within windows
3. Correlate across windows
4. Confidence scoring via LLM

**Example:**
```python
chains = detect_attack_chains(security_alerts, window_minutes=5)
critical_chains = [c for c in chains if c['severity'] in ['P1', 'P2']]

for chain in critical_chains:
    print(f"{chain['attack_id']}: {chain['pattern']}")
    print(f"  MITRE: {', '.join(chain['mitre_techniques'])}")
    print(f"  Confidence: {chain['confidence']:.0%}")
```

**Cost:** ~$0.005 per alert

---

### `phishing_analysis(emails)`

Specialized phishing detection and categorization.

**Parameters:**
- `emails` (list): List of email dictionaries

**Returns:** Phishing analysis results
```python
{
    "credential_harvesting": [
        {"email_id": "...", "subject": "...", "reason": "..."}
    ],
    "bec_attempts": [...],
    "brand_impersonation": [...],
    "malicious_attachments": [...],
    "malicious_links": [...],
    "summary": "LLM-generated summary"
}
```

**Analyzes:**
- Credential harvesting
- Business email compromise (BEC)
- Brand impersonation
- Attachment-based phishing
- Link-based phishing

**Example:**
```python
phishing_results = phishing_analysis(suspicious_emails)
high_risk = phishing_results['credential_harvesting']

print(f"Credential Harvesting: {len(phishing_results['credential_harvesting'])}")
print(f"BEC Attempts: {len(phishing_results['bec_attempts'])}")
print(f"\n{phishing_results['summary']}")
```

**Cost:** ~$0.003 per email

---

## Cost Summary

| Function Category | Cost Range | Speed |
|------------------|-----------|-------|
| Core LLM (llm_query) | $0.001-0.01/call | Medium |
| Parallel LLM | Same as sequential | 3-5x faster |
| Chunking/Filter/Utility | Free | Instant |
| inbox_triage | $0.002/email | Medium |
| weekly_summary | $0.001/email | Fast |
| find_action_items | $0.0015/email | Medium |
| sender_analysis | $0.003/sender | Medium |
| Security triage | $0.004/alert | Medium |
| Attack chain detection | $0.005/alert | Slow |
| Phishing analysis | $0.003/email | Medium |
| IOC extraction | Free | Instant |

**Model Comparison:**
- `claude-sonnet-4-20250514`: Accurate, $0.015/1K tokens
- `claude-haiku-4-20250514`: Fast & cheap, $0.0015/1K tokens (10x cheaper)

---

## Quick Reference

**Most Common Patterns:**

```python
# 1. Triage inbox
result = inbox_triage(emails)
FINAL(f"{len(result['urgent'])} urgent emails")

# 2. Weekly summary
summary = weekly_summary(emails)
FINAL(summary)

# 3. Security triage
result = security_triage(emails)
FINAL(result['executive_summary'])

# 4. Top senders
by_sender = chunk_by_sender(emails)
top_5 = get_top_senders(emails, 5)
for sender, count in top_5:
    print(f"{sender}: {count}")

# 5. Custom analysis with parallel processing
chunks = chunk_by_size(emails, 20)
results = parallel_map("Summarize", chunks, str, max_workers=5)
FINAL(aggregate_results(results))
```

---

For orchestration guidance, see `RLM_AGENT_GUIDE.md`.
