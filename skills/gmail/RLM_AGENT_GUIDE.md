# RLM Agent Orchestration Guide

**For Claude Code Agent Use Only**

This guide provides complete instructions for Claude Code's general-purpose Agent to orchestrate RLM (Recursive Language Model) email analysis operations via the Gmail skill.

## Purpose

This document replaces the standalone `gmail_agent.py` module. Instead of calling a subprocess agent, Claude Code's Agent directly orchestrates RLM operations by:

1. Interpreting user goals into RLM function calls
2. Executing `gmail_rlm_repl.py` subprocess with appropriate code
3. Managing multi-turn dialogue context
4. Formatting and presenting results naturally

## When to Activate

Activate RLM orchestration when the user requests:

### Trigger Patterns

**IMPORTANT: First check email count before activating RLM mode!**

Use RLM mode when:
- **≥100 emails** requiring any analysis (pagination needed)
- **<100 emails** with **complex** analysis (security_triage, attack_chains, phishing_analysis)
- **≥100 emails** with simple operations like categorization or summarization

Use Normal Mode + Agent direct analysis when:
- **<100 emails** with **simple** analysis (find_action_items, inbox_triage, weekly_summary)
- Agent can fetch with `gmail_read.py` and analyze the JSON directly (faster, cheaper)

**Trigger Keywords:**
- "Triage my inbox" / "Organize my emails" → Check count first!
- "Summarize my emails" / "What's in my inbox?" → Check count first!
- "Find action items" / "What do I need to do?" → Check count first!
- "Analyze security alerts" / "Check for threats" → Usually RLM (complex)
- "Find emails from..." / "Search for..." (with analysis intent) → Check count first!
- "What are the urgent emails?" → Check count first!
- Security-specific: "Triage alerts", "Find attack chains", "Detect phishing" → Always RLM (complex)

### Keywords Mapping
| User Keywords | Recommended Workflow |
|---------------|---------------------|
| triage, organize, categorize | `inbox_triage(emails)` |
| summarize, overview, weekly summary | `weekly_summary(emails)` |
| action items, tasks, deadlines | `find_action_items(emails)` |
| security alerts, threats | `security_triage(emails)` |
| attack chains, kill chains | `detect_attack_chains(emails)` |
| phishing, suspicious senders | `phishing_analysis(emails)` |
| top senders, sender analysis | `sender_analysis(emails)` |

## Orchestration Workflow

### Step 1: Understand User Goal

Parse the user's natural language request to determine:
- **Intent**: What does the user want to accomplish?
- **Scope**: Which emails to analyze (query, time range, max results)?
- **Output**: How should results be presented?

**Example:**
```
User: "Triage security alerts from last week"
Intent: Security alert classification and analysis
Scope: label:security-alerts newer_than:7d, ~500 emails
Output: Executive summary with P1/P2 breakdown
```

### Step 2: Select RLM Functions

Based on intent, choose appropriate RLM functions:

**Pre-built Workflows (recommended):**
- `inbox_triage(emails)` - Categorize into urgent/action/fyi/newsletter
- `weekly_summary(emails)` - Generate executive brief
- `find_action_items(emails)` - Extract tasks with deadlines
- `security_triage(emails)` - Complete security alert pipeline (P1-P5, IOCs, kill chains)
- `detect_attack_chains(emails, window_minutes=5)` - Multi-stage attack detection
- `phishing_analysis(emails)` - Categorize phishing attempts
- `sender_analysis(emails, top_n=5)` - Analyze communication patterns

**Custom Compositions:**
For non-standard requests, compose functions:
```python
# Example: "Find emails from top 3 senders about project X"
by_sender = chunk_by_sender(emails)
top_senders = get_top_senders(emails, 3)
project_emails = filter_by_keyword(emails, 'project x')
# ... compose logic
```

### Step 3: Construct RLM Code

Build the Python code to pass to `gmail_rlm_repl.py --code`:

**Template:**
```python
# Use pre-built workflow
result = WORKFLOW_FUNCTION(emails)
FINAL(result)
```

**Important:**
- Always end with `FINAL(result)` or `FINAL_VAR('variable_name')`
- Use `llm_query()` for custom LLM calls within the code
- Use `parallel_map()` for processing chunks in parallel
- Respect budget constraints (estimate cost before execution)

### Step 4: Estimate Cost & Confirm Budget

Calculate approximate cost based on:
- Email count
- Workflow complexity
- Model (default: claude-sonnet-4-20250514)

