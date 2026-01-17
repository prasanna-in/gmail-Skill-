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
    parallel_llm_query(prompts, max_workers)  - Parallel LLM calls (3-5x faster)
    parallel_map(prompt, chunks, context_fn)  - Apply prompt to chunks in parallel
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
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from anthropic import Anthropic
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
    deduplicate_emails,
    prepare_llm_batch
)


# OAuth scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# RLM preamble for sub-query framing
RLM_PREAMBLE = """You are a sub-query processor in a Recursive Language Model (RLM) system.

Your role:
- You are one of potentially many parallel sub-queries analyzing a subset of data
- Your output will be aggregated with other sub-query results
- Be concise and focused - avoid preambles, summaries of what you'll do, or sign-offs
- Output structured data when possible (bullet points, key: value pairs)
- If the task asks for a specific format, follow it exactly

"""

# Global to store final result
_final_result = None
_final_set = False

# Global default for RLM framing (can be disabled via CLI)
_default_use_rlm_framing = True

# Global default model for sub-queries
_default_model = "claude-sonnet-4-20250514"


@dataclass
class RLMSession:
    """Tracks token usage and metadata for an RLM session."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    call_count: int = 0
    model: str = "claude-sonnet-4-20250514"

    def add_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Accumulate token counts from an API call."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.call_count += 1
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        """Return session stats as a dictionary."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "call_count": self.call_count,
            "model": self.model
        }


# Global session instance
_session: Optional[RLMSession] = None


def get_session() -> RLMSession:
    """Get or create the global RLM session."""
    global _session
    if _session is None:
        _session = RLMSession(model=_default_model)
    return _session


def reset_session(model: str = None) -> RLMSession:
    """Reset the session with optional model override."""
    global _session
    _session = RLMSession(model=model or _default_model)
    return _session


def llm_query(
    prompt: str,
    context: str = None,
    timeout: int = 120,
    use_rlm_framing: bool = None,
    model: str = None,
    json_output: bool = False
) -> str:
    """
    Invoke Claude recursively via Anthropic SDK.

    This is the key RLM function - enables recursive LLM calls where each
    sub-query has fresh context, avoiding context rot from long conversations.

    Args:
        prompt: The task/question for the LLM
        context: Optional context data (e.g., email contents)
        timeout: Timeout in seconds (default: 120)
        use_rlm_framing: Include RLM preamble for concise, aggregation-ready output
                         (default: None, uses global _default_use_rlm_framing)
        model: Model to use (default: uses global _default_model)
        json_output: Request JSON response format (default: False)

    Returns:
        LLM response string

    Example:
        summary = llm_query(
            'What action items are in these emails?',
            context=str([e['snippet'] for e in emails[:10]])
        )
    """
    # Use global defaults if not explicitly set
    if use_rlm_framing is None:
        use_rlm_framing = _default_use_rlm_framing
    if model is None:
        model = _default_model

    # Build the full prompt with optional RLM framing
    parts = []

    if use_rlm_framing:
        parts.append(RLM_PREAMBLE)

    if context:
        parts.append(f"Data to analyze:\n{context}\n")

    parts.append(f"Task: {prompt}")

    full_prompt = "\n".join(parts)

    try:
        # Get session for token tracking
        session = get_session()

        # Initialize Anthropic client (uses ANTHROPIC_API_KEY env var)
        client = Anthropic()

        # Build request parameters
        request_params = {
            "model": model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": full_prompt}],
        }

        # Add JSON output mode if requested
        if json_output:
            request_params["response_format"] = {"type": "json_object"}

        # Make API call with timeout
        response = client.messages.create(
            **request_params,
            timeout=float(timeout)
        )

        # Track token usage
        session.add_usage(
            response.usage.input_tokens,
            response.usage.output_tokens
        )

        return response.content[0].text

    except Exception as e:
        error_str = str(e)
        if "ANTHROPIC_API_KEY" in error_str or "api_key" in error_str.lower():
            return "[LLM Error: ANTHROPIC_API_KEY not set. Export it in your environment.]"
        elif "timeout" in error_str.lower():
            return "[LLM Error: Query timed out]"
        else:
            return f"[LLM Error: {error_str}]"


