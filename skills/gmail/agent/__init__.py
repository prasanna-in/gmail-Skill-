"""
Gmail Agent Module

⚠️  DEPRECATED: This module is deprecated and will be removed in a future version.

This standalone agent module (1,348 lines) has been replaced with a documentation-driven
approach where Claude Code's general-purpose Agent directly orchestrates RLM operations.

See:
- skills/gmail/RLM_AGENT_GUIDE.md for orchestration guide
- skills/gmail/agent/README_DEPRECATED.md for migration details
- skills/gmail/SKILL.md for current usage patterns

For backward compatibility, this module remains functional but will be removed in v0.5.0.
"""

import warnings

warnings.warn(
    "The gmail.agent module is deprecated and will be removed in v0.5.0. "
    "Claude Code's Agent now orchestrates RLM directly via documentation. "
    "See skills/gmail/RLM_AGENT_GUIDE.md for details.",
    DeprecationWarning,
    stacklevel=2
)

__version__ = "1.0.0-deprecated"
