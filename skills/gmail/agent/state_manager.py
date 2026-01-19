"""
State Manager for Gmail Agent

Handles session persistence, conversation history, and budget tracking.
Sessions are saved to ~/.gmail_agent_sessions/ for resumption.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


class SessionState:
    """Represents a conversation session with the agent."""

    def __init__(self, session_id: str, budget: float = 1.0):
        self.session_id = session_id
        self.history: List[Tuple[str, str]] = []  # [(goal, response), ...]
        self.budget_limit = budget
        self.budget_used = 0.0
        self.budget_remaining = budget
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.metadata: Dict[str, Any] = {}

    def add_turn(self, goal: str, response: str, cost: float = 0.0):
        """Add a conversation turn and update budget."""
        self.history.append((goal, response))
        self.budget_used += cost
        self.budget_remaining = self.budget_limit - self.budget_used
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Convert session to dictionary for JSON serialization."""
        return {
            'session_id': self.session_id,
            'history': self.history,
            'budget_limit': self.budget_limit,
            'budget_used': self.budget_used,
            'budget_remaining': self.budget_remaining,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'SessionState':
        """Create session from dictionary."""
        session = cls(data['session_id'], data['budget_limit'])
        session.history = [tuple(turn) for turn in data['history']]
        session.budget_used = data['budget_used']
        session.budget_remaining = data['budget_remaining']
        session.created_at = data['created_at']
        session.updated_at = data['updated_at']
        session.metadata = data.get('metadata', {})
        return session


class StateManager:
    """Manages session storage and retrieval."""

    def __init__(self, sessions_dir: Optional[Path] = None):
        if sessions_dir is None:
            self.sessions_dir = Path.home() / '.gmail_agent_sessions'
        else:
            self.sessions_dir = Path(sessions_dir)

        # Create sessions directory if it doesn't exist
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def create_session_id(self) -> str:
        """Generate a unique session ID."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"session_{timestamp}"

    def create_session(self, budget: float = 1.0) -> SessionState:
        """Create a new session."""
        session_id = self.create_session_id()
        return SessionState(session_id, budget)

    def save_session(self, session: SessionState) -> Path:
        """Save session to disk."""
        session_file = self.sessions_dir / f"{session.session_id}.json"
        with open(session_file, 'w') as f:
            json.dump(session.to_dict(), f, indent=2)
        return session_file

    def load_session(self, session_id: str) -> Optional[SessionState]:
        """Load session from disk."""
        session_file = self.sessions_dir / f"{session_id}.json"

        if not session_file.exists():
            return None

        try:
            with open(session_file, 'r') as f:
                data = json.load(f)
            return SessionState.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading session {session_id}: {e}")
            return None

    def list_sessions(self) -> List[Dict]:
        """List all available sessions."""
        sessions = []
        for session_file in self.sessions_dir.glob('session_*.json'):
            try:
                with open(session_file, 'r') as f:
                    data = json.load(f)
                sessions.append({
                    'session_id': data['session_id'],
                    'created_at': data['created_at'],
                    'updated_at': data['updated_at'],
                    'turns': len(data['history']),
                    'budget_used': data['budget_used'],
                    'budget_remaining': data['budget_remaining']
                })
            except (json.JSONDecodeError, KeyError):
                continue

        # Sort by most recently updated
        sessions.sort(key=lambda x: x['updated_at'], reverse=True)
        return sessions

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        session_file = self.sessions_dir / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()
            return True
        return False

    def get_session_path(self, session_id: str) -> Path:
        """Get the file path for a session."""
        return self.sessions_dir / f"{session_id}.json"