def parallel_llm_query(
    prompts: list[tuple[str, str]],
    max_workers: int = 5,
    timeout: int = 120,
    use_rlm_framing: bool = None,
    model: str = None,
    json_output: bool = False
) -> list[str]:
    """
    Execute multiple LLM queries in parallel.

    Args:
        prompts: List of (prompt, context) tuples
        max_workers: Max concurrent workers (default: 5)
        timeout: Per-query timeout in seconds
        use_rlm_framing: Include RLM preamble for concise, aggregation-ready output
                         (default: None, uses global _default_use_rlm_framing)
        model: Model to use (default: uses global _default_model)
        json_output: Request JSON response format (default: False)

    Returns:
        List of results in same order as prompts
    """
    results = [None] * len(prompts)

    def execute_query(index, prompt, context):
        return index, llm_query(prompt, context, timeout, use_rlm_framing, model, json_output)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(execute_query, i, p, c): i
            for i, (p, c) in enumerate(prompts)
        }

        for future in as_completed(futures):
            idx, result = future.result()
            results[idx] = result

    return results


def parallel_map(
    func_prompt: str,
    chunks: list,
    context_fn: Callable = str,
    max_workers: int = 5,
    use_rlm_framing: bool = None,
    model: str = None,
    json_output: bool = False
) -> list[str]:
    """
    Apply the same LLM prompt to multiple chunks in parallel.

    Args:
        func_prompt: Prompt template (use {chunk} placeholder)
        chunks: List of data chunks
        context_fn: Function to convert chunk to context string
        max_workers: Max concurrent workers
        use_rlm_framing: Include RLM preamble for concise, aggregation-ready output
                         (default: None, uses global _default_use_rlm_framing)
        model: Model to use (default: uses global _default_model)
        json_output: Request JSON response format (default: False)

    Returns:
        List of results

    Example:
        summaries = parallel_map(
            'Summarize these emails',
            chunk_by_size(emails, 20),
            context_fn=lambda c: str([e['snippet'] for e in c]),
            max_workers=5
        )
    """
    prompts = [(func_prompt, context_fn(chunk)) for chunk in chunks]
    return parallel_llm_query(prompts, max_workers=max_workers, use_rlm_framing=use_rlm_framing, model=model, json_output=json_output)


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
        'parallel_llm_query': parallel_llm_query,
        'parallel_map': parallel_map,
        'FINAL': FINAL,
        'FINAL_VAR': FINAL_VAR,
        'RLM_PREAMBLE': RLM_PREAMBLE,
        'get_session': get_session,

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
        'prepare_llm_batch': prepare_llm_batch,

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
  parallel_llm_query(prompts, max_workers)  - Parallel LLM calls (3-5x faster)
  parallel_map(prompt, chunks, context_fn)  - Apply prompt to chunks in parallel
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

    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Max parallel workers for parallel_* functions (default: 5)"
    )

    parser.add_argument(
        "--no-rlm-framing",
        action="store_true",
        help="Disable RLM preamble in sub-queries (for debugging)"
    )

    parser.add_argument(
        "--model",
        type=str,
        default="claude-sonnet-4-20250514",
        help="Model for LLM sub-queries (default: claude-sonnet-4-20250514)"
    )

    args = parser.parse_args()

    # Set global defaults based on CLI flags
    global _default_use_rlm_framing, _default_model
    if args.no_rlm_framing:
        _default_use_rlm_framing = False
    _default_model = args.model

    # Initialize session with the specified model
    reset_session(model=args.model)

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
                "query": metadata.get('query', ''),
                "session": get_session().to_dict()
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
