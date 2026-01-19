# Gmail Agent - Autonomous Email Analysis

The Gmail Agent provides a natural language interface to powerful email analysis capabilities. It converts your goals into sophisticated RLM (Recursive Language Model) operations, making complex email analysis accessible to everyone.

## Quick Start

```bash
# Install dependencies (one-time setup)
uv sync

# Set up authentication (one-time setup)
.venv/bin/python skills/gmail/scripts/gmail_auth.py

# Set your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Run the agent
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage my inbox"
```

## Operating Modes

### Agent Mode (Default)
**For:** Non-technical users, quick analyses, SOC analysts

Natural language goals are automatically converted to RLM function calls:

```bash
# Security workflows
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage security alerts from last week"
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Find attack chains in alerts"
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Analyze phishing attempts"

# General email workflows
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage my inbox"
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Summarize emails from top 5 senders"
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Find action items with deadlines"
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Summarize my week"
```

### Script Mode (Power Users)
**For:** Advanced users who want full control

Execute custom Python code directly:

```bash
.venv/bin/python skills/gmail/scripts/gmail_agent.py --script "
result = security_triage(emails)
print(f'P1: {len(result[\"classifications\"][\"P1\"])}')
FINAL(result['executive_summary'])
"
```

## Multi-Turn Dialogue

The agent supports interactive conversations:

```bash
$ .venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage security alerts"

Interpreting goal...
Optimizing parameters...
Estimated cost: $0.0245
Executing...

EXECUTIVE SUMMARY
──────────────────────────────────────────────────
Found 47 alerts. 5 P1 critical, 12 P2 high, 30 P3+.
Detected 2 potential kill chains requiring immediate investigation...

[Full triage results...]

Suggested follow-ups:
  1. Show me P1 alert details
  2. What's the confidence on the kill chains?
  3. Extract IOCs for threat intel

Session saved: ~/.gmail_agent_sessions/session_20250119_143022.json
Budget used: $0.0230 | Remaining: $0.9770

> Show me P1 details

[P1 alert details displayed...]

> What's the confidence on the kill chains?

[Kill chain confidence analysis...]

> done

Session ended. Use --resume to continue later.
```

## Session Management

### Resuming Sessions

Continue a previous conversation:

```bash
# Resume by session ID
.venv/bin/python skills/gmail/scripts/gmail_agent.py --resume session_20250119_143022

# List all sessions
.venv/bin/python skills/gmail/scripts/gmail_agent.py --list-sessions
```

Session files are stored in `~/.gmail_agent_sessions/` and include:
- Full conversation history
- Budget tracking
- Timestamps
- Metadata

### Budget Control

Protect against runaway costs:

```bash
# Default: $1.00 budget
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Analyze emails"

# Custom budget
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Analyze 1000 emails" --max-budget 5.00

# The agent will warn if estimated cost exceeds budget
```

## Available Workflows

### Security Workflows

#### 1. Security Alert Triage
Complete analysis of security alerts with P1-P5 classification, IOC extraction, and kill chain detection:

```bash
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage security alerts from last week"
```

**Output includes:**
- Executive summary
- P1-P5 classification with reasoning
- Detected kill chains
- Extracted IOCs (IPs, domains, hashes, URLs)
- Source IP correlation
- Suspicious sender analysis

#### 2. Attack Chain Detection
Identify multi-stage attacks within time windows:

```bash
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Find attack chains in alerts"
```

**Output includes:**
- Attack chain ID and pattern
- Confidence scores
- MITRE ATT&CK techniques
- Timeline of events
- Affected systems

#### 3. Phishing Analysis
Categorized phishing detection:

```bash
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Analyze phishing attempts"
```

**Output includes:**
- Credential harvesting attempts
- BEC (Business Email Compromise) attempts
- Brand impersonation
- Malicious attachments
- Malicious links

### General Email Workflows

#### 1. Inbox Triage
Categorize emails into actionable groups:

```bash
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage my inbox"
```

