#!/usr/bin/env python3
"""
Gmail RLM REPL Environment

This script creates a Python REPL environment for Recursive Language Model (RLM)
email analysis. It loads emails into variables and provides functions for
recursive LLM calls, chunking, and result aggregation.

Based on the RLM approach from arxiv 2512.24601v1:
1. Store data in REPL environment (emails as Python variables)
2. Write code to examine data (programmatic filtering/analysis)
3. Recursively call LLM via llm_query() function
4. Aggregate results via FINAL() function

Usage:
    # Query and process emails directly
    python gmail_rlm_repl.py --query "is:unread" --max-results 200 --code "CODE"

    # Load pre-fetched emails from file
    python gmail_rlm_repl.py --load-file /tmp/emails.json --code "CODE"

Built-in Variables:
    emails    - List of email dictionaries from query
    metadata  - Query metadata (count, query string, etc.)

Built-in Functions:
    llm_query(prompt, context=None)  - Recursive LLM call via Claude CLI
    chunk_by_size(emails, size)      - Split into batches
    chunk_by_sender(emails)          - Group by sender
    chunk_by_date(emails, period)    - Group by day/week/month
    filter_emails(emails, predicate) - Filter with custom function
    filter_by_keyword(emails, kw)    - Filter by keyword
    FINAL(result)                    - Output final answer (string)
    FINAL_VAR(var_name)              - Output variable as result

Example:
    python gmail_rlm_repl.py --query "newer_than:7d" --max-results 100 --code "
    by_sender = chunk_by_sender(emails)
    summaries = []
    for sender, msgs in list(by_sender.items())[:5]:
        summary = llm_query(
            f'Summarize emails from {sender}',
            context=str([m['snippet'] for m in msgs])
        )
        summaries.append(f'{sender}: {summary}')
    FINAL('\\n'.join(summaries))
    "
"""

import argparse
import json
import subprocess
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

# Import RLM helper functions
from gmail_rlm_helpers import (
    chunk_by_size,
    chunk_by_sender,
    chunk_by_sender_domain,
    chunk_by_date,
    chunk_by_thread,
    filter_emails,
    filter_by_keyword,
    filter_by_sender,
    sort_emails,
    get_top_senders,
    extract_email_summary,
    batch_extract_summaries,
    aggregate_results,
    deduplicate_emails
)


# OAuth scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Global to store final result
_final_result = None
_final_set = False


