"""
Adaptive Optimizer for Gmail Agent

Automatically optimizes execution parameters based on dataset size,
available budget, and goal complexity.
"""

from typing import Dict, List, Optional, Tuple
from .goal_interpreter import Action


class AdaptiveOptimizer:
    """Optimizes RLM execution parameters based on context."""

    def __init__(self):
        pass

    def optimize_parameters(
        self,
        email_count: int,
        actions: List[Action],
        budget: float,
        goal: str
    ) -> Dict:
        """
        Optimize execution parameters.

        Args:
            email_count: Number of emails to process
            actions: Planned actions to execute
            budget: Available budget in USD
            goal: User's goal

        Returns:
            Dictionary with optimized parameters:
            - chunk_size: Recommended chunk size
            - max_workers: Number of parallel workers
            - max_results: Max emails to fetch
            - estimated_cost: Estimated execution cost
            - warnings: List of warnings if any
        """
        params = {}
        warnings = []

        # Optimize chunk size
        params['chunk_size'] = self._optimize_chunk_size(email_count)

        # Optimize parallel workers
        params['max_workers'] = self._optimize_workers(email_count, actions)

        # Determine max results (may reduce if budget is tight)
        max_results, cost_warning = self._optimize_max_results(
            email_count, actions, budget
        )
        params['max_results'] = max_results
        if cost_warning:
            warnings.append(cost_warning)

        # Estimate cost
        params['estimated_cost'] = self._estimate_cost(
            max_results, actions, params['max_workers']
        )

        # Check if estimated cost exceeds budget
        if params['estimated_cost'] > budget:
            warnings.append(
                f"Estimated cost (${params['estimated_cost']:.2f}) exceeds budget (${budget:.2f}). "
                f"Consider reducing --max-results or increasing --max-budget."
            )

        params['warnings'] = warnings

        return params

    def _optimize_chunk_size(self, email_count: int) -> int:
        """
        Determine optimal chunk size based on email count.

        Args:
            email_count: Number of emails

        Returns:
            Recommended chunk size
        """
        if email_count < 50:
            # No chunking needed for small datasets
            return email_count
        elif email_count < 200:
            # Small chunks for better parallelization
            return 25
        elif email_count < 500:
            # Medium chunks
            return 50
        else:
            # Larger chunks for efficiency
            return 100

    def _optimize_workers(self, email_count: int, actions: List[Action]) -> int:
        """
        Determine optimal number of parallel workers.

        Args:
            email_count: Number of emails
            actions: Planned actions

        Returns:
            Recommended number of workers
        """
        # Check if any action uses parallel processing
        uses_parallel = any(
            action.function in ['parallel_map', 'parallel_llm_query']
            for action in actions
        )

        if not uses_parallel:
            # No parallel processing, workers don't matter
            return 1

        # Determine workers based on dataset size
        if email_count < 100:
            return 3
        elif email_count < 500:
            return 5
        else:
            return 10

    def _optimize_max_results(
        self,
        email_count: int,
        actions: List[Action],
        budget: float
    ) -> Tuple[int, Optional[str]]:
        """
        Determine maximum number of emails to fetch based on budget.

        Args:
            email_count: Requested number of emails
            actions: Planned actions
            budget: Available budget

        Returns:
            Tuple of (max_results, warning_message)
        """
        # Estimate cost per email for the given actions
        cost_per_email = self._estimate_cost_per_email(actions)

        # Calculate max emails we can afford
        max_affordable = int(budget / cost_per_email)

        if max_affordable < email_count:
            warning = (
                f"Budget (${budget:.2f}) may only support ~{max_affordable} emails. "
                f"Requested {email_count}. Consider reducing --max-results."
            )
            return max_affordable, warning

        return email_count, None

    def _estimate_cost_per_email(self, actions: List[Action]) -> float:
        """
        Estimate cost per email for a sequence of actions.

        Args:
            actions: List of actions to execute

        Returns:
            Estimated cost per email in USD
        """
        # Base costs per action type (per email)
        action_costs = {
            'security_triage': 0.005,  # Expensive due to multiple LLM calls
            'detect_attack_chains': 0.004,
            'phishing_analysis': 0.004,
            'classify_alerts': 0.003,
            'inbox_triage': 0.003,
            'weekly_summary': 0.002,
            'find_action_items': 0.002,
            'parallel_map': 0.003,
            'llm_query': 0.002,
            'chunk_by_sender': 0.0001,  # Cheap operations
            'chunk_by_date': 0.0001,
            'filter_by_keyword': 0.0001,
        }

        total_cost = 0.0
        for action in actions:
            cost = action_costs.get(action.function, 0.001)  # Default to 0.001
            total_cost += cost

        # Return total cost per email
        return max(total_cost, 0.001)  # Minimum 0.001 per email

    def _estimate_cost(
        self,
        email_count: int,
        actions: List[Action],
        max_workers: int
    ) -> float:
        """
        Estimate total execution cost.

        Args:
            email_count: Number of emails
            actions: Planned actions
            max_workers: Number of parallel workers

        Returns:
            Estimated total cost in USD
        """
        cost_per_email = self._estimate_cost_per_email(actions)

        # Base cost
        total_cost = cost_per_email * email_count

        # Add overhead for goal interpretation
        goal_interpretation_cost = 0.01

        # Add overhead for parallel processing (slight increase due to coordination)
        if max_workers > 1:
            parallel_overhead = 0.02
            total_cost += parallel_overhead

        total_cost += goal_interpretation_cost

        return round(total_cost, 2)

    def suggest_optimizations(
        self,
        email_count: int,
        actions: List[Action],
        budget: float
    ) -> List[str]:
        """
        Suggest optimizations to reduce cost or improve performance.

        Args:
            email_count: Number of emails
            actions: Planned actions
            budget: Available budget

        Returns:
            List of optimization suggestions
        """
        suggestions = []

        # Estimate cost
        estimated_cost = self._estimate_cost(email_count, actions, 5)

        # If cost exceeds budget, suggest reducing dataset
        if estimated_cost > budget:
            max_affordable = int(budget / self._estimate_cost_per_email(actions))
            suggestions.append(
                f"Consider reducing --max-results to {max_affordable} to stay within budget"
            )

        # If dataset is large, suggest using bulk read
        if email_count > 500:
            suggestions.append(
                "For large datasets (>500 emails), consider using --max-budget to increase limit"
            )

        # If using expensive operations, suggest caching
        expensive_actions = [
            action for action in actions
            if action.function in ['security_triage', 'detect_attack_chains', 'phishing_analysis']
        ]
        if expensive_actions:
            suggestions.append(
                "This analysis uses expensive operations. Results will be cached for 24 hours."
            )

        return suggestions
