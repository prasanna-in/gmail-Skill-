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
import re
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
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
    log_verbose,
    status_start,
    status_done,
    status_async
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

# Import cache module
from gmail_rlm_cache import get_cache, init_cache, disable_cache

# Import checkpoint module
from gmail_rlm_checkpoint import (
    checkpoint_parallel_map,
    load_checkpoint_info,
    clear_checkpoint,
    RLMCheckpoint
)

# Import workflow creators
from gmail_rlm_helpers import (
    create_inbox_triage,
    create_weekly_summary,
    create_find_action_items,
    create_sender_analysis
)

# Import security modules
from gmail_security_helpers import (
    extract_severity,
    classify_alerts,
    extract_iocs,
    validate_email_auth,
    map_to_mitre,
    chunk_by_time,
    detect_kill_chains,
    correlate_by_source_ip,
    detect_suspicious_senders,
    analyze_attachments,
    extract_and_analyze_urls,
    deduplicate_security_alerts
)

from gmail_security_workflows import (
    create_security_triage,
    create_detect_attack_chains,
    create_enrich_with_threat_intel,
    create_phishing_analysis
)

import gmail_security_schemas


# OAuth scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


# =============================================================================
# Custom Exceptions
# =============================================================================

class BudgetExceededError(Exception):
    """Raised when session budget or call limit is exceeded."""
    pass


class RecursionDepthExceededError(Exception):
    """Raised when max recursion depth is exceeded."""
    pass


class LowConfidenceError(Exception):
    """Raised when LLM confidence is below threshold."""
    pass


# =============================================================================
# Model Pricing and Defaults
# =============================================================================