def llm_query(prompt: str, context: str = None, timeout: int = 120) -> str:
    """
    Invoke Claude recursively via CLI subprocess.

    This is the key RLM function - enables recursive LLM calls where each
    sub-query has fresh context, avoiding context rot from long conversations.

    Args:
        prompt: The task/question for the LLM
        context: Optional context data (e.g., email contents)
        timeout: Timeout in seconds (default: 120)

    Returns:
        LLM response string

    Example:
        summary = llm_query(
            'What action items are in these emails?',
            context=str([e['snippet'] for e in emails[:10]])
        )
    """
    # Build the full prompt
    if context:
        full_prompt = f"Context:\n{context}\n\nTask:\n{prompt}"
    else:
        full_prompt = prompt

    try:
        # Call Claude CLI in print mode (no interactive features)
        result = subprocess.run(
            ["claude", "--print", "-p", full_prompt],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            return f"[LLM Error: {error_msg}]"

        return result.stdout.strip()

    except subprocess.TimeoutExpired:
        return "[LLM Error: Query timed out]"
    except FileNotFoundError:
        return "[LLM Error: Claude CLI not found. Ensure 'claude' is in PATH]"
    except Exception as e:
        return f"[LLM Error: {str(e)}]"


def FINAL(result: str):
    """
    Set the final output result.

    Call this at the end of your RLM code to specify the output.
    Only the first call to FINAL() takes effect.

    Args:
        result: The final result string to output

    Example:
        summaries = [...]
        FINAL('## Summary\\n' + '\\n'.join(summaries))
    """
    global _final_result, _final_set
    if not _final_set:
        _final_result = str(result)
        _final_set = True


def FINAL_VAR(var_name: str):
    """
    Set a variable as the final output result (JSON serialized).

    Useful for outputting structured data like dictionaries or lists.

    Args:
        var_name: Name of variable in the execution context to output

    Example:
        categories = {'urgent': [...], 'fyi': [...]}
        FINAL_VAR('categories')
    """
    global _final_result, _final_set, _exec_globals
    if not _final_set:
        if var_name in _exec_globals:
            value = _exec_globals[var_name]
            try:
                _final_result = json.dumps(value, indent=2, default=str)
            except:
                _final_result = str(value)
        else:
            _final_result = f"[Error: Variable '{var_name}' not found]"
        _final_set = True


# Global execution context for FINAL_VAR
_exec_globals = {}


def fetch_emails_for_repl(
    query: str,
    max_results: int = 200,
    format_type: str = "metadata",
    verbose: bool = False
) -> tuple[list[dict], dict]:
    """
    Fetch emails for REPL environment with pagination.

    Args:
        query: Gmail search query
        max_results: Maximum emails to fetch
        format_type: Level of detail
        verbose: Enable verbose logging

    Returns:
        Tuple of (emails list, metadata dict)
    """
    service = get_gmail_service(SCOPES)

    all_message_ids = []
    page_token = None
    page_num = 0

    # Phase 1: Collect message IDs with pagination
    while len(all_message_ids) < max_results:
        page_num += 1
        remaining = max_results - len(all_message_ids)
        page_size = min(100, remaining)

        print(f"[REPL] Fetching page {page_num}...", file=sys.stderr)

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
            break

    total_found = len(all_message_ids)
    print(f"[REPL] Found {total_found} messages", file=sys.stderr)

    if not all_message_ids:
        return [], {"query": query, "count": 0, "format": format_type}

    # Phase 2: Fetch message details
    detailed_messages = []

    for i, msg in enumerate(all_message_ids):
        if (i + 1) % 50 == 0:
            print(f"[REPL] Fetching details {i + 1}/{total_found}...", file=sys.stderr)

        if format_type == "minimal":
            api_format = "minimal"
        elif format_type == "metadata":
            api_format = "metadata"
        else:
            api_format = "full"

        full_msg = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format=api_format
        ).execute()

        parsed = parse_message(full_msg, format_type)
        detailed_messages.append(parsed)

    print(f"[REPL] Loaded {total_found} emails into environment", file=sys.stderr)

    metadata = {
        "query": query,
        "count": total_found,
        "format": format_type,
        "pages_fetched": page_num
    }

    return detailed_messages, metadata


