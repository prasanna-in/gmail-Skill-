"""
Result Formatter for Gmail Agent

Formats RLM execution results for user-friendly display.
Supports text, JSON, and HTML output formats.
"""

import json
from typing import Dict, List, Optional, Any, Tuple


class ResultFormatter:
    """Formats execution results for display."""

    def __init__(self, format: str = 'text'):
        """
        Initialize formatter.

        Args:
            format: Output format ('text', 'json', 'html')
        """
        self.format = format

    def format_result(
        self,
        data: Any,
        conversation_history: Optional[List[Tuple[str, str]]] = None,
        context: Optional[Dict] = None
    ) -> str:
        """
        Format execution result based on output format.

        Args:
            data: Result data from RLM execution
            conversation_history: Previous conversation turns
            context: Additional context (cost, execution time, etc.)

        Returns:
            Formatted string for display
        """
        if self.format == 'json':
            return self._format_json(data, context)
        elif self.format == 'html':
            return self._format_html(data, context)
        else:
            return self._format_text(data, conversation_history, context)

    def _format_text(
        self,
        data: Any,
        conversation_history: Optional[List[Tuple[str, str]]],
        context: Optional[Dict]
    ) -> str:
        """Format result as human-readable text."""
        lines = []

        # Detect result type and format accordingly
        if isinstance(data, dict):
            # Check for common result structures
            if 'summary' in data or 'classifications' in data:
                # Security triage result
                lines.extend(self._format_security_triage(data))
            elif 'urgent' in data or 'action_required' in data:
                # Inbox triage result
                lines.extend(self._format_inbox_triage(data))
            elif 'attack_id' in data or (isinstance(data, list) and data and 'attack_id' in data[0]):
                # Attack chains result
                lines.extend(self._format_attack_chains(data))
            elif 'credential_harvesting' in data or 'bec_attempts' in data:
                # Phishing analysis result
                lines.extend(self._format_phishing_analysis(data))
            else:
                # Generic dict result
                lines.extend(self._format_generic_dict(data))
        elif isinstance(data, list):
            # List of items
            lines.extend(self._format_list(data))
        else:
            # Simple value
            lines.append(str(data))

        # Add context information if available
        if context:
            lines.append("")
            lines.append("─" * 50)
            if 'cost' in context:
                lines.append(f"Cost: ${context['cost']:.4f}")
            if 'execution_time' in context:
                lines.append(f"Execution time: {context['execution_time']:.2f}s")

        return "\n".join(lines)

    def _format_security_triage(self, data: Dict) -> List[str]:
        """Format security triage results."""
        lines = []

        # Executive summary
        if 'executive_summary' in data:
            lines.append("EXECUTIVE SUMMARY")
            lines.append("─" * 50)
            lines.append(data['executive_summary'])
            lines.append("")

        # Summary statistics
        if 'summary' in data:
            summary = data['summary']
            lines.append("SUMMARY STATISTICS")
            lines.append("─" * 50)
            lines.append(f"Total Alerts: {summary.get('total_alerts', 0)}")
            lines.append(f"P1 Critical: {summary.get('p1_critical', 0)}")
            lines.append(f"P2 High: {summary.get('p2_high', 0)}")
            lines.append(f"P3 Medium: {summary.get('p3_medium', 0)}")
            lines.append(f"P4 Low: {summary.get('p4_low', 0)}")
            lines.append(f"P5 Info: {summary.get('p5_info', 0)}")
            lines.append("")

        # Classifications
        if 'classifications' in data:
            classifications = data['classifications']
            if classifications.get('P1'):
                lines.append("P1 CRITICAL ALERTS")
                lines.append("─" * 50)
                for alert in classifications['P1'][:5]:  # Show first 5
                    lines.append(f"• {alert.get('subject', 'No subject')}")
                    if 'reasoning' in alert:
                        lines.append(f"  Reason: {alert['reasoning']}")
                if len(classifications['P1']) > 5:
                    lines.append(f"  ... and {len(classifications['P1']) - 5} more")
                lines.append("")

        # Kill chains
        if 'kill_chains' in data and data['kill_chains']:
            lines.append("DETECTED ATTACK CHAINS")
            lines.append("─" * 50)
            for i, chain in enumerate(data['kill_chains'][:3]):  # Show first 3
                lines.append(f"Chain {i + 1}: {chain.get('pattern', 'Unknown pattern')}")
                lines.append(f"  Confidence: {chain.get('confidence', 0):.0%}")
                if 'mitre_techniques' in chain:
                    lines.append(f"  MITRE: {', '.join(chain['mitre_techniques'])}")
            if len(data['kill_chains']) > 3:
                lines.append(f"  ... and {len(data['kill_chains']) - 3} more")
            lines.append("")

        # IOCs
        if 'iocs' in data:
            iocs = data['iocs']
            lines.append("INDICATORS OF COMPROMISE")
            lines.append("─" * 50)
            lines.append(f"IPs: {len(iocs.get('ips', []))}")
            lines.append(f"Domains: {len(iocs.get('domains', []))}")
            lines.append(f"File Hashes: {len(iocs.get('file_hashes', []))}")
            lines.append(f"URLs: {len(iocs.get('urls', []))}")
            lines.append("")

        return lines

    def _format_inbox_triage(self, data: Dict) -> List[str]:
        """Format inbox triage results."""
        lines = []

        lines.append("INBOX TRIAGE")
        lines.append("─" * 50)

        categories = [
            ('urgent', 'URGENT'),
            ('action_required', 'ACTION REQUIRED'),
            ('fyi', 'FYI'),
            ('newsletter', 'NEWSLETTERS')
        ]

        for key, label in categories:
            if key in data:
                items = data[key]
                lines.append(f"\n{label} ({len(items)} emails)")
                lines.append("─" * 30)
                for email in items[:5]:  # Show first 5
                    subject = email.get('subject', 'No subject')
                    sender = email.get('from', 'Unknown sender')
                    lines.append(f"• {subject}")
                    lines.append(f"  From: {sender}")
                if len(items) > 5:
                    lines.append(f"  ... and {len(items) - 5} more")

        return lines

    def _format_attack_chains(self, data: Any) -> List[str]:
        """Format attack chain detection results."""
        lines = []

        chains = data if isinstance(data, list) else [data]

        lines.append("ATTACK CHAIN DETECTION")
        lines.append("─" * 50)
        lines.append(f"Total Chains Detected: {len(chains)}")
        lines.append("")

        for i, chain in enumerate(chains):
            lines.append(f"Chain {i + 1}: {chain.get('attack_id', 'Unknown')}")
            lines.append(f"  Pattern: {chain.get('pattern', 'Unknown')}")
            lines.append(f"  Severity: {chain.get('severity', 'Unknown')}")
            lines.append(f"  Confidence: {chain.get('confidence', 0):.0%}")
            if 'mitre_techniques' in chain:
                lines.append(f"  MITRE: {', '.join(chain['mitre_techniques'])}")
            if 'start_time' in chain:
                lines.append(f"  Start Time: {chain['start_time']}")
            lines.append("")

        return lines

    def _format_phishing_analysis(self, data: Dict) -> List[str]:
        """Format phishing analysis results."""
        lines = []

        lines.append("PHISHING ANALYSIS")
        lines.append("─" * 50)

        if 'summary' in data:
            lines.append(data['summary'])
            lines.append("")

        categories = [
            ('credential_harvesting', 'Credential Harvesting'),
            ('bec_attempts', 'BEC Attempts'),
            ('brand_impersonation', 'Brand Impersonation'),
            ('malicious_attachments', 'Malicious Attachments'),
            ('malicious_links', 'Malicious Links')
        ]

        for key, label in categories:
            if key in data and data[key]:
                items = data[key]
                lines.append(f"\n{label} ({len(items)})")
                lines.append("─" * 30)
                for item in items[:3]:  # Show first 3
                    lines.append(f"• {item.get('subject', item.get('description', 'No details'))}")
                if len(items) > 3:
                    lines.append(f"  ... and {len(items) - 3} more")

        return lines

    def _format_generic_dict(self, data: Dict) -> List[str]:
        """Format a generic dictionary result."""
        lines = []
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                lines.append(f"{key}: {json.dumps(value, indent=2)}")
            else:
                lines.append(f"{key}: {value}")
        return lines

    def _format_list(self, data: List) -> List[str]:
        """Format a list result."""
        lines = []
        for i, item in enumerate(data[:10]):  # Show first 10
            if isinstance(item, dict):
                # Try to find a meaningful field to display
                display = item.get('subject') or item.get('title') or item.get('description') or str(item)
                lines.append(f"{i + 1}. {display}")
            else:
                lines.append(f"{i + 1}. {item}")

        if len(data) > 10:
            lines.append(f"... and {len(data) - 10} more items")

        return lines

    def _format_json(self, data: Any, context: Optional[Dict]) -> str:
        """Format result as JSON."""
        output = {
            'result': data,
            'context': context or {}
        }
        return json.dumps(output, indent=2)

    def _format_html(self, data: Any, context: Optional[Dict]) -> str:
        """Format result as HTML."""
        # Simple HTML formatting
        html_parts = []
        html_parts.append("<html><head><style>")
        html_parts.append("body { font-family: Arial, sans-serif; margin: 20px; }")
        html_parts.append("h1 { color: #333; }")
        html_parts.append("h2 { color: #666; margin-top: 20px; }")
        html_parts.append(".stat { margin: 10px 0; }")
        html_parts.append(".alert { padding: 10px; margin: 5px 0; border-left: 3px solid #f00; }")
        html_parts.append("</style></head><body>")

        html_parts.append("<h1>Gmail Agent Results</h1>")

        # Convert data to HTML
        if isinstance(data, dict):
            for key, value in data.items():
                html_parts.append(f"<h2>{key}</h2>")
                html_parts.append(f"<div>{self._value_to_html(value)}</div>")
        else:
            html_parts.append(f"<div>{self._value_to_html(data)}</div>")

        # Add context
        if context:
            html_parts.append("<h2>Execution Details</h2>")
            for key, value in context.items():
                html_parts.append(f'<div class="stat"><strong>{key}:</strong> {value}</div>')

        html_parts.append("</body></html>")
        return "\n".join(html_parts)

    def _value_to_html(self, value: Any) -> str:
        """Convert a value to HTML."""
        if isinstance(value, dict):
            items = [f"<li><strong>{k}:</strong> {self._value_to_html(v)}</li>" for k, v in value.items()]
            return f"<ul>{''.join(items)}</ul>"
        elif isinstance(value, list):
            items = [f"<li>{self._value_to_html(item)}</li>" for item in value]
            return f"<ul>{''.join(items)}</ul>"
        else:
            return str(value)

    def suggest_follow_ups(self, data: Any, goal: str) -> List[str]:
        """
        Suggest follow-up questions based on the result.

        Args:
            data: Result data
            goal: Original goal

        Returns:
            List of suggested follow-up questions
        """
        suggestions = []

        if isinstance(data, dict):
            # Security triage suggestions
            if 'classifications' in data:
                if data['classifications'].get('P1'):
                    suggestions.append("Show me P1 alert details")
                if data['classifications'].get('P2'):
                    suggestions.append("Show me P2 alert details")
                if 'kill_chains' in data and data['kill_chains']:
                    suggestions.append("What's the confidence on the kill chains?")
                if 'iocs' in data:
                    suggestions.append("Extract IOCs for threat intel")

            # Inbox triage suggestions
            if 'urgent' in data:
                suggestions.append("Show me urgent emails")
            if 'action_required' in data:
                suggestions.append("Extract action items")

        # Generic suggestions
        if not suggestions:
            suggestions.append("Provide more details")
            suggestions.append("Summarize the key findings")

        return suggestions[:4]  # Return max 4 suggestions