**Cost Guidelines:**
| Workflow | Per Email Cost | 100 Emails | 500 Emails |
|----------|---------------|------------|------------|
| inbox_triage | ~$0.002 | $0.20 | $1.00 |
| weekly_summary | ~$0.001 | $0.10 | $0.50 |
| find_action_items | ~$0.0015 | $0.15 | $0.75 |
| security_triage | ~$0.004 | $0.40 | $2.00 |
| detect_attack_chains | ~$0.005 | $0.50 | $2.50 |
| phishing_analysis | ~$0.003 | $0.30 | $1.50 |

**Budget Control:**
- Default budget: $1.00
- High-volume security analysis: $2.00-$5.00
- Warn user if estimated cost > $1.00
- Ask for confirmation if estimated cost > $2.00

### Step 5: Execute via Subprocess

Call `gmail_rlm_repl.py` with constructed code:

```bash
.venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py \
  --query "GMAIL_QUERY" \
  --max-results MAX_EMAILS \
  --max-budget BUDGET \
  --code "RLM_CODE"
```

**Parameters:**
- `--query`: Gmail search query (e.g., "newer_than:7d", "label:security-alerts")
- `--max-results`: Maximum emails to fetch (default: 100, max recommended: 1000)
- `--max-budget`: Budget limit in USD (default: $1.00)
- `--model`: LLM model (default: claude-sonnet-4-20250514, or use claude-haiku-4-20250514 for speed)
- `--code`: Python code to execute in RLM environment

### Step 6: Parse & Present Results

The subprocess returns JSON:
```json
{
  "status": "success",
  "result": "...",
  "session": {
    "total_tokens": 12000,
    "total_cost": 0.45,
    "llm_calls": 8
  }
}
```

**Present results naturally:**
- Format as markdown for readability
- Highlight key findings (P1 alerts, urgent emails, action items)
- Include session stats if relevant (cost, tokens used)
- Offer follow-up options based on results

### Step 7: Multi-Turn Dialogue

After presenting results, prepare for follow-up questions:

**Context Preservation:**
- Keep RLM result in memory for follow-up queries
- User may ask: "Show me P1 details", "What IOCs were found?", "Tell me more about..."
- Reference previous result instead of re-executing expensive RLM

**Example Multi-Turn Flow:**
```
Turn 1: "Triage security alerts"
  → Execute security_triage, store result as `triage_result`
  → Present: "Found 47 alerts: 5 P1, 12 P2, 30 P3+..."

Turn 2: "Show me P1 details"
  → Access triage_result['classifications']['P1']
  → Present: "P1 Critical Alerts: [details]"

Turn 3: "What IOCs were found?"
  → Access triage_result['iocs']
  → Present: "IOCs: [IPs, domains, hashes]"
```

**Optimization:**
- Cache expensive RLM results
- Only re-execute if user modifies query/scope
- Accumulate budget across turns

## Parameter Optimization

### Email Count → Chunk Size

Optimize chunk size based on email volume:

| Email Count | Chunk Size | Parallel Workers | Reasoning |
|-------------|-----------|-----------------|-----------|
| 1-50 | 10 | 3 | Small batch, minimize overhead |
| 51-200 | 20 | 5 | Standard processing |
| 201-500 | 30 | 5 | Balance throughput and context |
| 501-1000 | 40 | 8 | Large-scale, maximize parallelism |

**Example:**
```python
# Adaptive chunking
email_count = len(emails)
chunk_size = 10 if email_count < 50 else (20 if email_count < 200 else 30)

chunks = chunk_by_size(emails, chunk_size)
results = parallel_map(prompt, chunks, context_fn=batch_extract_summaries, max_workers=5)
```

### Model Selection

Choose model based on task complexity:

| Task | Recommended Model | Reasoning |
|------|------------------|-----------|
| Simple triage | claude-haiku-4-20250514 | 3x faster, 10x cheaper |
| Security analysis | claude-sonnet-4-20250514 | Better pattern recognition |
| Complex correlation | claude-sonnet-4-20250514 | Nuanced reasoning required |
| Bulk classification | claude-haiku-4-20250514 | High throughput needed |

**Usage:**
```bash
# Fast & cheap for simple tasks
--model claude-haiku-4-20250514

# Accurate for complex tasks (default)
--model claude-sonnet-4-20250514
```

## Available RLM Functions

### Core Functions

**`llm_query(prompt, context, model=None, json_output=False)`**
- Recursive LLM call via Anthropic SDK
- Returns: String response from LLM
- Example: `summary = llm_query("Summarize these emails", context=str(emails))`

