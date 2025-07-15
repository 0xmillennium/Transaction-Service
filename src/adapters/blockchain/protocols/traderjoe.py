"""
Backward Compatibility Module for TraderJoe Protocol.

This module maintains backward compatibility for existing imports while
providing the new modular architecture underneath.
"""

# Import the main class from the new modular structure
from .traderjoe import TraderJoeProtocol

# Re-export for backward compatibility
__all__ = ['TraderJoeProtocol']
