#!/usr/bin/env python3
"""
Gmail Agent - Autonomous Email Analysis

Provides natural language interface to Gmail operations using RLM.
Supports both agent mode (default) and script mode (for power users).

Usage:
    # Agent mode (default - natural language)
    gmail_agent.py "Triage security alerts from last week"

    # Script mode (power users - Python code)
    gmail_agent.py --script "result = security_triage(emails); FINAL(result)"

    # Resume previous session
    gmail_agent.py --resume session_20250119_143022

    # List available sessions
    gmail_agent.py --list-sessions

Examples:
    # Security workflows
    gmail_agent.py "Triage security alerts"
    gmail_agent.py "Find attack chains in alerts from yesterday"
    gmail_agent.py "Analyze phishing attempts"

    # General email workflows
    gmail_agent.py "Triage my inbox"
    gmail_agent.py "Summarize emails from top 5 senders"
    gmail_agent.py "Find action items with deadlines"
    gmail_agent.py "Summarize my week"

    # Multi-turn dialogue
    gmail_agent.py "Triage alerts"
    > Show me P1 details
    > What IOCs were found?
    > done
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add parent directory to path to import agent module
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.agent_core import AgentCore


def main():
    parser = argparse.ArgumentParser(
        description='Gmail Agent - Autonomous Email Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        'goal',
        nargs='?',
        help='Natural language goal (agent mode - default)'
    )
    mode_group.add_argument(
        '--script',
        type=str,
        help='Python code to execute (script mode for power users)'
    )
    mode_group.add_argument(
        '--resume',
        type=str,
        metavar='SESSION_ID',
        help='Resume a previous session'
    )
    mode_group.add_argument(
        '--list-sessions',
        action='store_true',
        help='List all available sessions'
    )

    # Email query parameters
    parser.add_argument(
        '--query',
        type=str,
        default='newer_than:7d',
        help='Gmail query string (default: newer_than:7d)'
    )
    parser.add_argument(
        '--max-results',
        type=int,
        default=100,
        help='Maximum number of emails to fetch (default: 100)'
    )

    # Budget and model
    parser.add_argument(
        '--max-budget',
        type=float,
        default=1.0,
        help='Budget limit in USD (default: $1.00)'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='claude-sonnet-4-20250514',
        help='LLM model to use (default: claude-sonnet-4-20250514)'
    )

    # Output options
    parser.add_argument(
        '--format',
        type=str,
        choices=['text', 'json', 'html'],
        default='text',
        help='Output format (default: text)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode (shows generated code)'
    )
    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='Disable multi-turn dialogue (exit after first response)'
    )

    args = parser.parse_args()

    # Check for ANTHROPIC_API_KEY
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("Error: ANTHROPIC_API_KEY environment variable not set", file=sys.stderr)
        print("", file=sys.stderr)
        print("Please set your Anthropic API key:", file=sys.stderr)
        print("  export ANTHROPIC_API_KEY='sk-ant-...'", file=sys.stderr)
        print("", file=sys.stderr)
        print("Or add it to your shell profile (~/.bashrc or ~/.zshrc):", file=sys.stderr)
        print("  echo 'export ANTHROPIC_API_KEY=\"sk-ant-...\"' >> ~/.zshrc", file=sys.stderr)
        return 1

    # Initialize agent
    try:
        agent = AgentCore(
            model=args.model,
            output_format=args.format,
            debug=args.debug
        )
    except Exception as e:
        print(f"Error initializing agent: {e}", file=sys.stderr)
        return 1

    # List sessions mode
    if args.list_sessions:
        print(agent.list_sessions())
        return 0

    # Resume mode
    if args.resume:
        print(f"Resuming session: {args.resume}")
        print()
        # The goal will be obtained interactively
        response, session_id = agent.run_agent_mode(
            goal="",  # Will prompt for goal
            query=args.query,
            max_results=args.max_results,
            max_budget=args.max_budget,
            session_id=args.resume,
            interactive=not args.non_interactive
        )
        return 0

    # Script mode (power users)
    if args.script:
        response = agent.run_script_mode(
            code=args.script,
            query=args.query,
            max_results=args.max_results,
            max_budget=args.max_budget
        )
        print(response)
        return 0

    # Agent mode (default)
    if not args.goal:
        print("Error: Please provide a goal or use --help for usage information", file=sys.stderr)
        return 1

    try:
        response, session_id = agent.run_agent_mode(
            goal=args.goal,
            query=args.query,
            max_results=args.max_results,
            max_budget=args.max_budget,
            interactive=not args.non_interactive
        )
        return 0
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