**`parallel_llm_query(prompts, max_workers=5, model=None)`**
- Execute multiple LLM queries concurrently
- prompts: List of (prompt, context) tuples
- Returns: List of responses
- Example: `results = parallel_llm_query([(p1, c1), (p2, c2)], max_workers=5)`

**`parallel_map(func_prompt, chunks, context_fn, max_workers=5)`**
- Apply same prompt to multiple chunks in parallel
- context_fn: Function to extract context from each chunk
- Returns: List of results
- Example: `summaries = parallel_map("Summarize", chunks, lambda c: str(c))`

**`FINAL(result)` / `FINAL_VAR(var_name)`**
- Output final result
- FINAL: For string results
- FINAL_VAR: For complex structures (outputs as JSON)

**`get_session()`**
- Get session statistics
- Returns: `{"total_tokens": int, "total_cost": float, "llm_calls": int}`

### Chunking Functions

**`chunk_by_size(emails, chunk_size=20)`**
- Split into fixed-size chunks
- Returns: List of email chunks

**`chunk_by_sender(emails)`**
- Group by sender email address
- Returns: Dict mapping sender to emails

**`chunk_by_sender_domain(emails)`**
- Group by sender domain
- Returns: Dict mapping domain to emails

**`chunk_by_date(emails, period='day')`**
- Group by date period (day/week/month)
- Returns: Dict mapping date key to emails

**`chunk_by_thread(emails)`**
- Group by thread ID
- Returns: Dict mapping thread ID to emails

**`chunk_by_time(emails, window_minutes=5)`** *(Security)*
- Group into time windows for correlation
- Returns: Dict mapping window timestamp to emails

### Filter Functions

**`filter_emails(emails, predicate)`**
- Filter with custom function
- predicate: Function returning bool
- Returns: Filtered list

**`filter_by_keyword(emails, keyword, fields=['subject', 'snippet', 'body'])`**
- Filter by keyword in specified fields
- Returns: Matching emails

**`filter_by_sender(emails, sender_pattern)`**
- Filter by sender pattern (case-insensitive)
- Returns: Matching emails

### Utility Functions

**`sort_emails(emails, by='date', reverse=True)`**
- Sort by field
- Returns: Sorted list

**`get_top_senders(emails, n=10)`**
- Get top N senders by count
- Returns: List of (sender, count) tuples

**`extract_email_summary(email)`**
- Text summary of single email
- Returns: Formatted string

**`batch_extract_summaries(emails, max_chars=4000)`**
- Combined summary of multiple emails
- Returns: String within char limit

**`aggregate_results(results, separator='\n\n---\n\n')`**
- Combine multiple LLM results
- Returns: Aggregated string

**`deduplicate_emails(emails)`**
- Remove duplicates by message ID
- Returns: Deduplicated list

### Pre-built Workflows

**`inbox_triage(emails)`**
- Classify into categories: urgent, action_required, fyi, newsletter
- Returns: `{"urgent": [...], "action_required": [...], "fyi": [...], "newsletter": [...]}`

**`weekly_summary(emails)`**
- Generate executive summary
- Groups by day, summarizes, then creates overall brief
- Returns: Executive summary string

**`find_action_items(emails)`**
- Extract action items with deadlines
- Returns: `[{"task": "...", "deadline": "...", "sender": "...", "priority": "..."}]`

**`sender_analysis(emails, top_n=5)`**
- Analyze communication patterns for top senders
- Returns: `{"sender@domain.com": {"count": int, "summary": str, "tone": str}}`

### Security Functions

**`security_triage(emails, deduplicate=True, include_executive_summary=True)`**
- Complete security alert triage pipeline
- Returns: Comprehensive dict with classifications, IOCs, kill chains, executive summary
- See Security Workflows section for details

**`detect_attack_chains(emails, window_minutes=5, min_alerts_per_chain=2)`**
- Multi-pass correlation for sophisticated attacks
- Returns: List of detected attack chains with MITRE mappings

**`phishing_analysis(emails)`**
- Specialized phishing detection and categorization
- Returns: Dict with credential_harvesting, bec_attempts, brand_impersonation, etc.

**`classify_alerts(emails, llm_query, batch_size=20)`**
- Batch classify alerts into P1-P5
- Returns: `{"P1": [...], "P2": [...], "P3": [...], "P4": [...], "P5": [...]}`

