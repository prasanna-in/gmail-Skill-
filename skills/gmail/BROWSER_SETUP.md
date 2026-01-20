# Browser-Based Gmail Extraction Setup Guide

This guide shows you how to use browser automation to extract emails from Gmail when API access is blocked (e.g., corporate Gmail with OAuth2 disabled).

## Overview

**What it does:**
- Opens Gmail in a browser
- Extracts emails without Gmail API
- Works with corporate SSO/MFA
- Session persists (login once, use many times)
- Outputs Gmail API-compatible JSON

**What you need:**
- Node.js + npm (for agent-browser)
- Gmail account with webmail access
- 2 minutes for initial setup

## Quick Start

### 1. Install agent-browser

```bash
npm install -g agent-browser
agent-browser install
```

### 2. Test with Real Gmail

```bash
# This will open Gmail in a browser for you to login
.venv/bin/python skills/gmail/scripts/browser_email_fetch.py \
  --url "https://mail.google.com/mail/u/0" \
  --max-results 10 \
  --session my_gmail \
  --output /tmp/my_emails.json \
  --verbose
```

**What happens:**
1. Browser opens at Gmail
2. If not logged in, you'll see the login page - login manually
3. Once logged in, the script extracts 10 emails from your inbox
4. Browser may stay open or close (depending on session state)
5. Emails saved to `/tmp/my_emails.json` in Gmail API format

### 3. Use with RLM Analysis

```bash
# Extract and analyze emails in one command
.venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py \
  --source browser \
  --webmail-url "https://mail.google.com/mail/u/0" \
  --browser-session my_gmail \
  --max-results 50 \
  --code "
result = inbox_triage(emails)
print(f'Urgent: {len(result[\"urgent\"])}')
print(f'Action required: {len(result[\"action_required\"])}')
FINAL('Inbox triaged successfully')
"
```

## How Sessions Work

**First run:** Browser opens, you login, session saved as `my_gmail`
**Second run:** Session `my_gmail` reused, no login needed
**30 days later:** Session may expire, you'll need to login again

**Multiple accounts:**
```bash
# Personal Gmail
--browser-session personal_gmail

# Work Gmail
--browser-session work_gmail
```

Each session maintains separate cookies/auth.

## Gmail-Specific Implementation

Currently, **only Gmail is fully implemented** for real browser extraction.

**Supported:**
- ✅ Gmail / Google Workspace (mail.google.com)
- ✅ Personal Gmail accounts
- ✅ Corporate Gmail with SSO/MFA
- ✅ Corporate Gmail with API disabled

**Mock data only:**
- ⚠️ Outlook 365 (use `--mock` flag)
- ⚠️ Exchange Online (use `--mock` flag)

To use mock data for testing:
```bash
.venv/bin/python skills/gmail/scripts/browser_email_fetch.py \
  --url "https://outlook.office365.com" \
  --max-results 10 \
  --mock \
  --output /tmp/mock_emails.json
```

## Extracted Data

**From inbox list (fast):**
- ✅ Subject
- ✅ Sender (from email address)
- ✅ Date
- ✅ Body snippet (preview from inbox)
- ⚠️ Full body (not extracted, use snippet)
- ❌ Recipients (to/cc) - not visible in list view

**Schema:**
```json
{
  "id": "browser_email_webmail_000001",
  "threadId": "browser_thread_abc123",
  "subject": "Your email subject",
  "from": "sender@example.com",
  "to": "",
  "date": "2026-01-20T03:24:47.812Z",
  "snippet": "First ~200 chars of email body...",
  "body": "Full snippet text (not full email body)"
}
```

**Note:** To get full email bodies, you'd need to click each email individually, which is much slower. Current implementation prioritizes speed by extracting from the inbox list.

## Troubleshooting

### "agent-browser not found"

```bash
npm install -g agent-browser
agent-browser install
```

### "Found 0 email rows"

- Gmail UI may have changed (selectors need update)
- Not logged in (browser closed before extraction)
- Inbox is actually empty

Check manually:
```bash
agent-browser --session my_gmail get title
# Should show: "Inbox (###) - your@email.com - Gmail"
```

### Dates showing same timestamp

Known issue - date extraction from inbox list needs improvement. The dates default to current timestamp when not properly extracted from Gmail's DOM.

### Session expired / need to login again

```bash
# Open browser manually to re-login
agent-browser --session my_gmail --headed open "https://mail.google.com"
# Login, then close browser
# Future commands will use the new session
```

### Want to see what's happening

Add `--verbose` flag:
```bash
.venv/bin/python skills/gmail/scripts/browser_email_fetch.py \
  --url "https://mail.google.com/mail/u/0" \
  --max-results 10 \
  --session my_gmail \
  --output /tmp/emails.json \
  --verbose
```

## Standalone Browser Extractor

For advanced use or debugging:

```bash
# Direct Gmail extraction (standalone script)
.venv/bin/python skills/gmail/scripts/browser_gmail_extractor.py \
  --max-results 10 \
  --session my_gmail \
  --headed  # Show browser window
```

This runs the core extraction logic directly without the wrapper script.

## Comparison: Browser vs API

| Feature | Gmail API | Browser Extraction |
|---------|-----------|-------------------|
| **Setup** | OAuth2 credentials, approval flow | One-time manual login |
| **Auth** | API tokens | Browser cookies |
| **MFA/SSO** | Complex (if supported) | Natural (login in browser) |
| **Speed** | ~100ms per email | ~30 sec for 500 emails |
| **Max emails** | 1000s (paginated) | 1,250 (25 pages) |
| **Corporate restrictions** | Often blocked | Usually works |
| **Maintenance** | Stable API | May break if Gmail UI changes |

**Use browser when:**
- Gmail API access blocked by IT
- Can't get OAuth2 credentials approved
- Corporate SSO/MFA blocking API
- Need quick setup without admin approval

**Use API when:**
- API access available
- Need high volume (1000+ emails)
- Speed is critical
- Want stable, supported interface

## Security Notes

- Sessions are stored in agent-browser's data directory
- Cookies/auth persisted locally
- No credentials stored by our scripts
- You control when browser opens
- Sessions expire per Gmail's normal timeout rules
- Use strong session names (not default) for production

## Next Steps

1. **Try the demo:**
   ```bash
   bash examples/browser_email_poc.sh
   ```

2. **Run real analysis:**
   ```bash
   .venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py \
     --source browser \
     --webmail-url "https://mail.google.com/mail/u/0" \
     --browser-session my_work_gmail \
     --max-results 100 \
     --code "result = security_triage(emails); FINAL(result['executive_summary'])"
   ```

3. **Integrate into workflows:**
   - See `SKILL.md` for agent orchestration patterns
   - See `RLM_AGENT_GUIDE.md` for complete RLM workflows
   - See `examples/agent-conversations.md` for usage examples

## Known Limitations

1. **Gmail only** - Outlook/Exchange support planned but not implemented
2. **No full body** - Only snippets from inbox list (full body requires clicking each email)
3. **Date extraction** - Currently shows current timestamp (needs DOM selector improvement)
4. **No "to" field** - Not visible in Gmail's inbox list view
5. **Speed** - Slower than API (but faster than manual review!)

## Contributing

To add support for other webmail providers (Outlook, Exchange, etc.):

1. Create a new extractor in `skills/gmail/scripts/browser_<provider>_extractor.py`
2. Update `browser_email_fetch.py` to detect and use the new extractor
3. Test with real accounts
4. Submit PR with examples and documentation