**Categories:**
- Urgent (requires immediate action)
- Action Required (needs response but not urgent)
- FYI (informational only)
- Newsletters (bulk/marketing)

#### 2. Sender Analysis
Analyze email patterns by sender:

```bash
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Summarize emails from top 5 senders"
```

#### 3. Action Item Extraction
Find tasks and deadlines:

```bash
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Find action items with deadlines"
```

**Output includes:**
- Task description
- Deadline (if specified)
- Priority level
- Sender
- Original email reference

#### 4. Weekly Summary
High-level overview of weekly emails:

```bash
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Summarize my week"
```

## Advanced Features

### Adaptive Optimization

The agent automatically optimizes parameters based on your dataset:

**Chunk Sizing:**
- < 50 emails: No chunking
- 50-200 emails: 25-email chunks
- 200-500 emails: 50-email chunks
- \> 500 emails: 100-email chunks

**Parallel Workers:**
- < 100 emails: 3 workers
- 100-500 emails: 5 workers
- \> 500 emails: 10 workers

**Budget Estimation:**
- Pre-execution cost estimate
- Warning if budget insufficient
- Suggest optimizations

### Cost Control

**Budget Warnings:**
```bash
$ .venv/bin/python skills/gmail/scripts/gmail_agent.py "Analyze 1000 emails"

⚠️  Estimated cost ($2.50) exceeds budget ($1.00).
    Consider reducing --max-results or increasing --max-budget.

This operation will use ~250% of your budget.
Continue? (y/n):
```

**Caching:**
- Query results cached for 24 hours
- Security patterns cached for 7 days
- IOC analyses cached indefinitely
- Significant cost savings on repeated queries

### Output Formats

#### Text (Default)
Human-readable formatted output:

```bash
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage alerts"
```

#### JSON
Machine-readable output for automation:

```bash
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage alerts" --format json
```

#### HTML
Shareable reports for management:

```bash
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage alerts" --format html > report.html
```

### Debug Mode

Show generated code for transparency:

```bash
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage alerts" --debug
```

**Output includes:**
- Goal interpretation reasoning
- Planned actions
- Generated Python code
- Execution details

## Query Customization

### Gmail Query Syntax

Use standard Gmail search operators:

```bash
# Time-based queries
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage alerts" --query "newer_than:7d"
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Analyze emails" --query "after:2025/01/01"

# Label-based queries
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage alerts" --query "label:security-alerts"

# Sender-based queries
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Summarize" --query "from:boss@company.com"

# Combined queries
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Analyze" --query "label:security-alerts newer_than:24h is:unread"
```

### Result Limits

Control the number of emails processed:

```bash
# Default: 100 emails
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage inbox"

# Custom limit
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Analyze all alerts" --max-results 500

# Large datasets (use with higher budget)
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Full analysis" --max-results 1000 --max-budget 5.00
```

## Model Selection

Choose the LLM model based on your needs:

```bash
# Default: Claude Sonnet 4 (balanced performance/cost)
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage alerts"

# Fast/cheap: Claude Haiku 4
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Quick summary" --model claude-haiku-4-20250514

# Maximum capability: Claude Opus 4 (expensive)
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Complex analysis" --model claude-opus-4-5-20251101
```

## Architecture

```
gmail_agent.py (CLI)
    ↓
agent_core.py (Main loop)
    ↓
    ├─→ goal_interpreter.py (NL → RLM functions)
    │
    ├─→ adaptive_optimizer.py (Parameter optimization)
    │
    ├─→ function_orchestrator.py (Execute RLM)
    │       ↓
    │   gmail_rlm_repl.py (RLM execution)
    │
    ├─→ result_formatter.py (Format output)
    │
    └─→ state_manager.py (Session persistence)
```

## Error Handling

### Automatic Retry

Failed LLM calls are retried automatically (3 attempts with exponential backoff):

```
Executing...
⚠️  Attempt 1 failed (API timeout). Retrying in 2s...
⚠️  Attempt 2 failed (API timeout). Retrying in 4s...
✓  Attempt 3 succeeded
```