**`extract_iocs(emails)`**
- Extract indicators of compromise
- Returns: `{"ips": [...], "domains": [...], "file_hashes": {...}, "urls": [...]}`

**`extract_severity(alert)`**
- Normalize severity from security tools
- Returns: "P1" | "P2" | "P3" | "P4" | "P5"

**`map_to_mitre(alert, llm_query=None)`**
- Map alert to MITRE ATT&CK techniques
- Returns: List of technique IDs (e.g., ["T1566.001", "T1059"])

**`correlate_by_source_ip(emails, llm_query)`**
- Group and analyze alerts by source IP
- Returns: Dict mapping IPs to analysis

**`detect_suspicious_senders(emails, llm_query)`**
- Identify phishing, spoofing, domain squatting
- Returns: List of suspicious sender detections

**`analyze_attachments(emails)`**
- Risk scoring for attachments
- Returns: List of risky attachments

**`extract_and_analyze_urls(emails)`**
- Identify suspicious URLs
- Returns: List of suspicious URLs

**`deduplicate_security_alerts(emails, similarity_threshold=0.9)`**
- Remove duplicate alerts
- Returns: Deduplicated list

## Example Orchestration Scenarios

### Scenario 1: Inbox Triage

**User Request:** "Triage my inbox"

**Agent Actions:**
1. Interpret: User wants emails categorized by urgency
2. Select: `inbox_triage(emails)` workflow
3. Construct code:
```python
result = inbox_triage(emails)
summary = f"""
Inbox Triage Results:
- Urgent: {len(result['urgent'])} emails
- Action Required: {len(result['action_required'])} emails
- FYI: {len(result['fyi'])} emails
- Newsletters: {len(result['newsletter'])} emails
"""
FINAL(summary)
```
4. Estimate: ~100 emails × $0.002 = $0.20
5. Execute:
```bash
.venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py \
  --query "is:inbox newer_than:7d" \
  --max-results 100 \
  --max-budget 1.00 \
  --code "result = inbox_triage(emails); FINAL(str(len(result['urgent'])) + ' urgent emails')"
```
6. Present results naturally
7. Prepare for follow-up: "Show me urgent emails", "What are the action items?"

### Scenario 2: Security Alert Triage

**User Request:** "Triage security alerts from last week"

**Agent Actions:**
1. Interpret: Security-specific triage with P1-P5 classification
2. Select: `security_triage(emails)` workflow
3. Construct code:
```python
result = security_triage(emails)
print(f"P1: {len(result['classifications']['P1'])}")
print(f"P2: {len(result['classifications']['P2'])}")
print(f"Kill Chains: {len(result['kill_chains'])}")
FINAL(result['executive_summary'])
```
4. Estimate: ~500 emails × $0.004 = $2.00 (warn user, ask confirmation)
5. Execute:
```bash
.venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py \
  --query "label:security-alerts newer_than:7d" \
  --max-results 500 \
  --max-budget 2.00 \
  --code "result = security_triage(emails); FINAL(result['executive_summary'])"
```
6. Present executive summary + key stats
7. Prepare for follow-up: "Show P1 details", "What IOCs were found?", "Explain the kill chains"

### Scenario 3: Custom Analysis

**User Request:** "Find emails from top 5 senders and summarize what each is emailing about"

**Agent Actions:**
1. Interpret: Sender analysis with custom summarization
2. Select: Compose `chunk_by_sender()` + `parallel_map()`
3. Construct code:
```python
by_sender = chunk_by_sender(emails)
top_senders = sorted(by_sender.items(), key=lambda x: -len(x[1]))[:5]

summaries = []
for sender, msgs in top_senders:
    summary = llm_query(
        f'What is {sender} emailing about? Summarize in 2-3 sentences.',
        context=str([m['snippet'] for m in msgs[:10]])
    )
    summaries.append(f"**{sender}** ({len(msgs)} emails): {summary}")

FINAL('\n\n'.join(summaries))
```
4. Estimate: ~200 emails, 5 LLM calls = ~$0.15
5. Execute with constructed code
6. Present formatted summaries

### Scenario 4: Attack Chain Detection

**User Request:** "Find attack chains in security alerts from today"

