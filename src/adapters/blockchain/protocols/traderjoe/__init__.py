"""TraderJoe Protocol Package.

This package provides modular components for interacting with TraderJoe V2.2 DEX:
- Router: Main swap execution interface with customer-friendly methods
- Strategies: Different swap optimization strategies (fast, cheap, secure)
- PathBuilder: Route optimization and pathfinding logic
- SwapExecutor: Low-level swap execution methods
- Utils: Shared utilities to eliminate code duplication
"""

from .router import TraderJoeProtocol
from .strategies import SwapStrategy, StrategyConfig

__all__ = [
    'TraderJoeProtocol',
    'SwapStrategy',
    'StrategyConfig'
]