# Model pricing per 1M tokens (as of Jan 2026)
MODEL_PRICING = {
    "claude-3-5-haiku-20241022": {"input": 1.00, "output": 5.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-20250514": {"input": 1.00, "output": 5.00},
}

DEFAULT_MAX_BUDGET_USD = 5.00
DEFAULT_MAX_CALLS = 100
DEFAULT_MAX_DEPTH = 3

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
    # Budget and limits
    max_budget_usd: float = DEFAULT_MAX_BUDGET_USD
    max_calls: int = DEFAULT_MAX_CALLS
    budget_exceeded: bool = False
    # Recursion depth tracking
    current_depth: int = 0
    max_depth: int = DEFAULT_MAX_DEPTH
    # Cache stats (populated by cache module)
    cache_hits: int = 0
    cache_misses: int = 0
    cache_tokens_saved: int = 0

    def add_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Accumulate token counts from an API call."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.call_count += 1
        self.updated_at = datetime.now().isoformat()

    def calculate_cost(self) -> float:
        """Calculate total cost based on model pricing."""
        pricing = MODEL_PRICING.get(self.model, {"input": 3.00, "output": 15.00})
        input_cost = (self.total_input_tokens / 1_000_000) * pricing["input"]
        output_cost = (self.total_output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    def check_budget(self) -> None:
        """Raise BudgetExceededError if limits exceeded."""
        current_cost = self.calculate_cost()
        if current_cost >= self.max_budget_usd:
            self.budget_exceeded = True
            raise BudgetExceededError(
                f"Budget exceeded: ${current_cost:.4f} >= ${self.max_budget_usd:.2f} "
                f"(input: {self.total_input_tokens}, output: {self.total_output_tokens})"
            )
        if self.call_count >= self.max_calls:
            self.budget_exceeded = True
            raise BudgetExceededError(
                f"Call limit exceeded: {self.call_count} >= {self.max_calls}"
            )

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
            "model": self.model,
            "estimated_cost_usd": round(self.calculate_cost(), 4),
            "max_budget_usd": self.max_budget_usd,
            "max_calls": self.max_calls,
            "budget_exceeded": self.budget_exceeded,
            "current_depth": self.current_depth,
            "max_depth": self.max_depth,
            "cache": {
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "tokens_saved": self.cache_tokens_saved
            }
        }


# Global session instance
_session: Optional[RLMSession] = None


def get_session() -> RLMSession:
    """Get or create the global RLM session."""
    global _session
    if _session is None:
        _session = RLMSession(model=_default_model)
    return _session


def reset_session(
    model: str = None,
    max_budget_usd: float = None,
    max_calls: int = None,
    max_depth: int = None
) -> RLMSession:
    """Reset the session with optional overrides."""
    global _session
    _session = RLMSession(
        model=model or _default_model,
        max_budget_usd=max_budget_usd if max_budget_usd is not None else DEFAULT_MAX_BUDGET_USD,
        max_calls=max_calls if max_calls is not None else DEFAULT_MAX_CALLS,
        max_depth=max_depth if max_depth is not None else DEFAULT_MAX_DEPTH
    )
    return _session


@contextmanager
def depth_context(session: RLMSession):
    """Track recursion depth, raise if exceeded."""
    if session.current_depth >= session.max_depth:
        raise RecursionDepthExceededError(
            f"Max recursion depth {session.max_depth} exceeded at depth {session.current_depth}"
        )
    session.current_depth += 1
    try:
        yield session.current_depth
    finally:
        session.current_depth -= 1


def llm_query(
    prompt: str,
    context: str = None,
    timeout: int = 120,
    use_rlm_framing: bool = None,
    model: str = None,
    json_output: bool = False,
    use_cache: bool = True,
    _skip_status: bool = False
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
        use_cache: Use caching layer (default: True)

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

    # Get session for token tracking and budget/depth checks
    session = get_session()

    # Check budget before making API call
    session.check_budget()

    # Build the full prompt with optional RLM framing
    parts = []

    if use_rlm_framing:
        parts.append(RLM_PREAMBLE)

    if context:
        parts.append(f"Data to analyze:\n{context}\n")

    parts.append(f"Task: {prompt}")

    full_prompt = "\n".join(parts)

    # Check cache first
    cache = get_cache()
    if use_cache and cache is not None:
        cache_key = cache.get_key(prompt, context or "", model)
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            session.cache_hits += 1
            if not _skip_status:
                status_done("Cache hit")
            return cached_result
        session.cache_misses += 1

    try:
        # Track recursion depth
        with depth_context(session):
            # Initialize Anthropic client (uses ANTHROPIC_API_KEY env var)
            client = Anthropic()

            # Add JSON formatting instruction to prompt if requested
            if json_output:
                full_prompt = full_prompt + "\n\nIMPORTANT: Respond with valid JSON only. No markdown, no explanation, just the JSON."

            # Build request parameters
            request_params = {
                "model": model,
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": full_prompt}],
            }

            # Make API call with timeout
            if not _skip_status:
                status_async("Querying LLM...")
            response = client.messages.create(
                **request_params,
                timeout=float(timeout)
            )

            # Track token usage
            session.add_usage(
                response.usage.input_tokens,
                response.usage.output_tokens
            )

            result = response.content[0].text

            # Store in cache
            if use_cache and cache is not None:
                tokens_used = response.usage.input_tokens + response.usage.output_tokens
                cache.set(cache_key, result, tokens_used, model)

            if not _skip_status:
                status_done("LLM query complete")
            return result

    except (BudgetExceededError, RecursionDepthExceededError):
        raise  # Re-raise control flow exceptions
    except Exception as e:
        import traceback
        error_str = str(e)
        error_type = type(e).__name__

        # Check for missing API key (AuthenticationError)
        if "authentication" in error_str.lower() or "api_key" in error_str.lower():
            return "[LLM Error: ANTHROPIC_API_KEY not set or invalid. Export it in your environment.]"
        elif "timeout" in error_str.lower():
            return "[LLM Error: Query timed out]"
        else:
            # Include error type for better debugging
            return f"[LLM Error: {error_type}: {error_str}]"


def parallel_llm_query(
    prompts: list[tuple[str, str]],
    max_workers: int = 5,
    timeout: int = 120,
    use_rlm_framing: bool = None,
    model: str = None,
    json_output: bool = False,
    _skip_status: bool = False
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
    if not _skip_status:
        status_async(f"Running {len(prompts)} parallel LLM queries...")
    results = [None] * len(prompts)

    def execute_query(index, prompt, context):
        # Note: Individual queries don't print status to avoid noise
        return index, llm_query(prompt, context, timeout, use_rlm_framing, model, json_output, _skip_status=True)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(execute_query, i, p, c): i
            for i, (p, c) in enumerate(prompts)
        }

        for future in as_completed(futures):
            idx, result = future.result()
            results[idx] = result

    if not _skip_status:
        status_done(f"Completed {len(prompts)} queries")
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
    status_async(f"Processing {len(chunks)} chunks...")
    prompts = [(func_prompt, context_fn(chunk)) for chunk in chunks]
    results = parallel_llm_query(prompts, max_workers=max_workers, use_rlm_framing=use_rlm_framing, model=model, json_output=json_output, _skip_status=True)
    status_done(f"Processed {len(chunks)} chunks")
    return results


# =============================================================================
# JSON Output Enforcement (Task 5)
# =============================================================================

# Common JSON schemas for structured output
ACTION_ITEMS_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "task": {"type": "string"},
            "deadline": {"type": "string"},
            "sender": {"type": "string"},
            "priority": {"enum": ["high", "medium", "low"]}
        },
        "required": ["task"]
    }
}

