#!/usr/bin/env python3
"""
Gmail Bulk Read Script (RLM Mode)

This script extends gmail_read.py with pagination support for fetching large
numbers of emails (1000+). Designed for RLM (Recursive Language Model) workflows
that need to process emails in bulk.

Usage:
    python gmail_bulk_read.py --query "QUERY" [--max-results N] [--format metadata] [--output-file FILE]

Examples:
    # Fetch 500 emails from last month
    python gmail_bulk_read.py --query "newer_than:30d" --max-results 500

    # Save results to file for REPL loading
    python gmail_bulk_read.py --query "is:unread" --max-results 1000 --output-file /tmp/emails.json

    # Metadata only (faster, less data)
    python gmail_bulk_read.py --query "from:newsletter@" --max-results 200 --format metadata

Educational Note:
- Gmail API returns max 100 results per page with nextPageToken
- This script handles pagination automatically
- Progress is logged to stderr to keep stdout clean for JSON
- Use --output-file to save large results without overwhelming context
"""

import argparse
import json
import sys
from pathlib import Path

from googleapiclient.errors import HttpError

# Import common utilities
from gmail_common import (
    get_gmail_service,
    parse_message,
    format_error,
    format_success,
    log_verbose
)


# OAuth scopes required for reading emails
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Gmail API page size limit
PAGE_SIZE = 100


def bulk_search_messages(
    query: str,
    max_results: int = 500,
    format_type: str = "metadata",
    verbose: bool = False,
    progress_to_stderr: bool = True
) -> dict:
    """
    Search for Gmail messages with pagination support for large result sets.

    Args:
        query: Gmail search query (e.g., "is:unread from:user@example.com")
        max_results: Maximum number of messages to return (no hard limit)
        format_type: Level of detail - "minimal", "metadata", or "full"
        verbose: Whether to log detailed progress
        progress_to_stderr: Whether to log progress to stderr

    Returns:
        Dictionary with search results

    Raises:
        Exception: If API call fails
    """
    log_verbose(f"Bulk search for: {query}", verbose)
    log_verbose(f"Max results: {max_results}", verbose)
    log_verbose(f"Format: {format_type}", verbose)

    # Get authenticated Gmail service
    service = get_gmail_service(SCOPES)

    all_message_ids = []
    page_token = None
    page_num = 0

    try:
        # Phase 1: Collect all message IDs with pagination
        while len(all_message_ids) < max_results:
            page_num += 1
            remaining = max_results - len(all_message_ids)
            page_size = min(PAGE_SIZE, remaining)

            if progress_to_stderr:
                print(f"[Progress] Fetching page {page_num}... ({len(all_message_ids)} messages so far)", file=sys.stderr)

            # Build request with pagination
            request_params = {
                'userId': 'me',
                'q': query,
                'maxResults': page_size
            }
            if page_token:
                request_params['pageToken'] = page_token

            results = service.users().messages().list(**request_params).execute()

            messages = results.get('messages', [])
            if not messages:
                break

            all_message_ids.extend(messages)
            page_token = results.get('nextPageToken')

            if not page_token:
                # No more pages
                break

        total_found = len(all_message_ids)
        if progress_to_stderr:
            print(f"[Progress] Found {total_found} messages total", file=sys.stderr)

        if not all_message_ids:
            return {
                "result_count": 0,
                "query": query,
                "messages": [],
                "metadata": {
                    "pages_fetched": page_num,
                    "format": format_type
                }
            }

        # Phase 2: Fetch message details
        detailed_messages = []

        for i, msg in enumerate(all_message_ids):
            if progress_to_stderr and (i + 1) % 50 == 0:
                print(f"[Progress] Fetching details... {i + 1}/{total_found}", file=sys.stderr)

            # Determine API format based on requested format
            if format_type == "minimal":
                api_format = "minimal"
            elif format_type == "metadata":
                api_format = "metadata"
            else:  # full
                api_format = "full"

            # Fetch message details
            full_msg = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format=api_format
            ).execute()

            # Parse message into standardized format
            parsed = parse_message(full_msg, format_type)
            detailed_messages.append(parsed)

        if progress_to_stderr:
            print(f"[Progress] Bulk read completed: {total_found} messages", file=sys.stderr)

        return {
            "result_count": total_found,
            "query": query,
            "messages": detailed_messages,
            "metadata": {
                "pages_fetched": page_num,
                "format": format_type
            }
        }

    except HttpError as error:
        error_details = error.error_details if hasattr(error, 'error_details') else []
        raise Exception(
            f"Gmail API error: {error.reason}\n"
            f"Status code: {error.status_code}\n"
            f"Details: {error_details}"
        )


def main():
    """Main entry point for bulk read script."""
    parser = argparse.ArgumentParser(
        description="Bulk search and read Gmail messages with pagination (RLM Mode)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
RLM Mode Usage:
  This script is designed for Recursive Language Model workflows that need
  to process large numbers of emails. Use --output-file to save results
  to a file, then load in the RLM REPL environment.

Examples:
  # Fetch last month's emails for analysis
  python gmail_bulk_read.py --query "newer_than:30d" --max-results 500 --output-file /tmp/emails.json

  # Then in RLM REPL:
  python gmail_rlm_repl.py --load-file /tmp/emails.json --code "..."

Query Syntax:
  Same as gmail_read.py - see https://support.google.com/mail/answer/7190
        """
    )

    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Gmail search query (e.g., 'is:unread newer_than:30d')"
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=500,
        help="Maximum number of messages to return (default: 500, recommended max: 1000)"
    )

    parser.add_argument(
        "--format",
        type=str,
        choices=["minimal", "metadata", "full"],
        default="metadata",
        help="Output format: minimal (IDs only), metadata (headers), full (includes body)"
    )

    parser.add_argument(
        "--output-file",
        type=str,
        help="Save JSON output to file instead of stdout (recommended for large results)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging to stderr"
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress messages to stderr"
    )

    args = parser.parse_args()

    # Validate max-results
    if args.max_results < 1:
        print(format_error(
            "InvalidParameter",
            "max-results must be at least 1",
            provided=args.max_results
        ), file=sys.stderr)
        sys.exit(1)

    if args.max_results > 2000:
        print("[Warning] Fetching more than 2000 emails may be slow and hit rate limits", file=sys.stderr)

    # Execute search
    try:
        result = bulk_search_messages(
            query=args.query,
            max_results=args.max_results,
            format_type=args.format,
            verbose=args.verbose,
            progress_to_stderr=not args.quiet
        )

        output = format_success(result)

        # Write to file or stdout
        if args.output_file:
            output_path = Path(args.output_file)
            output_path.write_text(output)
            print(f"[Success] Saved {result['result_count']} messages to {args.output_file}", file=sys.stderr)
        else:
            print(output)

        sys.exit(0)

    except FileNotFoundError as e:
        print(format_error("MissingCredentials", str(e)), file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(format_error("BulkReadError", str(e)), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