### Budget Exhaustion

```
Budget exhausted. Use --max-budget to increase.
Session saved: ~/.gmail_agent_sessions/session_20250119_143022.json

# Resume later with higher budget
.venv/bin/python skills/gmail/scripts/gmail_agent.py --resume session_20250119_143022 --max-budget 2.00
```

### API Key Issues

```
Error: ANTHROPIC_API_KEY environment variable not set

Please set your Anthropic API key:
  export ANTHROPIC_API_KEY='sk-ant-...'

Or add it to your shell profile (~/.bashrc or ~/.zshrc):
  echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.zshrc
```

## Common Use Cases

### Daily SOC Workflow

```bash
# Morning triage
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage security alerts from last 24 hours" \
  --query "label:security-alerts newer_than:24h" \
  --max-budget 2.00

# Investigate P1 alerts
> Show me P1 alert details
> What IOCs were found?
> Map these to MITRE ATT&CK
> done
```

### Weekly Email Review

```bash
# Get weekly summary
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Summarize my week" \
  --query "newer_than:7d" \
  --max-results 500

# Extract action items
> Find action items with deadlines
> Show me urgent tasks
> done
```

### Incident Response

```bash
# Analyze suspicious emails
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Analyze phishing attempts from last 48 hours" \
  --query "newer_than:2d" \
  --max-budget 1.50

# Deep dive on findings
> Extract URLs from suspicious emails
> Analyze attachments
> Identify sender patterns
> done
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'anthropic'"

**Solution:** Ensure you're using the virtual environment Python:
```bash
.venv/bin/python skills/gmail/scripts/gmail_agent.py [args...]
```

### "Failed to interpret goal"

**Solution:** Make your goal more specific:
```bash
# Too vague
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Help me"

# Better
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Triage my inbox and find urgent emails"
```

### "Budget exhausted"

**Solution:** Increase budget or reduce dataset size:
```bash
# Option 1: Increase budget
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Analyze emails" --max-budget 5.00

# Option 2: Reduce dataset
.venv/bin/python skills/gmail/scripts/gmail_agent.py "Analyze emails" --max-results 50
```

## Comparison: Agent vs Script Mode

| Aspect | Agent Mode | Script Mode |
|--------|-----------|-------------|
| **Interface** | Natural language | Python code |
| **Target Users** | Non-technical, SOC analysts | Power users, developers |
| **Learning Curve** | Minutes | Requires Python knowledge |
| **Flexibility** | Pre-built workflows | Full customization |
| **Multi-turn** | ✅ Interactive dialogue | ❌ Single execution |
| **Error Recovery** | ✅ Automatic retry | ❌ Manual |
| **Cost** | +$0.01-0.05 for interpretation | Direct execution |
| **Speed** | Slightly slower (interpretation) | Fastest |

**When to use Agent Mode:**
- Quick analyses
- Non-technical users
- Interactive exploration
- Standard workflows

**When to use Script Mode:**
- Custom logic required
- Performance critical
- Automated pipelines
- Advanced power users

## Performance Tips

1. **Use specific queries** to reduce dataset size:
   ```bash
   --query "label:security-alerts newer_than:24h is:unread"
   ```

2. **Start with small datasets** for testing:
   ```bash
   --max-results 20
   ```

3. **Leverage caching** by re-running similar queries within 24 hours

4. **Use --non-interactive** for automated scripts:
   ```bash
   --non-interactive
   ```

5. **Choose the right model**:
   - Haiku: Fast, cheap, good for simple tasks
   - Sonnet: Balanced (default)
   - Opus: Most capable but expensive

## Examples

See `/Users/pk/work/gmail_skill/skills/gmail/examples/` for more query patterns and use cases.

## Support

- **Documentation:** See CLAUDE.md and SKILL.md
- **Issues:** Report at https://github.com/anthropics/claude-code/issues
- **RLM Functions:** See `gmail_rlm_helpers.py` for available functions
- **Security Workflows:** See `gmail_security_workflows.py` for pre-built analyses
