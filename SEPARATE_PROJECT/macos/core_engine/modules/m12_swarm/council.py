"""
Swarm Council — The governing body of sub-agents that guards the Hero Agent.
"""
from dataclasses import dataclass
from typing import List, Optional
import numpy as np
from bol.utils.logging import get_logger

logger = get_logger(__name__)

@dataclass
class SwarmDecision:
    approved: bool
    reason: str
    vetoed_by: Optional[str] = None

class SwarmCouncil:
    """
    The Swarm Council manages a team of tiny Guard Agents.
    Before the Hero Agent performs a physical action, it consults the Council.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SwarmCouncil, cls).__new__(cls)
            cls._instance.guards = []
        return cls._instance

    def register_guard(self, guard):
        """Add a new guard sub-agent to the Swarm."""
        self.guards.append(guard)
        logger.debug(f"[SWARM] Registered new sub-agent: {guard.__class__.__name__}")

    def evaluate(self, action_type: str, x: int, y: int, screenshot: np.ndarray, context: dict) -> SwarmDecision:
        """
        Presents the proposed action to all Guard Agents.
        Requires UNANIMOUS approval. If any Guard vetoes, the action is blocked.
        """
        for guard in self.guards:
            decision = guard.evaluate(action_type, x, y, screenshot, context)
            if not decision.approved:
                logger.warning(f"[SWARM VETO] The {decision.vetoed_by} vetoed the action: {decision.reason}")
                return decision
        
        return SwarmDecision(approved=True, reason="Unanimous approval by the Swarm")

# Global singleton council instance
swarm_council = SwarmCouncil()
