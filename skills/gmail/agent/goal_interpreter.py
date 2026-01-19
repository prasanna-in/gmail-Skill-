"""
Goal Interpreter for Gmail Agent

Converts natural language goals into RLM function execution plans.
Uses LLM to analyze user intent and map to available functions.
"""

import json
import os
from typing import Dict, List, Optional, Tuple, Any
from anthropic import Anthropic


class Action:
    """Represents a single RLM function call."""

    def __init__(self, function: str, args: Dict[str, Any], description: str = ""):
        self.function = function
        self.args = args
        self.description = description

    def to_dict(self) -> Dict:
        return {
            'function': self.function,
            'args': self.args,
            'description': self.description
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Action':
        return cls(
            function=data['function'],
            args=data['args'],
            description=data.get('description', '')
        )

    def __repr__(self):
        return f"Action({self.function}, {self.args})"


class GoalInterpreter:
    """Interprets natural language goals and generates RLM execution plans."""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self.client = Anthropic(api_key=api_key)

    def parse_goal(
        self,
        goal: str,
        email_count: int,
        conversation_history: Optional[List[Tuple[str, str]]] = None,
        query_info: Optional[Dict] = None
    ) -> Tuple[List[Action], str]:
        """
        Parse a natural language goal into a sequence of RLM actions.

        Args:
            goal: Natural language goal from user
            email_count: Number of emails to operate on
            conversation_history: Previous conversation turns
            query_info: Information about the email query (query string, labels, etc.)

        Returns:
            Tuple of (actions, reasoning) where actions is a list of Action objects
            and reasoning explains the interpretation
        """
        prompt = self._build_goal_parsing_prompt(
            goal, email_count, conversation_history, query_info
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract text from response
            response_text = response.content[0].text

            # Parse JSON response
            result = json.loads(response_text)

            # Convert to Action objects
            actions = [Action.from_dict(action_dict) for action_dict in result['actions']]
            reasoning = result.get('reasoning', '')

            return actions, reasoning

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}\nResponse: {response_text}")
        except Exception as e:
            raise ValueError(f"Failed to interpret goal: {e}")

    def _build_goal_parsing_prompt(
        self,
        goal: str,
        email_count: int,
        conversation_history: Optional[List[Tuple[str, str]]],
        query_info: Optional[Dict]
    ) -> str:
        """Build the prompt for goal parsing."""

        history_context = ""
        if conversation_history:
            history_context = "\n\nConversation History:\n"
            for turn_goal, turn_response in conversation_history[-3:]:  # Last 3 turns
                history_context += f"User: {turn_goal}\n"
                history_context += f"Agent: {turn_response[:200]}...\n\n"

        query_context = ""
        if query_info:
            query_context = f"\n\nEmail Query Info:\n{json.dumps(query_info, indent=2)}\n"

        prompt = f"""You are an email analysis assistant. The user has {email_count} emails and wants to accomplish the following goal:

"{goal}"
{history_context}{query_context}
Your task is to determine the sequence of RLM (Recursive Language Model) functions to call to accomplish this goal.

Available RLM Functions:

SECURITY WORKFLOWS:
- security_triage(emails): Complete security alert triage (P1-P5 classification, IOCs, kill chains, executive summary)
- detect_attack_chains(emails, window_minutes=5): Detect multi-stage attack patterns
- phishing_analysis(emails): Analyze phishing attempts (credential harvesting, BEC, brand impersonation)
- classify_alerts(emails, llm_query): Batch classify alerts into P1-P5
- extract_iocs(emails): Extract IPs, domains, file hashes, URLs
- map_to_mitre(alert, llm_query): Map alerts to MITRE ATT&CK techniques
- correlate_by_source_ip(emails, llm_query): Analyze alerts by source IP
- detect_suspicious_senders(emails, llm_query): Identify phishing/spoofing
- analyze_attachments(emails): Risk scoring for attachments
- extract_and_analyze_urls(emails): Identify suspicious URLs

GENERAL EMAIL WORKFLOWS:
- inbox_triage(emails): Classify emails into urgent/action_required/fyi/newsletter
- weekly_summary(emails): Generate executive summary of weekly emails
- find_action_items(emails): Extract action items with deadlines
- chunk_by_sender(emails): Group emails by sender
- chunk_by_date(emails): Group emails by date
- chunk_by_thread(emails): Group emails by thread
- chunk_by_size(emails, chunk_size): Split emails into chunks
- filter_by_keyword(emails, pattern): Filter emails by keyword
- filter_by_sender(emails, pattern): Filter emails by sender
- parallel_map(prompt, chunks, context_fn, max_workers=5): Apply prompt to chunks in parallel
- llm_query(prompt, context): Make a recursive LLM call for analysis

DATA EXTRACTION:
- extract_field(emails, field_name): Extract specific field from all emails
- summarize_thread(emails): Summarize email thread
- detect_patterns(emails): Detect patterns in email content

Return a JSON object with this structure:
{{
    "reasoning": "Brief explanation of why you chose these functions",
    "actions": [
        {{
            "function": "function_name",
            "args": {{"arg1": "value1", "arg2": "value2"}},
            "description": "What this step does"
        }}
    ]
}}

IMPORTANT GUIDELINES:
1. If the goal is vague or could be interpreted multiple ways, choose the most likely interpretation based on context
2. For security-related goals, prefer security_triage as a comprehensive starting point
3. For inbox management goals, prefer inbox_triage
4. Use chunk_by_* functions when dealing with large datasets (>100 emails)
5. Use parallel_map for operations that need to process many chunks
6. Keep action sequences short (1-3 actions is usually sufficient)
7. The special argument "emails" refers to the email dataset
8. Only use functions from the list above - don't invent new functions
9. Return ONLY valid JSON, no markdown, no explanation outside the JSON

Examples:

Goal: "Triage security alerts from last week"
{{
    "reasoning": "User wants comprehensive security analysis. security_triage provides P1-P5 classification, IOCs, kill chains, and executive summary.",
    "actions": [
        {{
            "function": "security_triage",
            "args": {{"emails": "emails"}},
            "description": "Complete security alert triage with classification, IOCs, and kill chain detection"
        }}
    ]
}}

Goal: "Summarize my inbox"
{{
    "reasoning": "User wants email categorization and summary. inbox_triage classifies into urgent/action/fyi/newsletter.",
    "actions": [
        {{
            "function": "inbox_triage",
            "args": {{"emails": "emails"}},
            "description": "Classify emails into categories for quick inbox overview"
        }}
    ]
}}

Goal: "Find action items"
{{
    "reasoning": "User wants to extract tasks with deadlines. find_action_items is the specific function for this.",
    "actions": [
        {{
            "function": "find_action_items",
            "args": {{"emails": "emails"}},
            "description": "Extract action items with deadlines and priority"
        }}
    ]
}}

Goal: "Show me P1 alerts"
{{
    "reasoning": "User previously ran triage and now wants to filter for P1. Need to run triage first if not in history.",
    "actions": [
        {{
            "function": "security_triage",
            "args": {{"emails": "emails"}},
            "description": "Run security triage to get P1 classifications"
        }}
    ]
}}

Now interpret the user's goal and return the JSON action plan."""

        return prompt

    def estimate_cost(self, actions: List[Action], email_count: int) -> float:
        """
        Estimate the cost of executing a sequence of actions.

        This is a rough estimate based on typical token usage.
        """
        # Base cost per action (LLM call overhead)
        base_cost = 0.01

        # Per-email processing cost
        per_email_cost = {
            'security_triage': 0.005,  # Expensive due to multiple LLM calls
            'detect_attack_chains': 0.004,
            'phishing_analysis': 0.004,
            'inbox_triage': 0.003,
            'weekly_summary': 0.002,
            'find_action_items': 0.002,
            'parallel_map': 0.003,
            'llm_query': 0.002,
        }

        total_cost = 0.0
        for action in actions:
            # Base cost for the action
            total_cost += base_cost

            # Add per-email cost if applicable
            func_cost = per_email_cost.get(action.function, 0.001)
            total_cost += func_cost * email_count

        return round(total_cost, 2)
