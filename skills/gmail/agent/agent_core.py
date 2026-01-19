"""
Agent Core for Gmail Agent

Main agent loop that orchestrates goal interpretation, execution, and formatting.
Supports multi-turn dialogue and session persistence.
"""

import sys
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from .state_manager import StateManager, SessionState
from .goal_interpreter import GoalInterpreter
from .function_orchestrator import FunctionOrchestrator, ExecutionResult
from .result_formatter import ResultFormatter
from .adaptive_optimizer import AdaptiveOptimizer


class AgentCore:
    """Core agent logic for autonomous email analysis."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        output_format: str = "text",
        debug: bool = False
    ):
        """
        Initialize the agent.

        Args:
            model: LLM model to use
            output_format: Output format ('text', 'json', 'html')
            debug: Enable debug mode (shows generated code)
        """
        self.model = model
        self.debug = debug

        # Initialize components
        self.state_manager = StateManager()
        self.goal_interpreter = GoalInterpreter(model=model)
        self.orchestrator = FunctionOrchestrator()
        self.formatter = ResultFormatter(format=output_format)
        self.optimizer = AdaptiveOptimizer()

    def run_agent_mode(
        self,
        goal: str,
        query: str = "newer_than:7d",
        max_results: int = 100,
        max_budget: float = 1.0,
        session_id: Optional[str] = None,
        interactive: bool = True
    ) -> Tuple[str, Optional[str]]:
        """
        Run the agent in autonomous mode.

        Args:
            goal: Natural language goal
            query: Gmail query string
            max_results: Maximum number of emails to fetch
            max_budget: Budget limit in USD
            session_id: Optional session ID to resume
            interactive: Enable multi-turn dialogue

        Returns:
            Tuple of (response, session_id)
        """
        # Load or create session
        if session_id:
            session = self.state_manager.load_session(session_id)
            if not session:
                return f"Error: Session {session_id} not found", None
            print(f"Resumed session: {session_id}")
            print(f"Budget remaining: ${session.budget_remaining:.2f}")
            print()
        else:
            session = self.state_manager.create_session(budget=max_budget)

        # Main agent loop
        current_goal = goal
        while True:
            # Check budget
            if session.budget_remaining <= 0:
                response = "Budget exhausted. Use --max-budget to increase."
                print(response)
                break

            # Execute goal
            try:
                response, cost = self._execute_goal(
                    goal=current_goal,
                    query=query,
                    max_results=max_results,
                    max_budget=session.budget_remaining,
                    conversation_history=session.history
                )

                # Update session
                session.add_turn(current_goal, response, cost)

                # Display response
                print(response)
                print()

                # Show suggested follow-ups (if in interactive mode)
                if interactive:
                    # Parse the result data to suggest follow-ups
                    # (This is a simplified version - in production, we'd extract data from the response)
                    suggestions = self.formatter.suggest_follow_ups({}, current_goal)
                    if suggestions:
                        print("Suggested follow-ups:")
                        for i, suggestion in enumerate(suggestions, 1):
                            print(f"  {i}. {suggestion}")
                        print()

                # Save session
                session_file = self.state_manager.save_session(session)
                print(f"Session saved: {session_file}")
                print(f"Budget used: ${session.budget_used:.4f} | Remaining: ${session.budget_remaining:.4f}")
                print()

                # Multi-turn dialogue
                if interactive and session.budget_remaining > 0:
                    try:
                        next_goal = input("> ").strip()
                        if not next_goal or next_goal.lower() in ['done', 'exit', 'quit']:
                            print("Session ended. Use --resume to continue later.")
                            break
                        current_goal = next_goal
                    except (EOFError, KeyboardInterrupt):
                        print("\nSession ended. Use --resume to continue later.")
                        break
                else:
                    # Non-interactive mode - exit after first turn
                    break

            except Exception as e:
                error_msg = f"Error: {str(e)}"
                print(error_msg)
                session.add_turn(current_goal, error_msg, 0.0)
                self.state_manager.save_session(session)
                break

        return response, session.session_id

    def _execute_goal(
        self,
        goal: str,
        query: str,
        max_results: int,
        max_budget: float,
        conversation_history: List[Tuple[str, str]]
    ) -> Tuple[str, float]:
        """
        Execute a single goal.

        Args:
            goal: Natural language goal
            query: Gmail query string
            max_results: Maximum number of emails
            max_budget: Budget limit
            conversation_history: Previous conversation turns

        Returns:
            Tuple of (response_text, cost)
        """
        # Step 1: Interpret goal
        print("Interpreting goal...")
        try:
            actions, reasoning = self.goal_interpreter.parse_goal(
                goal=goal,
                email_count=max_results,
                conversation_history=conversation_history,
                query_info={'query': query, 'max_results': max_results}
            )
        except Exception as e:
            return f"Failed to interpret goal: {str(e)}", 0.0

        if self.debug:
            print(f"\nReasoning: {reasoning}")
            print(f"Planned actions: {[str(a) for a in actions]}\n")

        # Step 2: Optimize parameters
        print("Optimizing parameters...")
        optimized_params = self.optimizer.optimize_parameters(
            email_count=max_results,
            actions=actions,
            budget=max_budget,
            goal=goal
        )

        # Show warnings
        if optimized_params['warnings']:
            for warning in optimized_params['warnings']:
                print(f"⚠️  {warning}")
            print()

        # Estimate cost
        estimated_cost = optimized_params['estimated_cost']
        print(f"Estimated cost: ${estimated_cost:.4f}")
        print()

        # Ask for confirmation if cost is high
        if estimated_cost > max_budget * 0.5:  # More than 50% of budget
            print(f"This operation will use ~{(estimated_cost / max_budget) * 100:.0f}% of your budget.")
            try:
                confirm = input("Continue? (y/n): ").strip().lower()
                if confirm != 'y':
                    return "Operation cancelled by user.", 0.0
            except (EOFError, KeyboardInterrupt):
                return "Operation cancelled by user.", 0.0

        # Step 3: Execute actions
        print("Executing...")
        result = self.orchestrator.execute(
            actions=actions,
            query=query,
            max_results=optimized_params['max_results'],
            max_budget=max_budget,
            model=self.model
        )

        if self.debug and result.generated_code:
            print("\nGenerated code:")
            print("-" * 50)
            print(result.generated_code)
            print("-" * 50)
            print()

        # Step 4: Format result
        if not result.success:
            return f"Execution failed: {result.error}", 0.0

        context = {
            'cost': result.cost,
            'execution_time': result.execution_time
        }

        response = self.formatter.format_result(
            data=result.data,
            conversation_history=conversation_history,
            context=context
        )

        return response, result.cost

    def run_script_mode(
        self,
        code: str,
        query: str = "newer_than:7d",
        max_results: int = 100,
        max_budget: float = 5.0
    ) -> str:
        """
        Run custom Python code directly (script mode for power users).

        Args:
            code: Python code to execute
            query: Gmail query string
            max_results: Maximum number of emails
            max_budget: Budget limit

        Returns:
            Formatted response
        """
        print("Running in script mode...")
        print()

        # Execute custom code
        result = self.orchestrator.execute_custom_code(
            code=code,
            query=query,
            max_results=max_results,
            max_budget=max_budget,
            model=self.model
        )

        if not result.success:
            return f"Execution failed: {result.error}"

        # Format result
        context = {
            'cost': result.cost,
            'execution_time': result.execution_time
        }

        response = self.formatter.format_result(
            data=result.data,
            conversation_history=None,
            context=context
        )

        return response

    def list_sessions(self) -> str:
        """List all available sessions."""
        sessions = self.state_manager.list_sessions()

        if not sessions:
            return "No sessions found."

        lines = []
        lines.append("Available Sessions:")
        lines.append("─" * 80)
        lines.append(f"{'Session ID':<30} {'Created':<20} {'Turns':<8} {'Budget Used':<12} {'Budget Left'}")
        lines.append("─" * 80)

        for session in sessions:
            lines.append(
                f"{session['session_id']:<30} "
                f"{session['created_at'][:19]:<20} "
                f"{session['turns']:<8} "
                f"${session['budget_used']:<11.4f} "
                f"${session['budget_remaining']:.4f}"
            )

        return "\n".join(lines)