def load_emails_from_file(filepath: str) -> tuple[list[dict], dict]:
    """
    Load pre-fetched emails from JSON file.

    Args:
        filepath: Path to JSON file (from gmail_bulk_read.py)

    Returns:
        Tuple of (emails list, metadata dict)
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    data = json.loads(path.read_text())

    if data.get('status') != 'success':
        raise ValueError(f"Invalid email file: status={data.get('status')}")

    emails = data.get('messages', [])
    metadata = {
        "query": data.get('query', 'loaded_from_file'),
        "count": data.get('result_count', len(emails)),
        "format": data.get('metadata', {}).get('format', 'unknown'),
        "source_file": filepath
    }

    print(f"[REPL] Loaded {len(emails)} emails from {filepath}", file=sys.stderr)

    return emails, metadata


def execute_rlm_code(
    code: str,
    emails: list[dict],
    metadata: dict,
    verbose: bool = False
) -> str:
    """
    Execute RLM code in prepared environment.

    Args:
        code: Python code to execute
        emails: List of email dictionaries
        metadata: Query metadata
        verbose: Enable verbose logging

    Returns:
        Final result string
    """
    global _final_result, _final_set, _exec_globals

    # Reset state
    _final_result = None
    _final_set = False

    # Build execution environment
    exec_env = {
        # Data
        'emails': emails,
        'metadata': metadata,

        # Core RLM functions
        'llm_query': llm_query,
        'FINAL': FINAL,
        'FINAL_VAR': FINAL_VAR,

        # Helper functions
        'chunk_by_size': chunk_by_size,
        'chunk_by_sender': chunk_by_sender,
        'chunk_by_sender_domain': chunk_by_sender_domain,
        'chunk_by_date': chunk_by_date,
        'chunk_by_thread': chunk_by_thread,
        'filter_emails': filter_emails,
        'filter_by_keyword': filter_by_keyword,
        'filter_by_sender': filter_by_sender,
        'sort_emails': sort_emails,
        'get_top_senders': get_top_senders,
        'extract_email_summary': extract_email_summary,
        'batch_extract_summaries': batch_extract_summaries,
        'aggregate_results': aggregate_results,
        'deduplicate_emails': deduplicate_emails,

        # Standard library (safe subset)
        'len': len,
        'str': str,
        'int': int,
        'float': float,
        'list': list,
        'dict': dict,
        'set': set,
        'tuple': tuple,
        'range': range,
        'enumerate': enumerate,
        'zip': zip,
        'map': map,
        'filter': filter,
        'sorted': sorted,
        'reversed': reversed,
        'min': min,
        'max': max,
        'sum': sum,
        'any': any,
        'all': all,
        'abs': abs,
        'round': round,
        'print': lambda *args, **kwargs: print(*args, file=sys.stderr, **kwargs),
        'json': json,
    }

    # Store for FINAL_VAR access
    _exec_globals = exec_env

    try:
        if verbose:
            print(f"[REPL] Executing code:\n{code[:200]}...", file=sys.stderr)

        # Execute the code
        exec(code, exec_env)

        # Update globals for FINAL_VAR
        _exec_globals = exec_env

        # Check if FINAL was called
        if _final_set and _final_result is not None:
            return _final_result
        else:
            # No FINAL called - return info message
            return "[Note: Code executed but FINAL() was not called. Use FINAL(result) to output.]"

    except Exception as e:
        return f"[Execution Error: {type(e).__name__}: {str(e)}]"


def main():
    """Main entry point for RLM REPL."""
    parser = argparse.ArgumentParser(
        description="Gmail RLM REPL - Recursive Language Model email analysis environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Built-in Variables:
  emails    - List of email dicts with keys: id, threadId, subject, from, to, date, snippet, body
  metadata  - Dict with: query, count, format

Built-in Functions:
  llm_query(prompt, context)     - Recursive Claude call (returns string)
  chunk_by_size(emails, n)       - Split into n-sized chunks (returns list of lists)
  chunk_by_sender(emails)        - Group by sender (returns dict)
  chunk_by_date(emails, period)  - Group by day/week/month (returns dict)
  filter_by_keyword(emails, kw)  - Filter by keyword (returns list)
  FINAL(result)                  - Set output result (string)
  FINAL_VAR(name)                - Set variable as output (JSON)

Example:
  python gmail_rlm_repl.py --query "newer_than:7d" --max-results 100 --code "
  # Group by sender and summarize top 3
  by_sender = chunk_by_sender(emails)
  top = sorted(by_sender.items(), key=lambda x: -len(x[1]))[:3]
  summaries = []
  for sender, msgs in top:
      s = llm_query(f'Summarize emails from {sender}', str([m['snippet'] for m in msgs]))
      summaries.append(f'{sender} ({len(msgs)}): {s}')
  FINAL('\\n'.join(summaries))
  "
        """
    )

    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--query",
        type=str,
        help="Gmail search query to fetch emails"
    )
    input_group.add_argument(
        "--load-file",
        type=str,
        help="Load emails from JSON file (from gmail_bulk_read.py)"
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=200,
        help="Maximum emails to fetch (default: 200, only used with --query)"
    )

    parser.add_argument(
        "--format",
        type=str,
        choices=["minimal", "metadata", "full"],
        default="metadata",
        help="Email format (default: metadata, only used with --query)"
    )

    parser.add_argument(
        "--code",
        type=str,
        required=True,
        help="Python code to execute in RLM environment"
    )

    parser.add_argument(
        "--code-file",
        type=str,
        help="Load code from file instead of --code argument"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Wrap output in JSON success format"
    )

    args = parser.parse_args()

    # Load code
    if args.code_file:
        code_path = Path(args.code_file)
        if not code_path.exists():
            print(format_error("FileNotFound", f"Code file not found: {args.code_file}"), file=sys.stderr)
            sys.exit(1)
        code = code_path.read_text()
    else:
        code = args.code

    try:
        # Load emails
        if args.query:
            emails, metadata = fetch_emails_for_repl(
                query=args.query,
                max_results=args.max_results,
                format_type=args.format,
                verbose=args.verbose
            )
        else:
            emails, metadata = load_emails_from_file(args.load_file)

        # Execute code
        print(f"[REPL] Executing RLM code...", file=sys.stderr)
        result = execute_rlm_code(code, emails, metadata, args.verbose)

        # Output result
        if args.json_output:
            print(format_success({
                "rlm_result": result,
                "emails_processed": len(emails),
                "query": metadata.get('query', '')
            }))
        else:
            print(result)

        sys.exit(0)

    except FileNotFoundError as e:
        print(format_error("MissingCredentials", str(e)), file=sys.stderr)
        sys.exit(1)

    except HttpError as error:
        print(format_error("APIError", f"Gmail API error: {error.reason}"), file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(format_error("RLMError", str(e)), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
