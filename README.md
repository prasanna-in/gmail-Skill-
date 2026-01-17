# Gmail Skill with Recursive Language Models support for Claude Code

A Claude Code skill that provides direct Gmail API integration for reading, searching, sending emails, and managing.

This Skill can make your Gmail behave a Datastore allowing you to querry it.

## Features

- **Read & Search Emails:** Powerful Gmail search syntax with flexible output formats
- **Send Emails:** Compose and send emails with attachments
- **Manage Labels:** Create labels and organize emails
- **RLM Mode:** Large-scale email analysis with recursive LLM sub-queries (1000+ emails)
- **Bulk Operations:** Process large email datasets with pagination
- **Direct API Integration:** No MCP server required - uses standalone Python scripts
- **OAuth2 Authentication:** Secure browser-based authentication flow
- **Auto Token Refresh:** Tokens refresh automatically, no manual intervention needed

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Google Cloud Setup](#google-cloud-setup)
4. [Authentication](#authentication)
5. [Usage with Claude Code](#usage-with-claude-code)
6. [Usage Examples](#usage-examples)
7. [RLM Mode](#rlm-mode)
8. [Project Structure](#project-structure)
9. [How It Works](#how-it-works)
10. [Troubleshooting](#troubleshooting)

## Prerequisites

- Python 3.12 or higher
- Google account (Gmail)
- Google Cloud Platform account (free tier is sufficient)
- pip or uv for package management

## Installation

1. **Clone or download this repository:**
   ```bash
   cd <project-dir>
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -e .
   ```

   Or with uv:
   ```bash
   uv pip install -e .
   ```

   This installs:
   - `google-api-python-client` - Gmail API client
   - `google-auth-httplib2` - HTTP transport for authentication
   - `google-auth-oauthlib` - OAuth2 flow implementation

## Google Cloud Setup

Before using the skill, you must create OAuth2 credentials in Google Cloud Console.

### Step-by-Step Setup

1. **Go to Google Cloud Console:**
   - Visit https://console.cloud.google.com
   - Sign in with your Google account

2. **Create a New Project:**
   - Click "Select a project" → "New Project"
   - Name it "Gmail Skill" (or your preferred name)
   - Click "Create"
   - Wait for project creation to complete

3. **Enable Gmail API:**
   - In your project dashboard, go to "APIs & Services" → "Library"
   - Search for "Gmail API"
   - Click on it, then click "Enable"

4. **Configure OAuth Consent Screen:**
   - Go to "APIs & Services" → "OAuth consent screen"
   - Select "External" user type (for personal Gmail)
   - Click "Create"
   - Fill in required fields:
     - App name: "Gmail Skill"
     - User support email: Your email
     - Developer contact: Your email
   - Click "Save and Continue"
   - Skip "Scopes" (click "Save and Continue")
   - Add yourself as a test user:
     - Click "Add Users"
     - Enter your Gmail address
     - Click "Save and Continue"
   - Review and click "Back to Dashboard"

5. **Create OAuth 2.0 Credentials:**
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: Select "Desktop app"
   - Name: "Gmail Skill Desktop Client"
   - Click "Create"
   - Click "Download JSON" to download credentials file
   - **Important:** Save this file as `credentials.json`

6. **Place Credentials File:**
   ```bash
   # Move downloaded credentials file to the credentials directory
   mv ~/Downloads/client_secret_*.json <project-dir>/credentials/credentials.json
   ```

   Or if it's already named credentials.json:
   ```bash
   mv ~/Downloads/credentials.json <project-dir>/credentials/credentials.json
   ```

## Authentication

After placing the credentials file, run the one-time authentication:

```bash
python <project-dir>/skills/gmail/scripts/gmail_auth.py
```

**What happens:**
1. Script opens your default web browser
2. Google OAuth consent screen appears
3. You may see "Google hasn't verified this app" warning:
   - Click "Advanced"
   - Click "Go to Gmail Skill (unsafe)" - this is safe because it's your own app
4. Grant the requested permissions
5. Browser shows "The authentication flow has completed"
6. Script saves token to `credentials/token.json`
7. Success message displays your authenticated email

**Output example:**
```json
{
  "status": "success",
  "message": "Authentication successful",
  "email": "your.email@gmail.com",
  "scopes": ["https://www.googleapis.com/auth/gmail.modify"],
  "token_file": "<project-dir>/credentials/token.json"
}
```

**Note:** This is a one-time setup. Tokens auto-refresh when they expire.

## Usage with Claude Code

Once authenticated, you can use this skill with Claude Code in two ways:

### Option 1: Via Plugin Directory Flag

```bash
# Start Claude Code with this plugin
cc --plugin-dir <project-dir>

# Then ask Claude:
# "Check my unread emails"
# "Send an email to john@example.com with subject 'Hello'"
# "Create a label called 'Important' and apply it to my boss's emails"
```

### Option 2: Install as Global Plugin (Future)

Copy to Claude Code plugins directory (when supported):
```bash
cp -r <project-dir> ~/.claude/plugins/gmail-skill
```

## Usage Examples

Once installed, Claude will auto-discover and use this skill when you mention Gmail operations.

### Reading Emails

**Simple queries:**
```
"Check my unread emails"
"What emails did I get today?"
"Show me emails from john@example.com"
```

**Advanced queries:**
```
"Find all unread emails from my boss with attachments"
"Show me invoices from last month that have PDFs attached"
"What important emails did I get in the last 3 days?"
```

### Sending Emails

**Simple sends:**
```
"Send an email to alice@example.com with subject 'Meeting' and say we'll meet at 2pm"
```

**With attachments:**
```
"Send the report.pdf to team@example.com with subject 'Q1 Report' and CC my manager"
```

### Managing Labels

**Creating labels:**
```
"Create a label called 'Urgent'"
"Make a Work/Projects label" (creates hierarchical label)
```

**Organizing emails:**
```
"Apply the 'Important' label to all unread emails from my boss"
"Label all emails about ProjectX with a ProjectX label"
```

## RLM Mode

RLM (Recursive Language Model) mode enables large-scale email analysis by combining bulk email fetching with parallel LLM sub-queries. Use this when working with 1000+ emails or when you need complex analysis that would be too large for a single context window.

### When to Use RLM Mode

- Analyzing large email datasets (100+ emails)
- Complex aggregation or categorization tasks
- When you need to break down analysis into smaller chunks
- Pattern detection across many emails

### RLM Scripts

```bash
# Bulk read - fetch large email datasets with pagination
.venv/bin/python skills/gmail/scripts/gmail_bulk_read.py --query "newer_than:30d" --max-results 500

# RLM REPL - Python environment with LLM sub-query capabilities
.venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py --query "newer_than:7d" --max-results 200 --code "
by_sender = chunk_by_sender(emails)
FINAL(str(len(by_sender)) + ' unique senders')
"
```

### RLM Built-in Functions

**LLM Query Functions:**
- `llm_query(prompt, context, model=None, json_output=False)` - Make recursive LLM call
- `parallel_llm_query(prompts, max_workers=5)` - Concurrent LLM calls
- `parallel_map(prompt, chunks, context_fn, max_workers=5)` - Apply prompt to chunks

**Chunking Functions:**
- `chunk_by_size(emails, size=50)` - Group by count
- `chunk_by_sender(emails)` - Group by sender
- `chunk_by_date(emails, days=1)` - Group by date
- `chunk_by_thread(emails)` - Group by thread

**Filtering Functions:**
- `filter_by_keyword(emails, pattern)` - Filter by keyword regex
- `filter_by_sender(emails, pattern)` - Filter by sender regex

**Output Functions:**
- `FINAL(result)` - Output final result
- `FINAL_VAR(var)` - Output variable as final result
- `get_session()` - Get session stats (token usage, call count)

### RLM Example

```bash
# Analyze emails by sender and summarize
.venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py \
  --query "newer_than:7d" \
  --max-results 500 \
  --code "
chunks = chunk_by_sender(emails)
summaries = parallel_map(
    'Summarize the key topics in these emails',
    list(chunks.values())[:10],
    lambda chunk: '\\n'.join([e['subject'] for e in chunk])
)
FINAL(summaries)
"
```

**Note:** RLM mode requires the `ANTHROPIC_API_KEY` environment variable to be set.

## Project Structure

```
gmail_skill/
├── .claude-plugin/
│   └── plugin.json                # Plugin metadata
├── credentials/
│   ├── .gitkeep
│   ├── credentials.json           # OAuth client credentials (user provides)
│   └── token.json                 # OAuth tokens (auto-generated)
├── skills/
│   └── gmail/
│       ├── SKILL.md               # Main skill definition (Claude loads this)
│       ├── scripts/
│       │   ├── __init__.py        # Package marker
│       │   ├── gmail_common.py    # Shared OAuth & utility functions
│       │   ├── gmail_auth.py      # OAuth2 setup script
│       │   ├── gmail_read.py      # Read/search emails script
│       │   ├── gmail_send.py      # Send emails script
│       │   ├── gmail_labels.py    # Label management script
│       │   ├── gmail_mark_read.py # Mark emails as read
│       │   ├── gmail_bulk_read.py # Pagination for 1000+ emails
│       │   ├── gmail_rlm_repl.py  # RLM Python REPL environment
│       │   └── gmail_rlm_helpers.py # RLM chunking/filtering helpers
│       ├── references/
│       │   ├── api-reference.md   # Gmail API technical details
│       │   └── troubleshooting.md # Common issues and solutions
│       └── examples/
│           └── search-examples.md # Gmail search query patterns
├── .gitignore
├── pyproject.toml
└── README.md (this file)
```

## How It Works

### Architecture

This skill uses a **standalone scripts** architecture:

1. **SKILL.md** teaches Claude:
   - When to use the skill (trigger phrases like "read my email")
   - How to call the Python scripts
   - How to parse JSON output
   - Common workflows and error handling

2. **Python Scripts** handle operations:
   - Each script is independent and focused on one operation
   - All scripts output standardized JSON
   - Shared authentication logic in `gmail_common.py`
   - Token refresh happens automatically

3. **OAuth2 Flow:**
   - User runs `gmail_auth.py` once for initial setup
   - Browser opens for Google OAuth consent
   - Tokens saved to `credentials/token.json`
   - Scripts auto-refresh tokens when expired
   - Re-auth only needed if tokens revoked

### Why Standalone Scripts vs MCP?

This project intentionally avoids MCP (Model Context Protocol) for the "last mile" connection to demonstrate:
- Direct API integration approach
- Skill architecture with supporting scripts
- OAuth2 implementation
- Token management
- Educational code structure

MCP servers provide similar functionality but abstract away these implementation details.

### Skills vs Slash Commands

This is implemented as a **Skill** (not a Slash Command):
- **Skills** are auto-discovered by Claude based on your request
- **Slash Commands** require explicit `/command` invocation

When you say "check my email", Claude automatically:
1. Matches your request to the skill's description
2. Loads SKILL.md for instructions
3. Executes appropriate Python script
4. Parses JSON output
5. Responds in natural language

## Troubleshooting

### Common Issues

**"No valid credentials found"**
- Solution: Run `python skills/gmail/scripts/gmail_auth.py`
- Ensure `credentials.json` exists in credentials/

**"Google hasn't verified this app"**
- This is normal for personal OAuth apps
- Click "Advanced" → "Go to Gmail Skill (unsafe)"
- It's safe because you created the app

**"Token refresh failed"**
- Solution: Re-authenticate with `python skills/gmail/scripts/gmail_auth.py`
- Tokens can expire if not used for extended periods

**"Insufficient permissions"**
- Solution: Re-auth with broader scopes: `python gmail_auth.py --scopes gmail.modify`

**"Module not found"**
- Solution: Install dependencies: `pip install -e .`

**Scripts not working**
- Verify Python version: `python --version` (should be 3.12+)
- Check credentials files exist: `ls credentials/`
- Try verbose mode: `python gmail_read.py --query "is:unread" --verbose`

### Detailed Troubleshooting

For comprehensive troubleshooting, see:
- [skills/gmail/references/troubleshooting.md](skills/gmail/references/troubleshooting.md)

## Future Enhancements

Ideas for extending this skill (marked as TODOs in code):

- [ ] Draft management (create, update, send drafts)
- [ ] Thread operations (reply to threads, forward)
- [ ] HTML email composition
- [ ] Batch operations (process 100+ emails efficiently)
- [ ] Email templates and signatures
- [ ] Scheduled sending
- [ ] Export emails to CSV/PDF
- [ ] Calendar integration (extract meeting invites)

## Contributing

Contributions are welcome! Feel free to:
- Report bugs and issues
- Add new features
- Improve error handling
- Extend documentation
- Submit pull requests

## Security Notes

- **Never commit credentials.json or token.json** - they're gitignored
- OAuth tokens have appropriate scopes (gmail.modify by default)
- Credentials stored locally in credentials/ directory
- All communication with Gmail API uses HTTPS
- No email content is logged or stored by the scripts

## License

MIT

## Questions?

For issues or questions:
1. Check [skills/gmail/references/troubleshooting.md](skills/gmail/references/troubleshooting.md)
2. Review inline code comments
3. Check Gmail API documentation

---

Version: 0.2.0
Last Updated: 2026-01-18
