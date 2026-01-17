#!/usr/bin/env python3
"""
Gmail Mark as Read Script

Marks emails matching a query as read by removing the UNREAD label.

Usage:
    python gmail_mark_read.py --query "is:unread before:2024/03/01" --max-results 500 --batch-size 100
"""

import argparse
import sys
import json

from googleapiclient.errors import HttpError

# Import common utilities
from gmail_common import (
    get_gmail_service,
    format_error,
    format_success,
    log_verbose
)

# OAuth scope required for modifying message labels
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


def mark_as_read(
    query: str,
    max_results: int = 500,
    batch_size: int = 100,
    verbose: bool = False
) -> dict:
    """
    Mark emails matching query as read.

    Args:
        query: Gmail search query (e.g., "is:unread before:2024/03/01")
        max_results: Maximum number of messages to process
        batch_size: Number of messages to process per batch
        verbose: Whether to log detailed progress

    Returns:
        Dictionary with operation result
    """
    log_verbose(f"Searching for: {query}", verbose)
    log_verbose(f"Max results: {max_results}", verbose)

    service = get_gmail_service(SCOPES)

    try:
        # Collect all message IDs matching the query
        all_message_ids = []
        page_token = None

        while len(all_message_ids) < max_results:
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=min(100, max_results - len(all_message_ids)),
                pageToken=page_token
            ).execute()

            messages = results.get('messages', [])
            if not messages:
                break

            all_message_ids.extend([m['id'] for m in messages])
            log_verbose(f"Found {len(all_message_ids)} messages so far...", verbose)

            page_token = results.get('nextPageToken')
            if not page_token:
                break

        if not all_message_ids:
            return {
                "action": "mark_as_read",
                "query": query,
                "affected_messages": 0,
                "message": "No messages found matching query"
            }

        log_verbose(f"Total messages to process: {len(all_message_ids)}", verbose)

        # Process in batches using batchModify
        total_processed = 0

        for i in range(0, len(all_message_ids), batch_size):
            batch = all_message_ids[i:i + batch_size]
            log_verbose(f"Processing batch {i // batch_size + 1}: {len(batch)} messages", verbose)

            # Use batchModify for efficiency
            service.users().messages().batchModify(
                userId='me',
                body={
                    'ids': batch,
                    'removeLabelIds': ['UNREAD']
                }
            ).execute()

            total_processed += len(batch)
            print(f"[Progress] Marked {total_processed}/{len(all_message_ids)} messages as read", file=sys.stderr)

        return {
            "action": "mark_as_read",
            "query": query,
            "affected_messages": total_processed
        }

    except HttpError as error:
        error_details = error.error_details if hasattr(error, 'error_details') else []
        raise Exception(
            f"Gmail API error: {error.reason}\n"
            f"Status code: {error.status_code}\n"
            f"Details: {error_details}"
        )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Mark Gmail messages as read",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Mark old unread emails as read
  python gmail_mark_read.py --query "is:unread before:2024/03/01" --max-results 500

  # Mark all unread emails from a sender as read
  python gmail_mark_read.py --query "is:unread from:newsletter@example.com" --max-results 100
        """
    )

    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Gmail search query (e.g., 'is:unread before:2024/03/01')"
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=500,
        help="Maximum number of messages to process (default: 500)"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of messages to process per batch (default: 100)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging to stderr"
    )

    args = parser.parse_args()

    try:
        result = mark_as_read(
            query=args.query,
            max_results=args.max_results,
            batch_size=args.batch_size,
            verbose=args.verbose
        )
        print(format_success(result))
        sys.exit(0)

    except FileNotFoundError as e:
        print(format_error("MissingCredentials", str(e)), file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(format_error("MarkReadError", str(e)), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