EMAIL_CLASSIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"enum": ["urgent", "action_required", "fyi", "newsletter"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1}
    },
    "required": ["category"]
}


def llm_query_json(
    prompt: str,
    context: str = None,
    schema: dict = None,
    max_retries: int = 2,
    **kwargs
) -> dict | list:
    """
    LLM query with guaranteed JSON output and optional schema validation.

    Retries on parse errors, providing error feedback to improve results.

    Args:
        prompt: The task/question for the LLM
        context: Optional context data
        schema: Optional JSON schema for validation
        max_retries: Number of retries on parse failure (default: 2)
        **kwargs: Additional arguments passed to llm_query

    Returns:
        Parsed JSON (dict or list)

    Raises:
        ValueError: If JSON parsing fails after all retries

    Example:
        items = llm_query_json(
            'Extract action items as JSON array',
            context=email_text,
            schema=ACTION_ITEMS_SCHEMA
        )
    """
    try:
        import jsonschema
        has_jsonschema = True
    except ImportError:
        has_jsonschema = False

    current_prompt = prompt

    for attempt in range(max_retries + 1):
        result = llm_query(current_prompt, context, json_output=True, **kwargs)

        try:
            # Parse JSON
            parsed = json.loads(result)

            # Validate against schema if provided
            if schema and has_jsonschema:
                jsonschema.validate(parsed, schema)

            return parsed

        except json.JSONDecodeError as e:
            if attempt == max_retries:
                raise ValueError(f"JSON parsing failed after {max_retries + 1} attempts: {e}")
            # Retry with error feedback
            current_prompt = f"{prompt}\n\nPrevious response was invalid JSON. Error: {e}. Please respond with valid JSON only."

        except Exception as e:
            # jsonschema.ValidationError or other
            if attempt == max_retries:
                raise ValueError(f"JSON validation failed after {max_retries + 1} attempts: {e}")
            # Retry with schema feedback
            current_prompt = f"{prompt}\n\nPrevious response failed validation: {e}. Please fix and respond with valid JSON."

    return parsed  # Should not reach here


# =============================================================================
# Confidence Scoring (Task 7)
# =============================================================================

@dataclass
class ConfidenceResult:
    """Result with confidence score from LLM query."""
    answer: str
    confidence: float  # 0.0 to 1.0
    reasoning: str     # Optional explanation of confidence level


