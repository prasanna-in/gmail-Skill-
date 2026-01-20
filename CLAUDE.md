# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Gmail Skill is a Claude Code integration that provides direct Gmail API access for email operations. It supports three operating modes:

- **Normal Mode**: Single script calls for specific operations (max 100 emails)
- **RLM Mode**: Recursive Language Model processing for large-scale analysis (1000+ emails with parallel LLM sub-queries)
- **Agent Orchestration**: Claude Code's general-purpose Agent directly orchestrates RLM operations via comprehensive documentation (recommended for complex analysis)

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

# Security alert triage
.venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py --query "label:security-alerts newer_than:7d" --max-results 500 --max-budget 2.00 --code "
result = security_triage(emails)
print(f'P1 Critical: {len(result[\"classifications\"][\"P1\"])}')
print(f'Kill Chains: {len(result[\"kill_chains\"])}')
FINAL(result['executive_summary'])
"
```

### Browser-Based Email Access

For environments where API access is blocked (corporate Gmail, Outlook 365, Exchange):

**When to use:**
- Corporate Gmail with API disabled
- Google Workspace with OAuth2 restrictions
- Outlook 365 / Exchange Online
- Any webmail behind SSO/MFA

**One-time setup:**
```bash
# Install agent-browser
npm install -g agent-browser
agent-browser install

# Login once (browser opens - use YOUR webmail URL)
agent-browser open https://mail.google.com  # Corporate Gmail
# OR
agent-browser open https://outlook.office365.com  # Outlook 365

# Complete SSO/MFA in browser, click "Stay signed in"
```

**Examples:**

**Corporate Gmail:**
```bash
.venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py \
  --source browser \
  --webmail-url "https://mail.google.com/mail/u/0" \
  --webmail-folder "Inbox" \
  --max-results 100 \
  --code "
result = inbox_triage(emails)
FINAL(f'Urgent: {len(result[\"urgent\"])}, Action: {len(result[\"action_required\"])}')
"
```

**Outlook 365 Security Alerts:**
```bash
.venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py \
  --source browser \
  --webmail-url "https://outlook.office365.com" \
  --webmail-folder "Security Alerts" \
  --max-results 100 \
  --code "
result = security_triage(emails)
FINAL(result['executive_summary'])
"
```

**How it works:**
1. Browser session persists after initial login
2. `browser_email_fetch.py` uses agent-browser to navigate webmail
3. Emails extracted with 93% less context (snapshot refs vs DOM)
4. Data normalized to Gmail API schema
5. Same RLM functions work identically

### Development

```bash
# Format code
uv run black skills/gmail/scripts/

# Run tests
uv run pytest

# Syntax check
python3 -m py_compile skills/gmail/scripts/gmail_read.py
```

## How Claude Code Agent Orchestrates RLM

**NEW ARCHITECTURE:** Instead of calling a standalone agent subprocess (`gmail_agent.py`), Claude Code's general-purpose Agent now directly orchestrates RLM operations using comprehensive documentation.

### Architecture Change

**Old (Deprecated):**
```
User → Claude Code → gmail_agent.py subprocess
                        ↓
                     AgentCore (1,348 lines of Python)
                        ├─ GoalInterpreter
                        ├─ FunctionOrchestrator
                        │   ↓ calls gmail_rlm_repl.py
                        └─ ResultFormatter
```

**New (Current):**
```
User → Claude Code → General-Purpose Agent
                        ↓ reads documentation
                     SKILL.md + RLM_AGENT_GUIDE.md + examples
                        ↓ interprets goal
                        ↓ constructs RLM code
                     gmail_rlm_repl.py subprocess
                        ↓ returns JSON results
                     Agent formats naturally
