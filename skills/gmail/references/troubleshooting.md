# Gmail Skill Troubleshooting Guide

This guide covers common issues and their solutions when using the Gmail skill.

## Table of Contents

1. [Authentication Issues](#authentication-issues)
2. [Permission Errors](#permission-errors)
3. [Search and Query Problems](#search-and-query-problems)
4. [Email Sending Issues](#email-sending-issues)
5. [Label Management Problems](#label-management-problems)
6. [API Rate Limiting](#api-rate-limiting)
7. [Installation and Setup Issues](#installation-and-setup-issues)

---

## Authentication Issues

### Error: "No valid credentials found"

**Symptom:**
```json
{
  "status": "error",
  "error_type": "MissingCredentials",
  "message": "No valid credentials found.\nPlease run: python .../gmail_auth.py"
}
```

**Cause:** You haven't completed the OAuth2 setup, or the `token.json` file is missing.

**Solution:**

1. Ensure `credentials.json` exists in the credentials directory:
   ```bash
   ls credentials/credentials.json
   ```

2. If missing, obtain credentials from Google Cloud Console:
   - Visit https://console.cloud.google.com
   - Create/select project
   - Enable Gmail API
   - Create OAuth 2.0 Client ID (Desktop app)
   - Download and save to `credentials/credentials.json`

3. Run authentication:
   ```bash
   python skills/gmail/scripts/gmail_auth.py
   ```

---

### Error: "Token refresh failed"

**Symptom:**
```json
{
  "status": "error",
  "error_type": "AuthenticationError",
  "message": "Token refresh failed: ..."
}
```

**Cause:** The refresh token has expired or been revoked.

**Solution:**

Re-authenticate to get a new token:

```bash
python skills/gmail/scripts/gmail_auth.py
```

This will:
- Delete old token
- Open browser for fresh OAuth consent
- Create new token with valid refresh token

**Prevention:** Don't manually edit `token.json`. Let the scripts manage it automatically.

---

### Error: OAuth consent screen shows "App not verified"

**Symptom:** During OAuth flow, Google shows a warning that the app isn't verified.

**Cause:** Your Google Cloud project hasn't gone through Google's verification process.

**Solution:**

For personal use, this is normal and safe to proceed:

1. Click "Advanced"
2. Click "Go to [your app name] (unsafe)"
3. Grant permissions

**Note:** This warning appears because you're using your own OAuth credentials. For production apps serving other users, you'd need to complete Google's verification process.

---

## Permission Errors

### Error: "Insufficient permissions"

**Symptom:**
```json
{
  "status": "error",
  "error_type": "APIError",
  "message": "Gmail API error: insufficientPermissions"
}
```

**Cause:** The OAuth token was created with insufficient scopes for the requested operation.

**Solution:**

Re-authenticate with broader scopes:

```bash
# For full Gmail access (read, send, modify, labels)
python gmail_auth.py --scopes gmail.modify

# Or specify exact scopes needed
python gmail_auth.py --scopes "gmail.readonly,gmail.send,gmail.labels"
```

**Scope Reference:**
- `gmail.readonly`: Read-only access to all emails
- `gmail.send`: Send emails only
- `gmail.modify`: Full access (read, send, modify, delete)
- `gmail.labels`: Create, read, update, delete labels
- `gmail.compose`: Create, read, update drafts

**Note:** You must re-run authentication when changing scopes. The new token will replace the old one.

---

### Error: "Access blocked: This app's request is invalid"

**Symptom:** OAuth consent screen shows this error.

**Cause:** OAuth client configuration issue in Google Cloud Console.

**Solution:**

1. Go to Google Cloud Console → APIs & Services → OAuth consent screen
2. Verify these settings:
   - User Type: Should be "External" for personal Gmail
   - Publishing status: Can be "Testing" for personal use
   - Test users: Add your Gmail address to test users list
3. Go to Credentials → OAuth 2.0 Client IDs
4. Verify Application type is "Desktop app" or "Web application"
5. Download fresh credentials.json
6. Replace old credentials file
7. Re-run authentication

---

## Search and Query Problems

### Error: "Invalid query"

**Symptom:**
```json
{
  "status": "error",
  "error_type": "SearchError",
  "message": "Gmail API error: invalidQuery"
}
```

**Cause:** The search query uses invalid syntax.

**Common Issues:**

1. **Wrong date format:**
   ```
   ❌ after:01/15/2026
   ✅ after:2026/01/15
   ```

2. **Invalid operators:**
   ```
   ❌ from = alice@example.com
   ✅ from:alice@example.com
   ```

3. **Mismatched quotes:**
   ```
   ❌ subject:"unmatched
   ✅ subject:"matched quotes"
   ```

**Solution:**

- Test queries in Gmail web interface first
- Reference [search-examples.md](../examples/search-examples.md)
- Use `--verbose` flag to see the exact query being sent

---

### No Results Found (Expected Messages)

**Symptom:** Query returns 0 results but you know matching emails exist.

**Possible Causes & Solutions:**

1. **Query too specific:**
   ```bash
   # Try broader query
   python gmail_read.py --query "from:example.com" --max-results 100
   ```

2. **Archived emails:**
   ```bash
   # Search all mail, not just inbox
   python gmail_read.py --query "your-query -in:trash -in:spam"
   ```

3. **Label filters:**
   ```bash
   # Remove label restrictions
   python gmail_read.py --query "from:sender" --max-results 50
   ```

4. **Date ranges:**
   ```bash
   # Expand date range
   python gmail_read.py --query "from:sender after:2025/01/01"
   ```

---

## Email Sending Issues

### Error: "Invalid email address"

**Symptom:**
```json
{
  "status": "error",
  "error_type": "ValidationError",
  "message": "Invalid email address: ..."
}
```

**Cause:** Email address doesn't match basic format validation.

**Solution:**

1. Check for typos in email addresses
2. Ensure proper format: `user@domain.com`
3. Remove extra spaces: `alice@example.com` not ` alice@example.com `
4. Use comma-separated lists for multiple recipients:
   ```bash
   --to "alice@example.com,bob@example.com"
   ```

---

### Error: "Attachment not found"

**Symptom:**
```json
{
  "status": "error",
  "error_type": "FileNotFound",
  "message": "Attachment not found: /path/to/file.pdf"
}
```

**Cause:** Specified file doesn't exist at the given path.

**Solution:**

1. Verify file exists:
   ```bash
   ls /path/to/file.pdf
   ```

2. Use absolute paths:
   ```bash
   --attach "/path/to/report.pdf"
   ```

3. Check file permissions:
   ```bash
   chmod 644 /path/to/file.pdf
   ```

---

### Error: "Message too large"

**Symptom:**
```json
{
  "status": "error",
  "error_type": "SendError",
  "message": "... messageTooLarge ..."
}
```

**Cause:** Total message size (body + attachments) exceeds Gmail's 25MB limit.

**Solution:**

1. Check attachment sizes:
   ```bash
   du -h file1.pdf file2.docx
   ```

2. Compress large files:
   ```bash
   zip report.zip large_file.pdf
   ```

3. Use Google Drive links instead of attachments for large files

4. Split into multiple emails

---

## Label Management Problems

### Error: "Label already exists"

**Symptom:**
```json
{
  "status": "error",
  "error_type": "LabelError",
  "message": "Label 'Work' already exists"
}
```

**Cause:** Attempting to create a label with a name that already exists.

**Solution:**

1. List existing labels first:
   ```bash
   python gmail_labels.py --action list
   ```

2. Use a different name, or use the existing label

3. For hierarchical labels, use full path:
   ```bash
   # Instead of "Projects", use:
   --name "Work/Projects"
   ```

---

### Error: "Label not found"

**Symptom:**
```json
{
  "status": "error",
  "error_type": "LabelError",
  "message": "Label not found: Important"
}
```

**Cause:** Trying to apply/remove a label that doesn't exist.

**Solution:**

1. List all labels:
   ```bash
   python gmail_labels.py --action list
   ```

2. Check exact spelling (labels are case-sensitive)

3. Create the label if it doesn't exist:
   ```bash
   python gmail_labels.py --action create --name "Important"
   ```

---

### Cannot Modify System Labels

**Symptom:** Error when trying to create label named "INBOX", "SENT", etc.

**Cause:** System labels cannot be created, deleted, or modified.

**Solution:**

System labels are built-in and managed by Gmail:
- INBOX
- SENT
- DRAFT
- SPAM
- TRASH
- UNREAD
- STARRED
- IMPORTANT

Create user labels with different names:
```bash
--name "My Inbox"  # ✅ Valid
--name "INBOX"     # ❌ Invalid (system label)
```

---

## API Rate Limiting

### Error: "Quota exceeded" or "Rate limit exceeded"

**Symptom:**
```json
{
  "status": "error",
  "error_type": "APIError",
  "message": "... quotaExceeded ... or ... rateLimitExceeded ..."
}
```

**Cause:** Too many API requests in short time period.

**Gmail API Quotas:**
- 250 quota units per user per second
- 1 billion quota units per day

**Operation Costs:**
- Read message: 5 units
- Send message: 100 units
- Modify labels: 5 units
- List messages: 5 units

**Solution:**

1. **Immediate:** Wait 1-2 minutes and retry

2. **Reduce request frequency:**
   - Use `--max-results` to limit search results
   - Batch operations when possible
   - Use `--format minimal` when full data isn't needed

3. **Optimize queries:**
   ```bash
   # ❌ Inefficient: Fetch all, filter client-side
   python gmail_read.py --query "" --max-results 100

   # ✅ Efficient: Filter server-side
   python gmail_read.py --query "from:sender after:2026/01/01" --max-results 10
   ```

4. **Monitor quota usage:**
   - Check Google Cloud Console → APIs & Services → Dashboard
   - View quota usage and limits

5. **Request quota increase:**
   - For production use, request quota increase in Google Cloud Console
   - Personal use typically doesn't need increase

---

## Installation and Setup Issues

### Error: "No module named 'google'"

**Symptom:**
```python
ModuleNotFoundError: No module named 'google'
```

**Cause:** Google API client libraries not installed.

**Solution:**

```bash
# Install dependencies
pip install -e .

# Or install individually
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

**Verify installation:**
```bash
python -c "import googleapiclient; print('✅ Google API client installed')"
```

---

### Error: "Permission denied" when running scripts

**Symptom:**
```bash
-bash: permission denied: ./gmail_read.py
```

**Cause:** Script doesn't have execute permissions.

**Solution:**

```bash
# Add execute permissions
chmod +x skills/gmail/scripts/*.py

# Or run with python explicitly
python skills/gmail/scripts/gmail_read.py
```

---

### Error: "credentials.json: Permission denied"

**Symptom:** Cannot read credentials file.

**Cause:** Incorrect file permissions.

**Solution:**

```bash
# Fix permissions
chmod 600 credentials/credentials.json
chmod 600 credentials/token.json

# Verify
ls -la credentials/
```

---

## Debugging Tips

### Enable Verbose Logging

All scripts support `--verbose` flag for detailed output:

```bash
python gmail_read.py --query "is:unread" --verbose
```

This logs to stderr:
- Authentication steps
- API calls being made
- Response parsing
- Error details

### Test with Minimal Query

Start with simple queries to isolate issues:

```bash
# Simplest query - should always work
python gmail_read.py --query "is:inbox" --max-results 1 --format minimal
```

If this works, gradually add complexity to find where it breaks.

### Check Google Cloud Console

1. Visit https://console.cloud.google.com
2. Select your project
3. Go to APIs & Services → Dashboard
4. Check:
   - Gmail API is enabled
   - Request counts (for quota issues)
   - Error rates

### Verify Credentials Files

```bash
# Check files exist
ls -la credentials/

# Should see:
# -rw-------  credentials.json
# -rw-------  token.json  (after auth)
# -rw-r--r--  .gitkeep
```

### Test OAuth Flow Manually

```bash
python skills/gmail/scripts/gmail_auth.py --verbose
```

This shows each step of authentication and will pinpoint setup issues.

---

## Getting Help

If you encounter an issue not covered here:

1. **Check error message carefully** - Most errors include actionable guidance

2. **Enable verbose logging** - Provides detailed context:
   ```bash
   python script.py --verbose
   ```

3. **Test in Gmail web interface** - Verify queries work there first

4. **Review Google documentation:**
   - Gmail API: https://developers.google.com/gmail/api
   - OAuth 2.0: https://developers.google.com/identity/protocols/oauth2
   - Search operators: https://support.google.com/mail/answer/7190

5. **Check Google Cloud Console** - Look for API errors and quota usage

6. **Re-authenticate** - Many issues resolve with fresh auth:
   ```bash
   python gmail_auth.py
   ```

---

## Common Solution Checklist

Before troubleshooting specific errors, verify these basics:

- [ ] Gmail API is enabled in Google Cloud Console
- [ ] credentials.json exists and is valid
- [ ] token.json exists (run gmail_auth.py if not)
- [ ] Python dependencies are installed
- [ ] Using Python 3.12 or higher
- [ ] File paths are absolute, not relative
- [ ] Credentials files have correct permissions (600)
- [ ] Not hitting rate limits (wait a minute and retry)
- [ ] Testing queries in Gmail web first

Most issues resolve by completing this checklist.
