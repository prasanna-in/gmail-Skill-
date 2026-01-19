"""
Function Orchestrator for Gmail Agent

Executes RLM functions by generating Python code and calling gmail_rlm_repl.py.
Handles error recovery, retries, and result parsing.
"""

import ast
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from .goal_interpreter import Action


class ExecutionResult:
    """Represents the result of executing RLM functions."""

    def __init__(
        self,
        success: bool,
        data: Optional[Dict] = None,
        error: Optional[str] = None,
        cost: float = 0.0,
        execution_time: float = 0.0,
        generated_code: str = ""
    ):
        self.success = success
        self.data = data or {}
        self.error = error
        self.cost = cost
        self.execution_time = execution_time
        self.generated_code = generated_code

    def to_dict(self) -> Dict:
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'cost': self.cost,
            'execution_time': self.execution_time,
            'generated_code': self.generated_code
        }


class FunctionOrchestrator:
    """Orchestrates execution of RLM functions."""

    def __init__(self, scripts_dir: Optional[Path] = None, python_path: Optional[str] = None):
        if scripts_dir is None:
            # Assume scripts are in skills/gmail/scripts/
            self.scripts_dir = Path(__file__).parent.parent / 'scripts'
        else:
            self.scripts_dir = Path(scripts_dir)

        # Use virtual environment Python by default
        if python_path is None:
            venv_python = Path.cwd() / '.venv' / 'bin' / 'python'
            if venv_python.exists():
                self.python_path = str(venv_python)
            else:
                self.python_path = sys.executable
        else:
            self.python_path = python_path

        self.rlm_script = self.scripts_dir / 'gmail_rlm_repl.py'
        if not self.rlm_script.exists():
            raise FileNotFoundError(f"RLM script not found: {self.rlm_script}")

    def _parse_result(self, result_str: Any) -> Any:
        """
        Parse RLM result, converting string representations to Python objects.

        Args:
            result_str: Result from RLM (may be string, dict, list, etc.)

        Returns:
            Parsed Python object
        """
        # If already a dict or list, return as-is
        if isinstance(result_str, (dict, list)):
            return result_str

        # If it's a string, try to parse it
        if isinstance(result_str, str):
            # Try to parse as Python literal (dict, list, etc.)
            try:
                return ast.literal_eval(result_str)
            except (ValueError, SyntaxError):
                # If that fails, return as-is (it's a plain string result)
                return result_str

        # For other types, return as-is
        return result_str

    def execute(
        self,
        actions: List[Action],
        query: str,
        max_results: int,
        max_budget: float,
        model: str = "claude-sonnet-4-20250514",
        max_retries: int = 3
    ) -> ExecutionResult:
        """
        Execute a sequence of RLM actions.

        Args:
            actions: List of Action objects to execute
            query: Gmail query string
            max_results: Maximum number of emails to fetch
            max_budget: Budget limit in USD
            model: LLM model to use
            max_retries: Number of retry attempts on failure

        Returns:
            ExecutionResult with data or error
        """
        # Generate Python code from actions
        code = self._generate_code(actions)

        # Execute with retries
        for attempt in range(max_retries):
            try:
                start_time = time.time()

                result = self._execute_rlm_script(
                    code=code,
                    query=query,
                    max_results=max_results,
                    max_budget=max_budget,
                    model=model
                )

                execution_time = time.time() - start_time

                # Parse result
                if result['status'] == 'success':
                    # Parse the result (convert string representations to Python objects)
                    parsed_data = self._parse_result(result.get('result'))

                    return ExecutionResult(
                        success=True,
                        data=parsed_data,
                        cost=result.get('session_stats', {}).get('total_cost', 0.0),
                        execution_time=execution_time,
                        generated_code=code
                    )
                else:
                    # If this is the last attempt, return the error
                    if attempt == max_retries - 1:
                        return ExecutionResult(
                            success=False,
                            error=result.get('message', 'Unknown error'),
                            generated_code=code
                        )

                    # Otherwise, wait and retry
                    time.sleep(2 ** attempt)  # Exponential backoff

            except Exception as e:
                if attempt == max_retries - 1:
                    return ExecutionResult(
                        success=False,
                        error=str(e),
                        generated_code=code
                    )
                time.sleep(2 ** attempt)

        # Should never reach here, but just in case
        return ExecutionResult(
            success=False,
            error="Max retries exceeded",
            generated_code=code
        )

    def _generate_code(self, actions: List[Action]) -> str:
        """
        Generate Python code from a sequence of actions.

        Args:
            actions: List of Action objects

        Returns:
            Python code string to execute in RLM environment
        """
        code_lines = []

        # Add header comment
        code_lines.append("# Generated by Gmail Agent")
        code_lines.append("")

        # Generate code for each action
        for i, action in enumerate(actions):
            code_lines.append(f"# Action {i + 1}: {action.description}")

            # Build function call
            func_name = action.function
            args_str = self._format_args(action.args)

            # Store result in variable
            result_var = f"result_{i}"
            code_lines.append(f"{result_var} = {func_name}({args_str})")
            code_lines.append("")

        # Final output - use the last result
        if actions:
            last_result = f"result_{len(actions) - 1}"
            code_lines.append(f"# Output final result")
            code_lines.append(f"FINAL({last_result})")
        else:
            code_lines.append("FINAL('No actions to execute')")

        return "\n".join(code_lines)

    def _format_args(self, args: Dict[str, Any]) -> str:
        """Format function arguments for Python code."""
        arg_parts = []
        for key, value in args.items():
            if isinstance(value, str):
                # Check if it's a variable reference (like "emails") or a literal
                if value in ['emails', 'llm_query']:
                    arg_parts.append(f"{key}={value}")
                else:
                    # Escape quotes in string literals
                    escaped_value = value.replace("'", "\\'")
                    arg_parts.append(f"{key}='{escaped_value}'")
            elif isinstance(value, (int, float)):
                arg_parts.append(f"{key}={value}")
            elif isinstance(value, bool):
                arg_parts.append(f"{key}={str(value)}")
            elif isinstance(value, (list, dict)):
                arg_parts.append(f"{key}={repr(value)}")
            else:
                arg_parts.append(f"{key}={repr(value)}")

        return ", ".join(arg_parts)

    def _execute_rlm_script(
        self,
        code: str,
        query: str,
        max_results: int,
        max_budget: float,
        model: str
    ) -> Dict:
        """
        Execute the RLM script with generated code.

        Args:
            code: Python code to execute
            query: Gmail query string
            max_results: Maximum number of emails
            max_budget: Budget limit
            model: LLM model to use

        Returns:
            Parsed JSON result from RLM script
        """
        # Build command
        cmd = [
            self.python_path,
            str(self.rlm_script),
            '--query', query,
            '--max-results', str(max_results),
            '--max-budget', str(max_budget),
            '--model', model,
            '--max-depth', '50',  # Set high depth for parallel processing
            '--json-output',  # Request JSON output with session stats
            '--code', code
        ]

        # Execute command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        # Parse output
        try:
            # The script should output JSON
            output = json.loads(result.stdout)
            return output
        except json.JSONDecodeError:
            # If JSON parsing fails, return error
            return {
                'status': 'error',
                'message': f'Failed to parse RLM output. stdout: {result.stdout[:500]}, stderr: {result.stderr[:500]}'
            }

    def execute_custom_code(
        self,
        code: str,
        query: str,
        max_results: int,
        max_budget: float,
        model: str = "claude-sonnet-4-20250514"
    ) -> ExecutionResult:
        """
        Execute custom Python code directly (for script mode).

        Args:
            code: Python code to execute
            query: Gmail query string
            max_results: Maximum number of emails
            max_budget: Budget limit
            model: LLM model to use

        Returns:
            ExecutionResult with data or error
        """
        try:
            start_time = time.time()

            result = self._execute_rlm_script(
                code=code,
                query=query,
                max_results=max_results,
                max_budget=max_budget,
                model=model
            )

            execution_time = time.time() - start_time

            if result['status'] == 'success':
                # Parse the result (convert string representations to Python objects)
                parsed_data = self._parse_result(result.get('result'))

                return ExecutionResult(
                    success=True,
                    data=parsed_data,
                    cost=result.get('session_stats', {}).get('total_cost', 0.0),
                    execution_time=execution_time,
                    generated_code=code
                )
            else:
                return ExecutionResult(
                    success=False,
                    error=result.get('message', 'Unknown error'),
                    generated_code=code
                )

        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                generated_code=code
            )