def llm_query_with_confidence(
    prompt: str,
    context: str = None,
    min_confidence: float = 0.0,
    **kwargs
) -> ConfidenceResult:
    """
    LLM query that returns confidence score with answer.

    The LLM is asked to provide a confidence level (0-100) and reasoning
    along with its answer.

    Args:
        prompt: The task/question for the LLM
        context: Optional context data
        min_confidence: Minimum required confidence (0.0-1.0). Raises if below.
        **kwargs: Additional arguments passed to llm_query

    Returns:
        ConfidenceResult with answer, confidence (0.0-1.0), and reasoning

    Raises:
        LowConfidenceError: If confidence is below min_confidence

    Example:
        result = llm_query_with_confidence(
            'Is this email urgent?',
            context=email_text,
            min_confidence=0.7
        )
        if result.confidence >= 0.8:
            mark_as_urgent(email)
    """
    enhanced_prompt = f"""{prompt}

After your answer, provide on separate lines:
CONFIDENCE: [0-100]
REASONING: [brief explanation of confidence level]"""

    result = llm_query(enhanced_prompt, context, **kwargs)

    # Parse confidence from response
    confidence = 0.5  # Default
    reasoning = ""
    answer = result

    # Extract confidence
    confidence_match = re.search(r'CONFIDENCE:\s*(\d+)', result, re.IGNORECASE)
    if confidence_match:
        confidence = int(confidence_match.group(1)) / 100
        answer = result[:confidence_match.start()].strip()

    # Extract reasoning
    reasoning_match = re.search(r'REASONING:\s*(.+?)(?:\n|$)', result, re.IGNORECASE)
    if reasoning_match:
        reasoning = reasoning_match.group(1).strip()

    # Check minimum confidence threshold
    if confidence < min_confidence:
        raise LowConfidenceError(
            f"Confidence {confidence:.0%} below threshold {min_confidence:.0%}"
        )

    return ConfidenceResult(answer=answer, confidence=confidence, reasoning=reasoning)


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

    status_start("Fetching emails...")

    all_message_ids = []
    page_token = None
    page_num = 0

    # Phase 1: Collect message IDs with pagination
    while len(all_message_ids) < max_results:
        page_num += 1
        remaining = max_results - len(all_message_ids)
        page_size = min(100, remaining)

        log_verbose(f"Fetching page {page_num}...", verbose)

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
    log_verbose(f"Found {total_found} messages", verbose)

    if not all_message_ids:
        status_done("Found 0 emails")
        return [], {"query": query, "count": 0, "format": format_type}

    # Phase 2: Fetch message details
    detailed_messages = []

    for i, msg in enumerate(all_message_ids):
        if (i + 1) % 50 == 0:
            log_verbose(f"Fetching details {i + 1}/{total_found}...", verbose)

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

    status_done(f"Loaded {total_found} emails")

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
    file_metadata = data.get('metadata', {})
    metadata = {
        "query": data.get('query', 'loaded_from_file'),
        "count": data.get('result_count', len(emails)),
        "format": file_metadata.get('format', 'unknown'),
        "source": file_metadata.get('source', 'file'),
        "source_file": filepath
    }

    # Preserve browser-specific metadata if present
    if file_metadata.get('source') == 'browser':
        metadata['webmail_url'] = file_metadata.get('webmail_url', '')
        metadata['folder'] = file_metadata.get('folder', '')

    status_done(f"Loaded {len(emails)} emails")

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

    # Create workflow functions with injected dependencies
    inbox_triage = create_inbox_triage(llm_query, parallel_map)
    weekly_summary = create_weekly_summary(llm_query, parallel_map)
    find_action_items = create_find_action_items(llm_query, llm_query_json)
    sender_analysis = create_sender_analysis(llm_query, parallel_map)

    # Create security workflow functions with injected dependencies
    security_triage = create_security_triage(llm_query, parallel_map)
    detect_attack_chains = create_detect_attack_chains(llm_query)
    enrich_with_threat_intel = create_enrich_with_threat_intel()
    phishing_analysis = create_phishing_analysis(llm_query)

    # Create checkpoint-enabled parallel_map wrapper
    def checkpoint_map(
        func_prompt: str,
        chunks: list,
        context_fn=str,
        checkpoint_path: str = None,
        checkpoint_interval: int = 10,
        **kwargs
    ):
        """parallel_map with checkpoint/resume support."""
        return checkpoint_parallel_map(
            func_prompt=func_prompt,
            chunks=chunks,
            context_fn=context_fn,
            llm_query_fn=llm_query,
            checkpoint_path=checkpoint_path,
            checkpoint_interval=checkpoint_interval,
            emails=emails,
            session_state_fn=lambda: get_session().to_dict(),
            **kwargs
        )

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

        # JSON and confidence functions
        'llm_query_json': llm_query_json,
        'llm_query_with_confidence': llm_query_with_confidence,
        'ConfidenceResult': ConfidenceResult,

        # Pre-built workflows
        'inbox_triage': inbox_triage,
        'weekly_summary': weekly_summary,
        'find_action_items': find_action_items,
        'sender_analysis': sender_analysis,

        # Security workflows
        'security_triage': security_triage,
        'detect_attack_chains': detect_attack_chains,
        'enrich_with_threat_intel': enrich_with_threat_intel,
        'phishing_analysis': phishing_analysis,

        # Security helper functions
        'extract_severity': extract_severity,
        'classify_alerts': classify_alerts,
        'extract_iocs': extract_iocs,
        'validate_email_auth': validate_email_auth,
        'map_to_mitre': map_to_mitre,
        'chunk_by_time': chunk_by_time,
        'detect_kill_chains': detect_kill_chains,
        'correlate_by_source_ip': correlate_by_source_ip,
        'detect_suspicious_senders': detect_suspicious_senders,
        'analyze_attachments': analyze_attachments,
        'extract_and_analyze_urls': extract_and_analyze_urls,
        'deduplicate_security_alerts': deduplicate_security_alerts,

        # Security schemas
        'security_schemas': gmail_security_schemas,

        # Checkpoint support
        'checkpoint_parallel_map': checkpoint_map,

        # JSON schemas
        'ACTION_ITEMS_SCHEMA': ACTION_ITEMS_SCHEMA,
        'EMAIL_CLASSIFICATION_SCHEMA': EMAIL_CLASSIFICATION_SCHEMA,

        # Exceptions (for catching)
        'BudgetExceededError': BudgetExceededError,
        'RecursionDepthExceededError': RecursionDepthExceededError,
        'LowConfidenceError': LowConfidenceError,

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
        're': re,
    }

    # Store for FINAL_VAR access
    _exec_globals = exec_env

    try:
        status_start("Executing code...")
        if verbose:
            log_verbose(f"Code:\n{code[:200]}...", verbose)

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


