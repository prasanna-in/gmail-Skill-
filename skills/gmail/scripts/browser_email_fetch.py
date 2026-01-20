#!/usr/bin/env python3
"""
Browser-based email fetcher for corporate webmail.

Uses agent-browser to extract emails from Gmail, Outlook 365, Exchange, or any
webmail that blocks API access. Outputs Gmail API-compatible JSON for use with
gmail_rlm_repl.py.

Usage:
    # Corporate Gmail
    python browser_email_fetch.py \
        --url "https://mail.google.com/mail/u/0" \
        --folder "Inbox" \
        --max-results 10 \
        --output emails.json

    # Outlook 365
    python browser_email_fetch.py \
        --url "https://outlook.office365.com" \
        --folder "Inbox" \
        --max-results 10 \
        --output emails.json
"""

import argparse
import json
import subprocess
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Optional


def check_agent_browser_installed() -> bool:
    """Check if agent-browser is installed and accessible."""
    try:
        result = subprocess.run(
            ["agent-browser", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def generate_email_id(index: int, url: str) -> str:
    """
    Generate unique email ID for browser-fetched emails.

    Format: browser_email_{provider}_{index}
    """
    if "gmail.com" in url:
        provider = "gmail"
    elif "outlook.office365.com" in url:
        provider = "o365"
    elif "outlook.office.com" in url or "outlook.com" in url:
        provider = "exchange"
    else:
        provider = "webmail"

    return f"browser_email_{provider}_{index:06d}"


def generate_thread_id(index: int, subject: str) -> str:
    """
    Generate thread ID based on subject.

    In POC, we use a simple hash of the subject. In production,
    this would use email References headers for true threading.
    """
    subject_hash = hash(subject.lower().strip()) & 0x7FFFFFFF
    return f"browser_thread_{subject_hash:08x}"


def normalize_date(date_str: str) -> str:
    """
    Normalize date string to Gmail API format.

    Gmail API format: "Mon, 20 Jan 2025 10:30:00 -0800"

    This is a simple implementation. In production, would handle
    various date formats from different webmail providers.
    """
    # If already in RFC 2822 format, return as-is
    if re.match(r'\w+, \d+ \w+ \d{4} \d{2}:\d{2}:\d{2}', date_str):
        return date_str

    # Try to parse and reformat
    try:
        # Handle common formats
        for fmt in [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%m/%d/%Y %H:%M",
            "%d/%m/%Y %H:%M",
        ]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
            except ValueError:
                continue

        # If no format matches, return as-is
        return date_str
    except Exception:
        return date_str


def extract_emails_via_browser(url: str, folder: str, max_results: int, session_name: str = "gmail_corporate", use_mock: bool = False) -> list[dict]:
    """
    Use agent-browser to navigate webmail and extract emails.

    Args:
        url: Webmail URL (e.g., https://mail.google.com/mail/u/0)
        folder: Folder name (currently only Inbox supported for Gmail)
        max_results: Maximum emails to extract
        session_name: Agent-browser session name (persists login)
        use_mock: If True, return mock data instead of real extraction

    Returns:
        List of email dicts with keys: subject, from, to, date, body
    """
    # Check provider
    if "mail.google.com" not in url and not use_mock:
        raise ValueError(
            f"Real browser extraction currently only supports Gmail.\n"
            f"URL provided: {url}\n"
            f"Use --mock flag for POC mock data, or provide a Gmail URL (mail.google.com)."
        )

    if use_mock:
        # Mock data for POC/testing
        return _generate_mock_emails(url, folder, max_results)

    # Real Gmail extraction
    print(f"Initializing real browser extraction for Gmail...")
    print(f"URL: {url}")
    print(f"Folder: {folder}")
    print(f"Max results: {max_results}")
    print()

    try:
        # Import the real extractor
        from browser_gmail_extractor import GmailBrowserExtractor

        # Create extractor with persistent session
        extractor = GmailBrowserExtractor(
            session_name=session_name,
            headless=False  # Show browser for manual login
        )

        # Open Gmail (will prompt for manual login if needed)
        extractor.open_gmail(url)

        # Extract emails
        emails = extractor.extract_emails(max_results=max_results)

        return emails

    except ImportError as e:
        raise RuntimeError(
            f"Failed to import Gmail extractor: {e}\n"
            f"Ensure browser_gmail_extractor.py is in the same directory."
        )
    except Exception as e:
        raise RuntimeError(f"Browser extraction failed: {e}")


def _generate_mock_emails(url: str, folder: str, max_results: int) -> list[dict]:
    """
    Generate mock emails for POC/testing.

    This is used when --mock flag is set, or when testing the data pipeline
    without actual browser automation.
    """
    # Determine provider-specific mock data
    if "gmail.com" in url:
        provider_name = "Corporate Gmail"
        from_domain = "company.com"
    elif "outlook.office365.com" in url:
        provider_name = "Outlook 365"
        from_domain = "company.com"
    elif "outlook.office.com" in url or "outlook.com" in url:
        provider_name = "Exchange Online"
        from_domain = "company.com"
    else:
        provider_name = "Webmail"
        from_domain = "example.com"

    # Generate sample emails for POC
    mock_emails = []
    for i in range(min(max_results, 5)):  # Limit to 5 for POC
        email = {
            "subject": f"Sample Email {i+1} from {provider_name}",
            "from": f"Sender{i+1} <sender{i+1}@{from_domain}>",
            "to": "user@company.com",
            "date": datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "body": f"This is a sample email body extracted from {provider_name} via agent-browser.\n\nEmail #{i+1} in {folder} folder.\n\nThis demonstrates the browser-based email extraction for corporate webmail that blocks API access."
        }
        mock_emails.append(email)

    return mock_emails


def normalize_to_gmail_schema(browser_emails: list[dict], url: str) -> list[dict]:
    """
    Transform browser-extracted emails to Gmail API schema.

    Browser format (input):
    {
        "subject": "...",
        "from": "...",
        "to": "...",
        "date": "...",
        "body": "..."
    }

    Gmail API format (output):
    {
        "id": "browser_email_001",
        "threadId": "browser_thread_001",
        "subject": "...",
        "from": "...",
        "to": "...",
        "date": "...",
        "snippet": "first 200 chars of body",
        "body": "..."
    }
    """
    normalized = []

    for idx, email in enumerate(browser_emails):
        email_id = generate_email_id(idx + 1, url)
        thread_id = generate_thread_id(idx + 1, email.get("subject", ""))

        # Extract snippet (first 200 chars of body)
        body = email.get("body", "")
        snippet = body[:200] + "..." if len(body) > 200 else body

        normalized_email = {
            "id": email_id,
            "threadId": thread_id,
            "subject": email.get("subject", "(No subject)"),
            "from": email.get("from", "(Unknown sender)"),
            "to": email.get("to", ""),
            "date": normalize_date(email.get("date", "")),
            "snippet": snippet,
            "body": body
        }

        normalized.append(normalized_email)

    return normalized


def fetch_via_browser(url: str, folder: str, max_results: int, session_name: str = "gmail_corporate", use_mock: bool = False) -> dict:
    """
    Main fetch function: orchestrate browser extraction and normalization.

    Args:
        url: Webmail URL
        folder: Folder name
        max_results: Max emails to fetch
        session_name: Browser session name (persists login)
        use_mock: If True, use mock data instead of real browser

    Returns:
        Dictionary with status, messages, and metadata (Gmail API format)
    """
    # Check if agent-browser is installed when using real extraction
    if not use_mock and not check_agent_browser_installed():
        print(
            "ERROR: agent-browser not found. Install with: npm install -g agent-browser",
            file=sys.stderr
        )
        print("Or use --mock flag for POC demonstration with mock data.", file=sys.stderr)
        raise RuntimeError("agent-browser not installed")

    # Extract emails via browser (real or mock)
    browser_emails = extract_emails_via_browser(
        url, folder, max_results, session_name, use_mock
    )

    # Normalize to Gmail schema
    normalized_emails = normalize_to_gmail_schema(browser_emails, url)

    # Build response in Gmail API format
    response = {
        "status": "success",
        "messages": normalized_emails,
        "result_count": len(normalized_emails),
        "metadata": {
            "source": "browser_mock" if use_mock else "browser_real",
            "webmail_url": url,
            "folder": folder,
            "format": "full",
            "timestamp": datetime.now().isoformat(),
            "session": session_name if not use_mock else "mock"
        }
    }

    return response


def main():
    """CLI entry point for browser email fetcher."""
    parser = argparse.ArgumentParser(
        description="Browser-based email fetcher for corporate webmail",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Real Gmail extraction (requires manual login first time)
  python browser_email_fetch.py \\
    --url "https://mail.google.com/mail/u/0" \\
    --max-results 10 \\
    --output emails.json

  # Use custom session name
  python browser_email_fetch.py \\
    --url "https://mail.google.com/mail/u/0" \\
    --max-results 20 \\
    --session my_work_gmail \\
    --output emails.json

  # POC mode with mock data (for testing pipeline)
  python browser_email_fetch.py \\
    --url "https://outlook.office365.com" \\
    --max-results 10 \\
    --mock \\
    --output emails.json

Supported Webmail Providers:
  - Corporate Gmail (REAL EXTRACTION - fully implemented)
  - Outlook 365 (MOCK DATA - planned for future)
  - Exchange Online (MOCK DATA - planned for future)

Prerequisites:
  1. Install agent-browser: npm install -g agent-browser
  2. Run this script - it will open a browser for manual login on first use
  3. Login persists in session for future runs

How It Works:
  - First run: Browser window opens, you login manually (MFA/SSO supported)
  - Subsequent runs: Session persists, no re-login needed
  - Script extracts emails using browser automation
  - Output in Gmail API-compatible JSON format
        """
    )

    parser.add_argument(
        "--url",
        required=True,
        help="Webmail URL (e.g., https://mail.google.com/mail/u/0)"
    )

    parser.add_argument(
        "--folder",
        default="Inbox",
        help="Folder to read from (default: Inbox)"
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Maximum emails to fetch (default: 10, POC limit: 5)"
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON file path"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock data instead of real browser extraction (for POC/testing)"
    )

    parser.add_argument(
        "--session",
        default="gmail_corporate",
        help="Browser session name (persists login cookies, default: gmail_corporate)"
    )

    args = parser.parse_args()

    # Validate URL
    if not args.url.startswith("https://"):
        print(
            json.dumps({
                "status": "error",
                "error_type": "ValidationError",
                "message": "URL must start with https://"
            }),
            file=sys.stderr
        )
        sys.exit(1)

    try:
        if args.verbose:
            print(f"Fetching emails from: {args.url}", file=sys.stderr)
            print(f"Folder: {args.folder}", file=sys.stderr)
            print(f"Max results: {args.max_results}", file=sys.stderr)
            print(f"Mode: {'MOCK DATA' if args.mock else 'REAL BROWSER'}", file=sys.stderr)
            if not args.mock:
                print(f"Session: {args.session}", file=sys.stderr)

        # Fetch emails via browser
        result = fetch_via_browser(
            args.url,
            args.folder,
            args.max_results,
            args.session,
            args.mock
        )

        # Write to output file
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2))

        if args.verbose:
            print(f"\nSuccessfully fetched {result['result_count']} emails", file=sys.stderr)
            print(f"Output written to: {args.output}", file=sys.stderr)

        # Print success message to stdout (for chaining with other scripts)
        print(json.dumps({
            "status": "success",
            "count": result["result_count"],
            "output_file": args.output
        }))

        sys.exit(0)

    except Exception as e:
        error_response = {
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e)
        }
        print(json.dumps(error_response), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