**Agent Actions:**
1. Interpret: Time-based correlation for kill chains
2. Select: `detect_attack_chains(emails, window_minutes=5)`
3. Construct code:
```python
chains = detect_attack_chains(emails, window_minutes=5)
critical = [c for c in chains if c['severity'] in ['P1', 'P2']]

if critical:
    output = '## Critical Attack Chains Detected\n\n'
    for chain in critical:
        output += f"**{chain['attack_id']}** ({chain['severity']})\n"
        output += f"Pattern: {chain['pattern']}\n"
        output += f"MITRE: {', '.join(chain['mitre_techniques'])}\n"
        output += f"Confidence: {chain['confidence']:.0%}\n\n"
    FINAL(output)
else:
    FINAL('No critical attack chains detected.')
```
4. Estimate: ~200 emails × $0.005 = $1.00
5. Execute
6. Present attack chain details with actionable information

## Error Handling

### Common Errors

**1. ANTHROPIC_API_KEY not set**
```json
{"status": "error", "error_type": "EnvironmentError", "message": "ANTHROPIC_API_KEY not set"}
```
**Solution:** Inform user to set environment variable:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

**2. Gmail credentials invalid**
```json
{"status": "error", "error_type": "AuthenticationError", "message": "No valid credentials"}
```
**Solution:** User needs to re-authenticate:
```bash
.venv/bin/python skills/gmail/scripts/gmail_auth.py
```

**3. Budget exhausted mid-analysis**
```json
{"status": "error", "error_type": "BudgetExceededError", "message": "Budget limit reached"}
```
**Solution:** Partial results may be available. Ask user to increase budget or reduce scope.

**4. Subprocess failure**
```json
{"status": "error", "error_type": "ExecutionError", "message": "..."}
```
**Solution:** Parse error message, suggest remediation. Common causes: syntax error in code, invalid query, timeout.

### Error Recovery

1. **Catch and parse** error JSON from subprocess
2. **Explain** error to user in plain language
3. **Suggest** remediation steps
4. **Preserve** partial results if available
5. **Offer** to retry with adjusted parameters

## Best Practices

### 1. Start Simple
- Use pre-built workflows when possible
- Only compose custom logic for truly unique requests

### 2. Optimize for Cost
- Estimate before executing
- Use Haiku model for simple classification tasks
- Batch operations when possible
- Cache results for follow-up questions

### 3. Provide Context
- Show cost estimates before expensive operations
- Display session stats (tokens, cost, calls) after execution
- Explain what the RLM code is doing if user asks for `--debug`

### 4. Multi-Turn Flow
- Keep RLM results in memory for follow-up
- Avoid re-executing expensive operations
- Accumulate budget tracking across conversation

### 5. User Experience
- Present results in readable format (markdown, tables, lists)
- Highlight actionable insights (P1 alerts, urgent emails, deadlines)
- Offer natural follow-ups based on results
- Be transparent about limitations (budget, scope, accuracy)

## Advanced Patterns

### Parallel Processing for Speed

Use `parallel_map()` for 3-5x speedup on large datasets:

```python
# Sequential (slow)
summaries = []
for chunk in chunks:
    summaries.append(llm_query("Summarize", context=str(chunk)))

# Parallel (fast)
summaries = parallel_map("Summarize these emails", chunks, context_fn=str, max_workers=5)
```

### Progressive Disclosure

For large result sets, show summary first, then details on request:

```python
# Turn 1: High-level summary
result = security_triage(emails)
FINAL(result['executive_summary'])

# Turn 2: User asks "Show P1 details"
# Access cached result['classifications']['P1']
```

### Adaptive Parameters

Adjust parameters based on email volume:

```python
email_count = len(emails)

# Dynamic chunk size
chunk_size = min(40, max(10, email_count // 10))

# Dynamic workers
max_workers = 8 if email_count > 500 else 5

# Dynamic model
model = 'claude-haiku-4-20250514' if email_count > 300 else 'claude-sonnet-4-20250514'
```

## Testing & Validation

After orchestrating RLM execution:

1. **Verify JSON output** from subprocess (check `status: "success"`)
2. **Parse result field** for actual data
3. **Check session stats** for reasonableness (cost, token usage)
4. **Validate result structure** matches expected format
5. **Present** results in user-friendly format

## Summary

This guide provides everything Claude Code's Agent needs to:
- ✅ Interpret natural language goals
- ✅ Select appropriate RLM functions
- ✅ Construct and execute RLM code via subprocess
- ✅ Manage budget and optimization
- ✅ Handle multi-turn dialogue
- ✅ Present results naturally
- ✅ Handle errors gracefully

**Key Principle:** The Agent acts as an intelligent orchestrator, not a simple command executor. It understands context, optimizes parameters, estimates costs, and provides a natural conversational interface to powerful RLM email analysis capabilities.