```

### Benefits

1. **Code Reduction:** Eliminated 1,348 lines of standalone agent code
2. **Better Integration:** Leverages Claude Code's native multi-turn dialogue
3. **Maintainability:** New workflows added via documentation, not code
4. **Flexibility:** Agent can adapt approach based on context
5. **Cost Transparency:** Agent shows estimates and asks confirmation

### How It Works

When user requests complex email analysis (e.g., "Triage my inbox"):

1. **Agent reads SKILL.md** → Identifies trigger pattern for RLM orchestration
2. **Agent reads RLM_AGENT_GUIDE.md** → Learns orchestration workflow
3. **Agent interprets goal** → "Triage" maps to `inbox_triage(emails)` workflow
4. **Agent constructs code:**
   ```python
   result = inbox_triage(emails)
   FINAL(f'Found {len(result["urgent"])} urgent emails')
   ```
5. **Agent estimates cost** → ~100 emails × $0.002 = $0.20
6. **Agent executes subprocess:**
   ```bash
   .venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py \
     --query "is:inbox newer_than:7d" \
     --max-results 100 \
     --max-budget 1.00 \
     --code "result = inbox_triage(emails); FINAL(...)"
   ```
7. **Agent presents results** in natural markdown format
8. **Agent caches results** for follow-up questions without re-execution

### Example Orchestration

**User:** "Triage security alerts from last week"

**Agent internally:**
```
1. Interpret: Security-specific triage
2. Select: security_triage(emails) function
3. Scope: label:security-alerts newer_than:7d, ~500 emails
4. Estimate: $2.00 (high volume)
5. Confirm: "This will cost ~$2.00. Proceed?"
6. Execute: gmail_rlm_repl.py with security_triage code
7. Present: Executive summary + P1/P2 breakdown
8. Cache: Result stored for "Show me P1 details"
```

### Documentation for Agent

The Agent relies on these files to orchestrate RLM operations:

1. **SKILL.md** - When to activate, trigger patterns, workflow decision matrix
2. **RLM_AGENT_GUIDE.md** - Complete orchestration guide, cost tables, optimization patterns
3. **references/rlm-function-reference.md** - All 30+ RLM functions with signatures and examples
4. **examples/agent-conversations.md** - 10+ complete conversation examples

### Deprecated: gmail_agent.py

The standalone `gmail_agent.py` script and `agent/` module are **deprecated** and will be removed in a future version. They are kept temporarily for backward compatibility but should not be used for new integrations.

For users who still need the old interface, it remains functional but shows deprecation warnings.

## Architecture

```
skills/gmail/
├── SKILL.md              # Skill definition - Claude Code reads for usage instructions
├── RLM_AGENT_GUIDE.md    # Complete RLM orchestration guide for Claude Code Agent
├── agent/                # DEPRECATED - Standalone agent module (being removed)
│   └── *.py              # 1,348 lines replaced by documentation-driven approach
├── scripts/              # Python execution scripts
│   ├── gmail_common.py   # Shared: OAuth2, message parsing, validation
│   ├── gmail_auth.py     # One-time OAuth setup (browser flow)
│   ├── gmail_agent.py    # DEPRECATED - Shows deprecation warning
│   ├── gmail_read.py     # Search and retrieve emails (Normal Mode)
│   ├── gmail_send.py     # Compose and send emails (Normal Mode)
│   ├── gmail_labels.py   # Label management (Normal Mode)
│   ├── gmail_bulk_read.py        # Pagination for 1000+ emails
│   ├── gmail_rlm_repl.py         # RLM REPL - Core subprocess for email analysis
│   ├── gmail_rlm_helpers.py      # Chunking, filtering, pre-built workflows
│   ├── gmail_rlm_cache.py        # Query caching
│   ├── gmail_rlm_checkpoint.py   # Checkpoint/resume for long analyses
│   ├── gmail_security_helpers.py     # Security analysis functions
│   ├── gmail_security_workflows.py   # Security triage workflows
│   └── gmail_security_schemas.py     # JSON schemas for security data
├── references/           # Documentation
│   ├── rlm-function-reference.md # Complete catalog of 30+ RLM functions
│   ├── api-reference.md          # Gmail API details
│   └── troubleshooting.md        # Common issues and solutions
└── examples/             # Examples
    ├── agent-conversations.md    # 10+ complete conversation examples for Agent
    └── search-examples.md        # Gmail search query patterns
```

**Key Files for Claude Code Agent:**
- `SKILL.md` - When to activate RLM orchestration, trigger patterns
- `RLM_AGENT_GUIDE.md` - How to orchestrate: workflow, cost tables, patterns
- `references/rlm-function-reference.md` - All available RLM functions
- `examples/agent-conversations.md` - Example dialogues showing expected behavior


### Key Design Patterns

1. **All scripts return JSON** - Parse `status` field ("success" or "error")
2. **OAuth tokens auto-refresh** - After initial `gmail_auth.py`, tokens are managed automatically
3. **Scopes are minimal** - Each script requests only needed permissions (readonly, send, labels)
4. **RLM uses Anthropic SDK** - `llm_query()` calls Claude via Anthropic Python SDK (requires `ANTHROPIC_API_KEY`)

### RLM Built-in Functions

When writing `--code` for `gmail_rlm_repl.py`:

**Core RLM Functions:**
- `llm_query(prompt, context, model=None, json_output=False)` - Recursive LLM call via Anthropic SDK
- `parallel_llm_query(prompts, max_workers=5, model=None, json_output=False)` - Concurrent LLM calls
- `parallel_map(prompt, chunks, context_fn, max_workers=5, model=None, json_output=False)` - Apply prompt to chunks
- `get_session()` - Get session stats (token usage, call count)
- `chunk_by_size/sender/date/thread(emails)` - Grouping functions
- `filter_by_keyword/sender(emails, pattern)` - Filtering functions
- `FINAL(result)` / `FINAL_VAR(var)` - Output final result

**Security Functions:**
- `extract_severity(alert)` - Normalize severity from security tools (CrowdStrike, Splunk, etc.)
- `classify_alerts(emails, llm_query)` - Batch classify alerts into P1-P5
- `extract_iocs(emails)` - Extract IPs, domains, file hashes, URLs
- `map_to_mitre(alert, llm_query)` - Map alerts to MITRE ATT&CK techniques
- `chunk_by_time(emails, minutes)` - Group alerts into time windows
- `correlate_by_source_ip(emails, llm_query)` - Analyze alerts by source IP
- `detect_suspicious_senders(emails, llm_query)` - Identify phishing/spoofing
- `analyze_attachments(emails)` - Risk scoring for attachments
- `extract_and_analyze_urls(emails)` - Identify suspicious URLs
- `deduplicate_security_alerts(emails)` - Remove duplicate alerts

**CLI options:** `--model` selects LLM model (default: claude-sonnet-4-20250514), `--json-output` includes session stats in output.

### RLM Safety Controls

- `--max-budget USD` - Stop if cost exceeds budget (default: $5.00)
- `--max-calls N` - Stop after N LLM calls (default: 100)
- `--max-depth N` - Max recursion depth (default: 3)
- `--no-cache` - Disable query caching

### Pre-built Workflows

**General Email Workflows:**
```python
# Classify emails into categories
result = inbox_triage(emails)  # Returns {urgent:[], action_required:[], fyi:[], newsletter:[]}