def check_anthropic_api_key() -> bool:
    """Check if ANTHROPIC_API_KEY is set and valid."""
    import os
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return False
    if not api_key.startswith('sk-ant-'):
        return False
    return True


def main():
    """Main entry point for RLM REPL."""
    parser = argparse.ArgumentParser(
        description="Gmail RLM REPL - Recursive Language Model email analysis environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Built-in Variables:
  emails    - List of email dicts with keys: id, threadId, subject, from, to, date, snippet, body
  metadata  - Dict with: query, count, format

Core Functions:
  llm_query(prompt, context)           - Recursive Claude call (returns string)
  llm_query_json(prompt, context, schema)  - LLM call with JSON output validation
  llm_query_with_confidence(prompt, context, min_confidence)  - LLM call with confidence score
  parallel_llm_query(prompts, max_workers) - Parallel LLM calls (3-5x faster)
  parallel_map(prompt, chunks, context_fn) - Apply prompt to chunks in parallel
  checkpoint_parallel_map(...)         - parallel_map with checkpoint/resume support

Pre-built Workflows:
  inbox_triage(emails)                 - Classify: urgent, action_required, fyi, newsletter
  weekly_summary(emails)               - Executive summary with key themes
  find_action_items(emails)            - Extract tasks with deadlines
  sender_analysis(emails, top_n)       - Analyze top senders' communication patterns

Security Workflows:
  security_triage(emails)              - Complete security alert triage (P1-P5, IOCs, kill chains)
  detect_attack_chains(emails, window) - Multi-pass correlation for attack sequences
  phishing_analysis(emails)            - Specialized phishing detection and categorization
  enrich_with_threat_intel(iocs)       - Prepare IOCs for threat intel enrichment

Security Helper Functions:
  extract_severity(alert)              - Normalize severity from security tool formats
  classify_alerts(emails, llm_query)   - Batch classify alerts into P1-P5
  extract_iocs(emails)                 - Extract IPs, domains, hashes, URLs
  map_to_mitre(alert, llm_query)       - Map to MITRE ATT&CK techniques
  chunk_by_time(emails, minutes)       - Group emails into time windows
  correlate_by_source_ip(emails, llm)  - Analyze alerts by source IP
  detect_suspicious_senders(emails)    - Identify phishing/spoofing attempts
  analyze_attachments(emails)          - Risk assessment for attachments
  extract_and_analyze_urls(emails)     - Identify suspicious URLs

Helper Functions:
  chunk_by_size(emails, n)             - Split into n-sized chunks (returns list of lists)
  chunk_by_sender(emails)              - Group by sender (returns dict)
  chunk_by_date(emails, period)        - Group by day/week/month (returns dict)
  filter_by_keyword(emails, kw)        - Filter by keyword (returns list)
  get_session()                        - Get session stats (tokens, cost, calls)
  FINAL(result)                        - Set output result (string)
  FINAL_VAR(name)                      - Set variable as output (JSON)

Safety Controls:
  --max-budget USD                     - Stop if cost exceeds budget (default: $5.00)
  --max-calls N                        - Stop after N LLM calls (default: 100)
  --max-depth N                        - Max recursion depth (default: 3)
  --no-cache                           - Disable query caching

Example:
  # Basic analysis
  python gmail_rlm_repl.py --query "newer_than:7d" --max-results 100 --code "
  result = inbox_triage(emails)
  FINAL(json.dumps({k: len(v) for k, v in result.items()}))
  "

  # With budget control
  python gmail_rlm_repl.py --query "is:unread" --max-budget 1.00 --code "
  summary = weekly_summary(emails)
  FINAL(summary)
  "

  # Security alert triage
  python gmail_rlm_repl.py --query "label:security-alerts newer_than:7d" --code "
  result = security_triage(emails)
  print(f'P1 Critical: {len(result[\"classifications\"][\"P1\"])}')
  print(f'Kill Chains: {len(result[\"kill_chains\"])}')
  FINAL(result['executive_summary'])
  "
        """
    )

    # Email source selection
    parser.add_argument(
        "--source",
        type=str,
        choices=["gmail", "browser"],
        default="gmail",
        help="Email source: 'gmail' for Gmail API, 'browser' for webmail (default: gmail)"
    )

    # Input source (mutually exclusive for Gmail API mode)
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument(
        "--query",
        type=str,
        help="Gmail search query to fetch emails (used with --source gmail)"
    )
    input_group.add_argument(
        "--load-file",
        type=str,
        help="Load emails from JSON file (from gmail_bulk_read.py)"
    )

    # Browser source options
    parser.add_argument(
        "--webmail-url",
        type=str,
        help="Webmail URL for browser source (e.g., https://outlook.office365.com)"
    )

    parser.add_argument(
        "--webmail-folder",
        type=str,
        default="Inbox",
        help="Folder to read from browser source (default: Inbox)"
    )

    parser.add_argument(
        "--browser-session",
        type=str,
        default="gmail_corporate",
        help="Browser session name for --source browser (default: gmail_corporate)"
    )

    parser.add_argument(
        "--browser-mock",
        action="store_true",
        help="Use mock data for browser source (for testing pipeline)"
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=200,
        help="Maximum emails to fetch (default: 200)"
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

    # Budget and safety controls
    parser.add_argument(
        "--max-budget",
        type=float,
        default=DEFAULT_MAX_BUDGET_USD,
        help=f"Max USD budget for LLM calls (default: {DEFAULT_MAX_BUDGET_USD})"
    )

    parser.add_argument(
        "--max-calls",
        type=int,
        default=DEFAULT_MAX_CALLS,
        help=f"Max number of LLM calls (default: {DEFAULT_MAX_CALLS})"
    )

    parser.add_argument(
        "--max-depth",
        type=int,
        default=DEFAULT_MAX_DEPTH,
        help=f"Max recursion depth for LLM calls (default: {DEFAULT_MAX_DEPTH})"
    )

    # Cache control
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable LLM query caching"
    )

    parser.add_argument(
        "--cache-dir",
        type=str,
        default=None,
        help="Directory for cache files (default: system temp)"
    )

    parser.add_argument(
        "--cache-ttl",
        type=int,
        default=24,
        help="Cache TTL in hours (default: 24)"
    )

    # Checkpoint support
    parser.add_argument(
        "--checkpoint",
        type=str,
        default=None,
        help="Checkpoint file path for resume support"
    )

    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=10,
        help="Save checkpoint every N chunks (default: 10)"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force execution even if RLM mode may be overkill (suppress warnings)"
    )

    args = parser.parse_args()

    # Validate source-specific arguments
    if args.source == "browser":
        if not args.webmail_url:
            print(json.dumps({
                "status": "error",
                "error_type": "ValidationError",
                "message": "--webmail-url is required when using --source browser"
            }), file=sys.stderr)
            sys.exit(1)
        if args.query or args.load_file:
            print(json.dumps({
                "status": "error",
                "error_type": "ValidationError",
                "message": "--query and --load-file cannot be used with --source browser"
            }), file=sys.stderr)
            sys.exit(1)
    elif args.source == "gmail":
        if not args.query and not args.load_file:
            print(json.dumps({
                "status": "error",
                "error_type": "ValidationError",
                "message": "Either --query or --load-file is required when using --source gmail"
            }), file=sys.stderr)
            sys.exit(1)
        if args.webmail_url:
            print(json.dumps({
                "status": "error",
                "error_type": "ValidationError",
                "message": "--webmail-url can only be used with --source browser"
            }), file=sys.stderr)
            sys.exit(1)

    # Check for Anthropic API key
    if not check_anthropic_api_key():
        print(json.dumps({
            "status": "error",
            "error_type": "ConfigurationError",
            "message": "ANTHROPIC_API_KEY not set. RLM requires an Anthropic API key for LLM sub-queries.\n"
                       "Set it with: export ANTHROPIC_API_KEY='sk-ant-api03-...'\n"
                       "Get a key at: https://console.anthropic.com/"
        }), file=sys.stderr)
        sys.exit(1)

    # Set global defaults based on CLI flags
    global _default_use_rlm_framing, _default_model
    if args.no_rlm_framing:
        _default_use_rlm_framing = False
    _default_model = args.model

    # Initialize session with the specified model and limits
    reset_session(
        model=args.model,
        max_budget_usd=args.max_budget,
        max_calls=args.max_calls,
        max_depth=args.max_depth
    )

    # Initialize cache (or disable it)
    if args.no_cache:
        disable_cache()
    else:
        init_cache(cache_dir=args.cache_dir, ttl_hours=args.cache_ttl)

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
        # Load emails based on source
        if args.source == "browser":
            # Browser-based email fetching
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.json',
                delete=False
            )
            temp_filepath = temp_file.name
            temp_file.close()

            # Call browser_email_fetch.py script
            script_dir = Path(__file__).parent
            browser_fetch_script = script_dir / "browser_email_fetch.py"

            if not browser_fetch_script.exists():
                raise FileNotFoundError(
                    f"Browser fetch script not found: {browser_fetch_script}"
                )

            # Build command list
            cmd = [
                sys.executable,
                str(browser_fetch_script),
                "--url", args.webmail_url,
                "--folder", args.webmail_folder,
                "--max-results", str(args.max_results),
                "--session", args.browser_session,
                "--output", temp_filepath
            ]
            if args.verbose:
                cmd.append("--verbose")
            if args.browser_mock:
                cmd.append("--mock")

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                # Try to parse error message
                try:
                    error_data = json.loads(result.stderr)
                    error_msg = error_data.get("message", result.stderr)
                except:
                    error_msg = result.stderr

                raise RuntimeError(
                    f"Browser email fetch failed: {error_msg}"
                )

            # Load emails from temp file
            emails, metadata = load_emails_from_file(temp_filepath)

            # Clean up temp file
            Path(temp_filepath).unlink(missing_ok=True)

        elif args.query:
            # Gmail API query
            emails, metadata = fetch_emails_for_repl(
                query=args.query,
                max_results=args.max_results,
                format_type=args.format,
                verbose=args.verbose
            )
        else:
            # Load from file
            emails, metadata = load_emails_from_file(args.load_file)

        # Check if RLM mode is being misused (small dataset with simple workflows)
        if not args.force and len(emails) < 100:
            # List of simple workflows that could be done in Normal Mode for <100 emails
            simple_workflows = [
                'find_action_items',
                'inbox_triage',
                'weekly_summary',
                'sender_analysis'
            ]

            # Check if code uses any simple workflows
            using_simple_workflow = any(workflow in code for workflow in simple_workflows)

            if using_simple_workflow:
                print("", file=sys.stderr)
                print("⚠️  WARNING: RLM mode may be overkill for this task", file=sys.stderr)
                print(f"   • Email count: {len(emails)} (< 100)", file=sys.stderr)
                print(f"   • Detected simple workflow in code", file=sys.stderr)
                print("", file=sys.stderr)
                print("💡 RECOMMENDATION: Use Normal Mode instead", file=sys.stderr)
                print("   1. Fetch emails:", file=sys.stderr)
                print(f"      .venv/bin/python skills/gmail/scripts/gmail_read.py \\", file=sys.stderr)
                if args.query:
                    print(f"        --query \"{args.query}\" \\", file=sys.stderr)
                print(f"        --max-results {len(emails)} \\", file=sys.stderr)
                print(f"        --format full", file=sys.stderr)
                print("", file=sys.stderr)
                print("   2. Let Claude Code Agent analyze the JSON directly", file=sys.stderr)
                print("      (faster, cheaper, and simpler for <100 emails)", file=sys.stderr)
                print("", file=sys.stderr)
                print("To proceed anyway, use --force flag", file=sys.stderr)
                print("", file=sys.stderr)
                sys.exit(1)

        # Execute code
        result = execute_rlm_code(code, emails, metadata, args.verbose)

        # Output result
        if args.json_output:
            print(format_success({
                "result": result,
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
