#!/usr/bin/env python3
"""
Gmail Smart Dispatcher

Automatically decides whether to use Normal Mode or RLM Mode based on:
- Email count
- Task complexity
- Intent (send, read, analyze, etc.)

This provides a simpler CLI interface where users don't need to choose
between gmail_read.py and gmail_rlm_repl.py manually.

Usage:
    # Simple analysis - auto-routes to best mode
    python gmail_smart.py analyze "find action items" --query "newer_than:1d"

    # Send email - always uses Normal Mode
    python gmail_smart.py send --to "user@example.com" --subject "Hi" --body "Hello"

    # Triage - auto-decides based on email count
    python gmail_smart.py analyze "triage inbox" --query "is:inbox newer_than:7d"
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple


# Workflow complexity mapping
SIMPLE_WORKFLOWS = {
    'find_action_items',
    'inbox_triage',
    'weekly_summary',
    'sender_analysis'
}

COMPLEX_WORKFLOWS = {
    'security_triage',
    'detect_attack_chains',
    'phishing_analysis',
    'enrich_with_threat_intel'
}

# Intent keywords mapping
INTENT_KEYWORDS = {
    'send': ['send', 'compose', 'email to', 'write to'],
    'read': ['read', 'show', 'display', 'get', 'fetch'],
    'label': ['label', 'tag', 'organize', 'folder'],
    'triage': ['triage', 'organize', 'categorize', 'classify'],
    'summarize': ['summarize', 'summary', 'overview'],
    'action_items': ['action items', 'tasks', 'todo', 'deadlines'],
    'security': ['security', 'alert', 'threat', 'attack', 'phishing', 'malware'],
}


def detect_intent(goal: str) -> str:
    """Detect user intent from goal string."""
    goal_lower = goal.lower()

    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in goal_lower for keyword in keywords):
            return intent

    # Default to analyze
    return 'analyze'


def detect_workflow(goal: str) -> Optional[str]:
    """Detect if goal maps to a pre-built workflow."""
    goal_lower = goal.lower()

    # Check simple workflows
    if 'action item' in goal_lower or 'todo' in goal_lower:
        return 'find_action_items'
    if 'triage' in goal_lower or 'categorize' in goal_lower:
        return 'inbox_triage'
    if 'summary' in goal_lower or 'summarize' in goal_lower:
        return 'weekly_summary'
    if 'sender' in goal_lower and 'analyz' in goal_lower:
        return 'sender_analysis'

    # Check complex workflows
    if 'security' in goal_lower and 'triage' in goal_lower:
        return 'security_triage'
    if 'attack chain' in goal_lower or 'kill chain' in goal_lower:
        return 'detect_attack_chains'
    if 'phishing' in goal_lower:
        return 'phishing_analysis'

    return None


def estimate_email_count(query: str, max_results: int) -> int:
    """
    Estimate email count for a query.
    For now, just returns max_results as upper bound.
    Could be enhanced to actually count via Gmail API.
    """
    return max_results


def should_use_rlm(
    email_count: int,
    intent: str,
    workflow: Optional[str],
    complexity: str
) -> Tuple[bool, str]:
    """
    Decide whether to use RLM mode.

    Returns:
        (use_rlm, reason)
    """
    # Simple operations always use Normal Mode
    if intent in ['send', 'label', 'read']:
        return False, f"Simple operation ({intent}) - use Normal Mode"

    # Large datasets always use RLM
    if email_count >= 100:
        return True, f"Large dataset ({email_count} emails) - use RLM for pagination"

    # Security workflows are complex, always use RLM
    if intent == 'security' or workflow in COMPLEX_WORKFLOWS:
        return True, f"Complex security analysis - use RLM"

    # Small dataset (<100) with simple analysis
    if email_count < 100:
        if workflow in SIMPLE_WORKFLOWS:
            return False, f"Small dataset ({email_count} emails) + simple workflow - use Normal Mode + Agent"
        elif complexity == 'simple':
            return False, f"Small dataset ({email_count} emails) + simple analysis - use Normal Mode + Agent"
        else:
            return True, f"Small dataset but complex analysis - use RLM"

    # Default: use RLM for analysis tasks
    return True, "Analysis task - use RLM"


def main():
    parser = argparse.ArgumentParser(
        description="Smart Gmail dispatcher - automatically routes to Normal or RLM mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find action items (auto-routes based on email count)
  python gmail_smart.py analyze "find action items" --query "newer_than:1d"

  # Triage inbox (auto-routes based on email count)
  python gmail_smart.py analyze "triage my inbox" --query "is:inbox newer_than:7d"

  # Security analysis (always uses RLM - complex)
  python gmail_smart.py analyze "triage security alerts" --query "label:security-alerts"

  # Send email (always uses Normal Mode)
  python gmail_smart.py send --to "user@example.com" --subject "Hi" --body "Hello"
        """
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # Analyze subcommand
    analyze_parser = subparsers.add_parser('analyze', help='Analyze emails with smart mode selection')
    analyze_parser.add_argument('goal', type=str, help='Analysis goal in natural language')
    analyze_parser.add_argument('--query', type=str, required=True, help='Gmail search query')
    analyze_parser.add_argument('--max-results', type=int, default=100, help='Max emails to fetch')
    analyze_parser.add_argument('--complexity', type=str, choices=['simple', 'complex'], default='simple',
                                help='Analysis complexity (default: simple)')
    analyze_parser.add_argument('--max-budget', type=float, default=1.0, help='Max budget for RLM mode (USD)')
    analyze_parser.add_argument('--force-rlm', action='store_true', help='Force RLM mode')
    analyze_parser.add_argument('--force-normal', action='store_true', help='Force Normal mode')
    analyze_parser.add_argument('--verbose', action='store_true', help='Verbose output')
    analyze_parser.add_argument('--dry-run', action='store_true', help='Show decision without executing')

    # Send subcommand (always Normal Mode)
    send_parser = subparsers.add_parser('send', help='Send email (always Normal Mode)')
    send_parser.add_argument('--to', type=str, required=True, help='Recipient email')
    send_parser.add_argument('--subject', type=str, required=True, help='Email subject')
    send_parser.add_argument('--body', type=str, required=True, help='Email body')
    send_parser.add_argument('--cc', type=str, help='CC recipients')
    send_parser.add_argument('--bcc', type=str, help='BCC recipients')

    args = parser.parse_args()

    script_dir = Path(__file__).parent

    if args.command == 'send':
        # Always use Normal Mode for sending
        cmd = [
            sys.executable,
            str(script_dir / 'gmail_send.py'),
            '--to', args.to,
            '--subject', args.subject,
            '--body', args.body
        ]
        if args.cc:
            cmd.extend(['--cc', args.cc])
        if args.bcc:
            cmd.extend(['--bcc', args.bcc])

        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)

    elif args.command == 'analyze':
        # Detect intent and workflow
        intent = detect_intent(args.goal)
        workflow = detect_workflow(args.goal)
        email_count = estimate_email_count(args.query, args.max_results)

        # Decide mode
        if args.force_rlm:
            use_rlm = True
            reason = "User forced RLM mode"
        elif args.force_normal:
            use_rlm = False
            reason = "User forced Normal mode"
        else:
            use_rlm, reason = should_use_rlm(email_count, intent, workflow, args.complexity)

        # Print decision
        print(f"📊 Analysis Decision:", file=sys.stderr)
        print(f"   Goal: {args.goal}", file=sys.stderr)
        print(f"   Detected intent: {intent}", file=sys.stderr)
        if workflow:
            print(f"   Detected workflow: {workflow}", file=sys.stderr)
        print(f"   Estimated emails: {email_count}", file=sys.stderr)
        print(f"   Complexity: {args.complexity}", file=sys.stderr)
        print(f"   Mode: {'RLM' if use_rlm else 'Normal'}", file=sys.stderr)
        print(f"   Reason: {reason}", file=sys.stderr)
        print("", file=sys.stderr)

        if args.dry_run:
            print("✓ Dry run complete (no execution)", file=sys.stderr)
            sys.exit(0)

        if use_rlm:
            # Use RLM mode
            print("🚀 Executing with RLM mode...", file=sys.stderr)

            # Construct RLM code based on workflow
            if workflow:
                rlm_code = f"result = {workflow}(emails); FINAL_VAR('result')"
            else:
                # Generic analysis code
                rlm_code = f"""
# Goal: {args.goal}
# Custom analysis - please enhance this code based on your goal
summaries = []
for email in emails[:10]:
    summaries.append(f"From: {{email['from']}}, Subject: {{email['subject']}}")
FINAL('\\n'.join(summaries))
"""

            cmd = [
                sys.executable,
                str(script_dir / 'gmail_rlm_repl.py'),
                '--query', args.query,
                '--max-results', str(args.max_results),
                '--max-budget', str(args.max_budget),
                '--code', rlm_code,
                '--force'  # Suppress warning since we already made the decision
            ]
            if args.verbose:
                cmd.append('--verbose')

            result = subprocess.run(cmd, capture_output=True, text=True)
            print(result.stdout)
            if result.returncode != 0:
                print(result.stderr, file=sys.stderr)
            sys.exit(result.returncode)

        else:
            # Use Normal mode
            print("🚀 Executing with Normal mode...", file=sys.stderr)
            print("   Fetching emails, then recommend Agent to analyze", file=sys.stderr)
            print("", file=sys.stderr)

            cmd = [
                sys.executable,
                str(script_dir / 'gmail_read.py'),
                '--query', args.query,
                '--max-results', str(args.max_results),
                '--format', 'full'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                # Parse result
                data = json.loads(result.stdout)
                print(result.stdout)
                print("", file=sys.stderr)
                print(f"✓ Fetched {data.get('result_count', 0)} emails", file=sys.stderr)
                print("", file=sys.stderr)
                print("💡 NEXT STEP: Ask Claude Code Agent to analyze the JSON above", file=sys.stderr)
                print(f"   Example: \"Analyze the emails above and {args.goal}\"", file=sys.stderr)
            else:
                print(result.stderr, file=sys.stderr)

            sys.exit(result.returncode)


if __name__ == '__main__':
    main()