# Generate executive summary
summary = weekly_summary(emails)

# Extract action items with deadlines
items = find_action_items(emails)  # Returns [{task, deadline, sender, priority}]
```

**Security Workflows:**
```python
# Complete security alert triage
result = security_triage(emails)
# Returns: {summary, classifications (P1-P5), iocs, kill_chains, source_ip_analysis,
#           suspicious_senders, risky_attachments, suspicious_urls, executive_summary}

# Detect multi-stage attack chains
chains = detect_attack_chains(emails, window_minutes=5)
# Returns: [{attack_id, start_time, pattern, mitre_techniques, severity, confidence, ...}]

# Phishing analysis
phishing_results = phishing_analysis(emails)
# Returns: {credential_harvesting[], bec_attempts[], brand_impersonation[],
#           malicious_attachments[], malicious_links[], summary}

# Prepare IOCs for threat intel enrichment
enriched = enrich_with_threat_intel(iocs)
# Returns: Structured IOC data for VirusTotal, AbuseIPDB, etc.
```

### Security Alert Analysis

The RLM environment includes specialized security analysis capabilities for SOC/security teams:

**Use Case:** Triage Gmail-delivered security alerts from tools like CrowdStrike, Splunk, Azure Sentinel, Palo Alto, etc.

**Key Capabilities:**
1. **Severity Classification** - Normalize P1-P5 across different security tools
2. **IOC Extraction** - Automatically extract IPs, domains, hashes, URLs
3. **Kill Chain Detection** - Time-based correlation to detect multi-stage attacks (5-min windows)
4. **MITRE ATT&CK Mapping** - Map alerts to technique IDs (T1566, T1059, etc.)
5. **Source IP Correlation** - Identify coordinated attacks from same IP
6. **Phishing Detection** - Analyze for credential harvesting, BEC, brand impersonation
7. **Threat Pattern Storage** - Cross-session tracking with 30-day retention

**Security-Specific Caching:**
- Security patterns cached separately with 7-day TTL (vs 24-hour general cache)
- IOC analyses cached (same malware hash = instant lookup)
- MITRE mappings cached (same technique pattern = reuse)
- Historical threat patterns stored for recurring attack detection

**Example: Daily Security Triage**
```bash
.venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py \
  --query "label:security-alerts newer_than:7d" \
  --max-results 500 \
  --max-budget 2.00 \
  --code "
result = security_triage(emails)

# Print statistics
print(f'Total: {result[\"summary\"][\"total_alerts\"]}')
print(f'P1: {len(result[\"classifications\"][\"P1\"])} | P2: {len(result[\"classifications\"][\"P2\"])}')
print(f'Kill Chains: {len(result[\"kill_chains\"])}')
print(f'IOCs: {len(result[\"iocs\"][\"ips\"])} IPs, {len(result[\"iocs\"][\"domains\"])} domains')

# Output executive summary for CISO
FINAL(result['executive_summary'])
"
```

**Example: Kill Chain Detection**
```bash
.venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py \
  --query "label:security-alerts newer_than:24h" \
  --max-results 200 \
  --code "
chains = detect_attack_chains(emails, window_minutes=5)
critical = [c for c in chains if c['severity'] in ['P1', 'P2']]

if critical:
    for chain in critical:
        print(f'{chain[\"attack_id\"]}: {chain[\"pattern\"]} ({chain[\"confidence\"]:.0%})')
        print(f'  MITRE: {chain[\"mitre_techniques\"]}')
    FINAL(f'{len(critical)} critical attack chains detected')
else:
    FINAL('No critical chains detected')
"
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
